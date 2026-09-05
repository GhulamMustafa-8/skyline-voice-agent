"""
Phase 5: Data & CRM Layer.

A lightweight SQLite-backed store for:
  - leads: one row per phone number, holds latest known info + score
  - call_logs: one row per call attempt, full transcript + outcome
  - do_not_call: permanent opt-outs (checked before every outbound dial)

SQLite (not Postgres) is the right choice for an MVP/portfolio project —
zero setup, single file, easy to inspect/demo. Swapping to Postgres later is
a schema-compatible change if this needs to scale to real call volume.
"""

import sqlite3
import json
from datetime import datetime, timezone
from contextlib import contextmanager


DB_PATH = "crm.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    phone_number TEXT PRIMARY KEY,
    name TEXT,
    buy_or_rent TEXT,
    budget TEXT,
    location TEXT,
    timeline TEXT,
    score TEXT,
    last_outcome TEXT,
    last_contacted_at TEXT,
    do_not_call INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS call_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_sid TEXT,
    phone_number TEXT,
    started_at TEXT,
    ended_at TEXT,
    final_state TEXT,
    score TEXT,
    outcome TEXT,
    objection_count INTEGER,
    transcript_json TEXT,
    FOREIGN KEY (phone_number) REFERENCES leads (phone_number)
);
"""


@contextmanager
def get_conn(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str = DB_PATH):
    with get_conn(db_path) as conn:
        conn.executescript(SCHEMA)


def upsert_lead(phone_number: str, lead_info, db_path: str = DB_PATH):
    """lead_info is a LeadInfo instance (from state_machine.py) or dict-like."""
    with get_conn(db_path) as conn:
        conn.execute("""
            INSERT INTO leads (phone_number, name, buy_or_rent, budget, location,
                                timeline, score, last_outcome, last_contacted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(phone_number) DO UPDATE SET
                name=excluded.name,
                buy_or_rent=COALESCE(NULLIF(excluded.buy_or_rent, ''), leads.buy_or_rent),
                budget=COALESCE(NULLIF(excluded.budget, ''), leads.budget),
                location=COALESCE(NULLIF(excluded.location, ''), leads.location),
                timeline=COALESCE(NULLIF(excluded.timeline, ''), leads.timeline),
                score=excluded.score,
                last_outcome=excluded.last_outcome,
                last_contacted_at=excluded.last_contacted_at
        """, (
            phone_number, getattr(lead_info, "name", ""), lead_info.buy_or_rent,
            lead_info.budget, lead_info.location, lead_info.timeline,
            lead_info.score, lead_info.outcome, datetime.now(timezone.utc).isoformat()
        ))


def log_call(call_sid: str, phone_number: str, started_at: str, ended_at: str,
             final_state: str, score: str, outcome: str, objection_count: int,
             transcript: list, db_path: str = DB_PATH):
    with get_conn(db_path) as conn:
        conn.execute("""
            INSERT INTO call_logs (call_sid, phone_number, started_at, ended_at,
                                    final_state, score, outcome, objection_count, transcript_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (call_sid, phone_number, started_at, ended_at, final_state, score,
              outcome, objection_count, json.dumps(transcript)))


def is_do_not_call(phone_number: str, db_path: str = DB_PATH) -> bool:
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT do_not_call FROM leads WHERE phone_number = ?", (phone_number,)
        ).fetchone()
        return bool(row and row["do_not_call"])


def mark_do_not_call(phone_number: str, db_path: str = DB_PATH):
    with get_conn(db_path) as conn:
        conn.execute("""
            INSERT INTO leads (phone_number, do_not_call) VALUES (?, 1)
            ON CONFLICT(phone_number) DO UPDATE SET do_not_call = 1
        """, (phone_number,))


def get_leads_by_score(score: str, db_path: str = DB_PATH):
    with get_conn(db_path) as conn:
        rows = conn.execute("SELECT * FROM leads WHERE score = ?", (score,)).fetchall()
        return [dict(r) for r in rows]


def get_dashboard_stats(db_path: str = DB_PATH) -> dict:
    """Aggregate stats for the Phase 7 analytics dashboard."""
    with get_conn(db_path) as conn:
        total_calls = conn.execute("SELECT COUNT(*) c FROM call_logs").fetchone()["c"]
        by_outcome = conn.execute(
            "SELECT outcome, COUNT(*) c FROM call_logs GROUP BY outcome"
        ).fetchall()
        by_score = conn.execute(
            "SELECT score, COUNT(*) c FROM leads WHERE score != '' GROUP BY score"
        ).fetchall()
        avg_objections = conn.execute(
            "SELECT AVG(objection_count) a FROM call_logs"
        ).fetchone()["a"]

        return {
            "total_calls": total_calls,
            "by_outcome": {r["outcome"]: r["c"] for r in by_outcome},
            "by_score": {r["score"]: r["c"] for r in by_score},
            "avg_objections_per_call": round(avg_objections or 0, 2),
        }
