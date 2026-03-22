"""
Execute alter_fundamentals.sql against Snowflake (uses .env).
Run from repo: python backend/scripts/setup/run_alter_fundamentals.py
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv
import snowflake.connector

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")

SQL_PATH = Path(__file__).resolve().parent / "alter_fundamentals.sql"


def _statements_from_sql(text: str) -> list[str]:
    out: list[str] = []
    for part in text.split(";"):
        lines = [
            ln
            for ln in part.splitlines()
            if ln.strip() and not ln.strip().startswith("--")
        ]
        if not lines:
            continue
        stmt = "\n".join(lines).strip()
        if stmt:
            out.append(stmt)
    return out


def main() -> None:
    text = SQL_PATH.read_text(encoding="utf-8")
    stmts = _statements_from_sql(text)
    conn = snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )
    cur = conn.cursor()
    for stmt in stmts:
        preview = re.sub(r"\s+", " ", stmt)[:100]
        print(f"EXEC: {preview}...")
        cur.execute(stmt)
    conn.commit()
    cur.close()
    conn.close()
    print("OK: alter_fundamentals.sql applied.")


if __name__ == "__main__":
    main()
