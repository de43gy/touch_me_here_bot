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
                "SELECT id, giver_id, receiver_id FROM slots WHERE day = ? AND time = ? AND status = 'active'",
                (day, time)
            )
            existing_slots = await cursor.fetchall()
            
            if not existing_slots:
                return True
            
            for slot in existing_slots:
                slot_id, giver_id, receiver_id = slot
                
                if user_id is not None:
                    if giver_id == user_id:
                        logger.info(f"Пользователь {user_id} уже является дарителем в слоте {slot_id}")
                        return False
                    
                    if receiver_id is not None:
                        logger.info(f"Слот {slot_id} уже занят получателем {receiver_id}")
                        return False
                
                if user_id is not None:
                    cursor = await db.execute(
                        """
                        SELECT id FROM slots 
                        WHERE day = ? AND time = ? AND status = 'active' 
                        AND (giver_id = ? OR receiver_id = ?)
                        """,
                        (day, time, user_id, user_id)
                    )
                    conflicting_slot = await cursor.fetchone()
                    if conflicting_slot:
                        logger.info(f"Пользователь {user_id} уже записан на другой слот в это время")
                        return False
                else:
                    if receiver_id is not None:
                        return False
            
            logger.info(f"Слот доступен для записи в {day} {time}")
            return True
    except Exception as e:
        logger.error(f"Ошибка при проверке доступности слота: {e}")
        return False
async def is_cancellation_allowed(slot):
    try:
        slot_datetime = parse_slot_datetime(slot['day'], slot['time'])
        if not slot_datetime:
            return False
            
        now = get_current_moscow_time()
        
        return now < slot_datetime - timedelta(minutes=30)
    except Exception as e:
        logger.error(f"Ошибка при проверке возможности отмены слота: {e}")
        return False

def get_current_moscow_time():
    """
    Возвращает текущее время в московской временной зоне.
    """
    return datetime.now(pytz.UTC).astimezone(MOSCOW_TZ)

def normalize_time_format(time_str):
    """
    Нормализует формат времени, добавляя :00 если указан только час.
    
    Args:
        time_str (str): Строка с временем в формате "HH:MM" или просто "HH"
        
    Returns:
        str: Нормализованная строка с временем
    """
    if time_str.isdigit():
        return f"{time_str}:00"
        
    if "-" in time_str:
        time_parts = time_str.split("-")
        first_part = time_parts[0].strip()
        if first_part.isdigit():
            return f"{first_part}:00"
    
    return time_str

def parse_slot_datetime(day, time):
    """
    Парсит дату и время слота в объект datetime с московской временной зоной.
    
    Args:
        day (str): День слота в формате "DD месяц"
        time (str): Время слота в формате "HH:MM-HH:MM" или просто "HH"
        
    Returns:
        datetime: Объект datetime с установленной московской временной зоной,
                 или None в случае ошибки
    """
    try:
        day_parts = day.split()
        if len(day_parts) < 2:
            logger.error(f"Некорректный формат дня: {day}")
            return None
            
        day_num = int(day_parts[0])
        month_name = day_parts[1]
        
        month_map = {
            "января": 1, "февраля": 2, "марта": 3, "апреля": 4, 
            "мая": 5, "июня": 6, "июля": 7, "августа": 8, 
            "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12
        }
        month_num = month_map.get(month_name.lower())
        
        if not month_num:
            logger.error(f"Некорректное название месяца: {month_name}")
            return None
        
        normalized_time = normalize_time_format(time)
        
        time_str = normalized_time.split("-")[0].strip()
        
        if ":" not in time_str:
            time_str = f"{time_str}:00"
            
        time_parts = time_str.split(":")
        
        if len(time_parts) < 2:
            hour = int(time_parts[0])
            minute = 0
        else:
            hour = int(time_parts[0])
            minute = int(time_parts[1])
        
        current_year = datetime.now().year
        
        naive_datetime = datetime(current_year, month_num, day_num, hour, minute)
        slot_datetime = MOSCOW_TZ.localize(naive_datetime)
        
        logger.info(f"Создан datetime для слота: {slot_datetime} (day={day}, time={time})")
        
        return slot_datetime
    except Exception as e:
        logger.error(f"Ошибка при парсинге даты/времени слота ({day} {time}): {e}")
        return None