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
            }
            
            .container { 
                height: 100vh;
                max-width: 400px;
                margin: 0 auto;
                display: flex;
                flex-direction: column;
                padding: 6px;
            }
            
            .hidden { display: none !important; }
            
            .pixel-box {
                background: var(--panel-bg);
                border: 3px solid var(--border-color);
                box-shadow: 3px 3px 0px #000;
            }
            
            /* ===== СОЗДАНИЕ ===== */
            .create-screen {
                display: flex;
                flex-direction: column;
                height: 100%;
                gap: 6px;
            }
            
            .create-header {
                text-align: center;
                padding: 4px;
            }
            
            .create-header h1 { 
                font-size: 12px; 
                color: var(--accent);
                text-shadow: 2px 2px 0px #000;
            }
            
            /* ПЕРСОНАЖИ ВО ВЕСЬ РОСТ */
            .heroes-area {
                flex: 1;
                display: flex;
                flex-direction: column;
                min-height: 0;
            }
            
            .section-title {
                text-align: center;
                font-size: 8px;
                color: var(--warning);
                margin-bottom: 6px;
            }
            
            .heroes-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 6px;
                flex: 1;
            }
            
            .hero-card {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: flex-end;
                background: var(--panel-bg);
                border: 3px solid var(--border-color);
                box-shadow: 3px 3px 0px #000;
                cursor: pointer;
                padding: 4px;
                position: relative;
                overflow: hidden;
            }
            
            .hero-card:hover { 
                border-color: var(--accent);
            }
            
            .hero-card.selected { 
                border-color: var(--success);
                background: #0f3d3e;
                box-shadow: inset 2px 2px 0px #000;
            }
            
            /* ПИКСЕЛЬНЫЙ ЧЕЛОВЕЧЕК */
            .pixel-person {
                font-size: 48px;
                line-height: 1;
                filter: contrast(1.2);
                image-rendering: pixelated;
            }
            
            .hero-gender {
                font-size: 8px;
                color: #8b7cb0;
                margin-top: 4px;
            }
            
            /* ИМЯ */
            .name-row {
                display: flex;
                gap: 6px;
            }
            
            .name-input {
                flex: 1;
                padding: 8px;
                font-family: 'Press Start 2P', cursive;
                font-size: 10px;
                background: var(--panel-bg);
                border: 3px solid var(--border-color);
                box-shadow: 3px 3px 0px #000;
                color: var(--text);
                outline: none;
                text-align: center;
            }
            
            /* СТАТЫ КОМПАКТНО */
            .stats-row {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 6px;
            }
            
            .stat-item {
                background: var(--panel-bg);
                border: 3px solid var(--border-color);
                box-shadow: 3px 3px 0px #000;
                padding: 6px;
                text-align: center;
            }
            
            .stat-header {
                font-size: 12px;
                margin-bottom: 4px;
            }
            
            .stat-controls {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
            }
            
            .stat-btn {
                width: 20px;
                height: 20px;
                font-family: 'Press Start 2P', cursive;
                font-size: 10px;
                background: var(--accent);
                border: none;
                box-shadow: 2px 2px 0px #000;
                color: white;
                cursor: pointer;
            }
            
            .stat-btn:active {
                transform: translate(1px, 1px);
                box-shadow: 1px 1px 0px #000;
            }
            
            .stat-btn:disabled { 
                opacity: 0.3; 
            }
            
            .stat-num { 
                font-size: 12px; 
                color: var(--success);
                min-width: 20px;
            }
            
            .points-display {
                text-align: center;
                padding: 6px;
                border: 2px dashed var(--warning);
                color: var(--warning);
                font-size: 10px;
            }
            
            .start-btn {
                padding: 12px;
                font-family: 'Press Start 2P', cursive;
                font-size: 12px;
                background: var(--success);
                border: none;
                box-shadow: 3px 3px 0px #2d8b84;
                color: #000;
                cursor: pointer;
            }
            
            .start-btn:disabled { 
                opacity: 0.4;
                background: #666;
            }
            
            /* ===== ИГРА ===== */
            .game-screen {
                display: flex;
                flex-direction: column;
                height: 100%;
                gap: 6px;
            }
            
            .top-bar {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 6px 10px;
            }
            
            .game-title {
                font-size: 10px;
                color: var(--accent);
                text-shadow: 2px 2px 0px #000;
            }
            
            .day-box {
                background: var(--warning);
                color: #000;
                padding: 4px 8px;
                font-size: 8px;
                box-shadow: 2px 2px 0px #b8a030;
            }
            
            /* ЦЕНТР - ПЕРСОНАЖ */
            .main-stage {
                flex: 1;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                position: relative;
                min-height: 0;
            }
            
            .stage-floor {
                position: absolute;
                bottom: 20%;
                width: 200px;
                height: 40px;
                background: var(--panel-bg);
                border: 3px solid var(--border-color);
                border-radius: 50%;
                z-index: 0;
            }
            
            .hero-figure {
                font-size: 100px;
                line-height: 1;
                z-index: 1;
                filter: contrast(1.2);
                animation: idle 2s ease-in-out infinite;
                text-shadow: 4px 4px 0px #000;
            }
            
            @keyframes idle {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-5px); }
            }
            
            .hero-tag {
                margin-top: 8px;
                padding: 6px 16px;
                background: var(--panel-bg);
                border: 3px solid var(--border-color);
                box-shadow: 3px 3px 0px #000;
                font-size: 10px;
                color: var(--accent);
                z-index: 1;
            }
            
            .hero-build {
                display: flex;
                gap: 12px;
                margin-top: 6px;
                font-size: 10px;
                z-index: 1;
            }
            
            .build-stat {
                display: flex;
                align-items: center;
                gap: 2px;
            }
            
            /* РЕСУРСЫ */
            .res-row {
                display: grid;
                grid-template-columns: 2fr 1fr 1fr;
                gap: 6px;
            }
            
            .res-item {
                padding: 8px;
                text-align: center;
            }
            
            .res-val {
                font-size: 14px;
                color: var(--success);
                margin: 2px 0;
            }
            
            /* ЭНЕРГИЯ */
            .nrg-bar {
                height: 20px;
                position: relative;
            }
            
            .nrg-fill {
                height: 100%;
                background: linear-gradient(90deg, var(--danger), var(--warning), var(--success));
                transition: width 0.3s;
            }
            
            .nrg-text {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 10px;
                text-shadow: 2px 2px 0px #000;
            }
            
            /* КНОПКИ */
            .action-row {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 6px;
            }
            
            .act-btn {
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 10px 4px;
                gap: 4px;
                font-family: 'Press Start 2P', cursive;
                font-size: 8px;
                background: var(--panel-bg);
                border: 3px solid var(--border-color);
                box-shadow: 3px 3px 0px #000;
                color: var(--text);
                cursor: pointer;
            }
            
            .act-btn:active {
                transform: translate(2px, 2px);
                box-shadow: 1px 1px 0px #000;
            }
            
            .act-btn:disabled { 
                opacity: 0.4;
            }
            
            .act-btn.main {
                border-color: var(--success);
                background: #0f3d3e;
            }
            
            .act-ico {
                font-size: 24px;
            }
            
            /* ЛОГ */
            .game-log {
                height: 50px;
                overflow-y: auto;
                padding: 6px;
            }
            
            .log-line {
                margin: 2px 0;
                padding: 3px 6px;
                background: rgba(0,0,0,0.3);
                border-left: 3px solid var(--accent);
                font-size: 7px;
            }
            
            .good { border-left-color: var(--success); }
            .bad { border-left-color: var(--danger); }
            .warn { border-left-color: var(--warning); }
            
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                50% { transform: translateX(-3px); }
            }
            
            .shake {
                animation: shake 0.15s;
            }
        </style>
    </head>
    <body>
        <!-- СОЗДАНИЕ -->
        <div class="container create-screen" id="createScreen">
            <div class="create-header">
                <h1>◆ RE:ALITY ◆</h1>
            </div>
            
            <div class="heroes-area">
                <div class="section-title">◆ CHOOSE YOUR HERO ◆</div>
                <div class="heroes-grid" id="heroes">
                    <!-- МУЖЧИНЫ -->
                    <div class="hero-card" data-avatar="🧍‍♂️" data-type="Классика">
                        <div class="pixel-person">🧍‍♂️</div>
                        <div class="hero-gender">MALE</div>
                    </div>
                    <div class="hero-card" data-avatar="🧔‍♂️" data-type="Бородач">
                        <div class="pixel-person">🧔‍♂️</div>
                        <div class="hero-gender">MALE</div>
                    </div>
                    <div class="hero-card" data-avatar="👨‍🦱" data-type="Кудряш">
                        <div class="pixel-person">👨‍🦱</div>
                        <div class="hero-gender">MALE</div>
                    </div>
                    <div class="hero-card" data-avatar="👨‍🦲" data-type="Лысый">
                        <div class="pixel-person">👨‍🦲</div>
                        <div class="hero-gender">MALE</div>
                    </div>
                    <!-- ЖЕНЩИНЫ -->
                    <div class="hero-card" data-avatar="🧍‍♀️" data-type="Классика">
                        <div class="pixel-person">🧍‍♀️</div>
                        <div class="hero-gender">FEMALE</div>
                    </div>
                    <div class="hero-card" data-avatar="👩‍🦰" data-type="Рыжая">
                        <div class="pixel-person">👩‍🦰</div>
                        <div class="hero-gender">FEMALE</div>
                    </div>
                    <div class="hero-card" data-avatar="👱‍♀️" data-type="Блонди">
                        <div class="pixel-person">👱‍♀️</div>
                        <div class="hero-gender">FEMALE</div>
                    </div>
                    <div class="hero-card" data-avatar="👩‍🦱" data-type="Кудряшка">
                        <div class="pixel-person">👩‍🦱</div>
                        <div class="hero-gender">FEMALE</div>
                    </div>
                </div>
            </div>
            
            <div class="name-row">
                <input type="text" class="name-input pixel-box" id="charName" placeholder="NAME" maxlength="8">
            </div>
            
            <div class="stats-row">
                <div class="stat-item">
                    <div class="stat-header">💪</div>
                    <div class="stat-controls">
                        <button class="stat-btn" onclick="chg('str', -1)">-</button>
                        <span class="stat-num" id="str">5</span>
                        <button class="stat-btn" onclick="chg('str', 1)">+</button>
                    </div>
                </div>
                <div class="stat-item">
                    <div class="stat-header">🧠</div>
                    <div class="stat-controls">
                        <button class="stat-btn" onclick="chg('int', -1)">-</button>
                        <span class="stat-num" id="int">5</span>
                        <button class="stat-btn" onclick="chg('int', 1)">+</button>
                    </div>
                </div>
                <div class="stat-item">
                    <div class="stat-header">✨</div>
                    <div class="stat-controls">
                        <button class="stat-btn" onclick="chg('cha', -1)">-</button>
                        <span class="stat-num" id="cha">5</span>
                        <button class="stat-btn" onclick="chg('cha', 1)">+</button>
                    </div>
                </div>
                <div class="stat-item">
                    <div class="stat-header">🍀</div>
                    <div class="stat-controls">
                        <button class="stat-btn" onclick="chg('lck', -1)">-</button>
                        <span class="stat-num" id="lck">5</span>
                        <button class="stat-btn" onclick="chg('lck', 1)">+</button>
                    </div>
                </div>
            </div>
            
            <div class="points-display">
                POINTS: <span id="pts">0</span>/20
            </div>
            
            <button class="start-btn" id="startBtn" onclick="create()" disabled>
                START ▶
            </button>
        </div>
        
        <!-- ИГРА -->
        <div class="container game-screen hidden" id="gameScreen">
            <div class="top-bar pixel-box">
                <span class="game-title">◆ RE:ALITY ◆</span>
                <span class="day-box">DAY <span id="day">1</span></span>
            </div>
            
            <div class="main-stage">
                <div class="stage-floor"></div>
                <div class="hero-figure" id="gAvatar">🧍‍♂️</div>
                <div class="hero-tag" id="gName">HERO</div>
                <div class="hero-build">
                    <span class="build-stat">💪<span id="gStr">5</span></span>
                    <span class="build-stat">🧠<span id="gInt">5</span></span>
                    <span class="build-stat">✨<span id="gCha">5</span></span>
                    <span class="build-stat">🍀<span id="gLck">5</span></span>
                </div>
            </div>
            
            <div class="res-row">
                <div class="res-item pixel-box">
                    <div>💰</div>
                    <div class="res-val" id="gMoney">5000</div>
                    <div style="font-size:6px;color:#666">MONEY</div>
                </div>
                <div class="res-item pixel-box">
                    <div>⚡</div>
                    <div class="res-val" id="gNRG">100</div>
                    <div style="font-size:6px;color:#666">NRG</div>
                </div>
                <div class="res-item pixel-box">
                    <div>📅</div>
                    <div class="res-val" id="gAct">3</div>
                    <div style="font-size:6px;color:#666">ACT</div>
                </div>
            </div>
            
            <div class="nrg-bar pixel-box">
                <div class="nrg-fill" id="gBar" style="width:100%"></div>
                <span class="nrg-text" id="gBarTxt">100%</span>
            </div>
            
            <div class="action-row">
                <button class="act-btn main" id="btn-work" onclick="act('work')">
                    <span class="act-ico">💼</span>
                    <span>WORK</span>
                </button>
                <button class="act-btn" id="btn-eat" onclick="act('eat')">
                    <span class="act-ico">🍜</span>
                    <span>EAT</span>
                </button>
                <button class="act-btn" id="btn-sleep" onclick="act('sleep')">
                    <span class="act-ico">😴</span>
                    <span>SLEEP</span>
                </button>
            </div>
            
            <div class="game-log pixel-box" id="log">
                <div class="log-line">> SYSTEM READY...</div>
            </div>
        </div>
        
        <script>
            let tg = window.Telegram.WebApp;
            tg.expand();
            
            let uid = tg.initDataUnsafe?.user?.id || 1;
            let state = {}, hero = {}, sel = '';
            let stats = {str:5, int:5, cha:5, lck:5};
            const MAX = 20, MIN = 1;
            
            document.querySelectorAll('.hero-card').forEach(el => {
                el.onclick = function() {
                    document.querySelectorAll('.hero-card').forEach(h => h.classList.remove('selected'));
                    this.classList.add('selected');
                    sel = this.dataset.avatar;
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
                
                document.querySelectorAll('.stat-btn').forEach(b => {
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
                state = d.user; hero = d.character;
                
                document.getElementById('gAvatar').textContent = hero.avatar;
                document.getElementById('gName').textContent = hero.name.toUpperCase();
                document.getElementById('gStr').textContent = hero.strength;
                document.getElementById('gInt').textContent = hero.intelligence;
                document.getElementById('gCha').textContent = hero.charisma;
                document.getElementById('gLck').textContent = hero.luck;
                
                updGame();
                addLog('WELCOME ' + hero.name.toUpperCase(), 'good');
            }
            
            function updGame() {
                document.getElementById('gMoney').textContent = state.money;
                document.getElementById('day').textContent = state.day;
                document.getElementById('gAct').textContent = state.actions;
                document.getElementById('gNRG').textContent = state.energy;
                document.getElementById('gBar').style.width = state.energy+'%';
                document.getElementById('gBarTxt').textContent = state.energy+'%';
                
                document.getElementById('btn-work').disabled = state.actions<=0 || state.energy<30;
                document.getElementById('btn-eat').disabled = state.actions<=0;
            }
            
            function addLog(m, c='') {
                let l = document.getElementById('log');
                let e = document.createElement('div');
                e.className = 'log-line ' + c;
                e.textContent = '> ' + m;
                l.insertBefore(e, l.firstChild);
                while(l.children.length>3) l.removeChild(l.lastChild);
            }
            
            async function act(a) {
                let b = document.getElementById('btn-'+a);
                b.classList.add('shake');
                setTimeout(()=>b.classList.remove('shake'), 150);
                
                let r = await fetch('/api/action', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({user_id: uid, action: a})
                });
                let res = await r.json();
                
                if(res.success) {
                    state = res.state;
                    updGame();
                    let cl = res.message.includes('день')?'warn':'good';
                    addLog(res.message.toUpperCase(), cl);
                } else {
                    addLog('ERROR: '+res.message.toUpperCase(), 'bad');
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
    </html>
    """
