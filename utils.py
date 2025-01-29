from datetime import datetime, timedelta
from database import get_user_by_id
from config import ADMIN_ID
from aiogram import Bot
import aiosqlite
from config import DATABASE_PATH
import logging

logger = logging.getLogger(__name__)

async def send_notification_to_admin(bot: Bot, message: str):
    try:
        await bot.send_message(ADMIN_ID, message)
        logger.info(f"Отправлено уведомление администратору: {message}")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления администратору: {e}")

async def format_slot_info(slot):
    try:
        giver = await get_user_by_id(slot['giver_id'])
        giver_username = giver['username'] if giver else "Неизвестный пользователь"
        giver_comment = slot['giver_comment']
        if giver_comment:
            return f"{slot['day']} {slot['time']} - {giver_username} ({giver_comment})"
        else:
            return f"{slot['day']} {slot['time']} - {giver_username}"
    except Exception as e:
      logger.error(f"Ошибка при форматировании информации о слоте: {e}")

async def is_slot_available(day, time):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                "SELECT id FROM slots WHERE day = ? AND time = ? AND status = 'active' AND receiver_id IS NULL",
                (day, time)
            )
            existing_slot = await cursor.fetchone()
            return existing_slot is None
    except Exception as e:
        logger.error(f"Ошибка при проверке доступности слота: {e}")
        return False

async def is_cancellation_allowed(slot):
    try:
        slot_time = datetime.strptime(f"{slot['day']} {slot['time']}", "%d %B %H:%M")
        return datetime.now() < slot_time - timedelta(minutes=30)
    except Exception as e:
        logger.error(f"Ошибка при проверке возможности отмены слота: {e}")
        return False