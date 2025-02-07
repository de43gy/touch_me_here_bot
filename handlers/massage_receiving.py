from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from keyboards import main_menu, reminder_menu
from database import get_available_slots, book_slot, get_slot_by_id
from utils import format_slot_info
from datetime import datetime, timedelta
import asyncio
import logging

from aiogram import Bot
from config import BOT_TOKEN

logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)


class ReceiveMassage(StatesGroup):
    day = State()
    time = State()
    comment = State()

router = Router()

@router.message(F.text == "Я хочу получить массаж")
async def show_available_slots(message: types.Message):
    slots = await get_available_slots()
    if not slots:
        await message.answer("К сожалению, сейчас нет доступных слотов для записи.", reply_markup=main_menu)
        return

    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    days = sorted(list(set([slot['day'] for slot in slots])))

    for day in days:
        button = types.InlineKeyboardButton(F.text == day, callback_data=f"receive_day:{day}")
        markup.inline_keyboard.append([button])
    await message.answer("Выберите день:", reply_markup=markup)
    await ReceiveMassage.day.set()

@router.callback_query(ReceiveMassage.day)
async def process_day_selection(callback_query: types.CallbackQuery, state: FSMContext):
    day = callback_query.data.split(":")[1]
    await state.update_data(day=day)

    slots = await get_available_slots()
    day_slots = [slot for slot in slots if slot['day'] == day]

    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    for slot in day_slots:
        slot_info = await format_slot_info(slot)
        button = types.InlineKeyboardButton(F.text == slot_info, callback_data=f"receive_time:{slot['id']}")
        markup.inline_keyboard.append([button])

    await callback_query.message.edit_text(f"Доступные слоты на {day}:", reply_markup=markup)
    await ReceiveMassage.next()

@router.callback_query(ReceiveMassage.time)
async def process_time_selection(callback_query: types.CallbackQuery, state: FSMContext):
    slot_id = int(callback_query.data.split(":")[1])
    await state.update_data(slot_id=slot_id)

    await callback_query.message.edit_text("Напишите комментарий к записи (необязательно):") 
    await ReceiveMassage.next()

@router.message(ReceiveMassage.comment)
async def process_comment(message: types.Message, state: FSMContext):
    comment = message.text if message.text else ""
    data = await state.get_data()
    slot_id = data.get("slot_id")
    user_id = message.from_user.id

    slot = await get_slot_by_id(slot_id)
    if not slot:
        await message.answer("Извините, слот был занят или удален.", reply_markup=main_menu)
        await state.clear()
        return

    await book_slot(slot_id, user_id, comment)

    giver_id = slot['giver_id']
    await bot.send_message(giver_id, f"К вам записались на массаж!\nКомментарий: {comment}")

    await message.answer(f"Вы записаны на массаж!\n{await format_slot_info(slot)}", reply_markup=main_menu)
    await state.clear()

    day_str = slot['day']
    time_str = slot['time']
    reminder_time = datetime.strptime(f"День {day_str.split()[-1]} {time_str}", "День %d %H:%M") - timedelta(minutes=30)
    delay = (reminder_time - datetime.now()).total_seconds()

    if delay > 0:
      asyncio.create_task(schedule_reminder(message.from_user.id, message.from_user.username, day_str, time_str, "receiver", delay))
    else:
        logger.warning(f"Пропущено напоминание для пользователя {message.from_user.username} (ID: {message.from_user.id}), время: {day_str} {time_str} ({reminder_time})") # используем day_str


async def schedule_reminder(user_id: int, username: str, day: str, time: str, role: str, delay: int):
    await asyncio.sleep(delay)
    if role == "giver":
      text = f"Я помню, что через 30 минут делаю массаж в «Трогай тут (корпус , этаж)» и приду его делать 👌🏻"
    elif role == "receiver":
      text = f"Я помню, что через 30 минут получаю массаж в «Трогай тут (корпус , этаж)» и приду его получать 👌🏻"
    await bot.send_message(user_id, text, reply_markup=reminder_menu)