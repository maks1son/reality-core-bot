import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Статические файлы (CSS, JS)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

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
            .actions {
                display: grid;
                gap: 10px;
            }
            .btn {
                background: rgba(255,255,255,0.2);
                border: none;
                padding: 15px 20px;
                border-radius: 15px;
                color: white;
                font-size: 16px;
                cursor: pointer;
                transition: all 0.3s;
                backdrop-filter: blur(10px);
            }
            .btn:hover { background: rgba(255,255,255,0.3); transform: scale(1.02); }
            .btn:active { transform: scale(0.98); }
            .btn-primary { background: #4CAF50; }
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
                <button class="btn btn-primary" onclick="doAction('work')">
                    💼 Работать (+1500₽, -30⚡)
                </button>
                <button class="btn" onclick="doAction('eat')">
                    🍜 Есть (+20⚡, -200₽)
                </button>
                <button class="btn" onclick="doAction('sleep')">
                    😴 Спать (новый день)
                </button>
            </div>
            
            <div class="log" id="log">
                <p>Добро пожаловать! Начни свой путь.</p>
            </div>
        </div>
        
        <script>
            let tg = window.Telegram.WebApp;
            tg.expand();
            
            let gameState = {
                money: 5000,
                energy: 100,
                day: 1,
                actions: 3
            };
            
            function updateDisplay() {
                document.getElementById('money').textContent = gameState.money + ' ₽';
                document.getElementById('energy').textContent = gameState.energy + '%';
                document.getElementById('day').textContent = gameState.day;
                document.getElementById('actions').textContent = gameState.actions + '/3';
            }
            
            function log(message) {
                let logDiv = document.getElementById('log');
                let p = document.createElement('p');
                p.textContent = message;
                logDiv.insertBefore(p, logDiv.firstChild);
            }
            
            function doAction(action) {
                if (gameState.actions <= 0 && action !== 'sleep') {
                    log('⚡ Действия закончились! Нужно спать.');
                    return;
                }
                
                if (gameState.energy < 30 && action === 'work') {
                    log('😴 Слишком устал для работы!');
                    return;
                }
                
                switch(action) {
                    case 'work':
                        gameState.money += 1500;
                        gameState.energy -= 30;
                        gameState.actions--;
                        log('💼 Поработал. +1500₽, -30⚡');
                        break;
                    case 'eat':
                        gameState.money -= 200;
                        gameState.energy = Math.min(100, gameState.energy + 20);
                        gameState.actions--;
                        log('🍜 Поел. +20⚡, -200₽');
                        break;
                    case 'sleep':
                        gameState.day++;
                        gameState.energy = 100;
                        gameState.actions = 3;
                        gameState.money -= 700; // аренда + еда
                        log('🌙 Новый день! Расходы: 700₽');
                        break;
                }
                
                updateDisplay();
                
                // Отправляем данные боту (опционально)
                tg.sendData(JSON.stringify(gameState));
            }
            
            // Инициализация
            updateDisplay();
        </script>
    </body>
    </html>
    """

@app.post("/save")
async def save_progress(request: Request):
    data = await request.json()
    # Здесь будет сохранение в базу
    return {"status": "ok"}
