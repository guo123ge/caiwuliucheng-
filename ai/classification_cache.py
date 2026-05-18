import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DB_PATH = Path(__file__).parent.parent / "data" / "classification_cache.db"


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS classification_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text_hash TEXT NOT NULL UNIQUE,
            original_text TEXT NOT NULL,
            category TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            reason TEXT DEFAULT '',
            source TEXT DEFAULT 'llm',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            hit_count INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_text_hash ON classification_cache(text_hash)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_category ON classification_cache(category)
    """)
    conn.commit()
    return conn


def _hash_text(text: str) -> str:
    normalized = text.strip().lower().replace(" ", "").replace("\n", "")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def lookup(text: str) -> Optional[Dict]:
    text_hash = _hash_text(text)
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT category, confidence, reason, source FROM classification_cache WHERE text_hash = ?",
            (text_hash,),
        )
        row = cursor.fetchone()
        if row:
            conn.execute(
                "UPDATE classification_cache SET hit_count = hit_count + 1, updated_at = ? WHERE text_hash = ?",
                (time.time(), text_hash),
            )
            conn.commit()
            return {
                "category": row[0],
                "confidence": row[1],
                "reason": row[2],
                "source": row[3],
            }
        return None
    finally:
        conn.close()


def store(
    text: str,
    category: str,
    confidence: float = 1.0,
    reason: str = "",
    source: str = "llm",
):
    text_hash = _hash_text(text)
    now = time.time()
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO classification_cache
               (text_hash, original_text, category, confidence, reason, source, created_at, updated_at, hit_count)
               VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM classification_cache WHERE text_hash = ?), ?), ?, 1)""",
            (text_hash, text, category, confidence, reason, source, text_hash, now, now),
        )
        conn.commit()
    finally:
        conn.close()


def store_batch(items: List[Tuple[str, str, float, str]]):
    now = time.time()
    conn = _get_connection()
    try:
        for text, category, confidence, reason in items:
            text_hash = _hash_text(text)
            conn.execute(
                """INSERT OR REPLACE INTO classification_cache
                   (text_hash, original_text, category, confidence, reason, source, created_at, updated_at, hit_count)
                   VALUES (?, ?, ?, ?, ?, 'llm', COALESCE((SELECT created_at FROM classification_cache WHERE text_hash = ?), ?), ?, 1)""",
                (text_hash, text, category, confidence, reason, text_hash, now, now),
            )
        conn.commit()
    finally:
        conn.close()


def get_stats() -> Dict:
    conn = _get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM classification_cache").fetchone()[0]
        by_category = {}
        for row in conn.execute(
            "SELECT category, COUNT(*) FROM classification_cache GROUP BY category"
        ):
            by_category[row[0]] = row[1]
        total_hits = conn.execute(
            "SELECT COALESCE(SUM(hit_count), 0) FROM classification_cache"
        ).fetchone()[0]
        return {
            "total_entries": total,
            "by_category": by_category,
            "total_hits": total_hits,
        }
    finally:
        conn.close()


def clear():
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM classification_cache")
        conn.commit()
    finally:
        conn.close()
