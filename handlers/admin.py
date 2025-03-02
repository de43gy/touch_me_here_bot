from aiogram import types, Router, F
from aiogram.filters import Command
import aiosqlite
from config import DATABASE_PATH, ADMIN_ID
import logging
from utils import normalize_time_format

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

@router.message(Command("extended_stats"))
async def cmd_extended_stats(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                """
                SELECT 
                    COUNT(*) as total_slots,
                    SUM(CASE WHEN receiver_id IS NOT NULL THEN 1 ELSE 0 END) as booked_slots,
                    COUNT(DISTINCT giver_id) as unique_givers,
                    COUNT(DISTINCT receiver_id) as unique_receivers
                FROM slots
                WHERE status = 'active'
                """
            )
            overall_stats = await cursor.fetchone()
            
            cursor = await db.execute(
                """
                SELECT 
                    day,
                    COUNT(*) as total_slots,
                    SUM(CASE WHEN receiver_id IS NOT NULL THEN 1 ELSE 0 END) as booked_slots,
                    COUNT(DISTINCT giver_id) as unique_givers,
                    COUNT(DISTINCT receiver_id) as unique_receivers
                FROM slots
                WHERE status = 'active'
                GROUP BY day
                ORDER BY day
                """
            )
            daily_stats = await cursor.fetchall()
            
            stats_message = (
                f"📊 <b>Расширенная статистика бота:</b>\n\n"
                f"<b>ОБЩАЯ СТАТИСТИКА:</b>\n"
                f"🔶 Всего слотов для массажа: {overall_stats[0]}\n"
                f"🔷 Забронировано получателями: {overall_stats[1]}\n"
                f"🔸 Уникальных дарителей: {overall_stats[2]}\n"
                f"🔹 Уникальных получателей: {overall_stats[3]}\n\n"
                f"<b>СТАТИСТИКА ПО ДНЯМ:</b>\n"
            )
            
            for day_stat in daily_stats:
                day, total, booked, givers, receivers = day_stat
                stats_message += (
                    f"\n<b>{day}</b>\n"
                    f"- Всего слотов: {total}\n"
                    f"- Забронировано: {booked}\n"
                    f"- Свободно: {total - booked}\n"
                    f"- Уникальных дарителей: {givers}\n"
                    f"- Уникальных получателей: {receivers}\n"
                )
            
            await message.answer(stats_message, parse_mode="HTML")
            logger.info(f"Администратор {message.from_user.username} (ID: {message.from_user.id}) запросил расширенную статистику.")
    except Exception as e:
        await message.answer(f"Произошла ошибка при получении расширенной статистики: {e}")
        logger.error(f"Ошибка при получении расширенной статистики: {e}")

@router.message(Command("hourly_stats"))
async def cmd_hourly_stats(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                """
                SELECT 
                    day,
                    time,
                    CASE WHEN receiver_id IS NULL THEN 'свободен' ELSE 'занят' END as status,
                    COUNT(*) as count
                FROM slots
                WHERE status = 'active'
                GROUP BY day, time, CASE WHEN receiver_id IS NULL THEN 'свободен' ELSE 'занят' END
                ORDER BY day, time
                """
            )
            time_stats = await cursor.fetchall()
            
            days_data = {}
            for row in time_stats:
                day, time_slot, slot_status, count = row
                if day not in days_data:
                    days_data[day] = []
                days_data[day].append((time_slot, slot_status, count))
            
            stats_message = f"📊 <b>Статистика по часам:</b>\n\n"
            
            for day, time_entries in days_data.items():
                stats_message += f"<b>{day}</b>\n"
                
                for time_entry in time_entries:
                    time_slot, slot_status, count = time_entry
                    time_display = normalize_time_format(time_slot)
                    status_emoji = "✅" if slot_status == "занят" else "⏳"
                    stats_message += f"{status_emoji} {time_display}: {count} слот(ов) ({slot_status})\n"
                
                stats_message += "\n"
            
            max_message_length = 4096
            if len(stats_message) > max_message_length:
                chunks = [stats_message[i:i+max_message_length] for i in range(0, len(stats_message), max_message_length)]
                for chunk in chunks:
                    await message.answer(chunk, parse_mode="HTML")
            else:
                await message.answer(stats_message, parse_mode="HTML")
                
            logger.info(f"Администратор {message.from_user.username} (ID: {message.from_user.id}) запросил статистику по часам.")
    except Exception as e:
        await message.answer(f"Произошла ошибка при получении статистики по часам: {e}")
        logger.error(f"Ошибка при получении статистики по часам: {e}")