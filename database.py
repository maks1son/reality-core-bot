"""
RE:ALITY — База данных v2
Безлимитные уровни, прогресс заданий, медленная регенерация
"""
import sqlite3, os, json, time

DB_PATH = os.environ.get("DB_PATH", "reality.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        tg_id INTEGER PRIMARY KEY, name TEXT DEFAULT '', avatar INTEGER DEFAULT 1,
        stat_str INTEGER DEFAULT 5, stat_int INTEGER DEFAULT 5,
        stat_cha INTEGER DEFAULT 5, stat_luck INTEGER DEFAULT 5,
        coins INTEGER DEFAULT 0, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1,
        tokens INTEGER DEFAULT 0, energy INTEGER DEFAULT 100, max_energy INTEGER DEFAULT 100,
        coins_per_tap INTEGER DEFAULT 1, multi_tap INTEGER DEFAULT 1,
        energy_regen REAL DEFAULT 0.4, last_energy_update REAL DEFAULT 0,
        registered INTEGER DEFAULT 0,
        upg_tap_level INTEGER DEFAULT 0, upg_energy_level INTEGER DEFAULT 0,
        upg_multi_level INTEGER DEFAULT 0, upg_regen_level INTEGER DEFAULT 0,
        created_at REAL DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS unlocked_professions (
        tg_id INTEGER, profession_id TEXT, unlocked_at REAL DEFAULT 0,
        PRIMARY KEY (tg_id, profession_id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS completed_tasks (
        tg_id INTEGER, profession_id TEXT, task_index INTEGER,
        score INTEGER DEFAULT 0, completed_at REAL DEFAULT 0,
        PRIMARY KEY (tg_id, profession_id, task_index))""")
    c.execute("""CREATE TABLE IF NOT EXISTS task_progress (
        tg_id INTEGER, profession_id TEXT, task_index INTEGER,
        progress_data TEXT DEFAULT '{}', updated_at REAL DEFAULT 0,
        PRIMARY KEY (tg_id, profession_id, task_index))""")
    c.execute("""CREATE TABLE IF NOT EXISTS tap_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id INTEGER,
        tap_count INTEGER, timestamp REAL, ip TEXT DEFAULT '')""")
    conn.commit()
    conn.close()

def get_user(tg_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(tg_id):
    conn = get_conn()
    now = time.time()
    conn.execute("INSERT OR IGNORE INTO users (tg_id, last_energy_update, created_at) VALUES (?,?,?)",
                 (tg_id, now, now))
    conn.commit(); conn.close()

def register_user(tg_id, name, avatar, stats):
    conn = get_conn()
    conn.execute("""UPDATE users SET name=?, avatar=?, stat_str=?, stat_int=?,
        stat_cha=?, stat_luck=?, registered=1, last_energy_update=? WHERE tg_id=?""",
        (name, avatar, stats.get("str",5), stats.get("int",5),
         stats.get("cha",5), stats.get("luck",5), time.time(), tg_id))
    conn.commit(); conn.close()

def update_user_fields(tg_id, fields):
    allowed = {"coins","xp","level","tokens","energy","max_energy","coins_per_tap",
               "multi_tap","energy_regen","last_energy_update",
               "upg_tap_level","upg_energy_level","upg_multi_level","upg_regen_level"}
    fields = {k:v for k,v in fields.items() if k in allowed}
    if not fields: return
    sets = ", ".join(f"{k}=?" for k in fields)
    conn = get_conn()
    conn.execute(f"UPDATE users SET {sets} WHERE tg_id=?", list(fields.values())+[tg_id])
    conn.commit(); conn.close()

def unlock_profession(tg_id, pid):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO unlocked_professions VALUES (?,?,?)",
                 (tg_id, pid, time.time()))
    conn.commit(); conn.close()

def get_unlocked(tg_id):
    conn = get_conn()
    rows = conn.execute("SELECT profession_id FROM unlocked_professions WHERE tg_id=?",
                        (tg_id,)).fetchall()
    conn.close()
    return [r["profession_id"] for r in rows]

def complete_task(tg_id, pid, tidx, score):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO completed_tasks VALUES (?,?,?,?,?)",
                 (tg_id, pid, tidx, score, time.time()))
    conn.execute("DELETE FROM task_progress WHERE tg_id=? AND profession_id=? AND task_index=?",
                 (tg_id, pid, tidx))
    conn.commit(); conn.close()

def get_completed(tg_id, pid=None):
    conn = get_conn()
    if pid:
        rows = conn.execute("SELECT * FROM completed_tasks WHERE tg_id=? AND profession_id=?",
                            (tg_id, pid)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM completed_tasks WHERE tg_id=?", (tg_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_progress(tg_id, pid, tidx, data):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO task_progress VALUES (?,?,?,?,?)",
                 (tg_id, pid, tidx, json.dumps(data), time.time()))
    conn.commit(); conn.close()

def get_progress(tg_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM task_progress WHERE tg_id=?", (tg_id,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["progress_data"] = json.loads(d["progress_data"])
        result.append(d)
    return result

def log_taps(tg_id, count, ip=""):
    conn = get_conn()
    conn.execute("INSERT INTO tap_log (tg_id,tap_count,timestamp,ip) VALUES (?,?,?,?)",
                 (tg_id, count, time.time(), ip))
    conn.commit(); conn.close()

def check_tap_rate(tg_id, window=10, mx=200):
    conn = get_conn()
    row = conn.execute("SELECT COALESCE(SUM(tap_count),0) as t FROM tap_log WHERE tg_id=? AND timestamp>?",
                       (tg_id, time.time()-window)).fetchone()
    conn.close()
    return row["t"] <= mx

init_db()
