"""One short-lived SQLite connection per operation; JSON preserves null values."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connect():
    path = Path(os.environ.get("FINLENS_DB", "data/finlens.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=20)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize():
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY, filename TEXT NOT NULL,
            created_at TEXT NOT NULL, result TEXT NOT NULL)""")


def save(result):
    with connect() as db:
        db.execute("INSERT INTO analyses VALUES (?, ?, ?, ?)", (
            result["id"], result["filename"], result["created_at"],
            json.dumps(result, allow_nan=False)))


def history(limit, offset):
    with connect() as db:
        return [dict(row) for row in db.execute(
            "SELECT id, filename, created_at FROM analyses ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset))]


def get(analysis_id):
    with connect() as db:
        row = db.execute("SELECT result FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        return json.loads(row["result"]) if row else None
