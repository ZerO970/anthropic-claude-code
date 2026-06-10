import sqlite3
from contextlib import contextmanager

DB_PATH = "recruitment.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE,
                name TEXT,
                nationality TEXT,
                experience TEXT,
                score INTEGER,
                total INTEGER,
                answers TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)


def upsert_candidate(tg_id, name, nationality, experience, score, total, answers_json):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO candidates (tg_id, name, nationality, experience, score, total, answers)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tg_id) DO UPDATE SET
                name=excluded.name,
                nationality=excluded.nationality,
                experience=excluded.experience,
                score=excluded.score,
                total=excluded.total,
                answers=excluded.answers,
                created_at=CURRENT_TIMESTAMP
        """, (tg_id, name, nationality, experience, score, total, answers_json))


def get_all_candidates():
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM candidates ORDER BY score DESC, created_at DESC"
        ).fetchall()
