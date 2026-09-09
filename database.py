"""
Database manager for IELTS Master Hub using SQLite.
Handles user authentication, test history, writing submissions, vocabulary progress, and study statistics.
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "ielts_master.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Table: Users
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

    # Table: Test History (Listening & Reading)
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
    
    # Table: Writing Submissions
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
    
    # Table: Speaking Practice Logs
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
    
    # Table: Vocabulary Progress
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

    # Table: Cached Vocabulary (Enriched with Free Dictionary API + Gemini)
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
    
    # Check if user_id column exists in older tables (migration helper)
    tables_to_check = ['test_history', 'writing_submissions', 'speaking_logs', 'vocab_progress']
    for t in tables_to_check:
        cursor.execute(f"PRAGMA table_info({t})")
        columns = [col['name'] for col in cursor.fetchall()]
        if 'user_id' not in columns:
            cursor.execute(f"ALTER TABLE {t} ADD COLUMN user_id INTEGER DEFAULT 1")
            
    conn.commit()
    conn.close()

# --- User Management Queries ---
def create_user(username, email, password_hash, target_band=7.5):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (username, email, password_hash, target_band)
        VALUES (?, ?, ?, ?)
    """, (username.strip(), email.strip().lower(), password_hash, target_band))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id

def get_user_by_username_or_email(identifier):
    conn = get_db_connection()
    cursor = conn.cursor()
    ident = identifier.strip().lower()
    cursor.execute("""
        SELECT * FROM users 
        WHERE LOWER(username) = ? OR LOWER(email) = ?
    """, (ident, ident))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id):
    if not user_id:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, target_band, avatar, created_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_user_target_band(user_id, new_band):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET target_band = ? WHERE id = ?", (new_band, user_id))
    conn.commit()
    conn.close()

# --- Test & Practice Queries ---
def save_test_result(test_type, test_id, test_title, score, max_score, band_score, time_spent, answers, user_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO test_history (user_id, test_type, test_id, test_title, score, max_score, band_score, time_spent_seconds, answers_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, test_type, test_id, test_title, score, max_score, band_score, time_spent, json.dumps(answers)))
    conn.commit()
    test_id_inserted = cursor.lastrowid
    conn.close()
    return test_id_inserted

def get_test_history(limit=10, user_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT * FROM test_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
    else:
        cursor.execute("SELECT * FROM test_history ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def save_writing_submission(task_type, prompt_id, prompt_title, essay_text, word_count, estimated_band, evaluation, user_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO writing_submissions (user_id, task_type, prompt_id, prompt_title, essay_text, word_count, estimated_band, evaluation_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, task_type, prompt_id, prompt_title, essay_text, word_count, estimated_band, json.dumps(evaluation)))
    conn.commit()
    sub_id = cursor.lastrowid
    conn.close()
    return sub_id

def get_writing_submissions(limit=5, user_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT * FROM writing_submissions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
    else:
        cursor.execute("SELECT * FROM writing_submissions ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def save_speaking_log(topic_id, part, question, duration, notes, user_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO speaking_logs (user_id, topic_id, part, question, duration_seconds, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, topic_id, part, question, duration, notes))
    conn.commit()
    conn.close()

def toggle_vocab_mastery(word_id, user_id=1):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_mastered FROM vocab_progress WHERE word_id = ? AND user_id = ?", (word_id, user_id))
    row = cursor.fetchone()
    if row:
        new_status = 0 if row["is_mastered"] == 1 else 1
        cursor.execute("UPDATE vocab_progress SET is_mastered = ?, last_reviewed = CURRENT_TIMESTAMP, review_count = review_count + 1 WHERE word_id = ? AND user_id = ?", (new_status, word_id, user_id))
    else:
        new_status = 1
        cursor.execute("INSERT INTO vocab_progress (user_id, word_id, is_mastered, review_count) VALUES (?, ?, 1, 1)", (user_id, word_id))
    conn.commit()
    conn.close()
    return new_status

def get_vocab_progress(user_id=1):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT word_id, is_mastered, review_count FROM vocab_progress WHERE user_id = ?", (user_id,))
    rows = {row["word_id"]: {"is_mastered": bool(row["is_mastered"]), "review_count": row["review_count"]} for row in cursor.fetchall()}
    conn.close()
    return rows

def get_dashboard_summary(user_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if user_id:
        cursor.execute("SELECT COUNT(*) as total_tests, AVG(band_score) as avg_band FROM test_history WHERE user_id = ?", (user_id,))
        test_stat = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as total_essays, AVG(estimated_band) as avg_writing FROM writing_submissions WHERE user_id = ?", (user_id,))
        writing_stat = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as total_speaking, SUM(duration_seconds) as total_talk_time FROM speaking_logs WHERE user_id = ?", (user_id,))
        speaking_stat = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as mastered_count FROM vocab_progress WHERE user_id = ? AND is_mastered = 1", (user_id,))
        vocab_stat = cursor.fetchone()
        
        cursor.execute("SELECT target_band FROM users WHERE id = ?", (user_id,))
        user_info = cursor.fetchone()
        target_band = user_info['target_band'] if user_info else 7.5
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
    
    conn.close()
    
    return {
        "total_tests": test_stat["total_tests"] if test_stat else 0,
        "avg_band": round(test_stat["avg_band"], 1) if (test_stat and test_stat["avg_band"]) else 6.5,
        "total_essays": writing_stat["total_essays"] if writing_stat else 0,
        "avg_writing": round(writing_stat["avg_writing"], 1) if (writing_stat and writing_stat["avg_writing"]) else 6.5,
        "total_speaking": speaking_stat["total_speaking"] if speaking_stat else 0,
        "total_talk_minutes": round((speaking_stat["total_talk_time"] or 0) / 60, 1),
        "vocab_mastered": vocab_stat["mastered_count"] if vocab_stat else 0,
        "target_band": target_band,
        "streak_days": 3
    }

# --- Cached Vocabulary Helpers (Dictionary API + Gemini AI) ---
def get_cached_word(word):
    if not word:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cached_vocabulary WHERE LOWER(word) = ?", (word.strip().lower(),))
    row = cursor.fetchone()
    conn.close()
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
        "created_at": row["created_at"]
    }

def save_cached_word(data):
    if not data or not data.get("word"):
        return False
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO cached_vocabulary (
            word, phonetic, audio, pos, definition_en, example_en,
            meaning_vi, ielts_explanation, ielts_example,
            collocations_json, synonyms_json, antonyms_json,
            band, topic, source, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        data.get("word", "").strip().lower(),
        data.get("phonetic", ""),
        data.get("audio", ""),
        data.get("pos", ""),
        data.get("definition_en", ""),
        data.get("example_en", ""),
        data.get("meaning_vi", ""),
        data.get("ielts_explanation", ""),
        data.get("ielts_example", ""),
        json.dumps(data.get("collocations", []), ensure_ascii=False),
        json.dumps(data.get("synonyms", []), ensure_ascii=False),
        json.dumps(data.get("antonyms", []), ensure_ascii=False),
        data.get("band", "Band 7.0+"),
        data.get("topic", "Academic IELTS"),
        data.get("source", "gemini_dictionary")
    ))
    conn.commit()
    conn.close()
    return True

def list_cached_words(limit=50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cached_vocabulary ORDER BY updated_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for row in rows:
        results.append({
            "word": row["word"],
            "phonetic": row["phonetic"],
            "pos": row["pos"],
            "meaning_vi": row["meaning_vi"],
            "band": row["band"],
            "topic": row["topic"]
        })
    return results
