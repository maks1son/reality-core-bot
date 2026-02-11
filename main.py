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
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: white;
                padding: 20px;
            }
            .container { max-width: 400px; margin: 0 auto; }
            .hidden { display: none !important; }
            
            /* Экран создания персонажа */
            .create-screen { text-align: center; }
            .create-screen h1 { margin-bottom: 10px; }
            .create-screen h2 { margin: 20px 0 10px; font-size: 18px; }
            
            .avatars {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 10px;
                margin: 15px 0;
            }
            .avatar-option {
                font-size: 40px;
                padding: 10px;
                background: rgba(255,255,255,0.1);
                border-radius: 15px;
                cursor: pointer;
                transition: all 0.3s;
                border: 3px solid transparent;
            }
            .avatar-option:hover { background: rgba(255,255,255,0.2); }
            .avatar-option.selected { border-color: #4CAF50; background: rgba(76,175,80,0.3); }
            
            .name-input {
                width: 100%;
                padding: 15px;
                border-radius: 15px;
                border: none;
                font-size: 16px;
                margin: 10px 0;
                background: rgba(255,255,255,0.1);
                color: white;
            }
            .name-input::placeholder { color: rgba(255,255,255,0.5); }
            
            .stats-create {
                background: rgba(255,255,255,0.1);
                border-radius: 15px;
                padding: 15px;
                margin: 15px 0;
            }
            .stat-row-create {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin: 10px 0;
            }
            .stat-controls {
                display: flex;
                align-items: center;
                gap: 15px;
            }
            .stat-btn {
                width: 30px;
                height: 30px;
                border-radius: 50%;
                border: none;
                background: #4CAF50;
                color: white;
                font-size: 18px;
                cursor: pointer;
            }
            .stat-btn:disabled { opacity: 0.3; cursor: not-allowed; }
            .stat-value { font-size: 20px; font-weight: bold; min-width: 30px; }
            .points-left { margin-top: 15px; font-size: 18px; color: #FFD700; }
            
            .create-btn {
                width: 100%;
                padding: 18px;
                margin-top: 20px;
                background: #4CAF50;
                border: none;
                border-radius: 15px;
                color: white;
                font-size: 18px;
                cursor: pointer;
            }
            .create-btn:disabled { opacity: 0.5; }
            
            /* Экран игры */
            .game-screen { }
            .header { text-align: center; margin-bottom: 20px; }
            .header h1 { font-size: 24px; margin-bottom: 5px; }
            .character-bar {
                display: flex;
                align-items: center;
                gap: 15px;
                background: rgba(255,255,255,0.1);
                padding: 15px;
                border-radius: 15px;
                margin-bottom: 20px;
            }
            .character-avatar { font-size: 50px; }
            .character-info { flex: 1; }
            .character-name { font-size: 20px; font-weight: bold; }
            .character-stats { font-size: 12px; opacity: 0.8; margin-top: 5px; }
            
            .stats {
                background: rgba(255,255,255,0.1);
                border-radius: 15px;
                padding: 15px;
                margin-bottom: 15px;
            }
            .stat-row {
                display: flex;
                justify-content: space-between;
                margin: 8px 0;
                font-size: 16px;
            }
            
            .actions { display: grid; gap: 10px; }
            .btn {
                background: rgba(255,255,255,0.2);
                border: none;
                padding: 15px;
                border-radius: 12px;
                color: white;
                font-size: 16px;
                cursor: pointer;
                transition: all 0.3s;
            }
            .btn:hover { background: rgba(255,255,255,0.3); }
            .btn-primary { background: #4CAF50; }
            .btn:disabled { opacity: 0.4; cursor: not-allowed; }
            
            .log {
                margin-top: 15px;
                padding: 15px;
                background: rgba(0,0,0,0.2);
                border-radius: 12px;
                min-height: 80px;
                max-height: 150px;
                overflow-y: auto;
            }
            .log p { margin: 5px 0; font-size: 14px; }
        </style>
    </head>
    <body>
        <!-- Экран создания персонажа -->
        <div class="container create-screen" id="createScreen">
            <h1>🎮 RE:ALITY: Core</h1>
            <p>Создай своего персонажа</p>
            
            <h2>Выбери аватар</h2>
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
            
            <h2>Имя персонажа</h2>
            <input type="text" class="name-input" id="charName" placeholder="Введи имя..." maxlength="15">
            
            <h2>Распредели очки (15)</h2>
            <div class="stats-create">
                <div class="stat-row-create">
                    <span>💪 Сила (доход от работы)</span>
                    <div class="stat-controls">
                        <button class="stat-btn" onclick="changeStat('strength', -1)">-</button>
                        <span class="stat-value" id="strength">5</span>
                        <button class="stat-btn" onclick="changeStat('strength', 1)">+</button>
                    </div>
                </div>
                <div class="stat-row-create">
                    <span>🧠 Интеллект (скорость обучения)</span>
                    <div class="stat-controls">
                        <button class="stat-btn" onclick="changeStat('intelligence', -1)">-</button>
                        <span class="stat-value" id="intelligence">5</span>
                        <button class="stat-btn" onclick="changeStat('intelligence', 1)">+</button>
                    </div>
                </div>
                <div class="stat-row-create">
                    <span>✨ Харизма (социальные бонусы)</span>
                    <div class="stat-controls">
                        <button class="stat-btn" onclick="changeStat('charisma', -1)">-</button>
                        <span class="stat-value" id="charisma">5</span>
                        <button class="stat-btn" onclick="changeStat('charisma', 1)">+</button>
                    </div>
                </div>
                <div class="stat-row-create">
                    <span>🍀 Удача (случайные бонусы)</span>
                    <div class="stat-controls">
                        <button class="stat-btn" onclick="changeStat('luck', -1)">-</button>
                        <span class="stat-value" id="luck">5</span>
                        <button class="stat-btn" onclick="changeStat('luck', 1)">+</button>
                    </div>
                </div>
                <div class="points-left">Осталось очков: <span id="pointsLeft">0</span></div>
            </div>
            
            <button class="create-btn" id="createBtn" onclick="createCharacter()" disabled>
                Начать игру
            </button>
        </div>
        
        <!-- Экран игры -->
        <div class="container game-screen hidden" id="gameScreen">
            <div class="header">
                <h1>🎮 RE:ALITY: Core</h1>
                <p>День <span id="day">1</span></p>
            </div>
            
            <div class="character-bar">
                <div class="character-avatar" id="gameAvatar">👨</div>
                <div class="character-info">
                    <div class="character-name" id="gameName">Игрок</div>
                    <div class="character-stats" id="gameStats">💪5 🧠5 ✨5 🍀5</div>
                </div>
            </div>
            
            <div class="stats">
                <div class="stat-row">
                    <span>💰 Деньги</span>
                    <span id="money">5000 ₽</span>
                </div>
                <div class="stat-row">
                    <span>⚡ Энергия</span>
                    <span id="energy">100%</span>
                </div>
                <div class="stat-row">
                    <span>📅 Действий</span>
                    <span id="actions">3/3</span>
                </div>
            </div>
            
            <div class="actions">
                <button class="btn btn-primary" id="btn-work" onclick="doAction('work')">
                    💼 Работать (+1500₽)
                </button>
                <button class="btn" id="btn-eat" onclick="doAction('eat')">
                    🍜 Есть (+20⚡, -200₽)
                </button>
                <button class="btn" id="btn-sleep" onclick="doAction('sleep')">
                    😴 Спать (новый день)
                </button>
            </div>
            
            <div class="log" id="log">
                <p>Загрузка...</p>
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
                
                // Блокируем кнопки + если нет очков
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
                    document.getElementById('gameName').textContent = character.name || 'Игрок';
                    document.getElementById('gameStats').textContent = 
                        `💪${character.strength} 🧠${character.intelligence} ✨${character.charisma} 🍀${character.luck}`;
                }
                
                updateDisplay();
                log('Добро пожаловать в RE:ALITY!');
            }
            
            function updateDisplay() {
                document.getElementById('money').textContent = gameState.money + ' ₽';
                document.getElementById('energy').textContent = gameState.energy + '%';
                document.getElementById('day').textContent = gameState.day;
                document.getElementById('actions').textContent = gameState.actions + '/3';
                
                document.getElementById('btn-work').disabled = gameState.actions <= 0 || gameState.energy < 30;
                document.getElementById('btn-eat').disabled = gameState.actions <= 0;
            }
            
            function log(msg) {
                let logDiv = document.getElementById('log');
                let p = document.createElement('p');
                p.textContent = new Date().toLocaleTimeString() + ': ' + msg;
                logDiv.insertBefore(p, logDiv.firstChild);
            }
            
            async function doAction(action) {
                let response = await fetch('/api/action', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({user_id: userId, action: action})
                });
                let result = await response.json();
                
                if (result.success) {
                    gameState = result.state;
                    updateDisplay();
                    log(result.message);
                } else {
                    log('❌ ' + result.message);
                }
            }
            
            // Проверяем, есть ли персонаж
            async function init() {
                let response = await fetch(`/api/state?user_id=${userId}`);
                let data = await response.json();
                
                if (data.character) {
                    // Персонаж есть — сразу в игру
                    document.getElementById('createScreen').classList.add('hidden');
                    document.getElementById('gameScreen').classList.remove('hidden');
                    loadGame();
                } else {
                    // Нет персонажа — показываем создание
                    updatePoints();
                }
            }
            
            init();
        </script>
    </body>
    </html>
    """
