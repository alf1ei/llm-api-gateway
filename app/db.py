import sqlite3
from pathlib import Path
from .config import get_settings

def _db_path():
    url = get_settings().database_url
    if not url.startswith("sqlite:///"):
        raise ValueError("This starter currently supports SQLite only.")
    return url.removeprefix("sqlite:///")

def connect():
    path = Path(_db_path())
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS usage (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          provider TEXT NOT NULL, model TEXT NOT NULL,
          status_code INTEGER NOT NULL,
          prompt_tokens INTEGER NOT NULL DEFAULT 0,
          completion_tokens INTEGER NOT NULL DEFAULT 0,
          total_tokens INTEGER NOT NULL DEFAULT 0,
          latency_ms INTEGER NOT NULL DEFAULT 0)""")

def log_usage(provider, model, status_code, usage=None, latency_ms=0):
    usage = usage or {}
    with connect() as conn:
        conn.execute("""INSERT INTO usage(provider,model,status_code,prompt_tokens,
          completion_tokens,total_tokens,latency_ms) VALUES(?,?,?,?,?,?,?)""",
          (provider, model, status_code, usage.get("prompt_tokens", 0),
           usage.get("completion_tokens", 0), usage.get("total_tokens", 0), latency_ms))

def recent_usage(limit=100):
    with connect() as conn:
        rows = conn.execute("SELECT * FROM usage ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]
