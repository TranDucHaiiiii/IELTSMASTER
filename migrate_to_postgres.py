"""
IELTS Master Hub - Direct SQLite to PostgreSQL Migration Script.
Run this script to automatically create tables and copy all data from ielts_master.db to PostgreSQL.

Usage:
  python migrate_to_postgres.py "postgresql://username:password@localhost:5432/ielts_master"
Or set DATABASE_URL environment variable and run:
  python migrate_to_postgres.py
"""

import sys
import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_batch

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "ielts_master.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema_postgres.sql")

def migrate():
    # 1. Determine PostgreSQL connection URL
    if len(sys.argv) > 1:
        pg_url = sys.argv[1]
    else:
        pg_url = os.environ.get("DATABASE_URL")

    if not pg_url:
        print("[-] Vui lòng cung cấp chuỗi kết nối PostgreSQL (DATABASE_URL)!")
        print("Ví dụ:")
        print("  python migrate_to_postgres.py \"postgresql://postgres:password@localhost:5432/ielts_master\"")
        print("Hoặc bạn có thể mở file 'dump_postgres.sql' và chạy trực tiếp trong pgAdmin / DBeaver / psql.")
        return

    print(f"[*] Đang kết nối tới PostgreSQL: {pg_url}...")
    try:
        pg_conn = psycopg2.connect(pg_url)
        pg_conn.autocommit = False
        pg_cursor = pg_conn.cursor()
    except Exception as e:
        print(f"[-] Lỗi kết nối PostgreSQL: {e}")
        return

    # 2. Execute schema_postgres.sql
    print("[*] Đang khởi tạo bảng trên PostgreSQL...")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    pg_cursor.execute(schema_sql)
    pg_conn.commit()
    print("[+] Khởi tạo cấu trúc bảng thành công!")

    # 3. Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    table_order = [
        "users",
        "user_profile",
        "test_history",
        "writing_submissions",
        "speaking_logs",
        "vocab_progress",
        "cached_vocabulary"
    ]

    print("[*] Bắt đầu chuyển dữ liệu từ SQLite sang PostgreSQL...")
    for table in table_order:
        sqlite_cursor.execute(f"PRAGMA table_info({table})")
        cols = [col["name"] for col in sqlite_cursor.fetchall()]
        
        sqlite_cursor.execute(f"SELECT * FROM {table}")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            print(f"  - Bảng '{table}': 0 dòng (Bỏ qua)")
            continue

        cols_str = ", ".join(cols)
        placeholders = ", ".join(["%s"] * len(cols))
        query = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
        
        data_tuples = [tuple(row) for row in rows]
        execute_batch(pg_cursor, query, data_tuples)
        print(f"  [+] Đã chuyển {len(rows)} dòng vào bảng '{table}'")

    # 4. Reset sequences for tables with serial id
    seq_tables = ["users", "user_profile", "test_history", "writing_submissions", "speaking_logs"]
    for t in seq_tables:
        pg_cursor.execute(f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), COALESCE(MAX(id), 1)) FROM {t};")

    pg_conn.commit()
    pg_cursor.close()
    pg_conn.close()
    sqlite_conn.close()
    print("\n[V] CHUYỂN ĐỔI DỮ LIỆU SANG POSTGRESQL HOÀN TẤT THÀNH CÔNG!")

if __name__ == "__main__":
    migrate()
