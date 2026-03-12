# REALITY Профессии — Telegram Mini App для профориентации подростков
# FastAPI бэкенд + SQLite + Telegram Web App API

import os
import json
import time
import math
import random
import sqlite3
import hashlib
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


# --- Конфигурация ---
DB_PATH = "reality.db"
MAX_ENERGY = 100
ENERGY_REGEN_RATE = 2       # единиц в секунду
XP_PER_LEVEL = 100          # XP для повышения уровня (растёт)
COMBO_DECAY_MS = 800        # время затухания комбо в мс
MAX_COMBO = 5               # максимальный множитель комбо


# --- Модели данных ---
class CreateCharacter(BaseModel):
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
    combo: int = Field(ge=1, le=MAX_COMBO)


class UnlockProfession(BaseModel):
    telegram_id: int
    profession_id: str


class CompleteTask(BaseModel):
    telegram_id: int
    profession_id: str
    task_index: int
    score: float = Field(ge=0, le=100)


class BuyUpgrade(BaseModel):
    telegram_id: int
    upgrade_id: str


# --- Инициализация базы данных ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
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
            coins INTEGER NOT NULL DEFAULT 0,
            tokens INTEGER NOT NULL DEFAULT 1,
            energy REAL NOT NULL DEFAULT 100,
            max_energy INTEGER NOT NULL DEFAULT 100,
            last_energy_update REAL NOT NULL,
            tap_power INTEGER NOT NULL DEFAULT 1,
            multi_tap INTEGER NOT NULL DEFAULT 1,
            energy_regen REAL NOT NULL DEFAULT 2.0,
            last_tap_time REAL NOT NULL DEFAULT 0,
            tap_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS user_professions (
            telegram_id INTEGER,
            profession_id TEXT,
            unlocked INTEGER NOT NULL DEFAULT 0,
            tasks_completed TEXT NOT NULL DEFAULT '[]',
            PRIMARY KEY (telegram_id, profession_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS user_upgrades (
            telegram_id INTEGER,
            upgrade_id TEXT,
            level INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (telegram_id, upgrade_id)
        )
    """)

    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# --- Игровая логика ---
def calculate_xp_for_level(level):
    return int(XP_PER_LEVEL * (1.2 ** (level - 1)))


def update_energy(user):
    now = time.time()
    elapsed = now - user["last_energy_update"]
    regen = elapsed * user["energy_regen"]
    new_energy = min(user["max_energy"], user["energy"] + regen)
    result = dict(user)
    result["energy"] = new_energy
    result["last_energy_update"] = now
    return result


def check_level_up(user):
    leveled = False
    while user["xp"] >= calculate_xp_for_level(user["level"]):
        user["xp"] -= calculate_xp_for_level(user["level"])
        user["level"] += 1
        user["tokens"] += 1
        leveled = True
    return user, leveled


# --- Профессии и задания ---
PROFESSIONS = {
    "frontend": {
        "name": "Frontend-разработчик",
        "sphere": "IT-сфера",
        "icon": "🖥️",
        "description": "Создаёт интерфейсы сайтов и приложений",
        "tools": ["HTML/CSS", "JavaScript", "React", "Figma"],
        "cost": 1,
        "stat_bonus": "intellect",
        "tasks": [
            {"title": "Верстка кнопки", "type": "css_builder", "description": "Создай стилизованную кнопку, подбирая CSS-свойства", "xp": 30, "coins": 15},
            {"title": "Цветовая палитра", "type": "color_match", "description": "Подбери цвета для сайта по заданной теме", "xp": 35, "coins": 20},
            {"title": "Flexbox-макет", "type": "layout_puzzle", "description": "Расположи элементы на странице используя flexbox", "xp": 40, "coins": 25},
            {"title": "Адаптивный дизайн", "type": "responsive", "description": "Адаптируй макет под разные экраны", "xp": 45, "coins": 30},
            {"title": "Анимация интерфейса", "type": "animation_builder", "description": "Создай плавную анимацию появления элемента", "xp": 50, "coins": 40},
        ]
    },
    "backend": {
        "name": "Backend-разработчик",
        "sphere": "IT-сфера",
        "icon": "⚙️",
        "description": "Разрабатывает серверную логику приложений",
        "tools": ["Python", "SQL", "Docker", "REST API"],
        "cost": 1,
        "stat_bonus": "intellect",
        "tasks": [
            {"title": "SQL-запрос", "type": "sql_builder", "description": "Напиши SQL запрос для получения данных из базы", "xp": 30, "coins": 15},
            {"title": "Проектирование API", "type": "api_design", "description": "Спроектируй REST API для интернет-магазина", "xp": 35, "coins": 20},
            {"title": "Отладка кода", "type": "debug_code", "description": "Найди и исправь баг в серверном коде", "xp": 40, "coins": 25},
            {"title": "Оптимизация", "type": "optimize", "description": "Ускорь медленный запрос к базе данных", "xp": 45, "coins": 30},
            {"title": "Архитектура", "type": "architecture", "description": "Спроектируй архитектуру микросервисов", "xp": 50, "coins": 40},
        ]
    },
    "datasci": {
        "name": "Data Scientist",
        "sphere": "IT-сфера",
        "icon": "📊",
        "description": "Анализирует данные и строит модели ML",
        "tools": ["Python", "Pandas", "TensorFlow", "Jupyter"],
        "cost": 2,
        "stat_bonus": "intellect",
        "tasks": [
            {"title": "Анализ данных", "type": "data_analysis", "description": "Найди аномалии в наборе данных", "xp": 35, "coins": 20},
            {"title": "Визуализация", "type": "data_viz", "description": "Выбери правильный тип графика для данных", "xp": 35, "coins": 20},
            {"title": "Подготовка данных", "type": "data_clean", "description": "Очисти датасет от мусорных значений", "xp": 40, "coins": 25},
            {"title": "Модель предсказания", "type": "ml_model", "description": "Настрой модель для предсказания цен", "xp": 45, "coins": 30},
            {"title": "A/B тестирование", "type": "ab_test", "description": "Проанализируй результаты A/B теста", "xp": 50, "coins": 40},
        ]
    },
    "cyber": {
        "name": "Кибербезопасность",
        "sphere": "IT-сфера",
        "icon": "🛡️",
        "description": "Защищает системы от хакерских атак",
        "tools": ["Wireshark", "Kali Linux", "Metasploit", "SIEM"],
        "cost": 2,
        "stat_bonus": "intellect",
        "tasks": [
            {"title": "Анализ пароля", "type": "password_check", "description": "Оцени надёжность паролей пользователей", "xp": 30, "coins": 15},
            {"title": "Фишинг-детектор", "type": "phishing", "description": "Определи фишинговые письма среди настоящих", "xp": 35, "coins": 20},
            {"title": "Сетевой трафик", "type": "traffic_analysis", "description": "Найди подозрительную активность в логах", "xp": 40, "coins": 25},
            {"title": "Уязвимости", "type": "vulnerability", "description": "Найди уязвимости на веб-странице", "xp": 45, "coins": 30},
            {"title": "Инцидент-менеджмент", "type": "incident", "description": "Отреагируй на инцидент безопасности правильно", "xp": 50, "coins": 40},
        ]
    },
    "robotics": {
        "name": "Робототехник",
        "sphere": "Инженерия",
        "icon": "🤖",
        "description": "Проектирует и программирует роботов",
        "tools": ["Arduino", "ROS", "3D-печать", "Датчики"],
        "cost": 1,
        "stat_bonus": "strength",
        "tasks": [
            {"title": "Схема робота", "type": "robot_schema", "description": "Собери электрическую цепь для робота", "xp": 30, "coins": 15},
            {"title": "Программирование движения", "type": "robot_move", "description": "Запрограммируй маршрут робота по лабиринту", "xp": 35, "coins": 20},
            {"title": "Датчики", "type": "sensors", "description": "Настрой датчики для обхода препятствий", "xp": 40, "coins": 25},
            {"title": "Захват объекта", "type": "gripper", "description": "Откалибруй манипулятор для захвата предмета", "xp": 45, "coins": 30},
            {"title": "Автономная навигация", "type": "auto_nav", "description": "Создай алгоритм навигации робота", "xp": 50, "coins": 40},
        ]
    },
    "energy": {
        "name": "Энергетик",
        "sphere": "Инженерия",
        "icon": "⚡",
        "description": "Работает с электрическими сетями и генерацией",
        "tools": ["SCADA", "Мультиметр", "AutoCAD", "Реле"],
        "cost": 1,
        "stat_bonus": "strength",
        "tasks": [
            {"title": "Расчёт нагрузки", "type": "load_calc", "description": "Рассчитай нагрузку электрической сети дома", "xp": 30, "coins": 15},
            {"title": "Солнечная панель", "type": "solar", "description": "Спроектируй размещение солнечных панелей", "xp": 35, "coins": 20},
            {"title": "Поиск аварии", "type": "fault_find", "description": "Найди точку аварии в электросети", "xp": 40, "coins": 25},
            {"title": "Энергоэффективность", "type": "efficiency", "description": "Оптимизируй потребление энергии здания", "xp": 45, "coins": 30},
            {"title": "Проект подстанции", "type": "substation", "description": "Спроектируй трансформаторную подстанцию", "xp": 50, "coins": 40},
        ]
    },
    "surgery": {
        "name": "Хирург",
        "sphere": "Медицина",
        "icon": "🏥",
        "description": "Проводит операции и спасает жизни",
        "tools": ["Скальпель", "Лапароскоп", "МРТ", "Швы"],
        "cost": 2,
        "stat_bonus": "strength",
        "tasks": [
            {"title": "Анатомия", "type": "anatomy", "description": "Определи органы на анатомической схеме", "xp": 30, "coins": 15},
            {"title": "Наложение швов", "type": "stitching", "description": "Наложи шов правильной техникой", "xp": 35, "coins": 20},
            {"title": "Диагностика", "type": "diagnosis", "description": "Поставь диагноз по симптомам пациента", "xp": 40, "coins": 25},
            {"title": "Планирование операции", "type": "surgery_plan", "description": "Составь план операции по удалению аппендикса", "xp": 45, "coins": 30},
            {"title": "Экстренный случай", "type": "emergency", "description": "Прими решения в экстренной ситуации", "xp": 50, "coins": 40},
        ]
    },
    "biotech": {
        "name": "Биотехнолог",
        "sphere": "Медицина",
        "icon": "🧬",
        "description": "Разрабатывает биотехнологии и лекарства",
        "tools": ["ПЦР", "Секвенатор", "Биореактор", "CRISPR"],
        "cost": 2,
        "stat_bonus": "intellect",
        "tasks": [
            {"title": "ДНК-анализ", "type": "dna_analysis", "description": "Проанализируй последовательность ДНК", "xp": 30, "coins": 15},
            {"title": "Культивирование клеток", "type": "cell_culture", "description": "Подбери условия для роста клеточной культуры", "xp": 35, "coins": 20},
            {"title": "Разработка вакцины", "type": "vaccine", "description": "Выбери стратегию создания вакцины", "xp": 40, "coins": 25},
            {"title": "ПЦР-тест", "type": "pcr", "description": "Настрой параметры ПЦР-теста", "xp": 45, "coins": 30},
            {"title": "Биоэтика", "type": "bioethics", "description": "Прими этическое решение в биотехнологии", "xp": 50, "coins": 40},
        ]
    },
    "gamedev": {
        "name": "Геймдизайнер",
        "sphere": "Творчество",
        "icon": "🎮",
        "description": "Создаёт игровые механики и уровни",
        "tools": ["Unity", "Unreal Engine", "Blender", "Photoshop"],
        "cost": 1,
        "stat_bonus": "charisma",
        "tasks": [
            {"title": "Баланс персонажей", "type": "balance", "description": "Сбалансируй характеристики игровых персонажей", "xp": 30, "coins": 15},
            {"title": "Левел-дизайн", "type": "level_design", "description": "Спроектируй уровень для платформера", "xp": 35, "coins": 20},
            {"title": "Игровая экономика", "type": "game_economy", "description": "Настрой экономику виртуального мира", "xp": 40, "coins": 25},
            {"title": "Нарратив", "type": "narrative", "description": "Создай ветвящийся диалог для NPC", "xp": 45, "coins": 30},
            {"title": "Прототип механики", "type": "mechanic_proto", "description": "Спроектируй уникальную игровую механику", "xp": 50, "coins": 40},
        ]
    },
    "design": {
        "name": "UX/UI дизайнер",
        "sphere": "Творчество",
        "icon": "🎨",
        "description": "Проектирует удобные и красивые интерфейсы",
        "tools": ["Figma", "Adobe XD", "Sketch", "Principle"],
        "cost": 1,
        "stat_bonus": "charisma",
        "tasks": [
            {"title": "Цветовая теория", "type": "color_theory", "description": "Подбери гармоничную палитру для приложения", "xp": 30, "coins": 15},
            {"title": "Типографика", "type": "typography", "description": "Выбери и настрой шрифтовую пару", "xp": 35, "coins": 20},
            {"title": "Wireframe", "type": "wireframe", "description": "Создай каркас мобильного приложения", "xp": 40, "coins": 25},
            {"title": "Юзабилити", "type": "usability", "description": "Найди UX-проблемы на скриншоте интерфейса", "xp": 45, "coins": 30},
            {"title": "Дизайн-система", "type": "design_system", "description": "Создай компоненты дизайн-системы", "xp": 50, "coins": 40},
        ]
    },
    "marketing": {
        "name": "Маркетолог",
        "sphere": "Бизнес",
        "icon": "📢",
        "description": "Продвигает продукты и управляет брендом",
        "tools": ["Google Analytics", "Яндекс.Метрика", "Canva", "CRM"],
        "cost": 1,
        "stat_bonus": "charisma",
        "tasks": [
            {"title": "Целевая аудитория", "type": "target_audience", "description": "Определи целевую аудиторию продукта", "xp": 30, "coins": 15},
            {"title": "Рекламный текст", "type": "ad_copy", "description": "Напиши продающий текст для объявления", "xp": 35, "coins": 20},
            {"title": "Аналитика", "type": "analytics", "description": "Проанализируй метрики рекламной кампании", "xp": 40, "coins": 25},
            {"title": "Стратегия продвижения", "type": "strategy", "description": "Составь маркетинговую стратегию", "xp": 45, "coins": 30},
            {"title": "Антикризис", "type": "crisis_pr", "description": "Управляй репутацией в кризисной ситуации", "xp": 50, "coins": 40},
        ]
    },
    "finance": {
        "name": "Финансист",
        "sphere": "Бизнес",
        "icon": "💰",
        "description": "Управляет финансами и инвестициями",
        "tools": ["Excel", "1C", "Bloomberg", "Power BI"],
        "cost": 1,
        "stat_bonus": "intellect",
        "tasks": [
            {"title": "Бюджетирование", "type": "budget", "description": "Составь бюджет стартапа на месяц", "xp": 30, "coins": 15},
            {"title": "Анализ отчётности", "type": "fin_report", "description": "Проанализируй финансовый отчёт компании", "xp": 35, "coins": 20},
            {"title": "Инвестиционный портфель", "type": "portfolio", "description": "Собери инвестиционный портфель", "xp": 40, "coins": 25},
            {"title": "Оценка рисков", "type": "risk", "description": "Оцени финансовые риски проекта", "xp": 45, "coins": 30},
            {"title": "Бизнес-план", "type": "business_plan", "description": "Составь финансовую модель бизнес-плана", "xp": 50, "coins": 40},
        ]
    },
    "chemistry": {
        "name": "Химик",
        "sphere": "Наука",
        "icon": "🧪",
        "description": "Исследует вещества и создаёт новые материалы",
        "tools": ["Спектрометр", "Хроматограф", "Реактивы", "Лаборатория"],
        "cost": 1,
        "stat_bonus": "intellect",
        "tasks": [
            {"title": "Уравнение реакции", "type": "reaction_eq", "description": "Уравняй химическую реакцию", "xp": 30, "coins": 15},
            {"title": "Определение вещества", "type": "identify_substance", "description": "Определи вещество по его свойствам", "xp": 35, "coins": 20},
            {"title": "Лабораторная работа", "type": "lab_work", "description": "Проведи эксперимент по протоколу", "xp": 40, "coins": 25},
            {"title": "Молекулярное моделирование", "type": "molecular", "description": "Собери модель молекулы", "xp": 45, "coins": 30},
            {"title": "Синтез", "type": "synthesis", "description": "Спланируй синтез целевого соединения", "xp": 50, "coins": 40},
        ]
    },
    "physics": {
        "name": "Физик",
        "sphere": "Наука",
        "icon": "⚛️",
        "description": "Изучает законы природы и разрабатывает технологии",
        "tools": ["Осциллограф", "Лазер", "Ускоритель", "MATLAB"],
        "cost": 1,
        "stat_bonus": "intellect",
        "tasks": [
            {"title": "Расчёт траектории", "type": "trajectory", "description": "Рассчитай траекторию снаряда", "xp": 30, "coins": 15},
            {"title": "Электрическая цепь", "type": "circuit", "description": "Собери и рассчитай электрическую цепь", "xp": 35, "coins": 20},
            {"title": "Оптический эксперимент", "type": "optics", "description": "Настрой оптическую систему", "xp": 40, "coins": 25},
            {"title": "Термодинамика", "type": "thermo", "description": "Реши задачу на теплообмен", "xp": 45, "coins": 30},
            {"title": "Квантовые вычисления", "type": "quantum", "description": "Построй простую квантовую схему", "xp": 50, "coins": 40},
        ]
    },
}


# --- Улучшения ---
UPGRADES = {
    "tap_power": {
        "name": "Сила пальцев",
        "icon": "👊",
        "description": "+1 монета за тап",
        "max_level": 10,
        "base_cost": 50,
        "cost_multiplier": 1.8,
    },
    "max_energy": {
        "name": "Выносливость",
        "icon": "🔋",
        "description": "+20 макс. энергии",
        "max_level": 10,
        "base_cost": 80,
        "cost_multiplier": 2.0,
    },
    "multi_tap": {
        "name": "Мультитап",
        "icon": "🖐️",
        "description": "+1 одновременных касаний",
        "max_level": 4,
        "base_cost": 200,
        "cost_multiplier": 2.5,
    },
    "energy_regen": {
        "name": "Авто-восстановление",
        "icon": "⚡",
        "description": "+0.5 ед/сек регенерации",
        "max_level": 8,
        "base_cost": 100,
        "cost_multiplier": 2.0,
    },
}


# --- Античит ---
tap_history = {}


def validate_taps(telegram_id, taps, timestamp):
    now = time.time()

    if telegram_id not in tap_history:
        tap_history[telegram_id] = []

    history = tap_history[telegram_id]
    history.append(now)

    # Оставляем только последние 2 секунды
    tap_history[telegram_id] = [t for t in history if now - t < 2.0]
    history = tap_history[telegram_id]

    # Максимум 30 тапов за 2 секунды
    if len(history) > 30:
        return False

    # Проверка на бота (слишком равномерные интервалы)
    if len(history) > 10:
        intervals = [history[i + 1] - history[i] for i in range(len(history) - 1)]
        if intervals:
            avg = sum(intervals) / len(intervals)
            if avg > 0:
                variance = sum((iv - avg) ** 2 for iv in intervals) / len(intervals)
                if variance < 0.0001 and avg < 0.1:
                    return False

    return True


# --- FastAPI приложение ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="REALITY Профессии", lifespan=lifespan)


# --- API маршруты ---
@app.get("/api/user/{telegram_id}")
async def get_user(telegram_id: int):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    conn.close()

    if not user:
        return {"exists": False}

    user_dict = dict(user)
    user_dict = update_energy(user_dict)

    conn = get_db()
    conn.execute(
        "UPDATE users SET energy = ?, last_energy_update = ? WHERE telegram_id = ?",
        (user_dict["energy"], user_dict["last_energy_update"], telegram_id)
    )
    conn.commit()
    conn.close()

    user_dict["exists"] = True
    user_dict["xp_needed"] = calculate_xp_for_level(user_dict["level"])
    return user_dict


@app.post("/api/create")
async def create_character(data: CreateCharacter):
    total = data.strength + data.intellect + data.charisma + data.luck
    if total != 20:
        raise HTTPException(400, "Сумма характеристик должна быть 20")

    conn = get_db()
    existing = conn.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (data.telegram_id,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(400, "Персонаж уже создан")

    now = time.time()
    conn.execute(
        "INSERT INTO users (telegram_id, name, avatar, strength, intellect, charisma, luck,"
        " level, xp, coins, tokens, energy, max_energy, last_energy_update,"
        " tap_power, multi_tap, energy_regen, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, 0, 1, 100, 100, ?, 1, 1, 2.0, ?)",
        (data.telegram_id, data.name, data.avatar, data.strength, data.intellect,
         data.charisma, data.luck, now, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

    return {"success": True, "message": "Персонаж создан!"}


@app.post("/api/tap")
async def handle_tap(data: TapRequest):
    if not validate_taps(data.telegram_id, data.taps, data.timestamp):
        raise HTTPException(429, "Слишком быстро!")

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (data.telegram_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(404, "Пользователь не найден")

    user_dict = dict(user)
    user_dict = update_energy(user_dict)

    actual_taps = min(data.taps, user_dict["multi_tap"])

    if user_dict["energy"] < actual_taps:
        actual_taps = int(user_dict["energy"])
        if actual_taps <= 0:
            conn.close()
            return {"success": False, "message": "Нет энергии!", "energy": user_dict["energy"]}

    combo = min(data.combo, MAX_COMBO)
    luck_bonus = 1 + (user_dict["luck"] * 0.02)
    base_coins = user_dict["tap_power"] * actual_taps
    coins_earned = int(base_coins * combo * luck_bonus)
    xp_earned = actual_taps * combo

    crit = False
    if random.random() < (user_dict["luck"] * 0.01):
        coins_earned *= 3
        xp_earned *= 2
        crit = True

    new_energy = user_dict["energy"] - actual_taps
    new_coins = user_dict["coins"] + coins_earned
    new_xp = user_dict["xp"] + xp_earned

    temp_user = dict(user_dict)
    temp_user["xp"] = new_xp
    temp_user["coins"] = new_coins
    temp_user, leveled = check_level_up(temp_user)

    conn.execute(
        "UPDATE users SET energy = ?, coins = ?, xp = ?, level = ?, tokens = ?,"
        " last_energy_update = ?, tap_count = tap_count + ? WHERE telegram_id = ?",
        (new_energy, temp_user["coins"], temp_user["xp"], temp_user["level"],
         temp_user["tokens"], time.time(), actual_taps, data.telegram_id)
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "coins_earned": coins_earned,
        "xp_earned": xp_earned,
        "crit": crit,
        "energy": new_energy,
        "total_coins": temp_user["coins"],
        "total_xp": temp_user["xp"],
        "level": temp_user["level"],
        "tokens": temp_user["tokens"],
        "leveled_up": leveled,
        "xp_needed": calculate_xp_for_level(temp_user["level"]),
    }


@app.get("/api/professions")
async def get_professions():
    return PROFESSIONS


@app.get("/api/professions/{telegram_id}")
async def get_user_professions(telegram_id: int):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM user_professions WHERE telegram_id = ?", (telegram_id,)
    ).fetchall()
    conn.close()

    result = {}
    for row in rows:
        result[row["profession_id"]] = {
            "unlocked": bool(row["unlocked"]),
            "tasks_completed": json.loads(row["tasks_completed"]),
        }
    return result


@app.post("/api/professions/unlock")
async def unlock_profession(data: UnlockProfession):
    if data.profession_id not in PROFESSIONS:
        raise HTTPException(404, "Профессия не найдена")

    prof = PROFESSIONS[data.profession_id]
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (data.telegram_id,)).fetchone()

    if not user:
        conn.close()
        raise HTTPException(404, "Пользователь не найден")

    if user["tokens"] < prof["cost"]:
        conn.close()
        raise HTTPException(400, "Нужно больше токенов")

    existing = conn.execute(
        "SELECT * FROM user_professions WHERE telegram_id = ? AND profession_id = ?",
        (data.telegram_id, data.profession_id)
    ).fetchone()

    if existing and existing["unlocked"]:
        conn.close()
        raise HTTPException(400, "Уже открыта")

    conn.execute(
        "UPDATE users SET tokens = tokens - ? WHERE telegram_id = ?",
        (prof["cost"], data.telegram_id)
    )

    if existing:
        conn.execute(
            "UPDATE user_professions SET unlocked = 1 WHERE telegram_id = ? AND profession_id = ?",
            (data.telegram_id, data.profession_id)
        )
    else:
        conn.execute(
            "INSERT INTO user_professions (telegram_id, profession_id, unlocked, tasks_completed)"
            " VALUES (?, ?, 1, '[]')",
            (data.telegram_id, data.profession_id)
        )

    conn.commit()
    new_tokens = user["tokens"] - prof["cost"]
    conn.close()

    return {"success": True, "tokens": new_tokens}


@app.post("/api/professions/complete-task")
async def complete_task(data: CompleteTask):
    if data.profession_id not in PROFESSIONS:
        raise HTTPException(404, "Профессия не найдена")

    prof = PROFESSIONS[data.profession_id]
    if data.task_index < 0 or data.task_index >= len(prof["tasks"]):
        raise HTTPException(400, "Неверный индекс задания")

    task = prof["tasks"][data.task_index]
    conn = get_db()

    user_prof = conn.execute(
        "SELECT * FROM user_professions WHERE telegram_id = ? AND profession_id = ?",
        (data.telegram_id, data.profession_id)
    ).fetchone()

    if not user_prof or not user_prof["unlocked"]:
        conn.close()
        raise HTTPException(400, "Профессия не открыта")

    completed = json.loads(user_prof["tasks_completed"])
    if data.task_index in completed:
        conn.close()
        raise HTTPException(400, "Задание уже выполнено")

    user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (data.telegram_id,)).fetchone()
    stat_bonus = user[prof["stat_bonus"]]
    score_mult = data.score / 100
    bonus_mult = 1 + (stat_bonus * 0.03)

    coins_reward = int(task["coins"] * score_mult * bonus_mult)
    xp_reward = int(task["xp"] * score_mult * bonus_mult)

    completed.append(data.task_index)

    conn.execute(
        "UPDATE user_professions SET tasks_completed = ? WHERE telegram_id = ? AND profession_id = ?",
        (json.dumps(completed), data.telegram_id, data.profession_id)
    )

    new_xp = user["xp"] + xp_reward
    new_coins = user["coins"] + coins_reward
    temp_user = dict(user)
    temp_user["xp"] = new_xp
    temp_user["coins"] = new_coins
    temp_user, leveled = check_level_up(temp_user)

    conn.execute(
        "UPDATE users SET coins = ?, xp = ?, level = ?, tokens = ? WHERE telegram_id = ?",
        (temp_user["coins"], temp_user["xp"], temp_user["level"], temp_user["tokens"], data.telegram_id)
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "coins_earned": coins_reward,
        "xp_earned": xp_reward,
        "level": temp_user["level"],
        "leveled_up": leveled,
        "tasks_completed": completed,
    }


@app.get("/api/upgrades/{telegram_id}")
async def get_upgrades(telegram_id: int):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM user_upgrades WHERE telegram_id = ?", (telegram_id,)
    ).fetchall()
    conn.close()

    result = {}
    for uid, info in UPGRADES.items():
        level = 0
        for row in rows:
            if row["upgrade_id"] == uid:
                level = row["level"]
                break
        cost = int(info["base_cost"] * (info["cost_multiplier"] ** level))
        result[uid] = {
            "name": info["name"],
            "icon": info["icon"],
            "description": info["description"],
            "max_level": info["max_level"],
            "current_level": level,
            "cost": cost,
            "can_upgrade": level < info["max_level"],
        }
    return result


@app.post("/api/upgrades/buy")
async def buy_upgrade(data: BuyUpgrade):
    if data.upgrade_id not in UPGRADES:
        raise HTTPException(404, "Улучшение не найдено")

    upgrade = UPGRADES[data.upgrade_id]
    conn = get_db()

    user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (data.telegram_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(404, "Пользователь не найден")

    existing = conn.execute(
        "SELECT * FROM user_upgrades WHERE telegram_id = ? AND upgrade_id = ?",
        (data.telegram_id, data.upgrade_id)
    ).fetchone()

    current_level = existing["level"] if existing else 0

    if current_level >= upgrade["max_level"]:
        conn.close()
        raise HTTPException(400, "Максимальный уровень")

    cost = int(upgrade["base_cost"] * (upgrade["cost_multiplier"] ** current_level))

    if user["coins"] < cost:
        conn.close()
        raise HTTPException(400, "Недостаточно монет")

    new_level = current_level + 1
    updates = {}

    if data.upgrade_id == "tap_power":
        updates["tap_power"] = user["tap_power"] + 1
    elif data.upgrade_id == "max_energy":
        updates["max_energy"] = user["max_energy"] + 20
        updates["energy"] = min(user["energy"] + 20, user["max_energy"] + 20)
    elif data.upgrade_id == "multi_tap":
        updates["multi_tap"] = user["multi_tap"] + 1
    elif data.upgrade_id == "energy_regen":
        updates["energy_regen"] = user["energy_regen"] + 0.5

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values())
    conn.execute(
        f"UPDATE users SET coins = coins - ?, {set_clause} WHERE telegram_id = ?",
        [cost] + values + [data.telegram_id]
    )

    if existing:
        conn.execute(
            "UPDATE user_upgrades SET level = ? WHERE telegram_id = ? AND upgrade_id = ?",
            (new_level, data.telegram_id, data.upgrade_id)
        )
    else:
        conn.execute(
            "INSERT INTO user_upgrades (telegram_id, upgrade_id, level) VALUES (?, ?, ?)",
            (data.telegram_id, data.upgrade_id, new_level)
        )

    conn.commit()
    conn.close()

    return {"success": True, "new_level": new_level, "cost": cost}


# --- Главная страница ---
@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


# --- Запуск ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
