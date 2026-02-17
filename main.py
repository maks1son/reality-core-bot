import os
import time
import random
import threading
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from database import init_db, get_user, save_user, get_character, save_character, get_professions, unlock_profession

app = FastAPI()

init_db()

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
                'last_energy_update': time.time()
            }
        return sessions[user_id]

# === API маршруты ===

@app.get("/api/state")
async def get_state(user_id: int):
    user = get_user(user_id)
    character = get_character(user_id)
    session = get_session(user_id)
    professions = get_professions(user_id)
    
    # Плавное восстановление энергии
    now = time.time()
    time_passed = now - session['last_energy_update']
    energy_recovered = int(time_passed * 2)  # 2 энергии в секунду
    
    if energy_recovered > 0 and user['energy'] < 100:
        old_energy = user['energy']
        user['energy'] = min(100, user['energy'] + energy_recovered)
        actual_recovered = user['energy'] - old_energy
        
        if actual_recovered > 0:
            save_user(user_id, user['coins'], user['energy'], user['xp'], user['level'], 
                     user['total_taps'], user['tokens'])
            session['last_energy_update'] = now
        else:
            session['last_energy_update'] = now
    
    # Проверка сброса комбо (5 секунд бездействия)
    afk_time = now - session['last_tap']
    combo_reset = afk_time > 5
    
    if combo_reset and session['combo_taps'] > 0:
        session['combo_taps'] = 0
        session['current_multiplier'] = 1.0
    
    # Проверка полного восстановления
    full_recovery = user['energy'] >= 100 and energy_recovered > 0
    
    return {
        'user': user, 
        'character': character,
        'professions': professions,
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
    character = get_character(user_id)
    session = get_session(user_id)
    session['last_tap'] = time.time()
    session['last_energy_update'] = time.time()
    
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
    luck_bonus = 0
    crit = False
    if character:
        luck = character.get('luck', 5)
        crit_chance = luck * 0.02
        if random.random() < crit_chance:
            crit = True
            luck_bonus = base_reward * multiplier
    
    total_reward = int(base_reward * multiplier + luck_bonus)
    
    # Опыт: 5 XP за каждый тап
    new_total_taps = user.get('total_taps', 0) + fingers
    xp_gained = fingers * 5
    new_xp = user.get('xp', 0) + xp_gained
    
    # Уровень: 50 XP для 2 уровня, далее +100 каждый уровень
    def xp_for_level(lvl):
        if lvl == 1:
            return 0
        elif lvl == 2:
            return 50
        else:
            return 50 + (lvl - 2) * 100
    
    new_level = user.get('level', 1)
    tokens_gained = 0
    level_up = False
    
    while new_xp >= xp_for_level(new_level + 1):
        new_level += 1
        level_up = True
        tokens_gained += 1  # 1 токен за уровень
    
    # Обновление
    user['coins'] = user.get('coins', 0) + total_reward
    user['energy'] = max(0, user['energy'] - fingers)
    user['total_taps'] = new_total_taps
    user['xp'] = new_xp
    user['level'] = new_level
    user['tokens'] = user.get('tokens', 0) + tokens_gained
    
    save_user(user_id, user['coins'], user['energy'], user['xp'], user['level'], 
             user['total_taps'], user['tokens'])
    
    # Проверка открытия профессий при достижении 2 уровня
    professions_unlocked = False
    if new_level >= 2 and user.get('level', 1) < 2:
        professions_unlocked = True
    
    return {
        'success': True, 
        'reward': total_reward,
        'multiplier': multiplier,
        'crit': crit,
        'coins': user['coins'],
        'energy': user['energy'],
        'xp': user['xp'],
        'level': user['level'],
        'xp_gained': xp_gained,
        'level_up': level_up,
        'tokens_gained': tokens_gained,
        'total_taps': user['total_taps'],
        'combo_taps': session['combo_taps'],
        'professions_unlocked': professions_unlocked
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

@app.get("/api/professions")
async def get_professions_data(user_id: int):
    professions = get_professions(user_id)
    return {'professions': professions}

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
        
        /* СОЗДАНИЕ */
        .create-screen {
            display: flex;
            flex-direction: column;
            height: 100%;
            gap: 8px;
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
        .hero-slot:hover { 
            transform: translate(-2px, -2px);
            box-shadow: 6px 6px 0px #000;
            border-color: var(--accent);
        }
        .hero-slot.selected { 
            border-color: var(--success);
            background: #0f3d3e;
            box-shadow: inset 3px 3px 0px #000;
            transform: translate(2px, 2px);
        }
        .slot-number {
            position: absolute;
            top: 5px;
            left: 5px;
            font-size: 10px;
            color: #666;
        }
        .hero-preview {
            width: 64px;
            height: 64px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 8px;
        }
        .hero-preview img {
            width: 64px;
            height: 64px;
            image-rendering: pixelated;
        }
        .slot-label {
            font-size: 8px;
            color: #8b7cb0;
            text-align: center;
        }
        .name-section {
            display: flex;
            gap: 8px;
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
        .stat-btn-mini:active {
            transform: translate(1px, 1px);
            box-shadow: 1px 1px 0px #000;
        }
        .stat-val {
            font-size: 12px;
            color: var(--success);
            min-width: 18px;
        }
        .points-bar {
            text-align: center;
            padding: 8px;
            border: 2px dashed var(--warning);
            color: var(--warning);
            font-size: 10px;
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
        
        /* ИГРА */
        .game-screen {
            display: flex;
            flex-direction: column;
            height: 100%;
            gap: 10px;
        }
        
        /* Кнопка профессий слева */
        .prof-btn-side {
            position: fixed;
            left: 0;
            top: 50%;
            transform: translateY(-50%);
            writing-mode: vertical-rl;
            text-orientation: mixed;
            padding: 15px 8px;
            background: var(--token);
            border: 3px solid #000;
            border-left: none;
            box-shadow: 3px 3px 0px rgba(0,0,0,0.5);
            color: white;
            font-family: 'Press Start 2P', cursive;
            font-size: 8px;
            cursor: pointer;
            z-index: 100;
            transition: all 0.2s;
        }
        .prof-btn-side:active {
            transform: translateY(-50%) translateX(2px);
        }
        .prof-btn-side.new {
            animation: pulse-border 1s infinite;
            background: var(--success);
        }
        @keyframes pulse-border {
            0%, 100% { box-shadow: 3px 3px 0px rgba(0,0,0,0.5), 0 0 10px var(--success); }
            50% { box-shadow: 3px 3px 0px rgba(0,0,0,0.5), 0 0 20px var(--success); }
        }
        
        /* ВЕРХНЯЯ ПАНЕЛЬ */
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
        
        .player-info {
            display: flex;
            flex-direction: column;
            gap: 4px;
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
            position: relative;
        }
        
        .xp-fill {
            height: 100%;
            background: var(--xp);
            transition: width 0.3s;
        }
        
        /* Ресурсы */
        .resources-row {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 8px;
        }
        
        .res-box {
            padding: 8px;
            text-align: center;
            display: flex;
            flex-direction: column;
            gap: 3px;
        }
        
        .res-box.coins {
            background: linear-gradient(135deg, var(--panel-bg), #3d2b1e);
            border-color: var(--coin);
        }
        
        .res-box.tokens {
            background: linear-gradient(135deg, var(--panel-bg), #1e3d5c);
            border-color: var(--token);
        }
        
        .res-icon {
            font-size: 12px;
        }
        
        .res-value {
            font-size: 12px;
            color: var(--success);
            font-weight: bold;
        }
        
        .res-value.coins {
            color: var(--coin);
            text-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
        }
        
        .res-value.tokens {
            color: var(--token);
            text-shadow: 0 0 10px rgba(52, 152, 219, 0.3);
        }
        
        .res-label {
            font-size: 5px;
            color: #666;
            text-transform: uppercase;
        }
        
        /* Энергия */
        .energy-section {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        
        .energy-bar-container {
            height: 20px;
            position: relative;
            overflow: hidden;
        }
        
        .energy-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--danger) 0%, var(--warning) 50%, var(--success) 100%);
            transition: width 0.5s ease;
        }
        
        .energy-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 10px;
            text-shadow: 2px 2px 0px #000;
            color: white;
        }
        
        .recovery-status {
            text-align: center;
            font-size: 7px;
            color: var(--success);
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .recovery-status.show {
            opacity: 1;
        }
        
        /* Множители */
        .multiplier-row {
            display: flex;
            justify-content: center;
            gap: 3px;
            padding: 6px;
            flex-wrap: wrap;
        }
        
        .multiplier-badge {
            padding: 3px 5px;
            font-size: 6px;
            background: var(--panel-bg);
            border: 2px solid var(--border-color);
            opacity: 0.3;
        }
        
        .multiplier-badge.active {
            opacity: 1;
            border-color: var(--warning);
            background: #3d3b1e;
            color: var(--warning);
        }
        
        .multiplier-badge.current {
            animation: glow 1s ease-in-out infinite alternate;
        }
        
        @keyframes glow {
            from { box-shadow: 0 0 5px var(--warning); }
            to { box-shadow: 0 0 15px var(--warning); }
        }
        
        /* ЗОНА ТАПА */
        .tap-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            position: relative;
            min-height: 0;
        }
        
        .hero-container {
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 15px;
            cursor: pointer;
            padding: 20px;
            touch-action: manipulation;
        }
        
        .hero-sprite {
            width: 80px;
            height: 80px;
            animation: breathe 2s ease-in-out infinite;
            filter: drop-shadow(4px 4px 0px #000);
            pointer-events: none;
        }
        
        @keyframes breathe {
            0%, 100% { transform: translateY(0) scale(1); }
            50% { transform: translateY(-6px) scale(1.02); }
        }
        
        .tap-hint {
            font-size: 8px;
            color: var(--warning);
            opacity: 0.7;
            animation: pulse 1.5s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 0.7; }
            50% { opacity: 1; }
        }
        
        /* Плавающие числа */
        .floating-reward {
            position: absolute;
            font-size: 14px;
            font-weight: bold;
            color: var(--coin);
            text-shadow: 2px 2px 0px #000;
            pointer-events: none;
            animation: floatUp 0.8s ease-out forwards;
            z-index: 100;
        }
        
        @keyframes floatUp {
            0% { opacity: 1; transform: translateY(0) scale(1); }
            100% { opacity: 0; transform: translateY(-40px) scale(1.3); }
        }
        
        /* Характеристики */
        .stats-row {
            display: flex;
            justify-content: center;
            gap: 20px;
            padding: 8px;
            font-size: 10px;
        }
        
        .stat-item {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        /* Модальные окна */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        
        .modal-overlay.show {
            display: flex;
        }
        
        .modal-content {
            background: var(--panel-bg);
            border: 4px solid var(--border-color);
            box-shadow: 8px 8px 0px #000;
            padding: 20px;
            max-width: 350px;
            width: 90%;
            text-align: center;
        }
        
        .modal-title {
            font-size: 12px;
            color: var(--success);
            margin-bottom: 15px;
            text-shadow: 2px 2px 0px #000;
        }
        
        .modal-text {
            font-size: 8px;
            color: var(--text);
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
        
        .modal-btn:active {
            transform: translate(2px, 2px);
            box-shadow: 2px 2px 0px #2d8b84;
        }
        
        /* Страница профессий */
        .professions-screen {
            display: none;
            flex-direction: column;
            height: 100%;
            gap: 10px;
        }
        
        .professions-screen.show {
            display: flex;
        }
        
        .prof-header {
            text-align: center;
            padding: 10px;
        }
        
        .prof-header h2 {
            font-size: 12px;
            color: var(--token);
        }
        
        .tokens-display {
            display: flex;
            justify-content: center;
            gap: 10px;
            padding: 10px;
        }
        
        .token-badge {
            padding: 8px 15px;
            background: linear-gradient(135deg, var(--panel-bg), #1e3d5c);
            border: 2px solid var(--token);
            color: var(--token);
            font-size: 10px;
        }
        
        .professions-grid {
            flex: 1;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            padding: 10px;
            overflow-y: auto;
        }
        
        .profession-node {
            aspect-ratio: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 10px;
            cursor: pointer;
            transition: all 0.2s;
            position: relative;
        }
        
        .profession-node.locked {
            opacity: 0.4;
            cursor: not-allowed;
            filter: grayscale(1);
        }
        
        .profession-node.available {
            border-color: var(--success);
            animation: pulse-available 2s infinite;
        }
        
        @keyframes pulse-available {
            0%, 100% { box-shadow: 0 0 5px var(--success); }
            50% { box-shadow: 0 0 15px var(--success); }
        }
        
        .profession-node.unlocked {
            border-color: var(--token);
            background: linear-gradient(135deg, var(--panel-bg), #1e3d5c);
        }
        
        .prof-icon {
            font-size: 32px;
        }
        
        .prof-name {
            font-size: 8px;
            text-align: center;
        }
        
        .prof-cost {
            font-size: 6px;
            color: var(--token);
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
        
        /* Уведомления */
        .toast {
            position: fixed;
            top: 20%;
            left: 50%;
            transform: translateX(-50%) scale(0);
            padding: 10px 20px;
            border: 3px solid #000;
            box-shadow: 4px 4px 0px #000;
            font-size: 8px;
            z-index: 999;
            transition: transform 0.3s;
        }
        
        .toast.show {
            transform: translateX(-50%) scale(1);
        }
        
        .toast.success {
            background: var(--success);
            color: #000;
        }
        
        .toast.warning {
            background: var(--warning);
            color: #000;
        }
    </style>
</head>
<body>
    <!-- Уведомления -->
    <div class="toast success" id="toast">Энергия восстановлена!</div>
    
    <!-- Модальное окно открытия профессий -->
    <div class="modal-overlay" id="unlockModal">
        <div class="modal-content">
            <div class="modal-title">🎉 ОТКРЫТ ВЫБОР ПРОФЕССИЙ!</div>
            <div class="modal-text">
                Поздравляем с достижением 2 уровня!<br><br>
                Теперь ты можешь исследовать различные профессии и найти своё призвание.<br><br>
                Получено: <span style="color: var(--token);">1 ТОКЕН ИССЛЕДОВАНИЯ</span>
            </div>
            <button class="modal-btn" onclick="goToProfessions()">ПРОДОЛЖИТЬ ➤</button>
        </div>
    </div>

    <!-- СОЗДАНИЕ -->
    <div class="container create-screen" id="createScreen">
        <div class="create-header">
            <h1>◆ RE:ALITY ◆</h1>
            <p>CHOOSE YOUR CHARACTER</p>
        </div>
        
        <div class="heroes-select">
            <div class="section-label">◆ SELECT HERO ◆</div>
            
            <div class="heroes-trio">
                <div class="hero-slot" data-slot="1" data-avatar="hero1">
                    <span class="slot-number">1</span>
                    <div class="hero-preview">
                        <img src="/hero1.png" alt="Hero 1">
                    </div>
                    <div class="slot-label">HERO 1</div>
                </div>
                
                <div class="hero-slot" data-slot="2" data-avatar="hero2">
                    <span class="slot-number">2</span>
                    <div class="hero-preview">
                        <img src="/hero2.png" alt="Hero 2">
                    </div>
                    <div class="slot-label">HERO 2</div>
                </div>
                
                <div class="hero-slot" data-slot="3" data-avatar="hero3">
                    <span class="slot-number">3</span>
                    <div class="hero-preview">
                        <img src="/hero3.png" alt="Hero 3">
                    </div>
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
        
        <button class="start-btn" id="startBtn" onclick="create()" disabled>
            START ▶
        </button>
    </div>
    
    <!-- ИГРА -->
    <div class="container game-screen" id="gameScreen" style="display: none;">
        <!-- Кнопка профессий -->
        <button class="prof-btn-side" id="profBtn" onclick="openProfessions()">
            ПРОФЕССИИ
        </button>
        
        <!-- ВЕРХНЯЯ ПАНЕЛЬ -->
        <div class="top-panel">
            <div class="header-row pixel-box">
                <div class="player-info">
                    <span class="player-name" id="displayName">HERO</span>
                    <span class="player-level">LVL <span id="displayLevel">1</span></span>
                </div>
                <div class="xp-bar-container">
                    <div class="xp-fill" id="xpBar" style="width:0%"></div>
                </div>
            </div>
            
            <div class="resources-row">
                <div class="res-box pixel-box coins">
                    <div class="res-icon">🪙</div>
                    <div class="res-value coins" id="displayCoins">0</div>
                    <div class="res-label">REALITY COINS</div>
                </div>
                <div class="res-box pixel-box tokens">
                    <div class="res-icon">🔷</div>
                    <div class="res-value tokens" id="displayTokens">0</div>
                    <div class="res-label">ТОКЕНЫ</div>
                </div>
                <div class="res-box pixel-box">
                    <div class="res-icon">⚡</div>
                    <div class="res-value" id="displayEnergy">100</div>
                    <div class="res-label">ENERGY</div>
                </div>
            </div>
            
            <div class="energy-section">
                <div class="energy-bar-container pixel-box">
                    <div class="energy-fill" id="energyBar" style="width:100%"></div>
                    <span class="energy-text" id="energyText">100/100</span>
                </div>
                <div class="recovery-status" id="recoveryStatus">⚡ ЭНЕРГИЯ ВОССТАНОВЛЕНА</div>
            </div>
            
            <div class="multiplier-row pixel-box" id="multiplierRow">
                <div class="multiplier-badge" data-m="1.0">x1.0</div>
                <div class="multiplier-badge" data-m="1.1">x1.1</div>
                <div class="multiplier-badge" data-m="1.2">x1.2</div>
                <div class="multiplier-badge" data-m="1.3">x1.3</div>
                <div class="multiplier-badge" data-m="1.4">x1.4</div>
                <div class="multiplier-badge" data-m="1.5">x1.5</div>
                <div class="multiplier-badge" data-m="1.6">x1.6</div>
                <div class="multiplier-badge" data-m="1.7">x1.7</div>
                <div class="multiplier-badge" data-m="1.8">x1.8</div>
                <div class="multiplier-badge" data-m="1.9">x1.9</div>
                <div class="multiplier-badge" data-m="2.0">x2.0+</div>
            </div>
        </div>
        
        <!-- ЗОНА ТАПА -->
        <div class="tap-area" id="tapArea">
            <div class="hero-container" id="heroContainer">
                <img src="/hero1.png" alt="Hero" class="hero-sprite" id="gameHero">
                <div class="tap-hint">👆 ТАПАЙ ПО ПЕРСОНАЖУ</div>
            </div>
        </div>
        
        <!-- ХАРАКТЕРИСТИКИ -->
        <div class="stats-row pixel-box">
            <span class="stat-item">💪 <span id="statStr">5</span></span>
            <span class="stat-item">🧠 <span id="statInt">5</span></span>
            <span class="stat-item">✨ <span id="statCha">5</span></span>
            <span class="stat-item">🍀 <span id="statLck">5</span></span>
        </div>
    </div>
    
    <!-- СТРАНИЦА ПРОФЕССИЙ -->
    <div class="container professions-screen" id="professionsScreen">
        <div class="prof-header pixel-box">
            <h2>◆ ПРОФЕССИИ ◆</h2>
        </div>
        
        <div class="tokens-display">
            <div class="token-badge">
                🔷 ТОКЕНОВ: <span id="profTokens">0</span>
            </div>
        </div>
        
        <div class="professions-grid" id="professionsGrid">
            <!-- IT - доступно сразу -->
            <div class="profession-node unlocked pixel-box" onclick="exploreProfession('it')">
                <div class="prof-icon">💻</div>
                <div class="prof-name">СФЕРА IT</div>
                <div class="prof-cost">ОТКРЫТО</div>
            </div>
            
            <!-- Остальные закрыты -->
            <div class="profession-node locked pixel-box">
                <div class="prof-icon">🔒</div>
                <div class="prof-name">МЕДИЦИНА</div>
                <div class="prof-cost">1 ТОКЕН</div>
            </div>
            
            <div class="profession-node locked pixel-box">
                <div class="prof-icon">🔒</div>
                <div class="prof-name">ИНЖЕНЕРИЯ</div>
                <div class="prof-cost">1 ТОКЕН</div>
            </div>
            
            <div class="profession-node locked pixel-box">
                <div class="prof-icon">🔒</div>
                <div class="prof-name">ИСКУССТВО</div>
                <div class="prof-cost">1 ТОКЕН</div>
            </div>
            
            <div class="profession-node locked pixel-box">
                <div class="prof-icon">🔒</div>
                <div class="prof-name">БИЗНЕС</div>
                <div class="prof-cost">1 ТОКЕН</div>
            </div>
            
            <div class="profession-node locked pixel-box">
                <div class="prof-icon">🔒</div>
                <div class="prof-name">НАУКА</div>
                <div class="prof-cost">1 ТОКЕН</div>
            </div>
        </div>
        
        <button class="back-btn" onclick="backToGame()">◀ НАЗАД</button>
    </div>
    
    <script>
        let tg = window.Telegram.WebApp;
        tg.expand();
        
        let uid = tg.initDataUnsafe?.user?.id || 1;
        let state = {}, hero = {}, sel = '';
        let stats = {str:5, int:5, cha:5, lck:5};
        const MAX = 20, MIN = 1;
        
        let tapPattern = [];
        let lastTapTime = 0;
        let isProcessing = false;
        let currentMultiplier = 1.0;
        let lastAfkCheck = 0;
        let professionsUnlockedShown = false;
        
        const multipliers = [1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0];
        const thresholds = [5, 15, 30, 50, 75, 105, 140, 180, 225, 300];
        
        document.querySelectorAll('.hero-slot').forEach(el => {
            el.onclick = function() {
                document.querySelectorAll('.hero-slot').forEach(h => h.classList.remove('selected'));
                this.classList.add('selected');
                sel = this.dataset.avatar;
                let slotNum = this.dataset.slot;
                document.getElementById('gameHero').src = '/hero' + slotNum + '.png';
                check();
            };
        });
        
        function chg(s, d) {
            let cur = stats[s];
            let used = Object.values(stats).reduce((a,b)=>a+b,0);
            let left = MAX - used;
            if (d>0 && left<=0) return;
            if (d<0 && cur<=MIN) return;
            stats[s] += d;
            document.getElementById(s).textContent = stats[s];
            upd();
            check();
        }
        
        function upd() {
            let used = Object.values(stats).reduce((a,b)=>a+b,0);
            document.getElementById('pts').textContent = MAX - used;
            document.querySelectorAll('.stat-btn-mini').forEach(b => {
                b.disabled = (b.textContent=='+' && MAX-used<=0);
            });
        }
        
        function check() {
            let name = document.getElementById('charName').value.trim();
            let used = Object.values(stats).reduce((a,b)=>a+b,0);
            document.getElementById('startBtn').disabled = !(name && sel && used==MAX);
        }
        
        document.getElementById('charName').oninput = check;
        
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
            document.getElementById('createScreen').style.display = 'none';
            document.getElementById('gameScreen').style.display = 'flex';
            load();
        }
        
        async function load() {
            let r = await fetch(`/api/state?user_id=${uid}`);
            let d = await r.json();
            state = d.user; 
            hero = d.character;
            
            let heroNum = hero.avatar.replace('hero', '') || '1';
            document.getElementById('gameHero').src = '/hero' + heroNum + '.png';
            
            document.getElementById('displayName').textContent = hero.name.toUpperCase();
            document.getElementById('statStr').textContent = hero.strength;
            document.getElementById('statInt').textContent = hero.intelligence;
            document.getElementById('statCha').textContent = hero.charisma;
            document.getElementById('statLck').textContent = hero.luck;
            
            currentMultiplier = d.session.current_multiplier;
            
            updateUI();
            
            // Показываем уведомление о полном восстановлении
            if (d.full_recovery) {
                showRecovery();
            }
            
            setInterval(checkAfk, 1000);
        }
        
        function updateUI() {
            document.getElementById('displayCoins').textContent = state.coins || 0;
            document.getElementById('displayTokens').textContent = state.tokens || 0;
            document.getElementById('displayEnergy').textContent = state.energy || 0;
            document.getElementById('displayLevel').textContent = state.level || 1;
            
            // XP: для 1→2 нужно 50 XP, потом +100 каждый уровень
            let xpForNext = state.level === 1 ? 50 : 50 + (state.level - 1) * 100;
            let xpInLevel = (state.xp || 0) - ((state.level - 1) * 50 + Math.max(0, state.level - 2) * 50);
            if (state.level === 1) xpInLevel = state.xp || 0;
            let xpPercent = Math.min(100, (xpInLevel / xpForNext) * 100);
            document.getElementById('xpBar').style.width = xpPercent + '%';
            
            let energyPct = state.energy || 0;
            document.getElementById('energyBar').style.width = energyPct + '%';
            document.getElementById('energyText').textContent = (state.energy || 0) + '/100';
            
            // Множители
            document.querySelectorAll('.multiplier-badge').forEach(badge => {
                badge.classList.remove('active', 'current');
                let m = parseFloat(badge.dataset.m);
                if (currentMultiplier >= m) {
                    badge.classList.add('active');
                }
                if (Math.abs(currentMultiplier - m) < 0.05 || (currentMultiplier >= 2.0 && m === 2.0)) {
                    badge.classList.add('current');
                }
            });
            
            // Зона тапа
            const tapArea = document.getElementById('tapArea');
            if ((state.energy || 0) <= 0) {
                tapArea.style.opacity = '0.4';
                tapArea.style.pointerEvents = 'none';
                document.querySelector('.tap-hint').textContent = '⚡ НЕТ ЭНЕРГИИ';
            } else {
                tapArea.style.opacity = '1';
                tapArea.style.pointerEvents = 'auto';
                document.querySelector('.tap-hint').textContent = '👆 ТАПАЙ ПО ПЕРСОНАЖУ';
            }
            
            // Подсветка кнопки профессий если есть токены
            const profBtn = document.getElementById('profBtn');
            if ((state.tokens || 0) > 0) {
                profBtn.classList.add('new');
            } else {
                profBtn.classList.remove('new');
            }
        }
        
        function showRecovery() {
            const status = document.getElementById('recoveryStatus');
            status.classList.add('show');
            setTimeout(() => status.classList.remove('show'), 3000);
            
            const toast = document.getElementById('toast');
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2000);
        }
        
        async function checkAfk() {
            let now = Date.now();
            if (now - lastAfkCheck < 2000) return;
            lastAfkCheck = now;
            
            let r = await fetch(`/api/state?user_id=${uid}`);
            let d = await r.json();
            
            // Обновляем энергию
            if (d.user.energy !== state.energy) {
                state.energy = d.user.energy;
                updateUI();
            }
            
            // Показываем полное восстановление
            if (d.full_recovery && state.energy >= 100) {
                showRecovery();
            }
            
            // Сброс комбо
            if (d.combo_reset) {
                currentMultiplier = 1.0;
                updateUI();
            }
        }
        
        // === ОБРАБОТКА ТАПОВ ===
        const heroContainer = document.getElementById('heroContainer');
        
        heroContainer.addEventListener('touchstart', handleTouch, {passive: false});
        heroContainer.addEventListener('click', handleClick);
        
        function handleTouch(e) {
            e.preventDefault();
            const touches = e.touches;
            const fingers = touches.length;
            
            for (let i = 0; i < fingers; i++) {
                const touch = touches[i];
                processTap(touch.clientX, touch.clientY, fingers);
            }
        }
        
        function handleClick(e) {
            processTap(e.clientX, e.clientY, 1);
        }
        
        async function processTap(clientX, clientY, fingers) {
            if (isProcessing || (state.energy || 0) < fingers) return;
            
            const now = Date.now();
            if (now - lastTapTime < 60) return;
            
            isProcessing = true;
            lastTapTime = now;
            
            tapPattern.push(now);
            if (tapPattern.length > 10) tapPattern.shift();
            
            createFloatingText(clientX, clientY, fingers);
            
            try {
                let r = await fetch('/api/tap', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({
                        user_id: uid,
                        timestamp: now,
                        pattern: tapPattern,
                        fingers: fingers
                    })
                });
                
                let res = await r.json();
                
                if (res.success) {
                    state.coins = res.coins;
                    state.energy = res.energy;
                    state.xp = res.xp;
                    state.level = res.level;
                    state.tokens = res.tokens;
                    currentMultiplier = res.multiplier;
                    
                    updateUI();
                    
                    // Показываем окно профессий при достижении 2 уровня
                    if (res.level_up && res.level === 2 && !professionsUnlockedShown) {
                        professionsUnlockedShown = true;
                        document.getElementById('unlockModal').classList.add('show');
                    }
                } else if (res.cheat_detected) {
                    showCheatAlert();
                }
            } catch (e) {
                console.error('Error:', e);
            }
            
            isProcessing = false;
        }
        
        function createFloatingText(x, y, fingers) {
            const container = document.getElementById('heroContainer');
            const rect = container.getBoundingClientRect();
            
            const floatEl = document.createElement('div');
            floatEl.className = 'floating-reward';
            floatEl.textContent = '+' + fingers;
            floatEl.style.left = (x - rect.left) + 'px';
            floatEl.style.top = (y - rect.top - 40) + 'px';
            
            container.appendChild(floatEl);
            setTimeout(() => floatEl.remove(), 800);
        }
        
        function showCheatAlert() {
            // Просто игнорируем читерские клики без показа окна
        }
        
        // === НАВИГАЦИЯ ===
        
        function openProfessions() {
            document.getElementById('gameScreen').style.display = 'none';
            document.getElementById('professionsScreen').classList.add('show');
            document.getElementById('profTokens').textContent = state.tokens || 0;
        }
        
        function backToGame() {
            document.getElementById('professionsScreen').classList.remove('show');
            document.getElementById('gameScreen').style.display = 'flex';
        }
        
        function goToProfessions() {
            document.getElementById('unlockModal').classList.remove('show');
            openProfessions();
        }
        
        function exploreProfession(prof) {
            if (prof === 'it') {
                alert('IT Сфера: Программист, DevOps, Data Scientist, UX/UI дизайнер...');
            }
        }
        
        async function init() {
            let r = await fetch(`/api/state?user_id=${uid}`);
            let d = await r.json();
            
            if(d.character) {
                document.getElementById('createScreen').style.display = 'none';
                document.getElementById('gameScreen').style.display = 'flex';
                load();
            } else {
                upd();
            }
        }
        
        init();
    </script>
</body>
</html>"""

@app.get("/hero1.png")
async def hero1():
    return FileResponse("hero1.png")

@app.get("/hero2.png")
async def hero2():
    return FileResponse("hero2.png")

@app.get("/hero3.png")
async def hero3():
    return FileResponse("hero3.png")
