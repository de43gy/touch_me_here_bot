from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from keyboards import main_menu, reminder_menu
from database import add_slot
from utils import is_slot_available, get_current_moscow_time, parse_slot_datetime, normalize_time_format
from datetime import datetime, timedelta
import asyncio
import logging
import pytz
import re

from aiogram import Bot
from config import BOT_TOKEN

logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)

class GiveMassage(StatesGroup):
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

@router.message(F.text == "/debug_slots")
async def debug_slots(message: types.Message):
    try:
        import aiosqlite
        from config import DATABASE_PATH
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("SELECT * FROM slots WHERE status = 'active'")
            rows = await cursor.fetchall()
            
            if not rows:
                await message.answer("Нет активных слотов в базе данных.")
                return
                
            columns = [description[0] for description in cursor.description]
            
            result = "Активные слоты:\n\n"
            for row in rows:
                slot = dict(zip(columns, row))
                time_value = slot['time']
                normalized_time = normalize_time_format(time_value)
                slot_datetime = parse_slot_datetime(slot['day'], time_value)
                
                result += f"ID: {slot['id']}\n"
                result += f"День: {slot['day']}\n"
                result += f"Время (исходное): {time_value}\n"
                result += f"Время (нормализованное): {normalized_time}\n"
                result += f"Дата/время (объект): {slot_datetime}\n"
                result += f"Giver ID: {slot['giver_id']}\n"
                result += f"Receiver ID: {slot['receiver_id']}\n"
                result += f"Статус: {slot['status']}\n\n"
                
            await message.answer(result)
    except Exception as e:
        logger.error(f"Ошибка при отладке слотов: {e}")
        await message.answer(f"Ошибка при отладке: {e}")

SLOTS_SCHEDULE = {
    "28 февраля": ["16:00-17:00", "19:00-20:00", "20:00-21:00", "23:00-00:00"],
    "1 марта": ["00:00-01:00", "02:00-03:00", "03:00-04:00", "04:00-05:00", 
                "05:00-06:00", "06:00-07:00", "08:00-09:00", "10:00-11:00",
                "11:00-12:00", "12:00-13:00", "13:00-14:00", "14:00-15:00",
                "15:00-16:00", "17:30-18:00", "18:00-19:00", "21:00-22:00", 
                "22:00-23:00", "23:00-00:00"],
    "2 марта": ["01:00-02:00", "02:00-03:00", "03:00-04:00", "04:00-05:00",
               "05:00-06:00", "06:00-07:00", "07:00-08:00", "08:00-09:00",
               "09:00-10:00", "10:00-11:00", "11:00-12:00", "12:00-13:00", "23:00-00:00"]
}

@router.message(F.text == "Я хочу сделать массаж")
async def show_rules(message: types.Message, state: FSMContext):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Я прочитал и согласен", callback_data="confirm_give_rules")]
    ])
    
    await message.answer(
        "Привет, Бёрнер! \n"
        "Ты записался на дарение или получение массажа, и мы рады тебя будем видеть в своей хижине в то время, в которое ты записался.\n"
        "Помни, пожалуйста, что одним из главных правил у нас является активное согласие. Это значит, что того, кому ты даришь массаж, "
        "необходимо спросить, что он хочет получить и каким именно образом. Человек может отказаться или передумать в процессе и это окей. \n"
        "Пожалуйста, уважай наше сообщество и люби его. \n"
        "Помни, что у нас в палатке нет сексуализированных практик, а для нас это очень важно. Для этого есть другие кемпы. \n"
        "С любовью, кемп \"Трогай тут\"",
        reply_markup=markup
    )
    await state.set_state(GiveMassage.confirmation)

@router.callback_query(GiveMassage.confirmation, F.data == "confirm_give_rules")
async def request_day(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    
    now = get_current_moscow_time()
    
    available_days = []
    for day in SLOTS_SCHEDULE.keys():
        try:
            slot_datetime = parse_slot_datetime(day, "00:00")
            if slot_datetime and slot_datetime.date() >= now.date():
                available_days.append(day)
        except Exception as e:
            logger.error(f"Ошибка при обработке даты {day}: {e}")
    
    if not available_days:
        inline_markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back_to_main")]
        ])
        
        await callback_query.message.edit_text(
            "К сожалению, мероприятие уже закончилось и запись не доступна.", 
            reply_markup=inline_markup
        )
        await state.clear()
        return
    
    for day in available_days:
        button = types.InlineKeyboardButton(text=day, callback_data=f"give_day:{day}")
        markup.inline_keyboard.append([button])

    await callback_query.message.edit_text(
        "Пожалуйста, выберите день, когда вы хотите делать массаж:", 
        reply_markup=markup
    )
    await state.set_state(GiveMassage.day)

@router.callback_query(GiveMassage.day)
async def process_day(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    if callback_query.data.startswith("give_day:"):
        day = callback_query.data.split(":")[1]
        await state.update_data(day=day)

        user_id = callback_query.from_user.id
        markup = types.InlineKeyboardMarkup(inline_keyboard=[])
        
        times = SLOTS_SCHEDULE.get(day, [])
        
        now = get_current_moscow_time()
        
        available_slots_count = 0
        
        user_slots = await get_user_slots(user_id)
        user_slot_times = set()
        for slot in user_slots:
            if slot['day'] == day:
                user_slot_times.add(slot['time'])
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                "SELECT time FROM slots WHERE day = ? AND status = 'active'",
                (day,)
            )
            existing_slots = await cursor.fetchall()
            existing_slot_times = set([slot[0] for slot in existing_slots])
        
        for time in times:
            slot_datetime = parse_slot_datetime(day, time)
            
            if not slot_datetime or slot_datetime <= now:
                continue
                
            if time in user_slot_times:
                continue
                
            display_time = time
            if "-" in time:
                start_time, end_time = time.split("-")
                if ":" not in start_time.strip():
                    start_time = f"{start_time.strip()}:00"
                if ":" not in end_time.strip():
                    end_time = f"{end_time.strip()}:00"
                display_time = f"{start_time.strip()}-{end_time.strip()}"
            elif ":" not in time:
                display_time = f"{time}:00"
                
            if await is_slot_available(day, time, user_id):
                button = types.InlineKeyboardButton(text=display_time, callback_data=f"give_time:{time}")
                markup.inline_keyboard.append([button])
                available_slots_count += 1
        
        markup.inline_keyboard.append([
            types.InlineKeyboardButton(text="← Назад", callback_data="back_to_days")
        ])
        
        if available_slots_count == 0:
            await callback_query.message.edit_text(
                f"На {day} нет доступных слотов. Выберите другой день или попробуйте позже.",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(text="← Назад", callback_data="back_to_days")
                ]])
            )
            return

        await callback_query.message.edit_text(
            f"Вы выбрали день: {day}. Теперь выберите время:\n\n"
            f"«Вы можете делать массаж и меньше часа, просто укажите это в комментарии. \n"
            f"Пожалуйста не опаздывайте на свой слот дарения массажа 🙏🏻»", 
            reply_markup=markup
        )
        await state.set_state(GiveMassage.time)
    elif callback_query.data == "back_to_days":
        await back_to_days(callback_query, state)

@router.callback_query(GiveMassage.day, F.data == "back_to_days")
async def back_to_days(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Я прочитал и согласен", callback_data="confirm_give_rules")]
    ])
    
    await callback_query.message.edit_text(
        "Привет, Бёрнер! \n"
        "Ты записался на дарение или получение массажа, и мы рады тебя будем видеть в своей хижине в то время, в которое ты записался.\n"
        "Помни, пожалуйста, что одним из главных правил у нас является активное согласие. Это значит, что того, кому ты даришь массаж, "
        "необходимо спросить, что он хочет получить и каким именно образом. Человек может отказаться или передумать в процессе и это окей. \n"
        "Пожалуйста, уважай наше сообщество и люби его. \n"
        "Помни, что у нас в палатке нет сексуализированных практик, а для нас это очень важно. Для этого есть другие кемпы. \n"
        "С любовью, кемп \"Трогай тут\"",
        reply_markup=markup
    )
    await state.set_state(GiveMassage.confirmation)

@router.callback_query(GiveMassage.time)
async def process_time(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    if callback_query.data == "ignore":
        return
    elif callback_query.data == "back_to_days":
        data = await state.get_data()
        day = data.get("day")
        await process_day(callback_query, state)
        return
    elif callback_query.data.startswith("give_time:"):  
        time = callback_query.data.split(":")[1]
        await state.update_data(time=time)
        await callback_query.message.edit_text("Напишите комментарий к своему предложению массажа (необязательно):")
        await state.set_state(GiveMassage.comment)

@router.message(GiveMassage.comment)
async def process_comment(message: types.Message, state: FSMContext):
    try:
        comment = message.text if message.text else ""
        data = await state.get_data()
        day = data.get("day")
        time = data.get("time")
        user_id = message.from_user.id
        
        if not await is_slot_available(day, time, user_id):
            await message.answer(
                "К сожалению, этот слот уже занят. Пожалуйста, выберите другое время.",
                reply_markup=main_menu
            )
            await state.clear()
            return
        
        now = get_current_moscow_time()
        slot_datetime = parse_slot_datetime(day, time)
        
        if not slot_datetime or slot_datetime <= now:
            await message.answer("Извините, это время уже прошло.", reply_markup=main_menu)
            await state.clear()
            return
        
        normalized_time = normalize_time_format(time)
        logger.info(f"Сохраняем слот с нормализованным временем: {normalized_time} (исходное: {time})")
        
        await add_slot(user_id, day, time, comment)
        
        # Форматирование времени для отображения
        display_time = time
        if "-" in time:
            start_time, end_time = time.split("-")
            if ":" not in start_time.strip():
                start_time = f"{start_time.strip()}:00"
            if ":" not in end_time.strip():
                end_time = f"{end_time.strip()}:00"
            display_time = f"{start_time.strip()}-{end_time.strip()}"
        elif ":" not in time:
            display_time = f"{time}:00"
        
        await message.answer(
            f"Вы записаны на дарение массажа:\nДень: {day}\nВремя: {display_time}\nКомментарий: {comment}", 
            reply_markup=main_menu
        )
        
        try:
            reminder_time = slot_datetime - timedelta(minutes=30)
            delay = (reminder_time - now).total_seconds()

            if delay > 0:
                asyncio.create_task(
                    schedule_reminder(message.from_user.id, message.from_user.username, day, time, "giver", delay)
                )
            else:
                logger.warning(
                    f"Пропущено напоминание для пользователя {message.from_user.username} "
                    f"(ID: {message.from_user.id}), время: {day} {time}"
                )
        except Exception as e:
            logger.error(f"Ошибка при создании напоминания: {e}")
            
    except Exception as e:
        logger.error(f"Ошибка при создании слота: {e}")
        await message.answer(
            "Произошла ошибка при создании слота. Пожалуйста, попробуйте еще раз.",
            reply_markup=main_menu
        )
    finally:
        await state.clear()

async def schedule_reminder(user_id: int, username: str, day: str, time: str, role: str, delay: int):
    await asyncio.sleep(delay)
    
    display_time = time
    if "-" in time:
        start_time, end_time = time.split("-")
        if ":" not in start_time.strip():
            start_time = f"{start_time.strip()}:00"
        if ":" not in end_time.strip():
            end_time = f"{end_time.strip()}:00"
        display_time = f"{start_time.strip()}-{end_time.strip()}"
    elif ":" not in time:
        display_time = f"{time}:00"
    
    if role == "giver":
        text = f"Я помню, что через 30 минут делаю массаж в «Трогай тут (корпус , этаж)» ({day}, {display_time}) и приду его делать 👌🏻"
    elif role == "receiver":
        text = f"Я помню, что через 30 минут получаю массаж в «Трогай тут (корпус , этаж)» ({day}, {display_time}) и приду его получать 👌🏻"
    await bot.send_message(user_id, text, reply_markup=reminder_menu)