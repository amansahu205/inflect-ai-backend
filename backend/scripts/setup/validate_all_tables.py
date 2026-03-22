"""
Validate Snowflake tables against local data under DATA_DIR.

Usage (from repo root):
  python backend/scripts/setup/validate_all_tables.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import snowflake.connector

DATA_DIR = Path("D:/MS/Hackathon/HOOHACKS-2026/inflect/data")

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")


def connect():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )


def ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def warn(msg: str) -> None:
    print(f"  ⚠️  {msg}")


def fail(msg: str) -> None:
    print(f"  ❌ {msg}")


def approx_eq(a: Any, b: Any, tol: float = 1e-2) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        fa, fb = float(a), float(b)
        if fa == fb == 0:
            return True
        return abs(fa - fb) <= tol * max(1.0, abs(fb))
    except (TypeError, ValueError):
        return str(a).strip() == str(b).strip()


def _safe_query(cur, sql: str, params: tuple | None = None):
    try:
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        return cur.fetchall(), None
    except Exception as e:
        return None, str(e)


def validate_fundamentals(cur) -> None:
    print("\nTABLE: FUNDAMENTALS")
    fund_dir = DATA_DIR / "fundamentals"
    files = sorted(fund_dir.glob("*.json")) if fund_dir.is_dir() else []
    local_n = len(files)

    rows, err = _safe_query(cur, "SELECT COUNT(*) FROM FUNDAMENTALS")
    if err:
        fail(f"Snowflake COUNT: {err}")
        return
    sf_n = int(rows[0][0])
    if local_n == sf_n:
        ok(f"Row count: {sf_n} (local: {local_n})")
    else:
        warn(f"Row count: Snowflake={sf_n}, local files={local_n}")

    sample = [f.stem.upper() for f in files[:3]]
    if not sample and fund_dir.is_dir():
        sample = ["AAPL", "MSFT", "NVDA"]

    for t in sample:
        fp = fund_dir / f"{t}.json"
        if not fp.is_file():
            warn(f"{t}: no local file, skip spot check")
            continue
        try:
            d = json.loads(fp.read_text(encoding="utf-8", errors="ignore"))
        except Exception as e:
            warn(f"{t}: read JSON failed: {e}")
            continue

        r2, err = _safe_query(
            cur,
            """
            SELECT PE_RATIO, GROSS_MARGIN, ROE, FCF, SECTOR, HIGH_52W
            FROM FUNDAMENTALS WHERE TICKER = %s
            """,
            (t,),
        )
        if err or not r2:
            fail(f"{t}: Snowflake row missing or error: {err}")
            continue
        row = r2[0]
        pairs = [
            ("pe_ratio", row[0], d.get("pe_ratio")),
            ("gross_margins", row[1], d.get("gross_margins")),
            ("roe", row[2], d.get("roe")),
            ("fcf", row[3], d.get("fcf")),
            ("sector", row[4], d.get("sector")),
            ("52w_high", row[5], d.get("52w_high")),
        ]
        mismatches = []
        for label, sf_v, loc_v in pairs:
            if label in ("sector",):
                if (sf_v or "") != (loc_v or ""):
                    mismatches.append(f"{label} local={loc_v!r} SF={sf_v!r}")
            else:
                if not approx_eq(sf_v, loc_v):
                    mismatches.append(f"{label} local={loc_v} SF={sf_v}")
        if mismatches:
            fail(f"{t}: " + "; ".join(mismatches))
        else:
            ok(
                f"{t} pe_ratio: local={d.get('pe_ratio')}, "
                f"SF={row[0]}"
            )

    cols = [
        "PE_RATIO",
        "GROSS_MARGIN",
        "ROE",
        "FCF",
        "SECTOR",
        "HIGH_52W",
    ]
    null_sql = ", ".join(
        f"SUM(CASE WHEN {c} IS NULL THEN 1 ELSE 0 END) AS n_{c.lower()}"
        for c in cols
    )
    nr, err = _safe_query(cur, f"SELECT {null_sql} FROM FUNDAMENTALS")
    if err or not nr:
        warn(f"NULL scan failed: {err}")
        return
    null_row = nr[0]
    total = sf_n if sf_n else 1
    for i, c in enumerate(cols):
        n = int(null_row[i] or 0)
        pct = 100.0 * n / total
        if pct >= 80:
            fail(f"{c} null count: {n}/{total} ← needs fix")
        elif n == 0:
            ok(f"{c} null count: {n}/{total}")
        else:
            warn(f"{c} null count: {n}/{total} ({pct:.1f}%)")


def validate_news(cur) -> None:
    print("\nTABLE: NEWS")
    news_dir = DATA_DIR / "news"
    files = sorted(news_dir.glob("*.json")) if news_dir.is_dir() else []
    expected = 0
    for f in files:
        try:
            articles = json.loads(
                f.read_text(encoding="utf-8", errors="ignore")
            )
            if isinstance(articles, list):
                expected += min(len(articles), 20)
        except Exception:
            pass

    rows, err = _safe_query(cur, "SELECT COUNT(*) FROM NEWS")
    if err:
        fail(f"COUNT: {err}")
        return
    sf_n = int(rows[0][0])
    if expected and sf_n == expected:
        ok(f"Row count: {sf_n} (local expected ≤20 per ticker: {expected})")
    else:
        warn(
            f"Row count: Snowflake={sf_n}, "
            f"local expected sum (max 20/article file)={expected}"
        )

    for ticker in [f.stem.upper() for f in files[:3]]:
        r2, err = _safe_query(
            cur,
            """
            SELECT COUNT(*),
                   SUM(CASE WHEN UPPER(COALESCE(HEADLINE,'')) LIKE %s
                             OR UPPER(COALESCE(SUMMARY,'')) LIKE %s
                        THEN 1 ELSE 0 END)
            FROM NEWS WHERE TICKER = %s
            """,
            (f"%{ticker}%", f"%{ticker}%", ticker),
        )
        if err or not r2:
            warn(f"{ticker} relevance query failed: {err}")
            continue
        tot, rel = int(r2[0][0]), int(r2[0][1] or 0)
        if tot == 0:
            warn(f"{ticker}: no rows in NEWS")
            continue
        pct = 100.0 * rel / tot
        ok(
            f"{ticker} relevance (ticker in headline/summary): "
            f"{rel}/{tot} ({pct:.1f}%)"
        )

    r3, err = _safe_query(
        cur,
        """
        SELECT
          COUNT(*),
          SUM(CASE WHEN SENTIMENT IS NULL OR SENTIMENT = 0 THEN 1 ELSE 0 END)
        FROM NEWS
        """,
    )
    if err or not r3:
        warn(f"Sentiment check: {err}")
        return
    tot, zeroish = int(r3[0][0]), int(r3[0][1] or 0)
    if tot == 0:
        warn("NEWS: empty table")
        return
    if zeroish == tot:
        warn(
            f"Sentiment: all {tot}/{tot} rows are NULL or 0 "
            f"(known pipeline placeholder)"
        )
    else:
        ok(f"Sentiment non-zero rows: {tot - zeroish}/{tot}")


def validate_metrics(cur) -> None:
    print("\nTABLE: METRICS (vs data/fundamentals/*.json)")
    fund_dir = DATA_DIR / "fundamentals"
    files = sorted(fund_dir.glob("*.json")) if fund_dir.is_dir() else []
    sample = [f.stem.upper() for f in files[:3]]

    for t in sample:
        fp = fund_dir / f"{t}.json"
        if not fp.is_file():
            continue
        d = json.loads(fp.read_text(encoding="utf-8", errors="ignore"))
        r2, err = _safe_query(
            cur,
            """
            SELECT HIGH_52W, LOW_52W, REVENUE_GROWTH
            FROM METRICS WHERE TICKER = %s
            """,
            (t,),
        )
        if err or not r2:
            fail(f"{t}: METRICS row missing: {err}")
            continue
        h, lo, rg = r2[0]
        loc_h = d.get("52w_high")
        loc_lo = d.get("52w_low")
        loc_rg = d.get("revenue_growth")
        if approx_eq(h, loc_h) and approx_eq(lo, loc_lo) and approx_eq(
            rg, loc_rg
        ):
            ok(
                f"{t} HIGH_52W local={loc_h}, SF={h}; "
                f"LOW local={loc_lo}, SF={lo}; "
                f"REV_GROWTH local={loc_rg}, SF={rg}"
            )
        else:
            fail(
                f"{t} mismatch: local 52w_high={loc_h} SF={h}; "
                f"52w_low={loc_lo} SF={lo}; "
                f"revenue_growth={loc_rg} SF={rg}"
            )

    null_r, err = _safe_query(
        cur,
        """
        SELECT
          SUM(CASE WHEN HIGH_52W IS NULL THEN 1 ELSE 0 END),
          SUM(CASE WHEN LOW_52W IS NULL THEN 1 ELSE 0 END),
          SUM(CASE WHEN REVENUE_GROWTH IS NULL THEN 1 ELSE 0 END),
          COUNT(*)
        FROM METRICS
        """,
    )
    if err or not null_r:
        warn(f"METRICS NULL scan: {err}")
        return
    nh, nl, nr, tot = null_r[0]
    tot = int(tot or 1)
    for label, n in (("HIGH_52W", nh), ("LOW_52W", nl), ("REVENUE_GROWTH", nr)):
        n = int(n or 0)
        if n == 0:
            ok(f"{label} null count: {n}/{tot}")
        else:
            warn(f"{label} null count: {n}/{tot}")


def validate_prices(cur) -> None:
    print("\nTABLE: PRICES")
    pdir = DATA_DIR / "prices"
    files = sorted(pdir.glob("*.csv")) if pdir.is_dir() else []
    local_rows = 0
    local_min: date | None = None
    local_max: date | None = None
    local_zero = 0

    for f in files:
        try:
            with f.open(newline="", encoding="utf-8", errors="ignore") as fh:
                rdr = csv.DictReader(fh)
                for row in rdr:
                    local_rows += 1
                    dt_raw = row.get("Date") or row.get("date")
                    if not dt_raw:
                        continue
                    try:
                        dtp = datetime.strptime(
                            str(dt_raw)[:10], "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        continue
                    local_min = (
                        dtp if local_min is None else min(local_min, dtp)
                    )
                    local_max = (
                        dtp if local_max is None else max(local_max, dtp)
                    )
                    try:
                        c = float(row.get("Close") or row.get("close") or 0)
                        if c <= 0:
                            local_zero += 1
                    except (TypeError, ValueError):
                        pass
        except Exception:
            pass

    rows, err = _safe_query(cur, "SELECT COUNT(*) FROM PRICES")
    if err:
        fail(f"COUNT: {err}")
        return
    sf_n = int(rows[0][0])
    if local_rows == sf_n:
        ok(f"Row count: {sf_n} (local CSV rows: {local_rows})")
    else:
        warn(f"Row count: Snowflake={sf_n}, local CSV rows={local_rows}")

    rng, err = _safe_query(
        cur,
        "SELECT MIN(TRADE_DATE), MAX(TRADE_DATE) FROM PRICES",
    )
    if err or not rng:
        warn(f"Date range query failed: {err}")
    else:
        mn, mx = rng[0]
        ok(f"Snowflake date range: {mn} .. {mx}")
        if local_min and local_max:
            ok(f"Local CSV date range: {local_min} .. {local_max}")
        if mn and mx:
            try:
                y0 = int(str(mn)[:4])
                y1 = int(str(mx)[:4])
                if 2016 <= y0 and y1 <= 2026:
                    ok("Date range 2016–2026 (spot check on years)")
                else:
                    warn(
                        f"Date range years {y0}-{y1} outside 2016-2026 "
                        f"(adjust if expected)"
                    )
            except Exception:
                pass

    zr, err = _safe_query(
        cur,
        "SELECT COUNT(*) FROM PRICES WHERE CLOSE_PRICE <= 0",
    )
    if err:
        warn(f"Zero-price check: {err}")
    else:
        z = int(zr[0][0])
        if z == 0:
            ok("No zero/negative CLOSE_PRICE in Snowflake")
        else:
            fail(f"Rows with CLOSE_PRICE <= 0: {z}")
    if local_zero:
        warn(f"Local CSV rows with Close<=0: {local_zero}")


def validate_recommendations(cur) -> None:
    print("\nTABLE: RECOMMENDATIONS")
    rdir = DATA_DIR / "recommendations"
    files = sorted(rdir.glob("*.json")) if rdir.is_dir() else []
    expected = 0
    analyst_sum = 0
    for f in files:
        try:
            recs = json.loads(
                f.read_text(encoding="utf-8", errors="ignore")
            )
            if isinstance(recs, list):
                for rec in recs[:12]:
                    expected += 1
                    analyst_sum += int(rec.get("strongBuy", 0) or 0)
                    analyst_sum += int(rec.get("buy", 0) or 0)
                    analyst_sum += int(rec.get("hold", 0) or 0)
                    analyst_sum += int(rec.get("sell", 0) or 0)
                    analyst_sum += int(rec.get("strongSell", 0) or 0)
        except Exception:
            pass

    rows, err = _safe_query(cur, "SELECT COUNT(*) FROM RECOMMENDATIONS")
    if err:
        fail(f"COUNT: {err}")
        return
    sf_n = int(rows[0][0])
    if expected == sf_n:
        ok(f"Row count: {sf_n} (local rows counted: {expected})")
    else:
        warn(
            f"Row count: Snowflake={sf_n}, "
            f"local expected (recs per file, cap 12)={expected}"
        )

    ar, err = _safe_query(
        cur,
        """
        SELECT SUM(STRONG_BUY + BUY + HOLD + SELL + STRONG_SELL)
        FROM RECOMMENDATIONS
        """,
    )
    if err or not ar:
        warn(f"Analyst sum: {err}")
    else:
        s = int(ar[0][0] or 0)
        if s > 0:
            ok(f"Analyst rating counts total (all rows): {s} > 0")
        else:
            fail("Analyst counts sum to 0 in Snowflake")


def validate_sec_embeddings(cur) -> None:
    print("\nTABLE: SEC_EMBEDDINGS")
    rows, err = _safe_query(
        cur,
        """
        SELECT TICKER, COUNT(*) AS chunks
        FROM SEC_EMBEDDINGS
        GROUP BY TICKER
        ORDER BY chunks DESC
        LIMIT 5
        """,
    )
    if err:
        fail(f"Per-ticker chunks: {err}")
        return
    if not rows:
        warn("SEC_EMBEDDINGS: no rows")
        return
    ok("Top tickers by chunk count:")
    for t, c in rows:
        print(f"  — {t}: {c} chunks")

    rng, err = _safe_query(
        cur,
        "SELECT MIN(FILING_DATE), MAX(FILING_DATE) FROM SEC_EMBEDDINGS",
    )
    if err or not rng:
        warn(f"Filing date range: {err}")
    else:
        ok(f"Filing date range: {rng[0][0]} .. {rng[0][1]}")

    empty, err = _safe_query(
        cur,
        """
        SELECT
          COUNT(*),
          SUM(CASE WHEN CHUNK_TEXT IS NULL OR TRIM(CHUNK_TEXT) = ''
              THEN 1 ELSE 0 END)
        FROM SEC_EMBEDDINGS
        """,
    )
    if err or not empty:
        warn(f"Empty chunk check: {err}")
        return
    tot, emp = int(empty[0][0]), int(empty[0][1] or 0)
    if emp == 0:
        ok(f"Empty CHUNK_TEXT: {emp}/{tot}")
    else:
        fail(f"Empty CHUNK_TEXT rows: {emp}/{tot}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    print("=" * 60)
    print("  INFLECT — validate Snowflake vs local files")
    print(f"  DATA_DIR: {DATA_DIR}")
    print(f"  Run at: {datetime.now().isoformat(timespec='seconds')}")
    print("=" * 60)

    if not DATA_DIR.is_dir():
        warn(f"DATA_DIR does not exist: {DATA_DIR} — local counts will be 0")

    try:
        conn = connect()
    except Exception as e:
        fail(f"Snowflake connection failed: {e}")
        return

    cur = conn.cursor()
    try:
        validate_fundamentals(cur)
        validate_news(cur)
        validate_metrics(cur)
        validate_prices(cur)
        validate_recommendations(cur)
        validate_sec_embeddings(cur)
    finally:
        cur.close()
        conn.close()

    print("\n" + "=" * 60)
    print("  Validation run complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
