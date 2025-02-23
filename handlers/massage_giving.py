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
    day = State()
    time = State()
    comment = State()

router = Router()

@router.message(F.text == "Я хочу сделать массаж")
async def request_day(message: types.Message, state: FSMContext):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    days = ["День 1", "День 2", "День 3"]
    for day in days:
        button = types.InlineKeyboardButton(text=day, callback_data=f"give_day:{day}")
        markup.inline_keyboard.append([button])

    await message.answer("Пожалуйста, выберите день, когда вы хотите делать массаж:", reply_markup=markup)
    await state.set_state(GiveMassage.day)

@router.callback_query(GiveMassage.time, F.data.startswith("give_time:"))
async def process_time(callback_query: types.CallbackQuery, state: FSMContext):
    time = callback_query.data.split(":")[1]
    if ':' not in time:
        time = f"{time}:00"
    await state.update_data(time=time)
    await callback_query.message.edit_text("Напишите комментарий к своему предложению массажа (необязательно):")
    await state.set_state(GiveMassage.comment)

@router.callback_query(GiveMassage.time, F.data == "ignore")
async def process_time_ignore(callback_query: types.CallbackQuery):
    await callback_query.answer("Это время уже занято.")

@router.message(GiveMassage.comment)
async def process_comment(message: types.Message, state: FSMContext):
    try:
        comment = message.text if message.text else ""
        data = await state.get_data()
        day = data.get("day")
        time = data.get("time")
        
        await add_slot(message.from_user.id, day, time, comment)
        await message.answer(
            f"Вы записаны на дарение массажа:\nДень: {day}\nВремя: {time}\nКомментарий: {comment}", 
            reply_markup=main_menu
        )
        
        try:
            # Используем текущую дату и заменяем только часы и минуты
            now = datetime.now()
            time_parts = time.split(':')
            reminder_datetime = now.replace(
                hour=int(time_parts[0]),
                minute=int(time_parts[1]),
                second=0,
                microsecond=0
            )
            
            reminder_time = reminder_datetime - timedelta(minutes=30)
            delay = (reminder_time - datetime.now()).total_seconds()

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