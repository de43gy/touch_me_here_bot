from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from keyboards import main_menu
from database import get_user_slots, cancel_slot, get_slot_by_id
from utils import format_slot_info, is_cancellation_allowed
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
        await message.answer("У вас нет активных записей.", reply_markup=main_menu)
        return

    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    for slot in user_slots:
        slot_info = await format_slot_info(slot)
        
        # Преобразуем номер дня в формат "01", "02" и т.д.
        day_number = slot['day'].split()[1].zfill(2)
        
        # Форматируем время
        time_str = slot['time']
        if len(time_str) == 2:  # Если время в формате "12", добавляем ":00"
            time_str = f"{time_str}:00"
            
        try:
            slot_datetime = datetime.strptime(f"{day_number} {time_str}", "%d %H:%M")
            
            if slot_datetime > datetime.now():
                button = types.InlineKeyboardButton(text=slot_info, callback_data=f"cancel:{slot['id']}")
                markup.inline_keyboard.append([button])
            else:
                button = types.InlineKeyboardButton(text=f"{slot_info} (время слота прошло)", callback_data="ignore")
                markup.inline_keyboard.append([button])
        except ValueError as e:
            logger.error(f"Ошибка при парсинге даты/времени: {e}")
            continue

    if not markup.inline_keyboard:
        await message.answer("У вас нет активных записей.", reply_markup=main_menu)
        return

    await message.answer("Выберите запись для отмены:", reply_markup=markup)
    await state.set_state(Cancel.confirm_cancellation)

@router.callback_query(Cancel.confirm_cancellation, F.data.startswith("cancel:"))
async def handle_cancel_slot(callback_query: types.CallbackQuery, state: FSMContext):
    slot_id = int(callback_query.data.split(":")[1])
    slot = await get_slot_by_id(slot_id)

    if not slot:
        await callback_query.answer("Извините, слот был удален.")
        await state.clear()
        return

    if not await is_cancellation_allowed(slot):
        await callback_query.message.edit_text(
            "Извините, отмена записи возможна не позднее, чем за 30 минут до начала.",
            reply_markup=main_menu
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
    await callback_query.message.edit_text("Запись успешно отменена.", reply_markup=main_menu)
    
    if other_user_id:
        try:
            await bot.send_message(
                other_user_id,
                f"Ваша запись на массаж {slot['day']} в {slot['time']} была отменена {'массажистом' if canceled_by == 'giver' else 'получателем'}."
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления об отмене: {e}")

    await state.clear()

@router.callback_query(Cancel.confirm_cancellation, F.data == "ignore")
async def handle_ignore(callback_query: types.CallbackQuery):
    await callback_query.answer("Это время уже прошло.")