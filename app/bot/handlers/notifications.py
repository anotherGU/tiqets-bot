from aiogram import types, Dispatcher, Bot
from aiogram.filters import Command
from database.crud import get_unique_logs_last_24h
import config


async def logs_command(message: types.Message):
    # Проверка, чтобы команду могли вызывать только админы
    admin_ids = [6444536776, 1727679734]  # замени на свои ID или вынеси в config
    if message.from_user.id not in admin_ids:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    logs = get_unique_logs_last_24h()
    if not logs:
        await message.answer("❌ За последние 24 часа логов не найдено.")
        return

    count = len(logs)
    response = f"📊 <b>Логи за последние 24 часа:</b>\nВсего: <b>{count}</b>\n\n"

    for log in logs:
        response += (
            f"🆔 <b>#{log['booking_id']}</b> || #{log['client_id']}\n"
            f"💳 {log['masked_pan']}\n"
            f"🕒 {log['created_at']}\n\n"
        )

    # Если сообщение слишком длинное — отправляем как файл
    if len(response) > 4000:
        await message.answer_document(("logs.txt", response.encode("utf-8")))
    else:
        await message.answer(response, parse_mode="HTML")


async def register_handlers(dp: Dispatcher, bot: Bot):
    dp.message.register(logs_command, Command("logs"))
