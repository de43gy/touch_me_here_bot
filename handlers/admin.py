from aiogram import types, Router, F
from aiogram.filters import Command
import aiosqlite
from config import DATABASE_PATH, ADMIN_ID
import logging

logger = logging.getLogger(__name__)

router = Router()

@router.message(Command("clear_db"))
async def cmd_clear_db(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("У вас нет прав для выполнения этой команды.")
        logger.warning(f"Пользователь {message.from_user.username} (ID: {message.from_user.id}) "
                       f"попытался выполнить команду /clear_db без прав администратора.")
        return

    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("DELETE FROM slots")
            
            await db.execute("DELETE FROM sqlite_sequence WHERE name='slots'")
            
            await db.commit()
            
        await message.answer("База данных успешно очищена! Все записи на массаж удалены.")
        logger.info(f"Администратор {message.from_user.username} (ID: {message.from_user.id}) очистил базу данных.")
    except Exception as e:
        await message.answer(f"Произошла ошибка при очистке базы данных: {e}")
        logger.error(f"Ошибка при очистке базы данных: {e}")

@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            users_count = await cursor.fetchone()
            
            cursor = await db.execute("SELECT COUNT(*) FROM slots")
            slots_count = await cursor.fetchone()
            
            cursor = await db.execute("SELECT COUNT(*) FROM slots WHERE receiver_id IS NOT NULL")
            booked_slots = await cursor.fetchone()
            
            cursor = await db.execute("SELECT COUNT(*) FROM slots WHERE receiver_id IS NULL")
            available_slots = await cursor.fetchone()
            
            stats_message = (
                f"📊 Статистика бота:\n\n"
                f"👤 Всего пользователей: {users_count[0]}\n"
                f"🗓 Всего слотов: {slots_count[0]}\n"
                f"✅ Забронированных слотов: {booked_slots[0]}\n"
                f"⏳ Доступных слотов: {available_slots[0]}\n"
            )
            
            await message.answer(stats_message)
            logger.info(f"Администратор {message.from_user.username} (ID: {message.from_user.id}) запросил статистику.")
    except Exception as e:
        await message.answer(f"Произошла ошибка при получении статистики: {e}")
        logger.error(f"Ошибка при получении статистики: {e}")