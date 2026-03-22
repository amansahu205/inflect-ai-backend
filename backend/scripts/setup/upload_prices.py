"""
Fast price upload using executemany per file
Batch of entire file at once
"""

import pandas as pd
import snowflake.connector
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
import os
import warnings
warnings.filterwarnings('ignore')

load_dotenv(Path(
    'D:/MS/Hackathon/HOOHACKS-2026/inflect/.env'))

PRICES_DIR = Path(
    'D:/MS/Hackathon/HOOHACKS-2026/inflect/data/prices')


def connect():
    return snowflake.connector.connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    )


def main():
    files = list(PRICES_DIR.glob('*.csv'))
    print(f"Uploading {len(files)} price files...")

    conn = connect()
    cursor = conn.cursor()
    print("Connected!")

    print("Truncating PRICES table...")
    cursor.execute("TRUNCATE TABLE PRICES")
    conn.commit()

    uploaded = 0
    file_errors = 0

    for f in tqdm(files):
        try:
            ticker = f.stem.upper()
            df = pd.read_csv(f)

            # Fix timezone dates
            df['Date'] = pd.to_datetime(
                df['Date'], utc=True
            ).dt.date

            # Build all rows for this file
            rows = []
            for _, row in df.iterrows():
                try:
                    rows.append((
                        ticker,
                        row['Date'],
                        float(row.get('Open', 0) or 0),
                        float(row.get('High', 0) or 0),
                        float(row.get('Low', 0) or 0),
                        float(row.get('Close', 0) or 0),
                        int(row.get('Volume', 0) or 0)
                    ))
                except Exception:
                    continue

            if not rows:
                continue

            # Insert ALL rows for this file at once
            cursor.executemany(
                "INSERT INTO PRICES "
                "(TICKER, TRADE_DATE, "
                "OPEN_PRICE, HIGH_PRICE, "
                "LOW_PRICE, CLOSE_PRICE, "
                "VOLUME) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                rows
            )
            conn.commit()
            uploaded += len(rows)

        except Exception as e:
            file_errors += 1
            if file_errors <= 3:
                print(f"\nError {f.stem}: {e}")

    cursor.close()
    conn.close()

    print(f"\nDone!")
    print(f"Rows uploaded: {uploaded:,}")
    print(f"File errors:   {file_errors}")
    print(f"\nVerify in Snowflake:")
    print(f"SELECT COUNT(*) FROM PRICES;")


if __name__ == '__main__':
    main()