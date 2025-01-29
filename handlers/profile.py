from aiogram import types
from keyboards import main_menu
from database import cancel_slot, get_slot_by_id
from utils import is_cancellation_allowed
from datetime import datetime, timedelta

async def confirm_reminder(callback_query: types.CallbackQuery):
    await bot.edit_message_text("Спасибо за подтверждение!", callback_query.from_user.id, callback_query.message.message_id, reply_markup=main_menu)

async def cancel_from_reminder(callback_query: types.CallbackQuery):
    message_text = callback_query.message.text

    index = message_text.find("через 30 минут")

    substring = message_text[index + len("через 30 минут"):].strip()

    parts = substring.split()
    if len(parts) < 7:
        await callback_query.answer("Не удалось разобрать время из напоминания", show_alert=True)
        return

    day = parts[4]  # "Day"
    time = parts[6] # "12:00"

    user_slots = await get_user_slots(callback_query.from_user.id)
    target_slot = None
    for slot in user_slots:
        if slot['day'] == day and slot['time'] == time:
            target_slot = slot
            break
    
    if target_slot is None:
        await callback_query.answer("Не удалось найти слот по данным из напоминания", show_alert=True)
        return

    slot_id = target_slot['id']
    slot = await get_slot_by_id(slot_id)

    if not slot:
        await callback_query.answer("Извините, слот был удален.")
        return

    if not await is_cancellation_allowed(slot):
        await bot.edit_message_text("Извините, отмена записи возможна не позднее, чем за 30 минут до начала.", callback_query.from_user.id, callback_query.message.message_id, reply_markup=main_menu)
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