import aiosqlite
from comfig import DATABASE_PATH

async def create_tables():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                giver_id INTEGER,
                reciever_id INTEGER,
                day TEXT,
                time TEXT,
                gitver_comment TEXT,
                reciever_comment TEXT,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (giver_id) REFERENCES users(id),
                FOREIGN KEY (reciever_id) REFERENCES users(id)
            )
            """
        )
        await db.commit()

async def add_user(user_id, username):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)", (user_id, username))