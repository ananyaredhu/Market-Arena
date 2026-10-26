"""Short, serialized SQLite transactions; never hold one across network I/O."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
 id TEXT PRIMARY KEY, variants TEXT NOT NULL, approved INTEGER DEFAULT 0,
 created REAL NOT NULL, run_id TEXT, project_id TEXT, kit_source TEXT);
CREATE TABLE IF NOT EXISTS subscribers (
 chat INTEGER PRIMARY KEY, active INTEGER NOT NULL, consent REAL NOT NULL,
 last_command_id INTEGER NOT NULL DEFAULT 0, generation INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS memberships (campaign TEXT, chat INTEGER, PRIMARY KEY(campaign,chat));
CREATE TABLE IF NOT EXISTS consent_log (chat INTEGER, active INTEGER, campaign TEXT, at REAL);
CREATE TABLE IF NOT EXISTS deliveries (
 id TEXT PRIMARY KEY, campaign TEXT, chat INTEGER, variant INTEGER, status TEXT, at REAL,
 message_id INTEGER, retry_at REAL DEFAULT 0, reason TEXT, consent_generation INTEGER,
 UNIQUE(campaign,chat));
CREATE TABLE IF NOT EXISTS updates (id INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS events (delivery TEXT, kind TEXT, at REAL, PRIMARY KEY(delivery,kind));
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value REAL NOT NULL);
"""
# Additive migration: never replace delivery claims or infer legacy provenance.
MIGRATIONS = {
    "campaigns": {"project_id": "TEXT", "kit_source": "TEXT"},
    "subscribers": {"last_command_id": "INTEGER NOT NULL DEFAULT 0", "generation": "INTEGER NOT NULL DEFAULT 0"},
    "deliveries": {"reason": "TEXT", "consent_generation": "INTEGER"},
}


@contextmanager
def database():
    path = Path(os.getenv("TELEGRAM_DB_PATH", "data/telegram.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    try:
        db.execute("BEGIN IMMEDIATE")
        for statement in SCHEMA.split(";"):
            if statement.strip():
                db.execute(statement)
        for table, additions in MIGRATIONS.items():
            columns = {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
            for name, declaration in additions.items():
                if name not in columns:
                    db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
