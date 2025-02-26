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

@router.message(F.text == "Я хочу получить массаж")
async def show_rules(message: types.Message, state: FSMContext):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Я прочитал и согласен", callback_data="confirm_receive_rules")]
    ])
    
    await message.answer(
        "«Важно!\n"
        "При дарении массажа необходимо соблюдать принципы взаимного согласия и уважения. "
        "Все действия должны быть комфортными для обеих сторон. Массаж не подразумевает никакого "
        "сексуализированного контекста. Если кто-либо испытывает дискомфорт, процесс должен быть "
        "немедленно остановлен. Уважайте границы друг друга!»",
        reply_markup=markup
    )
    await state.set_state(ReceiveMassage.confirmation)

@router.callback_query(ReceiveMassage.confirmation, F.data == "confirm_receive_rules")
async def show_available_slots_after_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    slots = await get_available_slots()
    if not slots:
        inline_markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back_to_main")]
        ])
        
        await callback_query.message.edit_text(
            "К сожалению, сейчас нет доступных слотов для записи.", 
            reply_markup=inline_markup
        )
        await state.clear()
        return

    user_id = callback_query.from_user.id
    
    now = get_current_moscow_time()
    
    logger.info(f"Доступные слоты: {len(slots)}")
    for i, slot in enumerate(slots):
        logger.info(f"Слот {i+1}: день={slot['day']}, время={slot['time']}")
    
    filtered_slots = []
    for slot in slots:
        try:
            if 'day' not in slot or 'time' not in slot:
                logger.error(f"Слот не содержит необходимых полей day или time