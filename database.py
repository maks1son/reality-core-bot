import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('reality.db')
    c = conn.cursor()
    
    # Таблица пользователей
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            money INTEGER DEFAULT 5000,
            energy INTEGER DEFAULT 100,
            day INTEGER DEFAULT 1,
            actions INTEGER DEFAULT 3,
            last_update TEXT
        )
    ''')
    
    # Таблица персонажей
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
    
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('reality.db')
    c = conn.cursor()
    c.execute('SELECT money, energy, day, actions FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return {
            'money': result[0],
            'energy': result[1],
            'day': result[2],
            'actions': result[3]
        }
    else:
        save_user(user_id, 5000, 100, 1, 3)
        return {'money': 5000, 'energy': 100, 'day': 1, 'actions': 3}

def save_user(user_id, money, energy, day, actions):
    conn = sqlite3.connect('reality.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO users (user_id, money, energy, day, actions, last_update)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, money, energy, day, actions, datetime.now().isoformat()))
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
