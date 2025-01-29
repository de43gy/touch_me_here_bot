import aiosqlite
from config import DATABASE_PATH
import logging

logger = logging.getLogger(__name__)

async def create_tables():
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    giver_id INTEGER,
                    receiver_id INTEGER,
                    day TEXT,
                    time TEXT,
                    giver_comment TEXT,
                    receiver_comment TEXT,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY (giver_id) REFERENCES users(id),
                    FOREIGN KEY (receiver_id) REFERENCES users(id)
                )
                """
            )
            await db.commit()
            logger.info("Таблицы успешно созданы.")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")

async def add_user(user_id, username):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)", (user_id, username))
            await db.commit()
            logger.info(f"Пользователь {username} (ID: {user_id}) добавлен в базу данных.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя {username} (ID: {user_id}): {e}")

async def add_slot(giver_id, day, time, giver_comment):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO slots (giver_id, day, time, giver_comment) VALUES (?, ?, ?, ?)",
                (giver_id, day, time, giver_comment)
            )
            await db.commit()
            logger.info(f"Слот добавлен: giver_id={giver_id}, day={day}, time={time}, comment='{giver_comment}'")
    except Exception as e:
        logger.error(f"Ошибка при добавлении слота: {e}")

async def get_available_slots():
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                "SELECT * FROM slots WHERE receiver_id IS NULL AND status = 'active'"
            )
            rows = await cursor.fetchall()
            columns = [column[0] for column in cursor.description]
            slots = []
            for row in rows:
                slot = dict(zip(columns, row))
                slots.append(slot)
            logger.info(f"Получено {len(slots)} доступных слотов.")
            return slots
    except Exception as e:
        logger.error(f"Ошибка при получении доступных слотов: {e}")
        return []

async def get_slot_by_id(slot_id):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                "SELECT * FROM slots WHERE id = ? AND status = 'active'",
                (slot_id,)
            )
            row = await cursor.fetchone()
            if row:
                columns = [column[0] for column in cursor.description]
                slot = dict(zip(columns, row))
                logger.info(f"Слот с ID {slot_id} успешно получен.")
                return slot
            else:
                logger.warning(f"Слот с ID {slot_id} не найден.")
                return None
    except Exception as e:
        logger.error(f"Ошибка при получении слота по ID {slot_id}: {e}")
        return None

async def book_slot(slot_id, receiver_id, receiver_comment):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "UPDATE slots SET receiver_id = ?, receiver_comment = ? WHERE id = ? AND receiver_id IS NULL AND status = 'active'",
                (receiver_id, receiver_comment, slot_id)
            )
            await db.commit()
            logger.info(f"Слот с ID {slot_id} забронирован пользователем {receiver_id}.")
    except Exception as e:
        logger.error(f"Ошибка при бронировании слота с ID {slot_id}: {e}")

async def get_user_slots(user_id):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                "SELECT * FROM slots WHERE (giver_id = ? OR receiver_id = ?) AND status = 'active'",
                (user_id, user_id)
            )
            rows = await cursor.fetchall()
            columns = [column[0] for column in cursor.description]
            slots = []
            for row in rows:
                slot = dict(zip(columns, row))
                slots.append(slot)
            logger.info(f"Получено {len(slots)} слотов для пользователя {user_id}.")
            return slots
    except Exception as e:
        logger.error(f"Ошибка при получении слотов пользователя {user_id}: {e}")
        return []

async def cancel_slot(slot_id, canceled_by):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            if canceled_by == "giver":
                await db.execute("UPDATE slots SET status = 'canceled', receiver_id = NULL, receiver_comment = NULL WHERE id = ?", (slot_id,))
            else:  # canceled_by == "receiver"
                await db.execute("UPDATE slots SET status = 'canceled' WHERE id = ?", (slot_id,))
            await db.commit()
            logger.info(f"Слот с ID {slot_id} отменен пользователем {canceled_by}.")
    except Exception as e:
        logger.error(f"Ошибка при отмене слота с ID {slot_id}: {e}")

async def get_user_by_id(user_id):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()
            if row:
                columns = [column[0] for column in cursor.description]
                user = dict(zip(columns, row))
                logger.info(f"Пользователь с ID {user_id} успешно получен.")
                return user
            else:
                logger.warning(f"Пользователь с ID {user_id} не найден.")
                return None
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя по ID {user_id}: {e}")
        return None