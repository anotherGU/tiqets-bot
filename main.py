import sys
import os

# Добавляем текущую директорию в Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher
from fastapi import FastAPI
import uvicorn
import asyncio
from app.bot.handlers.callbacks import register_callbacks
from app.bot.handlers.notifications import register_handlers
from app.api.endpoints import register_endpoints
from app.database.models import init_db
import config

bot = Bot(token=config.TOKEN_TEST)
dp = Dispatcher()
app = FastAPI()

async def main():
    # Инициализация БД
    init_db()
    
    # Регистрация обработчиков
    register_callbacks(dp)
    await register_handlers(dp, bot) 
    register_endpoints(app, bot)
    
    # Запуск бота и сервера
    bot_task = asyncio.create_task(dp.start_polling(bot))
    
    config_uvicorn = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(config_uvicorn)
    server_task = asyncio.create_task(server.serve())
    
    await asyncio.gather(bot_task, server_task)

if __name__ == "__main__":
    asyncio.run(main())