from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards import main_menu
from database import get_user_slots, get_slot_by_id
from utils import format_slot_info, get_current_moscow_time, parse_slot_datetime
import logging

from aiogram import Bot
from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)


logger = logging.getLogger(__name__)

router = Router()

class Profile(StatesGroup):
    viewing_slot = State()

@router.message(F.text == "Мои записи")
async def show_profile(message: types.Message, state: FSMContext):
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
            button = types.InlineKeyboardButton(text=slot_info, callback_data=f"view_slot:{slot['id']}")
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
        "Ваши записи:", 
        reply_markup=markup,
        parse_mode="HTML"
    )
    await state.set_state(Profile.viewing_slot)

@router.callback_query(Profile.viewing_slot, F.data.startswith("view_slot:"))
async def read_receiver_comment(callback_query: types.CallbackQuery, state: FSMContext):
    slot_id = int(callback_query.data.split(":")[1])
    slot = await get_slot_by_id(slot_id)

    if not slot:
        await callback_query.answer("Извините, слот был удален.")
        await state.clear()
        return

    if callback_query.from_user.id != slot['giver_id']:
        await callback_query.answer("Вы не можете просматривать комментарий получателя в этом слоте.")
        return

    if slot['receiver_comment']:
        await callback_query.answer(f"Комментарий получателя: {slot['receiver_comment']}", show_alert=True)
    else:
        await callback_query.answer("Получатель не оставил комментария.", show_alert=True)

    await state.clear()

@router.callback_query(Profile.viewing_slot, F.data == "ignore")
async def process_ignore(callback_query: types.CallbackQuery):
    await callback_query.answer("Это время уже прошло.")