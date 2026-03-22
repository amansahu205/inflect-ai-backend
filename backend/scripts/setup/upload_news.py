"""
Upload news JSONs to Snowflake NEWS table
Fixed: datetime is Unix timestamp integer
"""

import json
import hashlib
import snowflake.connector
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
from datetime import datetime
import os

load_dotenv(Path(
    'D:/MS/Hackathon/HOOHACKS-2026/inflect/.env'))

NEWS_DIR = Path(
    'D:/MS/Hackathon/HOOHACKS-2026/inflect/data/news')


def connect():
    return snowflake.connector.connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    )


def make_id(ticker: str, headline: str) -> str:
    return hashlib.md5(
        f"{ticker}{headline}".encode()
    ).hexdigest()[:100]


def unix_to_dt(ts):
    """Convert Unix timestamp to datetime string"""
    try:
        return datetime.utcfromtimestamp(
            int(ts)
        ).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return '2024-01-01 00:00:00'


def main():
    files = list(NEWS_DIR.glob('*.json'))
    print(f"Uploading news for {len(files)} tickers...")

    conn = connect()
    cursor = conn.cursor()
    print("Connected!")

    print("Truncating NEWS table...")
    cursor.execute("TRUNCATE TABLE NEWS")
    conn.commit()

    uploaded = 0
    errors = 0

    for f in tqdm(files):
        try:
            articles = json.loads(
                f.read_text(
                    encoding='utf-8',
                    errors='ignore'))

            if not isinstance(articles, list):
                continue

            ticker = f.stem.upper()
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
                            article.get('datetime', 0))
                    ))
                except Exception:
                    errors += 1

            if rows:
                cursor.executemany(
                    "INSERT INTO NEWS "
                    "(ID, TICKER, HEADLINE, "
                    "SUMMARY, SOURCE_NAME, "
                    "URL, PUBLISHED_AT) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    rows
                )
                conn.commit()
                uploaded += len(rows)

        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"\nError {f.stem}: {e}")

    cursor.close()
    conn.close()

    print(f"\nDone!")
    print(f"Articles uploaded: {uploaded:,}")
    print(f"Errors: {errors}")
    print(f"\nVerify:")
    print(f"SELECT COUNT(*) FROM NEWS;")
    print(f"SELECT TICKER, HEADLINE, PUBLISHED_AT")
    print(f"FROM NEWS WHERE TICKER='AAPL' LIMIT 3;")


if __name__ == '__main__':
    main()