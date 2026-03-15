"""
RE:ALITY: Профессии — FastAPI бэкенд
Telegram Mini App для профориентации подростков
"""

import os
import time
import math
import json
import hashlib
import hmac
import urllib.parse
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database as db

app = FastAPI(title="RE:ALITY Профессии")

# CORS для Telegram
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статика (аватары и т.п.) — создаём папку если нет
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# ============ Константы ============

XP_PER_LEVEL = [0, 100, 250, 500, 900, 1500, 2500, 4000, 6500, 10000]  # XP для уровней 1-10
MAX_LEVEL = 10
COMBO_WINDOW = 1.5  # секунды между тапами для комбо
MAX_COMBO_MULT = 5

# Стоимости улучшений (базовая, множитель за уровень)
UPGRADES = {
    "tap": {"base_cost": 50, "mult": 2.0, "max_level": 10},
    "energy": {"base_cost": 80, "mult": 2.2, "max_level": 10},
    "multi": {"base_cost": 200, "mult": 2.5, "max_level": 4},
    "regen": {"base_cost": 100, "mult": 2.0, "max_level": 10},
}


# ============ Утилиты ============

def xp_for_level(level: int) -> int:
    """Сколько XP нужно для следующего уровня"""
    if level <= 0:
        return 100
    if level < len(XP_PER_LEVEL):
        return XP_PER_LEVEL[level]
    return int(XP_PER_LEVEL[-1] * (1.5 ** (level - len(XP_PER_LEVEL) + 1)))


def upgrade_cost(base: int, mult: float, level: int) -> int:
    """Стоимость улучшения"""
    return int(base * (mult ** level))


def regenerate_energy(user: dict) -> dict:
    """Пересчитать энергию на основе времени"""
    now = time.time()
    elapsed = now - user["last_energy_update"]
    regen = user["energy_regen"]
    new_energy = min(user["max_energy"], user["energy"] + elapsed * regen)
    user["energy"] = int(new_energy)
    user["last_energy_update"] = now
    return user


def validate_telegram_data(init_data: str) -> Optional[int]:
    """
    Проверка данных от Telegram Web App.
    Возвращает tg_id или None если невалидно.
    """
    if not BOT_TOKEN:
        # Если нет токена — режим разработки, доверяем
        try:
            parsed = urllib.parse.parse_qs(init_data)
            user_data = json.loads(parsed.get("user", ["{}"])[0])
            return user_data.get("id")
        except:
            return None

    try:
        parsed = urllib.parse.parse_qs(init_data)
        check_hash = parsed.get("hash", [None])[0]
        if not check_hash:
            return None

        # Собираем строку для проверки
        data_pairs = []
        for key, val in parsed.items():
            if key != "hash":
                data_pairs.append(f"{key}={val[0]}")
        data_pairs.sort()
        data_check_string = "\n".join(data_pairs)

        # HMAC-SHA256
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if computed == check_hash:
            user_data = json.loads(parsed.get("user", ["{}"])[0])
            return user_data.get("id")
    except:
        pass
    return None


# ============ Модели запросов ============

class RegisterRequest(BaseModel):
    init_data: str = ""
    tg_id: int = 0
    name: str
    avatar: int
    stats: dict  # {"str": X, "int": X, "cha": X, "luck": X}


class TapRequest(BaseModel):
    init_data: str = ""
    tg_id: int = 0
    taps: int = 1


class AuthRequest(BaseModel):
    init_data: str = ""
    tg_id: int = 0


class UnlockRequest(BaseModel):
    init_data: str = ""
    tg_id: int = 0
    profession_id: str


class UpgradeRequest(BaseModel):
    init_data: str = ""
    tg_id: int = 0
    upgrade_type: str  # "tap" | "energy" | "multi" | "regen"


class TaskCompleteRequest(BaseModel):
    init_data: str = ""
    tg_id: int = 0
    profession_id: str
    task_index: int
    score: int = 100


def get_tg_id(req) -> int:
    """Извлечь tg_id из запроса"""
    if req.init_data:
        tg_id = validate_telegram_data(req.init_data)
        if tg_id:
            return tg_id
    if req.tg_id:
        return req.tg_id
    raise HTTPException(400, "Не удалось определить пользователя")


# ============ API ============

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Отдать главную страницу"""
    return FileResponse("index.html")


# Отдача аватаров из корня
@app.get("/hero1.png")
async def hero1():
    return FileResponse("hero1.png")

@app.get("/hero2.png")
async def hero2():
    return FileResponse("hero2.png")

@app.get("/hero3.png")
async def hero3():
    return FileResponse("hero3.png")


@app.post("/api/auth")
async def auth(req: AuthRequest):
    """Авторизация / получение данных пользователя"""
    tg_id = get_tg_id(req)
    user = db.get_user(tg_id)
    if not user:
        db.create_user(tg_id)
        user = db.get_user(tg_id)

    # Регенерация энергии
    user = regenerate_energy(user)
    db.update_user_fields(tg_id, {
        "energy": user["energy"],
        "last_energy_update": user["last_energy_update"]
    })

    unlocked = db.get_unlocked_professions(tg_id)
    completed = db.get_completed_tasks(tg_id)

    return {
        "user": user,
        "unlocked_professions": unlocked,
        "completed_tasks": completed,
        "xp_needed": xp_for_level(user["level"])
    }


@app.post("/api/register")
async def register(req: RegisterRequest):
    """Регистрация персонажа"""
    tg_id = get_tg_id(req)

    # Валидация
    name = req.name.strip()[:8]
    if not name:
        raise HTTPException(400, "Введите имя")
    if req.avatar not in [1, 2, 3]:
        raise HTTPException(400, "Неверный аватар")

    stats = req.stats
    total = stats.get("str", 0) + stats.get("int", 0) + stats.get("cha", 0) + stats.get("luck", 0)
    if total != 20:
        raise HTTPException(400, f"Сумма характеристик должна быть 20 (сейчас {total})")
    for v in stats.values():
        if v < 1 or v > 14:
            raise HTTPException(400, "Каждая характеристика от 1 до 14")

    db.create_user(tg_id)
    db.register_user(tg_id, name, req.avatar, stats)
    user = db.get_user(tg_id)

    return {"user": user, "xp_needed": xp_for_level(user["level"])}


@app.post("/api/tap")
async def tap(req: TapRequest, request: Request):
    """Обработка тапов"""
    tg_id = get_tg_id(req)
    user = db.get_user(tg_id)
    if not user or not user["registered"]:
        raise HTTPException(400, "Сначала зарегистрируйтесь")

    taps = min(req.taps, user["multi_tap"] * 5)  # Максимум разумное количество
    if taps < 1:
        taps = 1

    # Античит
    ip = request.client.host if request.client else ""
    db.log_taps(tg_id, taps, ip)
    if not db.check_tap_rate(tg_id):
        raise HTTPException(429, "Слишком быстро! Подождите немного.")

    # Регенерация энергии
    user = regenerate_energy(user)

    # Проверка энергии
    actual_taps = min(taps, user["energy"])
    if actual_taps <= 0:
        db.update_user_fields(tg_id, {
            "energy": user["energy"],
            "last_energy_update": user["last_energy_update"]
        })
        return {"user": user, "earned": 0, "combo": 1, "xp_needed": xp_for_level(user["level"])}

    # Комбо-система
    now = time.time()
    if now - user["combo_last_tap"] < COMBO_WINDOW:
        combo = min(user["combo_count"] + 1, MAX_COMBO_MULT * 10)
    else:
        combo = 1
    combo_mult = min(1 + (combo // 10), MAX_COMBO_MULT)

    # Бонус от силы
    str_bonus = 1 + user["stat_str"] * 0.05

    # Монеты
    base_coins = user["coins_per_tap"] * actual_taps
    earned = int(base_coins * combo_mult * str_bonus)

    # XP
    xp_gain = actual_taps * 2
    # Бонус от интеллекта
    xp_gain = int(xp_gain * (1 + user["stat_int"] * 0.03))

    new_coins = user["coins"] + earned
    new_xp = user["xp"] + xp_gain
    new_energy = user["energy"] - actual_taps
    new_level = user["level"]
    new_tokens = user["tokens"]

    # Проверка левел-апа
    level_up = False
    while new_level < MAX_LEVEL and new_xp >= xp_for_level(new_level):
        new_xp -= xp_for_level(new_level)
        new_level += 1
        new_tokens += 1  # +1 токен за уровень
        level_up = True

    db.update_user_fields(tg_id, {
        "coins": new_coins,
        "xp": new_xp,
        "level": new_level,
        "tokens": new_tokens,
        "energy": new_energy,
        "combo_count": combo,
        "combo_last_tap": now,
        "last_energy_update": now
    })

    user = db.get_user(tg_id)

    return {
        "user": user,
        "earned": earned,
        "combo": combo_mult,
        "xp_gained": xp_gain,
        "level_up": level_up,
        "xp_needed": xp_for_level(user["level"])
    }


@app.post("/api/unlock")
async def unlock_profession(req: UnlockRequest):
    """Открыть профессию за токены"""
    tg_id = get_tg_id(req)
    user = db.get_user(tg_id)
    if not user:
        raise HTTPException(400, "Пользователь не найден")

    cost = 1  # Стоимость в токенах
    if user["tokens"] < cost:
        raise HTTPException(400, "Недостаточно токенов профессий")

    # Проверить не открыта ли уже
    unlocked = db.get_unlocked_professions(tg_id)
    if req.profession_id in unlocked:
        raise HTTPException(400, "Профессия уже открыта")

    db.update_user_field(tg_id, "tokens", user["tokens"] - cost)
    db.unlock_profession(tg_id, req.profession_id)

    user = db.get_user(tg_id)
    unlocked = db.get_unlocked_professions(tg_id)

    return {
        "user": user,
        "unlocked_professions": unlocked,
        "xp_needed": xp_for_level(user["level"])
    }


@app.post("/api/upgrade")
async def buy_upgrade(req: UpgradeRequest):
    """Купить улучшение"""
    tg_id = get_tg_id(req)
    user = db.get_user(tg_id)
    if not user:
        raise HTTPException(400, "Пользователь не найден")

    utype = req.upgrade_type
    if utype not in UPGRADES:
        raise HTTPException(400, "Неверный тип улучшения")

    cfg = UPGRADES[utype]
    level_field = f"upg_{utype}_level"
    current_level = user[level_field]

    if current_level >= cfg["max_level"]:
        raise HTTPException(400, "Максимальный уровень!")

    cost = upgrade_cost(cfg["base_cost"], cfg["mult"], current_level)
    if user["coins"] < cost:
        raise HTTPException(400, f"Нужно {cost} монет")

    # Применяем улучшение
    updates = {
        "coins": user["coins"] - cost,
        level_field: current_level + 1
    }

    if utype == "tap":
        updates["coins_per_tap"] = user["coins_per_tap"] + 1
    elif utype == "energy":
        updates["max_energy"] = user["max_energy"] + 20
        updates["energy"] = min(user["energy"] + 20, user["max_energy"] + 20)
    elif utype == "multi":
        updates["multi_tap"] = user["multi_tap"] + 1
    elif utype == "regen":
        updates["energy_regen"] = round(user["energy_regen"] + 0.5, 1)

    db.update_user_fields(tg_id, updates)
    user = db.get_user(tg_id)

    return {
        "user": user,
        "xp_needed": xp_for_level(user["level"])
    }


@app.post("/api/task/complete")
async def task_complete(req: TaskCompleteRequest):
    """Завершение задания профессии"""
    tg_id = get_tg_id(req)
    user = db.get_user(tg_id)
    if not user:
        raise HTTPException(400, "Пользователь не найден")

    # Проверить что профессия открыта
    unlocked = db.get_unlocked_professions(tg_id)
    if req.profession_id not in unlocked:
        raise HTTPException(400, "Профессия не открыта")

    # Проверить не выполнено ли уже
    completed = db.get_completed_tasks(tg_id, req.profession_id)
    for c in completed:
        if c["task_index"] == req.task_index:
            return {"user": user, "already_completed": True, "xp_needed": xp_for_level(user["level"])}

    # Награды за задание
    score = min(max(req.score, 0), 100)
    coin_reward = 20 + int(score * 0.5)
    xp_reward = 30 + int(score * 0.3)

    # Бонус удачи
    import random
    if random.random() < user["stat_luck"] * 0.02:
        coin_reward *= 2  # Двойная награда!

    db.complete_task(tg_id, req.profession_id, req.task_index, score)

    new_coins = user["coins"] + coin_reward
    new_xp = user["xp"] + xp_reward
    new_level = user["level"]
    new_tokens = user["tokens"]

    while new_level < MAX_LEVEL and new_xp >= xp_for_level(new_level):
        new_xp -= xp_for_level(new_level)
        new_level += 1
        new_tokens += 1

    db.update_user_fields(tg_id, {
        "coins": new_coins,
        "xp": new_xp,
        "level": new_level,
        "tokens": new_tokens,
    })

    user = db.get_user(tg_id)
    completed = db.get_completed_tasks(tg_id, req.profession_id)

    return {
        "user": user,
        "coin_reward": coin_reward,
        "xp_reward": xp_reward,
        "completed_tasks": completed,
        "xp_needed": xp_for_level(user["level"])
    }


@app.get("/api/professions")
async def get_professions():
    """Каталог всех профессий и сфер"""
    return {"spheres": PROFESSIONS_DATA}


# ============ Данные профессий ============

PROFESSIONS_DATA = [
    {
        "id": "it",
        "name": "IT-сфера",
        "icon": "💻",
        "professions": [
            {
                "id": "frontend",
                "name": "Frontend-разработчик",
                "icon": "🌐",
                "desc": "Создаёт интерфейсы сайтов и приложений, которые видят пользователи",
                "tools": ["HTML/CSS", "JavaScript", "React", "Figma"],
                "cost": 1,
                "tasks": [
                    {"title": "Верстка кнопки", "type": "code_match", "desc": "Собери CSS-код для стильной кнопки"},
                    {"title": "Исправь баг", "type": "find_bug", "desc": "Найди ошибку в HTML-коде страницы"},
                    {"title": "Цветовая палитра", "type": "color_pick", "desc": "Подбери цвета для интерфейса по брифу"},
                    {"title": "Адаптивность", "type": "drag_arrange", "desc": "Расположи элементы для мобильной версии"},
                    {"title": "Финальный проект", "type": "quiz", "desc": "Ответь на вопросы по Frontend-разработке"}
                ]
            },
            {
                "id": "backend",
                "name": "Backend-разработчик",
                "icon": "⚙️",
                "desc": "Программирует серверную логику, базы данных и API",
                "tools": ["Python", "SQL", "Docker", "Linux"],
                "cost": 1,
                "tasks": [
                    {"title": "SQL-запрос", "type": "code_match", "desc": "Напиши запрос для получения данных"},
                    {"title": "API-дизайн", "type": "drag_arrange", "desc": "Спроектируй REST API для магазина"},
                    {"title": "Найди уязвимость", "type": "find_bug", "desc": "Найди проблему безопасности в коде"},
                    {"title": "Оптимизация", "type": "quiz", "desc": "Выбери оптимальное решение для нагрузки"},
                    {"title": "Архитектура", "type": "drag_arrange", "desc": "Спроектируй архитектуру сервиса"}
                ]
            },
            {
                "id": "datasci",
                "name": "Data Scientist",
                "icon": "📊",
                "desc": "Анализирует данные и строит предсказательные модели с помощью ML",
                "tools": ["Python", "Pandas", "TensorFlow", "Jupyter"],
                "cost": 1,
                "tasks": [
                    {"title": "Анализ графика", "type": "quiz", "desc": "Определи тренд по графику данных"},
                    {"title": "Чистка данных", "type": "find_bug", "desc": "Найди аномалии в датасете"},
                    {"title": "Выбор модели", "type": "quiz", "desc": "Подбери правильный алгоритм ML"},
                    {"title": "Визуализация", "type": "color_pick", "desc": "Выбери лучший тип графика для данных"},
                    {"title": "A/B тест", "type": "quiz", "desc": "Проанализируй результаты эксперимента"}
                ]
            },
            {
                "id": "cybersec",
                "name": "Кибербезопасность",
                "icon": "🛡️",
                "desc": "Защищает системы от взломов и кибератак",
                "tools": ["Kali Linux", "Wireshark", "Metasploit", "Burp Suite"],
                "cost": 1,
                "tasks": [
                    {"title": "Анализ пароля", "type": "quiz", "desc": "Оцени надёжность паролей"},
                    {"title": "Фишинг-тест", "type": "find_bug", "desc": "Определи фишинговое письмо среди настоящих"},
                    {"title": "Сетевой трафик", "type": "quiz", "desc": "Найди подозрительную активность в логах"},
                    {"title": "Шифрование", "type": "code_match", "desc": "Расшифруй сообщение с помощью ключа"},
                    {"title": "Инцидент", "type": "drag_arrange", "desc": "Составь план реагирования на взлом"}
                ]
            }
        ]
    },
    {
        "id": "engineering",
        "name": "Инженерия",
        "icon": "🔧",
        "professions": [
            {
                "id": "robotics",
                "name": "Робототехник",
                "icon": "🤖",
                "desc": "Проектирует и программирует роботов для различных задач",
                "tools": ["Arduino", "ROS", "C++", "3D-печать"],
                "cost": 1,
                "tasks": [
                    {"title": "Сборка схемы", "type": "drag_arrange", "desc": "Собери электрическую цепь робота"},
                    {"title": "Программа движения", "type": "code_match", "desc": "Напиши код для движения робота"},
                    {"title": "Датчики", "type": "quiz", "desc": "Подбери датчики для задачи"},
                    {"title": "Отладка", "type": "find_bug", "desc": "Найди ошибку в поведении робота"},
                    {"title": "Проект", "type": "drag_arrange", "desc": "Спроектируй робота-помощника"}
                ]
            },
            {
                "id": "energy",
                "name": "Энергетик",
                "icon": "⚡",
                "desc": "Работает с энергосистемами, возобновляемой энергией",
                "tools": ["AutoCAD", "MATLAB", "SCADA", "PLC"],
                "cost": 1,
                "tasks": [
                    {"title": "Расчёт мощности", "type": "quiz", "desc": "Рассчитай потребление для здания"},
                    {"title": "Солнечные панели", "type": "drag_arrange", "desc": "Расположи панели для макс. КПД"},
                    {"title": "Диагностика", "type": "find_bug", "desc": "Найди неисправность в электросети"},
                    {"title": "Энергобаланс", "type": "quiz", "desc": "Оптимизируй потребление предприятия"},
                    {"title": "Проект станции", "type": "drag_arrange", "desc": "Спроектируй мини-электростанцию"}
                ]
            }
        ]
    },
    {
        "id": "medicine",
        "name": "Медицина",
        "icon": "🏥",
        "professions": [
            {
                "id": "diagnostics",
                "name": "Врач-диагност",
                "icon": "🔬",
                "desc": "Ставит диагнозы по симптомам, анализам и обследованиям",
                "tools": ["МРТ", "УЗИ", "Анализы крови", "ЭКГ"],
                "cost": 1,
                "tasks": [
                    {"title": "Сбор анамнеза", "type": "quiz", "desc": "Задай правильные вопросы пациенту"},
                    {"title": "Анализ результатов", "type": "find_bug", "desc": "Найди отклонения в анализах"},
                    {"title": "Дифференциация", "type": "quiz", "desc": "Выбери верный диагноз из похожих"},
                    {"title": "Назначения", "type": "drag_arrange", "desc": "Составь план обследования"},
                    {"title": "Сложный случай", "type": "quiz", "desc": "Разбери клинический кейс"}
                ]
            },
            {
                "id": "biotech",
                "name": "Биотехнолог",
                "icon": "🧬",
                "desc": "Разрабатывает лекарства и биопрепараты на основе живых систем",
                "tools": ["ПЦР", "Секвенирование", "Биореакторы", "CRISPR"],
                "cost": 1,
                "tasks": [
                    {"title": "Протокол ПЦР", "type": "drag_arrange", "desc": "Расставь этапы ПЦР в правильном порядке"},
                    {"title": "Анализ генома", "type": "find_bug", "desc": "Найди мутацию в последовательности ДНК"},
                    {"title": "Подбор среды", "type": "quiz", "desc": "Выбери питательную среду для культуры"},
                    {"title": "Биореактор", "type": "quiz", "desc": "Оптимизируй параметры выращивания"},
                    {"title": "CRISPR-дизайн", "type": "code_match", "desc": "Подбери гидовую РНК для редактирования"}
                ]
            }
        ]
    },
    {
        "id": "creative",
        "name": "Творчество",
        "icon": "🎨",
        "professions": [
            {
                "id": "gamedev",
                "name": "Геймдизайнер",
                "icon": "🎮",
                "desc": "Придумывает механики и уровни для видеоигр",
                "tools": ["Unity", "Unreal Engine", "Figma", "Photoshop"],
                "cost": 1,
                "tasks": [
                    {"title": "Баланс персонажей", "type": "quiz", "desc": "Сбалансируй характеристики героев"},
                    {"title": "Дизайн уровня", "type": "drag_arrange", "desc": "Расположи объекты на игровом уровне"},
                    {"title": "Экономика игры", "type": "quiz", "desc": "Настрой внутриигровую экономику"},
                    {"title": "Нарратив", "type": "quiz", "desc": "Построй сюжетное дерево диалогов"},
                    {"title": "Прототип", "type": "drag_arrange", "desc": "Собери прототип игровой механики"}
                ]
            },
            {
                "id": "design",
                "name": "UX/UI Дизайнер",
                "icon": "✏️",
                "desc": "Создаёт удобные и красивые интерфейсы для приложений",
                "tools": ["Figma", "Sketch", "Adobe XD", "Principle"],
                "cost": 1,
                "tasks": [
                    {"title": "Цветовая схема", "type": "color_pick", "desc": "Подбери палитру для приложения банка"},
                    {"title": "Юзабилити", "type": "find_bug", "desc": "Найди UX-проблемы на экране"},
                    {"title": "Компоненты", "type": "drag_arrange", "desc": "Собери UI-кит из компонентов"},
                    {"title": "Прототип", "type": "quiz", "desc": "Спроектируй пользовательский путь"},
                    {"title": "Редизайн", "type": "color_pick", "desc": "Улучши дизайн существующего экрана"}
                ]
            }
        ]
    },
    {
        "id": "business",
        "name": "Бизнес",
        "icon": "💼",
        "professions": [
            {
                "id": "marketing",
                "name": "Маркетолог",
                "icon": "📢",
                "desc": "Продвигает продукты и бренды, анализирует целевую аудиторию",
                "tools": ["Google Analytics", "Canva", "Яндекс.Метрика", "CRM"],
                "cost": 1,
                "tasks": [
                    {"title": "Целевая аудитория", "type": "quiz", "desc": "Определи ЦА для нового продукта"},
                    {"title": "Рекламный бюджет", "type": "quiz", "desc": "Распредели бюджет между каналами"},
                    {"title": "A/B тест рекламы", "type": "find_bug", "desc": "Выбери более эффективный баннер"},
                    {"title": "Контент-план", "type": "drag_arrange", "desc": "Составь контент-план на неделю"},
                    {"title": "Аналитика", "type": "quiz", "desc": "Проанализируй метрики кампании"}
                ]
            },
            {
                "id": "pm",
                "name": "Менеджер проектов",
                "icon": "📋",
                "desc": "Координирует команду и управляет сроками/ресурсами проекта",
                "tools": ["Jira", "Trello", "Gantt", "Agile/Scrum"],
                "cost": 1,
                "tasks": [
                    {"title": "Декомпозиция", "type": "drag_arrange", "desc": "Разбей проект на задачи"},
                    {"title": "Оценка сроков", "type": "quiz", "desc": "Оцени время выполнения задач"},
                    {"title": "Управление рисками", "type": "quiz", "desc": "Определи и оцени риски проекта"},
                    {"title": "Стендап", "type": "quiz", "desc": "Проведи утреннюю встречу команды"},
                    {"title": "Ретроспектива", "type": "drag_arrange", "desc": "Проведи ретро по завершённому спринту"}
                ]
            }
        ]
    },
    {
        "id": "science",
        "name": "Наука",
        "icon": "🔬",
        "professions": [
            {
                "id": "chemistry",
                "name": "Химик",
                "icon": "⚗️",
                "desc": "Исследует вещества, создаёт новые материалы и соединения",
                "tools": ["Спектрометр", "Хроматограф", "Реактор", "Лаборатория"],
                "cost": 1,
                "tasks": [
                    {"title": "Уравнение реакции", "type": "code_match", "desc": "Уравняй химическую реакцию"},
                    {"title": "Техника безопасности", "type": "find_bug", "desc": "Найди нарушения ТБ в лаборатории"},
                    {"title": "Анализ вещества", "type": "quiz", "desc": "Определи вещество по свойствам"},
                    {"title": "Синтез", "type": "drag_arrange", "desc": "Составь план синтеза соединения"},
                    {"title": "Эксперимент", "type": "quiz", "desc": "Спланируй эксперимент и предскажи результат"}
                ]
            },
            {
                "id": "physics",
                "name": "Физик",
                "icon": "⚛️",
                "desc": "Изучает фундаментальные законы природы и применяет их",
                "tools": ["MATLAB", "LabVIEW", "Осциллограф", "Ускоритель"],
                "cost": 1,
                "tasks": [
                    {"title": "Расчёт задачи", "type": "quiz", "desc": "Реши задачу по механике"},
                    {"title": "Анализ графика", "type": "quiz", "desc": "Определи закон по экспериментальным данным"},
                    {"title": "Схема опыта", "type": "drag_arrange", "desc": "Собери экспериментальную установку"},
                    {"title": "Погрешности", "type": "find_bug", "desc": "Найди источник ошибки в измерениях"},
                    {"title": "Моделирование", "type": "quiz", "desc": "Предскажи поведение системы"}
                ]
            }
        ]
    }
]


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
