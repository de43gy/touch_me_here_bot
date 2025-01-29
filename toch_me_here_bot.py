import asyncio
import logging

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher import FCMContext

from config import BOT_TOKEN
from database import create_tables
from handlers import start, massage_giving, massage_receiving, cancellation, profile, reminders
from utils import send_notification_to_admin

logging.basicConfig(level=logging.INFO)

bot = Bot(toke=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

dp.register_message_handler(start.cmd_start, commands=["start"])
dp.register_message_handler(massage_giving.request_day, text="Я хочу сделать массаж")
dp.register_callback_query_handler(massage_giving.process_day, state=massage_giving.GiveMassage.day)
dp.register_callback_query_handler(massage_giving.process_time, state=massage_giving.GiveMassage.time)
dp.register_message_handler(massage_giving.process_comment, state=massage_giving.GiveMassage.comment)

dp.register_message_handler(massage_receiving.show_available_slots, text="Я хочу получить массаж")
dp.register_callback_query_handler(massage_receiving.process_day_selection, state=massage_receiving.ReceiveMassage.day)
dp.register_callback_query_handler(massage_receiving.process_time_selection, state=massage_receiving.ReceiveMassage.time)
dp.register_message_handler(massage_receiving.process_comment, state=massage_receiving.ReceiveMassage.comment)

dp.register_message_handler(cancellation.show_user_slots, text="Мои записи")
dp.register_callback_query_handler(cancellation.cancel_slot, state=cancellation.Cancel.confirm_cancellation)

dp.register_message_handler(profile.show_profile, text="Мои записи")
dp.register_callback_query_handler(profile.read_receiver_comment, state=profile.Profile.viewing_slot)

dp.register_callback_query_handler(reminders.confirm_reminder, lambda c: c.data == "confirm")
dp.register_callback_query_handler(reminders.cancel_from_reminder, lambda c: c.data == "cancel_reminder")

async def on_startup(db):
    await create_tables()
    print("Bot started")

async def on_shutdown(dp):
    await storage.close()
    await storage.wait_closed()
    send_notification_to_admin("Бот остановлен")

if __name__ == "__main__":
    executor.start_polling(dp, skip_ubdate=True, on_startup=on_startup, on_shutdown=on_shutdown)