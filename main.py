import os
import time
import math
import hashlib
import hmac
import json
from urllib.parse import unquote, parse_qs
from pathlib import Path
from collections import defaultdict

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

import database as db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="REALITY: Профессии")

# ─── Каталог профессий ───────────────────────────────────────────────

PROFESSIONS = {
    # IT
    "it_frontend": {
        "id": "it_frontend",
        "sphere": "IT",
        "name": "Frontend-разработчик",
        "description": "Создание интерфейсов веб-приложений",
        "tools": ["React", "TypeScript", "CSS"],
        "icon_emoji": "🖥️",
    },
    "it_backend": {
        "id": "it_backend",
        "sphere": "IT",
        "name": "Backend-разработчик",
        "description": "Серверная логика и API",
        "tools": ["Python", "FastAPI", "PostgreSQL"],
        "icon_emoji": "⚙️",
    },
    "it_data": {
        "id": "it_data",
        "sphere": "IT",
        "name": "Data Scientist",
        "description": "Анализ данных и машинное обучение",
        "tools": ["Python", "Pandas", "TensorFlow"],
        "icon_emoji": "📊",
    },
    "it_security": {
        "id": "it_security",
        "sphere": "IT",
        "name": "Специалист по кибербезопасности",
        "description": "Защита систем и данных от угроз",
        "tools": ["Kali Linux", "Wireshark", "Burp Suite"],
        "icon_emoji": "🔒",
    },
    # Engineering
    "eng_mechanical": {
        "id": "eng_mechanical",
        "sphere": "Engineering",
        "name": "Инженер-механик",
        "description": "Проектирование механизмов и машин",
        "tools": ["SolidWorks", "AutoCAD", "MATLAB"],
        "icon_emoji": "🔧",
    },
    "eng_electrical": {
        "id": "eng_electrical",
        "sphere": "Engineering",
        "name": "Инженер-электрик",
        "description": "Проектирование электрических систем",
        "tools": ["Altium", "SPICE", "LabVIEW"],
        "icon_emoji": "⚡",
    },
    "eng_civil": {
        "id": "eng_civil",
        "sphere": "Engineering",
        "name": "Инженер-строитель",
        "description": "Проектирование зданий и сооружений",
        "tools": ["Revit", "AutoCAD", "SAP2000"],
        "icon_emoji": "🏗️",
    },
    "eng_robotics": {
        "id": "eng_robotics",
        "sphere": "Engineering",
        "name": "Робототехник",
        "description": "Разработка и программирование роботов",
        "tools": ["ROS", "Arduino", "C++"],
        "icon_emoji": "🤖",
    },
    # Medicine
    "med_surgeon": {
        "id": "med_surgeon",
        "sphere": "Medicine",
        "name": "Хирург",
        "description": "Проведение операций и лечение",
        "tools": ["Скальпель", "Эндоскоп", "МРТ"],
        "icon_emoji": "🏥",
    },
    "med_pharma": {
        "id": "med_pharma",
        "sphere": "Medicine",
        "name": "Фармацевт",
        "description": "Разработка и тестирование лекарств",
        "tools": ["HPLC", "Спектрометр", "Биореактор"],
        "icon_emoji": "💊",
    },
    "med_neuro": {
        "id": "med_neuro",
        "sphere": "Medicine",
        "name": "Нейрохирург",
        "description": "Операции на головном и спинном мозге",
        "tools": ["Нейронавигация", "МРТ", "Микроскоп"],
        "icon_emoji": "🧠",
    },
    "med_genetics": {
        "id": "med_genetics",
        "sphere": "Medicine",
        "name": "Генетик",
        "description": "Исследование генома и генная терапия",
        "tools": ["ПЦР", "Секвенатор", "CRISPR"],
        "icon_emoji": "🧬",
    },
    # Science
    "sci_physics": {
        "id": "sci_physics",
        "sphere": "Science",
        "name": "Физик",
        "description": "Исследование фундаментальных законов природы",
        "tools": ["Коллайдер", "Лазер", "Python"],
        "icon_emoji": "⚛️",
    },
    "sci_chemistry": {
        "id": "sci_chemistry",
        "sphere": "Science",
        "name": "Химик",
        "description": "Синтез и анализ веществ",
        "tools": ["Спектрометр", "Хроматограф", "Реактор"],
        "icon_emoji": "🧪",
    },
    "sci_biology": {
        "id": "sci_biology",
        "sphere": "Science",
        "name": "Биолог",
        "description": "Изучение живых организмов",
        "tools": ["Микроскоп", "ПЦР", "Биоинформатика"],
        "icon_emoji": "🔬",
    },
    "sci_astro": {
        "id": "sci_astro",
        "sphere": "Science",
        "name": "Астрофизик",
        "description": "Исследование космоса и звёзд",
        "tools": ["Телескоп", "Python", "Спектроскоп"],
        "icon_emoji": "🌌",
    },
}

# ─── Античит: трекинг тапов ──────────────────────────────────────────

# tg_id → список timestamp'ов тапов
tap_history: dict[int, list[float]] = defaultdict(list)

MAX_TAPS_PER_SEC = 15
COMBO_WINDOW = 2.0  # секунд


def compute_combo(tg_id: int) -> int:
    """Комбо: кол-во тапов за последние 2 сек → множитель x1..x5."""
    now = time.time()
    history = tap_history[tg_id]
    recent = [t for t in history if now - t <= COMBO_WINDOW]
    tap_history[tg_id] = recent
    count = len(recent)
    if count >= 40:
        return 5
    if count >= 30:
        return 4
    if count >= 20:
        return 3
    if count >= 10:
        return 2
    return 1


# ─── Telegram initData верификация ───────────────────────────────────

def verify_telegram_init_data(init_data: str) -> dict | None:
    """Проверяет подпись initData от Telegram WebApp."""
    if not BOT_TOKEN:
        return None
    try:
        parsed = parse_qs(init_data)
        received_hash = parsed.get("hash", [None])[0]
        if not received_hash:
            return None
        data_pairs = []
        for key, values in parsed.items():
            if key == "hash":
                continue
            data_pairs.append(f"{key}={unquote(values[0])}")
        data_pairs.sort()
        data_check_string = "\n".join(data_pairs)
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if computed_hash != received_hash:
            return None
        user_str = parsed.get("user", [None])[0]
        if user_str:
            return json.loads(unquote(user_str))
        return {}
    except Exception:
        return None


# ─── Pydantic модели ─────────────────────────────────────────────────

class AuthRequest(BaseModel):
    initData: str = ""
    tg_id: int | None = None


class RegisterRequest(BaseModel):
    tg_id: int
    avatar: int
    name: str


class TapRequest(BaseModel):
    tg_id: int
    count: int
    timestamp: float


class UnlockRequest(BaseModel):
    tg_id: int
    profession_id: str


class UpgradeRequest(BaseModel):
    tg_id: int
    type: str


class TaskCompleteRequest(BaseModel):
    tg_id: int
    profession_id: str
    score: int


# ─── Events ──────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    await db.init_db()


# ─── Статика ─────────────────────────────────────────────────────────

@app.get("/")
async def serve_index():
    index_path = BASE_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(404, "index.html not found")
    return FileResponse(str(index_path))


@app.get("/hero1.png")
async def serve_hero1():
    return FileResponse(str(BASE_DIR / "hero1.png"))


@app.get("/hero2.png")
async def serve_hero2():
    return FileResponse(str(BASE_DIR / "hero2.png"))


@app.get("/hero3.png")
async def serve_hero3():
    return FileResponse(str(BASE_DIR / "hero3.png"))


# ─── API эндпоинты ───────────────────────────────────────────────────

@app.post("/api/auth")
async def auth(req: AuthRequest):
    """Авторизация через Telegram initData (или tg_id в dev-режиме)."""
    tg_id = None
    username = ""

    if DEV_MODE and req.tg_id:
        tg_id = req.tg_id
        username = f"dev_{tg_id}"
    elif req.initData:
        tg_user = verify_telegram_init_data(req.initData)
        if tg_user is None:
            raise HTTPException(401, "Invalid initData")
        tg_id = tg_user.get("id")
        username = tg_user.get("username", "")
    else:
        raise HTTPException(400, "initData or tg_id (dev) required")

    if not tg_id:
        raise HTTPException(400, "Could not extract tg_id")

    user = await db.get_user(tg_id)
    # Простой токен для сессии (не JWT, достаточно для MVP)
    token = hashlib.sha256(f"{tg_id}:{BOT_TOKEN}:{int(time.time() // 3600)}".encode()).hexdigest()

    return {
        "user": user,
        "token": token,
    }


@app.post("/api/register")
async def register(req: RegisterRequest):
    """Регистрация нового пользователя."""
    existing = await db.get_user(req.tg_id)
    if existing:
        raise HTTPException(409, "User already exists")
    if req.avatar not in (1, 2, 3):
        raise HTTPException(400, "Avatar must be 1, 2, or 3")
    user = await db.create_user(req.tg_id, req.name, req.avatar)
    return {"user": user}


@app.post("/api/tap")
async def tap(req: TapRequest):
    """Батч тапов с античитом: макс 15 тапов/сек."""
    user = await db.get_user(req.tg_id)
    if not user:
        raise HTTPException(404, "User not found")

    # Античит: ограничение тапов
    now = time.time()
    history = tap_history[req.tg_id]
    # Чистим старые записи (старше 2 секунд)
    history = [t for t in history if now - t > -0.1 and now - t <= 2.0]
    tap_history[req.tg_id] = history

    recent_count = len(history)
    allowed = min(req.count, max(0, MAX_TAPS_PER_SEC * 2 - recent_count))

    if allowed <= 0:
        return {
            "coins": user["coins"],
            "xp": user["xp"],
            "energy": user["energy"],
            "level": user["level"],
            "combo": compute_combo(req.tg_id),
            "rejected": req.count,
        }

    # Регистрируем тапы
    for i in range(allowed):
        tap_history[req.tg_id].append(now + i * 0.01)

    # Расход энергии
    energy = user["energy"]
    actual_taps = min(allowed, energy)
    if actual_taps <= 0:
        return {
            "coins": user["coins"],
            "xp": user["xp"],
            "energy": energy,
            "level": user["level"],
            "combo": compute_combo(req.tg_id),
            "rejected": req.count,
        }

    combo = compute_combo(req.tg_id)
    mpc = user["mpc"]
    coins_earned = actual_taps * mpc * combo
    xp_earned = actual_taps * combo
    new_coins = user["coins"] + coins_earned
    new_xp = user["xp"] + xp_earned
    new_energy = energy - actual_taps
    new_level = math.floor(new_xp / 100)
    old_level = user["level"]

    # Токены за уровень
    new_tokens = user["tokens"]
    if new_level > old_level:
        new_tokens += new_level - old_level

    updated = await db.update_user(
        req.tg_id,
        coins=new_coins,
        xp=new_xp,
        energy=new_energy,
        level=new_level,
        tokens=new_tokens,
        last_energy_update=time.time(),
    )

    return {
        "coins": updated["coins"],
        "xp": updated["xp"],
        "energy": updated["energy"],
        "level": updated["level"],
        "combo": combo,
        "coins_earned": coins_earned,
        "xp_earned": xp_earned,
    }


@app.get("/api/user/{tg_id}")
async def get_user(tg_id: int):
    """Полный стейт пользователя."""
    user = await db.get_user(tg_id)
    if not user:
        raise HTTPException(404, "User not found")
    upgrades = await db.get_upgrades(tg_id)
    unlocked = await db.get_unlocked_professions(tg_id)
    simulations = await db.get_completed_simulations(tg_id)
    return {
        "user": user,
        "upgrades": upgrades,
        "unlocked_professions": unlocked,
        "completed_simulations": simulations,
    }


@app.post("/api/unlock")
async def unlock(req: UnlockRequest):
    """Разблокировать профессию за 1 токен."""
    if req.profession_id not in PROFESSIONS:
        raise HTTPException(400, "Unknown profession")

    user = await db.get_user(req.tg_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user["tokens"] < 1:
        raise HTTPException(400, "Not enough tokens")

    success = await db.unlock_profession(req.tg_id, req.profession_id)
    if not success:
        raise HTTPException(409, "Profession already unlocked")

    await db.update_user(req.tg_id, tokens=user["tokens"] - 1)
    unlocked = await db.get_unlocked_professions(req.tg_id)

    return {
        "unlocked": unlocked,
        "tokens": user["tokens"] - 1,
    }


@app.post("/api/upgrade")
async def upgrade(req: UpgradeRequest):
    """Улучшение: mpc / stamina / regen. Стоимость растёт экспоненциально."""
    if req.type not in ("mpc", "stamina", "regen"):
        raise HTTPException(400, "Type must be mpc, stamina, or regen")

    user = await db.get_user(req.tg_id)
    if not user:
        raise HTTPException(404, "User not found")

    upgrades = await db.get_upgrades(req.tg_id)
    current_level = upgrades.get(req.type, 0)

    # Стоимость
    cost_map = {"mpc": 10, "stamina": 15, "regen": 20}
    cost = cost_map[req.type] * (2 ** current_level)

    if user["coins"] < cost:
        raise HTTPException(400, f"Not enough coins. Need {cost}")

    # Списываем монеты
    await db.update_user(req.tg_id, coins=user["coins"] - cost)
    new_level = await db.upgrade_level(req.tg_id, req.type)

    # Применяем эффект
    if req.type == "mpc":
        await db.update_user(req.tg_id, mpc=user["mpc"] + 1)
    elif req.type == "stamina":
        new_max = user["max_energy"] + 10
        await db.update_user(req.tg_id, max_energy=new_max)
    elif req.type == "regen":
        new_regen = user["auto_regen"] + 0.5
        await db.update_user(req.tg_id, auto_regen=new_regen)

    updated_user = await db.get_user(req.tg_id)
    return {
        "upgrade_type": req.type,
        "new_level": new_level,
        "cost": cost,
        "user": updated_user,
    }


@app.post("/api/task/complete")
async def task_complete(req: TaskCompleteRequest):
    """Завершение симуляции профессии."""
    if req.profession_id not in PROFESSIONS:
        raise HTTPException(400, "Unknown profession")

    user = await db.get_user(req.tg_id)
    if not user:
        raise HTTPException(404, "User not found")

    unlocked = await db.get_unlocked_professions(req.tg_id)
    if req.profession_id not in unlocked:
        raise HTTPException(403, "Profession not unlocked")

    await db.complete_simulation(req.tg_id, req.profession_id, req.score)

    return {
        "profession_id": req.profession_id,
        "score": req.score,
        "message": "Simulation completed",
    }


@app.get("/api/professions")
async def get_professions():
    """Список всех профессий."""
    return {"professions": list(PROFESSIONS.values())}


# ─── Запуск ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
