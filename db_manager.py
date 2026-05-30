"""
db_manager.py — قاعدة بيانات SQLite لحفظ مودات المستخدمين
"""
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "mods.db")


def init_db():
    """إنشاء قاعدة البيانات والجداول"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            mod_name TEXT NOT NULL,
            mod_type TEXT NOT NULL,
            mod_data TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_mod(user_id: int, mod_data: dict) -> int:
    """يحفظ مود ويرجع ID"""
    conn = sqlite3.connect(DB_PATH)
    name = mod_data.get("display_name") or mod_data.get("display_prefix") or "مود"
    mod_type = mod_data.get("mod_type", "item")
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    cursor = conn.execute(
        "INSERT INTO mods (user_id, mod_name, mod_type, mod_data, created_at) VALUES (?,?,?,?,?)",
        (user_id, name, mod_type, json.dumps(mod_data, ensure_ascii=False), created_at)
    )
    mod_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return mod_id


def get_user_mods(user_id: int) -> list[dict]:
    """يرجع كل مودات المستخدم"""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, mod_name, mod_type, created_at FROM mods WHERE user_id=? ORDER BY id DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "type": r[2], "date": r[3]} for r in rows]


def get_mod_by_id(mod_id: int, user_id: int) -> dict | None:
    """يرجع بيانات مود محدد"""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT mod_data FROM mods WHERE id=? AND user_id=?",
        (mod_id, user_id)
    ).fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None


def delete_mod(mod_id: int, user_id: int) -> bool:
    """يحذف مود"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "DELETE FROM mods WHERE id=? AND user_id=?",
        (mod_id, user_id)
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def get_mods_count(user_id: int) -> int:
    """عدد مودات المستخدم"""
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute(
        "SELECT COUNT(*) FROM mods WHERE user_id=?",
        (user_id,)
    ).fetchone()[0]
    conn.close()
    return count


# تهيئة قاعدة البيانات عند الاستيراد
init_db()
