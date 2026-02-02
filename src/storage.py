"""SQLite storage for daily snapshots (GBP totals)."""
import os
import sqlite3
from pathlib import Path


def _db_path(config_snapshot_db_path: str | None, default_dir: str | None = None) -> str:
    if config_snapshot_db_path and config_snapshot_db_path.strip():
        return config_snapshot_db_path.strip()
    if default_dir is None:
        default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    Path(default_dir).mkdir(parents=True, exist_ok=True)
    return os.path.join(default_dir, "snapshots.db")


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_snapshots (
            day TEXT PRIMARY KEY,
            gbp_total_reviews INTEGER,
            gbp_avg_rating REAL
        )
        """
    )
    conn.commit()


def get_snapshot(db_path: str | None, day: str) -> dict | None:
    """Return row for day if exists (gbp_total_reviews, gbp_avg_rating), else None."""
    path = _db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        _ensure_schema(conn)
        row = conn.execute(
            "SELECT gbp_total_reviews, gbp_avg_rating FROM daily_snapshots WHERE day = ?",
            (day,),
        ).fetchone()
        if row is None:
            return None
        return {"gbp_total_reviews": row[0], "gbp_avg_rating": row[1]}
    finally:
        conn.close()


def upsert_snapshot(db_path: str | None, day: str, gbp_total_reviews: int, gbp_avg_rating: float | None) -> None:
    """Insert or replace row for day with given GBP fields."""
    path = _db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO daily_snapshots (day, gbp_total_reviews, gbp_avg_rating)
            VALUES (?, ?, ?)
            """,
            (day, gbp_total_reviews, gbp_avg_rating),
        )
        conn.commit()
    finally:
        conn.close()
