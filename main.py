import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from database import init_db, get_user, save_user

app = FastAPI()

# Инициализация базы при старте
init_db()

# Статические файлы
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Получение данных пользователя
@app.get("/api/state")
async def get_state(user_id: int):
    state = get_user(user_id)
    return state

# Сохранение действия
@app.post("/api/action")
async def do_action(request: Request):
    data = await request.json()
    user_id = data.get('user_id')
    action = data.get('action')
    
    user = get_user(user_id)
    
    if action == 'work' and user['actions'] > 0 and user['energy'] >= 30:
        user['money'] += 1500
        user['energy'] -= 30
        user['actions'] -= 1
        save_user(user_id, user['money'], user['energy'], user['day'], user['actions'])
        return {'success': True, 'message': 'Поработал. +1500₽, -30⚡', 'state': user}
    
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
        user['money'] -= 700  # аренда + еда
        save_user(user_id, user['money'], user['energy'], user['day'], user['actions'])
        return {'success': True, 'message': 'Новый день! Расходы: 700₽', 'state': user}
    
    return {'success': False, 'message': 'Недостаточно действий или энергии'}

# Главная страница Mini App
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
            .header { text-align: center; margin-bottom: 30px; }
            .header h1 { font-size: 28px; margin-bottom: 10px; }
            .stats {
                background: rgba(255,255,255,0.1);
                border-radius: 20px;
                padding: 20px;
                margin-bottom: 20px;
                backdrop-filter: blur(10px);
            }
            .stat-row {
                display: flex;
                justify-content: space-between;
                margin: 10px 0;
                font-size: 18px;
            }
            .actions { display: grid; gap: 10px; }
            .btn {
                background: rgba(255,255,255,0.2);
                border: none;
                padding: 15px 20px;
                border-radius: 15px;
                color: white;
                font-size: 16px;
                cursor: pointer;
                transition: all 0.3s;
            }
            .btn:hover { background: rgba(255,255,255,0.3); }
            .btn-primary { background: #4CAF50; }
            .btn:disabled { opacity: 0.5; cursor: not-allowed; }
            .log {
                margin-top: 20px;
                padding: 15px;
                background: rgba(0,0,0,0.2);
                border-radius: 10px;
                min-height: 100px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎮 RE:ALITY: Core</h1>
                <p>День <span id="day">1</span></p>
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
                    💼 Работать
                </button>
                <button class="btn" id="btn-eat" onclick="doAction('eat')">
                    🍜 Есть
                </button>
                <button class="btn" id="btn-sleep" onclick="doAction('sleep')">
                    😴 Спать
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
            
            async function loadState() {
                try {
                    let response = await fetch(`/api/state?user_id=${userId}`);
                    gameState = await response.json();
                    updateDisplay();
                    log('Добро пожаловать! День ' + gameState.day);
                } catch(e) {
                    log('Ошибка загрузки: ' + e.message);
                }
            }
            
            function updateDisplay() {
                document.getElementById('money').textContent = gameState.money + ' ₽';
                document.getElementById('energy').textContent = gameState.energy + '%';
                document.getElementById('day').textContent = gameState.day;
                document.getElementById('actions').textContent = gameState.actions + '/3';
                
                // Блокируем кнопки если нет действий
                document.getElementById('btn-work').disabled = gameState.actions <= 0 || gameState.energy < 30;
                document.getElementById('btn-eat').disabled = gameState.actions <= 0;
            }
            
            function log(message) {
                let logDiv = document.getElementById('log');
                let p = document.createElement('p');
                p.textContent = new Date().toLocaleTimeString() + ': ' + message;
                logDiv.insertBefore(p, logDiv.firstChild);
            }
            
            async function doAction(action) {
                try {
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
                } catch(e) {
                    log('Ошибка: ' + e.message);
                }
            }
            
            // Загружаем состояние при старте
            loadState();
        </script>
    </body>
    </html>
    """
