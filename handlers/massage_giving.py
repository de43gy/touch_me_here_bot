from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from keyboards import main_menu
from database import add_slot
from utils import is_slot_available
from datetime import datetime, timedelta
import asyncio

class GiveMassage(StatesGroup):
    day = State()
    time = State()
    comment = State()

async def request_day(message: types.Message):
    markup = types.InlineKeyboardMarkup()
    days = ["День 1", "День 2", "День 3"]
    for day in days:
        markup.add(types.InlineKeyboardButton(day, callback_data=f"give_day:{day}"))
    await message.answer("Пожалуйста, выберите день, когда вы хотите делать массаж:", reply_markup=markup)
    await GiveMassage.day.set()

async def process_day(callback_query: types.CallbackQuery, state: FSMContext):
    day = callback_query.data.split(":")[1]
    await state.update_data(day=day)

    markup = types.InlineKeyboardMarkup()
    times = ["12:00", "12:30", "13:00", "13:30"]
    for time in times:
        if await is_slot_available(day, time):
          markup.add(types.InlineKeyboardButton(time, callback_data=f"give_time:{time}"))
        else:
          markup.add(types.InlineKeyboardButton(f"{time} (занято)", callback_data="ignore"))
    await bot.edit_message_text(f"Вы выбрали день: {day}. Теперь выберите время:", callback_query.from_user.id, callback_query.message.message_id, reply_markup=markup)
    await GiveMassage.next()

async def process_time(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "ignore":
        await callback_query.answer("Это время уже занято.")
        return
    
    time = callback_query.data.split(":")[1]
    await state.update_data(time=time)
    await bot.edit_message_text("Напишите комментарий к своему предложению массажа (необязательно):", callback_query.from_user.id, callback_query.message.message_id)
    await GiveMassage.next()

async def process_comment(message: types.Message, state: FSMContext):
    comment = message.text if message.text else ""
    data = await state.get_data()
    day = data.get("day")
    time = data.get("time")
    
    await add_slot(message.from_user.id, day, time, comment)
    await message.answer(f"Вы записаны на дарение массажа:\nДень: {day}\nВремя: {time}\nКомментарий: {comment}", reply_markup=main_menu)
    await state.finish()

    reminder_time = datetime.strptime(f"{day} {time}", "%d %B %H:%M") - timedelta(minutes=30)
    delay = (reminder_time - datetime.now()).total_seconds()

    if delay > 0:
      asyncio.create_task(schedule_reminder(message.from_user.id, message.from_user.username, day, time, "giver", delay))
    else:
        print(f"Пропущено напоминание для пользователя {message.from_user.username} ({message.from_user.id}), время: {day} {time} ({reminder_time})")

async def schedule_reminder(user_id: int, username: str, day: str, time: str, role: str, delay: int):
    await asyncio.sleep(delay)
    if role == "giver":
      text = f"Я помню, что через 30 минут делаю массаж в «Трогай тут (корпус , этаж)» и приду его делать 👌🏻"
    elif role == "receiver":
      text = f"Я помню, что через 30 минут получаю массаж в «Трогай тут (корпус , этаж)» и приду его получать 👌🏻"
    await bot.send_message(user_id, text, reply_markup=reminder_menu)