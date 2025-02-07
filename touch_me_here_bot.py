import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_ID
from database import create_tables
from handlers import start, massage_giving, massage_receiving, cancellation, profile
from utils import send_notification_to_admin

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

dp.include_router(start.router)
dp.include_router(massage_giving.router)
dp.include_router(massage_receiving.router)
dp.include_router(cancellation.router)
dp.include_router(profile.router)

async def on_startup(bot: Bot):
    try:
        await create_tables()
        logger.info("Бот запущен.")
        await send_notification_to_admin(bot, "Бот запущен.")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        await send_notification_to_admin(bot, f"Ошибка при запуске бота: {e}")


async def on_shutdown(bot: Bot):
    try:
        await bot.session.close()
        await storage.close()
        logger.info("Бот остановлен.")
        await send_notification_to_admin(bot, "Бот остановлен.")
    except Exception as e:
        logger.error(f"Ошибка при остановке бота: {e}")
        await send_notification_to_admin(bot, f"Ошибка при остановке бота: {e}")

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())