import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from database import init_db, get_user, save_user, get_character, save_character

app = FastAPI()

init_db()

# === API маршруты (должны быть ПЕРЕД статическими файлами) ===

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
    
    work_bonus = character['strength'] * 50 if character else 0
    
    if action == 'work' and user['actions'] > 0 and user['energy'] >= 30:
        user['money'] += 1500 + work_bonus
        user['energy'] -= 30
        user['actions'] -= 1
        save_user(user_id, user['money'], user['energy'], user['day'], user['actions'])
        msg = f'Поработал. +{1500 + work_bonus}₽, -30⚡'
        if work_bonus > 0:
            msg += ' 💎 Бонус!'
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
    
    return {'success': False, 'message': 'Недостаточно действий'}

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
        * { margin: 0; padding: 0; box-sizing: border-box; image-rendering: pixelated; }
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
        html, body { height: 100%; overflow: hidden; }
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
            gap: 6px;
        }
        .game-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 10px;
        }
        .game-title {
            font-size: 12px;
            color: var(--accent);
            text-shadow: 2px 2px 0px #000;
        }
        .day-pill {
            background: var(--warning);
            color: #000;
            padding: 5px 10px;
            font-size: 10px;
            box-shadow: 2px 2px 0px #b8a030;
        }
        .hero-stage {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            position: relative;
            min-height: 0;
        }
        .shadow-platform {
            position: absolute;
            bottom: 15%;
            width: 180px;
            height: 30px;
            background: rgba(0,0,0,0.3);
            border-radius: 50%;
            z-index: 0;
        }
        .hero-giant {
            width: 140px;
            height: 140px;
            z-index: 1;
            animation: breathe 2s ease-in-out infinite;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .hero-giant img {
            width: 140px;
            height: 140px;
            image-rendering: pixelated;
            filter: drop-shadow(4px 4px 0px #000);
        }
        @keyframes breathe {
            0%, 100% { transform: translateY(0) scale(1); }
            50% { transform: translateY(-8px) scale(1.02); }
        }
        .hero-badge {
            margin-top: 10px;
            padding: 8px 20px;
            background: var(--panel-bg);
            border: 3px solid var(--border-color);
            box-shadow: 3px 3px 0px #000;
            font-size: 12px;
            color: var(--accent);
            z-index: 1;
        }
        .hero-stats-row {
            display: flex;
            gap: 15px;
            margin-top: 8px;
            font-size: 12px;
            z-index: 1;
        }
        .h-stat {
            display: flex;
            align-items: center;
            gap: 3px;
        }
        .res-grid {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr;
            gap: 6px;
        }
        .res-cell {
            padding: 10px 6px;
            text-align: center;
        }
        .res-ico { font-size: 16px; }
        .res-num { 
            font-size: 16px; 
            color: var(--success);
            margin: 4px 0;
        }
        .res-lbl { font-size: 6px; color: #666; }
        .energy-box {
            height: 24px;
            position: relative;
        }
        .energy-inner {
            height: 100%;
            background: linear-gradient(90deg, var(--danger), var(--warning), var(--success));
            transition: width 0.3s;
        }
        .energy-txt {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 10px;
            text-shadow: 2px 2px 0px #000;
        }
        .acts-row {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 6px;
        }
        .act-pill {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 12px 4px;
            gap: 6px;
            font-family: 'Press Start 2P', cursive;
            font-size: 9px;
            background: var(--panel-bg);
            border: 3px solid var(--border-color);
            box-shadow: 3px 3px 0px #000;
            color: var(--text);
            cursor: pointer;
        }
        .act-pill:active {
            transform: translate(2px, 2px);
            box-shadow: 1px 1px 0px #000;
        }
        .act-pill:disabled { 
            opacity: 0.4;
        }
        .act-pill.main {
            border-color: var(--success);
            background: #0f3d3e;
        }
        .act-big-ico {
            font-size: 28px;
        }
        .log-compact {
            height: 45px;
            overflow-y: auto;
            padding: 6px;
        }
        .log-entry {
            margin: 2px 0;
            padding: 4px 8px;
            background: rgba(0,0,0,0.3);
            border-left: 3px solid var(--accent);
            font-size: 8px;
        }
        .ok { border-left-color: var(--success); }
        .no { border-left-color: var(--danger); }
        .at { border-left-color: var(--warning); }
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
        <div class="game-top pixel-box">
            <span class="game-title">◆ RE:ALITY ◆</span>
            <span class="day-pill">DAY <span id="day">1</span></span>
        </div>
        
        <div class="hero-stage">
            <div class="shadow-platform"></div>
            <div class="hero-giant">
                <img src="/hero1.png" alt="Hero" id="gameHero">
            </div>
            <div class="hero-badge" id="gName">HERO</div>
            <div class="hero-stats-row">
                <span class="h-stat">💪<span id="gStr">5</span></span>
                <span class="h-stat">🧠<span id="gInt">5</span></span>
                <span class="h-stat">✨<span id="gCha">5</span></span>
                <span class="h-stat">🍀<span id="gLck">5</span></span>
            </div>
        </div>
        
        <div class="res-grid">
            <div class="res-cell pixel-box">
                <div class="res-ico">💰</div>
                <div class="res-num" id="gMoney">5000</div>
                <div class="res-lbl">MONEY</div>
            </div>
            <div class="res-cell pixel-box">
                <div class="res-ico">⚡</div>
                <div class="res-num" id="gNRG">100</div>
                <div class="res-lbl">ENERGY</div>
            </div>
            <div class="res-cell pixel-box">
                <div class="res-ico">📅</div>
                <div class="res-num" id="gAct">3</div>
                <div class="res-lbl">ACTIONS</div>
            </div>
        </div>
        
        <div class="energy-box pixel-box">
            <div class="energy-inner" id="gBar" style="width:100%"></div>
            <span class="energy-txt" id="gBarTxt">100%</span>
        </div>
        
        <div class="acts-row">
            <button class="act-pill main" id="btn-work" onclick="act('work')">
                <span class="act-big-ico">💼</span>
                <span>WORK</span>
            </button>
            <button class="act-pill" id="btn-eat" onclick="act('eat')">
                <span class="act-big-ico">🍜</span>
                <span>EAT</span>
            </button>
            <button class="act-pill" id="btn-sleep" onclick="act('sleep')">
                <span class="act-big-ico">😴</span>
                <span>SLEEP</span>
            </button>
        </div>
        
        <div class="log-compact pixel-box" id="log">
            <div class="log-entry">> SYSTEM READY...</div>
        </div>
    </div>
    
    <script>
        let tg = window.Telegram.WebApp;
        tg.expand();
        
        let uid = tg.initDataUnsafe?.user?.id || 1;
        let state = {}, hero = {}, sel = '';
        let stats = {str:5, int:5, cha:5, lck:5};
        const MAX = 20, MIN = 1;
        
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
            state = d.user; hero = d.character;
            
            let heroNum = hero.avatar.replace('hero', '') || '1';
            document.getElementById('gameHero').src = '/hero' + heroNum + '.png';
            
            document.getElementById('gName').textContent = hero.name.toUpperCase();
            document.getElementById('gStr').textContent = hero.strength;
            document.getElementById('gInt').textContent = hero.intelligence;
            document.getElementById('gCha').textContent = hero.charisma;
            document.getElementById('gLck').textContent = hero.luck;
            
            updG();
            log('WELCOME ' + hero.name.toUpperCase(), 'ok');
        }
        
        function updG() {
            document.getElementById('gMoney').textContent = state.money;
            document.getElementById('day').textContent = state.day;
            document.getElementById('gAct').textContent = state.actions;
            document.getElementById('gNRG').textContent = state.energy;
            document.getElementById('gBar').style.width = state.energy+'%';
            document.getElementById('gBarTxt').textContent = state.energy+'%';
            
            document.getElementById('btn-work').disabled = state.actions<=0 || state.energy<30;
            document.getElementById('btn-eat').disabled = state.actions<=0;
        }
        
        function log(m, c='') {
            let l = document.getElementById('log');
            let e = document.createElement('div');
            e.className = 'log-entry ' + c;
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
                updG();
                let cl = res.message.includes('день')?'at':'ok';
                log(res.message.toUpperCase(), cl);
            } else {
                log('ERROR: '+res.message.toUpperCase(), 'no');
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

# === Статические файлы (после всех маршрутов) ===

# Отдельные эндпоинты для картинок
@app.get("/hero1.png")
async def hero1():
    return FileResponse("hero1.png")

@app.get("/hero2.png")
async def hero2():
    return FileResponse("hero2.png")

@app.get("/hero3.png")
async def hero3():
    return FileResponse("hero3.png")
