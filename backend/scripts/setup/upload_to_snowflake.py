"""
Upload embeddings_1024.jsonl to Snowflake
Row-by-row insert for VECTOR(FLOAT, 1024) type
Supports resume from checkpoint
"""

import json
import snowflake.connector
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv
import os

# ── Load environment ──────────────────────────────────────────
load_dotenv(Path(
    'D:/MS/Hackathon/HOOHACKS-2026/inflect/.env'))

# ── Config ────────────────────────────────────────────────────
EMBEDDINGS_FILE = (
    'D:/MS/Hackathon/HOOHACKS-2026/inflect/'
    'data/sec_filings/processed/'
    'embeddings_1024.jsonl'
)
CHECKPOINT_FILE = (
    'D:/MS/Hackathon/HOOHACKS-2026/inflect/'
    'data/sec_filings/processed/'
    'snowflake_upload_checkpoint.txt'
)
COMMIT_EVERY = 100  # commit every N rows


# ── Checkpoint helpers ────────────────────────────────────────
def get_checkpoint() -> int:
    p = Path(CHECKPOINT_FILE)
    if p.exists():
        val = p.read_text().strip()
        return int(val) if val else 0
    return 0


def save_checkpoint(n: int):
    Path(CHECKPOINT_FILE).write_text(str(n))


# ── Main ──────────────────────────────────────────────────────
def main():
    # Connect
    print("Connecting to Snowflake...")
    conn = snowflake.connector.connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    )
    cursor = conn.cursor()
    print("Connected to Snowflake!")

    # Count total lines
    print("Counting embeddings...")
    with open(EMBEDDINGS_FILE, 'r',
              encoding='utf-8',
              errors='ignore') as f:
        total = sum(1 for _ in f)
    print(f"Total embeddings: {total:,}")

    # Resume from checkpoint
    start = get_checkpoint()
    if start > 0:
        print(f"Resuming from line: {start:,}")
    else:
        print("Starting fresh upload...")

    # Stats
    uploaded = 0
    errors = 0
    skipped = 0
    current = 0
    since_commit = 0

    # Upload
    with open(EMBEDDINGS_FILE, 'r',
              encoding='utf-8',
              errors='ignore') as f:

        pbar = tqdm(
            f,
            total=total,
            initial=start,
            desc="Uploading to Snowflake",
            unit="rows"
        )

        for line in pbar:
            current += 1

            # Skip already uploaded
            if current <= start:
                skipped += 1
                continue

            try:
                record = json.loads(line)

                # Convert embedding list to
                # Snowflake VECTOR string format
                emb = record['embedding']
                emb_str = (
                    '[' +
                    ','.join(
                        f'{float(x):.6f}'
                        for x in emb
                    ) +
                    ']'
                )

                # Insert row
                cursor.execute(
                    f"INSERT INTO SEC_EMBEDDINGS "
                    f"SELECT %s, %s, %s, %s, %s, %s, %s, "
                    f"{emb_str}::VECTOR(FLOAT, 1024)",
                    (
                        str(record.get('chunk_id', ''))[:200],
                        str(record.get('ticker', ''))[:10],
                        str(record.get('form_type', ''))[:10],
                        str(record.get('filing_date', ''))[:20],
                        str(record.get('section', ''))[:200],
                        int(record.get('token_count', 0)),
                        str(record.get('text', ''))[:4000],
                    )
                )
                uploaded += 1
                since_commit += 1

                # Commit every COMMIT_EVERY rows
                if since_commit >= COMMIT_EVERY:
                    conn.commit()
                    save_checkpoint(current)
                    since_commit = 0
                    pbar.set_postfix({
                        'uploaded': f'{uploaded:,}',
                        'errors':   errors
                    })

            except json.JSONDecodeError:
                errors += 1

            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(
                        f"\nError at line "
                        f"{current}: {e}"
                    )

    # Final commit
    conn.commit()
    save_checkpoint(current)
    cursor.close()
    conn.close()

    # Final report
    print(f"\n{'='*50}")
    print(f"UPLOAD COMPLETE!")
    print(f"{'='*50}")
    print(f"Total lines:  {total:,}")
    print(f"Uploaded:     {uploaded:,}")
    print(f"Errors:       {errors:,}")
    print(f"Skipped:      {skipped:,}")
    print(f"{'='*50}")
    print(f"Verify in Snowflake:")
    print(f"SELECT COUNT(*) FROM SEC_EMBEDDINGS;")


if __name__ == '__main__':
    main()
