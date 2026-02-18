import os
import time
import random
import json
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
        {
            'id': 'fe_1',
            'title': 'Первый HTML',
            'description': 'Создай простую страницу с заголовком и параграфом. Это основа всего веба.',
            'difficulty': 1,
            'reward_coins': 100,
            'reward_xp': 20,
            'check': 'html_basics'
        },
        {
            'id': 'fe_2',
            'title': 'CSS стили',
            'description': 'Сделай кнопку красной и круглой. Научись менять внешний вид элементов.',
            'difficulty': 2,
            'reward_coins': 150,
            'reward_xp': 30,
            'check': 'css_styling'
        },
        {
            'id': 'fe_3',
            'title': 'JavaScript интерактив',
            'description': 'Сделай так, чтобы при клике на кнопку менялся текст. Первая интерактивность!',
            'difficulty': 3,
            'reward_coins': 250,
            'reward_xp': 50,
            'check': 'js_click'
        },
        {
            'id': 'fe_4',
            'title': 'Адаптивный дизайн',
            'description': 'Сделай страницу, которая красиво выглядит и на телефоне, и на компьютере.',
            'difficulty': 4,
            'reward_coins': 400,
            'reward_xp': 80,
            'check': 'responsive'
        },
        {
            'id': 'fe_5',
            'title': 'Мини-приложение',
            'description': 'Создай калькулятор или todo-лист. Полноценное приложение с логикой.',
            'difficulty': 5,
            'reward_coins': 800,
            'reward_xp': 150,
            'check': 'mini_app'
        }
    ],
    'backend': [
        {
            'id': 'be_1',
            'title': 'Первая API',
            'description': 'Создай endpoint, который возвращает "Hello, World!"',
            'difficulty': 1,
            'reward_coins': 100,
            'reward_xp': 20,
            'check': 'api_hello'
        },
        {
            'id': 'be_2',
            'title': 'Работа с данными',
            'description': 'Сделай API, которое принимает имя и возвращает персонализированное приветствие.',
            'difficulty': 2,
            'reward_coins': 150,
            'reward_xp': 30,
            'check': 'api_data'
        },
        {
            'id': 'be_3',
            'title': 'База данных',
            'description': 'Подключи базу данных и сделай CRUD операции (создание, чтение, обновление, удаление).',
            'difficulty': 3,
            'reward_coins': 300,
            'reward_xp': 60,
            'check': 'database_crud'
        },
        {
            'id': 'be_4',
            'title': 'Аутентификация',
            'description': 'Реализуй регистрацию и вход пользователей с хешированием паролей.',
            'difficulty': 4,
            'reward_coins': 500,
            'reward_xp': 100,
            'check': 'auth'
        },
        {
            'id': 'be_5',
            'title': 'Масштабирование',
            'description': 'Оптимизируй запросы и добавь кэширование для высокой нагрузки.',
            'difficulty': 5,
            'reward_coins': 1000,
            'reward_xp': 200,
            'check': 'scaling'
        }
    ],
    'mobile': [
        {
            'id': 'mob_1',
            'title': 'Hello Mobile',
            'description': 'Создай первое приложение с одним экраном и текстом.',
            'difficulty': 1,
            'reward_coins': 100,
            'reward_xp': 20,
            'check': 'hello_mobile'
        },
        {
            'id': 'mob_2',
            'title': 'Навигация',
            'description': 'Сделай переход между двумя экранами с кнопкой "Назад".',
            'difficulty': 2,
            'reward_coins': 180,
            'reward_xp': 35,
            'check': 'navigation'
        },
        {
            'id': 'mob_3',
            'title': 'Сенсоры',
            'description': 'Используй акселерометр или камеру в приложении.',
            'difficulty': 3,
            'reward_coins': 350,
            'reward_xp': 70,
            'check': 'sensors'
        },
        {
            'id': 'mob_4',
            'title': 'Офлайн-режим',
            'description': 'Сделай так, чтобы приложение работало без интернета и синхронизировалось.',
            'difficulty': 4,
            'reward_coins': 600,
            'reward_xp': 120,
            'check': 'offline'
        },
        {
            'id': 'mob_5',
            'title': 'Публикация',
            'description': 'Подготовь приложение к публикации в App Store или Google Play.',
            'difficulty': 5,
            'reward_coins': 1200,
            'reward_xp': 250,
            'check': 'publish'
        }
    ],
    'devops': [
        {
            'id': 'do_1',
            'title': 'Linux basics',
            'description': 'Освой базовые команды Linux: навигация, файлы, права доступа.',
            'difficulty': 1,
            'reward_coins': 150,
            'reward_xp': 30,
            'check': 'linux_basic'
        },
        {
            'id': 'do_2',
            'title': 'Docker контейнер',
            'description': 'Запусти приложение в Docker-контейнере.',
            'difficulty': 2,
            'reward_coins': 250,
            'reward_xp': 50,
            'check': 'docker_run'
        },
        {
            'id': 'do_3',
            'title': 'CI/CD Pipeline',
            'description': 'Настрой автоматическую сборку и деплой при пуше в git.',
            'difficulty': 3,
            'reward_coins': 500,
            'reward_xp': 100,
            'check': 'cicd'
        },
        {
            'id': 'do_4',
            'title': 'Kubernetes',
            'description': 'Разверни приложение в Kubernetes кластере.',
            'difficulty': 4,
            'reward_coins': 900,
            'reward_xp': 180,
            'check': 'k8s'
        },
        {
            'id': 'do_5',
            'title': 'Мониторинг',
            'description': 'Настрой логирование, метрики и алерты для системы.',
            'difficulty': 5,
            'reward_coins': 1500,
            'reward_xp': 300,
            'check': 'monitoring'
        }
    ],
    'data': [
        {
            'id': 'ds_1',
            'title': 'Первый датасет',
            'description': 'Загрузи данные и выведи базовую статистику.',
            'difficulty': 1,
            'reward_coins': 150,
            'reward_xp': 30,
            'check': 'dataset_load'
        },
        {
            'id': 'ds_2',
            'title': 'Визуализация',
            'description': 'Построй графики и диаграммы для данных.',
            'difficulty': 2,
            'reward_coins': 250,
            'reward_xp': 50,
            'check': 'visualization'
        },
        {
            'id': 'ds_3',
            'title': 'Предсказание',
            'description': 'Обучи простую модель линейной регрессии.',
            'difficulty': 3,
            'reward_coins': 500,
            'reward_xp': 100,
            'check': 'prediction'
        },
        {
            'id': 'ds_4',
            'title': 'Нейросеть',
            'description': 'Создай и обучи нейросеть для классификации.',
            'difficulty': 4,
            'reward_coins': 1000,
            'reward_xp': 200,
            'check': 'neural_net'
        },
        {
            'id': 'ds_5',
            'title': 'Production ML',
            'description': 'Разверни модель как API сервис с мониторингом качества.',
            'difficulty': 5,
            'reward_coins': 2000,
            'reward_xp': 400,
            'check': 'ml_prod'
        }
    ],
    'security': [
        {
            'id': 'sec_1',
            'title': 'Сканирование',
            'description': 'Просканируй сайт на открытые порты и версии ПО.',
            'difficulty': 1,
            'reward_coins': 150,
            'reward_xp': 30,
            'check': 'scanning'
        },
        {
            'id': 'sec_2',
            'title': 'SQL Injection',
            'description': 'Найди и исправь уязвимость SQL-инъекции.',
            'difficulty': 2,
            'reward_coins': 300,
            'reward_xp': 60,
            'check': 'sql_inject'
        },
        {
            'id': 'sec_3',
            'title': 'XSS атака',
            'description': 'Продемонстрируй и защити от XSS-уязвимости.',
            'difficulty': 3,
            'reward_coins': 600,
            'reward_xp': 120,
            'check': 'xss'
        },
        {
            'id': 'sec_4',
            'title': 'Reverse Engineering',
            'description': 'Проанализируй бинарный файл и найди скрытую функцию.',
            'difficulty': 4,
            'reward_coins': 1200,
            'reward_xp': 250,
            'check': 'reverse'
        },
        {
            'id': 'sec_5',
            'title': 'Red Team',
            'description': 'Проведи полноценный тест на проникновение системы.',
            'difficulty': 5,
            'reward_coins': 2500,
            'reward_xp': 500,
            'check': 'redteam'
        }
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
    
    # Отмечаем выполненные
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
    
    # Проверяем не открыта ли уже
    existing = get_professions(user_id)
    if prof_key in existing:
        return {'success': False, 'message': 'Already unlocked'}
    
    # Списываем токены и открываем
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
    
    # Находим задание
    if prof_key not in TASKS_DATA:
        return {'success': False, 'message': 'Profession not found'}
    
    task = None
    for t in TASKS_DATA[prof_key]:
        if t['id'] == task_id:
            task = t
            break
    
    if not task:
        return {'success': False, 'message': 'Task not found'}
    
    # Проверяем не выполнено ли уже
    completed = get_tasks(user_id)
    if task_id in completed:
        return {'success': False, 'message': 'Already completed'}
    
    # Выдаём награду
    user['coins'] += task['reward_coins']
    user['xp'] += task['reward_xp']
    
    # Проверяем повышение уровня
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

# === Главная страница ===

@app.get("/", response_class=HTMLResponse)
async def root():
    return """<!DOCTYPE html>
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
        
        /* ЭКРАНЫ */
        .screen {
            display: none;
            flex-direction: column;
            height: 100%;
            gap: 10px;
        }
        .screen.show {
            display: flex;
        }
        
        /* БОКОВЫЕ КНОПКИ */
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
        
        /* СОЗДАНИЕ */
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
        
        /* ИГРОВОЙ ЭКРАН */
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
        
        /* ПРОФЕССИИ */
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
        
        /* ГАЙД ПРОФЕССИИ */
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
        
        /* ЗАДАНИЯ */
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
        }
        
        .task-card:hover:not(.completed) {
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
        
        .task-status {
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 20px;
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
        
        /* МОДАЛЬНЫЕ ОКНА */
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
        
        /* УВЕДОМЛЕНИЯ */
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
    </style>
</head>
<body>
    <!-- Уведомления -->
    <div class="toast" id="toast"></div>
    
    <!-- Модальное окно открытия профессий -->
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
    
    <!-- Гайд профессии -->
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

    <!-- СОЗДАНИЕ ПЕРСОНАЖА -->
    <div class="container screen show" id="createScreen">
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
    
    <!-- ИГРОВОЙ ЭКРАН -->
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
    
    <!-- ЭКРАН ПРОФЕССИЙ -->
    <div class="container screen" id="professionsScreen">
        <div class="pixel-box" style="padding: 15px; text-align: center;">
            <h2 style="font-size: 12px; color: var(--token);">◆ ИССЛЕДОВАНИЕ ПРОФЕССИЙ ◆</h2>
            <div style="margin-top: 10px; font-size: 10px; color: var(--token);">
                🔷 ТОКЕНОВ: <span id="profScreenTokens">0</span>
            </div>
        </div>
        
        <div class="professions-grid" id="professionsGrid"></div>
        
        <button class="back-btn" onclick="backToGame()">◀ НАЗАД</button>
    </div>
    
    <!-- ЭКРАН ЗАДАНИЙ -->
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
        
        const professionsData = {
            'frontend': {name: 'FRONTEND DEV', icon: '🎨', cost: 1},
            'backend': {name: 'BACKEND DEV', icon: '⚙️', cost: 1},
            'mobile': {name: 'MOBILE DEV', icon: '📱', cost: 1},
            'devops': {name: 'DEVOPS', icon: '🚀', cost: 2},
            'data': {name: 'DATA SCIENCE', icon: '📊', cost: 2},
            'security': {name: 'SECURITY', icon: '🔒', cost: 2}
        };
        
        // Инициализация создания персонажа
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
            
            // XP
            let xpForNext = state.level === 1 ? 50 : 50 + (state.level - 1) * 100;
            let currentBase = state.level === 1 ? 0 : 50 + (state.level - 2) * 100;
            let xpPercent = Math.min(100, ((state.xp - currentBase) / (xpForNext - currentBase)) * 100);
            document.getElementById('xpBar').style.width = xpPercent + '%';
            
            // Energy
            document.getElementById('energyBar').style.width = (state.energy || 0) + '%';
            
            // Side buttons highlight
            if ((state.tokens || 0) > 0) {
                document.getElementById('profBtn').classList.add('new');
            }
            
            // Check professions unlock
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
        
        // TAP SYSTEM
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
            
            // Visual
            const floatEl = document.createElement('div');
            floatEl.className = 'floating-reward';
            floatEl.textContent = '+' + fingers;
            floatEl.style.left = (x - heroContainer.getBoundingClientRect().left) + 'px';
            floatEl.style.top = (y - heroContainer.getBoundingClientRect().top - 40) + 'px';
            heroContainer.appendChild(floatEl);
            setTimeout(() => floatEl.remove(), 800);
            
            // API
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
        
        // NAVIGATION
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
        
        // PROFESSIONS
        async function openProfessions() {
            showScreen('professionsScreen');
            document.getElementById('profScreenTokens').textContent = state.tokens || 0;
            
            const grid = document.getElementById('professionsGrid');
            grid.innerHTML = '';
            
            for (let [key, data] of Object.entries(professionsData)) {
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
        
        // TASKS
        async function openTasks() {
            showScreen('tasksScreen');
            // Показываем список открытых профессий для выбора
            const list = document.getElementById('tasksList');
            list.innerHTML = '';
            
            const unlocked = Object.keys(unlockedProfs);
            if (unlocked.length === 0) {
                list.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">Сначала открой профессию в разделе ПРОФЕССИИ</div>';
                return;
            }
            
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
                card.style.position = 'relative';
                
                card.innerHTML = `
                    <div class="task
