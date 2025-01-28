from config import ADMIN_ID
from aiogram import Bot

async def send_notification_to_admin(bot: Bot, message: str):
    await bot.send_message(ADMIN_ID, message)