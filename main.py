"""
RE:ALITY: Профессии — Telegram Mini App для профориентации подростков
FastAPI бэкенд + SQLite + встроенный HTML фронтенд
"""

import json
import time
import hashlib
import sqlite3
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

# ===================== МОДЕЛИ ДАННЫХ =====================

class RegisterRequest(BaseModel):
    telegram_id: int
    name: str = Field(max_length=8)
    avatar: int = Field(ge=1, le=3)
    strength: int = Field(ge=0, le=20)
    intellect: int = Field(ge=0, le=20)
    charisma: int = Field(ge=0, le=20)
    luck: int = Field(ge=0, le=20)

class TapRequest(BaseModel):
    telegram_id: int
    taps: int = Field(ge=1, le=10)
    timestamp: float

class UnlockProfessionRequest(BaseModel):
    telegram_id: int
    profession_id: str

class CompleteTaskRequest(BaseModel):
    telegram_id: int
    profession_id: str
    task_index: int
    score: float = Field(ge=0, le=100)

class UpgradeRequest(BaseModel):
    telegram_id: int
    upgrade_type: str

# ===================== БАЗА ДАННЫХ =====================

DB_PATH = "reality_game.db"

def get_db():
    """Получение подключения к БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    """Инициализация таблиц БД"""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            avatar INTEGER NOT NULL DEFAULT 1,
            strength INTEGER NOT NULL DEFAULT 5,
            intellect INTEGER NOT NULL DEFAULT 5,
            charisma INTEGER NOT NULL DEFAULT 5,
            luck INTEGER NOT NULL DEFAULT 5,
            level INTEGER NOT NULL DEFAULT 1,
            xp INTEGER NOT NULL DEFAULT 0,
            xp_to_next INTEGER NOT NULL DEFAULT 100,
            coins INTEGER NOT NULL DEFAULT 0,
            tokens INTEGER NOT NULL DEFAULT 1,
            energy INTEGER NOT NULL DEFAULT 100,
            max_energy INTEGER NOT NULL DEFAULT 100,
            energy_regen REAL NOT NULL DEFAULT 2.0,
            tap_power INTEGER NOT NULL DEFAULT 1,
            max_taps INTEGER NOT NULL DEFAULT 1,
            combo_multiplier REAL NOT NULL DEFAULT 1.0,
            last_tap_time REAL NOT NULL DEFAULT 0,
            last_energy_update REAL NOT NULL DEFAULT 0,
            upgrade_tap_level INTEGER NOT NULL DEFAULT 0,
            upgrade_energy_level INTEGER NOT NULL DEFAULT 0,
            upgrade_multitap_level INTEGER NOT NULL DEFAULT 0,
            upgrade_regen_level INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS unlocked_professions (
            telegram_id INTEGER NOT NULL,
            profession_id TEXT NOT NULL,
            tasks_completed INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (telegram_id, profession_id),
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        );

        CREATE TABLE IF NOT EXISTS completed_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            profession_id TEXT NOT NULL,
            task_index INTEGER NOT NULL,
            score REAL NOT NULL,
            completed_at REAL NOT NULL,
            UNIQUE(telegram_id, profession_id, task_index),
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        );

        CREATE TABLE IF NOT EXISTS tap_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            taps INTEGER NOT NULL,
            timestamp REAL NOT NULL,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        );
    """)
    conn.commit()
    conn.close()

# ===================== ДАННЫЕ ПРОФЕССИЙ =====================

PROFESSIONS_DATA = {
    "it": {
        "name": "IT-сфера",
        "icon": "💻",
        "professions": {
            "frontend": {
                "name": "Frontend-разработчик",
                "icon": "🌐",
                "description": "Создаёт интерфейсы сайтов и приложений. Превращает дизайн в живые интерактивные страницы.",
                "tools": ["HTML/CSS", "JavaScript", "React", "Figma"],
                "cost": 1,
                "tasks": [
                    {"name": "CSS-головоломка", "description": "Расположи элементы по макету, выбирая правильные CSS-свойства", "type": "css_puzzle", "reward_coins": 50, "reward_xp": 30},
                    {"name": "Цветовой код", "description": "Подбери HEX-цвета по образцу интерфейса", "type": "color_match", "reward_coins": 60, "reward_xp": 35},
                    {"name": "Отладка бага", "description": "Найди и исправь ошибку в HTML-разметке", "type": "debug_html", "reward_coins": 70, "reward_xp": 40},
                    {"name": "Адаптивный дизайн", "description": "Настрой отображение сайта для мобильного экрана", "type": "responsive", "reward_coins": 80, "reward_xp": 45},
                    {"name": "Анимация кнопки", "description": "Создай эффект нажатия кнопки, подбирая параметры анимации", "type": "animation", "reward_coins": 100, "reward_xp": 60}
                ]
            },
            "backend": {
                "name": "Backend-разработчик",
                "icon": "⚙️",
                "description": "Строит серверную логику приложений. Работает с базами данных, API и архитектурой.",
                "tools": ["Python", "SQL", "Docker", "REST API"],
                "cost": 1,
                "tasks": [
                    {"name": "SQL-запрос", "description": "Составь SQL-запрос для получения данных из базы", "type": "sql_query", "reward_coins": 50, "reward_xp": 30},
                    {"name": "API-роутинг", "description": "Определи правильные HTTP-методы для каждого эндпоинта", "type": "api_routing", "reward_coins": 60, "reward_xp": 35},
                    {"name": "Отладка сервера", "description": "Найди ошибку в логике серверного кода", "type": "server_debug", "reward_coins": 70, "reward_xp": 40},
                    {"name": "Архитектор БД", "description": "Спроектируй структуру базы данных для интернет-магазина", "type": "db_design", "reward_coins": 80, "reward_xp": 45},
                    {"name": "Оптимизация", "description": "Ускорь медленный запрос, выбрав правильную стратегию", "type": "optimization", "reward_coins": 100, "reward_xp": 60}
                ]
            },
            "datasci": {
                "name": "Data Scientist",
                "icon": "📊",
                "description": "Анализирует данные и строит модели машинного обучения для прогнозов и решений.",
                "tools": ["Python", "Pandas", "TensorFlow", "Jupyter"],
                "cost": 1,
                "tasks": [
                    {"name": "Фильтрация данных", "description": "Очисти датасет от аномалий и пропущенных значений", "type": "data_filter", "reward_coins": 50, "reward_xp": 30},
                    {"name": "Визуализация", "description": "Выбери правильный тип графика для каждого типа данных", "type": "chart_pick", "reward_coins": 60, "reward_xp": 35},
                    {"name": "Корреляция", "description": "Определи, какие переменные связаны друг с другом", "type": "correlation", "reward_coins": 70, "reward_xp": 40},
                    {"name": "Классификация", "description": "Обучи простую модель, разделив данные на группы", "type": "classify", "reward_coins": 80, "reward_xp": 45},
                    {"name": "Прогноз", "description": "Предскажи будущее значение на основе тренда данных", "type": "prediction", "reward_coins": 100, "reward_xp": 60}
                ]
            },
            "cyber": {
                "name": "Кибербезопасник",
                "icon": "🔒",
                "description": "Защищает системы от хакеров, находит уязвимости и обеспечивает безопасность данных.",
                "tools": ["Linux", "Wireshark", "Nmap", "Metasploit"],
                "cost": 2,
                "tasks": [
                    {"name": "Анализ пароля", "description": "Оцени надёжность паролей и найди слабые", "type": "password_check", "reward_coins": 50, "reward_xp": 30},
                    {"name": "Фишинг-детектор", "description": "Определи фишинговые письма среди настоящих", "type": "phishing", "reward_coins": 60, "reward_xp": 35},
                    {"name": "Сетевой трафик", "description": "Найди подозрительные пакеты в сетевом логе", "type": "traffic_analysis", "reward_coins": 70, "reward_xp": 40},
                    {"name": "Шифрование", "description": "Расшифруй сообщение, определив тип шифра", "type": "decrypt", "reward_coins": 80, "reward_xp": 45},
                    {"name": "Инцидент", "description": "Отреагируй на кибератаку, выбирая правильные действия", "type": "incident", "reward_coins": 100, "reward_xp": 60}
                ]
            }
        }
    },
    "engineering": {
        "name": "Инженерия",
        "icon": "🔧",
        "professions": {
            "robotics": {
                "name": "Робототехник",
                "icon": "🤖",
                "description": "Проектирует и программирует роботов для промышленности, медицины и повседневной жизни.",
                "tools": ["Arduino", "ROS", "3D-печать", "C++"],
                "cost": 1,
                "tasks": [
                    {"name": "Сборка схемы", "description": "Соедини компоненты робота в правильном порядке", "type": "circuit_build", "reward_coins": 50, "reward_xp": 30},
                    {"name": "Программа движения", "description": "Запрограммируй робота для прохождения лабиринта", "type": "robot_maze", "reward_coins": 60, "reward_xp": 35},
                    {"name": "Датчики", "description": "Подбери правильные датчики для каждой задачи", "type": "sensors", "reward_coins": 70, "reward_xp": 40},
                    {"name": "Калибровка", "description": "Настрой параметры робота-манипулятора для точного захвата", "type": "calibration", "reward_coins": 80, "reward_xp": 45},
                    {"name": "Автопилот", "description": "Настрой алгоритм объезда препятствий для робота", "type": "autopilot", "reward_coins": 100, "reward_xp": 60}
                ]
            },
            "energy": {
                "name": "Энергетик",
                "icon": "⚡",
                "description": "Проектирует и обслуживает энергетические системы: от солнечных панелей до атомных станций.",
                "tools": ["AutoCAD", "MATLAB", "SCADA", "PLC"],
                "cost": 1,
                "tasks": [
                    {"name": "Цепь питания", "description": "Собери электрическую цепь для питания дома", "type": "power_circuit", "reward_coins": 50, "reward_xp": 30},
                    {"name": "Солнечная ферма", "description": "Расположи солнечные панели для максимальной выработки", "type": "solar_farm", "reward_coins": 60, "reward_xp": 35},
                    {"name": "Баланс сети", "description": "Распредели нагрузку между источниками энергии", "type": "grid_balance", "reward_coins": 70, "reward_xp": 40},
                    {"name": "Авария!", "description": "Локализуй и устрани аварию в энергосети", "type": "power_emergency", "reward_coins": 80, "reward_xp": 45},
                    {"name": "Проект станции", "description": "Спроектируй мини-электростанцию, балансируя параметры", "type": "station_design", "reward_coins": 100, "reward_xp": 60}
                ]
            }
        }
    },
    "medicine": {
        "name": "Медицина",
        "icon": "🏥",
        "professions": {
            "surgery": {
                "name": "Хирург",
                "icon": "🔪",
                "description": "Проводит операции для лечения болезней и травм. Требует точности и хладнокровия.",
                "tools": ["Скальпель", "Лапароскоп", "МРТ", "УЗИ"],
                "cost": 2,
                "tasks": [
                    {"name": "Анатомия", "description": "Определи расположение органов на схеме тела", "type": "anatomy", "reward_coins": 50, "reward_xp": 30},
                    {"name": "Точный разрез", "description": "Проведи линию разреза с хирургической точностью", "type": "precise_cut", "reward_coins": 60, "reward_xp": 35},
                    {"name": "Диагноз", "description": "Поставь диагноз по симптомам пациента", "type": "diagnosis", "reward_coins": 70, "reward_xp": 40},
                    {"name": "Приоритеты", "description": "Определи порядок действий в экстренной ситуации", "type": "triage", "reward_coins": 80, "reward_xp": 45},
                    {"name": "Операция", "description": "Выполни последовательность действий при операции", "type": "operation", "reward_coins": 100, "reward_xp": 60}
                ]
            },
            "biotech": {
                "name": "Биотехнолог",
                "icon": "🧬",
                "description": "Разрабатывает биологические технологии для медицины, сельского хозяйства и экологии.",
                "tools": ["ПЦР", "Секвенатор", "Биореактор", "CRISPR"],
                "cost": 1,
                "tasks": [
                    {"name": "ДНК-последовательность", "description": "Собери цепочку ДНК из нуклеотидов по образцу", "type": "dna_sequence", "reward_coins": 50, "reward_xp": 30},
                    {"name": "Среда культивирования", "description": "Подбери условия для выращивания клеток", "type": "culture", "reward_coins": 60, "reward_xp": 35},
                    {"name": "Генная модификация", "description": "Выбери правильный ген для модификации организма", "type": "gene_edit", "reward_coins": 70, "reward_xp": 40},
                    {"name": "Анализ белка", "description": "Определи структуру белка по его свойствам", "type": "protein", "reward_coins": 80, "reward_xp": 45},
                    {"name": "Вакцина", "description": "Разработай вакцину, выбирая компоненты и дозировку", "type": "vaccine", "reward_coins": 100, "reward_xp": 60}
                ]
            }
        }
    },
    "creative": {
        "name": "Творчество",
        "icon": "🎨",
        "professions": {
            "gamedev": {
                "name": "Геймдизайнер",
                "icon": "🎮",
                "description": "Проектирует игровые механики, уровни и баланс. Создаёт увлекательный игровой опыт.",
                "tools": ["Unity", "Unreal Engine", "Figma", "Aseprite"],
                "cost": 1,
                "tasks": [
                    {"name": "Баланс персонажей", "description": "Сбалансируй характеристики трёх классов персонажей", "type": "balance", "reward_coins": 50, "reward_xp": 30},
                    {"name": "Дизайн уровня", "description": "Расставь платформы и врагов для интересного уровня", "type": "level_design", "reward_coins": 60, "reward_xp": 35},
                    {"name": "Экономика игры", "description": "Настрой внутриигровую экономику чтобы она не ломалась", "type": "game_economy", "reward_coins": 70, "reward_xp": 40},
                    {"name": "Нарратив", "description": "Выбери ветки диалога для создания интересной истории", "type": "narrative", "reward_coins": 80, "reward_xp": 45},
                    {"name": "Прототип", "description": "Собери прототип игровой механики из готовых блоков", "type": "prototype", "reward_coins": 100, "reward_xp": 60}
                ]
            },
            "design": {
                "name": "Дизайнер",
                "icon": "✏️",
                "description": "Создаёт визуальные решения: логотипы, интерфейсы, рекламу, упаковку.",
                "tools": ["Figma", "Photoshop", "Illustrator", "Canva"],
                "cost": 1,
                "tasks": [
                    {"name": "Типографика", "description": "Подбери правильные шрифты и размеры для макета", "type": "typography", "reward_coins": 50, "reward_xp": 30},
                    {"name": "Цветовая палитра", "description": "Создай гармоничную палитру для бренда", "type": "palette", "reward_coins": 60, "reward_xp": 35},
                    {"name": "Композиция", "description": "Расположи элементы постера по правилам дизайна", "type": "composition", "reward_coins": 70, "reward_xp": 40},
                    {"name": "Логотип", "description": "Выбери лучший логотип из вариантов для компании", "type": "logo", "reward_coins": 80, "reward_xp": 45},
                    {"name": "Редизайн", "description": "Улучши плохой дизайн, находя и исправляя ошибки", "type": "redesign", "reward_coins": 100, "reward_xp": 60}
                ]
            }
        }
    },
    "business": {
        "name": "Бизнес",
        "icon": "📈",
        "professions": {
            "marketing": {
                "name": "Маркетолог",
                "icon": "📢",
                "description": "Продвигает продукты и бренды. Анализирует рынок, создаёт рекламные кампании.",
                "tools": ["Google Analytics", "Яндекс.Метрика", "Canva", "CRM"],
                "cost": 1,
                "tasks": [
                    {"name": "Целевая аудитория", "description": "Определи ЦА для нового продукта по характеристикам", "type": "target_audience", "reward_coins": 50, "reward_xp": 30},
                    {"name": "A/B тест", "description": "Выбери лучший вариант рекламы по метрикам", "type": "ab_test", "reward_coins": 60, "reward_xp": 35},
                    {"name": "Бюджет кампании", "description": "Распредели рекламный бюджет по каналам", "type": "budget", "reward_coins": 70, "reward_xp": 40},
                    {"name": "Контент-план", "description": "Составь контент-план для соцсетей на неделю", "type": "content_plan", "reward_coins": 80, "reward_xp": 45},
                    {"name": "Запуск продукта", "description": "Спланируй запуск продукта, выбирая стратегии", "type": "product_launch", "reward_coins": 100, "reward_xp": 60}
                ]
            },
            "finance": {
                "name": "Финансист",
                "icon": "💰",
                "description": "Управляет деньгами компаний и людей. Анализирует инвестиции, планирует бюджеты.",
                "tools": ["Excel", "1C", "Power BI", "Bloomberg"],
                "cost": 1,
                "tasks": [
                    {"name": "Бюджет", "description": "Составь бюджет проекта, балансируя расходы", "type": "make_budget", "reward_coins": 50, "reward_xp": 30},
                    {"name": "Инвестиции", "description": "Выбери портфель инвестиций с лучшим балансом риска", "type": "invest", "reward_coins": 60, "reward_xp": 35},
                    {"name": "Отчётность", "description": "Найди ошибки в финансовом отчёте", "type": "report_check", "reward_coins": 70, "reward_xp": 40},
                    {"name": "Налоги", "description": "Рассчитай налоги для малого бизнеса", "type": "taxes", "reward_coins": 80, "reward_xp": 45},
                    {"name": "Стартап", "description": "Оцени бизнес-план стартапа и реши, стоит ли инвестировать", "type": "startup_eval", "reward_coins": 100, "reward_xp": 60}
                ]
            }
        }
    },
    "science": {
        "name": "Наука",
        "icon": "🔬",
        "professions": {
            "chemistry": {
                "name": "Химик",
                "icon": "⚗️",
                "description": "Исследует вещества и их превращения. Создаёт новые материалы, лекарства, топливо.",
                "tools": ["Спектрометр", "Хроматограф", "Реактор", "ChemDraw"],
                "cost": 1,
                "tasks": [
                    {"name": "Уравнение реакции", "description": "Уравняй химическую реакцию, расставив коэффициенты", "type": "balance_equation", "reward_coins": 50, "reward_xp": 30},
                    {"name": "Таблица Менделеева", "description": "Определи элемент по его свойствам и положению", "type": "periodic_table", "reward_coins": 60, "reward_xp": 35},
                    {"name": "Титрование", "description": "Определи концентрацию раствора методом титрования", "type": "titration", "reward_coins": 70, "reward_xp": 40},
                    {"name": "Синтез", "description": "Выбери правильную последовательность синтеза вещества", "type": "synthesis", "reward_coins": 80, "reward_xp": 45},
                    {"name": "Анализ", "description": "Определи состав неизвестного вещества по данным анализа", "type": "analysis", "reward_coins": 100, "reward_xp": 60}
                ]
            },
            "physics": {
                "name": "Физик",
                "icon": "⚛️",
                "description": "Изучает фундаментальные законы природы. Работает с экспериментами и теоретическими моделями.",
                "tools": ["MATLAB", "LaTeX", "Осциллограф", "Детекторы"],
                "cost": 1,
                "tasks": [
                    {"name": "Закон Ньютона", "description": "Рассчитай траекторию тела с учётом всех сил", "type": "newton", "reward_coins": 50, "reward_xp": 30},
                    {"name": "Электрическая цепь", "description": "Рассчитай параметры сложной электрической цепи", "type": "electric", "reward_coins": 60, "reward_xp": 35},
                    {"name": "Оптика", "description": "Направь луч света через систему линз в цель", "type": "optics", "reward_coins": 70, "reward_xp": 40},
                    {"name": "Волны", "description": "Настрой параметры волны для резонанса", "type": "waves", "reward_coins": 80, "reward_xp": 45},
                    {"name": "Эксперимент", "description": "Спланируй и проведи физический эксперимент", "type": "experiment", "reward_coins": 100, "reward_xp": 60}
                ]
            }
        }
    }
}

# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================

def calculate_xp_for_level(level: int) -> int:
    """Расчёт необходимого XP для следующего уровня"""
    return 100 + (level - 1) * 50

def update_energy(user: dict) -> dict:
    """Обновление энергии на основе прошедшего времени"""
    now = time.time()
    elapsed = now - user["last_energy_update"]
    regen = user["energy_regen"]
    new_energy = min(user["max_energy"], user["energy"] + elapsed * regen)
    return {**user, "energy": int(new_energy), "last_energy_update": now}

def get_upgrade_cost(base: int, level: int) -> int:
    """Расчёт стоимости улучшения"""
    return int(base * (1.5 ** level))

# ===================== АНТИЧИТ =====================

tap_history = {}  # telegram_id -> [timestamps]

def check_anticheat(telegram_id: int, taps: int, timestamp: float) -> bool:
    """Проверка на читерство: слишком частые тапы"""
    now = time.time()
    if abs(now - timestamp) > 5:
        return False
    
    if telegram_id not in tap_history:
        tap_history[telegram_id] = []
    
    history = tap_history[telegram_id]
    history.append(now)
    # Оставляем только последние 3 секунды
    history[:] = [t for t in history if now - t < 3]
    
    # Максимум 30 тапов за 3 секунды (10 тапов/сек)
    if len(history) > 30:
        return False
    
    return True

# ===================== FASTAPI ПРИЛОЖЕНИЕ =====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация при старте"""
    init_db()
    yield

app = FastAPI(title="RE:ALITY: Профессии", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== API ЭНДПОИНТЫ =====================

@app.get("/api/professions")
async def get_professions():
    """Получить все профессии"""
    return JSONResponse(content=PROFESSIONS_DATA)

@app.post("/api/register")
async def register(req: RegisterRequest):
    """Регистрация нового пользователя"""
    # Проверка суммы очков
    if req.strength + req.intellect + req.charisma + req.luck != 20:
        raise HTTPException(400, "Сумма характеристик должна быть 20")
    
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT telegram_id FROM users WHERE telegram_id = ?",
            (req.telegram_id,)
        ).fetchone()
        
        if existing:
            raise HTTPException(400, "Пользователь уже зарегистрирован")
        
        now = time.time()
        conn.execute("""
            INSERT INTO users (telegram_id, name, avatar, strength, intellect, charisma, luck,
                             last_energy_update, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (req.telegram_id, req.name, req.avatar, req.strength, req.intellect,
              req.charisma, req.luck, now, now))
        conn.commit()
        
        user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (req.telegram_id,)).fetchone()
        return JSONResponse(content=dict(user))
    finally:
        conn.close()

@app.get("/api/user/{telegram_id}")
async def get_user(telegram_id: int):
    """Получение данных пользователя"""
    conn = get_db()
    try:
        user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
        if not user:
            raise HTTPException(404, "Пользователь не найден")
        
        user_dict = dict(user)
        user_dict = update_energy(user_dict)
        
        # Обновляем энергию в БД
        conn.execute(
            "UPDATE users SET energy = ?, last_energy_update = ? WHERE telegram_id = ?",
            (user_dict["energy"], user_dict["last_energy_update"], telegram_id)
        )
        
        # Получаем открытые профессии
        profs = conn.execute(
            "SELECT * FROM unlocked_professions WHERE telegram_id = ?",
            (telegram_id,)
        ).fetchall()
        user_dict["unlocked_professions"] = [dict(p) for p in profs]
        
        # Получаем выполненные задания
        tasks = conn.execute(
            "SELECT * FROM completed_tasks WHERE telegram_id = ?",
            (telegram_id,)
        ).fetchall()
        user_dict["completed_tasks"] = [dict(t) for t in tasks]
        
        conn.commit()
        return JSONResponse(content=user_dict)
    finally:
        conn.close()

@app.post("/api/tap")
async def handle_tap(req: TapRequest):
    """Обработка тапов"""
    if not check_anticheat(req.telegram_id, req.taps, req.timestamp):
        raise HTTPException(429, "Слишком быстро! Притормози немного.")
    
    conn = get_db()
    try:
        user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (req.telegram_id,)).fetchone()
        if not user:
            raise HTTPException(404, "Пользователь не найден")
        
        user_dict = update_energy(dict(user))
        
        # Проверка энергии
        actual_taps = min(req.taps, user_dict["energy"], user_dict["max_taps"])
        if actual_taps <= 0:
            raise HTTPException(400, "Недостаточно энергии!")
        
        # Расчёт комбо-множителя
        now = time.time()
        time_since_last = now - user_dict["last_tap_time"]
        if time_since_last < 1.0:
            combo = min(5.0, user_dict["combo_multiplier"] + 0.2)
        elif time_since_last < 2.0:
            combo = user_dict["combo_multiplier"]
        else:
            combo = 1.0
        
        # Расчёт заработка с учётом характеристик
        luck_bonus = 1 + user_dict["luck"] * 0.05  # До +100% от удачи
        base_coins = user_dict["tap_power"] * actual_taps
        total_coins = int(base_coins * combo * luck_bonus)
        
        # XP за тапы
        xp_gain = actual_taps
        new_xp = user_dict["xp"] + xp_gain
        new_level = user_dict["level"]
        new_tokens = user_dict["tokens"]
        xp_to_next = user_dict["xp_to_next"]
        level_up = False
        
        # Проверка повышения уровня
        while new_xp >= xp_to_next:
            new_xp -= xp_to_next
            new_level += 1
            new_tokens += 1
            xp_to_next = calculate_xp_for_level(new_level)
            level_up = True
        
        # Обновление данных
        new_energy = user_dict["energy"] - actual_taps
        new_coins = user_dict["coins"] + total_coins
        
        conn.execute("""
            UPDATE users SET coins = ?, energy = ?, xp = ?, level = ?, tokens = ?,
                           xp_to_next = ?, combo_multiplier = ?, last_tap_time = ?,
                           last_energy_update = ?
            WHERE telegram_id = ?
        """, (new_coins, new_energy, new_xp, new_level, new_tokens,
              xp_to_next, combo, now, now, req.telegram_id))
        
        # Логируем тапы для аналитики
        conn.execute(
            "INSERT INTO tap_log (telegram_id, taps, timestamp) VALUES (?, ?, ?)",
            (req.telegram_id, actual_taps, now)
        )
        
        conn.commit()
        
        return JSONResponse(content={
            "coins_earned": total_coins,
            "total_coins": new_coins,
            "energy": new_energy,
            "max_energy": user_dict["max_energy"],
            "xp": new_xp,
            "xp_to_next": xp_to_next,
            "level": new_level,
            "tokens": new_tokens,
            "combo": round(combo, 1),
            "level_up": level_up,
            "actual_taps": actual_taps
        })
    finally:
        conn.close()

@app.post("/api/unlock-profession")
async def unlock_profession(req: UnlockProfessionRequest):
    """Открытие профессии за токены"""
    conn = get_db()
    try:
        user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (req.telegram_id,)).fetchone()
        if not user:
            raise HTTPException(404, "Пользователь не найден")
        
        # Поиск профессии
        prof = None
        for sphere in PROFESSIONS_DATA.values():
            if req.profession_id in sphere["professions"]:
                prof = sphere["professions"][req.profession_id]
                break
        
        if not prof:
            raise HTTPException(404, "Профессия не найдена")
        
        # Проверка: не открыта ли уже
        existing = conn.execute(
            "SELECT * FROM unlocked_professions WHERE telegram_id = ? AND profession_id = ?",
            (req.telegram_id, req.profession_id)
        ).fetchone()
        if existing:
            raise HTTPException(400, "Профессия уже открыта")
        
        # Проверка токенов
        if user["tokens"] < prof["cost"]:
            raise HTTPException(400, "Недостаточно токенов!")
        
        # Списываем токены и открываем
        conn.execute(
            "UPDATE users SET tokens = tokens - ? WHERE telegram_id = ?",
            (prof["cost"], req.telegram_id)
        )
        conn.execute(
            "INSERT INTO unlocked_professions (telegram_id, profession_id) VALUES (?, ?)",
            (req.telegram_id, req.profession_id)
        )
        conn.commit()
        
        return JSONResponse(content={"success": True, "tokens_remaining": user["tokens"] - prof["cost"]})
    finally:
        conn.close()

@app.post("/api/complete-task")
async def complete_task(req: CompleteTaskRequest):
    """Завершение задания профессии"""
    conn = get_db()
    try:
        user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (req.telegram_id,)).fetchone()
        if not user:
            raise HTTPException(404, "Пользователь не найден")
        
        # Проверка: открыта ли профессия
        unlocked = conn.execute(
            "SELECT * FROM unlocked_professions WHERE telegram_id = ? AND profession_id = ?",
            (req.telegram_id, req.profession_id)
        ).fetchone()
        if not unlocked:
            raise HTTPException(400, "Профессия не открыта!")
        
        # Проверка: не выполнено ли уже
        done = conn.execute(
            "SELECT * FROM completed_tasks WHERE telegram_id = ? AND profession_id = ? AND task_index = ?",
            (req.telegram_id, req.profession_id, req.task_index)
        ).fetchone()
        if done:
            raise HTTPException(400, "Задание уже выполнено!")
        
        # Получаем данные задания
        prof = None
        for sphere in PROFESSIONS_DATA.values():
            if req.profession_id in sphere["professions"]:
                prof = sphere["professions"][req.profession_id]
                break
        
        if not prof or req.task_index >= len(prof["tasks"]):
            raise HTTPException(404, "Задание не найдено")
        
        task = prof["tasks"][req.task_index]
        
        # Расчёт награды с учётом характеристик и оценки
        score_multiplier = req.score / 100.0
        intellect_bonus = 1 + user["intellect"] * 0.05
        coin_reward = int(task["reward_coins"] * score_multiplier * intellect_bonus)
        xp_reward = int(task["reward_xp"] * score_multiplier)
        
        # Обновляем прогресс
        now = time.time()
        conn.execute(
            "INSERT INTO completed_tasks (telegram_id, profession_id, task_index, score, completed_at) VALUES (?, ?, ?, ?, ?)",
            (req.telegram_id, req.profession_id, req.task_index, req.score, now)
        )
        conn.execute(
            "UPDATE unlocked_professions SET tasks_completed = tasks_completed + 1 WHERE telegram_id = ? AND profession_id = ?",
            (req.telegram_id, req.profession_id)
        )
        
        # Начисляем награды
        new_xp = user["xp"] + xp_reward
        new_level = user["level"]
        new_tokens = user["tokens"]
        xp_to_next = user["xp_to_next"]
        level_up = False
        
        while new_xp >= xp_to_next:
            new_xp -= xp_to_next
            new_level += 1
            new_tokens += 1
            xp_to_next = calculate_xp_for_level(new_level)
            level_up = True
        
        new_coins = user["coins"] + coin_reward
        
        conn.execute("""
            UPDATE users SET coins = ?, xp = ?, level = ?, tokens = ?, xp_to_next = ?
            WHERE telegram_id = ?
        """, (new_coins, new_xp, new_level, new_tokens, xp_to_next, req.telegram_id))
        
        conn.commit()
        
        return JSONResponse(content={
            "success": True,
            "coins_earned": coin_reward,
            "xp_earned": xp_reward,
            "total_coins": new_coins,
            "xp": new_xp,
            "level": new_level,
            "tokens": new_tokens,
            "level_up": level_up,
            "score": req.score
        })
    finally:
        conn.close()

@app.post("/api/upgrade")
async def buy_upgrade(req: UpgradeRequest):
    """Покупка улучшения"""
    conn = get_db()
    try:
        user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (req.telegram_id,)).fetchone()
        if not user:
            raise HTTPException(404, "Пользователь не найден")
        
        user_dict = dict(user)
        
        upgrades = {
            "tap_power": {
                "field": "upgrade_tap_level",
                "base_cost": 100,
                "apply": lambda u, l: {"tap_power": u["tap_power"] + 1}
            },
            "max_energy": {
                "field": "upgrade_energy_level",
                "base_cost": 150,
                "apply": lambda u, l: {"max_energy": u["max_energy"] + 20}
            },
            "multitap": {
                "field": "upgrade_multitap_level",
                "base_cost": 300,
                "apply": lambda u, l: {"max_taps": min(5, u["max_taps"] + 1)},
                "max_level": 4
            },
            "regen": {
                "field": "upgrade_regen_level",
                "base_cost": 200,
                "apply": lambda u, l: {"energy_regen": round(u["energy_regen"] + 0.5, 1)}
            }
        }
        
        if req.upgrade_type not in upgrades:
            raise HTTPException(400, "Неизвестное улучшение")
        
        upg = upgrades[req.upgrade_type]
        current_level = user_dict[upg["field"]]
        
        # Проверка максимального уровня
        if "max_level" in upg and current_level >= upg["max_level"]:
            raise HTTPException(400, "Максимальный уровень!")
        
        cost = get_upgrade_cost(upg["base_cost"], current_level)
        
        if user_dict["coins"] < cost:
            raise HTTPException(400, "Недостаточно монет!")
        
        # Применяем улучшение
        changes = upg["apply"](user_dict, current_level)
        set_clauses = [f"{k} = ?" for k in changes.keys()]
        set_clauses.append(f"{upg['field']} = ?")
        set_clauses.append("coins = ?")
        
        values = list(changes.values())
        values.append(current_level + 1)
        values.append(user_dict["coins"] - cost)
        values.append(req.telegram_id)
        
        conn.execute(
            f"UPDATE users SET {', '.join(set_clauses)} WHERE telegram_id = ?",
            values
        )
        conn.commit()
        
        updated_user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (req.telegram_id,)).fetchone()
        return JSONResponse(content=dict(updated_user))
    finally:
        conn.close()

# ===================== ФРОНТЕНД =====================

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Отдача HTML-фронтенда"""
    return FRONTEND_HTML

# HTML фронтенд загружается из отдельного файла
FRONTEND_HTML = open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend.html"),
    "r", encoding="utf-8"
).read() if os.path.exists(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend.html")
) else "<h1>frontend.html not found</h1>"

# ===================== ЗАПУСК =====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
