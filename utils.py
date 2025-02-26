from datetime import datetime, timedelta
from database import get_user_by_id
from config import ADMIN_ID
from aiogram import Bot
import aiosqlite
from config import DATABASE_PATH
import logging
import pytz

logger = logging.getLogger(__name__)

MOSCOW_TZ = pytz.timezone('Europe/Moscow')

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

async def is_slot_available(day, time, user_id=None):
    """
    Проверяет доступность слота для записи.
    
    Args:
        day: День слота
        time: Время слота
        user_id: ID пользователя (для проверки повторной записи)
        
    Returns:
        bool: True если слот доступен, False если занят
    """
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                "SELECT id FROM slots WHERE day = ? AND time = ? AND status = 'active'",
                (day, time)
            )
            existing_slot = await cursor.fetchone()
            
            if existing_slot is None:
                return True
                
            if user_id:
                cursor = await db.execute(
                    "SELECT id FROM slots WHERE day = ? AND time = ? AND status = 'active' AND giver_id = ?",
                    (day, time, user_id)
                )
                user_slot = await cursor.fetchone()
                if user_slot:
                    return False
                
                cursor = await db.execute(
                    "SELECT id FROM slots WHERE day = ? AND time = ? AND status = 'active' AND receiver_id = ?",
                    (day, time, user_id)
                )
                receiver_slot = await cursor.fetchone()
                if receiver_slot:
                    return False
            
            return False
    except Exception as e:
        logger.error(f"Ошибка при проверке доступности слота: {e}")
        return False

async def is_cancellation_allowed(slot):
    try:
        day_parts = slot['day'].split()
        day_num = int(day_parts[0])
        month_name = day_parts[1]
        month_map = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
                    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12}
        month_num = month_map.get(month_name.lower(), 0)
        
        time_str = slot['time'].split("-")[0].strip()
        time_parts = time_str.split(":")
        hour = int(time_parts[0])
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
        
        now = datetime.now(MOSCOW_TZ)
        slot_datetime = datetime(now.year, month_num, day_num, hour, minute, tzinfo=MOSCOW_TZ)
        
        return now < slot_datetime - timedelta(minutes=30)
    except Exception as e:
        logger.error(f"Ошибка при проверке возможности отмены слота: {e}")
        return False

def get_current_moscow_time():
    return datetime.now(MOSCOW_TZ)

def parse_slot_datetime(day, time):
    try:
        day_parts = day.split()
        day_num = int(day_parts[0])
        month_name = day_parts[1]
        month_map = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
                    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12}
        month_num = month_map.get(month_name.lower(), 0)
        
        time_str = time.split("-")[0].strip()
        time_parts = time_str.split(":")
        hour = int(time_parts[0])
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
        
        now = datetime.now(MOSCOW_TZ)
        return datetime(now.year, month_num, day_num, hour, minute, tzinfo=MOSCOW_TZ)
    except Exception as e:
        logger.error(f"Ошибка при парсинге даты/времени слота: {e}")
        return None