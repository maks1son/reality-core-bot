import os
import time
import random
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from database import init_db, get_user, save_user, get_character, save_character

app = FastAPI()

init_db()

# === API маршруты ===

@app.get("/api/state")
async def get_state(user_id: int):
    user = get_user(user_id)
    character = get_character(user_id)
    return {'user': user, 'character': character}

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
    # Создаём пользователя сразу
    save_user(data['user_id'], 0, 100, 1, 5, 0)
    return {'success': True}

@app.post("/api/tap")
async def do_tap(request: Request):
    data = await request.json()
    user_id = data.get('user_id')
    tap_count = data.get('tap_count', 0)
    timestamp = data.get('timestamp', 0)
    pattern = data.get('pattern', [])
    
    user = get_user(user_id)
    character = get_character(user_id)
    
    # Проверка энергии
    if user['energy'] < 1:
        return {'success': False, 'message': 'Недостаточно энергии!'}
    
    # === ЗАЩИТА ОТ АВТОКЛИКЕРОВ ===
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
            
            if min(intervals) < 80:
                return {'success': False, 'message': 'Слишком быстро!', 'cheat_detected': True}
    
    if len(set(pattern[-5:])) == 1 and len(pattern) >= 5:
        return {'success': False, 'message': 'Обнаружен бот!', 'cheat_detected': True}
    
    # === РАСЧЁТ НАГРАДЫ ===
    base_reward = 1
    
    if tap_count >= 100:
        multiplier = 2.0
    elif tap_count >= 50:
        multiplier = 1.5
    elif tap_count >= 30:
        multiplier = 1.3
    elif tap_count >= 10:
        multiplier = 1.1
    else:
        multiplier = 1.0
    
    luck_bonus = 0
    crit = False
    if character:
        luck = character.get('luck', 5)
        crit_chance = luck * 0.02
        if random.random() < crit_chance:
            crit = True
            luck_bonus = base_reward * multiplier
    
    total_reward = int(base_reward * multiplier + luck_bonus)
    
    # Обновление
    user['coins'] = user.get('coins', 0) + total_reward
    user['energy'] = max(0, user['energy'] - 1)
    user['total_taps'] = user.get('total_taps', 0) + 1
    
    save_user(
        user_id, 
        user['coins'], 
        user['energy'], 
        user['day'], 
        user['actions'],
        user['total_taps']
    )
    
    return {
        'success': True, 
        'reward': total_reward,
        'multiplier': multiplier,
        'crit': crit,
        'coins': user['coins'],
        'energy': user['energy'],
        'day': user['day'],
        'actions': user['actions']
    }

@app.post("/api/eat")
async def do_eat(request: Request):
    data = await request.json()
    user_id = data.get('user_id')
    
    user = get_user(user_id)
    
    if user['actions'] <= 0:
        return {'success': False, 'message': 'Нет действий!'}
    
    if user['coins'] < 50:
        return {'success': False, 'message': 'Недостаточно RC!'}
    
    user['coins'] -= 50
    user['energy'] = min(100, user['energy'] + 30)
    user['actions'] -= 1
    
    save_user(user_id, user['coins'], user['energy'], user['day'], user['actions'], user.get('total_taps', 0))
    
    return {
        'success': True, 
        'coins': user['coins'],
        'energy': user['energy'],
        'actions': user['actions'],
        'day': user['day']
    }

@app.post("/api/sleep")
async def do_sleep(request: Request):
    data = await request.json()
    user_id = data.get('user_id')
    
    user = get_user(user_id)
    
    rent = 100
    
    user['day'] = user['day'] + 1
    user['energy'] = 100
    user['actions'] = 5
    user['coins'] = max(0, user['coins'] - rent)
    
    save_user(user_id, user['coins'], user['energy'], user['day'], user['actions'], user.get('total_taps', 0))
    
    return {
        'success': True, 
        'coins': user['coins'],
        'energy': user['energy'],
        'day': user['day'],
        'actions': user['actions']
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
        
        /* ИГРА - НОВАЯ ВЕРСТКА */
        .game-screen {
            display: flex;
            flex-direction: column;
            height: 100%;
            gap: 10px;
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
        
        .player-name {
            font-size: 12px;
            color: var(--accent);
            text-shadow: 2px 2px 0px #000;
        }
        
        .day-badge {
            background: var(--warning);
            color: #000;
            padding: 6px 12px;
            font-size: 10px;
            box-shadow: 2px 2px 0px #b8a030;
        }
        
        /* Ресурсы в ряд */
        .resources-row {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr;
            gap: 8px;
        }
        
        .res-box {
            padding: 10px;
            text-align: center;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        
        .res-box.coins {
            background: linear-gradient(135deg, var(--panel-bg), #3d2b1e);
            border-color: var(--coin);
        }
        
        .res-icon {
            font-size: 14px;
        }
        
        .res-value {
            font-size: 14px;
            color: var(--success);
            font-weight: bold;
        }
        
        .res-value.coins {
            color: var(--coin);
            text-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
        }
        
        .res-label {
            font-size: 6px;
            color: #666;
            text-transform: uppercase;
        }
        
        /* Энергия */
        .energy-bar-container {
            height: 20px;
            position: relative;
            overflow: hidden;
        }
        
        .energy-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--danger) 0%, var(--warning) 50%, var(--success) 100%);
            transition: width 0.3s ease;
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
        
        /* Множители */
        .multiplier-row {
            display: flex;
            justify-content: center;
            gap: 6px;
            padding: 6px;
        }
        
        .multiplier-badge {
            padding: 6px 10px;
            font-size: 8px;
            background: var(--panel-bg);
            border: 2px solid var(--border-color);
            opacity: 0.4;
        }
        
        .multiplier-badge.active {
            opacity: 1;
            border-color: var(--warning);
            background: #3d3b1e;
            color: var(--warning);
            box-shadow: 0 0 8px rgba(255, 230, 109, 0.3);
        }
        
        /* ЦЕНТРАЛЬНАЯ ЗОНА ТАПА */
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
        }
        
        .hero-sprite {
            width: 100px;
            height: 100px;
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
            font-size: 16px;
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
        
        /* Комбо текст */
        .combo-text {
            position: absolute;
            top: -30px;
            font-size: 14px;
            color: var(--warning);
            text-shadow: 2px 2px 0px #000;
            opacity: 0;
            transition: all 0.3s;
            pointer-events: none;
        }
        
        .combo-text.show {
            opacity: 1;
            animation: comboPop 0.5s ease-out;
        }
        
        @keyframes comboPop {
            0% { transform: scale(0) rotate(-10deg); }
            50% { transform: scale(1.2) rotate(5deg); }
            100% { transform: scale(1) rotate(0deg); }
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
        
        /* Кнопки действий */
        .actions-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        
        .action-btn {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 15px 10px;
            gap: 8px;
            font-family: 'Press Start 2P', cursive;
            font-size: 10px;
            background: var(--panel-bg);
            border: 3px solid var(--border-color);
            box-shadow: 3px 3px 0px #000;
            color: var(--text);
            cursor: pointer;
            transition: all 0.1s;
        }
        
        .action-btn:active:not(:disabled) {
            transform: translate(2px, 2px);
            box-shadow: 1px 1px 0px #000;
        }
        
        .action-btn:disabled {
            opacity: 0.3;
            cursor: not-allowed;
        }
        
        .action-btn.danger {
            border-color: var(--danger);
        }
        
        .action-icon {
            font-size: 24px;
        }
        
        /* Предупреждение */
        .cheat-alert {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) scale(0);
            background: var(--danger);
            color: white;
            padding: 20px;
            border: 4px solid #000;
            box-shadow: 8px 8px 0px #000;
            font-size: 10px;
            text-align: center;
            z-index: 1000;
            transition: transform 0.3s;
        }
        
        .cheat-alert.show {
            transform: translate(-50%, -50%) scale(1);
        }
    </style>
</head>
<body>
    <!-- Предупреждение -->
    <div class="cheat-alert" id="cheatAlert">
        ⚠️ АВТОКЛИКЕР!<br>
        <span style="font-size: 7px;">Играй честно</span>
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
    <div class="container game-screen hidden" id="gameScreen">
        <!-- ВЕРХНЯЯ ПАНЕЛЬ -->
        <div class="top-panel">
            <div class="header-row pixel-box">
                <span class="player-name" id="displayName">HERO</span>
                <span class="day-badge">DAY <span id="displayDay">1</span></span>
            </div>
            
            <div class="resources-row">
                <div class="res-box pixel-box coins">
                    <div class="res-icon">🪙</div>
                    <div class="res-value coins" id="displayCoins">0</div>
                    <div class="res-label">REALITY COINS</div>
                </div>
                <div class="res-box pixel-box">
                    <div class="res-icon">⚡</div>
                    <div class="res-value" id="displayEnergy">100</div>
                    <div class="res-label">ENERGY</div>
                </div>
                <div class="res-box pixel-box">
                    <div class="res-icon">📅</div>
                    <div class="res-value" id="displayActions">5</div>
                    <div class="res-label">ACTIONS</div>
                </div>
            </div>
            
            <div class="energy-bar-container pixel-box">
                <div class="energy-fill" id="energyBar" style="width:100%"></div>
                <span class="energy-text" id="energyText">100/100</span>
            </div>
            
            <div class="multiplier-row pixel-box">
                <div class="multiplier-badge" id="mb1">x1.0</div>
                <div class="multiplier-badge" id="mb2">x1.1</div>
                <div class="multiplier-badge" id="mb3">x1.3</div>
                <div class="multiplier-badge" id="mb4">x1.5</div>
                <div class="multiplier-badge" id="mb5">x2.0</div>
            </div>
        </div>
        
        <!-- ЗОНА ТАПА -->
        <div class="tap-area" id="tapArea" onclick="handleTap(event)">
            <div class="hero-container" id="heroContainer">
                <div class="combo-text" id="comboText">COMBO!</div>
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
        
        <!-- КНОПКИ -->
        <div class="actions-row">
            <button class="action-btn" id="btnEat" onclick="doEat()">
                <span class="action-icon">🍜</span>
                <span>EAT (-50 RC)</span>
            </button>
            <button class="action-btn danger" id="btnSleep" onclick="doSleep()">
                <span class="action-icon">😴</span>
                <span>SLEEP (-100 RC)</span>
            </button>
        </div>
    </div>
    
    <script>
        let tg = window.Telegram.WebApp;
        tg.expand();
        
        let uid = tg.initDataUnsafe?.user?.id || 1;
        let state = {}, hero = {}, sel = '';
        let stats = {str:5, int:5, cha:5, lck:5};
        const MAX = 20, MIN = 1;
        
        let tapCount = 0;
        let tapPattern = [];
        let lastTapTime = 0;
        let isProcessing = false;
        
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
            document.getElementById('createScreen').classList.add('hidden');
            document.getElementById('gameScreen').classList.remove('hidden');
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
            
            tapCount = state.total_taps || 0;
            updateUI();
        }
        
        function updateUI() {
            document.getElementById('displayCoins').textContent = state.coins || 0;
            document.getElementById('displayDay').textContent = state.day || 1;
            document.getElementById('displayEnergy').textContent = state.energy || 0;
            document.getElementById('displayActions').textContent = state.actions || 0;
            
            let energyPct = (state.energy || 0);
            document.getElementById('energyBar').style.width = energyPct + '%';
            document.getElementById('energyText').textContent = (state.energy || 0) + '/100';
            
            // Множители
            document.querySelectorAll('.multiplier-badge').forEach(b => b.classList.remove('active'));
            if (tapCount >= 100) document.getElementById('mb5').classList.add('active');
            else if (tapCount >= 50) document.getElementById('mb4').classList.add('active');
            else if (tapCount >= 30) document.getElementById('mb3').classList.add('active');
            else if (tapCount >= 10) document.getElementById('mb2').classList.add('active');
            else document.getElementById('mb1').classList.add('active');
            
            // Кнопки
            document.getElementById('btnEat').disabled = (state.actions <= 0) || ((state.coins || 0) < 50);
            document.getElementById('btnSleep').disabled = false;
            
            // Зона тапа
            const tapArea = document.getElementById('tapArea');
            if ((state.energy || 0) <= 0) {
                tapArea.style.opacity = '0.5';
                tapArea.style.pointerEvents = 'none';
            } else {
                tapArea.style.opacity = '1';
                tapArea.style.pointerEvents = 'auto';
            }
        }
        
        async function handleTap(event) {
            if (isProcessing || (state.energy || 0) <= 0) return;
            
            const now = Date.now();
            if (now - lastTapTime < 80) {
                showCheatAlert();
                return;
            }
            
            isProcessing = true;
            lastTapTime = now;
            tapCount++;
            
            tapPattern.push(now);
            if (tapPattern.length > 10) tapPattern.shift();
            
            // Визуальный эффект
            createFloatingText(event);
            
            try {
                let r = await fetch('/api/tap', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({
                        user_id: uid,
                        tap_count: tapCount,
                        timestamp: now,
                        pattern: tapPattern
                    })
                });
                
                let res = await r.json();
                
                if (res.success) {
                    state.coins = res.coins;
                    state.energy = res.energy;
                    state.day = res.day;
                    state.actions = res.actions;
                    updateUI();
                    
                    if (res.multiplier > 1 || res.crit) {
                        showCombo(res.multiplier, res.crit);
                    }
                } else {
                    if (res.cheat_detected) {
                        showCheatAlert();
                        tapCount--;
                    }
                }
            } catch (e) {
                console.error('Error:', e);
            }
            
            isProcessing = false;
        }
        
        function createFloatingText(event) {
            const container = document.getElementById('heroContainer');
            const rect = container.getBoundingClientRect();
            
            const floatEl = document.createElement('div');
            floatEl.className = 'floating-reward';
            floatEl.textContent = '+1';
            floatEl.style.left = (event.clientX - rect.left) + 'px';
            floatEl.style.top = (event.clientY - rect.top - 50) + 'px';
            
            container.appendChild(floatEl);
            setTimeout(() => floatEl.remove(), 800);
        }
        
        function showCombo(multiplier, crit) {
            const comboEl = document.getElementById('comboText');
            let text = 'x' + multiplier;
            if (crit) text += ' 🍀';
            comboEl.textContent = text;
            comboEl.classList.add('show');
            setTimeout(() => comboEl.classList.remove('show'), 600);
        }
        
        function showCheatAlert() {
            const alert = document.getElementById('cheatAlert');
            alert.classList.add('show');
            setTimeout(() => alert.classList.remove('show'), 1500);
        }
        
        async function doEat() {
            if (state.actions <= 0 || state.coins < 50) return;
            
            try {
                let r = await fetch('/api/eat', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({user_id: uid})
                });
                let res = await r.json();
                if (res.success) {
                    state.coins = res.coins;
                    state.energy = res.energy;
                    state.actions = res.actions;
                    updateUI();
                }
            } catch (e) {
                console.error('Error:', e);
            }
        }
        
        async function doSleep() {
            try {
                let r = await fetch('/api/sleep', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({user_id: uid})
                });
                let res = await r.json();
                if (res.success) {
                    state.coins = res.coins;
                    state.energy = res.energy;
                    state.day = res.day;
                    state.actions = res.actions;
                    updateUI();
                }
            } catch (e) {
                console.error('Error:', e);
            }
        }
        
        async function init() {
            let r = await fetch(`/api/state?user_id=${uid}`);
            let d = await r.json();
            
            if(d.character) {
                document.getElementById('createScreen').classList.add('hidden');
                document.getElementById('gameScreen').classList.remove('hidden');
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
