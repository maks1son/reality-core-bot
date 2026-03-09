import os
import time
import random
import threading
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from database import init_db, get_user, save_user, get_character, save_character, get_professions, unlock_profession, get_tasks, complete_task

app = FastAPI()

init_db()

# Данные профессий и заданий
PROFESSIONS_DATA = {
    'frontend': {
        'name': 'FRONTEND DEVELOPER',
        'icon': '🎨',
        'description': 'Создание визуальной части веб-приложений',
        'guide': 'Frontend-разработчик отвечает за то, что видит пользователь. Он превращает дизайн в работающий код, делает кнопки кликабельными, анимации плавными, а интерфейс удобным.',
        'tools': ['HTML', 'CSS', 'JavaScript', 'React'],
        'cost': 1
    },
    'backend': {
        'name': 'BACKEND DEVELOPER',
        'icon': '⚙️',
        'description': 'Серверная логика и базы данных',
        'guide': 'Backend-разработчик строит "мозг" приложения. Он создаёт API, работает с базами данных, обеспечивает безопасность и производительность.',
        'tools': ['Python', 'SQL', 'API', 'Docker'],
        'cost': 1
    },
    'mobile': {
        'name': 'MOBILE DEVELOPER',
        'icon': '📱',
        'description': 'Приложения для iOS и Android',
        'guide': 'Mobile-разработчик создаёт приложения для смартфонов. Он должен учитывать особенности touch-интерфейса, ограничения батареи и разные размеры экранов.',
        'tools': ['Swift', 'Kotlin', 'Flutter', 'Firebase'],
        'cost': 1
    },
    'devops': {
        'name': 'DEVOPS ENGINEER',
        'icon': '🚀',
        'description': 'Автоматизация и инфраструктура',
        'guide': 'DevOps-инженер делает так, чтобы код быстро и надёжно попадал на сервера. Он автоматизирует рутину, следит за стабильностью систем.',
        'tools': ['Linux', 'Docker', 'Kubernetes', 'CI/CD'],
        'cost': 2
    },
    'data': {
        'name': 'DATA SCIENTIST',
        'icon': '📊',
        'description': 'Анализ данных и машинное обучение',
        'guide': 'Data Scientist находит закономерности в данных, строит прогнозы и обучает нейросети. Это математика + программирование + бизнес-понимание.',
        'tools': ['Python', 'Pandas', 'ML', 'Statistics'],
        'cost': 2
    },
    'security': {
        'name': 'SECURITY SPECIALIST',
        'icon': '🔒',
        'description': 'Кибербезопасность и защита',
        'guide': 'Специалист по безопасности ищет уязвимости до того, как их найдут злоумышленники. Он мыслит как хакер, чтобы защитить системы.',
        'tools': ['Penetration Testing', 'Cryptography', 'Networking', 'Linux'],
        'cost': 2
    }
}

TASKS_DATA = {
    'frontend': [
        {'id': 'fe_1', 'title': 'Первый HTML', 'description': 'Создай простую страницу с заголовком и параграфом. Это основа всего веба.', 'difficulty': 1, 'reward_coins': 100, 'reward_xp': 20},
        {'id': 'fe_2', 'title': 'CSS стили', 'description': 'Сделай кнопку красной и круглой. Научись менять внешний вид элементов.', 'difficulty': 2, 'reward_coins': 150, 'reward_xp': 30},
        {'id': 'fe_3', 'title': 'JavaScript интерактив', 'description': 'Сделай так, чтобы при клике на кнопку менялся текст. Первая интерактивность!', 'difficulty': 3, 'reward_coins': 250, 'reward_xp': 50},
        {'id': 'fe_4', 'title': 'Адаптивный дизайн', 'description': 'Сделай страницу, которая красиво выглядит и на телефоне, и на компьютере.', 'difficulty': 4, 'reward_coins': 400, 'reward_xp': 80},
        {'id': 'fe_5', 'title': 'Мини-приложение', 'description': 'Создай калькулятор или todo-лист. Полноценное приложение с логикой.', 'difficulty': 5, 'reward_coins': 800, 'reward_xp': 150}
    ],
    'backend': [
        {'id': 'be_1', 'title': 'Первая API', 'description': 'Создай endpoint, который возвращает "Hello, World!"', 'difficulty': 1, 'reward_coins': 100, 'reward_xp': 20},
        {'id': 'be_2', 'title': 'Работа с данными', 'description': 'Сделай API, которое принимает имя и возвращает персонализированное приветствие.', 'difficulty': 2, 'reward_coins': 150, 'reward_xp': 30},
        {'id': 'be_3', 'title': 'База данных', 'description': 'Подключи базу данных и сделай CRUD операции.', 'difficulty': 3, 'reward_coins': 300, 'reward_xp': 60},
        {'id': 'be_4', 'title': 'Аутентификация', 'description': 'Реализуй регистрацию и вход пользователей с хешированием паролей.', 'difficulty': 4, 'reward_coins': 500, 'reward_xp': 100},
        {'id': 'be_5', 'title': 'Масштабирование', 'description': 'Оптимизируй запросы и добавь кэширование для высокой нагрузки.', 'difficulty': 5, 'reward_coins': 1000, 'reward_xp': 200}
    ],
    'mobile': [
        {'id': 'mob_1', 'title': 'Hello Mobile', 'description': 'Создай первое приложение с одним экраном и текстом.', 'difficulty': 1, 'reward_coins': 100, 'reward_xp': 20},
        {'id': 'mob_2', 'title': 'Навигация', 'description': 'Сделай переход между двумя экранами с кнопкой "Назад".', 'difficulty': 2, 'reward_coins': 180, 'reward_xp': 35},
        {'id': 'mob_3', 'title': 'Сенсоры', 'description': 'Используй акселерометр или камеру в приложении.', 'difficulty': 3, 'reward_coins': 350, 'reward_xp': 70},
        {'id': 'mob_4', 'title': 'Офлайн-режим', 'description': 'Сделай так, чтобы приложение работало без интернета.', 'difficulty': 4, 'reward_coins': 600, 'reward_xp': 120},
        {'id': 'mob_5', 'title': 'Публикация', 'description': 'Подготовь приложение к публикации в App Store или Google Play.', 'difficulty': 5, 'reward_coins': 1200, 'reward_xp': 250}
    ],
    'devops': [
        {'id': 'do_1', 'title': 'Linux basics', 'description': 'Освой базовые команды Linux: навигация, файлы, права доступа.', 'difficulty': 1, 'reward_coins': 150, 'reward_xp': 30},
        {'id': 'do_2', 'title': 'Docker контейнер', 'description': 'Запусти приложение в Docker-контейнере.', 'difficulty': 2, 'reward_coins': 250, 'reward_xp': 50},
        {'id': 'do_3', 'title': 'CI/CD Pipeline', 'description': 'Настрой автоматическую сборку и деплой при пуше в git.', 'difficulty': 3, 'reward_coins': 500, 'reward_xp': 100},
        {'id': 'do_4', 'title': 'Kubernetes', 'description': 'Разверни приложение в Kubernetes кластере.', 'difficulty': 4, 'reward_coins': 900, 'reward_xp': 180},
        {'id': 'do_5', 'title': 'Мониторинг', 'description': 'Настрой логирование, метрики и алерты для системы.', 'difficulty': 5, 'reward_coins': 1500, 'reward_xp': 300}
    ],
    'data': [
        {'id': 'ds_1', 'title': 'Первый датасет', 'description': 'Загрузи данные и выведи базовую статистику.', 'difficulty': 1, 'reward_coins': 150, 'reward_xp': 30},
        {'id': 'ds_2', 'title': 'Визуализация', 'description': 'Построй графики и диаграммы для данных.', 'difficulty': 2, 'reward_coins': 250, 'reward_xp': 50},
        {'id': 'ds_3', 'title': 'Предсказание', 'description': 'Обучи простую модель линейной регрессии.', 'difficulty': 3, 'reward_coins': 500, 'reward_xp': 100},
        {'id': 'ds_4', 'title': 'Нейросеть', 'description': 'Создай и обучи нейросеть для классификации.', 'difficulty': 4, 'reward_coins': 1000, 'reward_xp': 200},
        {'id': 'ds_5', 'title': 'Production ML', 'description': 'Разверни модель как API сервис с мониторингом качества.', 'difficulty': 5, 'reward_coins': 2000, 'reward_xp': 400}
    ],
    'marketing': [
        {'id': 'mk_1', 'title': 'Целевая аудитория', 'description': 'Определи ЦА для нового приложения. Кто покупатель?', 'difficulty': 1, 'reward_coins': 100, 'reward_xp': 20},
        {'id': 'mk_2', 'title': 'CTR анализ', 'description': 'Разбери метрики рекламной кампании и найди слабое место.', 'difficulty': 2, 'reward_coins': 180, 'reward_xp': 35},
        {'id': 'mk_3', 'title': 'SMM стратегия', 'description': 'Придумай контент-план для бренда в Instagram на месяц.', 'difficulty': 3, 'reward_coins': 350, 'reward_xp': 70},
    ],
    'finance': [
        {'id': 'fin_1', 'title': 'Ликвидность', 'description': 'Оцени ликвидность разных активов: акции, квартира, золото.', 'difficulty': 1, 'reward_coins': 100, 'reward_xp': 20},
        {'id': 'fin_2', 'title': 'Диверсификация', 'description': 'Составь диверсифицированный портфель из 5 активов.', 'difficulty': 2, 'reward_coins': 200, 'reward_xp': 40},
    ],
    'design': [
        {'id': 'des_1', 'title': 'Цветовая теория', 'description': 'Подбери цветовую палитру для мобильного приложения.', 'difficulty': 1, 'reward_coins': 100, 'reward_xp': 20},
        {'id': 'des_2', 'title': 'UX исследование', 'description': 'Проведи 5-секундный тест и опиши что запомнил пользователь.', 'difficulty': 2, 'reward_coins': 200, 'reward_xp': 40},
    ],
    'gamedev': [
        {'id': 'gd_1', 'title': 'Игровой движок', 'description': 'Установи Unity и создай первую сцену с кубом.', 'difficulty': 1, 'reward_coins': 150, 'reward_xp': 30},
        {'id': 'gd_2', 'title': 'Спрайты', 'description': 'Создай спрайт и анимируй его в Unity.', 'difficulty': 2, 'reward_coins': 280, 'reward_xp': 55},
    ],
    'medicine': [
        {'id': 'med_1', 'title': 'ЭКГ основы', 'description': 'Изучи нормальный ритм ЭКГ и его компоненты.', 'difficulty': 1, 'reward_coins': 150, 'reward_xp': 30},
        {'id': 'med_2', 'title': 'Антибиотики', 'description': 'Разбери механизм действия антибиотиков и их применение.', 'difficulty': 2, 'reward_coins': 280, 'reward_xp': 55},
    ],
    'robotics': [
        {'id': 'rob_1', 'title': 'Python для роботов', 'description': 'Напиши скрипт управления моторами через GPIO.', 'difficulty': 1, 'reward_coins': 150, 'reward_xp': 30},
        {'id': 'rob_2', 'title': 'Сервоприводы', 'description': 'Настрой сервопривод на точные угловые движения.', 'difficulty': 2, 'reward_coins': 300, 'reward_xp': 60},
    ],
    'security': [
        {'id': 'sec_1', 'title': 'Сканирование', 'description': 'Просканируй сайт на открытые порты и версии ПО.', 'difficulty': 1, 'reward_coins': 150, 'reward_xp': 30},
        {'id': 'sec_2', 'title': 'SQL Injection', 'description': 'Найди и исправь уязвимость SQL-инъекции.', 'difficulty': 2, 'reward_coins': 300, 'reward_xp': 60},
        {'id': 'sec_3', 'title': 'XSS атака', 'description': 'Продемонстрируй и защити от XSS-уязвимости.', 'difficulty': 3, 'reward_coins': 600, 'reward_xp': 120},
        {'id': 'sec_4', 'title': 'Reverse Engineering', 'description': 'Проанализируй бинарный файл и найди скрытую функцию.', 'difficulty': 4, 'reward_coins': 1200, 'reward_xp': 250},
        {'id': 'sec_5', 'title': 'Red Team', 'description': 'Проведи полноценный тест на проникновение системы.', 'difficulty': 5, 'reward_coins': 2500, 'reward_xp': 500}
    ]
}

# Хранилище сессий
sessions = {}
session_lock = threading.Lock()

def get_session(user_id):
    with session_lock:
        if user_id not in sessions:
            sessions[user_id] = {
                'last_tap': time.time(),
                'combo_taps': 0,
                'current_multiplier': 1.0,
                'last_energy_update': time.time(),
                'was_full': True
            }
        return sessions[user_id]

# === API маршруты ===

@app.get("/api/state")
async def get_state(user_id: int):
    user = get_user(user_id)
    character = get_character(user_id)
    session = get_session(user_id)
    professions = get_professions(user_id)
    completed_tasks = get_tasks(user_id)
    
    # Плавное восстановление энергии
    now = time.time()
    time_passed = now - session['last_energy_update']
    energy_recovered = int(time_passed * 2)
    
    full_recovery = False
    
    if energy_recovered > 0 and user['energy'] < 100:
        old_energy = user['energy']
        user['energy'] = min(100, user['energy'] + energy_recovered)
        actual_recovered = user['energy'] - old_energy
        
        if actual_recovered > 0:
            save_user(user_id, user['coins'], user['energy'], user['xp'], user['level'], 
                     user['total_taps'], user['tokens'])
            session['last_energy_update'] = now
            
            if user['energy'] >= 100 and not session['was_full']:
                full_recovery = True
                session['was_full'] = True
        else:
            session['last_energy_update'] = now
    elif user['energy'] >= 100:
        session['was_full'] = True
        session['last_energy_update'] = now
    else:
        session['was_full'] = False
    
    # Сброс комбо
    afk_time = now - session['last_tap']
    combo_reset = afk_time > 5
    
    if combo_reset and session['combo_taps'] > 0:
        session['combo_taps'] = 0
        session['current_multiplier'] = 1.0
    
    return {
        'user': user, 
        'character': character,
        'professions': professions,
        'completed_tasks': completed_tasks,
        'full_recovery': full_recovery,
        'combo_reset': combo_reset,
        'session': {
            'current_multiplier': session['current_multiplier'],
            'combo_taps': session['combo_taps']
        }
    }

@app.post("/api/tap")
async def do_tap(request: Request):
    data = await request.json()
    user_id = data.get('user_id')
    timestamp = data.get('timestamp', 0)
    pattern = data.get('pattern', [])
    fingers = data.get('fingers', 1)
    
    user = get_user(user_id)
    session = get_session(user_id)
    session['last_tap'] = time.time()
    session['last_energy_update'] = time.time()
    session['was_full'] = user['energy'] >= 100
    
    if user['energy'] < fingers:
        return {'success': False, 'message': 'Недостаточно энергии!'}
    
    # Защита от автокликеров
    current_time = time.time() * 1000
    time_diff = current_time - timestamp
    
    if time_diff < 50:
        return {'success': False, 'message': 'Слишком быстро!', 'cheat_detected': True}
    
    if len(pattern) >= 3:
        intervals = []
        for i in range(1, len(pattern)):
            intervals.append(pattern[i] - pattern[i-1])
        
        if len(intervals) >= 2:
            variance = sum((x - sum(intervals)/len(intervals)) ** 2 for x in intervals) / len(intervals)
            if variance < 10:
                return {'success': False, 'message': 'Обнаружен автокликер!', 'cheat_detected': True}
            if min(intervals) < 60:
                return {'success': False, 'message': 'Слишком быстро!', 'cheat_detected': True}
    
    # Система комбо
    easy_multipliers = [1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9]
    easy_thresholds = [5, 15, 30, 50, 75, 105, 140, 180, 225]
    
    session['combo_taps'] += fingers
    
    multiplier = 1.0
    for i, thresh in enumerate(easy_thresholds):
        if session['combo_taps'] >= thresh:
            multiplier = easy_multipliers[i]
    
    if session['combo_taps'] >= 300:
        extra = session['combo_taps'] - 300
        bonus_levels = extra // 150
        multiplier = 2.0 + (bonus_levels * 0.1)
        multiplier = min(multiplier, 5.0)
    
    session['current_multiplier'] = multiplier
    
    # Награда
    base_reward = 1 * fingers
    total_reward = int(base_reward * multiplier)
    
    # Опыт: 5 XP за тап
    new_total_taps = user.get('total_taps', 0) + fingers
    xp_gained = fingers * 5
    new_xp = user.get('xp', 0) + xp_gained
    
    # Уровень
    def xp_for_level(lvl):
        if lvl == 1:
            return 0
        elif lvl == 2:
            return 50
        else:
            return 50 + (lvl - 2) * 100
    
    old_level = user.get('level', 1)
    new_level = old_level
    tokens_gained = 0
    level_up = False
    
    while new_xp >= xp_for_level(new_level + 1):
        new_level += 1
        tokens_gained += 1
    
    if new_level > old_level:
        level_up = True
    
    # Обновление
    user['coins'] = user.get('coins', 0) + total_reward
    user['energy'] = max(0, user['energy'] - fingers)
    user['total_taps'] = new_total_taps
    user['xp'] = new_xp
    user['level'] = new_level
    user['tokens'] = user.get('tokens', 0) + tokens_gained
    
    save_user(user_id, user['coins'], user['energy'], user['xp'], user['level'], 
             user['total_taps'], user['tokens'])
    
    professions_unlocked = level_up and new_level == 2
    
    return {
        'success': True, 
        'reward': total_reward,
        'multiplier': multiplier,
        'coins': user['coins'],
        'energy': user['energy'],
        'xp': user['xp'],
        'level': user['level'],
        'xp_gained': xp_gained,
        'level_up': level_up,
        'tokens_gained': tokens_gained,
        'total_taps': user['total_taps'],
        'combo_taps': session['combo_taps'],
        'professions_unlocked': professions_unlocked,
        'tokens': user['tokens']
    }

@app.post("/api/character")
async def create_character(request: Request):
    data = await request.json()
    save_character(
        data['user_id'],
        data['name'],
        data['avatar'],
        data['strength'],
        data['intelligence'],
        data['charisma'],
        data['luck']
    )
    save_user(data['user_id'], 0, 100, 0, 1, 0, 0)
    return {'success': True}

@app.get("/api/profession_data")
async def get_profession_data(prof_key: str):
    if prof_key in PROFESSIONS_DATA:
        return {'success': True, 'data': PROFESSIONS_DATA[prof_key]}
    return {'success': False, 'message': 'Profession not found'}

@app.get("/api/profession_tasks")
async def get_profession_tasks(prof_key: str, user_id: int):
    if prof_key not in TASKS_DATA:
        return {'success': False, 'message': 'No tasks found'}
    
    completed = get_tasks(user_id)
    tasks = TASKS_DATA[prof_key]
    
    for task in tasks:
        task['completed'] = task['id'] in completed
    
    return {'success': True, 'tasks': tasks}

@app.post("/api/unlock_profession")
async def api_unlock_profession(request: Request):
    data = await request.json()
    user_id = data.get('user_id')
    prof_key = data.get('prof_key')
    
    user = get_user(user_id)
    
    if prof_key not in PROFESSIONS_DATA:
        return {'success': False, 'message': 'Profession not found'}
    
    prof_data = PROFESSIONS_DATA[prof_key]
    cost = prof_data['cost']
    
    if user['tokens'] < cost:
        return {'success': False, 'message': 'Недостаточно токенов!'}
    
    existing = get_professions(user_id)
    if prof_key in existing:
        return {'success': False, 'message': 'Already unlocked'}
    
    user['tokens'] -= cost
    save_user(user_id, user['coins'], user['energy'], user['xp'], user['level'], 
             user['total_taps'], user['tokens'])
    unlock_profession(user_id, prof_key)
    
    return {
        'success': True, 
        'tokens': user['tokens'],
        'profession': prof_data
    }

@app.post("/api/complete_task")
async def api_complete_task(request: Request):
    data = await request.json()
    user_id = data.get('user_id')
    task_id = data.get('task_id')
    prof_key = data.get('prof_key')
    
    user = get_user(user_id)
    
    if prof_key not in TASKS_DATA:
        return {'success': False, 'message': 'Profession not found'}
    
    task = None
    for t in TASKS_DATA[prof_key]:
        if t['id'] == task_id:
            task = t
            break
    
    if not task:
        return {'success': False, 'message': 'Task not found'}
    
    completed = get_tasks(user_id)
    if task_id in completed:
        return {'success': False, 'message': 'Already completed'}
    
    # Проверяем предыдущие задания
    tasks = TASKS_DATA[prof_key]
    task_idx = tasks.index(task)
    if task_idx > 0:
        prev_task = tasks[task_idx - 1]
        if prev_task['id'] not in completed:
            return {'success': False, 'message': 'Complete previous task first'}
    
    user['coins'] += task['reward_coins']
    user['xp'] += task['reward_xp']
    
    def xp_for_level(lvl):
        if lvl == 1:
            return 0
        elif lvl == 2:
            return 50
        else:
            return 50 + (lvl - 2) * 100
    
    new_level = user['level']
    tokens_gained = 0
    while user['xp'] >= xp_for_level(new_level + 1):
        new_level += 1
        tokens_gained += 1
    
    user['level'] = new_level
    user['tokens'] += tokens_gained
    
    save_user(user_id, user['coins'], user['energy'], user['xp'], user['level'], 
             user['total_taps'], user['tokens'])
    complete_task(user_id, task_id)
    
    return {
        'success': True,
        'coins': user['coins'],
        'xp': user['xp'],
        'level': user['level'],
        'tokens': user['tokens'],
        'tokens_gained': tokens_gained,
        'level_up': tokens_gained > 0,
        'reward': {
            'coins': task['reward_coins'],
            'xp': task['reward_xp']
        }
    }

# === HTML Template ===
HTML_TEMPLATE = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>RE:ALITY: Core</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet">
    <style>
        * { 
            margin: 0; 
            padding: 0; 
            box-sizing: border-box; 
            image-rendering: pixelated; 
            user-select: none; 
            -webkit-user-select: none; 
            touch-action: manipulation;
            -webkit-tap-highlight-color: transparent;
        }
        :root {
            --bg-color: #2d1b4e;
            --panel-bg: #1a0f2e;
            --border-color: #4a3b6b;
            --accent: #ff6b9d;
            --success: #4ecdc4;
            --warning: #ffe66d;
            --danger: #ff6b6b;
            --text: #f7f1e3;
            --coin: #ffd700;
            --xp: #9b59b6;
            --token: #3498db;
            --it: #00d4aa;
        }
        html, body { 
            height: 100%; 
            overflow: hidden; 
            background: var(--bg-color);
        }
        body {
            font-family: 'Press Start 2P', cursive;
            color: var(--text);
            font-size: 8px;
        }
        .container { 
            height: 100vh;
            max-width: 400px; 
            margin: 0 auto; 
            display: flex;
            flex-direction: column;
            padding: 10px;
            gap: 10px;
            position: relative;
        }
        .hidden { display: none !important; }
        .pixel-box {
            background: var(--panel-bg);
            border: 3px solid var(--border-color);
            box-shadow: 3px 3px 0px #000;
        }
        .screen {
            display: none;
            flex-direction: column;
            height: 100%;
            gap: 10px;
        }
        .screen.show {
            display: flex;
        }
        .side-buttons {
            position: fixed;
            left: 0;
            top: 50%;
            transform: translateY(-50%);
            display: flex;
            flex-direction: column;
            gap: 10px;
            z-index: 100;
        }
        .side-btn {
            writing-mode: vertical-rl;
            text-orientation: mixed;
            padding: 15px 8px;
            border: 3px solid #000;
            border-left: none;
            box-shadow: 3px 3px 0px rgba(0,0,0,0.5);
            color: white;
            font-family: 'Press Start 2P', cursive;
            font-size: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .side-btn:active {
            transform: translateX(2px);
        }
        .side-btn.prof {
            background: var(--token);
        }
        .side-btn.tasks {
            background: var(--warning);
            color: #000;
        }
        .side-btn.new {
            animation: pulse-border 1s infinite;
        }
        @keyframes pulse-border {
            0%, 100% { box-shadow: 3px 3px 0px rgba(0,0,0,0.5), 0 0 10px var(--success); }
            50% { box-shadow: 3px 3px 0px rgba(0,0,0,0.5), 0 0 20px var(--success); }
        }
        .create-header {
            text-align: center;
            padding: 4px;
        }
        .create-header h1 { 
            font-size: 14px; 
            color: var(--accent);
            text-shadow: 2px 2px 0px #000;
        }
        .create-header p { 
            font-size: 7px; 
            color: #8b7cb0;
            margin-top: 4px;
        }
        .heroes-select {
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 10px;
            padding: 10px 0;
        }
        .section-label {
            text-align: center;
            font-size: 8px;
            color: var(--warning);
        }
        .heroes-trio {
            display: flex;
            justify-content: center;
            gap: 15px;
        }
        .hero-slot {
            width: 90px;
            height: 140px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-end;
            background: var(--panel-bg);
            border: 4px solid var(--border-color);
            box-shadow: 4px 4px 0px #000;
            cursor: pointer;
            padding: 8px;
            position: relative;
            transition: all 0.2s;
        }
        .hero-slot:hover, .hero-slot.selected { 
            border-color: var(--accent);
            transform: translate(-2px, -2px);
            box-shadow: 6px 6px 0px #000;
        }
        .slot-number {
            position: absolute;
            top: 5px;
            left: 5px;
            font-size: 10px;
            color: #666;
        }
        .hero-preview img {
            width: 64px;
            height: 64px;
            image-rendering: pixelated;
        }
        .name-input {
            flex: 1;
            padding: 12px;
            font-family: 'Press Start 2P', cursive;
            font-size: 12px;
            background: var(--panel-bg);
            border: 3px solid var(--border-color);
            box-shadow: 3px 3px 0px #000;
            color: var(--text);
            outline: none;
            text-align: center;
        }
        .stats-compact {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 6px;
        }
        .stat-box {
            padding: 8px 4px;
            text-align: center;
        }
        .stat-ico {
            font-size: 14px;
            margin-bottom: 4px;
        }
        .stat-row-mini {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
        }
        .stat-btn-mini {
            width: 18px;
            height: 18px;
            font-family: 'Press Start 2P', cursive;
            font-size: 10px;
            background: var(--accent);
            border: none;
            box-shadow: 2px 2px 0px #000;
            color: white;
            cursor: pointer;
        }
        .start-btn {
            padding: 15px;
            font-family: 'Press Start 2P', cursive;
            font-size: 14px;
            background: var(--success);
            border: none;
            box-shadow: 4px 4px 0px #2d8b84;
            color: #000;
            cursor: pointer;
        }
        .start-btn:disabled { 
            opacity: 0.4;
            background: #666;
        }
        .top-panel {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .header-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
        }
        .player-name {
            font-size: 12px;
            color: var(--accent);
            text-shadow: 2px 2px 0px #000;
        }
        .player-level {
            font-size: 8px;
            color: var(--xp);
        }
        .xp-bar-container {
            width: 100px;
            height: 8px;
            background: #000;
            border: 1px solid var(--border-color);
        }
        .xp-fill {
            height: 100%;
            background: var(--xp);
            transition: width 0.3s;
        }
        .resources-row {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 8px;
        }
        .res-box {
            padding: 8px;
            text-align: center;
        }
        .res-box.coins { border-color: var(--coin); }
        .res-box.tokens { border-color: var(--token); }
        .res-value {
            font-size: 12px;
            color: var(--success);
        }
        .res-value.coins { color: var(--coin); }
        .res-value.tokens { color: var(--token); }
        .energy-bar-container {
            height: 20px;
            position: relative;
            overflow: hidden;
        }
        .energy-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--danger), var(--warning), var(--success));
            transition: width 0.5s;
        }
        .recovery-status {
            text-align: center;
            font-size: 7px;
            color: var(--success);
            opacity: 0;
            height: 10px;
        }
        .recovery-status.show { opacity: 1; }
        .tap-area {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .hero-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 15px;
            cursor: pointer;
            padding: 20px;
            position: relative;
        }
        .hero-sprite {
            width: 80px;
            height: 80px;
            animation: breathe 2s ease-in-out infinite;
            filter: drop-shadow(4px 4px 0px #000);
        }
        @keyframes breathe {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-6px); }
        }
        .floating-reward {
            position: absolute;
            font-size: 14px;
            color: var(--coin);
            text-shadow: 2px 2px 0px #000;
            pointer-events: none;
            animation: floatUp 0.8s forwards;
        }
        @keyframes floatUp {
            0% { opacity: 1; transform: translateY(0); }
            100% { opacity: 0; transform: translateY(-40px); }
        }
        .professions-grid {
            flex: 1;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            padding: 10px;
            overflow-y: auto;
        }
        .profession-card {
            aspect-ratio: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 10px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .profession-card.locked {
            opacity: 0.4;
            filter: grayscale(1);
            cursor: not-allowed;
        }
        .profession-card.available {
            border-color: var(--token);
            animation: glow 2s infinite;
        }
        .profession-card.unlocked {
            border-color: var(--success);
            background: linear-gradient(135deg, var(--panel-bg), #0f3d3e);
        }
        @keyframes glow {
            0%, 100% { box-shadow: 0 0 5px var(--token); }
            50% { box-shadow: 0 0 15px var(--token); }
        }
        .prof-icon { font-size: 32px; }
        .prof-name { font-size: 8px; text-align: center; }
        .prof-cost { font-size: 7px; color: var(--token); }
        .guide-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.95);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 2000;
            padding: 20px;
        }
        .guide-modal.show { display: flex; }
        .guide-content {
            background: var(--panel-bg);
            border: 4px solid var(--success);
            padding: 20px;
            max-width: 350px;
            width: 100%;
            max-height: 80vh;
            overflow-y: auto;
        }
        .guide-title {
            font-size: 12px;
            color: var(--success);
            margin-bottom: 15px;
            text-align: center;
        }
        .guide-section {
            margin-bottom: 15px;
        }
        .guide-section h4 {
            font-size: 8px;
            color: var(--warning);
            margin-bottom: 5px;
        }
        .guide-section p {
            font-size: 7px;
            line-height: 1.6;
            color: #aaa;
        }
        .guide-tools {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
        }
        .tool-tag {
            padding: 4px 8px;
            background: var(--border-color);
            font-size: 6px;
        }
        .guide-btn {
            width: 100%;
            padding: 12px;
            margin-top: 10px;
            font-family: 'Press Start 2P', cursive;
            font-size: 10px;
            background: var(--success);
            border: none;
            box-shadow: 3px 3px 0px #2d8b84;
            color: #000;
            cursor: pointer;
        }
        .tasks-list {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
            padding: 10px;
        }
        .task-card {
            padding: 15px;
            border: 3px solid var(--border-color);
            cursor: pointer;
            transition: all 0.2s;
            position: relative;
        }
        .task-card:hover:not(.completed):not(.locked) {
            border-color: var(--warning);
            transform: translate(-2px, -2px);
        }
        .task-card.completed {
            opacity: 0.5;
            border-color: var(--success);
            cursor: default;
        }
        .task-card.locked {
            opacity: 0.3;
            cursor: not-allowed;
        }
        .task-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .task-title {
            font-size: 10px;
            color: var(--text);
        }
        .task-difficulty {
            font-size: 7px;
            padding: 3px 6px;
            background: var(--warning);
            color: #000;
        }
        .task-desc {
            font-size: 7px;
            color: #888;
            margin-bottom: 10px;
            line-height: 1.4;
        }
        .task-reward {
            display: flex;
            gap: 15px;
            font-size: 8px;
        }
        .task-reward span {
            color: var(--coin);
        }
        .back-btn {
            padding: 15px;
            font-family: 'Press Start 2P', cursive;
            font-size: 10px;
            background: var(--panel-bg);
            border: 3px solid var(--border-color);
            color: var(--text);
            cursor: pointer;
        }
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .modal-overlay.show { display: flex; }
        .modal-content {
            background: var(--panel-bg);
            border: 4px solid var(--success);
            padding: 20px;
            max-width: 350px;
            text-align: center;
        }
        .modal-title {
            font-size: 12px;
            color: var(--success);
            margin-bottom: 15px;
        }
        .modal-text {
            font-size: 8px;
            margin-bottom: 20px;
            line-height: 1.6;
        }
        .modal-btn {
            padding: 12px 24px;
            font-family: 'Press Start 2P', cursive;
            font-size: 10px;
            background: var(--success);
            border: none;
            box-shadow: 4px 4px 0px #2d8b84;
            color: #000;
            cursor: pointer;
        }
        .toast {
            position: fixed;
            top: 20%;
            left: 50%;
            transform: translateX(-50%) scale(0);
            padding: 10px 20px;
            background: var(--success);
            color: #000;
            border: 3px solid #000;
            box-shadow: 4px 4px 0px #000;
            font-size: 8px;
            z-index: 999;
            transition: transform 0.3s;
        }
        .toast.show { transform: translateX(-50%) scale(1); }
        .sphere-screen-grid {
            flex: 1;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            padding: 10px;
            overflow-y: auto;
        }
        .sphere-card {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 10px;
            padding: 18px 10px;
            cursor: pointer;
            transition: all 0.2s;
            border: 3px solid var(--border-color);
            background: var(--panel-bg);
            box-shadow: 3px 3px 0px #000;
        }
        .sphere-card:active { transform: translate(2px, 2px); box-shadow: 1px 1px 0px #000; }
        .sphere-icon { font-size: 36px; }
        .sphere-name { font-size: 7px; text-align: center; line-height: 1.5; }
        .sphere-count { font-size: 6px; color: #888; }
        .sphere-card.it { border-color: var(--it); }
        .sphere-card.biz { border-color: var(--warning); }
        .sphere-card.creative { border-color: var(--accent); }
        .sphere-card.science { border-color: #27ae60; }
        /* Mini-game modal */
        .minigame-modal {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.97);
            display: none; align-items: center; justify-content: center;
            z-index: 3000; padding: 15px;
        }
        .minigame-modal.show { display: flex; }
        .minigame-content {
            background: var(--panel-bg);
            border: 4px solid var(--warning);
            padding: 20px;
            max-width: 360px;
            width: 100%;
            max-height: 88vh;
            overflow-y: auto;
        }
        .mg-header { text-align: center; margin-bottom: 15px; }
        .mg-title { font-size: 10px; color: var(--warning); margin-bottom: 6px; }
        .mg-task-name { font-size: 8px; color: var(--text); }
        .mg-question { font-size: 8px; color: #ccc; line-height: 1.7; margin: 15px 0 12px; }
        .mg-options { display: flex; flex-direction: column; gap: 8px; }
        .mg-option {
            padding: 12px 10px;
            border: 2px solid var(--border-color);
            font-family: 'Press Start 2P', cursive;
            font-size: 7px;
            color: var(--text);
            background: transparent;
            cursor: pointer;
            text-align: left;
            line-height: 1.5;
            transition: all 0.15s;
        }
        .mg-option:hover { border-color: var(--warning); color: var(--warning); }
        .mg-option.correct { border-color: var(--success); color: var(--success); background: rgba(78,205,196,0.1); }
        .mg-option.wrong { border-color: var(--danger); color: var(--danger); background: rgba(255,107,107,0.1); }
        .mg-feedback { text-align: center; margin-top: 12px; font-size: 8px; min-height: 20px; }
        .mg-feedback.ok { color: var(--success); }
        .mg-feedback.fail { color: var(--danger); }
        .mg-reward { text-align: center; margin-top: 10px; font-size: 7px; color: var(--coin); }
        .mg-close-btn {
            width: 100%; padding: 12px; margin-top: 12px;
            font-family: 'Press Start 2P', cursive; font-size: 9px;
            background: var(--border-color); border: none; color: var(--text); cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="toast" id="toast"></div>
    
    <div class="modal-overlay" id="unlockModal">
        <div class="modal-content">
            <div class="modal-title">🎉 ОТКРЫТ ВЫБОР ПРОФЕССИЙ!</div>
            <div class="modal-text">
                Поздравляем с достижением 2 уровня!<br><br>
                Теперь ты можешь исследовать профессии.<br><br>
                Получено: <span style="color: var(--token);">1 ТОКЕН ИССЛЕДОВАНИЯ</span>
            </div>
            <button class="modal-btn" onclick="goToProfessions()">ПРОДОЛЖИТЬ ➤</button>
        </div>
    </div>
    
    <div class="guide-modal" id="guideModal">
        <div class="guide-content">
            <div class="guide-title" id="guideTitle">PROFESSION GUIDE</div>
            <div class="guide-section">
                <h4>📋 ОПИСАНИЕ</h4>
                <p id="guideDesc">Описание профессии...</p>
            </div>
            <div class="guide-section">
                <h4>🛠️ ИНСТРУМЕНТЫ</h4>
                <div class="guide-tools" id="guideTools"></div>
            </div>
            <div class="guide-section">
                <h4>💡 ЧТО БУДЕШЬ ДЕЛАТЬ</h4>
                <p id="guideActivity">Активность...</p>
            </div>
            <button class="guide-btn" id="guideActionBtn" onclick="unlockOrStart()">ОТКРЫТЬ ЗА 1 ТОКЕН</button>
            <button class="guide-btn" onclick="closeGuide()" style="background: var(--panel-bg); color: var(--text); margin-top: 5px;">ЗАКРЫТЬ</button>
        </div>
    </div>

    <div class="minigame-modal" id="minigameModal">
        <div class="minigame-content">
            <div class="mg-header">
                <div class="mg-title">🎮 МИНИ-ИГРА</div>
                <div class="mg-task-name" id="mgTaskName"></div>
            </div>
            <div class="mg-question" id="mgQuestion"></div>
            <div class="mg-options" id="mgOptions"></div>
            <div class="mg-feedback" id="mgFeedback"></div>
            <div class="mg-reward" id="mgReward"></div>
            <button class="mg-close-btn" id="mgCloseBtn" onclick="closeMinigame()">✕ ЗАКРЫТЬ</button>
        </div>
    </div>


        <div class="create-header">
            <h1>◆ RE:ALITY ◆</h1>
            <p>CHOOSE YOUR CHARACTER</p>
        </div>
        
        <div class="heroes-select">
            <div class="section-label">◆ SELECT HERO ◆</div>
            <div class="heroes-trio">
                <div class="hero-slot" data-slot="1" data-avatar="hero1">
                    <span class="slot-number">1</span>
                    <div class="hero-preview"><img src="/hero1.png" alt="Hero 1"></div>
                    <div class="slot-label">HERO 1</div>
                </div>
                <div class="hero-slot" data-slot="2" data-avatar="hero2">
                    <span class="slot-number">2</span>
                    <div class="hero-preview"><img src="/hero2.png" alt="Hero 2"></div>
                    <div class="slot-label">HERO 2</div>
                </div>
                <div class="hero-slot" data-slot="3" data-avatar="hero3">
                    <span class="slot-number">3</span>
                    <div class="hero-preview"><img src="/hero3.png" alt="Hero 3"></div>
                    <div class="slot-label">HERO 3</div>
                </div>
            </div>
        </div>
        
        <div class="name-section">
            <input type="text" class="name-input pixel-box" id="charName" placeholder="NAME" maxlength="8">
        </div>
        
        <div class="stats-compact">
            <div class="stat-box pixel-box">
                <div class="stat-ico">💪</div>
                <div class="stat-row-mini">
                    <button class="stat-btn-mini" onclick="chg('str',-1)">-</button>
                    <span class="stat-val" id="str">5</span>
                    <button class="stat-btn-mini" onclick="chg('str',1)">+</button>
                </div>
            </div>
            <div class="stat-box pixel-box">
                <div class="stat-ico">🧠</div>
                <div class="stat-row-mini">
                    <button class="stat-btn-mini" onclick="chg('int',-1)">-</button>
                    <span class="stat-val" id="int">5</span>
                    <button class="stat-btn-mini" onclick="chg('int',1)">+</button>
                </div>
            </div>
            <div class="stat-box pixel-box">
                <div class="stat-ico">✨</div>
                <div class="stat-row-mini">
                    <button class="stat-btn-mini" onclick="chg('cha',-1)">-</button>
                    <span class="stat-val" id="cha">5</span>
                    <button class="stat-btn-mini" onclick="chg('cha',1)">+</button>
                </div>
            </div>
            <div class="stat-box pixel-box">
                <div class="stat-ico">🍀</div>
                <div class="stat-row-mini">
                    <button class="stat-btn-mini" onclick="chg('lck',-1)">-</button>
                    <span class="stat-val" id="lck">5</span>
                    <button class="stat-btn-mini" onclick="chg('lck',1)">+</button>
                </div>
            </div>
        </div>
        
        <div class="points-bar">
            POINTS: <span id="pts">0</span>/20
        </div>
        
        <button class="start-btn" id="startBtn" onclick="create()" disabled>START ▶</button>
    </div>
    
    <div class="container screen" id="gameScreen">
        <div class="side-buttons">
            <button class="side-btn prof" id="profBtn" onclick="openProfessions()">ПРОФЕССИИ</button>
            <button class="side-btn tasks" id="tasksBtn" onclick="openTasks()">ЗАДАНИЯ</button>
        </div>
        
        <div class="top-panel">
            <div class="header-row pixel-box">
                <div>
                    <div class="player-name" id="displayName">HERO</div>
                    <div class="player-level">LVL <span id="displayLevel">1</span></div>
                </div>
                <div class="xp-bar-container">
                    <div class="xp-fill" id="xpBar" style="width:0%"></div>
                </div>
            </div>
            
            <div class="resources-row">
                <div class="res-box pixel-box coins">
                    <div style="font-size: 10px;">🪙</div>
                    <div class="res-value coins" id="displayCoins">0</div>
                </div>
                <div class="res-box pixel-box tokens">
                    <div style="font-size: 10px;">🔷</div>
                    <div class="res-value tokens" id="displayTokens">0</div>
                </div>
                <div class="res-box pixel-box">
                    <div style="font-size: 10px;">⚡</div>
                    <div class="res-value" id="displayEnergy">100</div>
                </div>
            </div>
            
            <div class="energy-bar-container pixel-box">
                <div class="energy-fill" id="energyBar" style="width:100%"></div>
            </div>
            <div class="recovery-status" id="recoveryStatus">⚡ ЭНЕРГИЯ ВОССТАНОВЛЕНА</div>
        </div>
        
        <div class="tap-area" id="tapArea">
            <div class="hero-container" id="heroContainer">
                <img src="/hero1.png" alt="Hero" class="hero-sprite" id="gameHero">
                <div style="font-size: 8px; color: var(--warning);">👆 ТАПАЙ ПО ПЕРСОНАЖУ</div>
            </div>
        </div>
        
        <div class="pixel-box" style="padding: 10px; text-align: center;">
            <span style="font-size: 10px;">
                💪 <span id="statStr">5</span> | 
                🧠 <span id="statInt">5</span> | 
                ✨ <span id="statCha">5</span> | 
                🍀 <span id="statLck">5</span>
            </span>
        </div>
    </div>
    
    <div class="container screen" id="professionsScreen">
        <div class="pixel-box" style="padding: 15px; text-align: center;">
            <h2 style="font-size: 12px; color: var(--token);" id="profScreenTitle">◆ СФЕРЫ ПРОФЕССИЙ ◆</h2>
            <div style="margin-top: 8px; font-size: 8px; color: #888;" id="profScreenSubtitle">Выбери сферу для изучения</div>
            <div style="margin-top: 6px; font-size: 10px; color: var(--token);">
                🔷 ТОКЕНОВ: <span id="profScreenTokens">0</span>
            </div>
        </div>
        
        <!-- Sphere selection grid -->
        <div class="sphere-screen-grid" id="sphereGrid"></div>
        <!-- Professions grid (hidden initially) -->
        <div class="professions-grid hidden" id="professionsGrid"></div>
        
        <button class="back-btn" id="profBackBtn" onclick="profBackAction()">◀ НАЗАД</button>
    </div>
    
    <div class="container screen" id="tasksScreen">
        <div class="pixel-box" style="padding: 15px; text-align: center;">
            <h2 style="font-size: 12px; color: var(--warning);">◆ ЗАДАНИЯ ◆</h2>
            <div style="margin-top: 5px; font-size: 8px; color: #888;" id="tasksSubtitle">
                Выбери профессию чтобы видеть задания
            </div>
        </div>
        
        <div class="tasks-list" id="tasksList"></div>
        
        <button class="back-btn" onclick="backToGame()">◀ НАЗАД</button>
    </div>

    <script>
        let tg = window.Telegram.WebApp;
        tg.expand();
        
        let uid = tg.initDataUnsafe?.user?.id || 1;
        let state = {}, hero = {}, sel = '';
        let stats = {str:5, int:5, cha:5, lck:5};
        let tapPattern = [], lastTapTime = 0, isProcessing = false;
        let currentMultiplier = 1.0, professionsUnlockedShown = false;
        let currentGuideProf = null;
        let unlockedProfs = {};
        let completedTasks = [];
        let currentTaskProf = null;
        
        const MAX = 20, MIN = 1;
        
        const professionsData = {
            'frontend': {name: 'FRONTEND DEV', icon: '🎨', cost: 1, sphere: 'it'},
            'backend': {name: 'BACKEND DEV', icon: '⚙️', cost: 1, sphere: 'it'},
            'mobile': {name: 'MOBILE DEV', icon: '📱', cost: 1, sphere: 'it'},
            'devops': {name: 'DEVOPS', icon: '🚀', cost: 2, sphere: 'it'},
            'data': {name: 'DATA SCIENCE', icon: '📊', cost: 2, sphere: 'it'},
            'security': {name: 'SECURITY', icon: '🔒', cost: 2, sphere: 'it'},
            'marketing': {name: 'МАРКЕТИНГ', icon: '📣', cost: 1, sphere: 'biz'},
            'finance': {name: 'ФИНАНСЫ', icon: '💰', cost: 1, sphere: 'biz'},
            'design': {name: 'ДИЗАЙН', icon: '🎭', cost: 1, sphere: 'creative'},
            'gamedev': {name: 'ГЕЙМДЕВ', icon: '🕹️', cost: 2, sphere: 'creative'},
            'medicine': {name: 'МЕДИЦИНА', icon: '🩺', cost: 2, sphere: 'science'},
            'robotics': {name: 'РОБОТОТЕХНИКА', icon: '🤖', cost: 2, sphere: 'science'},
        };

        const spheres = {
            'it': {name: '💻 IT & КОД', desc: 'Программирование и технологии', cls: 'it', profs: ['frontend','backend','mobile','devops','data','security']},
            'biz': {name: '💼 БИЗНЕС', desc: 'Маркетинг, финансы, стартапы', cls: 'biz', profs: ['marketing','finance']},
            'creative': {name: '🎨 ТВОРЧЕСТВО', desc: 'Дизайн, медиа, геймдев', cls: 'creative', profs: ['design','gamedev']},
            'science': {name: '🔬 НАУКА', desc: 'Медицина, робототехника', cls: 'science', profs: ['medicine','robotics']},
        };

        // Mini-game questions per task
        const miniGames = {
            'fe_1': {q: 'Какой тег используется для заголовка первого уровня в HTML?', opts:['<h1>','<header>','<title>','<h>'], ans: 0, explain: 'Правильно! <h1> — это заголовок первого уровня.'},
            'fe_2': {q: 'Какое CSS-свойство делает кнопку круглой?', opts:['border-radius: 50%','shape: circle','round: true','circle: yes'], ans: 0, explain: 'border-radius: 50% делает элемент круглым!'},
            'fe_3': {q: 'Как в JS добавить обработчик клика на кнопку с id="btn"?', opts:['document.getElementById("btn").onclick = fn','btn.click(fn)','onClick(btn, fn)','btn.addEvent(fn)'], ans: 0, explain: 'Верно! .onclick присваивает обработчик события.'},
            'fe_4': {q: 'Что такое адаптивный дизайн?', opts:['Сайт выглядит хорошо на любом экране','Сайт быстро загружается','Сайт с анимацией','Сайт без картинок'], ans: 0, explain: 'Адаптивный (responsive) дизайн — адаптация под разные устройства!'},
            'fe_5': {q: 'Что из этого НЕ является фреймворком JavaScript?', opts:['Laravel','React','Vue','Angular'], ans: 0, explain: 'Laravel — это PHP-фреймворк, не JavaScript!'},
            'be_1': {q: 'Что возвращает "Hello, World!" API endpoint?', opts:['Строку текста','Изображение','Видеофайл','Базу данных'], ans: 0, explain: 'Правильно! REST API возвращает данные, чаще всего текст или JSON.'},
            'be_2': {q: 'Какой метод HTTP используется для получения данных?', opts:['GET','POST','DELETE','PATCH'], ans: 0, explain: 'GET используется для чтения данных с сервера!'},
            'be_3': {q: 'Что такое SQL?', opts:['Язык запросов к базам данных','Язык программирования','Протокол интернета','Операционная система'], ans: 0, explain: 'SQL — Structured Query Language для работы с БД!'},
            'be_4': {q: 'Зачем хешировать пароли?', opts:['Чтобы нельзя было восстановить оригинал','Чтобы пароль был короче','Чтобы пароль стал длиннее','Чтобы ускорить вход'], ans: 0, explain: 'Хеширование делает хранение паролей безопасным!'},
            'be_5': {q: 'Что такое кэширование?', opts:['Временное хранение данных для ускорения','Удаление старых данных','Шифрование данных','Резервное копирование'], ans: 0, explain: 'Кэш хранит часто запрашиваемые данные в быстром доступе!'},
            'mob_1': {q: 'Какой язык используется для разработки под iOS?', opts:['Swift','Kotlin','Java','C#'], ans: 0, explain: 'Swift — основной язык Apple для iOS/macOS разработки!'},
            'mob_2': {q: 'Что такое навигация в мобильном приложении?', opts:['Переход между экранами','Подключение к GPS','Работа с файлами','Отправка уведомлений'], ans: 0, explain: 'Навигация — это система переходов между экранами приложения!'},
            'mob_3': {q: 'Акселерометр в телефоне измеряет:', opts:['Ускорение и наклон устройства','Температуру воздуха','Уровень заряда батареи','Скорость интернета'], ans: 0, explain: 'Акселерометр измеряет физическое ускорение и наклон!'},
            'mob_4': {q: 'Как приложение работает без интернета?', opts:['Хранит данные локально на устройстве','Использует спутниковую связь','Подключается к соседям','Работает только в Wi-Fi зоне'], ans: 0, explain: 'Offline-режим = локальное хранение данных на устройстве!'},
            'mob_5': {q: 'Что нужно для публикации в App Store?', opts:['Аккаунт Apple Developer ($99/год)','Только компьютер Mac','Смартфон iPhone','Регистрация в налоговой'], ans: 0, explain: 'Нужен платный аккаунт Apple Developer!'},
            'do_1': {q: 'Какая команда Linux показывает содержимое папки?', opts:['ls','show','dir','list'], ans: 0, explain: 'ls (list) — стандартная команда для просмотра папки в Linux!'},
            'do_2': {q: 'Docker — это инструмент для:', opts:['Запуска приложений в изолированных контейнерах','Рисования диаграмм','Хранения паролей','Ускорения видеокарты'], ans: 0, explain: 'Docker создаёт контейнеры — изолированные среды для запуска приложений!'},
            'do_3': {q: 'CI/CD означает:', opts:['Continuous Integration/Continuous Deployment','Computer Interface/Computer Design','Code Inspector/Code Debugger','Central Index/Central Database'], ans: 0, explain: 'CI/CD — автоматизация сборки и деплоя кода!'},
            'do_4': {q: 'Kubernetes помогает:', opts:['Управлять множеством контейнеров','Рисовать интерфейсы','Писать CSS','Делать анимации'], ans: 0, explain: 'Kubernetes (K8s) — оркестратор контейнеров для масштабирования!'},
            'do_5': {q: 'Что такое алерт в мониторинге?', opts:['Уведомление при возникновении проблемы','Логотип системы','Тип базы данных','Вид контейнера'], ans: 0, explain: 'Алерт — автоматическое уведомление когда что-то идёт не так!'},
            'ds_1': {q: 'Что такое датасет?', opts:['Набор структурированных данных для анализа','Тип базы данных','Программа для графиков','Язык программирования'], ans: 0, explain: 'Dataset — набор данных, с которым работает Data Scientist!'},
            'ds_2': {q: 'Какой тип графика лучше показывает изменение данных во времени?', opts:['Линейный (line chart)','Круговая диаграмма','Столбчатый','Точечный'], ans: 0, explain: 'Line chart идеально показывает тренды и изменения во времени!'},
            'ds_3': {q: 'Что такое линейная регрессия?', opts:['Предсказание числового значения по данным','Сортировка данных','Фильтрация записей','Удаление дубликатов'], ans: 0, explain: 'Линейная регрессия предсказывает числовое значение (цену, температуру и т.д.)!'},
            'ds_4': {q: 'Нейросеть для классификации кошек и собак — это задача:', opts:['Бинарной классификации','Регрессии','Кластеризации','Ранжирования'], ans: 0, explain: 'Кошка/собака = 2 класса = бинарная классификация!'},
            'ds_5': {q: 'Как называется деградация качества модели ML на реальных данных?', opts:['Model drift (дрейф модели)','Data loss','Model crash','Overfitting'], ans: 0, explain: 'Model drift — модель устаревает т.к. реальные данные меняются!'},
            'sec_1': {q: 'Что сканирует nmap?', opts:['Открытые порты и сервисы хоста','Вирусы на компьютере','Скорость интернета','Пароли пользователей'], ans: 0, explain: 'nmap — сетевой сканер для обнаружения открытых портов и служб!'},
            'sec_2': {q: 'SQL Injection — это атака через:', opts:['Вредоносный SQL-код в поле ввода','Физическое повреждение сервера','Подбор паролей','Перехват Wi-Fi'], ans: 0, explain: 'SQL Injection встраивает вредоносный SQL через формы ввода!'},
            'sec_3': {q: 'XSS (Cross-Site Scripting) внедряет:', opts:['Вредоносный JavaScript в страницу','Вирус в файл','SQL в базу данных','Спам в почту'], ans: 0, explain: 'XSS внедряет JavaScript код в веб-страницу другого пользователя!'},
            'sec_4': {q: 'Reverse Engineering означает:', opts:['Анализ программы без исходного кода','Написание кода наоборот','Восстановление удалённых файлов','Взлом Wi-Fi'], ans: 0, explain: 'Реверс-инжиниринг = изучение программы через её бинарный код!'},
            'sec_5': {q: 'Penetration Testing (пентест) — это:', opts:['Легальная проверка защиты системы на уязвимости','Незаконный взлом','Тест скорости интернета','Проверка паролей'], ans: 0, explain: 'Пентест — это авторизованная симуляция атаки для поиска уязвимостей!'},
            // Marketing
            'mk_1': {q: 'Что такое целевая аудитория?', opts:['Группа людей, которым нужен продукт','Все жители страны','Команда маркетологов','Конкуренты'], ans: 0, explain: 'ЦА — конкретная группа потенциальных покупателей!'},
            'mk_2': {q: 'CTR (Click-Through Rate) — это:', opts:['Процент кликов от числа показов','Цена за клик','Число просмотров рекламы','Бюджет кампании'], ans: 0, explain: 'CTR = клики / показы × 100%. Показывает эффективность рекламы!'},
            'mk_3': {q: 'SMM — это маркетинг в:', opts:['Социальных сетях','Телевизоре','Газетах','Радио'], ans: 0, explain: 'SMM (Social Media Marketing) — продвижение через соцсети!'},
            // Finance
            'fin_1': {q: 'Что такое ликвидность актива?', opts:['Скорость превращения в деньги','Цена актива','Доходность актива','Риск потерь'], ans: 0, explain: 'Ликвидность = насколько быстро можно продать актив по рыночной цене!'},
            'fin_2': {q: 'Диверсификация портфеля означает:', opts:['Распределение денег между разными активами','Вложение всего в один актив','Продажу акций','Хранение в банке'], ans: 0, explain: 'Не клади все яйца в одну корзину — принцип диверсификации!'},
            // Design
            'des_1': {q: 'RGB — это модель:', opts:['Цветовая (Красный, Зелёный, Синий)','Размерная','Шрифтовая','Сеточная'], ans: 0, explain: 'RGB — аддитивная цветовая модель для экранов!'},
            'des_2': {q: 'Что такое UX Design?', opts:['Дизайн пользовательского опыта','Дизайн логотипов','3D моделирование','Анимация'], ans: 0, explain: 'UX (User Experience) — как пользователь чувствует себя при работе с продуктом!'},
            // Gamedev
            'gd_1': {q: 'Unity — это:', opts:['Движок для создания игр','Язык программирования','Графический редактор','Звуковой редактор'], ans: 0, explain: 'Unity — один из самых популярных игровых движков!'},
            'gd_2': {q: 'Что такое спрайт в геймдеве?', opts:['2D изображение персонажа или объекта','3D модель','Звуковой эффект','Код скрипта'], ans: 0, explain: 'Спрайт — 2D графический объект, используемый в играх!'},
            // Medicine
            'med_1': {q: 'ЭКГ показывает работу:', opts:['Сердца','Мозга','Лёгких','Почек'], ans: 0, explain: 'ЭКГ (электрокардиограмма) фиксирует электрическую активность сердца!'},
            'med_2': {q: 'Антибиотики лечат инфекции вызванные:', opts:['Бактериями','Вирусами','Грибками','Паразитами'], ans: 0, explain: 'Антибиотики эффективны против бактерий, но не вирусов!'},
            // Robotics
            'rob_1': {q: 'Какой язык чаще используется в робототехнике?', opts:['Python','HTML','CSS','SQL'], ans: 0, explain: 'Python — популярный язык для ROS и управления роботами!'},
            'rob_2': {q: 'Сервопривод в роботе управляет:', opts:['Точным движением суставов','Зрением робота','Речью робота','Зарядкой батареи'], ans: 0, explain: 'Сервоприводы обеспечивают точные угловые перемещения — "суставы" робота!'},
        };
        
        document.querySelectorAll('.hero-slot').forEach(el => {
            el.onclick = function() {
                document.querySelectorAll('.hero-slot').forEach(h => h.classList.remove('selected'));
                this.classList.add('selected');
                sel = this.dataset.avatar;
                document.getElementById('gameHero').src = '/hero' + this.dataset.slot + '.png';
                checkCreate();
            };
        });
        
        function chg(s, d) {
            let used = Object.values(stats).reduce((a,b)=>a+b,0);
            let left = MAX - used;
            if (d>0 && left<=0) return;
            if (d<0 && stats[s]<=MIN) return;
            stats[s] += d;
            document.getElementById(s).textContent = stats[s];
            updatePoints();
            checkCreate();
        }
        
        function updatePoints() {
            let used = Object.values(stats).reduce((a,b)=>a+b,0);
            document.getElementById('pts').textContent = MAX - used;
        }
        
        function checkCreate() {
            let name = document.getElementById('charName').value.trim();
            let used = Object.values(stats).reduce((a,b)=>a+b,0);
            document.getElementById('startBtn').disabled = !(name && sel && used==MAX);
        }
        
        document.getElementById('charName').oninput = checkCreate;
        
        async function create() {
            let name = document.getElementById('charName').value.trim();
            await fetch('/api/character', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({
                    user_id: uid, name: name, avatar: sel,
                    strength: stats.str, intelligence: stats.int,
                    charisma: stats.cha, luck: stats.lck
                })
            });
            showScreen('gameScreen');
            loadGame();
        }
        
        async function loadGame() {
            let r = await fetch(`/api/state?user_id=${uid}`);
            let d = await r.json();
            state = d.user;
            hero = d.character;
            unlockedProfs = d.professions || {};
            completedTasks = d.completed_tasks || [];
            
            document.getElementById('displayName').textContent = hero.name.toUpperCase();
            document.getElementById('statStr').textContent = hero.strength;
            document.getElementById('statInt').textContent = hero.intelligence;
            document.getElementById('statCha').textContent = hero.charisma;
            document.getElementById('statLck').textContent = hero.luck;
            
            updateUI();
            
            if (d.full_recovery) showRecovery();
            setInterval(checkAfk, 2000);
        }
        
        function updateUI() {
            document.getElementById('displayCoins').textContent = state.coins || 0;
            document.getElementById('displayTokens').textContent = state.tokens || 0;
            document.getElementById('displayEnergy').textContent = state.energy || 0;
            document.getElementById('displayLevel').textContent = state.level || 1;
            
            let xpForNext = state.level === 1 ? 50 : 50 + (state.level - 1) * 100;
            let currentBase = state.level === 1 ? 0 : 50 + (state.level - 2) * 100;
            let xpPercent = Math.min(100, ((state.xp - currentBase) / (xpForNext - currentBase)) * 100);
            document.getElementById('xpBar').style.width = xpPercent + '%';
            
            document.getElementById('energyBar').style.width = (state.energy || 0) + '%';
            
            if ((state.tokens || 0) > 0) {
                document.getElementById('profBtn').classList.add('new');
            }
            
            if (state.level >= 2 && !professionsUnlockedShown) {
                professionsUnlockedShown = true;
                document.getElementById('unlockModal').classList.add('show');
            }
        }
        
        function showRecovery() {
            document.getElementById('recoveryStatus').classList.add('show');
            setTimeout(() => document.getElementById('recoveryStatus').classList.remove('show'), 3000);
            showToast('⚡ Энергия восстановлена!');
        }
        
        function showToast(msg) {
            const t = document.getElementById('toast');
            t.textContent = msg;
            t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 2000);
        }
        
        async function checkAfk() {
            let r = await fetch(`/api/state?user_id=${uid}`);
            let d = await r.json();
            
            if (d.user.energy !== state.energy) {
                state.energy = d.user.energy;
                document.getElementById('displayEnergy').textContent = state.energy;
                document.getElementById('energyBar').style.width = state.energy + '%';
            }
            
            if (d.full_recovery) showRecovery();
        }
        
        const heroContainer = document.getElementById('heroContainer');
        heroContainer.addEventListener('touchstart', handleTouch, {passive: false});
        heroContainer.addEventListener('click', handleClick);
        
        function handleTouch(e) {
            e.preventDefault();
            for (let touch of e.touches) {
                processTap(touch.clientX, touch.clientY, e.touches.length);
            }
        }
        
        function handleClick(e) {
            processTap(e.clientX, e.clientY, 1);
        }
        
        async function processTap(x, y, fingers) {
            if (isProcessing || state.energy < fingers) return;
            
            const now = Date.now();
            if (now - lastTapTime < 60) return;
            
            isProcessing = true;
            lastTapTime = now;
            tapPattern.push(now);
            if (tapPattern.length > 10) tapPattern.shift();
            
            const rect = heroContainer.getBoundingClientRect();
            const floatEl = document.createElement('div');
            floatEl.className = 'floating-reward';
            floatEl.textContent = '+' + fingers;
            floatEl.style.left = (x - rect.left) + 'px';
            floatEl.style.top = (y - rect.top) + 'px';
            floatEl.style.position = 'absolute';
            heroContainer.appendChild(floatEl);
            setTimeout(() => floatEl.remove(), 800);
            
            let r = await fetch('/api/tap', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({
                    user_id: uid, timestamp: now, pattern: tapPattern, fingers: fingers
                })
            });
            
            let res = await r.json();
            if (res.success) {
                state = {...state, ...res};
                updateUI();
                if (res.professions_unlocked) {
                    document.getElementById('unlockModal').classList.add('show');
                }
            }
            
            isProcessing = false;
        }
        
        function showScreen(id) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('show'));
            document.getElementById(id).classList.add('show');
        }
        
        function backToGame() {
            showScreen('gameScreen');
            updateUI();
        }
        
        function goToProfessions() {
            document.getElementById('unlockModal').classList.remove('show');
            openProfessions();
        }
        
        let currentSphere = null;
        let profBackMode = 'game'; // 'game' or 'spheres'

        function profBackAction() {
            if (profBackMode === 'spheres') {
                openProfessions();
            } else {
                backToGame();
            }
        }

        async function openProfessions() {
            currentSphere = null;
            profBackMode = 'game';
            showScreen('professionsScreen');
            document.getElementById('profScreenTokens').textContent = state.tokens || 0;
            document.getElementById('profScreenTitle').textContent = '◆ СФЕРЫ ПРОФЕССИЙ ◆';
            document.getElementById('profScreenSubtitle').textContent = 'Выбери сферу для изучения';
            document.getElementById('profBackBtn').textContent = '◀ НАЗАД';

            const sphereGrid = document.getElementById('sphereGrid');
            const profsGrid = document.getElementById('professionsGrid');
            sphereGrid.classList.remove('hidden');
            profsGrid.classList.add('hidden');
            sphereGrid.innerHTML = '';

            for (let [key, s] of Object.entries(spheres)) {
                const card = document.createElement('div');
                card.className = 'sphere-card ' + s.cls;
                const unlockedInSphere = s.profs.filter(p => p in unlockedProfs).length;
                card.innerHTML = `
                    <div class="sphere-icon">${s.name.split(' ')[0]}</div>
                    <div class="sphere-name">${s.name.substring(s.name.indexOf(' ')+1)}</div>
                    <div class="sphere-count">${s.desc}</div>
                    <div class="sphere-count" style="color:var(--success)">${unlockedInSphere}/${s.profs.length} открыто</div>
                `;
                card.onclick = () => openSphere(key);
                sphereGrid.appendChild(card);
            }
        }

        function openSphere(sphereKey) {
            currentSphere = sphereKey;
            profBackMode = 'spheres';
            const s = spheres[sphereKey];
            document.getElementById('profScreenTitle').textContent = s.name;
            document.getElementById('profScreenSubtitle').textContent = s.desc;
            document.getElementById('profBackBtn').textContent = '◀ К СФЕРАМ';

            const sphereGrid = document.getElementById('sphereGrid');
            const grid = document.getElementById('professionsGrid');
            sphereGrid.classList.add('hidden');
            grid.classList.remove('hidden');
            grid.innerHTML = '';

            for (let key of s.profs) {
                const data = professionsData[key];
                if (!data) continue;
                const isUnlocked = key in unlockedProfs;
                const canAfford = (state.tokens || 0) >= data.cost;

                const card = document.createElement('div');
                card.className = 'profession-card pixel-box ' + (isUnlocked ? 'unlocked' : canAfford ? 'available' : 'locked');
                card.innerHTML = `
                    <div class="prof-icon">${data.icon}</div>
                    <div class="prof-name">${data.name}</div>
                    <div class="prof-cost">${isUnlocked ? '✓ ОТКРЫТО' : '🔷 ' + data.cost}</div>
                `;
                if (isUnlocked || canAfford) {
                    card.onclick = () => openGuide(key);
                }
                grid.appendChild(card);
            }
        }
        
        async function openGuide(profKey) {
            currentGuideProf = profKey;
            const r = await fetch(`/api/profession_data?prof_key=${profKey}`);
            const d = await r.json();
            
            if (!d.success) return;
            
            const data = d.data;
            const isUnlocked = profKey in unlockedProfs;
            
            document.getElementById('guideTitle').textContent = data.name;
            document.getElementById('guideDesc').textContent = data.description;
            document.getElementById('guideActivity').textContent = data.guide;
            
            const toolsContainer = document.getElementById('guideTools');
            toolsContainer.innerHTML = '';
            data.tools.forEach(tool => {
                const tag = document.createElement('span');
                tag.className = 'tool-tag';
                tag.textContent = tool;
                toolsContainer.appendChild(tag);
            });
            
            const btn = document.getElementById('guideActionBtn');
            if (isUnlocked) {
                btn.textContent = '▶ К ЗАДАНИЯМ';
                btn.onclick = () => {
                    closeGuide();
                    openProfessionTasks(profKey);
                };
            } else {
                btn.textContent = `ОТКРЫТЬ ЗА ${data.cost} ТОКЕНОВ`;
                btn.onclick = unlockProfession;
            }
            
            document.getElementById('guideModal').classList.add('show');
        }
        
        function closeGuide() {
            document.getElementById('guideModal').classList.remove('show');
        }
        
        async function unlockProfession() {
            if (!currentGuideProf) return;
            
            const r = await fetch('/api/unlock_profession', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({user_id: uid, prof_key: currentGuideProf})
            });
            
            const d = await r.json();
            if (d.success) {
                state.tokens = d.tokens;
                unlockedProfs[currentGuideProf] = true;
                showToast('✓ Профессия открыта!');
                closeGuide();
                openProfessions();
            } else {
                showToast('✗ ' + d.message);
            }
        }
        
        async function openTasks() {
            showScreen('tasksScreen');
            const list = document.getElementById('tasksList');
            list.innerHTML = '';
            
            const unlocked = Object.keys(unlockedProfs);
            if (unlocked.length === 0) {
                list.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">Сначала открой профессию в разделе ПРОФЕССИИ</div>';
                return;
            }
            
            document.getElementById('tasksSubtitle').textContent = 'Выбери профессию для просмотра заданий';
            
            unlocked.forEach(profKey => {
                const data = professionsData[profKey];
                const card = document.createElement('div');
                card.className = 'task-card pixel-box';
                card.innerHTML = `
                    <div class="task-header">
                        <span class="task-title">${data.icon} ${data.name}</span>
                    </div>
                    <div class="task-desc">Нажми чтобы увидеть задания</div>
                `;
                card.onclick = () => openProfessionTasks(profKey);
                list.appendChild(card);
            });
        }
        
        async function openProfessionTasks(profKey) {
            currentTaskProf = profKey;
            document.getElementById('tasksSubtitle').textContent = professionsData[profKey].name;
            const list = document.getElementById('tasksList');
            list.innerHTML = '';
            
            const r = await fetch(`/api/profession_tasks?prof_key=${profKey}&user_id=${uid}`);
            const d = await r.json();
            
            if (!d.success) return;
            
            let prevCompleted = true;
            
            d.tasks.forEach((task, idx) => {
                const isCompleted = task.completed;
                const isLocked = !prevCompleted;
                
                const card = document.createElement('div');
                card.className = 'task-card pixel-box ' + (isCompleted ? 'completed' : isLocked ? 'locked' : '');
                
                let statusIcon = isCompleted ? '✓' : isLocked ? '🔒' : '▶';
                let diffColor = task.difficulty === 1 ? '#4ecdc4' : task.difficulty === 2 ? '#ffe66d' : task.difficulty === 3 ? '#ff6b6b' : task.difficulty === 4 ? '#9b59b6' : '#e74c3c';
                
                card.innerHTML = `
                    <div class="task-header">
                        <span class="task-title">${statusIcon} ${task.title}</span>
                        <span class="task-difficulty" style="background: ${diffColor}">★${task.difficulty}</span>
                    </div>
                    <div class="task-desc">${task.description}</div>
                    <div class="task-reward">
                        <span>🪙 ${task.reward_coins}</span>
                        <span>✨ ${task.reward_xp} XP</span>
                    </div>
                `;
                
                if (!isCompleted && !isLocked) {
                    card.onclick = () => completeTask(task.id, task.title, task.reward_coins, task.reward_xp);
                }
                
                list.appendChild(card);
                
                if (!isCompleted) prevCompleted = false;
            });
        }
        
        let currentMinigameTaskId = null;
        let minigameAnswered = false;

        function openMinigame(taskId, taskTitle, rewardCoins, rewardXp) {
            currentMinigameTaskId = taskId;
            minigameAnswered = false;
            const mg = miniGames[taskId];

            document.getElementById('mgTaskName').textContent = taskTitle;
            document.getElementById('mgFeedback').textContent = '';
            document.getElementById('mgFeedback').className = 'mg-feedback';
            document.getElementById('mgReward').textContent = '';
            document.getElementById('mgCloseBtn').textContent = '✕ ЗАКРЫТЬ';

            if (!mg) {
                document.getElementById('mgQuestion').textContent = 'Подтверди выполнение задания чтобы получить награду!';
                const optsDiv = document.getElementById('mgOptions');
                optsDiv.innerHTML = '';
                const btn = document.createElement('button');
                btn.className = 'mg-option';
                btn.textContent = '✓ Задание выполнено!';
                btn.onclick = () => submitTaskComplete(rewardCoins, rewardXp);
                optsDiv.appendChild(btn);
            } else {
                document.getElementById('mgQuestion').textContent = mg.q;
                const optsDiv = document.getElementById('mgOptions');
                optsDiv.innerHTML = '';
                mg.opts.forEach((opt, idx) => {
                    const btn = document.createElement('button');
                    btn.className = 'mg-option';
                    btn.textContent = opt;
                    btn.onclick = () => checkAnswer(idx, mg.ans, mg.explain, rewardCoins, rewardXp, optsDiv);
                    optsDiv.appendChild(btn);
                });
            }

            document.getElementById('minigameModal').classList.add('show');
        }

        async function checkAnswer(chosen, correct, explain, rewardCoins, rewardXp, optsDiv) {
            if (minigameAnswered) return;
            minigameAnswered = true;
            const btns = optsDiv.querySelectorAll('.mg-option');
            btns.forEach(b => b.style.pointerEvents = 'none');
            btns[chosen].classList.add(chosen === correct ? 'correct' : 'wrong');
            if (chosen !== correct) btns[correct].classList.add('correct');

            const fb = document.getElementById('mgFeedback');
            if (chosen === correct) {
                fb.textContent = '✓ ' + explain;
                fb.className = 'mg-feedback ok';
                await submitTaskComplete(rewardCoins, rewardXp);
            } else {
                fb.textContent = '✗ Неверно! ' + explain;
                fb.className = 'mg-feedback fail';
                document.getElementById('mgCloseBtn').textContent = '↺ ПОПРОБОВАТЬ СНОВА';
                document.getElementById('mgCloseBtn').onclick = () => {
                    closeMinigame();
                    openProfessionTasks(currentTaskProf);
                };
            }
        }

        async function submitTaskComplete(rewardCoins, rewardXp) {
            if (!currentTaskProf || !currentMinigameTaskId) return;
            const r = await fetch('/api/complete_task', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({user_id: uid, task_id: currentMinigameTaskId, prof_key: currentTaskProf})
            });
            const d = await r.json();
            if (d.success) {
                state.coins = d.coins; state.xp = d.xp;
                state.level = d.level; state.tokens = d.tokens;
                document.getElementById('mgReward').textContent = `+${rewardCoins} 🪙  +${rewardXp} XP` + (d.level_up ? `  🎉 LVL ${d.level}!` : '');
                document.getElementById('mgCloseBtn').textContent = '✓ ЗАБРАТЬ НАГРАДУ';
                document.getElementById('mgCloseBtn').onclick = () => { closeMinigame(); openProfessionTasks(currentTaskProf); updateUI(); };
                updateUI();
            }
        }

        function closeMinigame() {
            document.getElementById('minigameModal').classList.remove('show');
            document.getElementById('mgCloseBtn').onclick = closeMinigame;
        }

        async function completeTask(taskId, taskTitle, rewardCoins, rewardXp) {
            if (!currentTaskProf) return;
            openMinigame(taskId, taskTitle, rewardCoins, rewardXp);
        }
        
        async function init() {
            let r = await fetch(`/api/state?user_id=${uid}`);
            let d = await r.json();
            
            if(d.character) {
                showScreen('gameScreen');
                loadGame();
            } else {
                updatePoints();
            }
        }
        
        init();
    </script>
</body>
</html>'''

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_TEMPLATE

@app.get("/hero1.png")
async def hero1():
    return FileResponse("hero1.png")

@app.get("/hero2.png")
async def hero2():
    return FileResponse("hero2.png")

@app.get("/hero3.png")
async def hero3():
    return FileResponse("hero3.png")
