import os
import time
import random
import threading
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from database import init_db, get_user, save_user, get_character, save_character, get_professions, unlock_profession, get_tasks, complete_task

app = FastAPI()

init_db()

# Данные профессий и заданий с практикой (мини-играми)
PROFESSIONS_DATA = {
    'frontend': {
        'name': 'FRONTEND DEVELOPER',
        'icon': '🎨',
        'description': 'Создание визуальной части веб-приложений',
        'guide': 'Frontend-разработчик отвечает за то, что видит пользователь. Он превращает дизайн в работающий код, делает кнопки кликабельными, анимации плавными, а интерфейс удобным.',
        'tools': ['HTML', 'CSS', 'JavaScript', 'React'],
        'cost': 1,
        'sphere': 'tech'
    },
    'backend': {
        'name': 'BACKEND DEVELOPER',
        'icon': '⚙️',
        'description': 'Серверная логика и базы данных',
        'guide': 'Backend-разработчик строит "мозг" приложения. Он создаёт API, работает с базами данных, обеспечивает безопасность и производительность.',
        'tools': ['Python', 'SQL', 'API', 'Docker'],
        'cost': 1,
        'sphere': 'tech'
    },
    'mobile': {
        'name': 'MOBILE DEVELOPER',
        'icon': '📱',
        'description': 'Приложения для iOS и Android',
        'guide': 'Mobile-разработчик создаёт приложения для смартфонов. Он должен учитывать особенности touch-интерфейса, ограничения батареи и разные размеры экранов.',
        'tools': ['Swift', 'Kotlin', 'Flutter', 'Firebase'],
        'cost': 1,
        'sphere': 'tech'
    },
    'devops': {
        'name': 'DEVOPS ENGINEER',
        'icon': '🚀',
        'description': 'Автоматизация и инфраструктура',
        'guide': 'DevOps-инженер делает так, чтобы код быстро и надёжно попадал на сервера. Он автоматизирует рутину, следит за стабильностью систем.',
        'tools': ['Linux', 'Docker', 'Kubernetes', 'CI/CD'],
        'cost': 2,
        'sphere': 'tech'
    },
    'data': {
        'name': 'DATA SCIENTIST',
        'icon': '📊',
        'description': 'Анализ данных и машинное обучение',
        'guide': 'Data Scientist находит закономерности в данных, строит прогнозы и обучает нейросети. Это математика + программирование + бизнес-понимание.',
        'tools': ['Python', 'Pandas', 'ML', 'Statistics'],
        'cost': 2,
        'sphere': 'tech'
    },
    'security': {
        'name': 'SECURITY SPECIALIST',
        'icon': '🔒',
        'description': 'Кибербезопасность и защита',
        'guide': 'Специалист по безопасности ищет уязвимости до того, как их найдут злоумышленники. Он мыслит как хакер, чтобы защитить системы.',
        'tools': ['Penetration Testing', 'Cryptography', 'Networking', 'Linux'],
        'cost': 2,
        'sphere': 'tech'
    }
}

# Задания с практикой (мини-играми) для IT-сферы - от лёгкого к сложному
TASKS_DATA = {
    'frontend': [
        {
            'id': 'fe_1',
            'title': 'HTML Builder',
            'description': 'Собери структуру HTML страницы из блоков. Правильный порядок: html → head → body.',
            'difficulty': 1,
            'reward_coins': 150,
            'reward_xp': 30,
            'practice_type': 'html_puzzle',
            'practice_desc': 'Перетащи блоки в правильном порядке'
        },
        {
            'id': 'fe_2',
            'title': 'CSS Color Master',
            'description': 'Подбери правильный цвет для элемента. Используй цветовой круг для гармонии.',
            'difficulty': 2,
            'reward_coins': 250,
            'reward_xp': 50,
            'practice_type': 'color_match',
            'practice_desc': 'Выбери цвет, гармонирующий с образцом'
        },
        {
            'id': 'fe_3',
            'title': 'Flexbox Defense',
            'description': 'Расположи элементы с помощью CSS Flexbox. Защити базу от атаки!',
            'difficulty': 3,
            'reward_coins': 400,
            'reward_xp': 80,
            'practice_type': 'flexbox_defense',
            'practice_desc': 'Выбери правильное свойство flexbox'
        },
        {
            'id': 'fe_4',
            'title': 'JavaScript Clicker',
            'description': 'Напиши логику обработчика событий. Сделай так, чтобы кнопка реагировала на клики.',
            'difficulty': 4,
            'reward_coins': 600,
            'reward_xp': 120,
            'practice_type': 'js_logic',
            'practice_desc': 'Собери правильную последовательность кода'
        },
        {
            'id': 'fe_5',
            'title': 'React Component Architect',
            'description': 'Построй компонентную архитектуру. Разбери интерфейс на переиспользуемые части.',
            'difficulty': 5,
            'reward_coins': 1000,
            'reward_xp': 200,
            'practice_type': 'component_build',
            'practice_desc': 'Собери компоненты в правильной иерархии'
        }
    ],
    'backend': [
        {
            'id': 'be_1',
            'title': 'API Endpoint',
            'description': 'Создай первый API endpoint. Научись обрабатывать GET запросы.',
            'difficulty': 1,
            'reward_coins': 150,
            'reward_xp': 30,
            'practice_type': 'api_path',
            'practice_desc': 'Собери правильный путь API'
        },
        {
            'id': 'be_2',
            'title': 'Logic Gates',
            'description': 'Пойми логические операции AND, OR, NOT. Это основа работы процессора.',
            'difficulty': 2,
            'reward_coins': 250,
            'reward_xp': 50,
            'practice_type': 'logic_gate',
            'practice_desc': 'Настрой переключатели для получения 1 на выходе'
        },
        {
            'id': 'be_3',
            'title': 'Database Query',
            'description': 'Напиши SQL запрос для получения данных. Выбери правильные таблицы.',
            'difficulty': 3,
            'reward_coins': 400,
            'reward_xp': 80,
            'practice_type': 'sql_query',
            'practice_desc': 'Собери SQL запрос из блоков'
        },
        {
            'id': 'be_4',
            'title': 'Auth Token',
            'description': 'Реализуй систему токенов. Пойми как работает JWT аутентификация.',
            'difficulty': 4,
            'reward_coins': 650,
            'reward_xp': 130,
            'practice_type': 'token_puzzle',
            'practice_desc': 'Расшифруй токен и проверь подпись'
        },
        {
            'id': 'be_5',
            'title': 'Load Balancer',
            'description': 'Настрой балансировку нагрузки между серверами. Оптимизируй распределение.',
            'difficulty': 5,
            'reward_coins': 1100,
            'reward_xp': 220,
            'practice_type': 'load_balance',
            'practice_desc': 'Распредели запросы между серверами'
        }
    ],
    'mobile': [
        {
            'id': 'mob_1',
            'title': 'Touch Gestures',
            'description': 'Научись распознавать жесты. Отличай tap от swipe и pinch.',
            'difficulty': 1,
            'reward_coins': 150,
            'reward_xp': 30,
            'practice_type': 'gesture_match',
            'practice_desc': 'Повтори жест на экране'
        },
        {
            'id': 'mob_2',
            'title': 'Screen Adapt',
            'description': 'Адаптируй интерфейс под разные размеры экранов. От телефона до планшета.',
            'difficulty': 2,
            'reward_coins': 250,
            'reward_xp': 50,
            'practice_type': 'responsive_design',
            'practice_desc': 'Подстрой макет под размер экрана'
        },
        {
            'id': 'mob_3',
            'title': 'Battery Saver',
            'description': 'Оптимизируй потребление энергии. Выбери что можно отключить для экономии.',
            'difficulty': 3,
            'reward_coins': 400,
            'reward_xp': 80,
            'practice_type': 'battery_opt',
            'practice_desc': 'Выбери оптимизации для экономии батареи'
        },
        {
            'id': 'mob_4',
            'title': 'Offline Sync',
            'description': 'Настрой синхронизацию данных. Приложение должно работать без интернета.',
            'difficulty': 4,
            'reward_coins': 650,
            'reward_xp': 130,
            'practice_type': 'sync_puzzle',
            'practice_desc': 'Упорядочи операции синхронизации'
        },
        {
            'id': 'mob_5',
            'title': 'App Store Ready',
            'description': 'Подготовь приложение к публикации. Пройди все проверки качества.',
            'difficulty': 5,
            'reward_coins': 1200,
            'reward_xp': 250,
            'practice_type': 'store_check',
            'practice_desc': 'Найди и исправь все ошибки в приложении'
        }
    ],
    'devops': [
        {
            'id': 'do_1',
            'title': 'Linux Commands',
            'description': 'Освой базовые команды Linux. Навигация, файлы, права доступа.',
            'difficulty': 1,
            'reward_coins': 200,
            'reward_xp': 40,
            'practice_type': 'linux_cmd',
            'practice_desc': 'Собери команду из частей'
        },
        {
            'id': 'do_2',
            'title': 'Docker Container',
            'description': 'Упакуй приложение в контейнер. Пойми изоляцию процессов.',
            'difficulty': 2,
            'reward_coins': 300,
            'reward_xp': 60,
            'practice_type': 'docker_build',
            'practice_desc': 'Собери Dockerfile правильно'
        },
        {
            'id': 'do_3',
            'title': 'Git Pipeline',
            'description': 'Настрой CI/CD pipeline. Автоматизируй тестирование и деплой.',
            'difficulty': 3,
            'reward_coins': 500,
            'reward_xp': 100,
            'practice_type': 'git_pipeline',
            'practice_desc': 'Расположи этапы pipeline в правильном порядке'
        },
        {
            'id': 'do_4',
            'title': 'Kubernetes Pods',
            'description': 'Оркестрируй контейнеры в Kubernetes. Масштабируй приложение.',
            'difficulty': 4,
            'reward_coins': 800,
            'reward_xp': 160,
            'practice_type': 'k8s_scale',
            'practice_desc': 'Распредели поды по нодам кластера'
        },
        {
            'id': 'do_5',
            'title': 'Disaster Recovery',
            'description': 'Подготовь план аварийного восстановления. Обеспечь 99.99% uptime.',
            'difficulty': 5,
            'reward_coins': 1400,
            'reward_xp': 280,
            'practice_type': 'disaster_recovery',
            'practice_desc': 'Восстанови систему после сбоя'
        }
    ],
    'data': [
        {
            'id': 'ds_1',
            'title': 'Data Cleaner',
            'description': 'Очисти данные от мусора. Найди пропуски и выбросы.',
            'difficulty': 1,
            'reward_coins': 200,
            'reward_xp': 40,
            'practice_type': 'data_clean',
            'practice_desc': 'Выбери неверные данные в таблице'
        },
        {
            'id': 'ds_2',
            'title': 'Pattern Finder',
            'description': 'Найди закономерности в данных. Визуализируй корреляции.',
            'difficulty': 2,
            'reward_coins': 300,
            'reward_xp': 60,
            'practice_type': 'pattern_match',
            'practice_desc': 'Найди совпадающие паттерны'
        },
        {
            'id': 'ds_3',
            'title': 'Regression Model',
            'description': 'Построй модель линейной регрессии. Предскажи значения.',
            'difficulty': 3,
            'reward_coins': 500,
            'reward_xp': 100,
            'practice_type': 'regression_fit',
            'practice_desc': 'Подбери линию к точкам данных'
        },
        {
            'id': 'ds_4',
            'title': 'Neural Network',
            'description': 'Настрой нейросеть для классификации. Подбери веса связей.',
            'difficulty': 4,
            'reward_coins': 900,
            'reward_xp': 180,
            'practice_type': 'neural_weights',
            'practice_desc': 'Настрой веса нейронов для правильной классификации'
        },
        {
            'id': 'ds_5',
            'title': 'Big Data Processing',
            'description': 'Обработай огромный массив данных. Оптимизируй производительность.',
            'difficulty': 5,
            'reward_coins': 1600,
            'reward_xp': 320,
            'practice_type': 'big_data',
            'practice_desc': 'Распредели данные по узлам кластера'
        }
    ],
    'security': [
        {
            'id': 'sec_1',
            'title': 'Port Scanner',
            'description': 'Просканируй систему на открытые порты. Найди точки входа.',
            'difficulty': 1,
            'reward_coins': 200,
            'reward_xp': 40,
            'practice_type': 'port_scan',
            'practice_desc': 'Найди открытые порты на сервере'
        },
        {
            'id': 'sec_2',
            'title': 'Password Cracker',
            'description': 'Пойми как взламывают пароли. Научись создавать надёжные.',
            'difficulty': 2,
            'reward_coins': 350,
            'reward_xp': 70,
            'practice_type': 'password_strength',
            'practice_desc': 'Собери пароль, устойчивый к атакам'
        },
        {
            'id': 'sec_3',
            'title': 'SQL Injection',
            'description': 'Найди и исправь уязвимость. Защити базу данных от инъекций.',
            'difficulty': 3,
            'reward_coins': 600,
            'reward_xp': 120,
            'practice_type': 'sql_inject_fix',
            'practice_desc': 'Найди уязвимый запрос и исправь его'
        },
        {
            'id': 'sec_4',
            'title': 'Encryption Master',
            'description': 'Работай с шифрованием. Расшифруй сообщение, зная ключ.',
            'difficulty': 4,
            'reward_coins': 1000,
            'reward_xp': 200,
            'practice_type': 'crypto_break',
            'practice_desc': 'Расшифруй сообщение методом частотного анализа'
        },
        {
            'id': 'sec_5',
            'title': 'Zero Day Hunt',
            'description': 'Найди неизвестную уязвимость. Проведи полный аудит системы.',
            'difficulty': 5,
            'reward_coins': 1800,
            'reward_xp': 360,
            'practice_type': 'zero_day',
            'practice_desc': 'Найди скрытую уязвимость в коде'
        }
    ]
}

# Сферы профессий
SPHERES_DATA = {
    'tech': {
        'name': 'IT & ТЕХНОЛОГИИ',
        'icon': '💻',
        'color': '#00d4aa',
        'description': 'Программирование, разработка, кибербезопасность и данные'
    }
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
                'was_full': True,
                'current_task': None,
                'practice_score': 0
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

@app.get("/api/spheres")
async def get_spheres():
    return {'success': True, 'spheres': SPHERES_DATA}

@app.get("/api/professions_by_sphere")
async def get_professions_by_sphere(sphere: str):
    profs = {k: v for k, v in PROFESSIONS_DATA.items() if v.get('sphere') == sphere}
    return {'success': True, 'professions': profs}

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

@app.post("/api/start_practice")
async def start_practice(request: Request):
    data = await request.json()
    user_id = data.get('user_id')
    task_id = data.get('task_id')
    prof_key = data.get('prof_key')
    
    if prof_key not in TASKS_DATA:
        return {'success': False, 'message': 'Profession not found'}
    
    task = None
    for t in TASKS_DATA[prof_key]:
        if t['id'] == task_id:
            task = t
            break
    
    if not task:
        return {'success': False, 'message': 'Task not found'}
    
    session = get_session(user_id)
    session['current_task'] = task_id
    session['practice_score'] = 0
    
    return {
        'success': True,
        'practice_type': task.get('practice_type'),
        'practice_desc': task.get('practice_desc'),
        'task': task
    }

@app.post("/api/complete_practice")
async def complete_practice(request: Request):
    data = await request.json()
    user_id = data.get('user_id')
    prof_key = data.get('prof_key')
    task_id = data.get('task_id')
    score = data.get('score', 0)
    
    user = get_user(user_id)
    session = get_session(user_id)
    
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
    
    # Награда зависит от score (0-100)
    max_coins = task['reward_coins']
    max_xp = task['reward_xp']
    
    earned_coins = int((score / 100) * max_coins)
    earned_xp = int((score / 100) * max_xp)
    
    # Минимум 50% за попытку
    earned_coins = max(int(max_coins * 0.5), earned_coins)
    earned_xp = max(int(max_xp * 0.5), earned_xp)
    
    user['coins'] += earned_coins
    user['xp'] += earned_xp
    
    # Проверка уровня
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
        'score': score,
        'earned_coins': earned_coins,
        'earned_xp': earned_xp,
        'coins': user['coins'],
        'xp': user['xp'],
        'level': user['level'],
        'tokens': user['tokens'],
        'tokens_gained': tokens_gained,
        'level_up': tokens_gained > 0
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
            position: relative;
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
            position: fixed;
            font-size: 14px;
            color: var(--coin);
            text-shadow: 2px 2px 0px #000;
            pointer-events: none;
            animation: floatUp 0.8s forwards;
            z-index: 9999;
        }
        @keyframes floatUp {
            0% { opacity: 1; transform: translateY(0) scale(1); }
            100% { opacity: 0; transform: translateY(-60px) scale(1.2); }
        }
        
        /* Spheres Screen */
        .spheres-grid {
            flex: 1;
            display: grid;
            grid-template-columns: 1fr;
            gap: 10px;
            padding: 10px;
            overflow-y: auto;
        }
        .sphere-card {
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 15px;
            cursor: pointer;
            transition: all 0.2s;
            border-left: 5px solid;
        }
        .sphere-card:hover {
            transform: translateX(5px);
        }
        .sphere-icon {
            font-size: 40px;
        }
        .sphere-info {
            flex: 1;
        }
        .sphere-name {
            font-size: 12px;
            margin-bottom: 5px;
        }
        .sphere-desc {
            font-size: 7px;
            color: #888;
            line-height: 1.4;
        }
        
        /* Professions Grid in Sphere */
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
        
        /* Guide Modal */
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
        
        /* Tasks List */
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
        .practice-badge {
            display: inline-block;
            padding: 3px 8px;
            background: var(--accent);
            color: #fff;
            font-size: 6px;
            margin-top: 5px;
        }
        
        /* Practice Modal */
        .practice-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.98);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 3000;
            padding: 10px;
        }
        .practice-modal.show { display: flex; }
        .practice-content {
            background: var(--panel-bg);
            border: 4px solid var(--accent);
            padding: 15px;
            max-width: 380px;
            width: 100%;
            height: 90vh;
            display: flex;
            flex-direction: column;
        }
        .practice-header {
            text-align: center;
            padding: 10px;
            border-bottom: 2px solid var(--border-color);
            margin-bottom: 10px;
        }
        .practice-title {
            font-size: 12px;
            color: var(--accent);
            margin-bottom: 5px;
        }
        .practice-desc {
            font-size: 8px;
            color: #888;
        }
        .practice-area {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }
        .practice-footer {
            padding-top: 10px;
            border-top: 2px solid var(--border-color);
            display: flex;
            gap: 10px;
        }
        .practice-btn {
            flex: 1;
            padding: 12px;
            font-family: 'Press Start 2P', cursive;
            font-size: 10px;
            background: var(--success);
            border: none;
            box-shadow: 3px 3px 0px #2d8b84;
            color: #000;
            cursor: pointer;
        }
        .practice-btn.secondary {
            background: var(--panel-bg);
            border: 2px solid var(--border-color);
            color: var(--text);
            box-shadow: none;
        }
        
        /* Mini Game Styles */
        .game-container {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        /* HTML Puzzle */
        .code-blocks {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .code-block {
            padding: 12px;
            background: var(--border-color);
            border: 3px solid #000;
            cursor: pointer;
            font-size: 10px;
            text-align: center;
            transition: all 0.2s;
        }
        .code-block.selected {
            background: var(--accent);
            transform: scale(1.05);
        }
        .code-dropzone {
            min-height: 150px;
            border: 3px dashed var(--border-color);
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-bottom: 15px;
        }
        .code-dropzone .code-block {
            background: var(--success);
            cursor: default;
        }
        
        /* Color Match */
        .color-target-box {
            width: 100%;
            height: 100px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            color: #000;
            text-shadow: 1px 1px 0 #fff;
            margin-bottom: 15px;
        }
        .color-options-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }
        .color-option-btn {
            aspect-ratio: 1;
            border: 4px solid #000;
            cursor: pointer;
            transition: transform 0.1s;
        }
        .color-option-btn:active {
            transform: scale(0.95);
        }
        
        /* Logic Gate */
        .logic-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 20px;
            padding: 20px;
        }
        .logic-switches {
            display: flex;
            gap: 30px;
        }
        .logic-switch-btn {
            width: 60px;
            height: 60px;
            border: 4px solid #000;
            font-size: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            background: var(--danger);
            transition: all 0.2s;
        }
        .logic-switch-btn.on {
            background: var(--success);
        }
        .logic-gate-display {
            padding: 15px 30px;
            background: var(--border-color);
            border: 4px solid #000;
            font-size: 12px;
        }
        .logic-output {
            width: 80px;
            height: 80px;
            border: 4px solid #000;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            background: var(--danger);
        }
        .logic-output.active {
            background: var(--success);
        }
        
        /* Flexbox Defense */
        .defense-container {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .defense-field {
            height: 200px;
            background: #0f3d3e;
            border: 3px solid var(--success);
            position: relative;
            display: flex;
            padding: 10px;
            gap: 10px;
        }
        .defense-enemy {
            width: 40px;
            height: 40px;
            background: var(--danger);
            border: 2px solid #000;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }
        .defense-tower {
            width: 40px;
            height: 40px;
            background: var(--warning);
            border: 2px solid #000;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }
        .defense-options {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }
        .defense-option {
            padding: 10px;
            background: var(--border-color);
            border: 2px solid #000;
            cursor: pointer;
            font-size: 8px;
            text-align: center;
        }
        .defense-option:hover {
            background: var(--accent);
        }
        
        /* Pattern Match */
        .pattern-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            max-width: 280px;
            margin: 0 auto;
        }
        .pattern-cell {
            aspect-ratio: 1;
            background: var(--border-color);
            border: 3px solid #000;
            cursor: pointer;
            transition: all 0.2s;
        }
        .pattern-cell.active {
            background: var(--success);
            box-shadow: 0 0 15px var(--success);
        }
        .pattern-cell.highlight {
            background: var(--warning);
        }
        
        /* SQL Query Builder */
        .sql-builder {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .sql-clauses {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: center;
        }
        .sql-clause {
            padding: 8px 12px;
            background: var(--border-color);
            border: 2px solid #000;
            cursor: pointer;
            font-size: 9px;
        }
        .sql-clause:hover {
            background: var(--accent);
        }
        .sql-query-display {
            min-height: 80px;
            background: #000;
            border: 2px solid var(--success);
            padding: 10px;
            font-family: monospace;
            font-size: 10px;
            color: var(--success);
        }
        
        /* Gesture Match */
        .gesture-area {
            width: 100%;
            height: 250px;
            background: var(--panel-bg);
            border: 4px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 48px;
            position: relative;
            overflow: hidden;
        }
        .gesture-target {
            position: absolute;
            font-size: 32px;
            opacity: 0.5;
        }
        .gesture-instruction {
            text-align: center;
            padding: 10px;
            font-size: 10px;
            color: var(--warning);
        }
        
        /* Battery Optimization */
        .battery-container {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .battery-display {
            height: 60px;
            background: #000;
            border: 3px solid var(--border-color);
            position: relative;
        }
        .battery-level {
            height: 100%;
            background: linear-gradient(90deg, var(--danger), var(--warning), var(--success));
            transition: width 0.5s;
        }
        .battery-options {
            display: grid;
            grid-template-columns: 1fr;
            gap: 8px;
        }
        .battery-option {
            padding: 12px;
            background: var(--border-color);
            border: 2px solid #000;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .battery-option.selected {
            background: var(--success);
        }
        .battery-option .saving {
            color: var(--success);
            font-size: 8px;
        }
        
        /* Result Screen */
        .result-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.95);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 4000;
            flex-direction: column;
            gap: 20px;
        }
        .result-overlay.show { display: flex; }
        .result-score-big {
            font-size: 64px;
            color: var(--success);
            text-shadow: 4px 4px 0 #000;
        }
        .result-reward-text {
            font-size: 14px;
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
            z-index: 9999;
            transition: transform 0.3s;
        }
        .toast.show { transform: translateX(-50%) scale(1); }
    </style>
</head>
<body>
    <div class="toast" id="toast"></div>
    
    <!-- Practice Result Overlay -->
    <div class="result-overlay" id="practiceResult">
        <div class="result-score-big" id="resultScore">0%</div>
        <div class="result-reward-text" id="resultReward">+0 🪙 +0 XP</div>
        <button class="modal-btn" onclick="closePracticeResult()">ПРОДОЛЖИТЬ</button>
    </div>
    
    <!-- Practice Modal -->
    <div class="practice-modal" id="practiceModal">
        <div class="practice-content">
            <div class="practice-header">
                <div class="practice-title" id="practiceTitle">ПРАКТИКА</div>
                <div class="practice-desc" id="practiceDesc">Выполни задание</div>
            </div>
            <div class="practice-area" id="practiceArea">
                <!-- Game content here -->
            </div>
            <div class="practice-footer">
                <button class="practice-btn secondary" onclick="closePractice()">ВЫЙТИ</button>
                <button class="practice-btn" id="checkPracticeBtn" onclick="checkPractice()">ПРОВЕРИТЬ</button>
            </div>
        </div>
    </div>
    
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
            <button class="guide-btn" id="guideActionBtn" onclick="unlockOrGoToTasks()">ОТКРЫТЬ ЗА 1 ТОКЕН</button>
            <button class="guide-btn" onclick="closeGuide()" style="background: var(--panel-bg); color: var(--text); margin-top: 5px;">ЗАКРЫТЬ</button>
        </div>
    </div>

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
    
    <!-- Spheres Screen -->
    <div class="container screen" id="spheresScreen">
        <div class="pixel-box" style="padding: 15px; text-align: center;">
            <h2 style="font-size: 12px; color: var(--token);">◆ СФЕРЫ ПРОФЕССИЙ ◆</h2>
            <div style="margin-top: 10px; font-size: 10px; color: var(--token);">
                🔷 ТОКЕНОВ: <span id="spheresScreenTokens">0</span>
            </div>
        </div>
        
        <div class="spheres-grid" id="spheresGrid"></div>
        
        <button class="back-btn" onclick="backToGame()">◀ НАЗАД</button>
    </div>
    
    <!-- Professions in Sphere Screen -->
    <div class="container screen" id="sphereProfessionsScreen">
        <div class="pixel-box" style="padding: 15px; text-align: center;">
            <h2 style="font-size: 12px;" id="sphereTitle">◆ IT & ТЕХНОЛОГИИ ◆</h2>
            <div style="margin-top: 5px; font-size: 8px; color: #888;" id="sphereDesc">
                Выбери профессию для изучения
            </div>
        </div>
        
        <div class="professions-grid" id="sphereProfessionsGrid"></div>
        
        <button class="back-btn" onclick="backToSpheres()">◀ К СФЕРАМ</button>
    </div>
    
    <!-- Tasks Screen -->
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
    
    <!-- Profession Tasks Screen -->
    <div class="container screen" id="professionTasksScreen">
        <div class="pixel-box" style="padding: 15px; text-align: center;">
            <h2 style="font-size: 12px; color: var(--accent);" id="profTasksTitle">◆ FRONTEND ◆</h2>
            <div style="margin-top: 5px; font-size: 8px; color: #888;">
                Выполняй задания от лёгких к сложным
            </div>
        </div>
        
        <div class="tasks-list" id="profTasksList"></div>
        
        <button class="back-btn" onclick="backToTasks()">◀ К ПРОФЕССИЯМ</button>
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
        let currentSphere = null;
        let spheresData = {};
        let currentPracticeTask = null;
        let practiceScore = 0;
        let practiceState = {};
        
        const MAX = 20, MIN = 1;
        
        const professionsData = {
            'frontend': {name: 'FRONTEND DEV', icon: '🎨', cost: 1, sphere: 'tech'},
            'backend': {name: 'BACKEND DEV', icon: '⚙️', cost: 1, sphere: 'tech'},
            'mobile': {name: 'MOBILE DEV', icon: '📱', cost: 1, sphere: 'tech'},
            'devops': {name: 'DEVOPS', icon: '🚀', cost: 2, sphere: 'tech'},
            'data': {name: 'DATA SCIENCE', icon: '📊', cost: 2, sphere: 'tech'},
            'security': {name: 'SECURITY', icon: '🔒', cost: 2, sphere: 'tech'}
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
            
            const floatEl = document.createElement('div');
            floatEl.className = 'floating-reward';
            floatEl.textContent = '+' + fingers;
            floatEl.style.left = x + 'px';
            floatEl.style.top = y + 'px';
            floatEl.style.transform = 'translate(-50%, -50%)';
            document.body.appendChild(floatEl);
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
        
        async function openProfessions() {
            let r = await fetch('/api/spheres');
            let d = await r.json();
            if (d.success) {
                spheresData = d.spheres;
                renderSpheres();
                showScreen('spheresScreen');
                document.getElementById('spheresScreenTokens').textContent = state.tokens || 0;
            }
        }
        
        function renderSpheres() {
            const grid = document.getElementById('spheresGrid');
            grid.innerHTML = '';
            
            for (let [key, data] of Object.entries(spheresData)) {
                const card = document.createElement('div');
                card.className = 'sphere-card pixel-box';
                card.style.borderLeftColor = data.color;
                card.innerHTML = `
                    <div class="sphere-icon">${data.icon}</div>
                    <div class="sphere-info">
                        <div class="sphere-name" style="color: ${data.color}">${data.name}</div>
                        <div class="sphere-desc">${data.description}</div>
                    </div>
                    <div style="font-size: 20px;">➤</div>
                `;
                card.onclick = () => openSphere(key);
                grid.appendChild(card);
            }
        }
        
        async function openSphere(sphereKey) {
            currentSphere = sphereKey;
            const sphere = spheresData[sphereKey];
            
            document.getElementById('sphereTitle').textContent = `◆ ${sphere.name} ◆`;
            document.getElementById('sphereTitle').style.color = sphere.color;
            document.getElementById('sphereDesc').textContent = sphere.description;
            
            let r = await fetch(`/api/professions_by_sphere?sphere=${sphereKey}`);
            let d = await r.json();
            
            if (d.success) {
                renderSphereProfessions(d.professions);
                showScreen('sphereProfessionsScreen');
            }
        }
        
        function renderSphereProfessions(professions) {
            const grid = document.getElementById('sphereProfessionsGrid');
            grid.innerHTML = '';
            
            for (let [key, data] of Object.entries(professions)) {
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
        
        function backToSpheres() {
            showScreen('spheresScreen');
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
                openProfessionTasks(currentGuideProf);
            } else {
                showToast('✗ ' + d.message);
            }
        }
        
        function unlockOrGoToTasks() {
            const isUnlocked = currentGuideProf in unlockedProfs;
            if (isUnlocked) {
                closeGuide();
                openProfessionTasks(currentGuideProf);
            } else {
                unlockProfession();
            }
        }
        
        async function openProfessionTasks(profKey) {
            currentTaskProf = profKey;
            const profData = professionsData[profKey];
            
            document.getElementById('profTasksTitle').textContent = `◆ ${profData.name} ◆`;
            
            const r = await fetch(`/api/profession_tasks?prof_key=${profKey}&user_id=${uid}`);
            const d = await r.json();
            
            if (!d.success) return;
            
            const list = document.getElementById('profTasksList');
            list.innerHTML = '';
            
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
                    ${!isCompleted && !isLocked ? `<span class="practice-badge">🎮 ПРАКТИКА: ${task.practice_desc}</span>` : ''}
                `;
                
                if (!isCompleted && !isLocked) {
                    card.onclick = () => startPractice(task);
                }
                
                list.appendChild(card);
                
                if (!isCompleted) prevCompleted = false;
            });
            
            showScreen('professionTasksScreen');
        }
        
        function backToTasks() {
            showScreen('tasksScreen');
        }
        
        // Practice / Mini Games
        async function startPractice(task) {
            currentPracticeTask = task;
            practiceScore = 0;
            practiceState = {};
            
            document.getElementById('practiceTitle').textContent = task.title;
            document.getElementById('practiceDesc').textContent = task.practice_desc;
            
            const container = document.getElementById('practiceArea');
            container.innerHTML = '';
            
            const practiceType = task.practice_type;
            
            switch(practiceType) {
                case 'html_puzzle':
                    initHtmlPuzzle(container);
                    break;
                case 'color_match':
                    initColorMatch(container);
                    break;
                case 'logic_gate':
                    initLogicGate(container);
                    break;
                case 'flexbox_defense':
                    initFlexboxDefense(container);
                    break;
                case 'pattern_match':
                    initPatternMatch(container);
                    break;
                case 'sql_query':
                    initSqlQuery(container);
                    break;
                case 'gesture_match':
                    initGestureMatch(container);
                    break;
                case 'battery_opt':
                    initBatteryOpt(container);
                    break;
                case 'linux_cmd':
                    initLinuxCmd(container);
                    break;
                case 'docker_build':
                    initDockerBuild(container);
                    break;
                case 'data_clean':
                    initDataClean(container);
                    break;
                case 'port_scan':
                    initPortScan(container);
                    break;
                default:
                    initHtmlPuzzle(container);
            }
            
            document.getElementById('practiceModal').classList.add('show');
        }
        
        function closePractice() {
            document.getElementById('practiceModal').classList.remove('show');
        }
        
        // HTML Puzzle Game
        function initHtmlPuzzle(container) {
            const blocks = [
                {tag: '<html>', order: 1},
                {tag: '<head>', order: 2},
                {tag: '<title>My Page</title>', order: 3},
                {tag: '</head>', order: 4},
                {tag: '<body>', order: 5},
                {tag: '<h1>Hello</h1>', order: 6},
                {tag: '</body>', order: 7},
                {tag: '</html>', order: 8}
            ];
            
            practiceState.correctOrder = [1,2,3,4,5,6,7,8];
            practiceState.playerOrder = [];
            practiceState.blocks = blocks;
            
            const dropzone = document.createElement('div');
            dropzone.className = 'code-dropzone';
            dropzone.id = 'htmlDropzone';
            container.appendChild(dropzone);
            
            const blocksContainer = document.createElement('div');
            blocksContainer.className = 'code-blocks';
            
            const shuffled = [...blocks].sort(() => Math.random() - 0.5);
            
            shuffled.forEach((block, idx) => {
                const div = document.createElement('div');
                div.className = 'code-block';
                div.textContent = block.tag;
                div.onclick = () => {
                    practiceState.playerOrder.push(block.order);
                    div.classList.add('selected');
                    div.style.pointerEvents = 'none';
                    div.style.opacity = '0.5';
                    
                    const inDropzone = document.createElement('div');
                    inDropzone.className = 'code-block';
                    inDropzone.textContent = block.tag;
                    dropzone.appendChild(inDropzone);
                    
                    if (practiceState.playerOrder.length === blocks.length) {
                        checkHtmlPuzzle();
                    }
                };
                blocksContainer.appendChild(div);
            });
            
            container.appendChild(blocksContainer);
            
            document.getElementById('checkPracticeBtn').style.display = 'none';
        }
        
        function checkHtmlPuzzle() {
            let correct = 0;
            for (let i = 0; i < practiceState.correctOrder.length; i++) {
                if (practiceState.playerOrder[i] === practiceState.correctOrder[i]) {
                    correct++;
                }
            }
            practiceScore = Math.round((correct / practiceState.correctOrder.length) * 100);
            submitPractice();
        }
        
        // Color Match Game
        function initColorMatch(container) {
            const colors = ['#ff6b6b', '#4ecdc4', '#ffe66d', '#9b59b6', '#ff6b9d', '#00d4aa'];
            const targetColor = colors[Math.floor(Math.random() * colors.length)];
            const harmonizing = colors[Math.floor(Math.random() * colors.length)];
            
            practiceState.correctColor = harmonizing;
            
            const targetBox = document.createElement('div');
            targetBox.className = 'color-target-box';
            targetBox.style.background = targetColor;
            targetBox.textContent = 'ОБРАЗЕЦ';
            container.appendChild(targetBox);
            
            const instruction = document.createElement('div');
            instruction.style.textAlign = 'center';
            instruction.style.marginBottom = '10px';
            instruction.textContent = 'Выбери гармонирующий цвет';
            container.appendChild(instruction);
            
            const grid = document.createElement('div');
            grid.className = 'color-options-grid';
            
            const shuffled = [...colors].sort(() => Math.random() - 0.5);
            shuffled.forEach(color => {
                const btn = document.createElement('div');
                btn.className = 'color-option-btn';
                btn.style.background = color;
                btn.onclick = () => {
                    practiceScore = color === harmonizing ? 100 : Math.floor(Math.random() * 40) + 30;
                    submitPractice();
                };
                grid.appendChild(btn);
            });
            
            container.appendChild(grid);
            document.getElementById('checkPracticeBtn').style.display = 'none';
        }
        
        // Logic Gate Game
        function initLogicGate(container) {
            const logicContainer = document.createElement('div');
            logicContainer.className = 'logic-container';
            
            practiceState.switches = [false, false];
            practiceState.targetOutput = true; // AND gate needs both true
            
            const switchesDiv = document.createElement('div');
            switchesDiv.className = 'logic-switches';
            
            for (let i = 0; i < 2; i++) {
                const sw = document.createElement('div');
                sw.className = 'logic-switch-btn';
                sw.textContent = '0';
                sw.onclick = () => {
                    practiceState.switches[i] = !practiceState.switches[i];
                    sw.classList.toggle('on');
                    sw.textContent = practiceState.switches[i] ? '1' : '0';
                    updateLogicOutput();
                };
                switchesDiv.appendChild(sw);
            }
            
            logicContainer.appendChild(switchesDiv);
            
            const gateLabel = document.createElement('div');
            gateLabel.textContent = 'AND GATE (нужно 1 и 1)';
            gateLabel.style.fontSize = '10px';
            logicContainer.appendChild(gateLabel);
            
            const output = document.createElement('div');
            output.className = 'logic-output';
            output.id = 'logicOutput';
            output.textContent = '0';
            logicContainer.appendChild(output);
            
            container.appendChild(logicContainer);
            
            window.updateLogicOutput = function() {
                const result = practiceState.switches[0] && practiceState.switches[1];
                const outEl = document.getElementById('logicOutput');
                outEl.textContent = result ? '1' : '0';
                outEl.classList.toggle('active', result);
                
                if (result) {
                    setTimeout(() => {
                        practiceScore = 100;
                        submitPractice();
                    }, 500);
                }
            };
            
            document.getElementById('checkPracticeBtn').style.display = 'none';
        }
        
        // Flexbox Defense Game
        function initFlexboxDefense(container) {
            const gameDiv = document.createElement('div');
            gameDiv.className = 'defense-container';
            
            practiceState.defenseCorrect = 'space-between';
            
            const field = document.createElement('div');
            field.className = 'defense-field';
            field.id = 'defenseField';
            field.style.justifyContent = 'flex-start';
            
            const tower = document.createElement('div');
            tower.className = 'defense-tower';
            tower.textContent = '🏰';
            field.appendChild(tower);
            
            const enemy1 = document.createElement('div');
            enemy1.className = 'defense-enemy';
            enemy1.textContent = '👾';
            field.appendChild(enemy1);
            
            const enemy2 = document.createElement('div');
            enemy2.className = 'defense-enemy';
            enemy2.textContent = '👾';
            field.appendChild(enemy2);
            
            gameDiv.appendChild(field);
            
            const instruction = document.createElement('div');
            instruction.textContent = 'Расположи башню между врагами используя flexbox';
            instruction.style.textAlign = 'center';
            instruction.style.fontSize = '8px';
            gameDiv.appendChild(instruction);
            
            const options = document.createElement('div');
            options.className = 'defense-options';
            
            const choices = ['flex-start', 'center', 'space-between', 'space-around'];
            choices.forEach(choice => {
                const btn = document.createElement('div');
                btn.className = 'defense-option';
                btn.textContent = choice;
                btn.onclick = () => {
                    field.style.justifyContent = choice;
                    practiceState.selectedDefense = choice;
                };
                options.appendChild(btn);
            });
            
            gameDiv.appendChild(options);
            container.appendChild(gameDiv);
            
            document.getElementById('checkPracticeBtn').onclick = () => {
                practiceScore = practiceState.selectedDefense === practiceState.defenseCorrect ? 100 : 50;
                submitPractice();
            };
            document.getElementById('checkPracticeBtn').style.display = 'block';
            document.getElementById('checkPracticeBtn').textContent = 'ПРОВЕРИТЬ';
        }
        
        // Pattern Match Game
        function initPatternMatch(container) {
            const grid = document.createElement('div');
            grid.className = 'pattern-grid';
            
            practiceState.pattern = [];
            practiceState.playerPattern = [];
            practiceState.round = 0;
            
            for (let i = 0; i < 16; i++) {
                const cell = document.createElement('div');
                cell.className = 'pattern-cell';
                cell.dataset.index = i;
                cell.onclick = () => handlePatternClick(i);
                grid.appendChild(cell);
            }
            
            container.appendChild(grid);
            
            const instruction = document.createElement('div');
            instruction.style.textAlign = 'center';
            instruction.style.marginTop = '10px';
            instruction.textContent = 'Повтори последовательность';
            container.appendChild(instruction);
            
            window.handlePatternClick = function(index) {
                practiceState.playerPattern.push(index);
                const cell = grid.children[index];
                cell.classList.add('highlight');
                setTimeout(() => cell.classList.remove('highlight'), 200);
                
                if (practiceState.playerPattern[practiceState.playerPattern.length - 1] !== 
                    practiceState.pattern[practiceState.playerPattern.length - 1]) {
                    practiceScore = Math.round((practiceState.round / 3) * 100);
                    submitPractice();
                    return;
                }
                
                if (practiceState.playerPattern.length === practiceState.pattern.length) {
                    practiceState.round++;
                    if (practiceState.round >= 3) {
                        practiceScore = 100;
                        submitPractice();
                    } else {
                        practiceState.playerPattern = [];
                        setTimeout(() => showPattern(), 500);
                    }
                }
            };
            
            window.showPattern = function() {
                practiceState.pattern.push(Math.floor(Math.random() * 16));
                let i = 0;
                const interval = setInterval(() => {
                    if (i >= practiceState.pattern.length) {
                        clearInterval(interval);
                        return;
                    }
                    const cell = grid.children[practiceState.pattern[i]];
                    cell.classList.add('active');
                    setTimeout(() => cell.classList.remove('active'), 400);
                    i++;
                }, 600);
            };
            
            setTimeout(() => showPattern(), 1000);
            document.getElementById('checkPracticeBtn').style.display = 'none';
        }
        
        // SQL Query Builder
        function initSqlQuery(container) {
            const builder = document.createElement('div');
            builder.className = 'sql-builder';
            
            practiceState.sqlParts = [];
            practiceState.correctSql = ['SELECT', '*', 'FROM', 'users', 'WHERE', 'age', '>', '18'];
            
            const display = document.createElement('div');
            display.className = 'sql-query-display';
            display.id = 'sqlDisplay';
            display.textContent = '-- Твой запрос появится здесь --';
            builder.appendChild(display);
            
            const clausesDiv = document.createElement('div');
            clausesDiv.className = 'sql-clauses';
            
            const clauses = ['SELECT', 'FROM', 'WHERE', '*', 'users', 'age', '>', '18', 'INSERT', 'UPDATE'];
            clauses.forEach(clause => {
                const btn = document.createElement('div');
                btn.className = 'sql-clause';
                btn.textContent = clause;
                btn.onclick = () => {
                    practiceState.sqlParts.push(clause);
                    updateSqlDisplay();
                };
                clausesDiv.appendChild(btn);
            });
            
            builder.appendChild(clausesDiv);
            
            const clearBtn = document.createElement('button');
            clearBtn.className = 'practice-btn secondary';
            clearBtn.textContent = 'ОЧИСТИТЬ';
            clearBtn.onclick = () => {
                practiceState.sqlParts = [];
                updateSqlDisplay();
            };
            clearBtn.style.marginTop = '10px';
            builder.appendChild(clearBtn);
            
            container.appendChild(builder);
            
            window.updateSqlDisplay = function() {
                document.getElementById('sqlDisplay').textContent = practiceState.sqlParts.join(' ') || '-- Твой запрос появится здесь --';
            };
            
            document.getElementById('checkPracticeBtn').onclick = () => {
                const playerStr = practiceState.sqlParts.join(' ');
                const correctStr = practiceState.correctSql.join(' ');
                practiceScore = playerStr === correctStr ? 100 : 
                    practiceState.sqlParts.slice(0,4).join(' ') === practiceState.correctSql.slice(0,4).join(' ') ? 70 : 40;
                submitPractice();
            };
            document.getElementById('checkPracticeBtn').style.display = 'block';
            document.getElementById('checkPracticeBtn').textContent = 'ВЫПОЛНИТЬ ЗАПРОС';
        }
        
        // Gesture Match
        function initGestureMatch(container) {
            const area = document.createElement('div');
            area.className = 'gesture-area';
            area.id = 'gestureArea';
            area.textContent = '👆';
            
            practiceState.gestureTarget = 'tap';
            practiceState.gestureDetected = false;
            
            let touchStartX, touchStartY;
            
            area.addEventListener('touchstart', (e) => {
                touchStartX = e.touches[0].clientX;
                touchStartY = e.touches[0].clientY;
            });
            
            area.addEventListener('touchend', (e) => {
                const touchEndX = e.changedTouches[0].clientX;
                const touchEndY = e.changedTouches[0].clientY;
                
                const diffX = touchEndX - touchStartX;
                const diffY = touchEndY - touchStartY;
                
                if (Math.abs(diffX) < 10 && Math.abs(diffY) < 10) {
                    practiceScore = 100;
                    submitPractice();
                } else {
                    area.textContent = '❌';
                    setTimeout(() => {
                        area.textContent = '👆';
                    }, 500);
                }
            });
            
            area.addEventListener('click', () => {
                practiceScore = 100;
                submitPractice();
            });
            
            container.appendChild(area);
            
            const instruction = document.createElement('div');
            instruction.className = 'gesture-instruction';
            instruction.textContent = 'Нажми (tap) на область';
            container.appendChild(instruction);
            
            document.getElementById('checkPracticeBtn').style.display = 'none';
        }
        
        // Battery Optimization
        function initBatteryOpt(container) {
            const batDiv = document.createElement('div');
            batDiv.className = 'battery-container';
            
            practiceState.selectedOptimizations = [];
            practiceState.correctOptimizations = ['wifi', 'brightness', 'background'];
            
            const levelDiv = document.createElement('div');
            levelDiv.className = 'battery-display';
            levelDiv.innerHTML = '<div class="battery-level" id="batteryLevel" style="width: 20%"></div>';
            batDiv.appendChild(levelDiv);
            
            const label = document.createElement('div');
            label.textContent = 'Заряд: 20% → Выбери оптимизации для экономии';
            label.style.textAlign = 'center';
            label.style.fontSize = '8px';
            batDiv.appendChild(label);
            
            const options = document.createElement('div');
            options.className = 'battery-options';
            
            const opts = [
                {id: 'wifi', text: 'Выключить WiFi', saving: 15},
                {id: 'brightness', text: 'Уменьшить яркость', saving: 20},
                {id: 'bluetooth', text: 'Выключить Bluetooth', saving: 5},
                {id: 'background', text: 'Закрыть фоновые приложения', saving: 25},
                {id: 'gps', text: 'Выключить GPS', saving: 10}
            ];
            
            opts.forEach(opt => {
                const btn = document.createElement('div');
                btn.className = 'battery-option';
                btn.innerHTML = `<span>${opt.text}</span><span class="saving">-${opt.saving}%</span>`;
                btn.onclick = () => {
                    btn.classList.toggle('selected');
                    if (btn.classList.contains('selected')) {
                        practiceState.selectedOptimizations.push(opt.id);
                    } else {
                        practiceState.selectedOptimizations = practiceState.selectedOptimizations.filter(id => id !== opt.id);
                    }
                    updateBatteryLevel();
                };
                options.appendChild(btn);
            });
            
            batDiv.appendChild(options);
            container.appendChild(batDiv);
            
            window.updateBatteryLevel = function() {
                const savings = practiceState.selectedOptimizations.reduce((sum, id) => {
                    const opt = opts.find(o => o.id === id);
                    return sum + (opt ? opt.saving : 0);
                }, 0);
                document.getElementById('batteryLevel').style.width = Math.min(100, 20 + savings) + '%';
            };
            
            document.getElementById('checkPracticeBtn').onclick = () => {
                const hasCorrect = practiceState.correctOptimizations.every(opt => 
                    practiceState.selectedOptimizations.includes(opt)
                );
                practiceScore = hasCorrect ? 100 : 60;
                submitPractice();
            };
            document.getElementById('checkPracticeBtn').style.display = 'block';
            document.getElementById('checkPracticeBtn').textContent = 'ПРИМЕНИТЬ';
        }
        
        // Linux Commands
        function initLinuxCmd(container) {
            const cmdDiv = document.createElement('div');
            cmdDiv.style.display = 'flex';
            cmdDiv.style.flexDirection = 'column';
            cmdDiv.style.gap = '10px';
            
            practiceState.cmdParts = [];
            practiceState.correctCmd = ['ls', '-la', '/home'];
            
            const target = document.createElement('div');
            target.style.padding = '10px';
            target.style.background = '#000';
            target.style.border = '2px solid var(--success)';
            target.textContent = 'Задача: показать все файлы в /home';
            target.style.fontSize = '9px';
            cmdDiv.appendChild(target);
            
            const display = document.createElement('div');
            display.id = 'cmdDisplay';
            display.style.padding = '15px';
            display.style.background = 'var(--border-color)';
            display.style.border = '3px solid #000';
            display.style.fontFamily = 'monospace';
            display.style.fontSize = '12px';
            display.textContent = '$ ';
            cmdDiv.appendChild(display);
            
            const parts = document.createElement('div');
            parts.style.display = 'flex';
            parts.style.flexWrap = 'wrap';
            parts.style.gap = '8px';
            parts.style.justifyContent = 'center';
            
            const cmdParts = ['ls', 'cd', 'mkdir', '-la', '-r', '/home', '/var', 'file.txt'];
            cmdParts.forEach(part => {
                const btn = document.createElement('div');
                btn.style.padding = '8px 12px';
                btn.style.background = 'var(--panel-bg)';
                btn.style.border = '2px solid #000';
                btn.style.cursor = 'pointer';
                btn.textContent = part;
                btn.onclick = () => {
                    practiceState.cmdParts.push(part);
                    document.getElementById('cmdDisplay').textContent = '$ ' + practiceState.cmdParts.join(' ');
                };
                parts.appendChild(btn);
            });
            
            cmdDiv.appendChild(parts);
            container.appendChild(cmdDiv);
            
            document.getElementById('checkPracticeBtn').onclick = () => {
                const cmd = practiceState.cmdParts.join(' ');
                practiceScore = cmd === 'ls -la /home' ? 100 : 
                    cmd.includes('ls') && cmd.includes('/home') ? 70 : 30;
                submitPractice();
            };
            document.getElementById('checkPracticeBtn').style.display = 'block';
            document.getElementById('checkPracticeBtn').textContent = 'ВЫПОЛНИТЬ';
        }
        
        // Docker Build
        function initDockerBuild(container) {
            const dockerDiv = document.createElement('div');
            dockerDiv.style.display = 'flex';
            dockerDiv.style.flexDirection = 'column';
            dockerDiv.style.gap = '15px';
            
            practiceState.dockerfile = [];
            practiceState.correctOrder = ['FROM', 'COPY', 'RUN', 'CMD'];
            
            const dropzone = document.createElement('div');
            dropzone.className = 'code-dropzone';
            dropzone.id = 'dockerDropzone';
            dropzone.innerHTML = '<div style="color: #666; text-align: center;">Собери Dockerfile здесь</div>';
            dockerDiv.appendChild(dropzone);
            
            const blocks = document.createElement('div');
            blocks.className = 'code-blocks';
            
            const instructions = [
                {text: 'FROM node:14', order: 1},
                {text: 'COPY . /app', order: 2},
                {text: 'RUN npm install', order: 3},
                {text: 'CMD ["npm", "start"]', order: 4},
                {text: 'EXPOSE 8080', order: 5},
                {text: 'WORKDIR /app', order: 6}
            ];
            
            const shuffled = [...instructions].sort(() => Math.random() - 0.5);
            
            shuffled.forEach(inst => {
                const btn = document.createElement('div');
                btn.className = 'code-block';
                btn.textContent = inst.text;
                btn.onclick = () => {
                    practiceState.dockerfile.push(inst);
                    btn.style.display = 'none';
                    
                    if (practiceState.dockerfile.length === 1) {
                        dropzone.innerHTML = '';
                    }
                    
                    const added = document.createElement('div');
                    added.className = 'code-block';
                    added.style.background = 'var(--success)';
                    added.textContent = inst.text;
                    dropzone.appendChild(added);
                    
                    if (practiceState.dockerfile.length === 4) {
                        checkDockerfile();
                    }
                };
                blocks.appendChild(btn);
            });
            
            dockerDiv.appendChild(blocks);
            container.appendChild(dockerDiv);
            
            window.checkDockerfile = function() {
                let correct = 0;
                for (let i = 0; i < 4; i++) {
                    if (practiceState.dockerfile[i].order === i + 1) correct++;
                }
                practiceScore = Math.round((correct / 4) * 100);
                submitPractice();
            };
            
            document.getElementById('checkPracticeBtn').style.display = 'none';
        }
        
        // Data Clean
        function initDataClean(container) {
            const dataDiv = document.createElement('div');
            dataDiv.style.display = 'flex';
            dataDiv.style.flexDirection = 'column';
            dataDiv.style.gap = '10px';
            
            const table = document.createElement('div');
            table.style.display = 'grid';
            table.style.gridTemplateColumns = 'repeat(3, 1fr)';
            table.style.gap = '5px';
            
            practiceState.dirtyData = [];
            practiceState.selectedCells = [];
            
            const data = [
                {name: 'Иван', age: 25, city: 'Москва'},
                {name: '---', age: -5, city: 'Питер'},
                {name: 'Мария', age: 30, city: null},
                {name: 'Петр', age: 150, city: 'Казань'},
                {name: 'Анна', age: 28, city: 'Сочи'}
            ];
            
            // Headers
            ['Имя', 'Возраст', 'Город'].forEach(h => {
                const cell = document.createElement('div');
                cell.style.padding = '8px';
                cell.style.background = 'var(--border-color)';
                cell.style.fontSize = '8px';
                cell.textContent = h;
                table.appendChild(cell);
            });
            
            data.forEach((row, rowIdx) => {
                ['name', 'age', 'city'].forEach((key, colIdx) => {
                    const cell = document.createElement('div');
                    cell.style.padding = '8px';
                    cell.style.background = 'var(--panel-bg)';
                    cell.style.border = '2px solid #000';
                    cell.style.cursor = 'pointer';
                    cell.style.fontSize = '9px';
                    cell.textContent = row[key] === null ? 'NULL' : row[key];
                    
                    const isDirty = row[key] === '---' || row[key] === null || 
                                   row[key] === -5 || row[key] === 150;
                    
                    cell.onclick = () => {
                        cell.style.background = cell.style.background === 'rgb(255, 107, 107)' ? 
                            'var(--panel-bg)' : '#ff6b6b';
                        if (isDirty) {
                            practiceState.selectedCells.push(`${rowIdx}-${colIdx}`);
                        }
                    };
                    
                    table.appendChild(cell);
                });
            });
            
            dataDiv.appendChild(table);
            
            const hint = document.createElement('div');
            hint.style.fontSize = '8px';
            hint.style.color = '#888';
            hint.textContent = 'Нажми на ячейки с некорректными данными (пропуски, отрицательные числа, нереальный возраст)';
            dataDiv.appendChild(hint);
            
            container.appendChild(dataDiv);
            
            document.getElementById('checkPracticeBtn').onclick = () => {
                const uniqueSelected = [...new Set(practiceState.selectedCells)].length;
                practiceScore = uniqueSelected >= 4 ? 100 : Math.round((uniqueSelected / 4) * 100);
                submitPractice();
            };
            document.getElementById('checkPracticeBtn').style.display = 'block';
            document.getElementById('checkPracticeBtn').textContent = 'ОЧИСТИТЬ ДАННЫЕ';
        }
        
        // Port Scan
        function initPortScan(container) {
            const scanDiv = document.createElement('div');
            scanDiv.style.display = 'flex';
            scanDiv.style.flexDirection = 'column';
            scanDiv.style.gap = '15px';
            
            const portsGrid = document.createElement('div');
            portsGrid.style.display = 'grid';
            portsGrid.style.gridTemplateColumns = 'repeat(5, 1fr)';
            portsGrid.style.gap = '8px';
            
            practiceState.openPorts = [22, 80, 443];
            practiceState.foundPorts = [];
            
            for (let i = 1; i <= 20; i++) {
                const port = document.createElement('div');
                port.style.aspectRatio = '1';
                port.style.background = 'var(--border-color)';
                port.style.border = '3px solid #000';
                port.style.display = 'flex';
                port.style.alignItems = 'center';
                port.style.justifyContent = 'center';
                port.style.fontSize = '8px';
                port.style.cursor = 'pointer';
                port.textContent = i * 10 + Math.floor(Math.random() * 9);
                
                const isOpen = practiceState.openPorts.includes(parseInt(port.textContent));
                
                port.onclick = () => {
                    if (isOpen && !practiceState.foundPorts.includes(port.textContent)) {
                        practiceState.foundPorts.push(port.textContent);
                        port.style.background = 'var(--success)';
                        port.textContent = '✓';
                        
                        if (practiceState.foundPorts.length === 3) {
                            setTimeout(() => {
                                practiceScore = 100;
                                submitPractice();
                            }, 500);
                        }
                    } else if (!isOpen) {
                        port.style.background = '#ff6b6b';
                        setTimeout(() => {
                            port.style.background = 'var(--border-color)';
                        }, 300);
                    }
                };
                
                portsGrid.appendChild(port);
            }
            
            scanDiv.appendChild(portsGrid);
            
            const info = document.createElement('div');
            info.style.fontSize = '8px';
            info.style.textAlign = 'center';
            info.innerHTML = 'Найди открытые порты:<br>🔍 SSH (22), HTTP (80), HTTPS (443)';
            scanDiv.appendChild(info);
            
            container.appendChild(scanDiv);
            document.getElementById('checkPracticeBtn').style.display = 'none';
        }
        
        async function submitPractice() {
            const r = await fetch('/api/complete_practice', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({
                    user_id: uid,
                    prof_key: currentTaskProf,
                    task_id: currentPracticeTask.id,
                    score: practiceScore
                })
            });
            
            const d = await r.json();
            if (d.success) {
                state.coins = d.coins;
                state.xp = d.xp;
                state.level = d.level;
                state.tokens = d.tokens;
                
                closePractice();
                
                document.getElementById('resultScore').textContent = practiceScore + '%';
                document.getElementById('resultReward').textContent = `+${d.earned_coins} 🪙 +${d.earned_xp} XP`;
                document.getElementById('practiceResult').classList.add('show');
                
                updateUI();
            }
        }
        
        function closePracticeResult() {
            document.getElementById('practiceResult').classList.remove('show');
            openProfessionTasks(currentTaskProf);
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
                    <div class="task-desc">Нажми чтобы увидеть задания с практикой</div>
                `;
                card.onclick = () => openProfessionTasks(profKey);
                list.appendChild(card);
            });
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
