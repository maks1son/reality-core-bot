"""
RE:ALITY: Профессии — Telegram Mini App
Backend: FastAPI + SQLite
Автор: AI-разработчик
"""

import os
import json
import time
import sqlite3
import hashlib
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# ─── Конфигурация ───────────────────────────────────────────────────────────
DB_PATH = "reality_game.db"
STATIC_DIR = Path(__file__).parent

# ─── Загрузка изображений героев ────────────────────────────────────────────
def load_hero_image(index: int) -> str:
    """Загружает изображение героя как base64 data URL"""
    hero_files = {
        1: "hero1__1_.png",
        2: "hero2__1_.png",
        3: "hero3__1_.png",
    }
    import base64
    # Пытаемся найти файл в разных местах
    search_paths = [
        Path(__file__).parent / hero_files[index],
        Path("/mnt/user-data/uploads") / hero_files[index],
    ]
    for path in search_paths:
        if path.exists():
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            return f"data:image/png;base64,{data}"
    return ""

HERO_IMAGES = {i: load_hero_image(i) for i in [1, 2, 3]}

# ─── Инициализация БД ────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Таблица игроков
    c.execute("""
        CREATE TABLE IF NOT EXISTS players (
            telegram_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            avatar INTEGER DEFAULT 1,
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            coins INTEGER DEFAULT 0,
            tokens INTEGER DEFAULT 1,
            energy INTEGER DEFAULT 100,
            max_energy INTEGER DEFAULT 100,
            last_energy_update REAL DEFAULT 0,
            stat_strength INTEGER DEFAULT 5,
            stat_intel INTEGER DEFAULT 5,
            stat_charisma INTEGER DEFAULT 5,
            stat_luck INTEGER DEFAULT 5,
            tap_power INTEGER DEFAULT 1,
            tap_multiplier INTEGER DEFAULT 1,
            energy_regen REAL DEFAULT 2.0,
            total_taps INTEGER DEFAULT 0,
            combo_count INTEGER DEFAULT 0,
            last_tap_time REAL DEFAULT 0,
            created_at REAL DEFAULT 0,
            upgrades TEXT DEFAULT '{}',
            opened_professions TEXT DEFAULT '[]',
            completed_tasks TEXT DEFAULT '{}'
        )
    """)
    
    conn.commit()
    conn.close()

# ─── Модели данных ───────────────────────────────────────────────────────────
class CreatePlayerRequest(BaseModel):
    telegram_id: str
    name: str
    avatar: int
    stat_strength: int
    stat_intel: int
    stat_charisma: int
    stat_luck: int

class TapRequest(BaseModel):
    telegram_id: str
    taps: int
    timestamp: float

class UpgradeRequest(BaseModel):
    telegram_id: str
    upgrade_id: str

class OpenProfessionRequest(BaseModel):
    telegram_id: str
    profession_id: str

class CompleteTaskRequest(BaseModel):
    telegram_id: str
    profession_id: str
    task_index: int
    score: int  # 0-100

# ─── Вспомогательные функции ────────────────────────────────────────────────
def get_player(telegram_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE telegram_id = ?", (telegram_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    columns = [desc[0] for desc in c.description] if c.description else []
    # Пересобираем с именами колонок
    conn2 = sqlite3.connect(DB_PATH)
    conn2.row_factory = sqlite3.Row
    c2 = conn2.cursor()
    c2.execute("SELECT * FROM players WHERE telegram_id = ?", (telegram_id,))
    row2 = c2.fetchone()
    conn2.close()
    if row2:
        return dict(row2)
    return None

def calc_energy(player: dict) -> int:
    """Вычисляет текущую энергию с учётом регенерации"""
    now = time.time()
    elapsed = now - player["last_energy_update"]
    regen = player["energy_regen"]
    restored = int(elapsed * regen)
    new_energy = min(player["max_energy"], player["energy"] + restored)
    return new_energy

def xp_for_level(level: int) -> int:
    """XP необходимый для следующего уровня"""
    return level * 100

def calc_level(xp: int) -> tuple:
    """Возвращает (уровень, текущий XP в уровне, нужно XP для апа)"""
    level = 1
    total = 0
    while True:
        needed = xp_for_level(level)
        if total + needed > xp:
            break
        total += needed
        level += 1
    return level, xp - total, xp_for_level(level)

# ─── Данные профессий ────────────────────────────────────────────────────────
PROFESSIONS_DATA = {
    "frontend": {
        "id": "frontend", "name": "Frontend-разработчик",
        "sphere": "it", "sphere_name": "IT-сфера",
        "icon": "💻", "cost": 1,
        "description": "Создаёт интерфейсы сайтов и приложений — то, что видит пользователь.",
        "tools": ["HTML/CSS", "JavaScript", "React", "Figma", "Git"],
        "tasks": [
            {"title": "Вёрстка макета", "type": "layout_puzzle",
             "desc": "Расставь CSS-свойства чтобы получить нужный макет"},
            {"title": "JS-баг", "type": "bug_fix",
             "desc": "Найди и исправь ошибку в JavaScript-коде"},
            {"title": "Адаптив", "type": "media_query",
             "desc": "Сделай сайт адаптивным для мобильных"},
            {"title": "Цветовая схема", "type": "color_picker",
             "desc": "Подбери правильную цветовую схему по ТЗ"},
            {"title": "Оптимизация", "type": "performance",
             "desc": "Оптимизируй загрузку страницы"}
        ]
    },
    "backend": {
        "id": "backend", "name": "Backend-разработчик",
        "sphere": "it", "sphere_name": "IT-сфера",
        "icon": "⚙️", "cost": 1,
        "description": "Создаёт серверную логику, базы данных и API.",
        "tools": ["Python", "SQL", "REST API", "Docker", "PostgreSQL"],
        "tasks": [
            {"title": "SQL-запрос", "type": "sql_puzzle",
             "desc": "Напиши правильный SQL-запрос для выборки данных"},
            {"title": "API-эндпоинт", "type": "api_design",
             "desc": "Спроектируй REST API для задачи"},
            {"title": "Оптимизация БД", "type": "db_optimize",
             "desc": "Найди проблему в работе с базой данных"},
            {"title": "Безопасность", "type": "security",
             "desc": "Найди уязвимость в коде"},
            {"title": "Рефакторинг", "type": "refactor",
             "desc": "Улучши структуру кода"}
        ]
    },
    "datasci": {
        "id": "datasci", "name": "Data Scientist",
        "sphere": "it", "sphere_name": "IT-сфера",
        "icon": "📊", "cost": 2,
        "description": "Анализирует большие данные и строит предсказательные модели.",
        "tools": ["Python", "pandas", "scikit-learn", "Jupyter", "Tableau"],
        "tasks": [
            {"title": "Анализ данных", "type": "data_analysis",
             "desc": "Найди закономерность в таблице данных"},
            {"title": "Визуализация", "type": "chart_reading",
             "desc": "Интерпретируй график и сделай вывод"},
            {"title": "Предсказание", "type": "prediction",
             "desc": "Предскажи значение по тренду данных"},
            {"title": "Очистка данных", "type": "data_cleaning",
             "desc": "Найди и исправь аномалии в датасете"},
            {"title": "Гипотеза", "type": "hypothesis",
             "desc": "Сформулируй и проверь гипотезу"}
        ]
    },
    "robotics": {
        "id": "robotics", "name": "Инженер-робототехник",
        "sphere": "engineering", "sphere_name": "Инженерия",
        "icon": "🤖", "cost": 1,
        "description": "Проектирует и программирует роботизированные системы.",
        "tools": ["CAD", "Arduino", "Python", "ROS", "3D-печать"],
        "tasks": [
            {"title": "Схема робота", "type": "circuit_puzzle",
             "desc": "Собери правильную схему из компонентов"},
            {"title": "Алгоритм движения", "type": "path_planning",
             "desc": "Запрограммируй маршрут робота"},
            {"title": "Сенсоры", "type": "sensor_config",
             "desc": "Настрой датчики для задачи"},
            {"title": "Механика", "type": "mechanics",
             "desc": "Выбери правильную конфигурацию механизма"},
            {"title": "Тест-кейс", "type": "testing",
             "desc": "Протестируй и найди баг в поведении робота"}
        ]
    },
    "surgeon": {
        "id": "surgeon", "name": "Хирург",
        "sphere": "medicine", "sphere_name": "Медицина",
        "icon": "🏥", "cost": 2,
        "description": "Проводит операции для лечения заболеваний и травм.",
        "tools": ["Скальпель", "Лапароскоп", "Мониторинг", "Анестезия", "ИВЛ"],
        "tasks": [
            {"title": "Диагноз", "type": "diagnosis",
             "desc": "Поставь диагноз по симптомам пациента"},
            {"title": "Операция", "type": "operation_sim",
             "desc": "Выполни последовательность хирургических действий"},
            {"title": "Экстренная помощь", "type": "emergency",
             "desc": "Прими правильное решение в экстренной ситуации"},
            {"title": "Анализы", "type": "lab_results",
             "desc": "Интерпретируй результаты анализов"},
            {"title": "Реабилитация", "type": "rehab_plan",
             "desc": "Составь план реабилитации пациента"}
        ]
    },
    "gamedev": {
        "id": "gamedev", "name": "Геймдев разработчик",
        "sphere": "creative", "sphere_name": "Творчество",
        "icon": "🎮", "cost": 1,
        "description": "Создаёт видеоигры — от идеи до релиза.",
        "tools": ["Unity", "Unreal", "C#", "Blender", "GitHub"],
        "tasks": [
            {"title": "Геймдизайн", "type": "game_design",
             "desc": "Спроектируй игровую механику"},
            {"title": "Баланс", "type": "balance",
             "desc": "Сбалансируй характеристики персонажей"},
            {"title": "Уровень", "type": "level_design",
             "desc": "Расставь препятствия на уровне"},
            {"title": "UI/UX игры", "type": "game_ui",
             "desc": "Улучши интерфейс игры"},
            {"title": "Монетизация", "type": "monetization",
             "desc": "Выбери правильную модель монетизации"}
        ]
    },
    "marketing": {
        "id": "marketing", "name": "Маркетолог",
        "sphere": "business", "sphere_name": "Бизнес",
        "icon": "📈", "cost": 1,
        "description": "Продвигает продукты и услуги, привлекает клиентов.",
        "tools": ["Яндекс.Метрика", "VK Ads", "Telegram", "Canva", "Excel"],
        "tasks": [
            {"title": "Целевая аудитория", "type": "target_audience",
             "desc": "Определи ЦА для продукта"},
            {"title": "Рекламный текст", "type": "copywriting",
             "desc": "Напиши продающий заголовок"},
            {"title": "A/B тест", "type": "ab_test",
             "desc": "Выбери лучший вариант по метрикам"},
            {"title": "Бюджет", "type": "budget_alloc",
             "desc": "Распредели маркетинговый бюджет"},
            {"title": "Аналитика", "type": "analytics",
             "desc": "Интерпретируй данные о конверсии"}
        ]
    },
    "chemist": {
        "id": "chemist", "name": "Химик-исследователь",
        "sphere": "science", "sphere_name": "Наука",
        "icon": "⚗️", "cost": 2,
        "description": "Проводит эксперименты и создаёт новые материалы и вещества.",
        "tools": ["Спектрометр", "Хроматограф", "Реактивы", "Python", "ChemDraw"],
        "tasks": [
            {"title": "Уравнение реакции", "type": "chem_equation",
             "desc": "Расставь коэффициенты в химическом уравнении"},
            {"title": "Эксперимент", "type": "experiment",
             "desc": "Выбери правильный порядок действий в опыте"},
            {"title": "Анализ", "type": "chem_analysis",
             "desc": "Определи вещество по спектру"},
            {"title": "Безопасность", "type": "lab_safety",
             "desc": "Найди нарушения техники безопасности"},
            {"title": "Синтез", "type": "synthesis",
             "desc": "Спланируй синтез целевого вещества"}
        ]
    }
}

SPHERES = {
    "it": {"name": "IT-сфера", "icon": "💻", "color": "#00ff88"},
    "engineering": {"name": "Инженерия", "icon": "🤖", "color": "#ff8800"},
    "medicine": {"name": "Медицина", "icon": "🏥", "color": "#ff4488"},
    "creative": {"name": "Творчество", "icon": "🎮", "color": "#aa44ff"},
    "business": {"name": "Бизнес", "icon": "📈", "color": "#ffdd00"},
    "science": {"name": "Наука", "icon": "⚗️", "color": "#44ddff"},
}

# ─── Таблица улучшений ────────────────────────────────────────────────────────
UPGRADES = {
    "tap_power_1": {"name": "Сила пальцев I", "desc": "+1 монета за тап", "cost": 50, "effect": "tap_power", "value": 1},
    "tap_power_2": {"name": "Сила пальцев II", "desc": "+2 монеты за тап", "cost": 200, "effect": "tap_power", "value": 2},
    "tap_power_3": {"name": "Сила пальцев III", "desc": "+3 монеты за тап", "cost": 500, "effect": "tap_power", "value": 3},
    "energy_1": {"name": "Выносливость I", "desc": "+20 макс. энергии", "cost": 75, "effect": "max_energy", "value": 20},
    "energy_2": {"name": "Выносливость II", "desc": "+40 макс. энергии", "cost": 300, "effect": "max_energy", "value": 40},
    "regen_1": {"name": "Авто-восстановление I", "desc": "+1 ед/сек регенерации", "cost": 100, "effect": "energy_regen", "value": 1.0},
    "regen_2": {"name": "Авто-восстановление II", "desc": "+2 ед/сек регенерации", "cost": 400, "effect": "energy_regen", "value": 2.0},
    "multitap": {"name": "Мультитап", "desc": "х2 монеты при серии тапов", "cost": 150, "effect": "tap_multiplier", "value": 2},
}

# ─── Lifespan ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

# ─── Создание приложения ──────────────────────────────────────────────────────
app = FastAPI(title="RE:ALITY API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Эндпоинты ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_app():
    """Отдаём главный HTML"""
    html = build_html()
    return HTMLResponse(content=html)

@app.get("/api/player/{telegram_id}")
async def get_player_api(telegram_id: str):
    player = get_player(telegram_id)
    if not player:
        return JSONResponse({"exists": False})
    # Обновляем энергию
    current_energy = calc_energy(player)
    level, xp_cur, xp_need = calc_level(player["xp"])
    return JSONResponse({
        "exists": True,
        "player": {**player,
                   "energy": current_energy,
                   "level": level,
                   "xp_current": xp_cur,
                   "xp_needed": xp_need,
                   "upgrades": json.loads(player["upgrades"]),
                   "opened_professions": json.loads(player["opened_professions"]),
                   "completed_tasks": json.loads(player["completed_tasks"]),
                   }
    })

@app.post("/api/player/create")
async def create_player(req: CreatePlayerRequest):
    # Проверяем, что сумма характеристик = 20
    total = req.stat_strength + req.stat_intel + req.stat_charisma + req.stat_luck
    if total != 20:
        raise HTTPException(400, "Сумма характеристик должна быть 20")
    if len(req.name) > 8:
        raise HTTPException(400, "Имя не более 8 символов")
    if req.avatar not in [1, 2, 3]:
        raise HTTPException(400, "Неверный аватар")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = time.time()
    try:
        c.execute("""
            INSERT INTO players
            (telegram_id, name, avatar, level, xp, coins, tokens, energy, max_energy,
             last_energy_update, stat_strength, stat_intel, stat_charisma, stat_luck,
             tap_power, energy_regen, created_at, upgrades, opened_professions, completed_tasks)
            VALUES (?,?,?,1,0,10,1,100,100,?,?,?,?,?,1,2.0,?,?,?,?)
        """, (
            req.telegram_id, req.name, req.avatar, now,
            req.stat_strength, req.stat_intel, req.stat_charisma, req.stat_luck,
            now, '{}', '[]', '{}'
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(400, "Игрок уже существует")
    finally:
        conn.close()
    return JSONResponse({"ok": True})

@app.post("/api/tap")
async def process_tap(req: TapRequest):
    """Обработка тапов с античитом"""
    player = get_player(req.telegram_id)
    if not player:
        raise HTTPException(404, "Игрок не найден")

    now = time.time()
    
    # Античит: не более 30 тапов за секунду
    if req.taps > 30:
        req.taps = 30

    # Обновляем энергию
    current_energy = calc_energy(player)
    
    # Проверяем энергию
    actual_taps = min(req.taps, current_energy)
    if actual_taps <= 0:
        return JSONResponse({"ok": True, "energy": 0, "coins": player["coins"], "xp": player["xp"]})

    # Комбо-система
    time_since_last = now - player["last_tap_time"]
    combo = player["combo_count"]
    if time_since_last < 2.0:
        combo = min(combo + actual_taps, 50)
    else:
        combo = actual_taps

    combo_multiplier = 1 + min(combo // 10, 4)  # до x5

    # Считаем монеты
    base_coins = player["tap_power"] * actual_taps
    luck_bonus = 1 + (player["stat_luck"] - 5) * 0.02  # ±2% за каждое очко
    coins_earned = int(base_coins * combo_multiplier * luck_bonus)

    # XP
    xp_earned = actual_taps * 2

    new_energy = current_energy - actual_taps
    new_coins = player["coins"] + coins_earned
    new_xp = player["xp"] + xp_earned
    new_total_taps = player["total_taps"] + actual_taps

    # Новый уровень?
    old_level = player["level"]
    new_level, xp_cur, xp_need = calc_level(new_xp)
    tokens_gained = max(0, new_level - old_level)
    new_tokens = player["tokens"] + tokens_gained

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE players SET
        coins = ?, xp = ?, energy = ?, last_energy_update = ?,
        combo_count = ?, last_tap_time = ?, total_taps = ?,
        level = ?, tokens = ?
        WHERE telegram_id = ?
    """, (new_coins, new_xp, new_energy, now,
          combo, now, new_total_taps,
          new_level, new_tokens,
          req.telegram_id))
    conn.commit()
    conn.close()

    return JSONResponse({
        "ok": True,
        "coins": new_coins,
        "xp": new_xp,
        "energy": new_energy,
        "coins_earned": coins_earned,
        "combo": combo,
        "combo_multiplier": combo_multiplier,
        "level": new_level,
        "xp_current": xp_cur,
        "xp_needed": xp_need,
        "tokens": new_tokens,
        "level_up": new_level > old_level,
    })

@app.post("/api/upgrade")
async def buy_upgrade(req: UpgradeRequest):
    player = get_player(req.telegram_id)
    if not player:
        raise HTTPException(404, "Игрок не найден")

    upgrade = UPGRADES.get(req.upgrade_id)
    if not upgrade:
        raise HTTPException(400, "Улучшение не найдено")

    upgrades_bought = json.loads(player["upgrades"])
    if req.upgrade_id in upgrades_bought:
        raise HTTPException(400, "Уже куплено")

    if player["coins"] < upgrade["cost"]:
        raise HTTPException(400, "Недостаточно монет")

    # Применяем эффект
    new_coins = player["coins"] - upgrade["cost"]
    effect = upgrade["effect"]
    value = upgrade["value"]

    update_fields = {"coins": new_coins}
    if effect == "tap_power":
        update_fields["tap_power"] = player["tap_power"] + value
    elif effect == "max_energy":
        update_fields["max_energy"] = player["max_energy"] + value
    elif effect == "energy_regen":
        update_fields["energy_regen"] = player["energy_regen"] + value
    elif effect == "tap_multiplier":
        update_fields["tap_multiplier"] = player["tap_multiplier"] + value

    upgrades_bought[req.upgrade_id] = True
    update_fields["upgrades"] = json.dumps(upgrades_bought)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    set_clause = ", ".join(f"{k} = ?" for k in update_fields)
    c.execute(
        f"UPDATE players SET {set_clause} WHERE telegram_id = ?",
        list(update_fields.values()) + [req.telegram_id]
    )
    conn.commit()
    conn.close()

    return JSONResponse({"ok": True, **update_fields})

@app.post("/api/profession/open")
async def open_profession(req: OpenProfessionRequest):
    player = get_player(req.telegram_id)
    if not player:
        raise HTTPException(404, "Игрок не найден")

    profession = PROFESSIONS_DATA.get(req.profession_id)
    if not profession:
        raise HTTPException(400, "Профессия не найдена")

    opened = json.loads(player["opened_professions"])
    if req.profession_id in opened:
        raise HTTPException(400, "Уже открыто")

    cost = profession["cost"]
    if player["tokens"] < cost:
        raise HTTPException(400, f"Нужно {cost} токенов")

    opened.append(req.profession_id)
    new_tokens = player["tokens"] - cost

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE players SET tokens = ?, opened_professions = ? WHERE telegram_id = ?",
        (new_tokens, json.dumps(opened), req.telegram_id)
    )
    conn.commit()
    conn.close()

    return JSONResponse({"ok": True, "tokens": new_tokens})

@app.post("/api/task/complete")
async def complete_task(req: CompleteTaskRequest):
    player = get_player(req.telegram_id)
    if not player:
        raise HTTPException(404, "Игрок не найден")

    profession = PROFESSIONS_DATA.get(req.profession_id)
    if not profession:
        raise HTTPException(400, "Профессия не найдена")

    opened = json.loads(player["opened_professions"])
    if req.profession_id not in opened:
        raise HTTPException(400, "Профессия не открыта")

    completed = json.loads(player["completed_tasks"])
    key = f"{req.profession_id}_{req.task_index}"
    if key in completed:
        return JSONResponse({"ok": True, "already_done": True})

    # Награда зависит от качества выполнения
    score_multiplier = max(0.5, req.score / 100)
    base_coins = 50 + req.task_index * 25
    base_xp = 100 + req.task_index * 50
    intel_bonus = 1 + (player["stat_intel"] - 5) * 0.03

    coins_earned = int(base_coins * score_multiplier * intel_bonus)
    xp_earned = int(base_xp * score_multiplier)

    completed[key] = {"score": req.score, "ts": time.time()}
    new_coins = player["coins"] + coins_earned
    new_xp = player["xp"] + xp_earned

    old_level = player["level"]
    new_level, xp_cur, xp_need = calc_level(new_xp)
    tokens_gained = max(0, new_level - old_level)
    new_tokens = player["tokens"] + tokens_gained

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE players SET coins=?, xp=?, level=?, tokens=?, completed_tasks=?
        WHERE telegram_id=?
    """, (new_coins, new_xp, new_level, new_tokens, json.dumps(completed), req.telegram_id))
    conn.commit()
    conn.close()

    return JSONResponse({
        "ok": True,
        "coins_earned": coins_earned,
        "xp_earned": xp_earned,
        "coins": new_coins,
        "xp": new_xp,
        "level": new_level,
        "tokens": new_tokens,
        "level_up": new_level > old_level,
    })

@app.get("/api/professions")
async def get_professions():
    return JSONResponse({
        "spheres": SPHERES,
        "professions": PROFESSIONS_DATA
    })

@app.get("/api/upgrades")
async def get_upgrades():
    return JSONResponse(UPGRADES)

# ─── HTML-фронтенд ────────────────────────────────────────────────────────────
def build_html() -> str:
    h1 = HERO_IMAGES.get(1, "")
    h2 = HERO_IMAGES.get(2, "")
    h3 = HERO_IMAGES.get(3, "")

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"/>
<title>RE:ALITY: Профессии</title>
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet"/>
<style>
:root{{
  --bg:#0a0a12;
  --bg2:#12121f;
  --bg3:#1a1a2e;
  --accent:#00ff88;
  --accent2:#ff6b35;
  --accent3:#a855f7;
  --gold:#ffd700;
  --red:#ff4444;
  --blue:#44aaff;
  --text:#e0e0ff;
  --text2:#8888aa;
  --border:#2a2a4a;
  --pixel:2px;
}}
*{{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}}
body{{
  font-family:'Press Start 2P',monospace;
  background:var(--bg);
  color:var(--text);
  max-width:400px;
  margin:0 auto;
  min-height:100vh;
  overflow-x:hidden;
  position:relative;
}}
/* Пиксельные рамки */
.pixel-border{{
  border:3px solid var(--accent);
  box-shadow:0 0 0 2px var(--bg),0 0 0 4px var(--accent),inset 0 0 0 2px var(--bg2);
  image-rendering:pixelated;
}}
.pixel-border-gold{{
  border:3px solid var(--gold);
  box-shadow:0 0 0 2px var(--bg),0 0 0 4px var(--gold);
}}
.pixel-border-red{{
  border:3px solid var(--red);
  box-shadow:0 0 0 2px var(--bg),0 0 0 4px var(--red);
}}

/* Кнопки */
.btn{{
  display:inline-block;
  padding:10px 16px;
  font-family:'Press Start 2P',monospace;
  font-size:9px;
  cursor:pointer;
  border:none;
  outline:none;
  text-transform:uppercase;
  letter-spacing:1px;
  transition:transform 0.1s,filter 0.1s;
  image-rendering:pixelated;
  user-select:none;
  -webkit-user-select:none;
}}
.btn:active{{transform:translateY(2px);filter:brightness(0.8)}}
.btn-green{{
  background:var(--accent);
  color:#000;
  box-shadow:0 4px 0 #007744,inset 0 1px 0 rgba(255,255,255,0.3);
}}
.btn-orange{{
  background:var(--accent2);
  color:#000;
  box-shadow:0 4px 0 #aa3300,inset 0 1px 0 rgba(255,255,255,0.3);
}}
.btn-purple{{
  background:var(--accent3);
  color:#fff;
  box-shadow:0 4px 0 #7722cc,inset 0 1px 0 rgba(255,255,255,0.3);
}}
.btn-gold{{
  background:var(--gold);
  color:#000;
  box-shadow:0 4px 0 #aa8800,inset 0 1px 0 rgba(255,255,255,0.3);
}}
.btn-red{{
  background:var(--red);
  color:#fff;
  box-shadow:0 4px 0 #aa0000;
}}
.btn-dark{{
  background:var(--bg3);
  color:var(--text);
  border:2px solid var(--border);
  box-shadow:0 3px 0 #000;
}}
.btn-full{{width:100%;display:block;text-align:center}}

/* Экраны */
.screen{{
  display:none;
  min-height:100vh;
  padding:16px;
  animation:fadeIn 0.3s ease;
}}
.screen.active{{display:block}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}

/* ── ЭКРАН РЕГИСТРАЦИИ ── */
#screen-register{{
  background:var(--bg);
  padding-bottom:80px;
}}
.register-title{{
  text-align:center;
  padding:20px 0 10px;
  font-size:14px;
  color:var(--accent);
  text-shadow:0 0 20px var(--accent),0 0 40px var(--accent);
  line-height:1.6;
}}
.register-subtitle{{
  text-align:center;
  font-size:7px;
  color:var(--text2);
  margin-bottom:24px;
}}
.avatar-grid{{
  display:flex;
  gap:12px;
  justify-content:center;
  margin-bottom:20px;
}}
.avatar-card{{
  width:100px;
  background:var(--bg2);
  border:3px solid var(--border);
  padding:8px;
  cursor:pointer;
  transition:all 0.15s;
  display:flex;
  flex-direction:column;
  align-items:center;
  gap:6px;
}}
.avatar-card img{{
  width:72px;
  height:auto;
  image-rendering:pixelated;
}}
.avatar-card.selected{{
  border-color:var(--accent);
  box-shadow:0 0 0 2px var(--bg),0 0 0 4px var(--accent),0 0 20px rgba(0,255,136,0.3);
  background:rgba(0,255,136,0.05);
}}
.avatar-card span{{
  font-size:6px;
  color:var(--text2);
}}
.input-group{{
  margin-bottom:16px;
}}
.input-label{{
  display:block;
  font-size:8px;
  color:var(--text2);
  margin-bottom:6px;
}}
.pixel-input{{
  width:100%;
  background:var(--bg2);
  border:3px solid var(--border);
  color:var(--text);
  font-family:'Press Start 2P',monospace;
  font-size:11px;
  padding:10px 12px;
  outline:none;
  transition:border-color 0.2s;
}}
.pixel-input:focus{{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}}

/* Статы */
.stats-header{{
  font-size:8px;
  color:var(--accent);
  margin-bottom:8px;
}}
.stats-points{{
  font-size:8px;
  color:var(--gold);
  text-align:right;
  margin-bottom:10px;
}}
.stat-row{{
  display:flex;
  align-items:center;
  gap:8px;
  margin-bottom:10px;
}}
.stat-name{{
  font-size:7px;
  width:80px;
  color:var(--text2);
}}
.stat-bar{{
  flex:1;
  height:12px;
  background:var(--bg3);
  border:2px solid var(--border);
  position:relative;
  overflow:hidden;
}}
.stat-bar-fill{{
  height:100%;
  background:var(--accent);
  transition:width 0.2s;
  image-rendering:pixelated;
}}
.stat-controls{{
  display:flex;
  gap:4px;
}}
.stat-btn{{
  width:24px;
  height:24px;
  background:var(--bg3);
  border:2px solid var(--border);
  color:var(--text);
  font-family:'Press Start 2P',monospace;
  font-size:12px;
  cursor:pointer;
  display:flex;
  align-items:center;
  justify-content:center;
  line-height:1;
  padding-bottom:2px;
}}
.stat-btn:active{{background:var(--accent);color:#000}}
.stat-value{{
  font-size:9px;
  color:var(--text);
  width:20px;
  text-align:center;
}}

/* ── ГЛАВНЫЙ ЭКРАН ── */
#screen-main{{
  padding:0 0 80px;
  background:var(--bg);
}}
.top-bar{{
  background:var(--bg2);
  border-bottom:3px solid var(--border);
  padding:10px 14px;
  display:flex;
  align-items:center;
  gap:10px;
}}
.player-avatar-sm{{
  width:36px;
  height:36px;
  border:2px solid var(--accent);
  overflow:hidden;
  background:var(--bg3);
  flex-shrink:0;
}}
.player-avatar-sm img{{
  width:100%;
  height:100%;
  object-fit:cover;
  object-position:top;
  image-rendering:pixelated;
}}
.player-info{{flex:1;min-width:0}}
.player-name{{
  font-size:9px;
  color:var(--accent);
  margin-bottom:4px;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}}
.level-row{{
  display:flex;
  align-items:center;
  gap:6px;
}}
.level-badge{{
  background:var(--accent3);
  color:#fff;
  font-size:7px;
  padding:2px 6px;
  flex-shrink:0;
}}
.xp-bar-wrap{{
  flex:1;
  height:8px;
  background:var(--bg3);
  border:2px solid var(--border);
}}
.xp-bar-fill{{
  height:100%;
  background:linear-gradient(90deg,var(--accent3),var(--blue));
  transition:width 0.5s ease;
}}
.xp-text{{
  font-size:6px;
  color:var(--text2);
  white-space:nowrap;
}}

/* Ресурсы */
.resources-bar{{
  display:flex;
  gap:8px;
  padding:10px 14px;
  background:var(--bg2);
  border-bottom:3px solid var(--border);
}}
.resource{{
  flex:1;
  background:var(--bg3);
  border:2px solid var(--border);
  padding:6px 8px;
  display:flex;
  flex-direction:column;
  gap:3px;
}}
.resource-icon{{font-size:14px;line-height:1}}
.resource-val{{
  font-size:9px;
  color:var(--gold);
}}
.resource-label{{
  font-size:5px;
  color:var(--text2);
  text-transform:uppercase;
}}

/* Зона тапалки */
.tap-zone{{
  padding:20px 14px;
  display:flex;
  flex-direction:column;
  align-items:center;
  gap:16px;
}}
.combo-display{{
  height:24px;
  display:flex;
  align-items:center;
  justify-content:center;
}}
.combo-badge{{
  background:var(--accent2);
  color:#000;
  font-size:8px;
  padding:4px 10px;
  display:none;
  animation:comboPop 0.3s ease;
}}
.combo-badge.show{{display:block}}
@keyframes comboPop{{
  0%{{transform:scale(0.5)}}
  70%{{transform:scale(1.2)}}
  100%{{transform:scale(1)}}
}}

.character-wrap{{
  position:relative;
  width:160px;
  height:200px;
  cursor:pointer;
  display:flex;
  align-items:flex-end;
  justify-content:center;
}}
.character-img{{
  width:120px;
  image-rendering:pixelated;
  animation:breathe 2s ease-in-out infinite;
  transition:transform 0.1s;
  user-select:none;
  -webkit-user-select:none;
  pointer-events:none;
}}
@keyframes breathe{{
  0%,100%{{transform:scaleY(1) translateY(0)}}
  50%{{transform:scaleY(1.03) translateY(-3px)}}
}}
.character-wrap:active .character-img{{
  transform:scale(0.92) translateY(4px)!important;
  animation:none!important;
}}
.tap-ring{{
  position:absolute;
  width:160px;
  height:160px;
  border:3px solid var(--accent);
  border-radius:50%;
  top:50%;left:50%;
  transform:translate(-50%,-50%);
  opacity:0;
  pointer-events:none;
  animation:none;
}}
.tap-ring.flash{{
  animation:ringFlash 0.4s ease forwards;
}}
@keyframes ringFlash{{
  0%{{opacity:0.8;transform:translate(-50%,-50%) scale(0.8)}}
  100%{{opacity:0;transform:translate(-50%,-50%) scale(1.5)}}
}}

/* Всплывающие монеты */
.coin-float{{
  position:fixed;
  font-size:11px;
  color:var(--gold);
  pointer-events:none;
  z-index:999;
  animation:floatUp 0.8s ease forwards;
  font-family:'Press Start 2P',monospace;
  text-shadow:0 0 10px var(--gold);
}}
@keyframes floatUp{{
  0%{{opacity:1;transform:translateY(0) scale(1)}}
  100%{{opacity:0;transform:translateY(-60px) scale(0.7)}}
}}

/* Энергия */
.energy-wrap{{
  width:100%;
  padding:0 14px;
}}
.energy-label{{
  font-size:7px;
  color:var(--text2);
  margin-bottom:5px;
  display:flex;
  justify-content:space-between;
}}
.energy-bar-bg{{
  width:100%;
  height:14px;
  background:var(--bg3);
  border:3px solid var(--border);
  overflow:hidden;
  position:relative;
}}
.energy-bar-fill{{
  height:100%;
  background:linear-gradient(90deg,#00aaff,#00ffaa);
  transition:width 0.3s;
  position:relative;
}}
.energy-bar-fill::after{{
  content:'';
  position:absolute;
  top:0;left:0;right:0;
  height:4px;
  background:rgba(255,255,255,0.3);
}}

/* Нижняя навигация */
.nav-bar{{
  position:fixed;
  bottom:0;left:50%;
  transform:translateX(-50%);
  width:100%;
  max-width:400px;
  background:var(--bg2);
  border-top:3px solid var(--border);
  display:flex;
  z-index:100;
}}
.nav-btn{{
  flex:1;
  padding:12px 8px;
  font-family:'Press Start 2P',monospace;
  font-size:7px;
  background:transparent;
  border:none;
  color:var(--text2);
  cursor:pointer;
  display:flex;
  flex-direction:column;
  align-items:center;
  gap:5px;
  transition:color 0.2s,background 0.2s;
}}
.nav-btn .nav-icon{{font-size:18px;line-height:1}}
.nav-btn.active{{
  color:var(--accent);
  background:rgba(0,255,136,0.05);
}}
.nav-btn:active{{background:rgba(0,255,136,0.1)}}

/* ── ЭКРАН ПРОФЕССИЙ ── */
#screen-professions{{
  padding:0 0 80px;
}}
.screen-header{{
  background:var(--bg2);
  border-bottom:3px solid var(--border);
  padding:14px 16px;
  display:flex;
  align-items:center;
  gap:10px;
}}
.screen-title{{
  font-size:11px;
  color:var(--accent);
}}
.sphere-grid{{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:12px;
  padding:16px;
}}
.sphere-card{{
  background:var(--bg2);
  border:3px solid var(--border);
  padding:14px;
  cursor:pointer;
  transition:all 0.15s;
  display:flex;
  flex-direction:column;
  align-items:center;
  gap:8px;
  text-align:center;
}}
.sphere-card:active{{transform:scale(0.96)}}
.sphere-icon{{font-size:28px;line-height:1}}
.sphere-name{{font-size:7px;color:var(--text)}}
.sphere-count{{font-size:6px;color:var(--text2)}}

/* Список профессий в сфере */
.prof-list{{
  padding:16px;
  display:flex;
  flex-direction:column;
  gap:10px;
}}
.prof-card{{
  background:var(--bg2);
  border:3px solid var(--border);
  padding:12px;
  cursor:pointer;
  transition:all 0.15s;
  display:flex;
  align-items:center;
  gap:12px;
}}
.prof-card.opened{{
  border-color:var(--accent);
  background:rgba(0,255,136,0.03);
}}
.prof-card:active{{transform:scale(0.98)}}
.prof-card-icon{{font-size:24px;flex-shrink:0}}
.prof-card-info{{flex:1;min-width:0}}
.prof-card-name{{font-size:8px;color:var(--text);margin-bottom:4px}}
.prof-card-desc{{font-size:6px;color:var(--text2);line-height:1.5}}
.prof-card-badge{{
  font-size:6px;
  padding:3px 6px;
  flex-shrink:0;
}}
.badge-open{{background:var(--accent);color:#000}}
.badge-locked{{background:var(--border);color:var(--text2)}}

/* Детали профессии */
.prof-detail{{
  padding:16px;
}}
.prof-detail-header{{
  display:flex;
  align-items:center;
  gap:12px;
  margin-bottom:16px;
  background:var(--bg2);
  border:3px solid var(--border);
  padding:12px;
}}
.prof-detail-icon{{font-size:36px}}
.prof-detail-name{{font-size:10px;color:var(--accent);margin-bottom:4px}}
.prof-detail-sphere{{font-size:6px;color:var(--text2)}}
.prof-detail-desc{{
  font-size:7px;
  color:var(--text);
  line-height:1.8;
  margin-bottom:16px;
}}
.tools-list{{
  display:flex;
  flex-wrap:wrap;
  gap:6px;
  margin-bottom:16px;
}}
.tool-tag{{
  background:var(--bg3);
  border:2px solid var(--border);
  padding:4px 8px;
  font-size:6px;
  color:var(--text2);
}}
.task-list{{
  display:flex;
  flex-direction:column;
  gap:8px;
}}
.task-item{{
  background:var(--bg2);
  border:2px solid var(--border);
  padding:10px 12px;
  display:flex;
  align-items:center;
  gap:10px;
  cursor:pointer;
  transition:all 0.15s;
}}
.task-item.done{{
  border-color:var(--accent);
  opacity:0.7;
}}
.task-item.locked{{
  opacity:0.4;
  cursor:not-allowed;
}}
.task-item:not(.done):not(.locked):active{{transform:scale(0.98)}}
.task-num{{
  font-size:8px;
  color:var(--text2);
  width:20px;
  flex-shrink:0;
}}
.task-name{{font-size:8px;color:var(--text);flex:1}}
.task-status{{font-size:10px}}

/* ── ЭКРАН УЛУЧШЕНИЙ ── */
#screen-upgrades{{
  padding:0 0 80px;
}}
.upgrades-list{{
  padding:16px;
  display:flex;
  flex-direction:column;
  gap:10px;
}}
.upgrade-card{{
  background:var(--bg2);
  border:3px solid var(--border);
  padding:12px;
  display:flex;
  gap:12px;
  align-items:center;
}}
.upgrade-card.bought{{
  border-color:var(--accent);
  opacity:0.6;
}}
.upgrade-icon{{font-size:24px;flex-shrink:0}}
.upgrade-info{{flex:1}}
.upgrade-name{{font-size:8px;color:var(--text);margin-bottom:4px}}
.upgrade-desc{{font-size:6px;color:var(--text2);margin-bottom:6px}}
.upgrade-cost{{
  font-size:8px;
  color:var(--gold);
}}
.upgrade-cost span{{color:var(--text2)}}

/* ── МИНИ-ИГРЫ ── */
.minigame-wrap{{
  position:fixed;
  top:0;left:50%;
  transform:translateX(-50%);
  width:100%;
  max-width:400px;
  height:100vh;
  background:var(--bg);
  z-index:200;
  display:none;
  flex-direction:column;
  overflow-y:auto;
  padding-bottom:20px;
}}
.minigame-wrap.active{{display:flex}}
.minigame-header{{
  background:var(--bg2);
  border-bottom:3px solid var(--border);
  padding:14px 16px;
  display:flex;
  align-items:center;
  gap:10px;
  flex-shrink:0;
}}
.mg-close{{
  background:var(--red);
  color:#fff;
  border:none;
  font-family:'Press Start 2P',monospace;
  font-size:8px;
  padding:6px 10px;
  cursor:pointer;
}}
.mg-title{{
  flex:1;
  font-size:9px;
  color:var(--accent);
}}
.mg-body{{
  padding:16px;
  flex:1;
}}
.mg-desc{{
  font-size:7px;
  color:var(--text2);
  line-height:1.8;
  margin-bottom:16px;
  background:var(--bg2);
  border:2px solid var(--border);
  padding:12px;
}}

/* Мини-игра: CSS Layout Puzzle */
.layout-puzzle{{
  margin-bottom:12px;
}}
.lp-preview{{
  width:100%;
  height:80px;
  background:var(--bg3);
  border:2px solid var(--border);
  margin-bottom:10px;
  display:flex;
  align-items:center;
  justify-content:center;
  gap:6px;
  padding:8px;
  font-size:7px;
  color:var(--text2);
}}
.lp-options{{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:8px;
}}
.lp-option{{
  background:var(--bg2);
  border:2px solid var(--border);
  padding:8px;
  font-size:7px;
  color:var(--text2);
  cursor:pointer;
  transition:all 0.15s;
  font-family:'Press Start 2P',monospace;
  text-align:center;
}}
.lp-option.correct{{border-color:var(--accent);color:var(--accent)}}
.lp-option.wrong{{border-color:var(--red);color:var(--red)}}
.lp-option:hover{{border-color:var(--text2)}}

/* Мини-игра: найди баг */
.bug-code{{
  background:#000;
  border:2px solid var(--border);
  padding:12px;
  font-family:monospace;
  font-size:10px;
  line-height:1.8;
  margin-bottom:12px;
  white-space:pre;
  overflow-x:auto;
  color:#aaffaa;
}}
.bug-line{{
  cursor:pointer;
  padding:2px 4px;
  transition:background 0.15s;
  display:block;
}}
.bug-line:hover{{background:rgba(255,255,255,0.05)}}
.bug-line.selected{{background:rgba(255,100,100,0.2)}}
.bug-line.correct{{background:rgba(0,255,100,0.2);color:var(--accent)}}

/* Данные / таблица */
.data-table{{
  width:100%;
  border-collapse:collapse;
  font-size:7px;
  margin-bottom:12px;
}}
.data-table th{{
  background:var(--accent);
  color:#000;
  padding:5px 8px;
  text-align:left;
}}
.data-table td{{
  background:var(--bg2);
  border:1px solid var(--border);
  padding:5px 8px;
  color:var(--text2);
}}
.data-table tr.anomaly td{{
  color:var(--red);
  background:rgba(255,0,0,0.05);
}}

/* Шкала прогресса в мини-игре */
.mg-progress{{
  display:flex;
  gap:4px;
  margin-bottom:16px;
}}
.mg-dot{{
  width:12px;height:12px;
  border:2px solid var(--border);
  background:var(--bg3);
}}
.mg-dot.done{{
  background:var(--accent);
  border-color:var(--accent);
}}
.mg-dot.current{{
  background:var(--gold);
  border-color:var(--gold);
  animation:pulse 1s infinite;
}}
@keyframes pulse{{50%{{opacity:0.5}}}}

/* Результат мини-игры */
.mg-result{{
  text-align:center;
  padding:20px;
  display:none;
}}
.mg-result.show{{display:block}}
.result-score{{
  font-size:32px;
  margin-bottom:12px;
}}
.result-title{{
  font-size:10px;
  color:var(--accent);
  margin-bottom:8px;
}}
.result-rewards{{
  display:flex;
  gap:10px;
  justify-content:center;
  margin:12px 0;
}}
.reward-item{{
  background:var(--bg2);
  border:2px solid var(--border);
  padding:8px 12px;
  font-size:8px;
}}
.reward-item span{{color:var(--gold)}}

/* Модальные окна */
.modal-overlay{{
  position:fixed;
  top:0;left:0;right:0;bottom:0;
  background:rgba(0,0,0,0.85);
  z-index:300;
  display:none;
  align-items:center;
  justify-content:center;
  padding:20px;
}}
.modal-overlay.active{{display:flex}}
.modal{{
  background:var(--bg2);
  border:3px solid var(--accent);
  box-shadow:0 0 0 2px var(--bg),0 0 0 5px var(--accent),0 0 40px rgba(0,255,136,0.2);
  padding:20px;
  width:100%;
  max-width:340px;
  animation:modalPop 0.3s ease;
}}
@keyframes modalPop{{
  0%{{transform:scale(0.8);opacity:0}}
  100%{{transform:scale(1);opacity:1}}
}}
.modal-title{{
  font-size:10px;
  color:var(--accent);
  margin-bottom:12px;
  text-align:center;
}}
.modal-body{{
  font-size:7px;
  color:var(--text2);
  line-height:1.8;
  margin-bottom:16px;
  text-align:center;
}}
.modal-body strong{{color:var(--text)}}

/* Пиксельный задний фон */
.scanlines{{
  position:fixed;
  top:0;left:0;right:0;bottom:0;
  background:repeating-linear-gradient(
    0deg,
    rgba(0,0,0,0.03) 0px,
    rgba(0,0,0,0.03) 1px,
    transparent 1px,
    transparent 3px
  );
  pointer-events:none;
  z-index:1000;
}}

/* Экран загрузки */
#screen-loading{{
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  min-height:100vh;
  gap:20px;
}}
.loading-title{{
  font-size:16px;
  color:var(--accent);
  text-align:center;
  text-shadow:0 0 20px var(--accent);
  line-height:1.6;
}}
.loading-sub{{
  font-size:7px;
  color:var(--text2);
}}
.loading-bar-wrap{{
  width:200px;
  height:12px;
  border:3px solid var(--border);
}}
.loading-bar{{
  height:100%;
  background:var(--accent);
  width:0%;
  transition:width 0.1s;
}}
.pixel-logo{{
  font-size:12px;
  color:var(--text2);
  text-align:center;
}}

/* Токен иконка */
.token-icon{{
  display:inline-block;
  width:14px;height:14px;
  background:var(--accent3);
  vertical-align:middle;
  margin-right:2px;
  clip-path:polygon(50% 0%,100% 50%,50% 100%,0% 50%);
}}

/* Scroll */
::-webkit-scrollbar{{width:4px}}
::-webkit-scrollbar-track{{background:var(--bg)}}
::-webkit-scrollbar-thumb{{background:var(--border)}}

/* Мульти-тап */
.multitap-hint{{
  font-size:6px;
  color:var(--text2);
  text-align:center;
  margin-top:-10px;
}}

/* Инфо-бар */
.info-section-title{{
  font-size:8px;
  color:var(--text2);
  margin-bottom:10px;
  padding:0 16px;
  padding-top:14px;
}}

/* Бар сферы */
.back-btn{{
  background:var(--bg3);
  border:2px solid var(--border);
  color:var(--text2);
  font-family:'Press Start 2P',monospace;
  font-size:8px;
  padding:6px 10px;
  cursor:pointer;
}}
.back-btn:active{{opacity:0.7}}
</style>
</head>
<body>
<div class="scanlines"></div>

<!-- Загрузка -->
<div id="screen-loading" class="screen active">
  <div class="loading-title">RE:ALITY</div>
  <div class="pixel-logo">⚔ ПРОФЕССИИ ⚔</div>
  <div class="loading-sub">загружаем мир...</div>
  <div class="loading-bar-wrap">
    <div class="loading-bar" id="loading-bar"></div>
  </div>
</div>

<!-- Регистрация -->
<div id="screen-register" class="screen">
  <div class="register-title">RE:ALITY<br/>ПРОФЕССИИ</div>
  <div class="register-subtitle">Выбери своего героя и начни путь!</div>

  <div style="padding:0 16px">
    <div class="input-label">ВЫБЕРИ АВАТАР:</div>
    <div class="avatar-grid" id="avatar-grid">
      <div class="avatar-card" data-avatar="1" onclick="selectAvatar(1)">
        <img src="{h2}" alt="hero1" id="av-img-1"/>
        <span>ГЕРОЙ</span>
      </div>
      <div class="avatar-card" data-avatar="2" onclick="selectAvatar(2)">
        <img src="{h3}" alt="hero2" id="av-img-2"/>
        <span>СТРАТЕГ</span>
      </div>
      <div class="avatar-card" data-avatar="3" onclick="selectAvatar(3)">
        <img src="{h1}" alt="hero3" id="av-img-3"/>
        <span>ПРОФИ</span>
      </div>
    </div>

    <div class="input-group">
      <label class="input-label" for="name-input">ИМЯ (макс 8 символов):</label>
      <input id="name-input" class="pixel-input" type="text" maxlength="8"
             placeholder="PLAYER" oninput="this.value=this.value.toUpperCase()"/>
    </div>

    <div class="stats-header">ХАРАКТЕРИСТИКИ</div>
    <div class="stats-points" id="points-left">ОЧКОВ ОСТАЛОСЬ: <span>5</span></div>
    <div id="stats-container">
      <div class="stat-row">
        <span class="stat-name">💪 СИЛА</span>
        <div class="stat-bar"><div class="stat-bar-fill" id="bar-strength" style="width:25%"></div></div>
        <div class="stat-controls">
          <button class="stat-btn" onclick="changeStat('strength',-1)">-</button>
          <span class="stat-value" id="val-strength">5</span>
          <button class="stat-btn" onclick="changeStat('strength',1)">+</button>
        </div>
      </div>
      <div class="stat-row">
        <span class="stat-name">🧠 ИНТЕЛ</span>
        <div class="stat-bar"><div class="stat-bar-fill" id="bar-intel" style="width:25%"></div></div>
        <div class="stat-controls">
          <button class="stat-btn" onclick="changeStat('intel',-1)">-</button>
          <span class="stat-value" id="val-intel">5</span>
          <button class="stat-btn" onclick="changeStat('intel',1)">+</button>
        </div>
      </div>
      <div class="stat-row">
        <span class="stat-name">💬 ХАРИЗ</span>
        <div class="stat-bar"><div class="stat-bar-fill" id="bar-charisma" style="width:25%"></div></div>
        <div class="stat-controls">
          <button class="stat-btn" onclick="changeStat('charisma',-1)">-</button>
          <span class="stat-value" id="val-charisma">5</span>
          <button class="stat-btn" onclick="changeStat('charisma',1)">+</button>
        </div>
      </div>
      <div class="stat-row">
        <span class="stat-name">🍀 УДАЧА</span>
        <div class="stat-bar"><div class="stat-bar-fill" id="bar-luck" style="width:25%"></div></div>
        <div class="stat-controls">
          <button class="stat-btn" onclick="changeStat('luck',-1)">-</button>
          <span class="stat-value" id="val-luck">5</span>
          <button class="stat-btn" onclick="changeStat('luck',1)">+</button>
        </div>
      </div>
    </div>

    <div style="margin-top:20px;margin-bottom:40px">
      <button class="btn btn-green btn-full" onclick="createPlayer()">▶ НАЧАТЬ ПУТЬ</button>
    </div>
  </div>
</div>

<!-- Главный экран (тапалка) -->
<div id="screen-main" class="screen">
  <div class="top-bar">
    <div class="player-avatar-sm">
      <img id="main-avatar" src="" alt="avatar"/>
    </div>
    <div class="player-info">
      <div class="player-name" id="main-name">PLAYER</div>
      <div class="level-row">
        <div class="level-badge">LVL <span id="main-level">1</span></div>
        <div class="xp-bar-wrap">
          <div class="xp-bar-fill" id="main-xp-bar" style="width:0%"></div>
        </div>
        <div class="xp-text"><span id="main-xp-cur">0</span>/<span id="main-xp-need">100</span></div>
      </div>
    </div>
  </div>

  <div class="resources-bar">
    <div class="resource">
      <div class="resource-icon">🪙</div>
      <div class="resource-val" id="main-coins">0</div>
      <div class="resource-label">МОНЕТЫ</div>
    </div>
    <div class="resource">
      <div class="resource-icon" style="color:var(--accent3)">◆</div>
      <div class="resource-val" id="main-tokens" style="color:var(--accent3)">0</div>
      <div class="resource-label">ТОКЕНЫ</div>
    </div>
    <div class="resource">
      <div class="resource-icon">⚡</div>
      <div class="resource-val" id="main-energy">100</div>
      <div class="resource-label">ЭНЕРГИЯ</div>
    </div>
  </div>

  <div class="tap-zone">
    <div class="combo-display">
      <div class="combo-badge" id="combo-badge">COMBO x1</div>
    </div>

    <div class="character-wrap" id="tap-area" ontouchstart="handleTap(event)" onclick="handleTapClick(event)">
      <img class="character-img" id="main-char" src="" alt="character"/>
      <div class="tap-ring" id="tap-ring"></div>
    </div>

    <div class="energy-wrap">
      <div class="energy-label">
        <span>⚡ ЭНЕРГИЯ</span>
        <span id="energy-label-val">100/100</span>
      </div>
      <div class="energy-bar-bg">
        <div class="energy-bar-fill" id="energy-bar" style="width:100%"></div>
      </div>
    </div>
    <div class="multitap-hint" id="tap-hint">ТАП ДЛЯ ЗАРАБОТКА МОНЕТ</div>
  </div>
</div>

<!-- Экран профессий -->
<div id="screen-professions" class="screen">
  <div class="screen-header">
    <button class="back-btn" id="prof-back-btn" onclick="profGoBack()" style="display:none">◀</button>
    <div class="screen-title" id="prof-screen-title">⚔ ПРОФЕССИИ</div>
    <div style="margin-left:auto;font-size:7px;color:var(--accent3)">
      ◆ <span id="prof-tokens">0</span> ТОКЕНОВ
    </div>
  </div>
  <div id="prof-content"></div>
</div>

<!-- Экран улучшений -->
<div id="screen-upgrades" class="screen">
  <div class="screen-header">
    <div class="screen-title">⚡ УЛУЧШЕНИЯ</div>
    <div style="margin-left:auto;font-size:7px;color:var(--gold)">
      🪙 <span id="upg-coins">0</span>
    </div>
  </div>
  <div class="info-section-title">ПРОКАЧАЙ СВОЕГО ГЕРОЯ</div>
  <div class="upgrades-list" id="upgrades-list"></div>
</div>

<!-- Мини-игра -->
<div class="minigame-wrap" id="minigame-wrap">
  <div class="minigame-header">
    <button class="mg-close" onclick="closeMinigame()">✕</button>
    <div class="mg-title" id="mg-title">ЗАДАНИЕ</div>
    <div id="mg-step-info" style="font-size:7px;color:var(--text2)"></div>
  </div>
  <div class="mg-body" id="mg-body"></div>
</div>

<!-- Модалки -->
<div class="modal-overlay" id="modal-levelup">
  <div class="modal">
    <div class="modal-title">🎉 НОВЫЙ УРОВЕНЬ!</div>
    <div class="modal-body" id="modal-levelup-body"></div>
    <button class="btn btn-green btn-full" onclick="closeModal('modal-levelup')">ОТЛИЧНО!</button>
  </div>
</div>

<div class="modal-overlay" id="modal-lvl2-hint">
  <div class="modal">
    <div class="modal-title">🔓 ТОКЕНЫ РАЗБЛОКИРОВАНЫ!</div>
    <div class="modal-body">
      Теперь ты можешь <strong>открывать профессии</strong> за токены!<br/><br/>
      Зарабатывай токены, повышая уровень, и исследуй реальные профессии.<br/><br/>
      <strong>Перейди в раздел ПРОФЕССИИ</strong> чтобы начать!
    </div>
    <button class="btn btn-green btn-full" onclick="closeModal('modal-lvl2-hint')">ПОНЯЛ!</button>
  </div>
</div>

<div class="modal-overlay" id="modal-task-result">
  <div class="modal">
    <div class="modal-title" id="task-result-title">✅ ЗАДАНИЕ ВЫПОЛНЕНО!</div>
    <div class="mg-result show" id="task-result-body"></div>
    <button class="btn btn-green btn-full" onclick="closeModal('modal-task-result')">ПРОДОЛЖИТЬ</button>
  </div>
</div>

<!-- Навигация -->
<nav class="nav-bar" id="nav-bar" style="display:none">
  <button class="nav-btn active" id="nav-main" onclick="navigate('main')">
    <span class="nav-icon">🏠</span>
    ГЛАВНАЯ
  </button>
  <button class="nav-btn" id="nav-professions" onclick="navigate('professions')">
    <span class="nav-icon">⚔</span>
    ПРОФЕССИИ
  </button>
  <button class="nav-btn" id="nav-upgrades" onclick="navigate('upgrades')">
    <span class="nav-icon">⚡</span>
    ПРОКАЧКА
  </button>
</nav>

<script>
// ──────────────────────────────────────────────────────────────────────
// ГЛОБАЛЬНОЕ СОСТОЯНИЕ
// ──────────────────────────────────────────────────────────────────────
const HERO_IMGS = {{
  1: "{h2}",
  2: "{h3}",
  3: "{h1}"
}};

let player = null;
let gameLoopInterval = null;
let energyUpdateInterval = null;
let tapQueue = 0;
let tapSendTimeout = null;
let comboTimer = null;
let telegramId = "dev_" + Math.random().toString(36).substr(2,8);

// Данные профессий (локальная копия)
let professionsData = {{}};
let spheresData = {{}};
let upgradesData = {{}};

// Навигация профессий
let profView = 'spheres'; // spheres | list | detail
let currentSphere = null;
let currentProfession = null;

// Состояние мини-игры
let currentTask = null;
let mgScore = 0;
let mgAnswered = false;

// ──────────────────────────────────────────────────────────────────────
// ИНИЦИАЛИЗАЦИЯ
// ──────────────────────────────────────────────────────────────────────
// Безопасный fetch с таймаутом (мс)
// Таймаут через Promise.race — надёжнее чем AbortController
// ──────────────────────────────────────────────────────────────────────
// ИНИЦИАЛИЗАЦИЯ — неблокирующая загрузка
// Логика: показываем бар 2 сек → переходим → грузим данные в фоне
// ──────────────────────────────────────────────────────────────────────

function sleep(ms) {{
  return new Promise(r => setTimeout(r, ms));
}}

// Безопасный fetch — никогда не бросает исключение, возвращает null при ошибке
async function fetchSafe(url, opts={{}}) {{
  return new Promise(resolve => {{
    const timer = setTimeout(() => resolve(null), 6000);
    fetch(url, opts)
      .then(r => {{ clearTimeout(timer); resolve(r); }})
      .catch(() => {{ clearTimeout(timer); resolve(null); }});
  }});
}}

window.addEventListener('DOMContentLoaded', () => {{
  // Telegram ID
  try {{
    if (window.Telegram?.WebApp) {{
      const tg = window.Telegram.WebApp;
      tg.ready(); tg.expand();
      const uid = tg.initDataUnsafe?.user?.id;
      if (uid) telegramId = String(uid);
    }}
  }} catch(e) {{}}

  // Анимируем прогресс-бар за 2 секунды, потом переходим
  const bar = document.getElementById('loading-bar');
  let prog = 0;
  const iv = setInterval(() => {{
    prog += 2;
    bar.style.width = Math.min(prog, 100) + '%';
    if (prog >= 100) {{
      clearInterval(iv);
      setTimeout(_afterLoading, 200);
    }}
  }}, 40); // 100/2 * 40ms = 2 секунды
}});

async function _afterLoading() {{
  // Сначала пробуем получить данные игрока (с коротким таймаутом)
  // Если сервер не ответил — просто идём на регистрацию
  const playerRes = await fetchSafe(`/api/player/${{telegramId}}`);

  let playerData = null;
  try {{
    if (playerRes?.ok) {{
      const d = await playerRes.json();
      if (d.exists) playerData = d.player;
    }}
  }} catch(e) {{}}

  // Загружаем словари в фоне (не блокируем переход)
  _loadDictionaries();

  if (playerData) {{
    player = playerData;
    startGame();
  }} else {{
    showScreen('register');
  }}
}}

// Фоновая загрузка справочников — не блокирует UI
async function _loadDictionaries() {{
  try {{
    const r = await fetchSafe('/api/professions');
    if (r?.ok) {{
      const d = await r.json();
      professionsData = d.professions;
      spheresData = d.spheres;
    }}
  }} catch(e) {{}}
  try {{
    const r = await fetchSafe('/api/upgrades');
    if (r?.ok) upgradesData = await r.json();
  }} catch(e) {{}}
}}

// ──────────────────────────────────────────────────────────────────────
// РЕГИСТРАЦИЯ
// ──────────────────────────────────────────────────────────────────────
let selectedAvatar = 1;
let stats = {{ strength:5, intel:5, charisma:5, luck:5 }};
const MAX_POINTS = 20;
const MIN_STAT = 1;
const MAX_STAT = 12;

function selectAvatar(n) {{
  selectedAvatar = n;
  document.querySelectorAll('.avatar-card').forEach(c => c.classList.remove('selected'));
  document.querySelector(`[data-avatar="${{n}}"]`).classList.add('selected');
}}
// Выбираем первый по умолчанию
setTimeout(() => selectAvatar(1), 100);

function getPointsUsed() {{
  return stats.strength + stats.intel + stats.charisma + stats.luck;
}}

function changeStat(stat, delta) {{
  const newVal = stats[stat] + delta;
  if (newVal < MIN_STAT || newVal > MAX_STAT) return;
  const newTotal = getPointsUsed() + delta;
  if (newTotal > MAX_POINTS || newTotal < 4) return;
  stats[stat] = newVal;
  updateStatUI();
}}

function updateStatUI() {{
  const remaining = MAX_POINTS - getPointsUsed();
  document.querySelector('#points-left span').textContent = remaining;
  ['strength','intel','charisma','luck'].forEach(s => {{
    document.getElementById(`val-${{s}}`).textContent = stats[s];
    document.getElementById(`bar-${{s}}`).style.width = (stats[s]/MAX_STAT*100) + '%';
  }});
}}

async function createPlayer() {{
  const name = document.getElementById('name-input').value.trim() || 'PLAYER';
  if (getPointsUsed() !== MAX_POINTS) {{
    alert('Распредели все 20 очков!'); return;
  }}
  const btn = document.querySelector('#screen-register .btn-green');
  if (btn) {{ btn.textContent = 'ЗАГРУЗКА...'; btn.disabled = true; }}
  try {{
    const res = await fetchWithTimeout('/api/player/create', {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{
        telegram_id: telegramId,
        name, avatar: selectedAvatar,
        stat_strength: stats.strength,
        stat_intel: stats.intel,
        stat_charisma: stats.charisma,
        stat_luck: stats.luck
      }})
    }}, 5000);
    const data = await res.json();
    if (data.ok) {{
      const p = await fetchWithTimeout(`/api/player/${{telegramId}}`, {{}}, 5000);
      const pd = await p.json();
      player = pd.player;
      startGame();
    }} else {{
      if (btn) {{ btn.textContent = '▶ НАЧАТЬ ПУТЬ'; btn.disabled = false; }}
      alert('Ошибка: ' + (data.detail || 'Не удалось'));
    }}
  }} catch(e) {{
    if (btn) {{ btn.textContent = '▶ НАЧАТЬ ПУТЬ'; btn.disabled = false; }}
    alert('Ошибка сервера. Проверь подключение.');
    console.error(e);
  }}
}}

// ──────────────────────────────────────────────────────────────────────
// ИГРА
// ──────────────────────────────────────────────────────────────────────
function startGame() {{
  document.getElementById('nav-bar').style.display = 'flex';
  navigate('main');
  updateMainUI();
  startGameLoop();
}}

function updateMainUI() {{
  if (!player) return;
  const av = HERO_IMGS[player.avatar] || HERO_IMGS[1];
  document.getElementById('main-avatar').src = av;
  document.getElementById('main-char').src = av;
  document.getElementById('main-name').textContent = player.name;
  document.getElementById('main-level').textContent = player.level;
  document.getElementById('main-coins').textContent = fmtNum(player.coins);
  document.getElementById('main-tokens').textContent = player.tokens;
  document.getElementById('main-energy').textContent = player.energy;
  document.getElementById('prof-tokens').textContent = player.tokens;
  document.getElementById('upg-coins').textContent = fmtNum(player.coins);
  
  const xpPct = player.xp_needed > 0 ? (player.xp_current/player.xp_needed*100) : 0;
  document.getElementById('main-xp-bar').style.width = xpPct + '%';
  document.getElementById('main-xp-cur').textContent = player.xp_current;
  document.getElementById('main-xp-need').textContent = player.xp_needed;
  
  const ePct = player.max_energy > 0 ? (player.energy/player.max_energy*100) : 0;
  document.getElementById('energy-bar').style.width = ePct + '%';
  document.getElementById('energy-label-val').textContent = `${{player.energy}}/${{player.max_energy}}`;
}}

function startGameLoop() {{
  // Регенерация энергии на клиенте
  clearInterval(energyUpdateInterval);
  energyUpdateInterval = setInterval(() => {{
    if (!player) return;
    const regen = player.energy_regen || 2;
    player.energy = Math.min(player.max_energy, player.energy + regen/10);
    player.energy = Math.round(player.energy);
    document.getElementById('main-energy').textContent = player.energy;
    document.getElementById('energy-label-val').textContent = `${{player.energy}}/${{player.max_energy}}`;
    const ePct = player.energy/player.max_energy*100;
    document.getElementById('energy-bar').style.width = ePct + '%';
  }}, 100);
}}

// ── ТАП ──────────────────────────────────────────────────────────────
let lastTapY = 0, lastTapX = 0;

function handleTapClick(e) {{
  if (e.touches && e.touches.length > 0) return; // Не дублировать тачи
  processTap(e.clientX || 200, e.clientY || 300, 1);
}}

function handleTap(e) {{
  e.preventDefault();
  const touches = e.changedTouches || e.touches;
  processTap(
    touches[0].clientX, touches[0].clientY,
    touches.length
  );
}}

let tapFlashTimer = null;
let pendingCoins = 0;
let pendingTaps = 0;

function processTap(x, y, numFingers) {{
  if (!player || player.energy <= 0) return;
  
  const taps = Math.min(numFingers, 5);
  pendingTaps += taps;
  
  // Визуальный фидбек
  const ring = document.getElementById('tap-ring');
  ring.classList.remove('flash');
  void ring.offsetWidth;
  ring.classList.add('flash');
  
  // Всплывающие монеты
  const coinsEst = taps * (player.tap_power || 1);
  showCoinFloat(x, y, coinsEst);
  
  // Уменьшаем энергию клиентски
  player.energy = Math.max(0, player.energy - taps);
  
  // Буферизируем тапы, отправляем батчами
  clearTimeout(tapSendTimeout);
  tapSendTimeout = setTimeout(sendTaps, 300);
}}

async function sendTaps() {{
  if (pendingTaps <= 0) return;
  const tapsToSend = pendingTaps;
  pendingTaps = 0;
  
  try {{
    const res = await fetch('/api/tap', {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{
        telegram_id: telegramId,
        taps: tapsToSend,
        timestamp: Date.now()/1000
      }})
    }});
    const data = await res.json();
    if (data.ok) {{
      player.coins = data.coins;
      player.xp = data.xp;
      player.energy = data.energy;
      player.level = data.level;
      player.xp_current = data.xp_current;
      player.xp_needed = data.xp_needed;
      player.tokens = data.tokens;
      
      // Комбо
      if (data.combo_multiplier > 1) {{
        const badge = document.getElementById('combo-badge');
        badge.textContent = `COMBO x${{data.combo_multiplier}}`;
        badge.classList.add('show');
        clearTimeout(comboTimer);
        comboTimer = setTimeout(() => badge.classList.remove('show'), 1500);
      }}
      
      // Левел-ап
      if (data.level_up) {{
        onLevelUp(data.level);
      }}
      
      updateMainUI();
    }}
  }} catch(e) {{}}
}}

function showCoinFloat(x, y, amount) {{
  const el = document.createElement('div');
  el.className = 'coin-float';
  el.textContent = `+${{amount}}🪙`;
  el.style.left = (x - 20) + 'px';
  el.style.top = (y - 20) + 'px';
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 800);
}}

function onLevelUp(newLevel) {{
  const body = document.getElementById('modal-levelup-body');
  body.innerHTML = `<strong>УРОВЕНЬ ${{newLevel}}</strong> достигнут!<br/><br/>+1 токен профессии 🎁`;
  document.getElementById('modal-levelup').classList.add('active');
  
  if (newLevel === 2) {{
    setTimeout(() => {{
      document.getElementById('modal-levelup').classList.remove('active');
      document.getElementById('modal-lvl2-hint').classList.add('active');
    }}, 1500);
  }}
}}

// ──────────────────────────────────────────────────────────────────────
// НАВИГАЦИЯ
// ──────────────────────────────────────────────────────────────────────
function navigate(screen) {{
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(`screen-${{screen}}`).classList.add('active');
  const navBtn = document.getElementById(`nav-${{screen}}`);
  if (navBtn) navBtn.classList.add('active');
  
  if (screen === 'professions') renderProfessions();
  if (screen === 'upgrades') renderUpgrades();
}}

function showScreen(name) {{
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(`screen-${{name}}`).classList.add('active');
}}

function closeModal(id) {{
  document.getElementById(id).classList.remove('active');
}}

// ──────────────────────────────────────────────────────────────────────
// ПРОФЕССИИ
// ──────────────────────────────────────────────────────────────────────
function renderProfessions() {{
  profView = 'spheres';
  document.getElementById('prof-back-btn').style.display = 'none';
  document.getElementById('prof-screen-title').textContent = '⚔ ПРОФЕССИИ';
  document.getElementById('prof-tokens').textContent = player ? player.tokens : 0;
  
  const content = document.getElementById('prof-content');
  
  // Группируем профессии по сферам
  const sphereMap = {{}};
  Object.values(professionsData).forEach(p => {{
    if (!sphereMap[p.sphere]) sphereMap[p.sphere] = [];
    sphereMap[p.sphere].push(p);
  }});
  
  let html = '<div class="sphere-grid">';
  Object.entries(spheresData).forEach(([key, sphere]) => {{
    const profs = sphereMap[key] || [];
    const openedCount = profs.filter(p => player && player.opened_professions && player.opened_professions.includes(p.id)).length;
    html += `
      <div class="sphere-card" onclick="showSphereProfs('${{key}}')" style="border-color:${{sphere.color}}40">
        <div class="sphere-icon">${{sphere.icon}}</div>
        <div class="sphere-name">${{sphere.name}}</div>
        <div class="sphere-count">${{openedCount}}/${{profs.length}} открыто</div>
      </div>`;
  }});
  html += '</div>';
  content.innerHTML = html;
}}

function showSphereProfs(sphereKey) {{
  profView = 'list';
  currentSphere = sphereKey;
  const sphere = spheresData[sphereKey];
  document.getElementById('prof-back-btn').style.display = 'inline-block';
  document.getElementById('prof-screen-title').textContent = sphere.icon + ' ' + sphere.name;
  
  const content = document.getElementById('prof-content');
  const profs = Object.values(professionsData).filter(p => p.sphere === sphereKey);
  const opened = player ? (player.opened_professions || []) : [];
  
  let html = '<div class="prof-list">';
  profs.forEach(p => {{
    const isOpen = opened.includes(p.id);
    html += `
      <div class="prof-card ${{isOpen?'opened':''}}" onclick="showProfDetail('${{p.id}}')">
        <div class="prof-card-icon">${{p.icon}}</div>
        <div class="prof-card-info">
          <div class="prof-card-name">${{p.name}}</div>
          <div class="prof-card-desc">${{p.description.substring(0,60)}}...</div>
        </div>
        <div class="prof-card-badge ${{isOpen?'badge-open':'badge-locked'}}">
          ${{isOpen ? '✓ ОТКРЫТО' : `${{p.cost}}◆`}}
        </div>
      </div>`;
  }});
  html += '</div>';
  content.innerHTML = html;
}}

function showProfDetail(profId) {{
  profView = 'detail';
  currentProfession = profId;
  const prof = professionsData[profId];
  if (!prof) return;
  
  document.getElementById('prof-back-btn').style.display = 'inline-block';
  document.getElementById('prof-screen-title').textContent = prof.icon + ' ' + prof.name;
  
  const opened = player ? (player.opened_professions || []) : [];
  const isOpen = opened.includes(profId);
  const completed = player ? (player.completed_tasks || {{}}) : {{}};
  
  let tasksHtml = '';
  if (isOpen) {{
    prof.tasks.forEach((t, i) => {{
      const key = `${{profId}}_${{i}}`;
      const isDone = !!completed[key];
      // Каждое следующее задание разблокируется только после выполнения предыдущего
      const prevDone = i === 0 || !!completed[`${{profId}}_${{i-1}}`];
      const locked = !prevDone && !isDone;
      tasksHtml += `
        <div class="task-item ${{isDone?'done':''}} ${{locked?'locked':''}}"
             onclick="${{locked?'':isDone?'':'openTask('+JSON.stringify(profId)+','+i+')'}}" >
          <div class="task-num">${{i+1}}</div>
          <div class="task-name">${{t.title}}</div>
          <div class="task-status">${{isDone?'✅':locked?'🔒':'▶'}}</div>
        </div>`;
    }});
  }}
  
  const content = document.getElementById('prof-content');
  content.innerHTML = `
    <div class="prof-detail">
      <div class="prof-detail-header">
        <div class="prof-detail-icon">${{prof.icon}}</div>
        <div>
          <div class="prof-detail-name">${{prof.name}}</div>
          <div class="prof-detail-sphere">${{prof.sphere_name}}</div>
        </div>
      </div>
      <div class="prof-detail-desc">${{prof.description}}</div>
      <div class="info-section-title" style="padding:0;margin-bottom:10px">🛠 ИНСТРУМЕНТЫ:</div>
      <div class="tools-list">${{prof.tools.map(t=>`<span class="tool-tag">${{t}}</span>`).join('')}}</div>
      ${{isOpen ? `
        <div class="info-section-title" style="padding:0;margin:14px 0 10px">📋 ЗАДАНИЯ:</div>
        <div class="task-list">${{tasksHtml}}</div>
      ` : `
        <button class="btn btn-purple btn-full" onclick="openProfession('${{profId}}')">
          ОТКРЫТЬ ЗА ${{prof.cost}} ◆
        </button>
      `}}
    </div>
  `;
}}

function profGoBack() {{
  if (profView === 'detail') {{
    showSphereProfs(currentSphere);
  }} else if (profView === 'list') {{
    renderProfessions();
  }}
}}

async function openProfession(profId) {{
  const prof = professionsData[profId];
  if (!player || player.tokens < prof.cost) {{
    alert(`Нужно ${{prof.cost}} токенов! У тебя ${{player?.tokens || 0}}.`); return;
  }}
  try {{
    const res = await fetch('/api/profession/open', {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{telegram_id: telegramId, profession_id: profId}})
    }});
    const data = await res.json();
    if (data.ok) {{
      player.tokens = data.tokens;
      if (!player.opened_professions) player.opened_professions = [];
      player.opened_professions.push(profId);
      updateMainUI();
      showProfDetail(profId);
    }}
  }} catch(e) {{ alert('Ошибка: '+e.message); }}
}}

// ──────────────────────────────────────────────────────────────────────
// УЛУЧШЕНИЯ
// ──────────────────────────────────────────────────────────────────────
function renderUpgrades() {{
  const list = document.getElementById('upgrades-list');
  const bought = player ? (player.upgrades || {{}}) : {{}};
  const coins = player ? player.coins : 0;
  document.getElementById('upg-coins').textContent = fmtNum(coins);
  
  const upgradeIcons = {{
    'tap_power_1':'👊','tap_power_2':'💪','tap_power_3':'⚡',
    'energy_1':'🔋','energy_2':'🔋',
    'regen_1':'♻️','regen_2':'⚡',
    'multitap':'🖐'
  }};
  
  let html = '';
  Object.entries(upgradesData).forEach(([id, upg]) => {{
    const isBought = !!bought[id];
    const canAfford = coins >= upg.cost;
    html += `
      <div class="upgrade-card ${{isBought?'bought':''}}">
        <div class="upgrade-icon">${{upgradeIcons[id]||'🔧'}}</div>
        <div class="upgrade-info">
          <div class="upgrade-name">${{upg.name}}</div>
          <div class="upgrade-desc">${{upg.desc}}</div>
          <div class="upgrade-cost">🪙 ${{upg.cost}} <span>монет</span></div>
        </div>
        ${{isBought
          ? `<button class="btn btn-dark" disabled style="font-size:6px">✓ КУПЛЕНО</button>`
          : `<button class="btn ${{canAfford?'btn-green':'btn-dark'}}" onclick="buyUpgrade('${{id}}')"
                     ${{canAfford?'':'disabled'}} style="font-size:7px;white-space:nowrap">
               КУПИТЬ
             </button>`
        }}
      </div>`;
  }});
  list.innerHTML = html || '<div style="text-align:center;padding:20px;font-size:7px;color:var(--text2)">Нет улучшений</div>';
}}

async function buyUpgrade(upgradeId) {{
  try {{
    const res = await fetch('/api/upgrade', {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{telegram_id: telegramId, upgrade_id: upgradeId}})
    }});
    const data = await res.json();
    if (data.ok) {{
      // Обновляем состояние
      const upg = upgradesData[upgradeId];
      player.coins = data.coins;
      if (!player.upgrades) player.upgrades = {{}};
      player.upgrades[upgradeId] = true;
      if (upg.effect === 'tap_power') player.tap_power = data.tap_power;
      if (upg.effect === 'max_energy') player.max_energy = data.max_energy;
      if (upg.effect === 'energy_regen') player.energy_regen = data.energy_regen;
      updateMainUI();
      renderUpgrades();
    }} else {{
      alert('Ошибка: ' + (data.detail||'Не удалось'));
    }}
  }} catch(e) {{ alert('Ошибка: ' + e.message); }}
}}

// ──────────────────────────────────────────────────────────────────────
// МИНИ-ИГРЫ
// ──────────────────────────────────────────────────────────────────────
function openTask(profId, taskIdx) {{
  const prof = professionsData[profId];
  if (!prof) return;
  const task = prof.tasks[taskIdx];
  if (!task) return;
  
  currentTask = {{ profId, taskIdx, task, prof }};
  mgScore = 0;
  mgAnswered = false;
  
  document.getElementById('mg-title').textContent = task.title.toUpperCase();
  document.getElementById('mg-step-info').textContent = `ЗАДАНИЕ ${{taskIdx+1}}/5`;
  
  const body = document.getElementById('mg-body');
  body.innerHTML = buildMinigame(task, taskIdx, prof);
  
  document.getElementById('minigame-wrap').classList.add('active');
}}

function closeMinigame() {{
  document.getElementById('minigame-wrap').classList.remove('active');
  currentTask = null;
}}

function buildMinigame(task, idx, prof) {{
  // Выбираем тип мини-игры на основе типа задания
  switch(task.type) {{
    case 'layout_puzzle': return buildLayoutPuzzle(task);
    case 'bug_fix': return buildBugFix(task);
    case 'sql_puzzle': return buildSqlPuzzle(task);
    case 'data_analysis': return buildDataAnalysis(task);
    case 'data_cleaning': return buildDataCleaning(task);
    case 'chart_reading': return buildChartReading(task);
    case 'prediction': return buildPrediction(task);
    case 'diagnosis': return buildDiagnosis(task);
    case 'chem_equation': return buildChemEquation(task);
    case 'circuit_puzzle': return buildCircuitPuzzle(task);
    case 'target_audience': return buildTargetAudience(task);
    case 'ab_test': return buildABTest(task);
    case 'game_design': return buildGameDesign(task);
    case 'balance': return buildBalance(task);
    default: return buildGenericQuiz(task, idx, prof);
  }}
}}

// ── Мини-игра: CSS Layout Puzzle ──────────────────────────────────────
function buildLayoutPuzzle(task) {{
  return `
    <div class="mg-desc">${{task.desc}}<br/><br/>
    Нужно сделать: три блока в ряд с равными отступами.<br/>
    Выбери правильный CSS:</div>
    <div class="lp-preview">
      <div style="width:60px;height:40px;background:#00ff88;border:2px solid #007744;display:flex;align-items:center;justify-content:center;font-size:8px">1</div>
      <div style="width:60px;height:40px;background:#00ff88;border:2px solid #007744;display:flex;align-items:center;justify-content:center;font-size:8px">2</div>
      <div style="width:60px;height:40px;background:#00ff88;border:2px solid #007744;display:flex;align-items:center;justify-content:center;font-size:8px">3</div>
    </div>
    <div class="lp-options">
      <div class="lp-option" onclick="checkLayout(this, false)">display:block;<br/>margin:auto</div>
      <div class="lp-option" onclick="checkLayout(this, true)">display:flex;<br/>justify-content:<br/>space-between</div>
      <div class="lp-option" onclick="checkLayout(this, false)">position:absolute;<br/>left:0</div>
      <div class="lp-option" onclick="checkLayout(this, false)">float:left;<br/>width:100%</div>
    </div>
    <div id="mg-result-inline" style="margin-top:12px;display:none"></div>
  `;
}}

function checkLayout(el, isCorrect) {{
  if (mgAnswered) return;
  mgAnswered = true;
  el.classList.add(isCorrect ? 'correct' : 'wrong');
  mgScore = isCorrect ? 100 : 40;
  document.getElementById('mg-result-inline').style.display = 'block';
  document.getElementById('mg-result-inline').innerHTML = `
    <div style="font-size:7px;color:${{isCorrect?'var(--accent)':'var(--red)'}};margin-bottom:12px">
      ${{isCorrect ? '✅ Верно! display:flex + justify-content:space-between — классический способ выравнивания.' 
                   : '❌ Неверно. Правильный ответ: display:flex; justify-content:space-between'}}
    </div>
    <button class="btn btn-green btn-full" onclick="submitMinigame(${{mgScore}})">
      ${{isCorrect ? 'ОТЛИЧНО! ДАЛЕЕ →' : 'ПОПРОБОВАЛ → ДАЛЕЕ'}}
    </button>
  `;
}}

// ── Мини-игра: Найди баг ──────────────────────────────────────────────
function buildBugFix(task) {{
  const lines = [
    'function calcTotal(items) {{',
    '  let total = 0;',
    '  for (let i = 0; i <= items.length; i++) {{',
    '    total += items[i].price;',
    '  }}',
    '  return total;',
    '}}'
  ];
  const bugLine = 2; // 0-indexed, строка с ошибкой
  
  return `
    <div class="mg-desc">${{task.desc}}<br/><br/>
    Нажми на строку с ошибкой:</div>
    <div class="bug-code">${{lines.map((l,i) => 
      `<span class="bug-line" onclick="checkBugLine(${{i}},${{bugLine===i}})">${{i+1}}: ${{l}}</span>`
    ).join('')}}</div>
    <div id="mg-result-inline" style="display:none;margin-top:12px"></div>
  `;
}}

function checkBugLine(lineIdx, isCorrect) {{
  if (mgAnswered) return;
  mgAnswered = true;
  const lines = document.querySelectorAll('.bug-line');
  lines[lineIdx].classList.add(isCorrect ? 'correct' : 'selected');
  if (!isCorrect) lines[2].classList.add('correct');
  mgScore = isCorrect ? 100 : 30;
  document.getElementById('mg-result-inline').style.display = 'block';
  document.getElementById('mg-result-inline').innerHTML = `
    <div style="font-size:7px;color:${{isCorrect?'var(--accent)':'var(--red)'}};margin-bottom:12px;line-height:1.7">
      ${{isCorrect ? '✅ Верно! i <= items.length вызывает выход за границу массива. Должно быть i < items.length'
                   : '❌ Ошибка в строке 3: i <= items.length должно быть i < items.length (иначе items[i] = undefined)'}}
    </div>
    <button class="btn btn-green btn-full" onclick="submitMinigame(${{mgScore}})">ДАЛЕЕ →</button>
  `;
}}

// ── Мини-игра: SQL ────────────────────────────────────────────────────
function buildSqlPuzzle(task) {{
  return `
    <div class="mg-desc">${{task.desc}}<br/><br/>
    Задача: получить имена пользователей с более чем 5 заказами, отсортированных по имени.</div>
    <div class="lp-options" style="grid-template-columns:1fr">
      <div class="lp-option" onclick="checkSql(this, false)" style="text-align:left;font-family:monospace;font-size:9px">
        SELECT name FROM users WHERE orders > 5</div>
      <div class="lp-option" onclick="checkSql(this, true)" style="text-align:left;font-family:monospace;font-size:9px">
        SELECT u.name FROM users u<br/>JOIN orders o ON u.id=o.user_id<br/>GROUP BY u.id HAVING COUNT(o.id)>5<br/>ORDER BY u.name</div>
      <div class="lp-option" onclick="checkSql(this, false)" style="text-align:left;font-family:monospace;font-size:9px">
        SELECT * FROM orders WHERE count > 5</div>
    </div>
    <div id="mg-result-inline" style="display:none;margin-top:12px"></div>
  `;
}}

function checkSql(el, isCorrect) {{
  if (mgAnswered) return;
  mgAnswered = true;
  el.classList.add(isCorrect?'correct':'wrong');
  mgScore = isCorrect ? 100 : 35;
  document.getElementById('mg-result-inline').style.display = 'block';
  document.getElementById('mg-result-inline').innerHTML = `
    <div style="font-size:7px;color:${{isCorrect?'var(--accent)':'var(--red)'}};margin-bottom:12px;line-height:1.7">
      ${{isCorrect ? '✅ Верно! Нужен JOIN с таблицей заказов, GROUP BY и HAVING для агрегации.'
                   : '❌ Неверно. Нельзя просто проверить поле orders — его нет. Нужен JOIN с таблицей orders.'}}
    </div>
    <button class="btn btn-green btn-full" onclick="submitMinigame(${{mgScore}})">ДАЛЕЕ →</button>
  `;
}}

// ── Мини-игра: Анализ данных ──────────────────────────────────────────
function buildDataAnalysis(task) {{
  const data = [
    {{month:'Янв', sales:120}}, {{month:'Фев', sales:135}},
    {{month:'Мар', sales:118}}, {{month:'Апр', sales:142}},
    {{month:'Май', sales:165}}, {{month:'Июн', sales:158}},
  ];
  const maxSales = Math.max(...data.map(d=>d.sales));
  
  return `
    <div class="mg-desc">${{task.desc}}<br/><br/>
    Проанализируй продажи и выбери правильный вывод:</div>
    <div style="padding:10px;background:var(--bg3);border:2px solid var(--border);margin-bottom:12px">
      ${{data.map(d => `
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
          <span style="font-size:7px;width:28px;color:var(--text2)">${{d.month}}</span>
          <div style="flex:1;height:14px;background:var(--bg2);position:relative">
            <div style="width:${{d.sales/maxSales*100}}%;height:100%;background:var(--accent);opacity:0.8"></div>
          </div>
          <span style="font-size:7px;width:28px;color:var(--text)">${{d.sales}}</span>
        </div>
      `).join('')}}
    </div>
    <div class="lp-options" style="grid-template-columns:1fr">
      <div class="lp-option" onclick="checkAnalysis(this,false)">Продажи падают — нужно срочно менять стратегию</div>
      <div class="lp-option" onclick="checkAnalysis(this,true)">Общий тренд роста с просадкой в марте, май — пик полугодия</div>
      <div class="lp-option" onclick="checkAnalysis(this,false)">Данных недостаточно для выводов</div>
    </div>
    <div id="mg-result-inline" style="display:none;margin-top:12px"></div>
  `;
}}

function checkAnalysis(el, isCorrect) {{
  if (mgAnswered) return;
  mgAnswered = true;
  el.classList.add(isCorrect?'correct':'wrong');
  mgScore = isCorrect ? 100 : 40;
  document.getElementById('mg-result-inline').style.display = 'block';
  document.getElementById('mg-result-inline').innerHTML = `
    <div style="font-size:7px;color:${{isCorrect?'var(--accent)':'var(--red)'}};margin-bottom:12px;line-height:1.7">
      ${{isCorrect ? '✅ Верно! Данные показывают восходящий тренд. Важно замечать аномалии (март) и пики (май).'
                   : '❌ Посмотри внимательнее — общая динамика положительная, в марте была лишь временная просадка.'}}
    </div>
    <button class="btn btn-green btn-full" onclick="submitMinigame(${{mgScore}})">ДАЛЕЕ →</button>
  `;
}}

// ── Мини-игра: Очистка данных ─────────────────────────────────────────
function buildDataCleaning(task) {{
  const rows = [
    {{name:'Иванов', age:25, salary:50000}},
    {{name:'Петров', age:-3, salary:60000}},  // аномалия
    {{name:'Сидоров', age:32, salary:55000}},
    {{name:'', age:28, salary:48000}},          // пустое имя
    {{name:'Козлов', age:999, salary:52000}},  // аномалия
  ];
  
  return `
    <div class="mg-desc">${{task.desc}}<br/><br/>Нажми на строки с аномалиями (их 3):</div>
    <table class="data-table">
      <tr><th>Имя</th><th>Возраст</th><th>Зарплата</th></tr>
      ${{rows.map((r,i) => `
        <tr class="${{[1,3,4].includes(i)?'anomaly':''}}" onclick="toggleAnomaly(this,${{[1,3,4].includes(i)}})" 
            style="cursor:pointer" id="row-${{i}}">
          <td>${{r.name||'<span style="color:var(--red)">ПУСТО</span>'}}</td>
          <td>${{r.age}}</td>
          <td>${{r.salary}}</td>
        </tr>
      `)}}
    </table>
    <div id="anomaly-status" style="font-size:7px;color:var(--text2);margin-bottom:12px">
      Выбрано: <span id="anomaly-count">0</span>/3
    </div>
    <div id="mg-result-inline" style="display:none;margin-top:12px"></div>
  `;
}}

let selectedAnomalies = new Set();
let anomalyCorrect = new Set([1,3,4]);

function toggleAnomaly(row, isCorrect) {{
  if (mgAnswered) return;
  const idx = parseInt(row.id.split('-')[1]);
  if (selectedAnomalies.has(idx)) {{
    selectedAnomalies.delete(idx);
    row.style.background = '';
  }} else {{
    selectedAnomalies.add(idx);
    row.style.background = isCorrect ? 'rgba(0,255,100,0.1)' : 'rgba(255,0,0,0.1)';
  }}
  document.getElementById('anomaly-count').textContent = selectedAnomalies.size;
  
  if (selectedAnomalies.size === 3) {{
    mgAnswered = true;
    const correct = [...selectedAnomalies].filter(i => anomalyCorrect.has(i)).length;
    mgScore = Math.round(correct/3*100);
    document.getElementById('mg-result-inline').style.display = 'block';
    document.getElementById('mg-result-inline').innerHTML = `
      <div style="font-size:7px;color:${{mgScore===100?'var(--accent)':'var(--accent2)'}};margin-bottom:12px;line-height:1.7">
        ${{mgScore===100 ? '✅ Отлично! Возраст -3, пустое имя и возраст 999 — явные аномалии данных.'
                        : `⚠️ Правильно: ${{correct}}/3. Проверь: возраст -3 (строка 2), пустое имя (строка 4), возраст 999 (строка 5)`}}
      </div>
      <button class="btn btn-green btn-full" onclick="submitMinigame(${{mgScore}})">ДАЛЕЕ →</button>
    `;
  }}
}}

// ── Мини-игра: График ─────────────────────────────────────────────────
function buildChartReading(task) {{
  return `
    <div class="mg-desc">${{task.desc}}<br/><br/>
    Что означает резкий скачок на графике конверсии сайта?</div>
    <div style="padding:12px;background:var(--bg3);border:2px solid var(--border);margin-bottom:12px;position:relative;height:100px">
      <svg width="100%" height="70" viewBox="0 0 300 70">
        <polyline points="0,60 50,55 100,50 150,45 160,20 200,22 250,18 300,15"
                  fill="none" stroke="var(--accent)" stroke-width="2"/>
        <circle cx="160" cy="20" r="5" fill="var(--gold)"/>
        <text x="155" y="14" fill="var(--gold)" font-size="8">← скачок</text>
      </svg>
      <div style="font-size:6px;color:var(--text2);display:flex;justify-content:space-between">
        <span>Янв</span><span>Фев</span><span>Мар</span><span>Апр</span>
      </div>
    </div>
    <div class="lp-options" style="grid-template-columns:1fr">
      <div class="lp-option" onclick="checkChart(this,false)">Технический сбой сервера</div>
      <div class="lp-option" onclick="checkChart(this,true)">Запуск новой рекламной кампании или изменение UX</div>
      <div class="lp-option" onclick="checkChart(this,false)">Случайное отклонение без причины</div>
    </div>
    <div id="mg-result-inline" style="display:none;margin-top:12px"></div>
  `;
}}

function checkChart(el, isCorrect) {{
  if (mgAnswered) return;
  mgAnswered = true;
  el.classList.add(isCorrect?'correct':'wrong');
  mgScore = isCorrect ? 100 : 40;
  document.getElementById('mg-result-inline').style.display = 'block';
  document.getElementById('mg-result-inline').innerHTML = `
    <div style="font-size:7px;color:${{isCorrect?'var(--accent)':'var(--red)'}};margin-bottom:12px;line-height:1.7">
      ${{isCorrect ? '✅ Верно! Резкий рост конверсии чаще всего объясняется маркетинговым событием или UX-улучшением.'
                   : '❌ Технические сбои обычно снижают конверсию. Такой рост — позитивное событие.'}}
    </div>
    <button class="btn btn-green btn-full" onclick="submitMinigame(${{mgScore}})">ДАЛЕЕ →</button>
  `;
}}

// ── Мини-игра: Предсказание ───────────────────────────────────────────
function buildPrediction(task) {{
  return `
    <div class="mg-desc">${{task.desc}}<br/><br/>
    Данные: 10, 20, 30, 40, ?<br/>Выбери следующее значение по линейному тренду:</div>
    <div class="lp-options">
      <div class="lp-option" onclick="checkPred(this,false)">35</div>
      <div class="lp-option" onclick="checkPred(this,true)">50</div>
      <div class="lp-option" onclick="checkPred(this,false)">45</div>
      <div class="lp-option" onclick="checkPred(this,false)">60</div>
    </div>
    <div id="mg-result-inline" style="display:none;margin-top:12px"></div>
  `;
}}

function checkPred(el, isCorrect) {{
  if (mgAnswered) return;
  mgAnswered = true;
  el.classList.add(isCorrect?'correct':'wrong');
  mgScore = isCorrect ? 100 : 20;
  document.getElementById('mg-result-inline').style.display = 'block';
  document.getElementById('mg-result-inline').innerHTML = `
    <div style="font-size:7px;color:${{isCorrect?'var(--accent)':'var(--red)'}};margin-bottom:12px;line-height:1.7">
      ${{isCorrect ? '✅ Верно! Шаг прироста = 10. 40+10 = 50. Линейная экстраполяция.'
                   : '❌ Посчитай разность соседних элементов: 20-10=10, 30-20=10. Значит следующий: 40+10=50'}}
    </div>
    <button class="btn btn-green btn-full" onclick="submitMinigame(${{mgScore}})">ДАЛЕЕ →</button>
  `;
}}

// ── Мини-игра: Диагноз ────────────────────────────────────────────────
function buildDiagnosis(task) {{
  return `
    <div class="mg-desc">Пациент: температура 38.5°C, боль в правом боку, тошнота, рвота.<br/>
    Симптомы появились 12 часов назад. Поставь предварительный диагноз:</div>
    <div class="lp-options" style="grid-template-columns:1fr">
      <div class="lp-option" onclick="checkDiag(this,false)">Грипп</div>
      <div class="lp-option" onclick="checkDiag(this,true)">Острый аппендицит</div>
      <div class="lp-option" onclick="checkDiag(this,false)">Пищевое отравление</div>
      <div class="lp-option" onclick="checkDiag(this,false)">Мигрень</div>
    </div>
    <div id="mg-result-inline" style="display:none;margin-top:12px"></div>
  `;
}}

function checkDiag(el, isCorrect) {{
  if (mgAnswered) return;
  mgAnswered = true;
  el.classList.add(isCorrect?'correct':'wrong');
  mgScore = isCorrect ? 100 : 30;
  document.getElementById('mg-result-inline').style.display = 'block';
  document.getElementById('mg-result-inline').innerHTML = `
    <div style="font-size:7px;color:${{isCorrect?'var(--accent)':'var(--red)'}};margin-bottom:12px;line-height:1.7">
      ${{isCorrect ? '✅ Верно! Боль в правом боку + температура + тошнота — классическая триада острого аппендицита. Требует экстренной операции!'
                   : '❌ Ключевой симптом — боль в правом боку. Это триада Мёрфи — признак острого аппендицита.'}}
    </div>
    <button class="btn btn-green btn-full" onclick="submitMinigame(${{mgScore}})">ДАЛЕЕ →</button>
  `;
}}

// ── Мини-игра: Химическое уравнение ──────────────────────────────────
function buildChemEquation(task) {{
  return `
    <div class="mg-desc">${{task.desc}}<br/><br/>
    Расставь коэффициенты: _H₂ + _O₂ → _H₂O</div>
    <div class="lp-options">
      <div class="lp-option" onclick="checkChem(this,false)">1H₂ + 1O₂ → 1H₂O</div>
      <div class="lp-option" onclick="checkChem(this,true)">2H₂ + O₂ → 2H₂O</div>
      <div class="lp-option" onclick="checkChem(this,false)">H₂ + 2O₂ → 2H₂O</div>
      <div class="lp-option" onclick="checkChem(this,false)">3H₂ + O₂ → 3H₂O</div>
    </div>
    <div id="mg-result-inline" style="display:none;margin-top:12px"></div>
  `;
}}

function checkChem(el, isCorrect) {{
  if (mgAnswered) return;
  mgAnswered = true;
  el.classList.add(isCorrect?'correct':'wrong');
  mgScore = isCorrect ? 100 : 25;
  document.getElementById('mg-result-inline').style.display = 'block';
  document.getElementById('mg-result-inline').innerHTML = `
    <div style="font-size:7px;color:${{isCorrect?'var(--accent)':'var(--red)'}};margin-bottom:12px;line-height:1.7">
      ${{isCorrect ? '✅ Верно! 2H₂ + O₂ → 2H₂O. Закон сохранения массы: 4H + 2O слева = 4H + 2O справа.'
                   : '❌ Проверь: атомов H слева = атомам H справа, то же для O. Ответ: 2H₂ + O₂ → 2H₂O'}}
    </div>
    <button class="btn btn-green btn-full" onclick="submitMinigame(${{mgScore}})">ДАЛЕЕ →</button>
  `;
}}

// ── Мини-игра: Схема робота ───────────────────────────────────────────
function buildCircuitPuzzle(task) {{
  return `
    <div class="mg-desc">${{task.desc}}<br/><br/>
    Выбери правильную схему подключения: нужно питать LED от Arduino через резистор 220Ом:</div>
    <div class="lp-options" style="grid-template-columns:1fr">
      <div class="lp-option" onclick="checkCircuit(this,false)">
        Arduino 5V → LED → GND (напрямую)
      </div>
      <div class="lp-option" onclick="checkCircuit(this,true)">
        Arduino 5V → Резистор 220Ом → LED (анод) → LED (катод) → GND
      </div>
      <div class="lp-option" onclick="checkCircuit(this,false)">
        Arduino GND → Резистор → LED → 5V
      </div>
    </div>
    <div id="mg-result-inline" style="display:none;margin-top:12px"></div>
  `;
}}

function checkCircuit(el, isCorrect) {{
  if (mgAnswered) return;
  mgAnswered = true;
  el.classList.add(isCorrect?'correct':'wrong');
  mgScore = isCorrect ? 100 : 30;
  document.getElementById('mg-result-inline').style.display = 'block';
  document.getElementById('mg-result-inline').innerHTML = `
    <div style="font-size:7px;color:${{isCorrect?'var(--accent)':'var(--red)'}};margin-bottom:12px;line-height:1.7">
      ${{isCorrect ? '✅ Верно! Резистор ограничивает ток. Без него LED сгорит. Ток = (5V-2V)/220Ом ≈ 14мА — безопасно.'
                   : '❌ LED без резистора сразу сгорит от перегрузки тока! Всегда нужен ограничительный резистор.'}}
    </div>
    <button class="btn btn-green btn-full" onclick="submitMinigame(${{mgScore}})">ДАЛЕЕ →</button>
  `;
}}

// ── Мини-игра: Целевая аудитория ──────────────────────────────────────
function buildTargetAudience(task) {{
  return `
    <div class="mg-desc">Продукт: мобильное приложение для контроля бюджета с геймификацией.<br/><br/>
    Выбери наиболее точную целевую аудиторию:</div>
    <div class="lp-options" style="grid-template-columns:1fr">
      <div class="lp-option" onclick="checkTA(this,false)">Все люди 18-65 лет, у кого есть деньги</div>
      <div class="lp-option" onclick="checkTA(this,true)">Молодые люди 18-35, активные пользователи смартфонов, хотят контролировать финансы, любят игровые механики</div>
      <div class="lp-option" onclick="checkTA(this,false)">Пенсионеры, желающие экономить</div>
    </div>
    <div id="mg-result-inline" style="display:none;margin-top:12px"></div>
  `;
}}

function checkTA(el, isCorrect) {{
  if (mgAnswered) return;
  mgAnswered = true;
  el.classList.add(isCorrect?'correct':'wrong');
  mgScore = isCorrect ? 100 : 25;
  document.getElementById('mg-result-inline').style.display = 'block';
  document.getElementById('mg-result-inline').innerHTML = `
    <div style="font-size:7px;color:${{isCorrect?'var(--accent)':'var(--red)'}};margin-bottom:12px;line-height:1.7">
      ${{isCorrect ? '✅ Верно! ЦА должна быть конкретной. Геймификация — это молодёжный тренд. Узкая ЦА = эффективная реклама.'
                   : '❌ "Все люди" — слишком широко. ЦА нужно сужать по: возрасту, интересам, поведению.'}}
    </div>
    <button class="btn btn-green btn-full" onclick="submitMinigame(${{mgScore}})">ДАЛЕЕ →</button>
  `;
}}

// ── Мини-игра: A/B тест ───────────────────────────────────────────────
function buildABTest(task) {{
  return `
    <div class="mg-desc">${{task.desc}}<br/><br/>Тест кнопки "Купить":</div>
    <table class="data-table" style="margin-bottom:12px">
      <tr><th>Вариант</th><th>Показы</th><th>Клики</th><th>CTR</th></tr>
      <tr><td>A: "Купить сейчас"</td><td>1000</td><td>45</td><td>4.5%</td></tr>
      <tr><td>B: "Получить за 990₽"</td><td>1000</td><td>68</td><td>6.8%</td></tr>
    </table>
    <div class="lp-options" style="grid-template-columns:1fr">
      <div class="lp-option" onclick="checkAB(this,false)">Оставить вариант A — он старый и проверенный</div>
      <div class="lp-option" onclick="checkAB(this,true)">Внедрить вариант B — CTR выше на 51%, результат статистически значимый</div>
      <div class="lp-option" onclick="checkAB(this,false)">Нужно ещё 3 месяца тестирования</div>
    </div>
    <div id="mg-result-inline" style="display:none;margin-top:12px"></div>
  `;
}}

function checkAB(el, isCorrect) {{
  if (mgAnswered) return;
  mgAnswered = true;
  el.classList.add(isCorrect?'correct':'wrong');
  mgScore = isCorrect ? 100 : 35;
  document.getElementById('mg-result-inline').style.display = 'block';
  document.getElementById('mg-result-inline').innerHTML = `
    <div style="font-size:7px;color:${{isCorrect?'var(--accent)':'var(--red)'}};margin-bottom:12px;line-height:1.7">
      ${{isCorrect ? '✅ Верно! Указание цены в CTA повышает конверсию. 6.8% vs 4.5% при 1000 показах — значимый результат.'
                   : '❌ Данные говорят в пользу варианта B. В маркетинге нужно доверять цифрам, не традициям.'}}
    </div>
    <button class="btn btn-green btn-full" onclick="submitMinigame(${{mgScore}})">ДАЛЕЕ →</button>
  `;
}}

// ── Мини-игра: Геймдизайн ─────────────────────────────────────────────
function buildGameDesign(task) {{
  return `
    <div class="mg-desc">Игра: бесконечный раннер. Игроки жалуются, что "слишком скучно через 2 минуты".<br/><br/>
    Что исправить?</div>
    <div class="lp-options" style="grid-template-columns:1fr">
      <div class="lp-option" onclick="checkGD(this,false)">Добавить больше уровней</div>
      <div class="lp-option" onclick="checkGD(this,true)">Добавить прогрессирующую сложность, случайные события и систему рекордов</div>
      <div class="lp-option" onclick="checkGD(this,false)">Улучшить графику</div>
      <div class="lp-option" onclick="checkGD(this,false)">Снизить цену в магазине</div>
    </div>
    <div id="mg-result-inline" style="display:none;margin-top:12px"></div>
  `;
}}

function checkGD(el, isCorrect) {{
  if (mgAnswered) return;
  mgAnswered = true;
  el.classList.add(isCorrect?'correct':'wrong');
  mgScore = isCorrect ? 100 : 30;
  document.getElementById('mg-result-inline').style.display = 'block';
  document.getElementById('mg-result-inline').innerHTML = `
    <div style="font-size:7px;color:${{isCorrect?'var(--accent)':'var(--red)'}};margin-bottom:12px;line-height:1.7">
      ${{isCorrect ? '✅ Верно! Retention в раннерах строится на: difficulty curve, неожиданности, соревновательности.'
                   : '❌ "Скучно" — проблема геймплейного лупа, а не уровней или графики. Нужен challenge progression.'}}
    </div>
    <button class="btn btn-green btn-full" onclick="submitMinigame(${{mgScore}})">ДАЛЕЕ →</button>
  `;
}}

// ── Мини-игра: Баланс ─────────────────────────────────────────────────
function buildBalance(task) {{
  return `
    <div class="mg-desc">RPG-игра. Маг: урон 100, HP 50. Воин: урон 30, HP 200.<br/>
    1000 игроков выбрали мага. Воина выбрали 50. Как сбалансировать?</div>
    <div class="lp-options" style="grid-template-columns:1fr">
      <div class="lp-option" onclick="checkBalance(this,false)">Убрать воина из игры</div>
      <div class="lp-option" onclick="checkBalance(this,false)">Ослабить мага — урон до 20</div>
      <div class="lp-option" onclick="checkBalance(this,true)">Усилить уникальность воина: добавить щит, контроль толпы, командные бонусы</div>
    </div>
    <div id="mg-result-inline" style="display:none;margin-top:12px"></div>
  `;
}}

function checkBalance(el, isCorrect) {{
  if (mgAnswered) return;
  mgAnswered = true;
  el.classList.add(isCorrect?'correct':'wrong');
  mgScore = isCorrect ? 100 : 25;
  document.getElementById('mg-result-inline').style.display = 'block';
  document.getElementById('mg-result-inline').innerHTML = `
    <div style="font-size:7px;color:${{isCorrect?'var(--accent)':'var(--red)'}};margin-bottom:12px;line-height:1.7">
      ${{isCorrect ? '✅ Верно! Баланс — не равные цифры, а разные сильные стороны. Нерф мага снизит fun-фактор.'
                   : '❌ Нерфить популярного персонажа — плохая идея. Лучше сделать альтернативу привлекательнее.'}}
    </div>
    <button class="btn btn-green btn-full" onclick="submitMinigame(${{mgScore}})">ДАЛЕЕ →</button>
  `;
}}

// ── Универсальная мини-игра ────────────────────────────────────────────
function buildGenericQuiz(task, idx, prof) {{
  const quizzes = {{
    'operation_sim': {{
      q: 'Правильная последовательность лапароскопии:',
      options: [
        [false, 'Разрез → Инструменты → Газ → Операция'],
        [true, 'Анестезия → Газ (пневмоперитонеум) → Троакары → Операция → Ушивание'],
        [false, 'Газ → Разрез → Операция → Проснуться'],
      ]
    }},
    'emergency': {{
      q: 'Пациент без сознания, нет пульса. Первое действие:',
      options: [
        [false, 'Вызвать заведующего отделением'],
        [true, 'Начать СЛР (30 компрессий + 2 вдоха), вызвать реанимацию'],
        [false, 'Ввести адреналин'],
      ]
    }},
    'api_design': {{
      q: 'REST API для создания заказа. Правильный метод:',
      options: [
        [false, 'GET /createOrder'],
        [true, 'POST /orders с телом запроса'],
        [false, 'PUT /order/new'],
      ]
    }},
    'security': {{
      q: 'Найди SQL-инъекцию:\nquery = "SELECT * FROM users WHERE id=" + user_input',
      options: [
        [false, 'Код работает нормально'],
        [true, 'user_input не очищен — можно ввести: 1 OR 1=1 и получить все данные'],
        [false, 'Проблема в SELECT *'],
      ]
    }},
    'path_planning': {{
      q: 'Робот должен объехать препятствие. Оптимальный алгоритм:',
      options: [
        [false, 'Двигаться по прямой и останавливаться перед стеной'],
        [true, 'A* (A-star) — поиск кратчайшего пути с учётом препятствий'],
        [false, 'Случайное блуждание'],
      ]
    }},
  }};
  
  const quiz = quizzes[task.type] || {{
    q: `Профессия ${{prof.name}}: какой навык самый важный?`,
    options: [
      [false, 'Умение красиво говорить'],
      [true, 'Системное мышление и постоянное обучение'],
      [false, 'Знание всех инструментов'],
    ]
  }};
  
  return `
    <div class="mg-desc">${{quiz.q}}</div>
    <div class="lp-options" style="grid-template-columns:1fr">
      ${{quiz.options.map(([correct, text]) => 
        `<div class="lp-option" onclick="checkGeneric(this,${{correct}})">${{text}}</div>`
      ).join('')}}
    </div>
    <div id="mg-result-inline" style="display:none;margin-top:12px"></div>
  `;
}}

function checkGeneric(el, isCorrect) {{
  if (mgAnswered) return;
  mgAnswered = true;
  el.classList.add(isCorrect?'correct':'wrong');
  if (!isCorrect) {{
    document.querySelectorAll('.lp-option').forEach(opt => {{
      // Подсвечиваем правильный ответ
    }});
  }}
  mgScore = isCorrect ? 100 : 40;
  document.getElementById('mg-result-inline').style.display = 'block';
  document.getElementById('mg-result-inline').innerHTML = `
    <div style="font-size:7px;color:${{isCorrect?'var(--accent)':'var(--red)'}};margin-bottom:12px;line-height:1.7">
      ${{isCorrect ? '✅ Отличная работа! Ты разбираешься в теме!' : '❌ Не совсем. Но это нормально — учиться на ошибках!'}}
    </div>
    <button class="btn btn-green btn-full" onclick="submitMinigame(${{mgScore}})">ДАЛЕЕ →</button>
  `;
}}

// ── Отправка результата мини-игры ─────────────────────────────────────
async function submitMinigame(score) {{
  if (!currentTask) return;
  const {{ profId, taskIdx }} = currentTask;
  
  try {{
    const res = await fetch('/api/task/complete', {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{
        telegram_id: telegramId,
        profession_id: profId,
        task_index: taskIdx,
        score
      }})
    }});
    const data = await res.json();
    
    if (data.ok && !data.already_done) {{
      // Обновляем состояние игрока
      player.coins = data.coins;
      player.xp = data.xp;
      player.level = data.level;
      player.tokens = data.tokens;
      if (!player.completed_tasks) player.completed_tasks = {{}};
      player.completed_tasks[`${{profId}}_${{taskIdx}}`] = {{score, ts: Date.now()/1000}};
      updateMainUI();
      
      // Показываем награду
      showTaskResult(score, data.coins_earned, data.xp_earned, data.level_up, data.level);
    }} else {{
      closeMinigame();
    }}
  }} catch(e) {{
    alert('Ошибка сохранения: ' + e.message);
  }}
}}

function showTaskResult(score, coinsEarned, xpEarned, levelUp, newLevel) {{
  const emoji = score >= 80 ? '🏆' : score >= 50 ? '✅' : '💪';
  const title = score >= 80 ? 'ОТЛИЧНО!' : score >= 50 ? 'ВЫПОЛНЕНО!' : 'ПОПЫТКА ЗАСЧИТАНА';
  
  document.getElementById('task-result-title').textContent = emoji + ' ' + title;
  document.getElementById('task-result-body').innerHTML = `
    <div class="result-score">${{emoji}}</div>
    <div style="font-size:8px;margin-bottom:8px;color:var(--text2)">
      Счёт: <span style="color:var(--gold)">${{score}}/100</span>
    </div>
    <div class="result-rewards">
      <div class="reward-item">🪙 <span>+${{coinsEarned}}</span></div>
      <div class="reward-item">⭐ <span>+${{xpEarned}} XP</span></div>
    </div>
    ${{levelUp ? `<div style="font-size:9px;color:var(--accent);margin-top:8px">⬆️ УРОВЕНЬ ${{newLevel}}!</div>` : ''}}
  `;
  
  closeMinigame();
  document.getElementById('modal-task-result').classList.add('active');
  
  // Обновляем экран профессий
  if (profView === 'detail') showProfDetail(currentTask?.profId);
}}

// ──────────────────────────────────────────────────────────────────────
// УТИЛИТЫ
// ──────────────────────────────────────────────────────────────────────
function fmtNum(n) {{
  if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n/1000).toFixed(1) + 'K';
  return Math.floor(n).toString();
}}
</script>
</body>
</html>"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
