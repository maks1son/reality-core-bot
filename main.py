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
            }
            
            body {
                font-family: 'Press Start 2P', cursive;
                background: var(--bg-color);
                min-height: 100vh;
                color: var(--text);
                padding: 10px;
                font-size: 8px;
                line-height: 1.6;
            }
            
            .container { 
                max-width: 360px; 
                margin: 0 auto; 
            }
            
            .hidden { display: none !important; }
            
            /* Пиксельные боксы */
            .pixel-box {
                background: var(--panel-bg);
                border: 4px solid var(--border-color);
                box-shadow: 4px 4px 0px #000;
            }
            
            /* Экран создания */
            .create-screen { text-align: center; }
            
            .create-screen h1 { 
                font-size: 14px; 
                color: var(--accent);
                text-shadow: 3px 3px 0px var(--accent-dark);
                margin-bottom: 15px;
            }
            
            .create-screen h2 { 
                font-size: 8px; 
                color: var(--warning);
                margin: 15px 0 10px;
            }
            
            .avatars {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 8px;
                margin: 10px 0;
            }
            
            .avatar-option {
                font-size: 28px;
                padding: 12px 8px;
                background: var(--panel-bg);
                border: 4px solid var(--border-color);
                box-shadow: 4px 4px 0px #000;
                cursor: pointer;
                transition: all 0.1s;
            }
            
            .avatar-option:hover { 
                transform: translate(-2px, -2px);
                box-shadow: 6px 6px 0px #000;
                border-color: var(--accent);
            }
            
            .avatar-option.selected { 
                border-color: var(--success);
                background: #0f3d3e;
                box-shadow: inset 2px 2px 0px #000;
                transform: translate(2px, 2px);
            }
            
            .name-input {
                width: 100%;
                padding: 12px;
                font-family: 'Press Start 2P', cursive;
                font-size: 10px;
                background: var(--panel-bg);
                border: 4px solid var(--border-color);
                box-shadow: 4px 4px 0px #000;
                color: var(--text);
                margin: 10px 0;
                outline: none;
                text-align: center;
            }
            
            .name-input::placeholder { 
                color: #6b5b8a; 
            }
            
            .stats-create {
                background: var(--panel-bg);
                border: 4px solid var(--border-color);
                box-shadow: 4px 4px 0px #000;
                padding: 12px;
                margin: 10px 0;
            }
            
            .stat-row-create {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin: 10px 0;
                font-size: 8px;
            }
            
            .stat-controls {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .stat-btn {
                width: 24px;
                height: 24px;
                font-family: 'Press Start 2P', cursive;
                font-size: 10px;
                background: var(--accent);
                border: none;
                box-shadow: 2px 2px 0px var(--accent-dark);
                color: white;
                cursor: pointer;
            }
            
            .stat-btn:active {
                transform: translate(2px, 2px);
                box-shadow: none;
            }
            
            .stat-btn:disabled { 
                opacity: 0.3; 
                cursor: not-allowed;
            }
            
            .stat-value { 
                font-size: 10px; 
                min-width: 20px;
                color: var(--success);
            }
            
            .points-left { 
                margin-top: 10px; 
                font-size: 8px; 
                color: var(--warning);
                padding: 8px;
                border: 2px dashed var(--warning);
            }
            
            .pixel-btn {
                width: 100%;
                padding: 15px;
                margin-top: 15px;
                font-family: 'Press Start 2P', cursive;
                font-size: 10px;
                background: var(--success);
                border: none;
                box-shadow: 4px 4px 0px #2d8b84;
                color: #1a0f2e;
                cursor: pointer;
            }
            
            .pixel-btn:active {
                transform: translate(2px, 2px);
                box-shadow: 2px 2px 0px #2d8b84;
            }
            
            .pixel-btn:disabled { 
                opacity: 0.4;
                background: #6b5b8a;
            }
            
            /* ЭКРАН ИГРЫ - ПЕРСОНАЖ В ЦЕНТРЕ */
            .game-screen { }
            
            .header { 
                text-align: center; 
                margin-bottom: 10px; 
            }
            
            .header h1 { 
                font-size: 12px; 
                color: var(--accent);
                text-shadow: 2px 2px 0px var(--accent-dark);
            }
            
            .day-counter {
                font-size: 8px;
                color: var(--warning);
                margin-top: 5px;
            }
            
            /* ЦЕНТРАЛЬНАЯ ЗОНА ПЕРСОНАЖА */
            .character-zone {
                display: flex;
                flex-direction: column;
                align-items: center;
                margin: 15px 0;
            }
            
            .character-avatar-big {
                width: 120px;
                height: 120px;
                font-size: 80px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: var(--panel-bg);
                border: 6px solid var(--border-color);
                box-shadow: 6px 6px 0px #000, inset 0 0 20px rgba(0,0,0,0.5);
                margin-bottom: 10px;
                position: relative;
            }
            
            .character-avatar-big::before {
                content: '◆';
                position: absolute;
                top: -15px;
                left: 50%;
                transform: translateX(-50%);
                color: var(--accent);
                font-size: 12px;
            }
            
            .character-avatar-big::after {
                content: '◆';
                position: absolute;
                bottom: -15px;
                left: 50%;
                transform: translateX(-50%);
                color: var(--accent);
                font-size: 12px;
            }
            
            .character-name-plate {
                background: var(--panel-bg);
                border: 4px solid var(--border-color);
                box-shadow: 4px 4px 0px #000;
                padding: 8px 20px;
                font-size: 10px;
                color: var(--accent);
                margin-bottom: 8px;
                text-align: center;
            }
            
            .character-stats-bar {
                display: flex;
                gap: 15px;
                font-size: 8px;
                color: #8b7cb0;
            }
            
            .stat-item {
                display: flex;
                align-items: center;
                gap: 4px;
            }
            
            /* ПАНЕЛЬ РЕСУРСОВ */
            .resources-panel {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 8px;
                margin-bottom: 12px;
            }
            
            .resource-box {
                background: var(--panel-bg);
                border: 4px solid var(--border-color);
                box-shadow: 4px 4px 0px #000;
                padding: 10px;
                text-align: center;
            }
            
            .resource-icon {
                font-size: 16px;
                margin-bottom: 5px;
            }
            
            .resource-value {
                font-size: 12px;
                color: var(--success);
            }
            
            .resource-label {
                font-size: 6px;
                color: #6b5b8a;
                margin-top: 3px;
            }
            
            /* ЭНЕРГИЯ ОТДЕЛЬНО */
            .energy-panel {
                background: var(--panel-bg);
                border: 4px solid var(--border-color);
                box-shadow: 4px 4px 0px #000;
                padding: 10px;
                margin-bottom: 12px;
            }
            
            .energy-header {
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
                font-size: 8px;
            }
            
            .energy-bar-container {
                height: 16px;
                background: #1a0f2e;
                border: 2px solid var(--border-color);
                position: relative;
            }
            
            .energy-bar-fill {
                height: 100%;
                background: linear-gradient(90deg, var(--danger) 0%, var(--warning) 50%, var(--success) 100%);
                transition: width 0.3s;
                box-shadow: inset 0 0 0 2px rgba(255,255,255,0.1);
            }
            
            .energy-text {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 8px;
                text-shadow: 1px 1px 0px #000;
            }
            
            /* ДЕЙСТВИЯ */
            .actions-title {
                text-align: center;
                font-size: 8px;
                color: var(--warning);
                margin-bottom: 8px;
            }
            
            .actions {
                display: grid;
                gap: 8px;
            }
            
            .action-btn {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 12px;
                font-family: 'Press Start 2P', cursive;
                font-size: 8px;
                background: var(--panel-bg);
                border: 4px solid var(--border-color);
                box-shadow: 4px 4px 0px #000;
                color: var(--text);
                cursor: pointer;
                text-align: left;
            }
            
            .action-btn:active {
                transform: translate(2px, 2px);
                box-shadow: 2px 2px 0px #000;
            }
            
            .action-btn:disabled { 
                opacity: 0.4;
                border-color: #3d2f5a;
            }
            
            .action-btn.primary {
                border-color: var(--success);
                background: #0f3d3e;
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
                color: var(--accent);
            }
            
            .action-desc {
                font-size: 6px;
                color: #8b7cb0;
            }
            
            /* ЛОГ */
            .log-panel {
                margin-top: 12px;
                background: var(--panel-bg);
                border: 4px solid var(--border-color);
                box-shadow: 4px 4px 0px #000;
                padding: 10px;
                min-height: 80px;
                max-height: 100px;
                overflow-y: auto;
            }
            
            .log-entry {
                margin: 6px 0;
                padding: 6px;
                background: rgba(0,0,0,0.3);
                border-left: 3px solid var(--accent);
                font-size: 7px;
                line-height: 1.5;
            }
            
            .log-success { border-left-color: var(--success); }
            .log-warning { border-left-color: var(--warning); }
            .log-danger { border-left-color: var(--danger); }
            
            /* Анимации */
            @keyframes bounce {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-5px); }
            }
            
            .bounce {
                animation: bounce 0.5s;
            }
            
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                25% { transform: translateX(-3px); }
                75% { transform: translateX(3px); }
            }
            
            .shake {
                animation: shake 0.3s;
            }
        </style>
    </head>
    <body>
        <!-- Экран создания -->
        <div class="container create-screen" id="createScreen">
            <h1>◆ RE:ALITY ◆</h1>
            <p style="font-size: 6px; color: #8b7cb0;">CREATE CHARACTER</p>
            
            <h2>◆ AVATAR ◆</h2>
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
            
            <h2>◆ NAME ◆</h2>
            <input type="text" class="name-input" id="charName" placeholder="..." maxlength="10">
            
            <h2>◆ STATS ◆</h2>
            <div class="stats-create">
                <div class="stat-row-create">
                    <span>💪 STR</span>
                    <div class="stat-controls">
                        <button class="stat-btn" onclick="changeStat('strength', -1)">-</button>
                        <span class="stat-value" id="strength">5</span>
                        <button class="stat-btn" onclick="changeStat('strength', 1)">+</button>
                    </div>
                </div>
                <div class="stat-row-create">
                    <span>🧠 INT</span>
                    <div class="stat-controls">
                        <button class="stat-btn" onclick="changeStat('intelligence', -1)">-</button>
                        <span class="stat-value" id="intelligence">5</span>
                        <button class="stat-btn" onclick="changeStat('intelligence', 1)">+</button>
                    </div>
                </div>
                <div class="stat-row-create">
                    <span>✨ CHA</span>
                    <div class="stat-controls">
                        <button class="stat-btn" onclick="changeStat('charisma', -1)">-</button>
                        <span class="stat-value" id="charisma">5</span>
                        <button class="stat-btn" onclick="changeStat('charisma', 1)">+</button>
                    </div>
                </div>
                <div class="stat-row-create">
                    <span>🍀 LCK</span>
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
                START ▶
            </button>
        </div>
        
        <!-- Экран игры -->
        <div class="container game-screen hidden" id="gameScreen">
            <div class="header">
                <h1>◆ RE:ALITY ◆</h1>
                <div class="day-counter">DAY <span id="day">1</span></div>
            </div>
            
            <!-- ПЕРСОНАЖ В ЦЕНТРЕ -->
            <div class="character-zone">
                <div class="character-avatar-big" id="gameAvatar">👨</div>
                <div class="character-name-plate" id="gameName">PLAYER</div>
                <div class="character-stats-bar">
                    <span class="stat-item">💪<span id="strVal">5</span></span>
                    <span class="stat-item">🧠<span id="intVal">5</span></span>
                    <span class="stat-item">✨<span id="chaVal">5</span></span>
                    <span class="stat-item">🍀<span id="lckVal">5</span></span>
                </div>
            </div>
            
            <!-- РЕСУРСЫ -->
            <div class="resources-panel">
                <div class="resource-box">
                    <div class="resource-icon">💰</div>
                    <div class="resource-value" id="moneyText">5000</div>
                    <div class="resource-label">MONEY</div>
                </div>
                <div class="resource-box">
                    <div class="resource-icon">📅</div>
                    <div class="resource-value" id="actionsText">3</div>
                    <div class="resource-label">ACTIONS</div>
                </div>
            </div>
            
            <!-- ЭНЕРГИЯ -->
            <div class="energy-panel">
                <div class="energy-header">
                    <span>⚡ ENERGY</span>
                    <span id="energyText">100%</span>
                </div>
                <div class="energy-bar-container">
                    <div class="energy-bar-fill" id="energyBar" style="width: 100%"></div>
                    <span class="energy-text" id="energyBarText">100%</span>
                </div>
            </div>
            
            <!-- ДЕЙСТВИЯ -->
            <div class="actions-title">◆ ACTIONS ◆</div>
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
                        <span class="action-desc">NEXT DAY / -700₽</span>
                    </span>
                </button>
            </div>
            
            <!-- ЛОГ -->
            <div class="log-panel" id="log">
                <div class="log-entry">SYSTEM READY...</div>
            </div>
        </div>
        
        <script>
            let tg = window.Telegram.WebApp;
            tg.expand();
            
            let userId = tg.initDataUnsafe?.user?.id || 1;
            let gameState = {};
            let character = {};
            let selectedAvatar = '';
            
            let stats = { strength: 5, intelligence: 5, charisma: 5, luck: 5 };
            const MAX_POINTS = 20;
            const MIN_STAT = 1;
            
            document.querySelectorAll('.avatar-option').forEach(el => {
                el.onclick = function() {
                    document.querySelectorAll('.avatar-option').forEach(a => a.classList.remove('selected'));
                    this.classList.add('selected');
                    selectedAvatar = this.dataset.avatar;
                    this.classList.add('bounce');
                    setTimeout(() => this.classList.remove('bounce'), 500);
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
            
            async function loadGame() {
                let response = await fetch(`/api/state?user_id=${userId}`);
                let data = await response.json();
                gameState = data.user;
                character = data.character || {};
                
                if (character) {
                    document.getElementById('gameAvatar').textContent = character.avatar || '👨';
                    document.getElementById('gameName').textContent = (character.name || 'PLAYER').toUpperCase();
                    document.getElementById('strVal').textContent = character.strength;
                    document.getElementById('intVal').textContent = character.intelligence;
                    document.getElementById('chaVal').textContent = character.charisma;
                    document.getElementById('lckVal').textContent = character.luck;
                }
                
                updateDisplay();
                log('WELCOME TO RE:ALITY', 'success');
            }
            
            function updateDisplay() {
                document.getElementById('moneyText').textContent = gameState.money;
                document.getElementById('day').textContent = gameState.day;
                document.getElementById('actionsText').textContent = gameState.actions;
                
                let energy = gameState.energy;
                document.getElementById('energyText').textContent = energy + '%';
                document.getElementById('energyBarText').textContent = energy + '%';
                document.getElementById('energyBar').style.width = energy + '%';
                
                document.getElementById('btn-work').disabled = gameState.actions <= 0 || gameState.energy < 30;
                document.getElementById('btn-eat').disabled = gameState.actions <= 0;
            }
            
            function log(msg, type = '') {
                let logDiv = document.getElementById('log');
                let entry = document.createElement('div');
                entry.className = 'log-entry log-' + type;
                entry.textContent = '> ' + msg;
                logDiv.insertBefore(entry, logDiv.firstChild);
                while (logDiv.children.length > 8) logDiv.removeChild(logDiv.lastChild);
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
                    let type = result.message.includes('день') ? 'warning' : 'success';
                    log(result.message.toUpperCase(), type);
                } else {
                    log('ERROR: ' + result.message.toUpperCase(), 'danger');
                }
            }
            
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
