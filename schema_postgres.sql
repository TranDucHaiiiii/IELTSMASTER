-- ====================================================================
-- IELTS Master Hub - PostgreSQL Database Schema
-- Compatible with PostgreSQL 12+ (pgAdmin, psql, Neon, Supabase, Render, Docker)
-- ====================================================================
\encoding UTF8
SET client_encoding = 'UTF8';

-- 1. Bảng Users (Quản lý người dùng & xác thực)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    target_band NUMERIC(3, 1) DEFAULT 7.5,
    avatar VARCHAR(50) DEFAULT '👨‍🎓',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. Bảng User Profile (Thông tin tiến độ mục tiêu bổ trợ)
CREATE TABLE IF NOT EXISTS user_profile (
    id SERIAL PRIMARY KEY,
    target_band NUMERIC(3, 1) DEFAULT 7.5,
    streak_days INTEGER DEFAULT 1,
    last_active_date VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3. Bảng Test History (Lịch sử làm bài Listening & Reading)
CREATE TABLE IF NOT EXISTS test_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    test_type VARCHAR(50) NOT NULL,
    test_id VARCHAR(100) NOT NULL,
    test_title VARCHAR(255) NOT NULL,
    score INTEGER NOT NULL,
    max_score INTEGER NOT NULL,
    band_score NUMERIC(3, 1) NOT NULL,
    time_spent_seconds INTEGER DEFAULT 0,
    answers_json TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 4. Bảng Writing Submissions (Bài nộp Writing & chấm điểm AI)
CREATE TABLE IF NOT EXISTS writing_submissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    task_type VARCHAR(50) NOT NULL,
    prompt_id VARCHAR(100) NOT NULL,
    prompt_title VARCHAR(255) NOT NULL,
    essay_text TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    estimated_band NUMERIC(3, 1) NOT NULL,
    evaluation_json TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 5. Bảng Speaking Practice Logs (Nhật ký luyện nói Speaking)
CREATE TABLE IF NOT EXISTS speaking_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    topic_id VARCHAR(100) NOT NULL,
    part VARCHAR(50) NOT NULL,
    question TEXT NOT NULL,
    duration_seconds INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 6. Bảng Vocabulary Progress (Tiến độ học từ vựng theo người dùng)
CREATE TABLE IF NOT EXISTS vocab_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER DEFAULT 1 REFERENCES users(id) ON DELETE CASCADE,
    word_id VARCHAR(100) NOT NULL,
    is_mastered INTEGER DEFAULT 0,
    review_count INTEGER DEFAULT 0,
    last_reviewed TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_word UNIQUE (user_id, word_id)
);

-- 7. Bảng Cached Vocabulary (Từ điển tra cứu đã lưu đệm từ Gemini / Dictionary API)
CREATE TABLE IF NOT EXISTS cached_vocabulary (
    word VARCHAR(100) PRIMARY KEY,
    phonetic VARCHAR(100),
    audio TEXT,
    pos VARCHAR(50),
    definition_en TEXT,
    example_en TEXT,
    meaning_vi TEXT,
    ielts_explanation TEXT,
    ielts_example TEXT,
    collocations_json TEXT,
    synonyms_json TEXT,
    antonyms_json TEXT,
    band VARCHAR(50),
    topic VARCHAR(100),
    source VARCHAR(100) DEFAULT 'gemini_dictionary',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ====================================================================
-- Tạo Index tối ưu hóa tốc độ truy vấn (Performance Indexes)
-- ====================================================================
CREATE INDEX IF NOT EXISTS idx_test_history_user_id ON test_history(user_id);
CREATE INDEX IF NOT EXISTS idx_writing_submissions_user_id ON writing_submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_speaking_logs_user_id ON speaking_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_vocab_progress_user_id ON vocab_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_cached_vocab_updated ON cached_vocabulary(updated_at DESC);

