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
            
            html, body {
                height: 100%;
                overflow: hidden;
            }
            
            body {
                font-family: 'Press Start 2P', cursive;
                background: var(--bg-color);
                color: var(--text);
                font-size: 8px;
                line-height: 1.4;
            }
            
            .container { 
                height: 100vh;
                max-width: 400px;
                margin: 0 auto;
                display: flex;
                flex-direction: column;
                padding: 8px;
            }
            
            .hidden { display: none !important; }
            
            .pixel-box {
                background: var(--panel-bg);
                border: 3px solid var(--border-color);
                box-shadow: 3px 3px 0px #000;
            }
            
            /* ===== СОЗДАНИЕ ПЕРСОНАЖА ===== */
            .create-screen {
                display: flex;
                flex-direction: column;
                height: 100%;
                gap: 8px;
            }
            
            .create-header {
                text-align: center;
                padding: 5px;
            }
            
            .create-header h1 { 
                font-size: 12px; 
                color: var(--accent);
                text-shadow: 2px 2px 0px var(--accent-dark);
            }
            
            .create-header p { 
                font-size: 6px; 
                color: #8b7cb0;
                margin-top: 3px;
            }
            
            /* ПЕРСОНАЖИ ВО ВЕСЬ РОСТ */
            .avatar-section {
                flex: 1;
                display: flex;
                flex-direction: column;
                min-height: 0;
            }
            
            .section-label {
                font-size: 7px;
                color: var(--warning);
                margin-bottom: 5px;
                text-align: center;
            }
            
            .avatars-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 6px;
                flex: 1;
            }
            
            .avatar-option {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                background: var(--panel-bg);
                border: 3px solid var(--border-color);
                box-shadow: 3px 3px 0px #000;
                cursor: pointer;
                padding: 4px;
                position: relative;
            }
            
            .avatar-sprite {
                font-size: 36px;
                line-height: 1;
                margin-bottom: 2px;
            }
            
            .avatar-body {
                font-size: 24px;
                line-height: 1;
            }
            
            .avatar-option:hover { 
                border-color: var(--accent);
            }
            
            .avatar-option.selected { 
                border-color: var(--success);
                background: #0f3d3e;
                box-shadow: inset 2px 2px 0px #000;
            }
            
            .avatar-name {
                font-size: 6px;
                color: #8b7cb0;
                margin-top: 2px;
            }
            
            /* ИМЯ */
            .name-section {
                display: flex;
                gap: 8px;
                align-items: center;
            }
            
            .name-input {
                flex: 1;
                padding: 8px;
                font-family: 'Press Start 2P', cursive;
                font-size: 8px;
                background: var(--panel-bg);
                border: 3px solid var(--border-color);
                box-shadow: 3px 3px 0px #000;
                color: var(--text);
                outline: none;
            }
            
            .name-input::placeholder { 
                color: #6b5b8a; 
            }
            
            /* СТАТЫ */
            .stats-section {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 6px;
            }
            
            .stat-box {
                background: var(--panel-bg);
                border: 3px solid var(--border-color);
                box-shadow: 3px 3px 0px #000;
                padding: 6px;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .stat-info {
                display: flex;
                align-items: center;
                gap: 6px;
            }
            
            .stat-icon {
                font-size: 14px;
            }
            
            .stat-name {
                font-size: 7px;
            }
            
            .stat-controls {
                display: flex;
                align-items: center;
                gap: 6px;
            }
            
            .stat-btn {
                width: 18px;
                height: 18px;
                font-family: 'Press Start 2P', cursive;
                font-size: 8px;
                background: var(--accent);
                border: none;
                box-shadow: 2px 2px 0px var(--accent-dark);
                color: white;
                cursor: pointer;
            }
            
            .stat-btn:active {
                transform: translate(1px, 1px);
                box-shadow: 1px 1px 0px var(--accent-dark);
            }
            
            .stat-btn:disabled { 
                opacity: 0.3; 
                cursor: not-allowed;
            }
            
            .stat-value { 
                font-size: 10px; 
                color: var(--success);
                min-width: 16px;
                text-align: center;
            }
            
            .points-box {
                grid-column: span 2;
                text-align: center;
                padding: 6px;
                border: 2px dashed var(--warning);
                color: var(--warning);
                font-size: 8px;
            }
            
            .pixel-btn {
                padding: 12px;
                font-family: 'Press Start 2P', cursive;
                font-size: 10px;
                background: var(--success);
                border: none;
                box-shadow: 3px 3px 0px #2d8b84;
                color: #1a0f2e;
                cursor: pointer;
            }
            
            .pixel-btn:active {
                transform: translate(2px, 2px);
                box-shadow: 1px 1px 0px #2d8b84;
            }
            
            .pixel-btn:disabled { 
                opacity: 0.4;
                background: #6b5b8a;
            }
            
            /* ===== ЭКРАН ИГРЫ ===== */
            .game-screen {
                display: flex;
                flex-direction: column;
                height: 100%;
                gap: 6px;
            }
            
            .game-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 5px 8px;
            }
            
            .game-title {
                font-size: 10px;
                color: var(--accent);
                text-shadow: 2px 2px 0px var(--accent-dark);
            }
            
            .day-badge {
                background: var(--warning);
                color: #1a0f2e;
                padding: 4px 8px;
                font-size: 8px;
                box-shadow: 2px 2px 0px #b8a030;
            }
            
            /* ПЕРСОНАЖ В ЦЕНТРЕ */
            .hero-section {
                flex: 1;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 0;
                position: relative;
            }
            
            .hero-avatar {
                font-size: 80px;
                line-height: 1;
                text-shadow: 4px 4px 0px #000;
                animation: breathe 2s ease-in-out infinite;
            }
            
            @keyframes breathe {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.05); }
            }
            
            .hero-platform {
                width: 120px;
                height: 20px;
                background: var(--panel-bg);
                border: 3px solid var(--border-color);
                margin-top: -10px;
                position: relative;
                z-index: -1;
            }
            
            .hero-name {
                margin-top: 8px;
                padding: 6px 16px;
                background: var(--panel-bg);
                border: 3px solid var(--border-color);
                box-shadow: 3px 3px 0px #000;
                font-size: 10px;
                color: var(--accent);
            }
            
            .hero-stats {
                display: flex;
                gap: 12px;
                margin-top: 6px;
                font-size: 8px;
            }
            
            .hero-stat {
                display: flex;
                align-items: center;
                gap: 3px;
            }
            
            /* РЕСУРСЫ */
            .resources-bar {
                display: grid;
                grid-template-columns: 2fr 1fr 1fr;
                gap: 6px;
            }
            
            .res-box {
                padding: 6px;
                text-align: center;
            }
            
            .res-icon {
                font-size: 12px;
            }
            
            .res-value {
                font-size: 12px;
                color: var(--success);
                margin: 2px 0;
            }
            
            .res-label {
                font-size: 6px;
                color: #6b5b8a;
            }
            
            /* ЭНЕРГИЯ */
            .energy-bar {
                height: 16px;
                background: #1a0f2e;
                border: 3px solid var(--border-color);
                box-shadow: 3px 3px 0px #000;
                position: relative;
            }
            
            .energy-fill {
                height: 100%;
                background: linear-gradient(90deg, var(--danger), var(--warning), var(--success));
                transition: width 0.3s;
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
            .actions-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 6px;
            }
            
            .action-btn {
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 8px 4px;
                font-family: 'Press Start 2P', cursive;
                font-size: 7px;
                background: var(--panel-bg);
                border: 3px solid var(--border-color);
                box-shadow: 3px 3px 0px #000;
                color: var(--text);
                cursor: pointer;
                gap: 4px;
            }
            
            .action-btn:active {
                transform: translate(2px, 2px);
                box-shadow: 1px 1px 0px #000;
            }
            
            .action-btn:disabled { 
                opacity: 0.4;
            }
            
            .action-btn.primary {
                border-color: var(--success);
                background: #0f3d3e;
            }
            
            .action-icon {
                font-size: 20px;
            }
            
            /* ЛОГ */
            .log-box {
                height: 60px;
                overflow-y: auto;
                padding: 6px;
                font-size: 7px;
            }
            
            .log-entry {
                margin: 3px 0;
                padding: 3px 6px;
                background: rgba(0,0,0,0.3);
                border-left: 2px solid var(--accent);
            }
            
            .log-success { border-left-color: var(--success); }
            .log-warning { border-left-color: var(--warning); }
            .log-danger { border-left-color: var(--danger); }
            
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                25% { transform: translateX(-2px); }
                75% { transform: translateX(2px); }
            }
            
            .shake {
                animation: shake 0.2s;
            }
        </style>
    </head>
    <body>
        <!-- СОЗДАНИЕ ПЕРСОНАЖА -->
        <div class="container create-screen" id="createScreen">
            <div class="create-header">
                <h1>◆ RE:ALITY ◆</h1>
                <p>CREATE YOUR HERO</p>
            </div>
            
            <div class="avatar-section">
                <div class="section-label">◆ SELECT HERO ◆</div>
                <div class="avatars-grid" id="avatars">
                    <div class="avatar-option" data-avatar="🧙‍♂️" data-name="MAGE">
                        <span class="avatar-sprite">🧙‍♂️</span>
                        <span class="avatar-name">MAGE</span>
                    </div>
                    <div class="avatar-option" data-avatar="⚔️" data-name="WARRIOR">
                        <span class="avatar-sprite">⚔️</span>
                        <span class="avatar-name">WARRIOR</span>
                    </div>
                    <div class="avatar-option" data-avatar="🏹" data-name="RANGER">
                        <span class="avatar-sprite">🏹</span>
                        <span class="avatar-name">RANGER</span>
                    </div>
                    <div class="avatar-option" data-avatar="🗡️" data-name="ROGUE">
                        <span class="avatar-sprite">🗡️</span>
                        <span class="avatar-name">ROGUE</span>
                    </div>
                    <div class="avatar-option" data-avatar="🔨" data-name="SMITH">
                        <span class="avatar-sprite">🔨</span>
                        <span class="avatar-name">SMITH</span>
                    </div>
                    <div class="avatar-option" data-avatar="📚" data-name="SCHOLAR">
                        <span class="avatar-sprite">📚</span>
                        <span class="avatar-name">SCHOLAR</span>
                    </div>
                    <div class="avatar-option" data-avatar="🎭" data-name="BARD">
                        <span class="avatar-sprite">🎭</span>
                        <span class="avatar-name">BARD</span>
                    </div>
                    <div class="avatar-option" data-avatar="🔮" data-name="SEER">
                        <span class="avatar-sprite">🔮</span>
                        <span class="avatar-name">SEER</span>
                    </div>
                </div>
            </div>
            
            <div class="name-section">
                <input type="text" class="name-input" id="charName" placeholder="NAME..." maxlength="8">
            </div>
            
            <div class="stats-section">
                <div class="stat-box">
                    <span class="stat-info">
                        <span class="stat-icon">💪</span>
                        <span class="stat-name">STR</span>
                    </span>
                    <span class="stat-controls">
                        <button class="stat-btn" onclick="changeStat('strength', -1)">-</button>
                        <span class="stat-value" id="strength">5</span>
                        <button class="stat-btn" onclick="changeStat('strength', 1)">+</button>
                    </span>
                </div>
                <div class="stat-box">
                    <span class="stat-info">
                        <span class="stat-icon">🧠</span>
                        <span class="stat-name">INT</span>
                    </span>
                    <span class="stat-controls">
                        <button class="stat-btn" onclick="changeStat('intelligence', -1)">-</button>
                        <span class="stat-value" id="intelligence">5</span>
                        <button class="stat-btn" onclick="changeStat('intelligence', 1)">+</button>
                    </span>
                </div>
                <div class="stat-box">
                    <span class="stat-info">
                        <span class="stat-icon">✨</span>
                        <span class="stat-name">CHA</span>
                    </span>
                    <span class="stat-controls">
                        <button class="stat-btn" onclick="changeStat('charisma', -1)">-</button>
                        <span class="stat-value" id="charisma">5</span>
                        <button class="stat-btn" onclick="changeStat('charisma', 1)">+</button>
                    </span>
                </div>
                <div class="stat-box">
                    <span class="stat-info">
                        <span class="stat-icon">🍀</span>
                        <span class="stat-name">LCK</span>
                    </span>
                    <span class="stat-controls">
                        <button class="stat-btn" onclick="changeStat('luck', -1)">-</button>
                        <span class="stat-value" id="luck">5</span>
                        <button class="stat-btn" onclick="changeStat('luck', 1)">+</button>
                    </span>
                </div>
                <div class="points-box">
                    POINTS: <span id="pointsLeft">0</span>/20
                </div>
            </div>
            
            <button class="pixel-btn" id="createBtn" onclick="createCharacter()" disabled>
                START ▶
            </button>
        </div>
        
        <!-- ЭКРАН ИГРЫ -->
        <div class="container game-screen hidden" id="gameScreen">
            <div class="game-header pixel-box">
                <span class="game-title">◆ RE:ALITY ◆</span>
                <span class="day-badge">DAY <span id="day">1</span></span>
            </div>
            
            <!-- ПЕРСОНАЖ ВО ВЕСЬ РОСТ -->
            <div class="hero-section">
                <div class="hero-avatar" id="gameAvatar">🧙‍♂️</div>
                <div class="hero-platform"></div>
                <div class="hero-name" id="gameName">HERO</div>
                <div class="hero-stats">
                    <span class="hero-stat">💪<span id="strVal">5</span></span>
                    <span class="hero-stat">🧠<span id="intVal">5</span></span>
                    <span class="hero-stat">✨<span id="chaVal">5</span></span>
                    <span class="hero-stat">🍀<span id="lckVal">5</span></span>
                </div>
            </div>
            
            <!-- РЕСУРСЫ -->
            <div class="resources-bar">
                <div class="res-box pixel-box">
                    <div class="res-icon">💰</div>
                    <div class="res-value" id="moneyText">5000</div>
                    <div class="res-label">MONEY</div>
                </div>
                <div class="res-box pixel-box">
                    <div class="res-icon">⚡</div>
                    <div class="res-value" id="energyText">100</div>
                    <div class="res-label">NRG</div>
                </div>
                <div class="res-box pixel-box">
                    <div class="res-icon">📅</div>
                    <div class="res-value" id="actionsText">3</div>
                    <div class="res-label">ACT</div>
                </div>
            </div>
            
            <!-- ЭНЕРГИЯ БАР -->
            <div class="energy-bar pixel-box">
                <div class="energy-fill" id="energyBar" style="width: 100%"></div>
                <span class="energy-text" id="energyBarText">100%</span>
            </div>
            
            <!-- ДЕЙСТВИЯ -->
            <div class="actions-grid">
                <button class="action-btn primary" id="btn-work" onclick="doAction('work')">
                    <span class="action-icon">💼</span>
                    <span>WORK</span>
                </button>
                <button class="action-btn" id="btn-eat" onclick="doAction('eat')">
                    <span class="action-icon">🍜</span>
                    <span>EAT</span>
                </button>
                <button class="action-btn" id="btn-sleep" onclick="doAction('sleep')">
                    <span class="action-icon">😴</span>
                    <span>SLEEP</span>
                </button>
            </div>
            
            <!-- ЛОГ -->
            <div class="log-box pixel-box" id="log">
                <div class="log-entry">> SYSTEM READY...</div>
            </div>
        </div>
        
        <script>
            let tg = window.Telegram.WebApp;
            tg.expand();
            
            let userId = tg.initDataUnsafe?.user?.id || 1;
            let gameState = {};
            let character = {};
            let selectedAvatar = '';
            let selectedClass = '';
            
            let stats = { strength: 5, intelligence: 5, charisma: 5, luck: 5 };
            const MAX_POINTS = 20;
            const MIN_STAT = 1;
            
            document.querySelectorAll('.avatar-option').forEach(el => {
                el.onclick = function() {
                    document.querySelectorAll('.avatar-option').forEach(a => a.classList.remove('selected'));
                    this.classList.add('selected');
                    selectedAvatar = this.dataset.avatar;
                    selectedClass = this.dataset.name;
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
                    document.getElementById('gameAvatar').textContent = character.avatar || '🧙‍♂️';
                    document.getElementById('gameName').textContent = (character.name || 'HERO').toUpperCase();
                    document.getElementById('strVal').textContent = character.strength;
                    document.getElementById('intVal').textContent = character.intelligence;
                    document.getElementById('chaVal').textContent = character.charisma;
                    document.getElementById('lckVal').textContent = character.luck;
                }
                
                updateDisplay();
                log('WELCOME HERO', 'success');
            }
            
            function updateDisplay() {
                document.getElementById('moneyText').textContent = gameState.money;
                document.getElementById('day').textContent = gameState.day;
                document.getElementById('actionsText').textContent = gameState.actions;
                
                let energy = gameState.energy;
                document.getElementById('energyText').textContent = energy;
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
                while (logDiv.children.length > 4) logDiv.removeChild(logDiv.lastChild);
            }
            
            async function doAction(action) {
                let btn = document.getElementById('btn-' + action);
                btn.classList.add('shake');
                setTimeout(() => btn.classList.remove('shake'), 200);
                
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
