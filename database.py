import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('reality.db')
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            coins INTEGER DEFAULT 0,
            energy INTEGER DEFAULT 100,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            total_taps INTEGER DEFAULT 0,
            tokens INTEGER DEFAULT 0,
            last_update TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            avatar TEXT,
            strength INTEGER DEFAULT 5,
            intelligence INTEGER DEFAULT 5,
            charisma INTEGER DEFAULT 5,
            luck INTEGER DEFAULT 5,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS professions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            profession_key TEXT,
            unlocked_at TEXT,
            progress INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_id TEXT,
            completed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('reality.db')
    c = conn.cursor()
    c.execute('SELECT coins, energy, xp, level, total_taps, tokens FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return {
            'coins': result[0],
            'energy': result[1],
            'xp': result[2],
            'level': result[3],
            'total_taps': result[4],
            'tokens': result[5]
        }
    else:
        save_user(user_id, 0, 100, 0, 1, 0, 0)
        return {'coins': 0, 'energy': 100, 'xp': 0, 'level': 1, 'total_taps': 0, 'tokens': 0}

def save_user(user_id, coins, energy, xp, level, total_taps, tokens):
    conn = sqlite3.connect('reality.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO users (user_id, coins, energy, xp, level, total_taps, tokens, last_update)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, coins, energy, xp, level, total_taps, tokens, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_character(user_id):
    conn = sqlite3.connect('reality.db')
    c = conn.cursor()
    c.execute('SELECT name, avatar, strength, intelligence, charisma, luck FROM characters WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return {
            'name': result[0],
            'avatar': result[1],
            'strength': result[2],
            'intelligence': result[3],
            'charisma': result[4],
            'luck': result[5]
        }
    return None

def save_character(user_id, name, avatar, strength, intelligence, charisma, luck):
    conn = sqlite3.connect('reality.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO characters (user_id, name, avatar, strength, intelligence, charisma, luck)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, name, avatar, strength, intelligence, charisma, luck))
    conn.commit()
    conn.close()

def get_professions(user_id):
    conn = sqlite3.connect('reality.db')
    c = conn.cursor()
    c.execute('SELECT profession_key, progress FROM professions WHERE user_id = ?', (user_id,))
    results = c.fetchall()
    conn.close()
    
    profs = {}
    for row in results:
        profs[row[0]] = {'progress': row[1]}
    return profs

def unlock_profession(user_id, profession_key):
    conn = sqlite3.connect('reality.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO professions (user_id, profession_key, unlocked_at, progress)
        VALUES (?, ?, ?, ?)
    ''', (user_id, profession_key, datetime.now().isoformat(), 0))
    conn.commit()
    conn.close()

def get_tasks(user_id):
    conn = sqlite3.connect('reality.db')
    c = conn.cursor()
    c.execute('SELECT task_id FROM tasks WHERE user_id = ?', (user_id,))
    results = c.fetchall()
    conn.close()
    
    return [row[0] for row in results]

def complete_task(user_id, task_id):
    conn = sqlite3.connect('reality.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO tasks (user_id, task_id, completed_at)
        VALUES (?, ?, ?)
    ''', (user_id, task_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()
