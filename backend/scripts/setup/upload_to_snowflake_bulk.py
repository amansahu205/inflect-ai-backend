"""
Bulk upload embeddings_1024.jsonl to Snowflake
Strategy:
  1. Convert .jsonl → CSV chunks (embedding stored as JSON array string)
  2. PUT each CSV chunk to Snowflake internal stage
  3. COPY INTO staging table (EMBEDDING as ARRAY/VARIANT)
  4. INSERT INTO SEC_EMBEDDINGS with EMBEDDING::VECTOR(FLOAT, 1024) cast
  5. Drop staging table and stage

~30 min for 488K rows vs ~78 hours row-by-row.
"""

import csv
import json
import os
import tempfile
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv
from tqdm import tqdm

# ── Load environment ──────────────────────────────────────────
load_dotenv(Path('D:/MS/Hackathon/HOOHACKS-2026/inflect/.env'))

# ── Config ────────────────────────────────────────────────────
EMBEDDINGS_FILE = (
    'D:/MS/Hackathon/HOOHACKS-2026/inflect/'
    'data/sec_filings/processed/'
    'embeddings_1024.jsonl'
)

# How many rows per CSV chunk file.
# 50K rows × ~6KB per row ≈ 300MB per chunk — fits comfortably in memory
# and keeps each PUT/COPY operation fast.
CHUNK_SIZE = 50_000

STAGING_TABLE = 'SEC_EMBEDDINGS_STAGING'
STAGE_NAME    = 'SEC_EMBEDDINGS_STAGE'


# ── Helpers ───────────────────────────────────────────────────
def count_lines(filepath: str) -> int:
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        return sum(1 for _ in f)


def setup(cursor) -> None:
    """Create internal stage and staging table."""

    cursor.execute(f"CREATE OR REPLACE STAGE {STAGE_NAME}")
    print(f"  Stage '{STAGE_NAME}' created.")

    cursor.execute(f"""
        CREATE OR REPLACE TABLE {STAGING_TABLE} (
            CHUNK_ID    VARCHAR(200),
            TICKER      VARCHAR(10),
            FORM_TYPE   VARCHAR(10),
            FILING_DATE VARCHAR(20),
            SECTION     VARCHAR(200),
            TOKEN_COUNT NUMBER,
            CHUNK_TEXT  VARCHAR(4000),
            EMBEDDING   VARIANT
        )
    """)
    print(f"  Staging table '{STAGING_TABLE}' created.")


def teardown(cursor) -> None:
    """Drop staging table and stage."""
    cursor.execute(f"DROP TABLE IF EXISTS {STAGING_TABLE}")
    cursor.execute(f"DROP STAGE IF EXISTS {STAGE_NAME}")
    print("  Staging table and stage dropped.")


def write_chunk_csv(rows: list, tmp_path: str) -> None:
    """Write a list of row dicts to a CSV file."""
    with open(tmp_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        for row in rows:
            writer.writerow([
                str(row.get('chunk_id',    ''))[:200],
                str(row.get('ticker',      ''))[:10],
                str(row.get('form_type',   ''))[:10],
                str(row.get('filing_date', ''))[:20],
                str(row.get('section',     ''))[:200],
                int(row.get('token_count', 0)),
                str(row.get('text',        ''))[:4000],
                # Embedding as a compact JSON array string.
                # Snowflake will parse this as VARIANT, then we cast to VECTOR.
                json.dumps(row['embedding']),
            ])


def put_and_copy(cursor, tmp_path: str, chunk_idx: int) -> int:
    """
    PUT a CSV file to the internal stage, then COPY INTO staging table.
    Returns the number of rows loaded.
    """
    # PUT — uploads the local file to the internal stage
    # 'file://' prefix required; forward slashes required on all platforms
    file_uri = 'file://' + tmp_path.replace('\\', '/')
    cursor.execute(
        f"PUT {file_uri} @{STAGE_NAME} "
        f"AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
    )

    # COPY INTO staging table
    # FIELD_OPTIONALLY_ENCLOSED_BY handles quoted fields (including
    # the JSON array strings in the embedding column)
    staged_filename = Path(tmp_path).name + '.gz'
    cursor.execute(f"""
        COPY INTO {STAGING_TABLE}
        FROM @{STAGE_NAME}/{staged_filename}
        FILE_FORMAT = (
            TYPE                        = 'CSV'
            FIELD_OPTIONALLY_ENCLOSED_BY = '"'
            NULL_IF                      = ('NULL', 'null', '')
            EMPTY_FIELD_AS_NULL          = TRUE
        )
        ON_ERROR = 'CONTINUE'
    """)

    # fetchall() returns one row per loaded file with row counts
    results = cursor.fetchall()
    rows_loaded = sum(r[3] for r in results) if results else 0
    return rows_loaded


def flush_staging_to_final(cursor) -> int:
    """
    INSERT INTO SEC_EMBEDDINGS from staging table,
    casting EMBEDDING VARIANT → VECTOR(FLOAT, 1024).
    Returns number of rows inserted.
    """
    cursor.execute(f"""
        INSERT INTO SEC_EMBEDDINGS
        SELECT
            CHUNK_ID,
            TICKER,
            FORM_TYPE,
            FILING_DATE,
            SECTION,
            TOKEN_COUNT,
            CHUNK_TEXT,
            EMBEDDING::VECTOR(FLOAT, 1024)
        FROM {STAGING_TABLE}
    """)
    # Snowflake reports rows inserted via the query result for INSERT ... SELECT
    result = cursor.fetchone()
    return result[0] if result else 0


def truncate_staging(cursor) -> None:
    cursor.execute(f"TRUNCATE TABLE {STAGING_TABLE}")


# ── Main ──────────────────────────────────────────────────────
def main():
    print("Connecting to Snowflake...")
    conn = snowflake.connector.connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA'),
    )
    cursor = conn.cursor()
    print("Connected!\n")

    # Count total
    print("Counting embeddings...")
    total = count_lines(EMBEDDINGS_FILE)
    print(f"Total embeddings: {total:,}\n")

    # Setup stage + staging table
    print("Setting up stage and staging table...")
    setup(cursor)
    print()

    total_staged  = 0
    total_inserted = 0
    total_errors   = 0
    chunk_idx      = 0
    buffer         = []

    print(f"Reading {EMBEDDINGS_FILE}...")
    with open(EMBEDDINGS_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        pbar = tqdm(f, total=total, unit='rows', desc='Processing')

        for line in pbar:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                buffer.append(record)
            except json.JSONDecodeError:
                total_errors += 1
                continue

            # When buffer reaches CHUNK_SIZE, flush to Snowflake
            if len(buffer) >= CHUNK_SIZE:
                chunk_idx += 1
                pbar.set_description(f'Uploading chunk {chunk_idx}')

                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix=f'_chunk{chunk_idx}.csv',
                    delete=False,
                    encoding='utf-8'
                ) as tmp:
                    tmp_path = tmp.name

                try:
                    write_chunk_csv(buffer, tmp_path)
                    rows_staged = put_and_copy(cursor, tmp_path, chunk_idx)
                    total_staged += rows_staged

                    # INSERT staged rows into final table, then clear staging
                    rows_inserted = flush_staging_to_final(cursor)
                    total_inserted += rows_inserted
                    truncate_staging(cursor)
                    conn.commit()

                    pbar.set_postfix({
                        'inserted': f'{total_inserted:,}',
                        'errors':   total_errors,
                    })
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

                buffer = []
                pbar.set_description('Processing')

    # Flush remaining rows in buffer
    if buffer:
        chunk_idx += 1
        print(f"\nFlushing final chunk ({len(buffer):,} rows)...")

        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=f'_chunk{chunk_idx}.csv',
            delete=False,
            encoding='utf-8'
        ) as tmp:
            tmp_path = tmp.name

        try:
            write_chunk_csv(buffer, tmp_path)
            rows_staged = put_and_copy(cursor, tmp_path, chunk_idx)
            total_staged += rows_staged

            rows_inserted = flush_staging_to_final(cursor)
            total_inserted += rows_inserted
            truncate_staging(cursor)
            conn.commit()
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    # Cleanup
    print("\nCleaning up staging resources...")
    teardown(cursor)
    conn.commit()

    cursor.close()
    conn.close()

    # Report
    print(f"\n{'='*50}")
    print(f"UPLOAD COMPLETE!")
    print(f"{'='*50}")
    print(f"Total in file:   {total:,}")
    print(f"Rows inserted:   {total_inserted:,}")
    print(f"JSON errors:     {total_errors:,}")
    print(f"{'='*50}")
    print(f"Verify in Snowflake:")
    print(f"  SELECT COUNT(*) FROM SEC_EMBEDDINGS;")


if __name__ == '__main__':
    main()