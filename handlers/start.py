from aiogram import types, Router, F
from aiogram.filters import Command, CommandStart
from keyboards import main_menu
import logging
from database import add_user

logger = logging.getLogger(__name__)

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    try:
        await add_user(message.from_user.id, message.from_user.username)
        await message.answer(
            "<b>📍 Дружба корпус 1 второй этаж</b>\n\n"
            "Привет! Я бот TouchHarmony, помогу тебе записаться на массаж или сделать его.",
            reply_markup=main_menu,
            parse_mode="HTML"
        )
        logger.info(f"Пользователь {message.from_user.username} (ID: {message.from_user.id}) запустил бота.")
    except Exception as e:
        logger.error(f"Ошибка в команде /start для пользователя {message.from_user.username} (ID: {message.from_user.id}): {e}")
        await message.answer("Произошла ошибка при обработке команды /start. Пожалуйста, попробуйте позже.")
        
@router.message(F.text == "📍 Дружба корпус 1 второй этаж")
async def show_location(message: types.Message):
    await message.answer(
        "<b>📍 ЛОКАЦИЯ КЕМПА «ТРОГАЙ ТУТ»</b>\n\n"
        "<b>Дружба корпус 1 второй этаж</b>\n\n"
        "Ждем тебя на массаж в указанное время!",
        parse_mode="HTML",
        reply_markup=main_menu
    )