import aiosqlite
import time
import os

DB_PATH = os.getenv("DB_PATH", "reality.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE NOT NULL,
                username TEXT NOT NULL DEFAULT '',
                avatar INTEGER NOT NULL DEFAULT 1,
                coins INTEGER NOT NULL DEFAULT 0,
                tokens INTEGER NOT NULL DEFAULT 0,
                xp INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 0,
                energy INTEGER NOT NULL DEFAULT 100,
                max_energy INTEGER NOT NULL DEFAULT 100,
                last_energy_update REAL NOT NULL DEFAULT 0,
                mpc INTEGER NOT NULL DEFAULT 1,
                auto_regen REAL NOT NULL DEFAULT 2.0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS upgrades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('mpc', 'stamina', 'regen')),
                level INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, type),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS unlocked_professions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                profession_id TEXT NOT NULL,
                unlocked_at REAL NOT NULL,
                UNIQUE(user_id, profession_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS completed_simulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                profession_id TEXT NOT NULL,
                score INTEGER NOT NULL DEFAULT 0,
                completed_at REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.commit()


async def get_user(tg_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        user = dict(row)
        # Пересчитываем энергию по времени
        now = time.time()
        elapsed = now - user["last_energy_update"]
        regen = user["auto_regen"]
        regenerated = int(elapsed * regen)
        if regenerated > 0:
            new_energy = min(user["energy"] + regenerated, user["max_energy"])
            await db.execute(
                "UPDATE users SET energy = ?, last_energy_update = ? WHERE tg_id = ?",
                (new_energy, now, tg_id),
            )
            await db.commit()
            user["energy"] = new_energy
            user["last_energy_update"] = now
        return user


async def create_user(tg_id: int, username: str, avatar: int) -> dict:
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO users (tg_id, username, avatar, last_energy_update)
               VALUES (?, ?, ?, ?)""",
            (tg_id, username, avatar, now),
        )
        user_id_cursor = await db.execute(
            "SELECT id FROM users WHERE tg_id = ?", (tg_id,)
        )
        row = await user_id_cursor.fetchone()
        user_id = row[0]
        for upgrade_type in ("mpc", "stamina", "regen"):
            await db.execute(
                "INSERT INTO upgrades (user_id, type, level) VALUES (?, ?, 0)",
                (user_id, upgrade_type),
            )
        await db.commit()
    return await get_user(tg_id)


async def update_user(tg_id: int, **fields) -> dict | None:
    if not fields:
        return await get_user(tg_id)
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [tg_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE users SET {set_clause} WHERE tg_id = ?", values
        )
        await db.commit()
    return await get_user(tg_id)


async def get_upgrades(tg_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT u.type, u.level FROM upgrades u
               JOIN users usr ON usr.id = u.user_id
               WHERE usr.tg_id = ?""",
            (tg_id,),
        )
        rows = await cursor.fetchall()
        return {row["type"]: row["level"] for row in rows}


async def upgrade_level(tg_id: int, upgrade_type: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE upgrades SET level = level + 1
               WHERE user_id = (SELECT id FROM users WHERE tg_id = ?)
               AND type = ?""",
            (tg_id, upgrade_type),
        )
        await db.commit()
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT level FROM upgrades
               WHERE user_id = (SELECT id FROM users WHERE tg_id = ?)
               AND type = ?""",
            (tg_id, upgrade_type),
        )
        row = await cursor.fetchone()
        return row["level"] if row else 0


async def unlock_profession(tg_id: int, profession_id: str) -> bool:
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                """INSERT INTO unlocked_professions (user_id, profession_id, unlocked_at)
                   VALUES ((SELECT id FROM users WHERE tg_id = ?), ?, ?)""",
                (tg_id, profession_id, now),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def get_unlocked_professions(tg_id: int) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """SELECT profession_id FROM unlocked_professions
               WHERE user_id = (SELECT id FROM users WHERE tg_id = ?)""",
            (tg_id,),
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def complete_simulation(tg_id: int, profession_id: str, score: int):
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO completed_simulations (user_id, profession_id, score, completed_at)
               VALUES ((SELECT id FROM users WHERE tg_id = ?), ?, ?, ?)""",
            (tg_id, profession_id, score, now),
        )
        await db.commit()


async def get_completed_simulations(tg_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT profession_id, score, completed_at FROM completed_simulations
               WHERE user_id = (SELECT id FROM users WHERE tg_id = ?)
               ORDER BY completed_at DESC""",
            (tg_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
