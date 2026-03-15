"""
RE:ALITY — Модуль базы данных (SQLite)
Хранение пользователей, прогресса, улучшений, открытых профессий и заданий.
"""

import sqlite3
import os
import json
import time

DB_PATH = os.environ.get("DB_PATH", "reality.db")


def get_conn():
    """Получить соединение к БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Инициализация таблиц"""
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL DEFAULT '',
            avatar INTEGER NOT NULL DEFAULT 1,
            stat_str INTEGER NOT NULL DEFAULT 5,
            stat_int INTEGER NOT NULL DEFAULT 5,
            stat_cha INTEGER NOT NULL DEFAULT 5,
            stat_luck INTEGER NOT NULL DEFAULT 5,
            coins INTEGER NOT NULL DEFAULT 0,
            xp INTEGER NOT NULL DEFAULT 0,
            level INTEGER NOT NULL DEFAULT 1,
            tokens INTEGER NOT NULL DEFAULT 0,
            energy INTEGER NOT NULL DEFAULT 100,
            max_energy INTEGER NOT NULL DEFAULT 100,
            coins_per_tap INTEGER NOT NULL DEFAULT 1,
            multi_tap INTEGER NOT NULL DEFAULT 1,
            energy_regen REAL NOT NULL DEFAULT 2.0,
            combo_count INTEGER NOT NULL DEFAULT 0,
            combo_last_tap REAL NOT NULL DEFAULT 0,
            last_energy_update REAL NOT NULL DEFAULT 0,
            registered INTEGER NOT NULL DEFAULT 0,
            upg_tap_level INTEGER NOT NULL DEFAULT 0,
            upg_energy_level INTEGER NOT NULL DEFAULT 0,
            upg_multi_level INTEGER NOT NULL DEFAULT 0,
            upg_regen_level INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS unlocked_professions (
            tg_id INTEGER NOT NULL,
            profession_id TEXT NOT NULL,
            unlocked_at REAL NOT NULL DEFAULT 0,
            PRIMARY KEY (tg_id, profession_id),
            FOREIGN KEY (tg_id) REFERENCES users(tg_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS completed_tasks (
            tg_id INTEGER NOT NULL,
            profession_id TEXT NOT NULL,
            task_index INTEGER NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            completed_at REAL NOT NULL DEFAULT 0,
            PRIMARY KEY (tg_id, profession_id, task_index),
            FOREIGN KEY (tg_id) REFERENCES users(tg_id)
        )
    """)

    # Античит: логи тапов
    c.execute("""
        CREATE TABLE IF NOT EXISTS tap_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER NOT NULL,
            tap_count INTEGER NOT NULL,
            timestamp REAL NOT NULL,
            ip TEXT DEFAULT ''
        )
    """)

    conn.commit()
    conn.close()


# ============ Пользователи ============

def get_user(tg_id: int):
    """Получить пользователя по tg_id"""
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def create_user(tg_id: int):
    """Создать пустого пользователя (до регистрации)"""
    conn = get_conn()
    now = time.time()
    conn.execute("""
        INSERT OR IGNORE INTO users (tg_id, last_energy_update, created_at)
        VALUES (?, ?, ?)
    """, (tg_id, now, now))
    conn.commit()
    conn.close()


def register_user(tg_id: int, name: str, avatar: int, stats: dict):
    """Регистрация: имя, аватар, распределение характеристик"""
    conn = get_conn()
    now = time.time()
    conn.execute("""
        UPDATE users SET
            name=?, avatar=?,
            stat_str=?, stat_int=?, stat_cha=?, stat_luck=?,
            registered=1, last_energy_update=?
        WHERE tg_id=?
    """, (
        name, avatar,
        stats.get("str", 5), stats.get("int", 5),
        stats.get("cha", 5), stats.get("luck", 5),
        now, tg_id
    ))
    conn.commit()
    conn.close()


def update_user_field(tg_id: int, field: str, value):
    """Обновить одно поле пользователя"""
    allowed = {
        "coins", "xp", "level", "tokens", "energy", "max_energy",
        "coins_per_tap", "multi_tap", "energy_regen",
        "combo_count", "combo_last_tap", "last_energy_update",
        "upg_tap_level", "upg_energy_level", "upg_multi_level", "upg_regen_level"
    }
    if field not in allowed:
        return
    conn = get_conn()
    conn.execute(f"UPDATE users SET {field}=? WHERE tg_id=?", (value, tg_id))
    conn.commit()
    conn.close()


def update_user_fields(tg_id: int, fields: dict):
    """Обновить несколько полей пользователя"""
    allowed = {
        "coins", "xp", "level", "tokens", "energy", "max_energy",
        "coins_per_tap", "multi_tap", "energy_regen",
        "combo_count", "combo_last_tap", "last_energy_update",
        "upg_tap_level", "upg_energy_level", "upg_multi_level", "upg_regen_level"
    }
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [tg_id]
    conn = get_conn()
    conn.execute(f"UPDATE users SET {sets} WHERE tg_id=?", vals)
    conn.commit()
    conn.close()


# ============ Профессии ============

def unlock_profession(tg_id: int, profession_id: str):
    """Открыть профессию"""
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO unlocked_professions (tg_id, profession_id, unlocked_at)
        VALUES (?, ?, ?)
    """, (tg_id, profession_id, time.time()))
    conn.commit()
    conn.close()


def get_unlocked_professions(tg_id: int):
    """Получить список открытых профессий"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT profession_id FROM unlocked_professions WHERE tg_id=?", (tg_id,)
    ).fetchall()
    conn.close()
    return [r["profession_id"] for r in rows]


# ============ Задания ============

def complete_task(tg_id: int, profession_id: str, task_index: int, score: int):
    """Отметить задание как выполненное"""
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO completed_tasks (tg_id, profession_id, task_index, score, completed_at)
        VALUES (?, ?, ?, ?, ?)
    """, (tg_id, profession_id, task_index, score, time.time()))
    conn.commit()
    conn.close()


def get_completed_tasks(tg_id: int, profession_id: str = None):
    """Получить выполненные задания"""
    conn = get_conn()
    if profession_id:
        rows = conn.execute(
            "SELECT * FROM completed_tasks WHERE tg_id=? AND profession_id=?",
            (tg_id, profession_id)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM completed_tasks WHERE tg_id=?", (tg_id,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============ Античит ============

def log_taps(tg_id: int, count: int, ip: str = ""):
    """Логировать пакет тапов для античита"""
    conn = get_conn()
    conn.execute("""
        INSERT INTO tap_log (tg_id, tap_count, timestamp, ip) VALUES (?, ?, ?, ?)
    """, (tg_id, count, time.time(), ip))
    conn.commit()
    conn.close()


def check_tap_rate(tg_id: int, window_sec: int = 10, max_taps: int = 200):
    """Проверка: не слишком ли быстро тапает (античит)"""
    conn = get_conn()
    since = time.time() - window_sec
    row = conn.execute("""
        SELECT COALESCE(SUM(tap_count), 0) as total
        FROM tap_log WHERE tg_id=? AND timestamp>?
    """, (tg_id, since)).fetchone()
    conn.close()
    return row["total"] <= max_taps


# Инициализация при импорте
init_db()
