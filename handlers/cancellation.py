from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from keyboards import main_menu
from database import get_user_slots, cancel_slot, get_slot_by_id
from utils import format_slot_info, is_cancellation_allowed
from datetime import datetime, timedelta

class Cancel(StatesGroup):
    confirm_cancellation = State()

async def show_user_slots(message: types.Message):
    user_slots = await get_user_slots(message.from_user.id)
    if not user_slots:
        await message.answer("У вас нет активных записей.", reply_markup=main_menu)
        return

    markup = types.InlineKeyboardMarkup()
    for slot in user_slots:
        slot_info = await format_slot_info(slot)
        slot_datetime = datetime.strptime(f"{slot['day']} {slot['time']}", "%d %B %H:%M")
        if slot_datetime > datetime.now():
            markup.add(types.InlineKeyboardButton(slot_info, callback_data=f"cancel:{slot['id']}"))
        else:
            markup.add(types.InlineKeyboardButton(f"{slot_info} (время слота прошло)", callback_data="ignore"))

    await message.answer("Выберите запись для отмены:", reply_markup=markup)
    await Cancel.confirm_cancellation.set()

async def cancel_slot(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "ignore":
        await callback_query.answer("Это время уже прошло.")
        return
    
    slot_id = int(callback_query.data.split(":")[1])
    slot = await get_slot_by_id(slot_id)

    if not slot:
        await callback_query.answer("Извините, слот был удален.")
        await state.finish()
        return

    if not await is_cancellation_allowed(slot):
        await bot.edit_message_text("Извините, отмена записи возможна не позднее, чем за 30 минут до начала.", callback_query.from_user.id, callback_query.message.message_id, reply_markup=main_menu)
        await state.finish()
        return

    if callback_query.from_user.id == slot['giver_id']:
        canceled_by = 'giver'
        other_user_id = slot['receiver_id']
    else:
        canceled_by = 'receiver'
        other_user_id = slot['giver_id']

    await cancel_slot(slot_id, canceled_by)

    if other_user_id:
        if canceled_by == 'giver':
            await bot.send_message(other_user_id, "Простите, ваш массажист не сможет сделать вам массаж.")
        else:
            await bot.send_message(other_user_id, "Простите, вам массажируемый не сможет прийти на массаж.")

    await bot.edit_message_text("Запись успешно отменена.", callback_query.from_user.id, callback_query.message.message_id, reply_markup=main_menu)
    await state.finish()