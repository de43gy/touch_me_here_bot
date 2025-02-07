from aiogram import types, Router, F
from keyboards import main_menu
from database import cancel_slot, get_slot_by_id, get_user_slots
from utils import is_cancellation_allowed
from datetime import datetime, timedelta
import logging

from aiogram import Bot
from config import BOT_TOKEN

logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)

router = Router()

@router.callback_query(F.data == "confirm")
async def confirm_reminder(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("Спасибо за подтверждение!")
    await callback_query.answer()

@router.callback_query(F.data == "cancel_reminder")
async def cancel_from_reminder(callback_query: types.CallbackQuery):
    message_text = callback_query.message.text

    try:
        index = message_text.find("через 30 минут")
        if index == -1:
            raise ValueError("Не найдена фраза 'через 30 минут'")

        substring = message_text[index + len("через 30 минут"):].strip()

        parts = substring.split()
        if "делаю" in message_text:
            day = " ".join(parts[4:6])
            time = parts[7]
        elif "получаю" in message_text:
            day = " ".join(parts[4:6])
            time = parts[7]
        else:
            raise ValueError("Не удалось определить тип сообщения (делаю/получаю)")

    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка при разборе времени из напоминания: {e}, текст: {message_text}")
        await callback_query.answer("Не удалось разобрать время из напоминания", show_alert=True)
        return
    
    logger.info(f"Извлечено из напоминания: день='{day}', время='{time}'")

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
        await callback_query.message.edit_text("Извините, отмена записи возможна не позднее, чем за 30 минут до начала.", reply_markup=main_menu)
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
            await bot.send_message(other_user_id, "Простите, ваш массажируемый не сможет прийти на массаж.")

    await callback_query.message.edit_text("Запись успешно отменена.", reply_markup=main_menu)
    await callback_query.answer()