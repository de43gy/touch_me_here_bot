from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from keyboards import main_menu
from database import get_user_slots, cancel_slot, get_slot_by_id
from utils import format_slot_info, is_cancellation_allowed, get_current_moscow_time, parse_slot_datetime
from datetime import datetime, timedelta
import logging
from aiogram import Bot
from config import BOT_TOKEN

logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)

class Cancel(StatesGroup):
    confirm_cancellation = State()

router = Router()

@router.message(F.text == "Мои записи")
async def show_user_slots(message: types.Message, state: FSMContext):
    user_slots = await get_user_slots(message.from_user.id)
    if not user_slots:
        await message.answer(
            "<b>📍 Салют 1 корпус 3 этаж</b>\n\n"
            "У вас нет активных записей.", 
            reply_markup=main_menu,
            parse_mode="HTML"
        )
        return

    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    now = get_current_moscow_time()
    
    for slot in user_slots:
        slot_info = await format_slot_info(slot)
        slot_datetime = parse_slot_datetime(slot['day'], slot['time'])
            
        if slot_datetime and slot_datetime > now:
            button = types.InlineKeyboardButton(text=slot_info, callback_data=f"cancel:{slot['id']}")
            markup.inline_keyboard.append([button])
        else:
            button = types.InlineKeyboardButton(text=f"{slot_info} (время слота прошло)", callback_data="ignore")
            markup.inline_keyboard.append([button])

    if not markup.inline_keyboard:
        await message.answer(
            "<b>📍 Салют 1 корпус 3 этаж</b>\n\n"
            "У вас нет активных записей.", 
            reply_markup=main_menu,
            parse_mode="HTML"
        )
        return

    await message.answer(
        "<b>📍 Салют 1 корпус 3 этаж</b>\n\n"
        "Выберите запись для отмены:\n"
        "<i>Нажмите на запись, чтобы отменить её</i>", 
        reply_markup=markup,
        parse_mode="HTML"
    )
    await state.set_state(Cancel.confirm_cancellation)

@router.callback_query(Cancel.confirm_cancellation, F.data.startswith("cancel:"))
async def handle_cancel_slot(callback_query: types.CallbackQuery, state: FSMContext):
    slot_id = int(callback_query.data.split(":")[1])
    slot = await get_slot_by_id(slot_id)

    if not slot:
        await callback_query.answer("Извините, слот был удален.")
        await state.clear()
        return

    confirm_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Да, отменить", callback_data=f"confirm_cancel:{slot_id}"),
            types.InlineKeyboardButton(text="❌ Нет", callback_data="cancel_cancel")
        ]
    ])
    
    slot_info = await format_slot_info(slot)
    
    await callback_query.message.edit_text(
        f"<b>📍 Салют 1 корпус 3 этаж</b>\n\n"
        f"Вы уверены, что хотите отменить запись?\n\n"
        f"{slot_info}",
        reply_markup=confirm_markup,
        parse_mode="HTML"
    )

@router.callback_query(Cancel.confirm_cancellation, F.data == "cancel_cancel")
async def handle_cancel_cancellation(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer("Отмена отменена 😊")
    await show_user_slots(callback_query.message, state)

@router.callback_query(Cancel.confirm_cancellation, F.data.startswith("confirm_cancel:"))
async def handle_confirm_cancel(callback_query: types.CallbackQuery, state: FSMContext):
    slot_id = int(callback_query.data.split(":")[1])
    slot = await get_slot_by_id(slot_id)

    if not slot:
        await callback_query.answer("Извините, слот был удален.")
        await state.clear()
        return

    if not await is_cancellation_allowed(slot):
        await callback_query.message.edit_text(
            "<b>📍 Салют 1 корпус 3 этаж</b>\n\n"
            "Извините, отмена записи возможна не позднее, чем за 30 минут до начала.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="← Назад", callback_data="back_to_main")
            ]]),
            parse_mode="HTML"
        )
        await state.clear()
        return

    if callback_query.from_user.id == slot['giver_id']:
        canceled_by = 'giver'
        other_user_id = slot['receiver_id']
    else:
        canceled_by = 'receiver'
        other_user_id = slot['giver_id']

    await cancel_slot(slot_id, canceled_by)
    await callback_query.message.edit_text(
        "<b>📍 Салют 1 корпус 3 этаж</b>\n\n"
        "Запись успешно отменена.", 
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back_to_main")
        ]]),
        parse_mode="HTML"
    )
    
    if other_user_id:
        try:
            await bot.send_message(
                other_user_id,
                f"<b>📍 Салют 1 корпус 3 этаж</b>\n\n"
                f"Ваша запись на массаж {slot['day']} в {slot['time']} была отменена "
                f"{'массажистом' if canceled_by == 'giver' else 'получателем'}.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления об отмене: {e}")

    await state.clear()

@router.callback_query(Cancel.confirm_cancellation, F.data == "ignore")
async def handle_ignore(callback_query: types.CallbackQuery):
    await callback_query.answer("Это время уже прошло.")
    
@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.clear()
    
    await callback_query.message.answer(
        "<b>📍 Салют 1 корпус 3 этаж</b>\n\n"
        "Вы вернулись в главное меню", 
        reply_markup=main_menu,
        parse_mode="HTML"
    )
    
    try:
        await callback_query.message.delete()
    except Exception as e:
        logger.error(f"Ошибка при удалении сообщения: {e}")