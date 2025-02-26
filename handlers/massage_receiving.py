from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from keyboards import main_menu, reminder_menu
from database import get_available_slots, book_slot, get_slot_by_id
from utils import format_slot_info, is_slot_available, get_current_moscow_time, parse_slot_datetime, normalize_time_format
from datetime import datetime, timedelta
import asyncio
import logging
import pytz

from aiogram import Bot
from config import BOT_TOKEN

logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)

class ReceiveMassage(StatesGroup):
    confirmation = State()
    day = State()
    time = State()
    comment = State()

router = Router()

@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.clear()
    
    await callback_query.message.answer("Вы вернулись в главное меню", reply_markup=main_menu)
    
    try:
        await callback_query.message.delete()
    except Exception as e:
        logger.error(f"Ошибка при удалении сообщения: {e}")

@router.message(F.text == "/debug_time")
async def debug_time(message: types.Message):
    try:
        now_utc = datetime.now(pytz.UTC)
        now_moscow = get_current_moscow_time()
        
        result = "Отладка времени:\n\n"
        result += f"UTC: {now_utc}\n"
        result += f"Московское время: {now_moscow}\n"
        result += f"Разница: {now_moscow.tzinfo.utcoffset(now_moscow)}\n\n"
        
        import aiosqlite
        from config import DATABASE_PATH
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("SELECT * FROM slots WHERE status = 'active'")
            rows = await cursor.fetchall()
            
            if not rows:
                result += "Нет активных слотов в базе данных."
            else:
                columns = [description[0] for description in cursor.description]
                result += "Активные слоты:\n\n"
                
                for row in rows:
                    slot = dict(zip(columns, row))
                    time_value = slot['time']
                    normalized_time = normalize_time_format(time_