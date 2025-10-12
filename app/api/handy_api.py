import httpx

HANDYAPI_KEY = "HAS-0YH7P8rbGpwLRHq4gM0BX6K"
HANDYAPI_BASE_URL = "https://data.handyapi.com/bin/"

async def get_card_info(bin_number):
    """Получает информацию о карте по BIN через HandyAPI"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{HANDYAPI_BASE_URL}{bin_number}",
                headers={"Authorization": f"Bearer {HANDYAPI_KEY}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                country_code = data.get("Country", {}).get("A2", "").upper()
                flag_emoji = get_country_flag_emoji(country_code)
                
                return {
                    "flag": flag_emoji,
                    "country": data.get("Country", {}).get("Name", "N/A").upper(),
                    "brand": data.get("Scheme", "N/A"),
                    "type": data.get("Type", "N/A"),
                    "level": data.get("CardTier", "N/A"),
                    "bank": data.get("Issuer", "N/A"),
                    "status": data.get("Status", "N/A"),
                    "success": True
                }
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_country_flag_emoji(country_code):
    """Конвертирует код страны в эмодзи флага"""
    if len(country_code) != 2:
        return "🏴"
    
    flag_emoji = ''.join(chr(ord(c) + 127397) for c in country_code.upper())
    return flag_emoji

def format_card_info(card_info):
    """Форматирует информацию о карте в красивый текст с эмодзи"""
    if not card_info.get("success"):
        return "❌ Информация о карте недоступна"
    
    if card_info.get("status") != "SUCCESS":
        return f"❌ Статус запроса: {card_info.get('status', 'UNKNOWN')}"
    
    return (
        f"{card_info['flag']} {card_info['country']}\n"
        f"🏷️ <b>Brand:</b> {card_info['brand']}\n"
        f"💳 <b>Type:</b> {card_info['type']}\n"
        f"⭐ <b>Level:</b> {card_info['level']}\n"
        f"🏦 <b>Bank:</b> {card_info['bank']}\n"
    )