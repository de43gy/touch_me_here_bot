from aiogram import types
from keyboards import main_menu
import logging

logger = logging.getLogger(__name__)

async def cmd_start(message: types.Message):
    try:
        from database import add_user
        await add_user(message.from_user.id, message.from_user.username)
        await message.answer("Привет! Я бот TouchHarmony, помогу тебе записаться на массаж или сделать его.", reply_markup=main_menu)
        logger.info(f"Пользователь {message.from_user.username} (ID: {message.from_user.id}) запустил бота.")
    except Exception as e:
        logger.error(f"Ошибка в команде /start для пользователя {message.from_user.username} (ID: {message.from_user.id}) ")