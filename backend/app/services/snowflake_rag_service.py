"""
SEC chunk retrieval from Snowflake (keyword / ILIKE fallback).

Full VECTOR_COSINE_SIMILARITY search needs a 1024-dim query embedding (BGE-M3).
When embeddings are not computed at request time, we match on ticker + text
keywords so the LLM still receives real filing excerpts when Snowflake is up.
"""

from __future__ import annotations

import os
import re
from typing import Any


def _connect():
    import snowflake.connector

    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
    )


def snowflake_configured() -> bool:
    return bool(
        os.getenv("SNOWFLAKE_ACCOUNT")
        and os.getenv("SNOWFLAKE_USER")
        and os.getenv("SNOWFLAKE_PASSWORD")
    )


def _query_keywords(text: str, max_terms: int = 8) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", text)
    seen: set[str] = set()
    out: list[str] = []
    for w in words:
        lw = w.lower()
        if lw in seen or lw in {
            "the", "and", "for", "what", "how", "why", "when", "from", "with",
            "this", "that", "their", "they", "have", "been", "were", "will",
        }:
            continue
        seen.add(lw)
        out.append(w)
        if len(out) >= max_terms:
            break
    return out


def search_sec_chunks(
    ticker: str | None,
    user_query: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Return rows: chunk_id, ticker, form_type, filing_date, section, chunk_text.
    """
    if not snowflake_configured():
        return []

    terms = _query_keywords(user_query)
    if not terms:
        terms = [user_query.strip()[:40] or "revenue"]

    conn = _connect()
    try:
        cur = conn.cursor()
        ilike_clauses = " OR ".join(["CHUNK_TEXT ILIKE %s"] * len(terms))
        like_params = [f"%{t}%" for t in terms]

        if ticker:
            sql = f"""
                SELECT CHUNK_ID, TICKER, FORM_TYPE, FILING_DATE, SECTION, CHUNK_TEXT
                FROM SEC_EMBEDDINGS
                WHERE TICKER = %s AND ({ilike_clauses})
                LIMIT %s
            """
            cur.execute(sql, (ticker.upper(), *like_params, limit))
        else:
            sql = f"""
                SELECT CHUNK_ID, TICKER, FORM_TYPE, FILING_DATE, SECTION, CHUNK_TEXT
                FROM SEC_EMBEDDINGS
                WHERE {ilike_clauses}
                LIMIT %s
            """
            cur.execute(sql, (*like_params, limit))

        cols = [c[0].lower() for c in cur.description]
        rows = []
        for row in cur.fetchall():
            rows.append(dict(zip(cols, row)))
        return rows
    except Exception:
        return []
    finally:
        conn.close()
