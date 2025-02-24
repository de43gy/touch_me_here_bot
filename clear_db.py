import asyncio
import aiosqlite
from config import DATABASE_PATH

async def clear_database():
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("DELETE FROM slots")
            
            #очистить и таблицу пользователей
            # await db.execute("DELETE FROM users")
            
            await db.execute("DELETE FROM sqlite_sequence WHERE name='slots'")
            
            await db.commit()
            print("База данных успешно очищена!")
    except Exception as e:
        print(f"Ошибка при очистке базы данных: {e}")

if __name__ == "__main__":
    asyncio.run(clear_database())