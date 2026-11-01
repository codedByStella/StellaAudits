"""
db.py
Local SQLite lead-tracking log. Every audit run (single or batch, success or
failure) gets a row here so the tool keeps a history instead of being a
one-off script: what's been scanned, its grade, its current status, and what
happened.

Single-file SQLite, zero setup, lives at stella_leads.db in the project
root next to config.json.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "stella_leads.db")

VALID_STATUSES = ["New", "Contacted", "Responded", "Client", "Not Interested", "Failed"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS audits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    domain TEXT NOT NULL,
    audited_at TEXT NOT NULL,
    score INTEGER,
    grade TEXT,
    total_findings INTEGER,
    pdf_filename TEXT,
    email_draft_filename TEXT,
    status TEXT NOT NULL DEFAULT 'New',
    notes TEXT DEFAULT '',
    error TEXT DEFAULT '',
    findings_snapshot TEXT DEFAULT ''
);
"""

# Columns added after the initial release -- applied with ALTER TABLE against
# any pre-existing database so upgrading the tool never loses history.
MIGRATIONS = [
    "ALTER TABLE audits ADD COLUMN findings_snapshot TEXT DEFAULT ''",
]


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as conn:
        conn.execute(SCHEMA)
        for migration in MIGRATIONS:
            try:
                conn.execute(migration)
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    raise


def _domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc or url
    except Exception:
        return url


# Public alias -- app.py needs this to look up prior audits for a domain
# before inserting a new one.
domain_of = _domain_of


def _findings_to_snapshot(findings) -> str:
    """Compact JSON list of {check_key, severity, title} for before/after diffing."""
    return json.dumps([
        {"check_key": f.check_key, "severity": f.severity, "title": f.title}
        for f in findings
    ])


def insert_success(url, score, grade, total_findings, pdf_filename, email_draft_filename,
                    findings=None) -> int:
    snapshot = _findings_to_snapshot(findings) if findings is not None else ""
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO audits (url, domain, audited_at, score, grade, total_findings, "
            "pdf_filename, email_draft_filename, status, findings_snapshot) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'New', ?)",
            (url, _domain_of(url), datetime.now(timezone.utc).isoformat(),
             score, grade, total_findings, pdf_filename, email_draft_filename, snapshot),
        )
        return cur.lastrowid


def get_latest_prior(domain: str, exclude_id: int = None):
    """Most recent successful (scored) prior audit for this domain, if any."""
    with _conn() as conn:
        if exclude_id is not None:
            row = conn.execute(
                "SELECT * FROM audits WHERE domain = ? AND score IS NOT NULL AND id != ? "
                "ORDER BY audited_at DESC LIMIT 1",
                (domain, exclude_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM audits WHERE domain = ? AND score IS NOT NULL "
                "ORDER BY audited_at DESC LIMIT 1",
                (domain,),
            ).fetchone()
        return dict(row) if row else None


def diff_findings(prior_snapshot_json: str, current_findings):
    """Compare a prior findings snapshot (JSON string from the DB) against the
    current run's Finding objects. Returns {resolved, persisting, new} lists
    of {check_key, severity, title}, matched by the stable check_key."""
    try:
        prior = json.loads(prior_snapshot_json) if prior_snapshot_json else []
    except (json.JSONDecodeError, TypeError):
        prior = []

    prior_keys = {p["check_key"]: p for p in prior}
    current_keys = {f.check_key: f for f in current_findings}

    resolved = [p for key, p in prior_keys.items() if key not in current_keys]
    new = [
        {"check_key": f.check_key, "severity": f.severity, "title": f.title}
        for key, f in current_keys.items() if key not in prior_keys
    ]
    persisting = [
        {"check_key": f.check_key, "severity": f.severity, "title": f.title}
        for key, f in current_keys.items() if key in prior_keys
    ]
    return {"resolved": resolved, "persisting": persisting, "new": new}


def insert_failure(url, error) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO audits (url, domain, audited_at, status, error) "
            "VALUES (?, ?, ?, 'Failed', ?)",
            (url, _domain_of(url), datetime.now(timezone.utc).isoformat(), str(error)),
        )
        return cur.lastrowid


def list_audits(status=None):
    with _conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM audits WHERE status = ? ORDER BY audited_at DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM audits ORDER BY audited_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_audit(audit_id):
    with _conn() as conn:
        row = conn.execute("SELECT * FROM audits WHERE id = ?", (audit_id,)).fetchone()
        return dict(row) if row else None


def update_status(audit_id, status, notes=None):
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of {VALID_STATUSES}.")
    with _conn() as conn:
        if notes is not None:
            conn.execute("UPDATE audits SET status = ?, notes = ? WHERE id = ?",
                         (status, notes, audit_id))
        else:
            conn.execute("UPDATE audits SET status = ? WHERE id = ?", (status, audit_id))


def summary_counts():
    with _conn() as conn:
        rows = conn.execute("SELECT status, COUNT(*) as n FROM audits GROUP BY status").fetchall()
        return {r["status"]: r["n"] for r in rows}


init_db()
