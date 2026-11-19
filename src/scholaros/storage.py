"""SQLite storage with atomic migration and optional Fernet encryption of student data."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from cryptography.fernet import Fernet

from .records import StudentProfile

SCHEMA_VERSION = 1


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path))
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    migrate(db)
    return db


def migrate(db: sqlite3.Connection) -> None:
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY
        )""")
        current = db.execute("SELECT max(version) FROM schema_migrations").fetchone()[0]
        if current is None:
            db.execute("""CREATE TABLE IF NOT EXISTS student_vault (
                student_id TEXT PRIMARY KEY,
                payload BLOB NOT NULL,
                encrypted INTEGER NOT NULL CHECK (encrypted = 0 OR encrypted = 1)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS student_events (
                event_id TEXT PRIMARY KEY,
                student_id TEXT NOT NULL REFERENCES student_vault(student_id) ON DELETE CASCADE,
                payload BLOB NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS public_snapshots (
                content_hash TEXT PRIMARY KEY,
                source_url TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                content_text TEXT NOT NULL
            )""")
            db.execute("INSERT INTO schema_migrations(version) VALUES (?)", (SCHEMA_VERSION,))


def _cipher() -> Fernet | None:
    key = os.environ.get("SCHOLAROS_FERNET_KEY")
    return Fernet(key.encode("ascii")) if key else None


def save_student(db: sqlite3.Connection, student: StudentProfile) -> None:
    if not student.consent_to_store:
        raise PermissionError("Student consent_to_store is required")
    cipher = _cipher()
    # Refuse plaintext student vault by default. Explicit local-only override for tests.
    if cipher is None and os.environ.get("SCHOLAROS_ALLOW_UNENCRYPTED_LOCAL") != "1":
        raise RuntimeError("Set SCHOLAROS_FERNET_KEY before saving student PII")
    raw = student.model_dump_json().encode("utf-8")
    payload = cipher.encrypt(raw) if cipher else raw
    with db:
        db.execute("""INSERT INTO student_vault(student_id, payload, encrypted)
            VALUES (?, ?, ?) ON CONFLICT(student_id) DO UPDATE
            SET payload = excluded.payload, encrypted = excluded.encrypted""",
            (student.student_id, payload, int(cipher is not None)))


def load_student(db: sqlite3.Connection, student_id: str) -> StudentProfile | None:
    row = db.execute(
        "SELECT payload, encrypted FROM student_vault WHERE student_id = ?", (student_id,)
    ).fetchone()
    if row is None:
        return None
    payload: bytes = row[0]
    if row[1]:
        cipher = _cipher()
        if cipher is None:
            raise RuntimeError("Encrypted student vault requires SCHOLAROS_FERNET_KEY")
        payload = cipher.decrypt(payload)
    return StudentProfile.model_validate_json(payload)


def purge_student(db: sqlite3.Connection, student_id: str) -> int:
    """Delete vault and linked student events. WAL may retain prior bytes until checkpoint."""
    with db:
        db.execute("DELETE FROM student_events WHERE student_id = ?", (student_id,))
        deleted = db.execute("DELETE FROM student_vault WHERE student_id = ?", (student_id,))
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    return deleted.rowcount


def export_schemas(path: Path) -> None:
    from .records import all_json_schemas
    path.mkdir(parents=True, exist_ok=True)
    for name, schema in all_json_schemas().items():
        (path / f"{name}.schema.json").write_text(
            json.dumps(schema, indent=2) + "\n", encoding="utf-8",
        )
