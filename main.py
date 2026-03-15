"""
RE:ALITY: Профессии — FastAPI бэкенд v2
Безлимитные уровни, мгновенные монеты/XP, прогресс заданий
"""
import os, time, json, hashlib, hmac, urllib.parse, random
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import database as db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = FastAPI(title="RE:ALITY Профессии")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Формула XP для уровня: 80 * level^1.4
def xp_for_level(level):
    return int(80 * (level ** 1.4))

UPGRADES = {
    "tap": {"base_cost": 50, "mult": 2.0, "max_level": 20},
    "energy": {"base_cost": 80, "mult": 2.2, "max_level": 20},
    "multi": {"base_cost": 200, "mult": 2.5, "max_level": 5},
    "regen": {"base_cost": 100, "mult": 2.0, "max_level": 20},
}

def regenerate_energy(user):
    now = time.time()
    elapsed = now - user["last_energy_update"]
    new_e = min(user["max_energy"], user["energy"] + elapsed * user["energy_regen"])
    user["energy"] = int(new_e)
    user["last_energy_update"] = now
    return user

def process_level_ups(user):
    """Обработка повышений уровня, возвращает кол-во новых уровней"""
    leveled = 0
    while True:
        needed = xp_for_level(user["level"])
        if user["xp"] >= needed:
            user["xp"] -= needed
            user["level"] += 1
            user["tokens"] += 1
            leveled += 1
        else:
            break
    return leveled

def validate_tg(init_data):
    if not BOT_TOKEN:
        try:
            parsed = urllib.parse.parse_qs(init_data)
            return json.loads(parsed.get("user",["{}"])[0]).get("id")
        except: return None
    try:
        parsed = urllib.parse.parse_qs(init_data)
        ch = parsed.get("hash",[None])[0]
        if not ch: return None
        pairs = sorted(f"{k}={v[0]}" for k,v in parsed.items() if k!="hash")
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        comp = hmac.new(secret, "\n".join(pairs).encode(), hashlib.sha256).hexdigest()
        if comp == ch:
            return json.loads(parsed.get("user",["{}"])[0]).get("id")
    except: pass
    return None

# === Модели ===
class AuthReq(BaseModel):
    init_data: str = ""; tg_id: int = 0
class RegReq(BaseModel):
    init_data: str = ""; tg_id: int = 0
    name: str; avatar: int; stats: dict
class TapReq(BaseModel):
    init_data: str = ""; tg_id: int = 0
    taps: int = 1; coins_earned: int = 0; xp_earned: int = 0
class UnlockReq(BaseModel):
    init_data: str = ""; tg_id: int = 0; profession_id: str
class UpgReq(BaseModel):
    init_data: str = ""; tg_id: int = 0; upgrade_type: str
class TaskReq(BaseModel):
    init_data: str = ""; tg_id: int = 0
    profession_id: str; task_index: int; score: int = 100
class ProgressReq(BaseModel):
    init_data: str = ""; tg_id: int = 0
    profession_id: str; task_index: int; data: dict = {}

def get_id(req):
    if req.init_data:
        t = validate_tg(req.init_data)
        if t: return t
    if req.tg_id: return req.tg_id
    raise HTTPException(400, "Auth error")

def user_resp(user):
    return {"user": user, "xp_needed": xp_for_level(user["level"])}

# === Роуты ===
@app.get("/")
async def index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.get("/hero{n}.png")
async def hero(n: int):
    if n not in (1,2,3): raise HTTPException(404)
    return FileResponse(os.path.join(BASE_DIR, f"hero{n}.png"))

@app.post("/api/auth")
async def auth(req: AuthReq):
    tg_id = get_id(req)
    user = db.get_user(tg_id)
    if not user:
        db.create_user(tg_id)
        user = db.get_user(tg_id)
    user = regenerate_energy(user)
    db.update_user_fields(tg_id, {"energy": user["energy"], "last_energy_update": user["last_energy_update"]})
    return {
        **user_resp(user),
        "unlocked": db.get_unlocked(tg_id),
        "completed": db.get_completed(tg_id),
        "progress": db.get_progress(tg_id)
    }

@app.post("/api/register")
async def register(req: RegReq):
    tg_id = get_id(req)
    name = req.name.strip()[:8]
    if not name: raise HTTPException(400, "Введите имя")
    if req.avatar not in (1,2,3): raise HTTPException(400, "Неверный аватар")
    total = sum(req.stats.get(k,0) for k in ("str","int","cha","luck"))
    if total != 20: raise HTTPException(400, f"Сумма должна быть 20 ({total})")
    db.create_user(tg_id)
    db.register_user(tg_id, name, req.avatar, req.stats)
    return user_resp(db.get_user(tg_id))

@app.post("/api/tap")
async def tap(req: TapReq, request: Request):
    """Синхронизация тапов — клиент отправляет заработанное, сервер валидирует"""
    tg_id = get_id(req)
    user = db.get_user(tg_id)
    if not user or not user["registered"]: raise HTTPException(400, "Не зарегистрирован")

    taps = min(req.taps, 50)
    ip = request.client.host if request.client else ""
    db.log_taps(tg_id, taps, ip)
    if not db.check_tap_rate(tg_id): raise HTTPException(429, "Слишком быстро")

    user = regenerate_energy(user)
    actual = min(taps, user["energy"])
    if actual <= 0:
        db.update_user_fields(tg_id, {"energy": user["energy"], "last_energy_update": user["last_energy_update"]})
        return {**user_resp(user), "earned": 0, "leveled": 0}

    # Валидируем монеты от клиента (максимум coins_per_tap * taps * 5 для множителя)
    max_coins = user["coins_per_tap"] * actual * 6
    coins = min(req.coins_earned, max_coins) if req.coins_earned > 0 else user["coins_per_tap"] * actual
    max_xp = actual * 3 * 2
    xp = min(req.xp_earned, max_xp) if req.xp_earned > 0 else actual * 2

    user["coins"] += coins
    user["xp"] += xp
    user["energy"] -= actual
    leveled = process_level_ups(user)

    db.update_user_fields(tg_id, {
        "coins": user["coins"], "xp": user["xp"], "level": user["level"],
        "tokens": user["tokens"], "energy": user["energy"],
        "last_energy_update": user["last_energy_update"]
    })
    user = db.get_user(tg_id)
    return {**user_resp(user), "earned": coins, "leveled": leveled}

@app.post("/api/unlock")
async def unlock(req: UnlockReq):
    tg_id = get_id(req)
    user = db.get_user(tg_id)
    if not user: raise HTTPException(400, "Нет юзера")
    if user["tokens"] < 1: raise HTTPException(400, "Нет токенов")
    if req.profession_id in db.get_unlocked(tg_id): raise HTTPException(400, "Уже открыто")
    db.update_user_fields(tg_id, {"tokens": user["tokens"] - 1})
    db.unlock_profession(tg_id, req.profession_id)
    return {**user_resp(db.get_user(tg_id)), "unlocked": db.get_unlocked(tg_id)}

@app.post("/api/upgrade")
async def upgrade(req: UpgReq):
    tg_id = get_id(req)
    user = db.get_user(tg_id)
    if not user: raise HTTPException(400, "Нет юзера")
    ut = req.upgrade_type
    if ut not in UPGRADES: raise HTTPException(400, "Неверный тип")
    cfg = UPGRADES[ut]
    lvl = user[f"upg_{ut}_level"]
    if lvl >= cfg["max_level"]: raise HTTPException(400, "Макс!")
    cost = int(cfg["base_cost"] * (cfg["mult"] ** lvl))
    if user["coins"] < cost: raise HTTPException(400, f"Нужно {cost}")
    upd = {"coins": user["coins"] - cost, f"upg_{ut}_level": lvl + 1}
    if ut == "tap": upd["coins_per_tap"] = user["coins_per_tap"] + 1
    elif ut == "energy":
        upd["max_energy"] = user["max_energy"] + 20
        upd["energy"] = min(user["energy"] + 20, user["max_energy"] + 20)
    elif ut == "multi": upd["multi_tap"] = user["multi_tap"] + 1
    elif ut == "regen": upd["energy_regen"] = round(user["energy_regen"] + 0.15, 2)
    db.update_user_fields(tg_id, upd)
    return user_resp(db.get_user(tg_id))

@app.post("/api/task/complete")
async def task_complete(req: TaskReq):
    tg_id = get_id(req)
    user = db.get_user(tg_id)
    if not user: raise HTTPException(400, "Нет юзера")
    if req.profession_id not in db.get_unlocked(tg_id): raise HTTPException(400, "Не открыто")
    for c in db.get_completed(tg_id, req.profession_id):
        if c["task_index"] == req.task_index:
            return {**user_resp(user), "already": True}
    score = min(max(req.score, 0), 100)
    coin_r = 30 + int(score * 0.7)
    xp_r = 50 + int(score * 0.5)
    if random.random() < user["stat_luck"] * 0.02: coin_r *= 2
    db.complete_task(tg_id, req.profession_id, req.task_index, score)
    user["coins"] += coin_r
    user["xp"] += xp_r
    leveled = process_level_ups(user)
    db.update_user_fields(tg_id, {"coins": user["coins"], "xp": user["xp"],
                                   "level": user["level"], "tokens": user["tokens"]})
    user = db.get_user(tg_id)
    return {**user_resp(user), "coin_r": coin_r, "xp_r": xp_r, "leveled": leveled,
            "completed": db.get_completed(tg_id, req.profession_id)}

@app.post("/api/task/progress")
async def save_task_progress(req: ProgressReq):
    tg_id = get_id(req)
    db.save_progress(tg_id, req.profession_id, req.task_index, req.data)
    return {"ok": True}

@app.get("/api/professions")
async def professions():
    return {"spheres": PROFESSIONS}

# === Данные профессий ===
PROFESSIONS = [
    {"id":"it","name":"IT-сфера","icon":"💻","professions":[
        {"id":"frontend","name":"Frontend-разработчик","icon":"🌐",
         "desc":"Создаёт интерфейсы сайтов и приложений",
         "tools":["HTML/CSS","JavaScript","React","Figma"],"cost":1,
         "tasks":[
             {"title":"Конструктор сайта","type":"site_builder","desc":"Собери лендинг из блоков"},
             {"title":"CSS-мастер","type":"css_challenge","desc":"Стилизуй элементы под макет"},
             {"title":"Исправь вёрстку","type":"debug_html","desc":"Найди и почини баги в коде"},
             {"title":"Адаптивный дизайн","type":"responsive","desc":"Адаптируй сайт под мобильный"},
             {"title":"Финальный проект","type":"site_builder_pro","desc":"Собери полный сайт-портфолио"}
         ]},
        {"id":"backend","name":"Backend-разработчик","icon":"⚙️",
         "desc":"Программирует серверную логику и API",
         "tools":["Python","SQL","Docker","Linux"],"cost":1,
         "tasks":[
             {"title":"SQL-детектив","type":"sql_detective","desc":"Напиши запросы к базе данных"},
             {"title":"API-архитектор","type":"api_builder","desc":"Спроектируй REST API"},
             {"title":"Серверный баг","type":"server_debug","desc":"Найди уязвимость в коде"},
             {"title":"Нагрузка","type":"load_balance","desc":"Оптимизируй сервер под нагрузку"},
             {"title":"Микросервисы","type":"architecture","desc":"Спроектируй архитектуру"}
         ]},
        {"id":"datasci","name":"Data Scientist","icon":"📊",
         "desc":"Анализирует данные и строит ML-модели",
         "tools":["Python","Pandas","TensorFlow","Jupyter"],"cost":1,
         "tasks":[
             {"title":"Анализ данных","type":"data_explorer","desc":"Исследуй датасет и найди инсайты"},
             {"title":"Чистка данных","type":"data_clean","desc":"Очисти данные от аномалий"},
             {"title":"Модель ML","type":"ml_model","desc":"Выбери и настрой модель"},
             {"title":"Визуализация","type":"data_viz","desc":"Построй информативные графики"},
             {"title":"A/B эксперимент","type":"ab_test","desc":"Проведи и проанализируй тест"}
         ]},
        {"id":"cybersec","name":"Кибербезопасность","icon":"🛡️",
         "desc":"Защищает системы от взломов",
         "tools":["Kali Linux","Wireshark","Burp Suite"],"cost":1,
         "tasks":[
             {"title":"Сканер сети","type":"network_scan","desc":"Просканируй сеть на уязвимости"},
             {"title":"Фишинг-детектор","type":"phishing","desc":"Распознай поддельные письма"},
             {"title":"Криптография","type":"crypto_challenge","desc":"Расшифруй перехваченное сообщение"},
             {"title":"Лог-анализ","type":"log_analysis","desc":"Найди следы взлома в логах"},
             {"title":"Инцидент","type":"incident","desc":"Отреагируй на кибератаку"}
         ]}
    ]},
    {"id":"engineering","name":"Инженерия","icon":"🔧","professions":[
        {"id":"robotics","name":"Робототехник","icon":"🤖",
         "desc":"Проектирует и программирует роботов",
         "tools":["Arduino","ROS","C++","3D-печать"],"cost":1,
         "tasks":[
             {"title":"Схема робота","type":"circuit_builder","desc":"Собери электрическую схему"},
             {"title":"Программа движения","type":"robot_code","desc":"Запрограммируй маршрут робота"},
             {"title":"Датчики","type":"sensor_setup","desc":"Настрой систему датчиков"},
             {"title":"Отладка","type":"robot_debug","desc":"Найди ошибку в поведении"},
             {"title":"Робот-проект","type":"robot_project","desc":"Спроектируй робота-помощника"}
         ]},
        {"id":"energy","name":"Энергетик","icon":"⚡",
         "desc":"Работает с энергосистемами",
         "tools":["AutoCAD","MATLAB","SCADA"],"cost":1,
         "tasks":[
             {"title":"Энергобаланс","type":"power_balance","desc":"Рассчитай потребление здания"},
             {"title":"Солнечная станция","type":"solar_setup","desc":"Расположи панели оптимально"},
             {"title":"Авария в сети","type":"grid_emergency","desc":"Устрани неисправность"},
             {"title":"Оптимизация","type":"energy_optimize","desc":"Снизи потребление завода"},
             {"title":"Проект станции","type":"power_plant","desc":"Спроектируй электростанцию"}
         ]}
    ]},
    {"id":"medicine","name":"Медицина","icon":"🏥","professions":[
        {"id":"diagnostics","name":"Врач-диагност","icon":"🔬",
         "desc":"Ставит диагнозы по симптомам и анализам",
         "tools":["МРТ","УЗИ","Анализы","ЭКГ"],"cost":1,
         "tasks":[
             {"title":"Приём пациента","type":"patient_sim","desc":"Проведи приём и поставь диагноз"},
             {"title":"Анализы","type":"lab_results","desc":"Расшифруй результаты анализов"},
             {"title":"Дифдиагноз","type":"diff_diagnosis","desc":"Отличи похожие болезни"},
             {"title":"Неотложка","type":"emergency","desc":"Прими решение в экстренной ситуации"},
             {"title":"Сложный случай","type":"complex_case","desc":"Разбери нетипичный кейс"}
         ]},
        {"id":"biotech","name":"Биотехнолог","icon":"🧬",
         "desc":"Разрабатывает биопрепараты",
         "tools":["ПЦР","CRISPR","Биореакторы"],"cost":1,
         "tasks":[
             {"title":"ПЦР-протокол","type":"pcr_lab","desc":"Проведи ПЦР-анализ"},
             {"title":"Анализ генома","type":"genome","desc":"Найди мутацию в ДНК"},
             {"title":"Культивирование","type":"cell_culture","desc":"Вырасти клеточную культуру"},
             {"title":"Биореактор","type":"bioreactor","desc":"Настрой параметры реактора"},
             {"title":"CRISPR-дизайн","type":"crispr","desc":"Спроектируй генное редактирование"}
         ]}
    ]},
    {"id":"creative","name":"Творчество","icon":"🎨","professions":[
        {"id":"gamedev","name":"Геймдизайнер","icon":"🎮",
         "desc":"Придумывает механики и уровни игр",
         "tools":["Unity","Unreal","Figma"],"cost":1,
         "tasks":[
             {"title":"Левел-дизайн","type":"level_editor","desc":"Построй игровой уровень"},
             {"title":"Баланс","type":"game_balance","desc":"Сбалансируй персонажей"},
             {"title":"Экономика","type":"game_economy","desc":"Настрой внутриигровую экономику"},
             {"title":"Нарратив","type":"narrative","desc":"Напиши диалоговое дерево"},
             {"title":"Прототип","type":"game_prototype","desc":"Создай игровой прототип"}
         ]},
        {"id":"design","name":"UX/UI Дизайнер","icon":"✏️",
         "desc":"Создаёт удобные интерфейсы",
         "tools":["Figma","Sketch","Adobe XD"],"cost":1,
         "tasks":[
             {"title":"Палитра бренда","type":"color_system","desc":"Создай цветовую систему"},
             {"title":"UX-аудит","type":"ux_audit","desc":"Найди проблемы юзабилити"},
             {"title":"Компоненты","type":"ui_kit","desc":"Собери UI-кит"},
             {"title":"Пользовательский путь","type":"user_flow","desc":"Спроектируй UX-флоу"},
             {"title":"Редизайн","type":"redesign","desc":"Улучши существующий интерфейс"}
         ]}
    ]},
    {"id":"business","name":"Бизнес","icon":"💼","professions":[
        {"id":"marketing","name":"Маркетолог","icon":"📢",
         "desc":"Продвигает продукты и бренды",
         "tools":["Analytics","Canva","Метрика","CRM"],"cost":1,
         "tasks":[
             {"title":"Целевая аудитория","type":"target_audience","desc":"Определи и сегментируй ЦА"},
             {"title":"Рекламная кампания","type":"ad_campaign","desc":"Запусти и оптимизируй рекламу"},
             {"title":"Контент-стратегия","type":"content_plan","desc":"Разработай контент-план"},
             {"title":"Аналитика","type":"marketing_analytics","desc":"Проанализируй метрики"},
             {"title":"Запуск продукта","type":"product_launch","desc":"Выведи продукт на рынок"}
         ]},
        {"id":"pm","name":"Менеджер проектов","icon":"📋",
         "desc":"Управляет командой и проектами",
         "tools":["Jira","Trello","Agile/Scrum"],"cost":1,
         "tasks":[
             {"title":"Планирование спринта","type":"sprint_plan","desc":"Спланируй двухнедельный спринт"},
             {"title":"Управление рисками","type":"risk_mgmt","desc":"Оцени и минимизируй риски"},
             {"title":"Стендап","type":"standup","desc":"Проведи утреннюю встречу"},
             {"title":"Конфликт в команде","type":"team_conflict","desc":"Разреши конфликт"},
             {"title":"Ретроспектива","type":"retro","desc":"Проведи ретро и улучши процесс"}
         ]}
    ]},
    {"id":"science","name":"Наука","icon":"🔬","professions":[
        {"id":"chemistry","name":"Химик","icon":"⚗️",
         "desc":"Исследует вещества и создаёт новые",
         "tools":["Спектрометр","Хроматограф","Реактор"],"cost":1,
         "tasks":[
             {"title":"Лабораторный опыт","type":"chem_lab","desc":"Проведи химический эксперимент"},
             {"title":"Анализ вещества","type":"substance_analysis","desc":"Определи неизвестное вещество"},
             {"title":"Техника безопасности","type":"lab_safety","desc":"Проверь соблюдение ТБ"},
             {"title":"Синтез","type":"synthesis","desc":"Проведи многостадийный синтез"},
             {"title":"Исследование","type":"chem_research","desc":"Спланируй эксперимент"}
         ]},
        {"id":"physics","name":"Физик","icon":"⚛️",
         "desc":"Изучает фундаментальные законы природы",
         "tools":["MATLAB","Осциллограф","Ускоритель"],"cost":1,
         "tasks":[
             {"title":"Механика","type":"physics_sim","desc":"Реши задачу по механике"},
             {"title":"Электричество","type":"circuit_sim","desc":"Собери электрическую цепь"},
             {"title":"Волны","type":"wave_sim","desc":"Исследуй волновые процессы"},
             {"title":"Эксперимент","type":"physics_experiment","desc":"Проведи измерения"},
             {"title":"Моделирование","type":"physics_model","desc":"Построй физическую модель"}
         ]}
    ]}
]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
