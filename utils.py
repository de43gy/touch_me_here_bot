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
        
        display_time = slot['time']
        if "-" in display_time:
            start_time, end_time = display_time.split("-")
            if ":" not in start_time.strip():
                start_time = f"{start_time.strip()}:00"
            if ":" not in end_time.strip():
                end_time = f"{end_time.strip()}:00"
            display_time = f"{start_time.strip()}-{end_time.strip()}"
        elif ":" not in display_time:
            display_time = f"{display_time}:00"
        
        if giver_comment:
            return f"{slot['day']} {display_time} - {giver_username} ({giver_comment})"
        else:
            return f"{slot['day']} {display_time} - {giver_username}"
    except Exception as e:
      logger.error(f"Ошибка при форматировании информации о слоте: {e}")
      return f"{slot['day']} {slot['time']} - Ошибка отображения"

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
        normalized_time = normalize_time_format(time)
        
        time_for_comparison = get_time_for_comparison(time)
        
        hour_for_comparison = get_hour_for_comparison(time)
        
        time_variants = [normalized_time, time_for_comparison, time, hour_for_comparison]
        if ":" in time_for_comparison:
            time_variants.append(time_for_comparison.split(":")[0])
        
        time_variants = list(set(time_variants))
        
        logger.info(f"Проверка доступности слота {day} {time} (варианты сравнения: {time_variants})")
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            placeholders = ", ".join(["?"] * len(time_variants))
            query = f"""
            SELECT id, giver_id, receiver_id, time FROM slots 
            WHERE day = ? AND status = 'active'
            """
            
            cursor = await db.execute(query, (day,))
            existing_slots = await cursor.fetchall()
            
            if not existing_slots:
                logger.info(f"Слот {day} {time} свободен, так как нет существующих слотов")
                return True
            
            for slot in existing_slots:
                slot_id, giver_id, receiver_id, slot_time = slot
                
                slot_normalized = normalize_time_format(slot_time)
                slot_comparison = get_time_for_comparison(slot_time)
                slot_hour = get_hour_for_comparison(slot_time)
                
                time_match = (
                    time_for_comparison == slot_comparison or
                    normalized_time == slot_normalized or
                    time == slot_time or
                    hour_for_comparison == slot_hour
                )
                
                if not time_match:
                    continue
                
                if user_id is not None:
                    if giver_id == user_id:
                        logger.info(f"Пользователь {user_id} уже является дарителем в слоте {slot_id} (время: {slot_time})")
                        return False
                    
                    if receiver_id is not None:
                        logger.info(f"Слот {slot_id} уже занят получателем {receiver_id} (время: {slot_time})")
                        return False
                    
                    cursor = await db.execute(
                        """
                        SELECT id FROM slots 
                        WHERE day = ? AND status = 'active' 
                        AND (giver_id = ? OR receiver_id = ?)
                        """,
                        (day, user_id, user_id)
                    )
                    user_slots = await cursor.fetchall()
                    
                    for user_slot in user_slots:
                        user_slot_id = user_slot[0]
                        if user_slot_id != slot_id:
                            cursor = await db.execute(
                                "SELECT time FROM slots WHERE id = ?", (user_slot_id,)
                            )
                            user_slot_time = await cursor.fetchone()
                            if user_slot_time:
                                user_slot_hour = get_hour_for_comparison(user_slot_time[0])
                                if user_slot_hour == hour_for_comparison:
                                    logger.info(f"Пользователь {user_id} уже записан на другой слот {user_slot_id} в этот же час ({user_slot_time[0]})")
                                    return False
                else:
                    if receiver_id is not None:
                        logger.info(f"Слот {slot_id} уже занят (без проверки конкретного пользователя)")
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

def normalize_time_format(time_str):
    """
    Нормализует формат времени, добавляя :00 если указан только час.
    Также обрабатывает форматы с диапазонами.
    
    Args:
        time_str (str): Строка с временем в различных форматах
        
    Returns:
        str: Нормализованная строка с временем
    """
    if not time_str:
        return time_str
        
    if "-" in time_str:
        start_time, end_time = time_str.split("-")
        start_time = start_time.strip()
        end_time = end_time.strip()
        
        if start_time.isdigit():
            start_time = f"{start_time}:00"
        elif ":" not in start_time:
            start_time = f"{start_time}:00"
        
        if end_time.isdigit():
            end_time = f"{end_time}:00"
        elif ":" not in end_time:
            end_time = f"{end_time}:00"
            
        return f"{start_time}-{end_time}"
    
    if time_str.isdigit():
        return f"{time_str}:00"
    
    if ":" not in time_str:
        return f"{time_str}:00"
    
    return time_str

def get_time_for_comparison(time_str):
    """
    Получает время для сравнения (первое время из диапазона, если это диапазон).
    
    Args:
        time_str (str): Строка с временем или диапазоном времени
        
    Returns:
        str: Время для сравнения в формате HH:MM
    """
    normalized = normalize_time_format(time_str)
    
    if "-" in normalized:
        normalized = normalized.split("-")[0].strip()
    
    return normalized

def get_hour_for_comparison(time_str):
    """
    Получает только час для более лояльного сравнения слотов.
    
    Args:
        time_str (str): Строка с временем в любом формате
        
    Returns:
        str: Часовая часть времени
    """
    normalized = get_time_for_comparison(time_str)
    
    if ":" in normalized:
        return normalized.split(":")[0]
    
    return normalized