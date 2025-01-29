from aiogram import types
from keyboard import main_menu

async def smd_start(message: types.Message):
    await message.answer("Привет! Я помогу хочешь получить массаж или сделать его?", reply_markup=main_menu)