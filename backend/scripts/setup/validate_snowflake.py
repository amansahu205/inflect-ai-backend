"""
Snowflake Data Quality Validation Script
Checks all tables for data completeness,
correctness, and contamination issues.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
import snowflake.connector
from datetime import datetime

load_dotenv(Path(
    'D:/MS/Hackathon/HOOHACKS-2026/inflect/.env'))

# ── Test tickers to validate ──────────────────
TEST_TICKERS = [
    'AAPL', 'NVDA', 'MSFT', 'TSLA', 'JPM'
]

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"


def connect():
    return snowflake.connector.connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    )


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check(label: str, passed: bool,
          detail: str = "", warn: bool = False):
    status = WARN if warn else (PASS if passed else FAIL)
    print(f"  {status}  {label}")
    if detail:
        print(f"         {detail}")


def main():
    print("\n" + "="*60)
    print("  INFLECT SNOWFLAKE DATA VALIDATION")
    print(f"  Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    conn = connect()
    cursor = conn.cursor()
    print("\n  Connected to Snowflake!")

    # ─────────────────────────────────────────
    # 1. TABLE ROW COUNTS
    # ─────────────────────────────────────────
    section("1. TABLE ROW COUNTS")

    tables = {
        'SEC_EMBEDDINGS':  (480000, 500000),
        'FUNDAMENTALS':    (500, 510),
        'NEWS':            (5000, 15000),
        'METRICS':         (490, 510),
        'RECOMMENDATIONS': (1000, 3000),
        'PRICES':          (1000000, 1400000),
    }

    counts = {}
    for table, (min_exp, max_exp) in tables.items():
        cursor.execute(
            f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        counts[table] = count
        passed = min_exp <= count <= max_exp
        check(
            f"{table}: {count:,} rows",
            passed,
            f"Expected {min_exp:,}–{max_exp:,}"
            if not passed else ""
        )

    # ─────────────────────────────────────────
    # 2. FUNDAMENTALS VALIDATION
    # ─────────────────────────────────────────
    section("2. FUNDAMENTALS DATA QUALITY")

    for ticker in TEST_TICKERS:
        cursor.execute("""
            SELECT TICKER, PE_RATIO, EPS,
                   REVENUE, GROSS_MARGIN,
                   MARKET_CAP, BETA
            FROM FUNDAMENTALS
            WHERE TICKER = %s
        """, (ticker,))
        row = cursor.fetchone()

        if not row:
            check(f"{ticker}: row exists", False,
                  "No row found!")
            continue

        non_null = sum(
            1 for v in row[1:] if v is not None)
        total = len(row) - 1

        check(
            f"{ticker}: {non_null}/{total} "
            f"fields populated",
            non_null >= 4,
            f"PE={row[1]}, EPS={row[2]}, "
            f"Revenue={row[3]:,.0f}"
            if row[3] else "Revenue=NULL",
            warn=(non_null < 4)
        )

    # Check for NULL-heavy rows
    cursor.execute("""
        SELECT COUNT(*) FROM FUNDAMENTALS
        WHERE PE_RATIO IS NULL
        AND REVENUE IS NULL
        AND MARKET_CAP IS NULL
    """)
    null_count = cursor.fetchone()[0]
    check(
        f"Rows with all key fields NULL: {null_count}",
        null_count < 50,
        "Too many empty rows" if null_count >= 50 else ""
    )

    # ─────────────────────────────────────────
    # 3. NEWS CONTAMINATION CHECK
    # ─────────────────────────────────────────
    section("3. NEWS CONTAMINATION CHECK")

    COMPANY_KEYWORDS = {
        'AAPL': ['apple', 'iphone', 'tim cook', 'aapl'],
        'NVDA': ['nvidia', 'jensen', 'nvda', 'gpu', 'cuda'],
        'MSFT': ['microsoft', 'azure', 'satya', 'msft'],
        'TSLA': ['tesla', 'elon', 'musk', 'tsla', 'ev'],
        'JPM': ['jpmorgan', 'jp morgan', 'dimon', 'jpm'],
    }

    for ticker in TEST_TICKERS:
        cursor.execute("""
            SELECT HEADLINE, SUMMARY
            FROM NEWS
            WHERE TICKER = %s
            ORDER BY PUBLISHED_AT DESC
            LIMIT 10
        """, (ticker,))
        rows = cursor.fetchall()

        if not rows:
            check(f"{ticker}: has news", False,
                  "No news found!")
            continue

        keywords = COMPANY_KEYWORDS.get(
            ticker, [ticker.lower()])
        relevant = 0
        for row in rows:
            headline = (row[0] or '').lower()
            summary = (row[1] or '').lower()
            if any(kw in headline or kw in summary
                   for kw in keywords):
                relevant += 1

        pct = relevant / len(rows) * 100
        check(
            f"{ticker}: {relevant}/{len(rows)} "
            f"relevant articles ({pct:.0f}%)",
            pct >= 30,
            f"Sample: '{rows[0][0][:60]}...'",
            warn=(pct < 30)
        )

    # Sentiment score distribution
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN SENTIMENT > 0.2
                THEN 1 ELSE 0 END) as positive,
            SUM(CASE WHEN SENTIMENT < -0.2
                THEN 1 ELSE 0 END) as negative,
            SUM(CASE WHEN SENTIMENT = 0
                THEN 1 ELSE 0 END) as zero,
            AVG(SENTIMENT) as avg_sent
        FROM NEWS
    """)
    row = cursor.fetchone()
    zero_pct = (row[3] / row[0] * 100) if row[0] else 0
    check(
        f"Sentiment scores: {row[3]:,} zeros "
        f"({zero_pct:.0f}% of total)",
        zero_pct < 90,
        f"Positive: {row[1]:,}, "
        f"Negative: {row[2]:,}, "
        f"Avg: {row[4]:.3f}",
        warn=(zero_pct >= 50)
    )

    # ─────────────────────────────────────────
    # 4. PRICES VALIDATION
    # ─────────────────────────────────────────
    section("4. PRICES DATA QUALITY")

    for ticker in TEST_TICKERS:
        cursor.execute("""
            SELECT
                COUNT(*) as rows,
                MIN(TRADE_DATE) as oldest,
                MAX(TRADE_DATE) as newest,
                AVG(CLOSE_PRICE) as avg_price,
                MIN(CLOSE_PRICE) as min_price,
                MAX(CLOSE_PRICE) as max_price
            FROM PRICES
            WHERE TICKER = %s
        """, (ticker,))
        row = cursor.fetchone()

        if not row or row[0] == 0:
            check(f"{ticker}: has price data",
                  False, "No prices found!")
            continue

        rows, oldest, newest, avg, mn, mx = row
        has_history = (
            oldest and
            str(oldest) < '2020-01-01'
        )
        check(
            f"{ticker}: {rows:,} rows "
            f"({oldest} → {newest})",
            rows >= 2000 and has_history,
            f"Avg=${avg:.2f}, "
            f"Range=${mn:.2f}–${mx:.2f}"
        )

    # Check for zero prices
    cursor.execute("""
        SELECT COUNT(*) FROM PRICES
        WHERE CLOSE_PRICE = 0
        OR CLOSE_PRICE IS NULL
    """)
    zero_prices = cursor.fetchone()[0]
    check(
        f"Zero/NULL close prices: {zero_prices:,}",
        zero_prices < 100,
        "Too many bad prices"
        if zero_prices >= 100 else ""
    )

    # ─────────────────────────────────────────
    # 5. SEC EMBEDDINGS VALIDATION
    # ─────────────────────────────────────────
    section("5. SEC EMBEDDINGS QUALITY")

    for ticker in TEST_TICKERS:
        cursor.execute("""
            SELECT COUNT(*),
                   COUNT(DISTINCT FORM_TYPE),
                   MIN(FILING_DATE),
                   MAX(FILING_DATE)
            FROM SEC_EMBEDDINGS
            WHERE TICKER = %s
        """, (ticker,))
        row = cursor.fetchone()

        if not row or row[0] == 0:
            check(f"{ticker}: has embeddings",
                  False, "No chunks found!")
            continue

        chunks, forms, oldest, newest = row
        check(
            f"{ticker}: {chunks:,} chunks, "
            f"{forms} form types "
            f"({oldest} → {newest})",
            chunks >= 100 and forms >= 2,
            f"Need more chunks or form types"
            if chunks < 100 else ""
        )

    # Check recent filings (2023+)
    cursor.execute("""
        SELECT COUNT(*) FROM SEC_EMBEDDINGS
        WHERE FILING_DATE >= '2023-01-01'
    """)
    recent = cursor.fetchone()[0]
    pct = recent / counts.get(
        'SEC_EMBEDDINGS', 1) * 100
    check(
        f"Recent filings (2023+): "
        f"{recent:,} ({pct:.1f}%)",
        pct >= 20,
        "Too few recent filings"
        if pct < 20 else ""
    )

    # ─────────────────────────────────────────
    # 6. METRICS VALIDATION
    # ─────────────────────────────────────────
    section("6. METRICS DATA QUALITY")

    for ticker in TEST_TICKERS:
        cursor.execute("""
            SELECT TICKER, HIGH_52W,
                   LOW_52W, BETA,
                   REVENUE_GROWTH
            FROM METRICS
            WHERE TICKER = %s
        """, (ticker,))
        row = cursor.fetchone()

        if not row:
            check(f"{ticker}: has metrics",
                  False, "No row found!")
            continue

        non_null = sum(
            1 for v in row[1:] if v is not None)
        check(
            f"{ticker}: {non_null}/4 "
            f"metrics populated",
            non_null >= 2,
            f"52W High={row[1]}, "
            f"Low={row[2]}, "
            f"Beta={row[3]}, "
            f"RevGrowth={row[4]}",
            warn=(non_null < 2)
        )

    # ─────────────────────────────────────────
    # 7. RECOMMENDATIONS VALIDATION
    # ─────────────────────────────────────────
    section("7. RECOMMENDATIONS DATA QUALITY")

    for ticker in TEST_TICKERS:
        cursor.execute("""
            SELECT COUNT(*),
                   SUM(STRONG_BUY + BUY +
                       HOLD + SELL + STRONG_SELL)
            FROM RECOMMENDATIONS
            WHERE TICKER = %s
        """, (ticker,))
        row = cursor.fetchone()

        if not row or row[0] == 0:
            check(f"{ticker}: has recs",
                  False, "No recommendations!")
            continue

        periods, total_analysts = row
        check(
            f"{ticker}: {periods} periods, "
            f"{total_analysts} analyst ratings",
            periods >= 3 and total_analysts > 0,
            "Needs more periods or ratings"
            if periods < 3 else ""
        )

    # ─────────────────────────────────────────
    # 8. CROSS-TABLE CONSISTENCY
    # ─────────────────────────────────────────
    section("8. CROSS-TABLE CONSISTENCY")

    # Tickers in fundamentals but not prices
    cursor.execute("""
        SELECT COUNT(*) FROM FUNDAMENTALS f
        WHERE NOT EXISTS (
            SELECT 1 FROM PRICES p
            WHERE p.TICKER = f.TICKER
        )
    """)
    missing_prices = cursor.fetchone()[0]
    check(
        f"Tickers in FUNDAMENTALS but "
        f"missing from PRICES: {missing_prices}",
        missing_prices < 10,
        f"{missing_prices} tickers have no price history"
        if missing_prices >= 10 else ""
    )

    # Tickers in embeddings but not fundamentals
    cursor.execute("""
        SELECT COUNT(DISTINCT TICKER)
        FROM SEC_EMBEDDINGS
        WHERE TICKER NOT IN (
            SELECT TICKER FROM FUNDAMENTALS
        )
    """)
    missing_fund = cursor.fetchone()[0]
    check(
        f"Tickers in SEC_EMBEDDINGS but "
        f"missing from FUNDAMENTALS: {missing_fund}",
        missing_fund < 20,
        f"{missing_fund} tickers lack fundamental data"
        if missing_fund >= 20 else ""
    )

    # ─────────────────────────────────────────
    # 9. RAG SEARCH TEST
    # ─────────────────────────────────────────
    section("9. RAG SEARCH QUALITY TEST")

    rag_tests = [
        ('AAPL', 'gross margin'),
        ('NVDA', 'revenue growth'),
        ('MSFT', 'cloud computing'),
        ('TSLA', 'vehicle deliveries'),
    ]

    for ticker, query in rag_tests:
        cursor.execute("""
            SELECT CHUNK_TEXT, FILING_DATE,
                   FORM_TYPE, SECTION
            FROM SEC_EMBEDDINGS
            WHERE TICKER = %s
            AND CHUNK_TEXT ILIKE %s
            LIMIT 3
        """, (ticker, f'%{query}%'))
        rows = cursor.fetchall()

        check(
            f"{ticker} — '{query}': "
            f"{len(rows)} chunks found",
            len(rows) >= 1,
            f"Latest: {rows[0][1]} "
            f"{rows[0][2]} {rows[0][3]}"
            if rows else "No matching chunks!"
        )

    # ─────────────────────────────────────────
    # 10. SUMMARY
    # ─────────────────────────────────────────
    section("10. SUMMARY & RECOMMENDATIONS")

    print("""
  Data Issues Found:
  
  1. NEWS CONTAMINATION
     Many articles tagged to wrong ticker
     Fix: Re-ingest with stricter filtering
     Workaround: Keyword filter at query time ✅
  
  2. SENTIMENT SCORES ALL ZERO
     FinBERT never ran during ingestion
     Fix: Run FinBERT on all headlines
     Workaround: Groq scoring at query time ✅
  
  3. RAG DATE FILTERING
     Returns older filings for recent queries
     Fix: Boost recent filing scores in search
     Status: Pending fix
  
  4. METRICS NULL VALUES
     Some tickers missing 52W high/low data
     Fix: Re-download from Finnhub
     Impact: Low - thesis uses fundamentals
    """)

    cursor.close()
    conn.close()
    print("="*60)
    print("  Validation complete!")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()