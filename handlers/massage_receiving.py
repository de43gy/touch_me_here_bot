from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from keyboards import main_menu, reminder_menu
from database import get_available_slots, book_slot, get_slot_by_id
from utils import format_slot_info, is_slot_available
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
async def show_available_slots(message: types.Message, state: FSMContext):
    slots = await get_available_slots()
    if not slots:
        await message.answer("К сожалению, сейчас нет доступных слотов для записи.", reply_markup=main_menu)
        return

    user_id = message.from_user.id
    
    filtered_slots = []
    for slot in slots:
        if await is_slot_available(slot['day'], slot['time'], user_id):
            filtered_slots.append(slot)
    
    if not filtered_slots:
        await message.answer("К сожалению, все доступные слоты уже заняты или вы уже записаны на эти времена.", 
                             reply_markup=main_menu)
        return

    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    days = sorted(list(set([slot['day'] for slot in filtered_slots])))

    for day in days:
        button = types.InlineKeyboardButton(text=day, callback_data=f"receive_day:{day}")
        markup.inline_keyboard.append([button])

    await message.answer("Выберите день:", reply_markup=markup)
    await state.set_state(ReceiveMassage.day)

@router.callback_query(ReceiveMassage.day)
async def process_day_selection(callback_query: types.CallbackQuery, state: FSMContext):
    day = callback_query.data.split(":")[1]
    await state.update_data(day=day)

    slots = await get_available_slots()
    day_slots = [slot for slot in slots if slot['day'] == day]
    
    user_id = callback_query.from_user.id
    
    filtered_slots = []
    for slot in day_slots:
        if await is_slot_available(slot['day'], slot['time'], user_id):
            filtered_slots.append(slot)
    
    if not filtered_slots:
        await callback_query.message.edit_text(
            f"К сожалению, на день {day} нет доступных слотов или вы уже записаны на все слоты этого дня.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="← Назад", callback_data="back_to_days")
            ]])
        )
        return

    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    for slot in filtered_slots:
        slot_info = await format_slot_info(slot)
        button = types.InlineKeyboardButton(text=slot_info, callback_data=f"receive_time:{slot['id']}")
        markup.inline_keyboard.append([button])

    await callback_query.message.edit_text(f"Доступные слоты на {day}:", reply_markup=markup)
    await state.set_state(ReceiveMassage.time)
    await callback_query.answer()

@router.callback_query(ReceiveMassage.day, F.data == "back_to_days")
async def back_to_days(callback_query: types.CallbackQuery, state: FSMContext):
    await show_available_slots(callback_query.message, state)
    await callback_query.answer()

@router.callback_query(ReceiveMassage.time)
async def process_time_selection(callback_query: types.CallbackQuery, state: FSMContext):
    slot_id = int(callback_query.data.split(":")[1])
    await state.update_data(slot_id=slot_id)

    await callback_query.message.edit_text("Напишите комментарий к записи (необязательно):")
    await state.set_state(ReceiveMassage.comment)
    await callback_query.answer()

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
        
    if slot['receiver_id'] is not None:
        await message.answer("Извините, этот слот уже занят другим пользователем.", reply_markup=main_menu)
        await state.clear()
        return
        
    if slot['giver_id'] == user_id:
        await message.answer("Извините, вы не можете записаться на собственный слот массажа.", reply_markup=main_menu)
        await state.clear()
        return
        
    if not await is_slot_available(slot['day'], slot['time'], user_id):
        await message.answer(
            "У вас уже есть запись на это время. Пожалуйста, выберите другое время.",
            reply_markup=main_menu
        )
        await state.clear()
        return

    await book_slot(slot_id, user_id, comment)
    await message.answer(f"Вы записаны на массаж!\n{await format_slot_info(slot)}", reply_markup=main_menu)
    
    giver_id = slot['giver_id']
    await bot.send_message(giver_id, f"К вам записались на массаж!\nКомментарий: {comment}")
    
    await state.clear()

    day_number = slot['day'].split()[1].zfill(2)
    
    time_str = slot['time']
    if len(time_str) == 2:
        time_str = f"{time_str}:00"
        
    try:
        reminder_datetime = datetime.now().replace(
            hour=int(time_str.split(':')[0]),
            minute=int(time_str.split(':')[1]),
            second=0,
            microsecond=0
        )
        reminder_time = reminder_datetime - timedelta(minutes=30)
        
        delay = (reminder_time - datetime.now()).total_seconds()

        if delay > 0:
            asyncio.create_task(schedule_reminder(message.from_user.id, message.from_user.username, slot['day'], time_str, "receiver", delay))
        else:
            logger.warning(f"Пропущено напоминание для пользователя {message.from_user.username} (ID: {message.from_user.id}), время: {slot['day']} {time_str}")
    except Exception as e:
        logger.error(f"Ошибка при создании напоминания: {e}")

async def schedule_reminder(user_id: int, username: str, day: str, time: str, role: str, delay: int):
    await asyncio.sleep(delay)
    if role == "giver":
        text = f"Я помню, что через 30 минут делаю массаж в «Трогай тут (корпус , этаж)» и приду его делать 👌🏻"
    elif role == "receiver":
        text = f"Я помню, что через 30 минут получаю массаж в «Трогай тут (корпус , этаж)» и приду его получать 👌🏻"
    await bot.send_message(user_id, text, reply_markup=reminder_menu)