import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# Channel configuration
CHANNEL_ID = os.getenv("CHANNEL_ID")  # e.g., "@fargona_jobs" or "-1001234567890"
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID environment variable is required")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Default PostgreSQL connection for local development
    DATABASE_URL = "postgresql+asyncpg://username:password@localhost/fargona_jobs_bot"
    print("Warning: Using default DATABASE_URL for local development")

# Admin configuration
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "123456789"))  # Replace with your Telegram ID

# Bot settings
MAX_DAILY_ADS = int(os.getenv("MAX_DAILY_ADS", "3"))
AD_EXPIRY_DAYS = int(os.getenv("AD_EXPIRY_DAYS", "7"))

# Text limits
MIN_TITLE_LENGTH = 5
MAX_TITLE_LENGTH = 100
MIN_DESCRIPTION_LENGTH = 10
MAX_DESCRIPTION_LENGTH = 1000
MIN_CONTACT_LENGTH = 5
MAX_CONTACT_LENGTH = 50

# Categories
JOB_CATEGORIES = [
    "💼 Ofis ishi",
    "🏗 Qurilish", 
    "🍽 Restoran/Kafe",
    "🚗 Haydovchi",
    "🏥 Tibbiyot",
    "💻 IT",
    "📚 Ta'lim",
    "🔧 Xizmat",
    "🛍 Savdo",
    "🏭 Ishlab chiqarish",
    "🎨 Ijodiy",
    "📞 Call-center"
]

# Messages
MESSAGES = {
    'welcome': """
🎉 <b>Farg'ona Jobs Bot</b>ga xush kelibsiz!

👋 Salom, {name}!

Bu bot orqali siz:
• 🆕 Ish e'lonlarini berishingiz
• 📋 O'z e'lonlaringizni kuzatishingiz
• 💼 Farg'ona viloyati bo'yicha ish imkoniyatlarini topishingiz mumkin

E'lonlaringiz admin tomonidan ko'rib chiqilgandan so'ng kanalda e'lon qilinadi.

<i>Botdan foydalanish uchun pastdagi tugmalardan birini tanlang:</i>
""",
    
    'help': """
ℹ️ <b>Bot haqida yordam</b>

<b>Foydalanuvchilar uchun:</b>
• ➕ E'lon berish - yangi ish e'loni yaratish
• 📋 Mening e'lonlarim - o'z e'lonlaringizni ko'rish
• ℹ️ Yordam - bu yordam sahifasi

<b>E'lon berish jarayoni:</b>
1. "E'lon berish" tugmasini bosing
2. Ish nomini kiriting
3. Batafsil tavsif yozing
4. Aloqa ma'lumotingizni qoldiring
5. Kategoriya tanlang

<b>Cheklovlar:</b>
• Kuniga maksimum {max_daily} ta e'lon
• E'lonlar {expiry_days} kundan keyin o'chiriladi
• Barcha e'lonlar admin tekshiruvidan o'tadi

<b>Aloqa:</b>
Savol va takliflar uchun: @admin_username
""",
    
    'daily_limit_reached': """
⚠️ <b>Kunlik limit</b>

Siz bugun allaqachon {count} ta e'lon bergansiz.
Ertaga qaytadan harakat qiling.
""",
    
    'ad_created': """
✅ <b>E'lon muvaffaqiyatli yaratildi!</b>

📝 <b>Sarlavha:</b> {title}
🏷 <b>Kategoriya:</b> {category}

⏳ E'loningiz admin tomonidan ko'rib chiqilmoqda.
Tasdiqlangandan so'ng kanalda e'lon qilinadi.
""",
    
    'ad_approved_user': """
🎉 <b>E'loningiz tasdiqlandi!</b>

📝 E'lon: {title}
📢 E'loningiz kanalda e'lon qilindi.
""",
    
    'ad_rejected_user': """
😔 <b>E'loningiz rad etildi</b>

📝 E'lon: {title}
💡 E'loningizni qaytadan ko'rib chiqib, yangi e'lon bering.
""",
    
    'no_ads': """
📭 <b>E'lonlaringiz yo'q</b>

Hozircha hech qanday e'lon bermagansiz.
Yangi e'lon berish uchun "➕ E'lon berish" tugmasini bosing.
""",
    
    'access_denied': """
❌ Sizda ushbu bo'limga kirish huquqi yo'q.
""",
    
    'no_pending_ads': """
📭 Yangi e'lonlar yo'q.
""",
    
    'ad_approved_admin': """
✅ <b>E'lon tasdiqlandi va kanalga joylandi!</b>

📝 <b>Sarlavha:</b> {title}
""",
    
    'ad_rejected_admin': """
❌ <b>E'lon rad etildi!</b>

📝 <b>Sarlavha:</b> {title}
""",
    
    'ad_not_found': """
❌ E'lon topilmadi!
""",
    
    'invalid_input': """
❌ Noto'g'ri kiritildi. Qaytadan urinib ko'ring.
"""
}

# Logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.FileHandler',
            'filename': 'bot.log',
            'mode': 'a',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default', 'file'],
            'level': 'INFO',
            'propagate': False
        }
    }
}