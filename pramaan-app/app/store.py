"""SQLite persistence and tamper-evident audit-chain helpers."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = "/tmp/pramaan.sqlite3" if os.getenv("VERCEL") else str(ROOT / "runtime" / "pramaan.sqlite3")
DB_PATH = Path(os.getenv("PRAMAAN_DB", DEFAULT_DB))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    finally:
        db.close()


def init_db() -> None:
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              username TEXT PRIMARY KEY, display_name TEXT NOT NULL,
              role TEXT NOT NULL, password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS institutions (
              id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL,
              campus_lat REAL, campus_lon REAL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS applications (
              id INTEGER PRIMARY KEY AUTOINCREMENT, institution_id INTEGER,
              institution_name TEXT NOT NULL, app_type TEXT NOT NULL,
              cycle TEXT NOT NULL, score INTEGER NOT NULL, band TEXT NOT NULL,
              report_json TEXT NOT NULL, created_at TEXT NOT NULL,
              decision TEXT, decision_by TEXT, decision_at TEXT,
              FOREIGN KEY(institution_id) REFERENCES institutions(id)
            );
            CREATE TABLE IF NOT EXISTS documents (
              id INTEGER PRIMARY KEY AUTOINCREMENT, application_id INTEGER NOT NULL,
              name TEXT NOT NULL, kind TEXT NOT NULL, filename TEXT,
              path TEXT, metadata_json TEXT NOT NULL,
              FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS flags (
              id INTEGER PRIMARY KEY AUTOINCREMENT, application_id INTEGER NOT NULL,
              code TEXT NOT NULL, engine TEXT NOT NULL, severity TEXT NOT NULL,
              title TEXT NOT NULL, message TEXT NOT NULL, evidence_json TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'Open', resolved_by TEXT, resolved_at TEXT,
              FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS claims (
              id INTEGER PRIMARY KEY AUTOINCREMENT, application_id INTEGER NOT NULL,
              key TEXT NOT NULL, value_json TEXT NOT NULL, confidence REAL NOT NULL,
              source_document TEXT, page INTEGER, region_json TEXT,
              FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS audits (
              id INTEGER PRIMARY KEY AUTOINCREMENT, application_id INTEGER,
              actor TEXT NOT NULL, action TEXT NOT NULL, detail_json TEXT NOT NULL,
              created_at TEXT NOT NULL, previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL,
              FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS rules (
              id TEXT PRIMARY KEY, edition TEXT NOT NULL, title TEXT NOT NULL,
              applies_to TEXT NOT NULL, required_evidence TEXT NOT NULL,
              threshold TEXT, severity TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1
            );
            """
        )


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def append_audit(actor: str, action: str, detail: Dict[str, Any], application_id: Optional[int] = None) -> Dict[str, Any]:
    with connect() as db:
        previous = db.execute("SELECT entry_hash FROM audits ORDER BY id DESC LIMIT 1").fetchone()
        previous_hash = previous[0] if previous else "GENESIS"
        created_at = utc_now()
        payload = {"application_id": application_id, "actor": actor, "action": action,
                   "detail": detail, "created_at": created_at, "previous_hash": previous_hash}
        entry_hash = hashlib.sha256(_json(payload).encode()).hexdigest()
        cur = db.execute(
            "INSERT INTO audits(application_id,actor,action,detail_json,created_at,previous_hash,entry_hash) VALUES(?,?,?,?,?,?,?)",
            (application_id, actor, action, _json(detail), created_at, previous_hash, entry_hash),
        )
        return {"id": cur.lastrowid, **payload, "entry_hash": entry_hash}


def verify_audit() -> Dict[str, Any]:
    with connect() as db:
        rows = db.execute("SELECT * FROM audits ORDER BY id").fetchall()
    previous = "GENESIS"
    for row in rows:
        detail = json.loads(row["detail_json"])
        payload = {"application_id": row["application_id"], "actor": row["actor"],
                   "action": row["action"], "detail": detail, "created_at": row["created_at"],
                   "previous_hash": row["previous_hash"]}
        expected = hashlib.sha256(_json(payload).encode()).hexdigest()
        if row["previous_hash"] != previous or row["entry_hash"] != expected:
            return {"valid": False, "entries": len(rows), "bad_entry": row["id"]}
        previous = row["entry_hash"]
    return {"valid": True, "entries": len(rows), "bad_entry": None}


def rows(sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    with connect() as db:
        return db.execute(sql, tuple(params)).fetchall()


def one(sql: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
    with connect() as db:
        return db.execute(sql, tuple(params)).fetchone()
