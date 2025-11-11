# [file name]: main.py
# [file content begin]
import sys
import os
import asyncio

# Добавляем текущую директорию в Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from fastapi import FastAPI
import uvicorn
from app.bot.handlers.callbacks import register_callbacks
from app.bot.handlers.notifications import register_handlers
from app.api.endpoints import register_endpoints
from app.database.models import init_db
import config

# Импортируем админский бот
from admin_bot import (
    notify_log_taken, notify_log_taken_over, notify_action,
    notify_user_response, notify_balance, notify_sms, notify_card_change,
    start_admin_bot
)

storage = MemoryStorage()
bot = Bot(token=config.TOKEN)
dp = Dispatcher(storage=storage)
app = FastAPI()

async def main():
    # Инициализация БД
    init_db()
    
    # Регистрация обработчиков
    register_callbacks(dp)
    await register_handlers(dp, bot) 
    register_endpoints(app, bot)
    
    # Запуск основного бота и сервера
    bot_task = asyncio.create_task(dp.start_polling(bot))
    
    config_uvicorn = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(config_uvicorn)
    server_task = asyncio.create_task(server.serve())
    
    # Запуск админского бота
    admin_bot_task = asyncio.create_task(start_admin_bot())
    
    await asyncio.gather(bot_task, server_task, admin_bot_task)


if __name__ == "__main__":
    asyncio.run(main())
# [file content end]