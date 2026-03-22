"""
Upload fundamentals, news, metrics,
recommendations to Snowflake
FIXED: all JSON key names correct
       ROE, FCF, DIV_YIELD now included
       metrics uses fundamentals JSON for 52W data
"""

import json
import hashlib
import snowflake.connector
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
from datetime import datetime, timezone
import os

load_dotenv(Path(
    'D:/MS/Hackathon/HOOHACKS-2026/inflect/.env'))

DATA_DIR = Path(
    'D:/MS/Hackathon/HOOHACKS-2026/inflect/data')


def connect():
    return snowflake.connector.connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    )


def unix_to_dt(ts):
    try:
        return datetime.utcfromtimestamp(
            int(ts)).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return '2024-01-01 00:00:00'


def make_id(ticker, headline):
    return hashlib.md5(
        f"{ticker}{headline}".encode()
    ).hexdigest()[:100]


def _fundamentals_values(ticker: str, d: dict) -> tuple:
    """
    Map fundamentals/*.json keys to FUNDAMENTALS columns (see alter_fundamentals.sql).
    Keys: ticker, name, sector, industry, market_cap, pe_ratio, forward_pe, peg_ratio,
    price_to_book, price_to_sales, eps, eps_forward, revenue, revenue_growth,
    gross_margins, profit_margins, ebitda, ebitda_margins, operating_margins,
    debt_to_equity, current_ratio, beta, roe, roa, fcf, total_cash, total_debt,
    dividend_yield, employees, ceo, website, description, 52w_high, 52w_low,
    avg_volume
    """
    desc = d.get('description')
    if desc is not None:
        desc = str(desc)
    return (
        ticker,
        d.get('name'),
        d.get('sector'),
        d.get('industry'),
        d.get('market_cap'),
        d.get('pe_ratio'),
        d.get('forward_pe'),
        d.get('peg_ratio'),
        d.get('price_to_book'),
        d.get('price_to_sales'),
        d.get('eps'),
        d.get('eps_forward'),
        d.get('revenue'),
        d.get('revenue_growth'),
        d.get('gross_margins'),
        d.get('profit_margins'),
        d.get('ebitda'),
        d.get('ebitda_margins'),
        d.get('operating_margins'),
        d.get('debt_to_equity'),
        d.get('current_ratio'),
        d.get('beta'),
        d.get('roe'),
        d.get('roa'),
        d.get('fcf'),
        d.get('total_cash'),
        d.get('total_debt'),
        d.get('dividend_yield'),
        d.get('employees'),
        d.get('ceo'),
        d.get('website'),
        desc,
        d.get('52w_high'),
        d.get('52w_low'),
        d.get('avg_volume'),
        datetime.now(timezone.utc),
    )


def upload_fundamentals(cursor, conn):
    files = list(
        (DATA_DIR / 'fundamentals').glob('*.json'))
    print(f"Uploading {len(files)} fundamentals (full JSON)...")

    cursor.execute("TRUNCATE TABLE FUNDAMENTALS")
    conn.commit()

    sql = (
        "INSERT INTO FUNDAMENTALS ("
        "TICKER, COMPANY_NAME, SECTOR, INDUSTRY, MARKET_CAP, "
        "PE_RATIO, FORWARD_PE, PEG_RATIO, PRICE_TO_BOOK, PRICE_TO_SALES, "
        "EPS, EPS_FORWARD, REVENUE, REVENUE_GROWTH, "
        "GROSS_MARGIN, PROFIT_MARGIN, EBITDA, EBITDA_MARGINS, OPERATING_MARGINS, "
        "DEBT_EQUITY, CURRENT_RATIO, BETA, ROE, ROA, FCF, "
        "TOTAL_CASH, TOTAL_DEBT, DIV_YIELD, "
        "EMPLOYEES, CEO, WEBSITE, DESCRIPTION, "
        "HIGH_52W, LOW_52W, AVG_VOLUME, "
        "UPDATED_AT"
        ") VALUES ("
        "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
        "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s"
        ")"
    )

    uploaded = 0
    errors = 0
    for f in tqdm(files):
        try:
            d = json.loads(f.read_text(
                encoding='utf-8', errors='ignore'))
            ticker = f.stem.upper()
            cursor.execute(sql, _fundamentals_values(ticker, d))
            uploaded += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"\nError {f.stem}: {e}")

    conn.commit()
    print(
        f"Fundamentals done! "
        f"{uploaded} uploaded, {errors} errors")


def upload_news(cursor, conn):
    files = list(
        (DATA_DIR / 'news').glob('*.json'))
    print(
        f"Uploading news for {len(files)} tickers...")

    cursor.execute("TRUNCATE TABLE NEWS")
    conn.commit()

    uploaded = 0
    errors = 0
    for f in tqdm(files):
        try:
            articles = json.loads(f.read_text(
                encoding='utf-8', errors='ignore'))
            ticker = f.stem.upper()

            if not isinstance(articles, list):
                continue

            rows = []
            for article in articles[:20]:
                try:
                    headline = str(
                        article.get(
                            'headline', ''))[:500]
                    if not headline:
                        continue
                    rows.append((
                        make_id(ticker, headline),
                        ticker,
                        headline,
                        str(article.get(
                            'summary', ''))[:2000],
                        str(article.get(
                            'source', ''))[:100],
                        str(article.get(
                            'url', ''))[:500],
                        unix_to_dt(
                            article.get('datetime', 0)),
                        0.0,
                    ))
                except Exception:
                    errors += 1

            if rows:
                cursor.executemany(
                    "INSERT INTO NEWS "
                    "(ID, TICKER, HEADLINE, "
                    "SUMMARY, SOURCE_NAME, "
                    "URL, PUBLISHED_AT, SENTIMENT) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    rows
                )
                conn.commit()
                uploaded += len(rows)

        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"\nError {f.stem}: {e}")

    print(
        f"News done! "
        f"{uploaded} uploaded, {errors} errors")


def upload_metrics(cursor, conn):
    """
    Metrics uses fundamentals JSON for 52W data
    since it has 52w_high and 52w_low fields.
    Falls back to metrics/ folder for Finnhub data.
    """
    fund_files = list(
        (DATA_DIR / 'fundamentals').glob('*.json'))
    metric_files = list(
        (DATA_DIR / 'metrics').glob('*.json'))

    print(f"Uploading {len(fund_files)} metrics...")

    cursor.execute("TRUNCATE TABLE METRICS")
    conn.commit()

    # Build metrics lookup from Finnhub metrics/
    finnhub_metrics = {}
    for f in metric_files:
        try:
            d = json.loads(f.read_text(
                encoding='utf-8', errors='ignore'))
            ticker = f.stem.upper()
            metric = d.get('metric', d)
            finnhub_metrics[ticker] = metric
        except Exception:
            pass

    uploaded = 0
    errors = 0
    for f in tqdm(fund_files):
        try:
            d = json.loads(f.read_text(
                encoding='utf-8', errors='ignore'))
            ticker = f.stem.upper()
            fm = finnhub_metrics.get(ticker, {})

            cursor.execute(
                "INSERT INTO METRICS "
                "(TICKER, HIGH_52W, LOW_52W, "
                "BETA, REVENUE_GROWTH) "
                "VALUES (%s,%s,%s,%s,%s)",
                (
                    ticker,
                    # 52W from fundamentals JSON
                    d.get('52w_high') or
                    fm.get('52WeekHigh'),
                    d.get('52w_low') or
                    fm.get('52WeekLow'),
                    d.get('beta') or
                    fm.get('beta'),
                    d.get('revenue_growth') or
                    fm.get('revenueGrowthTTMYoy')
                )
            )
            uploaded += 1
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"\nError {f.stem}: {e}")

    conn.commit()
    print(
        f"Metrics done! "
        f"{uploaded} uploaded, {errors} errors")


def upload_recommendations(cursor, conn):
    files = list(
        (DATA_DIR / 'recommendations').glob('*.json'))
    print(
        f"Uploading {len(files)} recommendations...")

    cursor.execute("TRUNCATE TABLE RECOMMENDATIONS")
    conn.commit()

    uploaded = 0
    errors = 0
    for f in tqdm(files):
        try:
            recs = json.loads(f.read_text(
                encoding='utf-8', errors='ignore'))
            ticker = f.stem.upper()

            if not isinstance(recs, list):
                continue

            rows = []
            for rec in recs[:12]:
                period = str(rec.get('period', ''))
                if not period:
                    continue
                rows.append((
                    ticker,
                    period,
                    int(rec.get('strongBuy', 0) or 0),
                    int(rec.get('buy', 0) or 0),
                    int(rec.get('hold', 0) or 0),
                    int(rec.get('sell', 0) or 0),
                    int(rec.get('strongSell', 0) or 0)
                ))

            if rows:
                cursor.executemany(
                    "INSERT INTO RECOMMENDATIONS "
                    "(TICKER, PERIOD, STRONG_BUY, "
                    "BUY, HOLD, SELL, STRONG_SELL) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    rows
                )
                conn.commit()
                uploaded += len(rows)

        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"\nError {f.stem}: {e}")

    print(
        f"Recommendations done! "
        f"{uploaded} uploaded, {errors} errors")


def main():
    print("Connecting to Snowflake...")
    conn = connect()
    cursor = conn.cursor()
    print("Connected!\n")

    upload_fundamentals(cursor, conn)
    upload_news(cursor, conn)
    upload_metrics(cursor, conn)
    upload_recommendations(cursor, conn)

    cursor.close()
    conn.close()

    print("\n" + "="*50)
    print("ALL DONE!")
    print("="*50)
    print("Verify in Snowflake:")
    print(
        "SELECT 'FUNDAMENTALS', COUNT(*) "
        "FROM FUNDAMENTALS")
    print(
        "UNION ALL SELECT 'NEWS', "
        "COUNT(*) FROM NEWS")
    print(
        "UNION ALL SELECT 'METRICS', "
        "COUNT(*) FROM METRICS")
    print(
        "UNION ALL SELECT 'RECOMMENDATIONS', "
        "COUNT(*) FROM RECOMMENDATIONS;")

    print("\nSpot check AAPL fundamentals:")
    print(
        "SELECT TICKER, PE_RATIO, ROE, "
        "FCF, DIV_YIELD FROM FUNDAMENTALS "
        "WHERE TICKER = 'AAPL';")

    print("\nSpot check AAPL metrics:")
    print(
        "SELECT * FROM METRICS "
        "WHERE TICKER = 'AAPL';")


if __name__ == '__main__':
    main()