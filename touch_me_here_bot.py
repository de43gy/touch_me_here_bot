from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, CommandStart
import asyncio
import logging

from config import BOT_TOKEN, ADMIN_ID
from database import create_tables
from handlers import start, massage_giving, massage_receiving, cancellation, profile
from utils import send_notification_to_admin

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    dp.include_router(start.router)
    dp.include_router(massage_giving.router)
    dp.include_router(massage_receiving.router)
    dp.include_router(cancellation.router)
    dp.include_router(profile.router)

    logger.info("Starting bot...")
    try:
        await create_tables()
        await send_notification_to_admin(bot, "Бот запущен.")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        await send_notification_to_admin(bot, f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())