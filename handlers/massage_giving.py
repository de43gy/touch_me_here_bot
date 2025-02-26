from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from keyboards import main_menu, reminder_menu
from database import add_slot
from utils import is_slot_available
from datetime import datetime, timedelta
import asyncio
import logging

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

SLOTS_SCHEDULE = {
    "28 февраля": ["16:00-17:00", "19:00-20:00", "20:00-21:00", "23:30-00:00"],
    "1 марта": ["00:00-01:00", "02:00-03:00", "03:00-04:00", "04:00-05:00", 
                "05:00-06:00", "06:00-07:00", "08:00-09:00", "10:00-11:00",
                "11:00-12:00", "12:00-13:00", "13:00-14:00", "14:00-15:00",
                "15:00-16:00", "17:30-18:00", "18:00-19:00", "21:00-22:00", 
                "22:00-23:00"],
    "2 марта": ["01:00-02:00", "02:00-03:00", "03:00-04:00", "04:00-05:00",
               "05:00-06:00", "06:00-07:00", "07:00-08:00", "08:00-09:00",
               "09:00-10:00", "10:00-11:00", "11:00-12:00", "12:00-13:00"]
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
    
    now = datetime.now()
    
    available_days = []
    for day in SLOTS_SCHEDULE.keys():
        try:
            day_parts = day.split()
            day_num = int(day_parts[0])
            month_name = day_parts[1]
            month_map = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
                         "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12}
            month_num = month_map.get(month_name.lower(), 0)
            day_date = datetime(now.year, month_num, day_num)
            
            if day_date.date() >= now.date():
                available_days.append(day)
        except Exception as e:
            logger.error(f"Ошибка при обработке даты {day}: {e}")
    
    if not available_days:
        await callback_query.message.edit_text(
            "К сожалению, мероприятие уже закончилось и запись не доступна.", 
            reply_markup=main_menu
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
    day = callback_query.data.split(":")[1]
    await state.update_data(day=day)

    user_id = callback_query.from_user.id
    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    
    times = SLOTS_SCHEDULE.get(day, [])
    
    now = datetime.now()
    
    available_slots_count = 0
    
    for time in times:
        time_parts = time.split("-")[0].strip().split(":")
        slot_hour = int(time_parts[0])
        slot_minute = int(time_parts[1]) if len(time_parts) > 1 else 0
        
        day_parts = day.split()
        day_num = int(day_parts[0])
        month_name = day_parts[1]
        month_map = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
                     "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12}
        month_num = month_map.get(month_name.lower(), 0)
        
        slot_datetime = datetime(now.year, month_num, day_num, slot_hour, slot_minute)
        
        if slot_datetime <= now:
            continue
            
        if await is_slot_available(day, time, user_id):
            button = types.InlineKeyboardButton(text=time, callback_data=f"give_time:{time}")
            markup.inline_keyboard.append([button])
            available_slots_count += 1
        else:
            button = types.InlineKeyboardButton(text=f"{time} (занято)", callback_data="ignore")
            markup.inline_keyboard.append([button])
    
    if available_slots_count == 0:
        await callback_query.message.edit_text(
            f"На {day} нет доступных слотов. Выберите другой день или попробуйте позже.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="← Назад", callback_data="back_to_days")
            ]])
        )
        await callback_query.answer()
        return

    await callback_query.message.edit_text(f"Вы выбрали день: {day}. Теперь выберите время:", reply_markup=markup)
    await state.set_state(GiveMassage.time)
    await callback_query.answer()

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
    if callback_query.data == "ignore":
        await callback_query.answer("Это время уже занято.")
        return
        
    time = callback_query.data.split(":")[1]
    await state.update_data(time=time)
    await callback_query.message.edit_text("Напишите комментарий к своему предложению массажа (необязательно):")
    await state.set_state(GiveMassage.comment)
    await callback_query.answer()

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
        
        await add_slot(user_id, day, time, comment)
        await message.answer(
            f"Вы записаны на дарение массажа:\nДень: {day}\nВремя: {time}\nКомментарий: {comment}", 
            reply_markup=main_menu
        )
        
        try:
            time_parts = time.split("-")[0].strip().split(":")
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            
            day_parts = day.split()
            day_num = int(day_parts[0])
            month_name = day_parts[1]
            month_map = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
                        "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12}
            month_num = month_map.get(month_name.lower(), 0)
            
            now = datetime.now()
            slot_datetime = datetime(now.year, month_num, day_num, hour, minute)
            
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
    if role == "giver":
        text = f"Я помню, что через 30 минут делаю массаж в «Трогай тут (корпус , этаж)» и приду его делать 👌🏻"
    elif role == "receiver":
        text = f"Я помню, что через 30 минут получаю массаж в «Трогай тут (корпус , этаж)» и приду его получать 👌🏻"
    await bot.send_message(user_id, text, reply_markup=reminder_menu)