import aiosqlite

DB_NAME = "appointments.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price INTEGER,
            duration INTEGER
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS masters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service_id INTEGER,
            master_id INTEGER,
            date TEXT,
            time TEXT
        )
        """)
        await db.commit()


async def insert_service(name, price, duration):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO services (name, price, duration) VALUES (?, ?, ?)",
            (name, price, duration)
        )
        await db.commit()


async def get_services():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM services") as cursor:
            return await cursor.fetchall()


async def get_masters():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM masters") as cursor:
            return await cursor.fetchall()


async def get_booked_slots(date, master_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT time FROM appointments WHERE date=? AND master_id=?",
            (date, master_id)
        ) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]


async def add_appointment(user_id, service_id, master_id, date, time):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO appointments (user_id, service_id, master_id, date, time) VALUES (?, ?, ?, ?, ?)",
            (user_id, service_id, master_id, date, time)
        )
        await db.commit()

# ================= MASTERS =================

async def insert_master(name):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO masters (name) VALUES (?)",
            (name,)
        )
        await db.commit()


async def delete_master(master_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM masters WHERE id=?",
            (master_id,)
        )
        await db.commit()
