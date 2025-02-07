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
async def show_user_slots(message: types.Message):
    user_slots = await get_user_slots(message.from_user.id)
    if not user_slots:
        await message.answer("У вас нет активных записей.", reply_markup=main_menu)
        return

    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    for slot in user_slots:
        slot_info = await format_slot_info(slot)
        slot_datetime = datetime.strptime(f"{slot['day']} {slot['time']}", "%d %B %H:%M")
        if slot_datetime > datetime.now():
            button = types.InlineKeyboardButton(text=slot_info, callback_data=f"cancel:{slot['id']}")
            markup.inline_keyboard.append([button])
        else:
            button = types.InlineKeyboardButton(text=f"{slot_info} (время слота прошло)", callback_data="ignore")
            markup.inline_keyboard.append([button])

    await message.answer("Выберите запись для отмены:", reply_markup=markup)
    await Cancel.confirm_cancellation.set()

@router.callback_query(Cancel.confirm_cancellation, F.data.startswith("cancel:"))
async def cancel_slot(callback_query: types.CallbackQuery, state: FSMContext):
    slot_id = int(callback_query.data.split(":")[1])
    slot = await get_slot_by_id(slot_id)

    if not slot:
        await callback_query.answer("Извините, слот был удален.")
        await state.clear()
        return

    if not await is_cancellation_allowed(slot):
        await callback_query.message.edit_text("Извините, отмена записи возможна не позднее, чем за 30 минут до начала.", reply_markup=main_menu)
        await state.clear()
        return

    if callback_query.from_user.id == slot['giver_id']:
        canceled_by = 'giver'
        other_user_id = slot['receiver_id']
    else:
        canceled_by = 'receiver'
        other_user_id = slot['giver_id']

    await cancel