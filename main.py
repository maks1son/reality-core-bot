import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from database import init_db, get_user, save_user, get_character, save_character

app = FastAPI()

init_db()
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    return {'success': True}

@app.post("/api/action")
async def do_action(request: Request):
    data = await request.json()
    user_id = data.get('user_id')
    action = data.get('action')
    
    user = get_user(user_id)
    character = get_character(user_id)
    
    # Бонусы от характеристик
    work_bonus = character['strength'] * 50 if character else 0
    luck_chance = character['luck'] * 0.02 if character else 0
    
    import random
    lucky = random.random() < luck_chance
    
    if action == 'work' and user['actions'] > 0 and user['energy'] >= 30:
        bonus = work_bonus if lucky else 0
        user['money'] += 1500 + bonus
        user['energy'] -= 30
        user['actions'] -= 1
        save_user(user_id, user['money'], user['energy'], user['day'], user['actions'])
        msg = f'Поработал. +{1500 + bonus}₽, -30⚡'
        if lucky:
            msg += ' 💎 Бонус за силу!'
        return {'success': True, 'message': msg, 'state': user}
    
    elif action == 'eat' and user['actions'] > 0:
        user['money'] -= 200
        user['energy'] = min(100, user['energy'] + 20)
        user['actions'] -= 1
        save_user(user_id, user['money'], user['energy'], user['day'], user['actions'])
        return {'success': True, 'message': 'Поел. +20⚡, -200₽', 'state': user}
    
    elif action == 'sleep':
        user['day'] += 1
        user['energy'] = 100
        user['actions'] = 3
        user['money'] -= 700
        save_user(user_id, user['money'], user['energy'], user['day'], user['actions'])
        return {'success': True, 'message': 'Новый день! Расходы: 700₽', 'state': user}
    
    return {'success': False, 'message': 'Недостаточно действий или энергии'}

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RE:ALITY: Core</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet">
        <style>
            * { 
                margin: 0; 
                padding: 0; 
                box-sizing: border-box; 
                image-rendering: pixelated;
                image-rendering: crisp-edges;
            }
            
            :root {
                --bg-color: #2d1b4e;
                --panel-bg: #1a0f2e;
                --border-color: #4a3b6b;
                --accent: #ff6b9d;
                --accent-dark: #c44569;
                --success: #4ecdc4;
                --warning: #ffe66d;
                --danger: #ff6b6b;
                --text: #f7f1e3;
                --shadow: 4px 4px 0px #1a0f2e;
            }
            
            body {
                font-family: 'Press Start 2P', cursive;
                background: var(--bg-color);
                min-height: 100vh;
                color: var(--text);
                padding: 15px;
                font-size: 10px;
                line-height: 1.6;
            }
            
            .container { 
                max-width: 380px; 
                margin: 0 auto; 
            }
            
            .hidden { display: none !important; }
            
            /* Пиксельные боксы */
            .pixel-box {
                background: var(--panel-bg);
                border: 4px solid var(--border-color);
                box-shadow: var(--shadow);
                position: relative;
            }
            
            .pixel-box::before {
                content: '';
                position: absolute;
                top: -4px; left: -4px; right: -4px; bottom: -4px;
                border: 2px solid var(--accent);
                pointer-events: none;
                opacity: 0;
                transition: opacity 0.2s;
            }
            
            .pixel-box:hover::before {
                opacity: 1;
            }
            
            /* Экран создания */
            .create-screen { text-align: center; }
            
            .create-screen h1 { 
                font-size: 16px; 
                color: var(--accent);
                text-shadow: 3px 3px 0px var(--accent-dark);
                margin-bottom: 15px;
                animation: blink 2s infinite;
            }
            
            @keyframes blink {
                0%, 50% { opacity: 1; }
                51%, 100% { opacity: 0.8; }
            }
            
            .create-screen h2 { 
                font-size: 10px; 
                color: var(--warning);
                margin: 20px 0 10px;
            }
            
            /* Аватары пиксельные */
            .avatars {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 8px;
                margin: 15px 0;
            }
            
            .avatar-option {
                font-size: 32px;
                padding: 15px 10px;
                background: var(--panel-bg);
                border: 4px solid var(--border-color);
                box-shadow: var(--shadow);
                cursor: pointer;
                transition: all 0.1s;
                image-rendering: pixelated;
            }
            
            .avatar-option:hover { 
                transform: translate(-2px, -2px);
                box-shadow: 6px 6px 0px #1a0f2e;
                border-color: var(--accent);
            }
            
            .avatar-option.selected { 
                border-color: var(--success);
                background: #0f3d3e;
                box-shadow: inset 4px 4px 0px #000;
                transform: translate(2px, 2px);
            }
            
            /* Пиксельный инпут */
            .name-input {
                width: 100%;
                padding: 15px;
                font-family: 'Press Start 2P', cursive;
                font-size: 10px;
                background: var(--panel-bg);
                border: 4px solid var(--border-color);
                box-shadow: var(--shadow);
                color: var(--text);
                margin: 10px 0;
                outline: none;
            }
            
            .name-input:focus {
                border-color: var(--accent);
            }
            
            .name-input::placeholder { 
                color: #6b5b8a; 
            }
            
            /* Статистики создания */
            .stats-create {
                background: var(--panel-bg);
                border: 4px solid var(--border-color);
                box-shadow: var(--shadow);
                padding: 15px;
                margin: 15px 0;
            }
            
            .stat-row-create {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin: 12px 0;
                font-size: 8px;
            }
            
            .stat-name {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .stat-icon {
                font-size: 16px;
            }
            
            .stat-controls {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .stat-btn {
                width: 28px;
                height: 28px;
                font-family: 'Press Start 2P', cursive;
                font-size: 12px;
                background: var(--accent);
                border: none;
                box-shadow: 3px 3px 0px var(--accent-dark);
                color: white;
                cursor: pointer;
                transition: all 0.1s;
            }
            
            .stat-btn:active {
                transform: translate(2px, 2px);
                box-shadow: 1px 1px 0px var(--accent-dark);
            }
            
            .stat-btn:disabled { 
                opacity: 0.3; 
                cursor: not-allowed;
                box-shadow: none;
            }
            
            .stat-value { 
                font-size: 12px; 
                min-width: 25px;
                color: var(--success);
            }
            
            .points-left { 
                margin-top: 15px; 
                font-size: 10px; 
                color: var(--warning);
                text-align: center;
                padding: 10px;
                background: rgba(255, 230, 109, 0.1);
                border: 2px dashed var(--warning);
            }
            
            /* Пиксельная кнопка */
            .pixel-btn {
                width: 100%;
                padding: 20px;
                margin-top: 20px;
                font-family: 'Press Start 2P', cursive;
                font-size: 12px;
                background: var(--success);
                border: none;
                box-shadow: 4px 4px 0px #2d8b84;
                color: #1a0f2e;
                cursor: pointer;
                transition: all 0.1s;
                text-transform: uppercase;
            }
            
            .pixel-btn:hover {
                transform: translate(-2px, -2px);
                box-shadow: 6px 6px 0px #2d8b84;
            }
            
            .pixel-btn:active {
                transform: translate(2px, 2px);
                box-shadow: 2px 2px 0px #2d8b84;
            }
            
            .pixel-btn:disabled { 
                opacity: 0.4;
                cursor: not-allowed;
                transform: none;
                box-shadow: 4px 4px 0px #2d8b84;
                background: #6b5b8a;
            }
            
            /* Экран игры */
            .game-screen { }
            
            .header { 
                text-align: center; 
                margin-bottom: 15px; 
            }
            
            .header h1 { 
                font-size: 14px; 
                color: var(--accent);
                text-shadow: 2px 2px 0px var(--accent-dark);
            }
            
            .day-counter {
                font-size: 10px;
                color: var(--warning);
                margin-top: 5px;
            }
            
            /* Карточка персонажа */
            .character-card {
                display: flex;
                align-items: center;
                                gap: 12px;
                background: var(--panel-bg);
                border: 4px solid var(--border-color);
                box-shadow: var(--shadow);
                padding: 12px;
                margin-bottom: 15px;
            }
            
            .character-avatar { 
                font-size: 40px;
                width: 60px;
                height: 60px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #0f3d3e;
                border: 3px solid var(--success);
                image-rendering: pixelated;
            }
            
            .character-info { flex: 1; }
            
            .character-name { 
                font-size: 12px; 
                color: var(--accent);
                margin-bottom: 5px;
            }
            
            .character-stats { 
                font-size: 8px; 
                color: #8b7cb0;
                line-height: 1.8;
            }
            
            /* Статус бар */
            .status-panel {
                background: var(--panel-bg);
                border: 4px solid var(--border-color);
                box-shadow: var(--shadow);
                padding: 15px;
                margin-bottom: 15px;
            }
            
            .stat-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin: 10px 0;
                font-size: 10px;
            }
            
            .stat-label {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .stat-bar {
                width: 100px;
                height: 12px;
                background: #1a0f2e;
                border: 2px solid var(--border-color);
                position: relative;
            }
            
            .stat-bar-fill {
                height: 100%;
                background: var(--success);
                transition: width 0.3s;
                box-shadow: inset 0 0 0 2px rgba(255,255,255,0.2);
            }
            
            .stat-bar-fill.low { background: var(--danger); }
            .stat-bar-fill.medium { background: var(--warning); }
            
            .stat-text {
                font-size: 10px;
                min-width: 60px;
                text-align: right;
            }
            
            /* Кнопки действий */
            .actions { 
                display: grid; 
                gap: 10px; 
            }
            
            .action-btn {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 15px;
                font-family: 'Press Start 2P', cursive;
                font-size: 10px;
                background: var(--panel-bg);
                border: 4px solid var(--border-color);
                box-shadow: var(--shadow);
                color: var(--text);
                cursor: pointer;
                transition: all 0.1s;
                text-align: left;
            }
            
            .action-btn:hover {
                transform: translate(-2px, -2px);
                box-shadow: 6px 6px 0px #1a0f2e;
                border-color: var(--accent);
            }
            
            .action-btn:active {
                transform: translate(2px, 2px);
                box-shadow: 2px 2px 0px #1a0f2e;
            }
            
            .action-btn:disabled { 
                opacity: 0.4;
                cursor: not-allowed;
                transform: none;
                box-shadow: var(--shadow);
                border-color: #3d2f5a;
            }
            
            .action-btn.primary {
                background: #0f3d3e;
                border-color: var(--success);
            }
            
            .action-btn.primary:hover {
                border-color: #6ee8df;
            }
            
            .action-icon {
                font-size: 24px;
                width: 40px;
                text-align: center;
            }
            
            .action-info {
                flex: 1;
            }
            
            .action-name {
                display: block;
                margin-bottom: 4px;
            }
            
            .action-desc {
                font-size: 8px;
                color: #8b7cb0;
            }
            
            /* Лог */
            .log-panel {
                margin-top: 15px;
                background: var(--panel-bg);
                border: 4px solid var(--border-color);
                box-shadow: var(--shadow);
                padding: 12px;
                min-height: 100px;
                max-height: 140px;
                overflow-y: auto;
            }
            
            .log-entry {
                margin: 8px 0;
                padding: 8px;
                background: rgba(0,0,0,0.3);
                border-left: 3px solid var(--accent);
                font-size: 8px;
                line-height: 1.6;
                animation: slideIn 0.3s;
            }
            
            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateX(-10px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }
            
            .log-time {
                color: #6b5b8a;
                font-size: 7px;
                margin-bottom: 3px;
            }
            
            .log-success { border-left-color: var(--success); }
            .log-warning { border-left-color: var(--warning); }
            .log-danger { border-left-color: var(--danger); }
            
            /* Скроллбар пиксельный */
            ::-webkit-scrollbar {
                width: 12px;
            }
            
            ::-webkit-scrollbar-track {
                background: var(--panel-bg);
                border: 2px solid var(--border-color);
            }
            
            ::-webkit-scrollbar-thumb {
                background: var(--accent);
                border: 2px solid var(--panel-bg);
            }
            
            ::-webkit-scrollbar-thumb:hover {
                background: var(--accent-dark);
            }
            
            /* Анимации */
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                25% { transform: translateX(-3px); }
                75% { transform: translateX(3px); }
            }
            
            .shake {
                animation: shake 0.3s;
            }
            
            @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.05); }
            }
            
            .pulse {
                animation: pulse 0.5s;
            }
        </style>
    </head>
    <body>
        <!-- Экран создания персонажа -->
        <div class="container create-screen" id="createScreen">
            <h1>◆ RE:ALITY: CORE ◆</h1>
            <p style="font-size: 8px; color: #8b7cb0;">CREATE YOUR CHARACTER</p>
            
            <h2>◆ SELECT AVATAR ◆</h2>
            <div class="avatars" id="avatars">
                <div class="avatar-option" data-avatar="👨">👨</div>
                <div class="avatar-option" data-avatar="👩">👩</div>
                <div class="avatar-option" data-avatar="🧑">🧑</div>
                <div class="avatar-option" data-avatar="👱">👱</div>
                <div class="avatar-option" data-avatar="🧔">🧔</div>
                <div class="avatar-option" data-avatar="👩‍🦰">👩‍🦰</div>
                <div class="avatar-option" data-avatar="🧑‍🦱">🧑‍🦱</div>
                <div class="avatar-option" data-avatar="👨‍🦲">👨‍🦲</div>
            </div>
            
            <h2>◆ ENTER NAME ◆</h2>
            <input type="text" class="name-input" id="charName" placeholder="..." maxlength="12">
            
            <h2>◆ DISTRIBUTE POINTS ◆</h2>
            <div class="stats-create">
                <div class="stat-row-create">
                    <span class="stat-name">
                        <span class="stat-icon">💪</span>
                        <span>STR</span>
                    </span>
                    <div class="stat-controls">
                        <button class="stat-btn" onclick="changeStat('strength', -1)">-</button>
                        <span class="stat-value" id="strength">5</span>
                        <button class="stat-btn" onclick="changeStat('strength', 1)">+</button>
                    </div>
                </div>
                <div class="stat-row-create">
                    <span class="stat-name">
                        <span class="stat-icon">🧠</span>
                        <span>INT</span>
                    </span>
                    <div class="stat-controls">
                        <button class="stat-btn" onclick="changeStat('intelligence', -1)">-</button>
                        <span class="stat-value" id="intelligence">5</span>
                        <button class="stat-btn" onclick="changeStat('intelligence', 1)">+</button>
                    </div>
                </div>
                <div class="stat-row-create">
                    <span class="stat-name">
                        <span class="stat-icon">✨</span>
                        <span>CHA</span>
                    </span>
                    <div class="stat-controls">
                        <button class="stat-btn" onclick="changeStat('charisma', -1)">-</button>
                        <span class="stat-value" id="charisma">5</span>
                        <button class="stat-btn" onclick="changeStat('charisma', 1)">+</button>
                    </div>
                </div>
                <div class="stat-row-create">
                    <span class="stat-name">
                        <span class="stat-icon">🍀</span>
                        <span>LCK</span>
                    </span>
                    <div class="stat-controls">
                        <button class="stat-btn" onclick="changeStat('luck', -1)">-</button>
                        <span class="stat-value" id="luck">5</span>
                        <button class="stat-btn" onclick="changeStat('luck', 1)">+</button>
                    </div>
                </div>
                <div class="points-left">
                    POINTS: <span id="pointsLeft">0</span>/20
                </div>
            </div>
            
            <button class="pixel-btn" id="createBtn" onclick="createCharacter()" disabled>
                START GAME ▶
            </button>
        </div>
        
        <!-- Экран игры -->
        <div class="container game-screen hidden" id="gameScreen">
            <div class="header">
                <h1>◆ RE:ALITY: CORE ◆</h1>
                <div class="day-counter">DAY <span id="day">1</span></div>
            </div>
            
            <div class="character-card">
                <div class="character-avatar" id="gameAvatar">👨</div>
                <div class="character-info">
                    <div class="character-name" id="gameName">PLAYER</div>
                    <div class="character-stats" id="gameStats">
                        STR:5 INT:5 CHA:5 LCK:5
                    </div>
                </div>
            </div>
            
            <div class="status-panel">
                <div class="stat-row">
                    <span class="stat-label">
                        <span>💰</span>
                        <span>MONEY</span>
                    </span>
                    <span class="stat-text" id="moneyText">5000₽</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">
                        <span>⚡</span>
                        <span>ENERGY</span>
                    </span>
                    <div class="stat-bar">
                        <div class="stat-bar-fill" id="energyBar" style="width: 100%"></div>
                    </div>
                    <span class="stat-text" id="energyText">100%</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">
                        <span>📅</span>
                        <span>ACTIONS</span>
                    </span>
                    <span class="stat-text" id="actionsText">3/3</span>
                </div>
            </div>
            
            <div class="actions">
                <button class="action-btn primary" id="btn-work" onclick="doAction('work')">
                    <span class="action-icon">💼</span>
                    <span class="action-info">
                        <span class="action-name">WORK</span>
                        <span class="action-desc">+1500₽ / -30⚡</span>
                    </span>
                </button>
                <button class="action-btn" id="btn-eat" onclick="doAction('eat')">
                    <span class="action-icon">🍜</span>
                    <span class="action-info">
                        <span class="action-name">EAT</span>
                        <span class="action-desc">+20⚡ / -200₽</span>
                    </span>
                </button>
                <button class="action-btn" id="btn-sleep" onclick="doAction('sleep')">
                    <span class="action-icon">😴</span>
                    <span class="action-info">
                        <span class="action-name">SLEEP</span>
                        <span class="action-desc">NEW DAY / -700₽</span>
                    </span>
                </button>
            </div>
            
            <div class="log-panel" id="log">
                <div class="log-entry">
                    <div class="log-time">--:--</div>
                    <div>WELCOME TO RE:ALITY...</div>
                </div>
            </div>
        </div>
        
        <script>
            let tg = window.Telegram.WebApp;
            tg.expand();
            
            let userId = tg.initDataUnsafe?.user?.id || 1;
            let gameState = {};
            let character = {};
            let selectedAvatar = '';
            
            // Создание персонажа
            let stats = { strength: 5, intelligence: 5, charisma: 5, luck: 5 };
            const MAX_POINTS = 20;
            const MIN_STAT = 1;
            
            // Выбор аватара
            document.querySelectorAll('.avatar-option').forEach(el => {
                el.onclick = function() {
                    document.querySelectorAll('.avatar-option').forEach(a => a.classList.remove('selected'));
                    this.classList.add('selected');
                    selectedAvatar = this.dataset.avatar;
                    this.classList.add('pulse');
                    setTimeout(() => this.classList.remove('pulse'), 500);
                    checkCreateButton();
                };
            });
            
            function changeStat(stat, delta) {
                let current = stats[stat];
                let totalUsed = Object.values(stats).reduce((a,b) => a+b, 0);
                let pointsLeft = MAX_POINTS - totalUsed;
                
                if (delta > 0 && pointsLeft <= 0) return;
                if (delta < 0 && current <= MIN_STAT) return;
                
                stats[stat] += delta;
                document.getElementById(stat).textContent = stats[stat];
                updatePoints();
                checkCreateButton();
            }
            
            function updatePoints() {
                let total = Object.values(stats).reduce((a,b) => a+b, 0);
                let left = MAX_POINTS - total;
                document.getElementById('pointsLeft').textContent = left;
                
                document.querySelectorAll('.stat-btn').forEach(btn => {
                    if (btn.textContent === '+' && left <= 0) {
                        btn.disabled = true;
                    } else {
                        btn.disabled = false;
                    }
                });
            }
            
            function checkCreateButton() {
                let name = document.getElementById('charName').value.trim();
                let total = Object.values(stats).reduce((a,b) => a+b, 0);
                let btn = document.getElementById('createBtn');
                
                btn.disabled = !(name && selectedAvatar && total === MAX_POINTS);
            }
            
            document.getElementById('charName').oninput = checkCreateButton;
            
            async function createCharacter() {
                let name = document.getElementById('charName').value.trim();
                
                let response = await fetch('/api/character', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        user_id: userId,
                        name: name,
                        avatar: selectedAvatar,
                        strength: stats.strength,
                        intelligence: stats.intelligence,
                        charisma: stats.charisma,
                        luck: stats.luck
                    })
                });
                
                if (response.ok) {
                    document.getElementById('createScreen').classList.add('hidden');
                    document.getElementById('gameScreen').classList.remove('hidden');
                    loadGame();
                }
            }
            
            // Игра
            async function loadGame() {
                let response = await fetch(`/api/state?user_id=${userId}`);
                let data = await response.json();
                gameState = data.user;
                character = data.character || {};
                
                if (character) {
                    document.getElementById('gameAvatar').textContent = character.avatar || '👨';
                    document.getElementById('gameName').textContent = (character.name || 'PLAYER').toUpperCase();
                    document.getElementById('gameStats').textContent = 
                        `STR:${character.strength} INT:${character.intelligence} CHA:${character.charisma} LCK:${character.luck}`;
                }
                
                updateDisplay();
                log('WELCOME TO THE SIMULATION...', 'success');
            }
            
            function updateDisplay() {
                document.getElementById('moneyText').textContent = gameState.money + '₽';
                document.getElementById('day').textContent = gameState.day;
                document.getElementById('actionsText').textContent = gameState.actions + '/3';
                
                let energyPercent = gameState.energy;
                let energyBar = document.getElementById('energyBar');
                energyBar.style.width = energyPercent + '%';
                document.getElementById('energyText').textContent = energyPercent + '%';
                
                // Цвет энергии
                energyBar.className = 'stat-bar-fill';
                if (energyPercent <= 30) energyBar.classList.add('low');
                else if (energyPercent <= 60) energyBar.classList.add('medium');
                
                // Кнопки
                document.getElementById('btn-work').disabled = gameState.actions <= 0 || gameState.energy < 30;
                document.getElementById('btn-eat').disabled = gameState.actions <= 0;
            }
            
            function log(msg, type = '') {
                let logDiv = document.getElementById('log');
                let entry = document.createElement('div');
                entry.className = 'log-entry log-' + type;
                
                let time = new Date().toLocaleTimeString('en-US', {hour12: false, hour: '2-digit', minute:'2-digit'});
                
                entry.innerHTML = `
                    <div class="log-time">${time}</div>
                    <div>${msg}</div>
                `;
                
                logDiv.insertBefore(entry, logDiv.firstChild);
                
                // Ограничиваем количество записей
                while (logDiv.children.length > 10) {
                    logDiv.removeChild(logDiv.lastChild);
                }
            }
            
            async function doAction(action) {
                let btn = document.getElementById('btn-' + action);
                btn.classList.add('shake');
                setTimeout(() => btn.classList.remove('shake'), 300);
                
                let response = await fetch('/api/action', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({user_id: userId, action: action})
                });
                let result = await response.json();
                
                if (result.success) {
                    gameState = result.state;
                    updateDisplay();
                    
                    let type = 'success';
                    if (result.message.includes('Новый день')) type = 'warning';
                    if (result.message.includes('❌')) type = 'danger';
                    
                    log(result.message.toUpperCase(), type);
                } else {
                    log('❌ ' + result.message.toUpperCase(), 'danger');
                }
            }
            
            // Инициализация
            async function init() {
                let response = await fetch(`/api/state?user_id=${userId}`);
                let data = await response.json();
                
                if (data.character) {
                    document.getElementById('createScreen').classList.add('hidden');
                    document.getElementById('gameScreen').classList.remove('hidden');
                    loadGame();
                } else {
                    updatePoints();
                }
            }
            
            init();
        </script>
    </body>
    </html>
    """
