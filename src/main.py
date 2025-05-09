import asyncio
import logging
from aiogram import executor

from src.config import *
from src.handlers import *
from src.timers import *

logging.basicConfig(level=logging.INFO)


async def on_startup():
    await telegraph.create_account(short_name=f"@{short_name}", author_url=f"https://t.me/{short_name}")
    logging.info("Bot started succefully")

if __name__ == "__main__":
    scheduler.start()
    executor.start_polling(dp, on_startup=asyncio.run(on_startup()), skip_updates=False)
