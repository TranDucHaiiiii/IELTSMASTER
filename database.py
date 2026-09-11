"""
Database manager for IELTS Master Hub.
Supports PostgreSQL (ielts_db) as primary engine with automatic fallback to SQLite (ielts_master.db).
Handles user authentication, test history, writing submissions, vocabulary progress, and study statistics.
"""

import os
import json
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Load configuration from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DB_PATH = os.path.join(os.path.dirname(__file__), "ielts_master.db")
DATABASE_URL = os.environ.get("DATABASE_URL")

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

_pg_warning_logged = False

def get_db_connection():
    """
    Returns a tuple of (connection, is_pg: bool).
    Prioritizes PostgreSQL when DATABASE_URL is configured and reachable.
    Falls back gracefully to SQLite if PostgreSQL connection fails.
    """
    global _pg_warning_logged
    db_url = os.environ.get("DATABASE_URL")

    if PSYCOPG2_AVAILABLE and db_url:
        try:
            conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
            return conn, True
        except Exception as e:
            if not _pg_warning_logged:
                print(f"[!] PostgreSQL connection failed ({e}). Falling back to SQLite: {DB_PATH}")
                _pg_warning_logged = True

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn, False

def get_active_engine():
    """Returns the currently active database engine name ('postgresql' or 'sqlite')."""
    conn, is_pg = get_db_connection()
    conn.close()
    return "postgresql" if is_pg else "sqlite"

def query_db(sql_pg, sql_sq, params=(), one=False, commit=False, return_id=False):
    """
    Helper to execute queries seamlessly across PostgreSQL and SQLite.
    """
    conn, is_pg = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = sql_pg if is_pg else sql_sq
        cursor.execute(sql, params)
        if commit:
            inserted_id = None
            if return_id:
                if is_pg:
                    res = cursor.fetchone()
                    inserted_id = res["id"] if isinstance(res, dict) else res[0]
                else:
                    inserted_id = cursor.lastrowid
            conn.commit()
            return inserted_id if return_id else True

        if one:
            row = cursor.fetchone()
            return dict(row) if row else None

        rows = cursor.fetchall()
        return [dict(r) for r in rows] if rows else []
    finally:
        conn.close()

def init_db():
    """
    Ensures all necessary tables and indexes exist on the active database engine.
    """
    conn, is_pg = get_db_connection()
    cursor = conn.cursor()
    try:
        if is_pg:
            # PostgreSQL Schema Initialization
            schema_file = os.path.join(os.path.dirname(__file__), "schema_postgres.sql")
            if os.path.exists(schema_file):
                with open(schema_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Filter out psql specific directives like \encoding
                    sql_clean = "\n".join(
                        line for line in content.splitlines()
                        if not line.strip().startswith("\\")
                    )
                    cursor.execute(sql_clean)
                    conn.commit()
        else:
            # SQLite Schema Initialization
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    target_band REAL DEFAULT 7.5,
                    avatar TEXT DEFAULT '👨‍🎓',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    test_type TEXT NOT NULL,
                    test_id TEXT NOT NULL,
                    test_title TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    max_score INTEGER NOT NULL,
                    band_score REAL NOT NULL,
                    time_spent_seconds INTEGER DEFAULT 0,
                    answers_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS writing_submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    task_type TEXT NOT NULL,
                    prompt_id TEXT NOT NULL,
                    prompt_title TEXT NOT NULL,
                    essay_text TEXT NOT NULL,
                    word_count INTEGER NOT NULL,
                    estimated_band REAL NOT NULL,
                    evaluation_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS speaking_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    topic_id TEXT NOT NULL,
                    part TEXT NOT NULL,
                    question TEXT NOT NULL,
                    duration_seconds INTEGER DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vocab_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER DEFAULT 1,
                    word_id TEXT NOT NULL,
                    is_mastered INTEGER DEFAULT 0,
                    review_count INTEGER DEFAULT 0,
                    last_reviewed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, word_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cached_vocabulary (
                    word TEXT PRIMARY KEY,
                    phonetic TEXT,
                    audio TEXT,
                    pos TEXT,
                    definition_en TEXT,
                    example_en TEXT,
                    meaning_vi TEXT,
                    ielts_explanation TEXT,
                    ielts_example TEXT,
                    collocations_json TEXT,
                    synonyms_json TEXT,
                    antonyms_json TEXT,
                    band TEXT,
                    topic TEXT,
                    source TEXT DEFAULT 'gemini_dictionary',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Migration check for user_id column in older SQLite tables
            tables_to_check = ['test_history', 'writing_submissions', 'speaking_logs', 'vocab_progress']
            for t in tables_to_check:
                cursor.execute(f"PRAGMA table_info({t})")
                columns = [col['name'] for col in cursor.fetchall()]
                if 'user_id' not in columns:
                    cursor.execute(f"ALTER TABLE {t} ADD COLUMN user_id INTEGER DEFAULT 1")
            conn.commit()
    finally:
        conn.close()

# --- User Management Queries ---
def create_user(username, email, password_hash, target_band=7.5):
    sql_pg = """
        INSERT INTO users (username, email, password_hash, target_band)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """
    sql_sq = """
        INSERT INTO users (username, email, password_hash, target_band)
        VALUES (?, ?, ?, ?)
    """
    return query_db(
        sql_pg, sql_sq,
        (username.strip(), email.strip().lower(), password_hash, target_band),
        commit=True, return_id=True
    )

def get_user_by_username_or_email(identifier):
    ident = identifier.strip().lower()
    sql_pg = "SELECT * FROM users WHERE LOWER(username) = %s OR LOWER(email) = %s"
    sql_sq = "SELECT * FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?"
    return query_db(sql_pg, sql_sq, (ident, ident), one=True)

def get_user_by_id(user_id):
    if not user_id:
        return None
    sql_pg = "SELECT id, username, email, target_band, avatar, created_at FROM users WHERE id = %s"
    sql_sq = "SELECT id, username, email, target_band, avatar, created_at FROM users WHERE id = ?"
    return query_db(sql_pg, sql_sq, (user_id,), one=True)

def update_user_target_band(user_id, new_band):
    sql_pg = "UPDATE users SET target_band = %s WHERE id = %s"
    sql_sq = "UPDATE users SET target_band = ? WHERE id = ?"
    query_db(sql_pg, sql_sq, (new_band, user_id), commit=True)

# --- Test & Practice Queries ---
def save_test_result(test_type, test_id, test_title, score, max_score, band_score, time_spent, answers, user_id=None):
    sql_pg = """
        INSERT INTO test_history (user_id, test_type, test_id, test_title, score, max_score, band_score, time_spent_seconds, answers_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    sql_sq = """
        INSERT INTO test_history (user_id, test_type, test_id, test_title, score, max_score, band_score, time_spent_seconds, answers_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    return query_db(
        sql_pg, sql_sq,
        (user_id, test_type, test_id, test_title, score, max_score, band_score, time_spent, json.dumps(answers)),
        commit=True, return_id=True
    )

def get_test_history(limit=10, user_id=None):
    if user_id:
        sql_pg = "SELECT * FROM test_history WHERE user_id = %s ORDER BY created_at DESC LIMIT %s"
        sql_sq = "SELECT * FROM test_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?"
        return query_db(sql_pg, sql_sq, (user_id, limit))
    else:
        sql_pg = "SELECT * FROM test_history ORDER BY created_at DESC LIMIT %s"
        sql_sq = "SELECT * FROM test_history ORDER BY created_at DESC LIMIT ?"
        return query_db(sql_pg, sql_sq, (limit,))

def save_writing_submission(task_type, prompt_id, prompt_title, essay_text, word_count, estimated_band, evaluation, user_id=None):
    sql_pg = """
        INSERT INTO writing_submissions (user_id, task_type, prompt_id, prompt_title, essay_text, word_count, estimated_band, evaluation_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    sql_sq = """
        INSERT INTO writing_submissions (user_id, task_type, prompt_id, prompt_title, essay_text, word_count, estimated_band, evaluation_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    return query_db(
        sql_pg, sql_sq,
        (user_id, task_type, prompt_id, prompt_title, essay_text, word_count, estimated_band, json.dumps(evaluation)),
        commit=True, return_id=True
    )

def get_writing_submissions(limit=5, user_id=None):
    if user_id:
        sql_pg = "SELECT * FROM writing_submissions WHERE user_id = %s ORDER BY created_at DESC LIMIT %s"
        sql_sq = "SELECT * FROM writing_submissions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?"
        return query_db(sql_pg, sql_sq, (user_id, limit))
    else:
        sql_pg = "SELECT * FROM writing_submissions ORDER BY created_at DESC LIMIT %s"
        sql_sq = "SELECT * FROM writing_submissions ORDER BY created_at DESC LIMIT ?"
        return query_db(sql_pg, sql_sq, (limit,))

def save_speaking_log(topic_id, part, question, duration, notes, user_id=None):
    sql_pg = """
        INSERT INTO speaking_logs (user_id, topic_id, part, question, duration_seconds, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    sql_sq = """
        INSERT INTO speaking_logs (user_id, topic_id, part, question, duration_seconds, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    query_db(sql_pg, sql_sq, (user_id, topic_id, part, question, duration, notes), commit=True)

def toggle_vocab_mastery(word_id, user_id=1):
    conn, is_pg = get_db_connection()
    cursor = conn.cursor()
    try:
        sql_check = "SELECT is_mastered FROM vocab_progress WHERE word_id = %s AND user_id = %s" if is_pg else "SELECT is_mastered FROM vocab_progress WHERE word_id = ? AND user_id = ?"
        cursor.execute(sql_check, (word_id, user_id))
        row = cursor.fetchone()
        if row:
            current_status = row["is_mastered"] if isinstance(row, dict) else row[0]
            new_status = 0 if current_status == 1 else 1
            sql_up = "UPDATE vocab_progress SET is_mastered = %s, last_reviewed = CURRENT_TIMESTAMP, review_count = review_count + 1 WHERE word_id = %s AND user_id = %s" if is_pg else "UPDATE vocab_progress SET is_mastered = ?, last_reviewed = CURRENT_TIMESTAMP, review_count = review_count + 1 WHERE word_id = ? AND user_id = ?"
            cursor.execute(sql_up, (new_status, word_id, user_id))
        else:
            new_status = 1
            sql_in = "INSERT INTO vocab_progress (user_id, word_id, is_mastered, review_count) VALUES (%s, %s, 1, 1)" if is_pg else "INSERT INTO vocab_progress (user_id, word_id, is_mastered, review_count) VALUES (?, ?, 1, 1)"
            cursor.execute(sql_in, (user_id, word_id))
        conn.commit()
        return new_status
    finally:
        conn.close()

def get_vocab_progress(user_id=1):
    sql_pg = "SELECT word_id, is_mastered, review_count FROM vocab_progress WHERE user_id = %s"
    sql_sq = "SELECT word_id, is_mastered, review_count FROM vocab_progress WHERE user_id = ?"
    rows = query_db(sql_pg, sql_sq, (user_id,))
    return {
        row["word_id"]: {
            "is_mastered": bool(row["is_mastered"]),
            "review_count": row["review_count"]
        }
        for row in rows
    }

def get_dashboard_summary(user_id=None):
    conn, is_pg = get_db_connection()
    cursor = conn.cursor()
    try:
        p = lambda s: s if is_pg else s.replace("%s", "?")
        if user_id:
            cursor.execute(p("SELECT COUNT(*) as total_tests, AVG(band_score) as avg_band FROM test_history WHERE user_id = %s"), (user_id,))
            test_stat = cursor.fetchone()
            
            cursor.execute(p("SELECT COUNT(*) as total_essays, AVG(estimated_band) as avg_writing FROM writing_submissions WHERE user_id = %s"), (user_id,))
            writing_stat = cursor.fetchone()
            
            cursor.execute(p("SELECT COUNT(*) as total_speaking, SUM(duration_seconds) as total_talk_time FROM speaking_logs WHERE user_id = %s"), (user_id,))
            speaking_stat = cursor.fetchone()
            
            cursor.execute(p("SELECT COUNT(*) as mastered_count FROM vocab_progress WHERE user_id = %s AND is_mastered = 1"), (user_id,))
            vocab_stat = cursor.fetchone()
            
            cursor.execute(p("SELECT target_band FROM users WHERE id = %s"), (user_id,))
            user_info = cursor.fetchone()
            target_band = user_info['target_band'] if user_info and user_info['target_band'] is not None else 7.5
        else:
            cursor.execute("SELECT COUNT(*) as total_tests, AVG(band_score) as avg_band FROM test_history")
            test_stat = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(*) as total_essays, AVG(estimated_band) as avg_writing FROM writing_submissions")
            writing_stat = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(*) as total_speaking, SUM(duration_seconds) as total_talk_time FROM speaking_logs")
            speaking_stat = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(*) as mastered_count FROM vocab_progress WHERE is_mastered = 1")
            vocab_stat = cursor.fetchone()
            target_band = 7.5
        
        t_dict = dict(test_stat) if test_stat else {}
        w_dict = dict(writing_stat) if writing_stat else {}
        s_dict = dict(speaking_stat) if speaking_stat else {}
        v_dict = dict(vocab_stat) if vocab_stat else {}

        return {
            "total_tests": t_dict.get("total_tests") or 0,
            "avg_band": round(float(t_dict["avg_band"]), 1) if t_dict.get("avg_band") is not None else 6.5,
            "total_essays": w_dict.get("total_essays") or 0,
            "avg_writing": round(float(w_dict["avg_writing"]), 1) if w_dict.get("avg_writing") is not None else 6.5,
            "total_speaking": s_dict.get("total_speaking") or 0,
            "total_talk_minutes": round(float(s_dict.get("total_talk_time") or 0) / 60, 1),
            "vocab_mastered": v_dict.get("mastered_count") or 0,
            "target_band": float(target_band),
            "streak_days": 3
        }
    finally:
        conn.close()

# --- Cached Vocabulary Helpers (Dictionary API + Gemini AI) ---
def get_cached_word(word):
    if not word:
        return None
    w = word.strip().lower()
    sql_pg = "SELECT * FROM cached_vocabulary WHERE LOWER(word) = %s"
    sql_sq = "SELECT * FROM cached_vocabulary WHERE LOWER(word) = ?"
    row = query_db(sql_pg, sql_sq, (w,), one=True)
    if not row:
        return None
    return {
        "word": row["word"],
        "phonetic": row["phonetic"],
        "audio": row["audio"],
        "pos": row["pos"],
        "definition_en": row["definition_en"],
        "example_en": row["example_en"],
        "meaning_vi": row["meaning_vi"],
        "ielts_explanation": row["ielts_explanation"],
        "ielts_example": row["ielts_example"],
        "collocations": json.loads(row["collocations_json"] or "[]"),
        "synonyms": json.loads(row["synonyms_json"] or "[]"),
        "antonyms": json.loads(row["antonyms_json"] or "[]"),
        "band": row["band"] or "Band 7.0+",
        "topic": row["topic"] or "Academic IELTS",
        "source": row["source"],
        "created_at": str(row["created_at"])
    }

def save_cached_word(data):
    if not data or not data.get("word"):
        return False
    
    word = data.get("word", "").strip().lower()
    phonetic = data.get("phonetic", "")
    audio = data.get("audio", "")
    pos = data.get("pos", "")
    definition_en = data.get("definition_en", "")
    example_en = data.get("example_en", "")
    meaning_vi = data.get("meaning_vi", "")
    ielts_explanation = data.get("ielts_explanation", "")
    ielts_example = data.get("ielts_example", "")
    collocations_json = json.dumps(data.get("collocations", []), ensure_ascii=False)
    synonyms_json = json.dumps(data.get("synonyms", []), ensure_ascii=False)
    antonyms_json = json.dumps(data.get("antonyms", []), ensure_ascii=False)
    band = data.get("band", "Band 7.0+")
    topic = data.get("topic", "Academic IELTS")
    source = data.get("source", "gemini_dictionary")

    sql_pg = """
        INSERT INTO cached_vocabulary (
            word, phonetic, audio, pos, definition_en, example_en,
            meaning_vi, ielts_explanation, ielts_example,
            collocations_json, synonyms_json, antonyms_json,
            band, topic, source, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (word) DO UPDATE SET
            phonetic = EXCLUDED.phonetic,
            audio = EXCLUDED.audio,
            pos = EXCLUDED.pos,
            definition_en = EXCLUDED.definition_en,
            example_en = EXCLUDED.example_en,
            meaning_vi = EXCLUDED.meaning_vi,
            ielts_explanation = EXCLUDED.ielts_explanation,
            ielts_example = EXCLUDED.ielts_example,
            collocations_json = EXCLUDED.collocations_json,
            synonyms_json = EXCLUDED.synonyms_json,
            antonyms_json = EXCLUDED.antonyms_json,
            band = EXCLUDED.band,
            topic = EXCLUDED.topic,
            source = EXCLUDED.source,
            updated_at = CURRENT_TIMESTAMP
    """
    sql_sq = """
        INSERT OR REPLACE INTO cached_vocabulary (
            word, phonetic, audio, pos, definition_en, example_en,
            meaning_vi, ielts_explanation, ielts_example,
            collocations_json, synonyms_json, antonyms_json,
            band, topic, source, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """
    params = (
        word, phonetic, audio, pos, definition_en, example_en,
        meaning_vi, ielts_explanation, ielts_example,
        collocations_json, synonyms_json, antonyms_json,
        band, topic, source
    )
    query_db(sql_pg, sql_sq, params, commit=True)
    return True

def list_cached_words(limit=50):
    sql_pg = "SELECT * FROM cached_vocabulary ORDER BY updated_at DESC LIMIT %s"
    sql_sq = "SELECT * FROM cached_vocabulary ORDER BY updated_at DESC LIMIT ?"
    rows = query_db(sql_pg, sql_sq, (limit,))
    return [
        {
            "word": r["word"],
            "phonetic": r["phonetic"],
            "pos": r["pos"],
            "meaning_vi": r["meaning_vi"],
            "band": r["band"],
            "topic": r["topic"]
        }
        for r in rows
    ]
