import asyncio
import logging
import sys
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from database import Database, User, Ad
from config import BOT_TOKEN, CHANNEL_ID

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Initialize database
db = Database()

# States for FSM
class AdCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_contact = State()
    waiting_for_category = State()

class AdminStates(StatesGroup):
    waiting_for_edit_title = State()
    waiting_for_edit_description = State()
    waiting_for_edit_contact = State()

# Categories
CATEGORIES = [
    "💼 Ofis ishi", "🏗 Qurilish", "🍽 Restoran/Kafe", 
    "🚗 Haydovchi", "🏥 Tibbiyot", "💻 IT", "📚 Ta'lim", "🔧 Xizmat"
]

# Keyboards
def get_main_keyboard():
    """Main keyboard for users"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ E'lon berish")],
            [KeyboardButton(text="📋 Mening e'lonlarim"), KeyboardButton(text="ℹ️ Yordam")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

def get_admin_keyboard():
    """Admin keyboard"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📋 Yangi e'lonlar")],
            [KeyboardButton(text="🗂 Barcha e'lonlar"), KeyboardButton(text="⚙️ Sozlamalar")],
            [KeyboardButton(text="👤 Foydalanuvchi rejimi")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

def get_superadmin_keyboard():
    """Super admin keyboard"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📋 Yangi e'lonlar")],
            [KeyboardButton(text="🗂 Barcha e'lonlar"), KeyboardButton(text="👥 Admin boshqaruv")],
            [KeyboardButton(text="⚙️ Sozlamalar"), KeyboardButton(text="👤 Foydalanuvchi rejimi")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

def get_categories_keyboard():
    """Categories inline keyboard"""
    keyboard = []
    for i in range(0, len(CATEGORIES), 2):
        row = [InlineKeyboardButton(text=CATEGORIES[i], callback_data=f"cat_{i}")]
        if i + 1 < len(CATEGORIES):
            row.append(InlineKeyboardButton(text=CATEGORIES[i + 1], callback_data=f"cat_{i + 1}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_ad_action_keyboard(ad_id: int):
    """Keyboard for ad actions (admin)"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{ad_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{ad_id}")
            ],
            [
                InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"edit_{ad_id}"),
                InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delete_{ad_id}")
            ]
        ]
    )
    return keyboard

def get_edit_keyboard(ad_id: int):
    """Edit options keyboard"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Sarlavha", callback_data=f"edit_title_{ad_id}")],
            [InlineKeyboardButton(text="📄 Tavsif", callback_data=f"edit_desc_{ad_id}")],
            [InlineKeyboardButton(text="📞 Aloqa", callback_data=f"edit_contact_{ad_id}")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"back_to_ad_{ad_id}")]
        ]
    )
    return keyboard

async def get_user_keyboard(user_id: int):
    """Get appropriate keyboard based on user role"""
    user = await db.get_user(user_id)
    if user and user.role == 'superadmin':
        return get_superadmin_keyboard()
    elif user and user.role == 'admin':
        return get_admin_keyboard()
    else:
        return get_main_keyboard()

# Handlers
@dp.message(CommandStart())
async def start_handler(message: Message):
    """Start command handler"""
    user = await db.get_user(message.from_user.id)
    
    if not user:
        # Create new user
        await db.create_user(
            telegram_id=message.from_user.id,
            full_name=message.from_user.full_name or "No name",
            role='user'
        )
    
    keyboard = await get_user_keyboard(message.from_user.id)
    
    welcome_text = f"""
🎉 <b>Farg'ona Jobs Bot</b>ga xush kelibsiz!

👋 Salom, {message.from_user.full_name}!

Bu bot orqali siz:
• 🆕 Ish e'lonlarini berishingiz
• 📋 O'z e'lonlaringizni kuzatishingiz
• 💼 Farg'ona viloyati bo'yicha ish imkoniyatlarini topishingiz mumkin

E'lonlaringiz admin tomonidan ko'rib chiqilgandan so'ng kanalda e'lon qilinadi.

<i>Botdan foydalanish uchun pastdagi tugmalardan birini tanlang:</i>
"""
    
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=keyboard)

@dp.message(F.text == "➕ E'lon berish")
async def create_ad_handler(message: Message, state: FSMContext):
    """Start ad creation process"""
    user = await db.get_user(message.from_user.id)
    
    # Check daily limit (3 ads per day)
    today_ads = await db.get_user_ads_today(message.from_user.id)
    if len(today_ads) >= 3:
        await message.answer(
            "⚠️ <b>Kunlik limit</b>\n\n"
            "Siz bugun allaqachon 3 ta e'lon bergansiz.\n"
            "Ertaga qaytadan harakat qiling.",
            parse_mode="HTML"
        )
        return
    
    await state.set_state(AdCreation.waiting_for_title)
    await message.answer(
        "📝 <b>Yangi e'lon yaratish</b>\n\n"
        "Ish nomini kiriting:\n"
        "<i>Masalan: Python dasturchi, Kassir, Qurilish ustasi</i>",
        parse_mode="HTML"
    )

@dp.message(AdCreation.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    """Process ad title"""
    if len(message.text) < 5 or len(message.text) > 100:
        await message.answer(
            "❌ Ish nomi 5-100 belgi orasida bo'lishi kerak.\n"
            "Qaytadan kiriting:"
        )
        return
    
    await state.update_data(title=message.text)
    await state.set_state(AdCreation.waiting_for_description)
    await message.answer(
        "📄 <b>Ish tavsifi</b>\n\n"
        "Ish haqida batafsil ma'lumot bering:\n"
        "<i>Talablar, ish vaqti, maosh va boshqa ma'lumotlar</i>",
        parse_mode="HTML"
    )

@dp.message(AdCreation.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    """Process ad description"""
    if len(message.text) < 10 or len(message.text) > 1000:
        await message.answer(
            "❌ Tavsif 10-1000 belgi orasida bo'lishi kerak.\n"
            "Qaytadan kiriting:"
        )
        return
    
    await state.update_data(description=message.text)
    await state.set_state(AdCreation.waiting_for_contact)
    await message.answer(
        "📞 <b>Aloqa ma'lumoti</b>\n\n"
        "Bog'lanish uchun telefon raqam yoki username kiriting:\n"
        "<i>Masalan: +998901234567 yoki @username</i>",
        parse_mode="HTML"
    )

@dp.message(AdCreation.waiting_for_contact)
async def process_contact(message: Message, state: FSMContext):
    """Process contact info"""
    if len(message.text) < 5 or len(message.text) > 50:
        await message.answer(
            "❌ Aloqa ma'lumoti 5-50 belgi orasida bo'lishi kerak.\n"
            "Qaytadan kiriting:"
        )
        return
    
    await state.update_data(contact=message.text)
    await state.set_state(AdCreation.waiting_for_category)
    await message.answer(
        "🏷 <b>Kategoriya tanlang:</b>",
        parse_mode="HTML",
        reply_markup=get_categories_keyboard()
    )

@dp.callback_query(F.data.startswith("cat_"))
async def process_category(callback: CallbackQuery, state: FSMContext):
    """Process category selection"""
    category_index = int(callback.data.split("_")[1])
    category = CATEGORIES[category_index]
    
    data = await state.get_data()
    
    # Create ad
    ad_id = await db.create_ad(
        user_id=callback.from_user.id,
        title=data['title'],
        description=data['description'],
        category=category,
        contact=data['contact'],
        status='pending'
    )
    
    await state.clear()
    
    # Notify user
    await callback.message.edit_text(
        f"✅ <b>E'lon muvaffaqiyatli yaratildi!</b>\n\n"
        f"📝 <b>Sarlavha:</b> {data['title']}\n"
        f"🏷 <b>Kategoriya:</b> {category}\n\n"
        f"⏳ E'loningiz admin tomonidan ko'rib chiqilmoqda.\n"
        f"Tasdiqlangandan so'ng kanalda e'lon qilinadi.",
        parse_mode="HTML"
    )
    
    # Notify admins
    await notify_admins_about_new_ad(ad_id)

async def notify_admins_about_new_ad(ad_id: int):
    """Notify admins about new ad"""
    ad = await db.get_ad(ad_id)
    if not ad:
        return
    
    user = await db.get_user(ad.user_id)
    admins = await db.get_admins()
    
    ad_text = f"""
🆕 <b>Yangi e'lon</b>

👤 <b>Foydalanuvchi:</b> {user.full_name}
📝 <b>Sarlavha:</b> {ad.title}
🏷 <b>Kategoriya:</b> {ad.category}
📄 <b>Tavsif:</b> {ad.description}
📞 <b>Aloqa:</b> {ad.contact}

🕐 <b>Sana:</b> {ad.created_at.strftime('%d.%m.%Y %H:%M')}
"""
    
    for admin in admins:
        try:
            await bot.send_message(
                admin.telegram_id,
                ad_text,
                parse_mode="HTML",
                reply_markup=get_ad_action_keyboard(ad_id)
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin.telegram_id}: {e}")

@dp.message(F.text == "📋 Mening e'lonlarim")
async def my_ads_handler(message: Message):
    """Show user's ads"""
    ads = await db.get_user_ads(message.from_user.id)
    
    if not ads:
        await message.answer(
            "📭 <b>E'lonlaringiz yo'q</b>\n\n"
            "Hozircha hech qanday e'lon bermagansiz.\n"
            "Yangi e'lon berish uchun \"➕ E'lon berish\" tugmasini bosing.",
            parse_mode="HTML"
        )
        return
    
    text = "📋 <b>Sizning e'lonlaringiz:</b>\n\n"
    
    for i, ad in enumerate(ads, 1):
        status_emoji = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌'
        }
        
        status_text = {
            'pending': 'Ko\'rib chiqilmoqda',
            'approved': 'Tasdiqlangan',
            'rejected': 'Rad etilgan'
        }
        
        text += f"{i}. {status_emoji.get(ad.status, '❓')} <b>{ad.title}</b>\n"
        text += f"   🏷 {ad.category}\n"
        text += f"   📅 {ad.created_at.strftime('%d.%m.%Y')}\n"
        text += f"   📊 {status_text.get(ad.status, 'Noma\'lum')}\n\n"
    
    await message.answer(text, parse_mode="HTML")

# Admin handlers
@dp.message(F.text == "📋 Yangi e'lonlar")
async def pending_ads_handler(message: Message):
    """Show pending ads to admin"""
    user = await db.get_user(message.from_user.id)
    if not user or user.role not in ['admin', 'superadmin']:
        await message.answer("❌ Sizda ushbu bo'limga kirish huquqi yo'q.")
        return
    
    ads = await db.get_ads_by_status('pending')
    
    if not ads:
        await message.answer("📭 Yangi e'lonlar yo'q.")
        return
    
    for ad in ads[:5]:  # Show max 5 ads at once
        user_info = await db.get_user(ad.user_id)
        ad_text = f"""
🆕 <b>Yangi e'lon</b>

👤 <b>Foydalanuvchi:</b> {user_info.full_name}
📝 <b>Sarlavha:</b> {ad.title}
🏷 <b>Kategoriya:</b> {ad.category}
📄 <b>Tavsif:</b> {ad.description}
📞 <b>Aloqa:</b> {ad.contact}

🕐 <b>Sana:</b> {ad.created_at.strftime('%d.%m.%Y %H:%M')}
"""
        await message.answer(
            ad_text,
            parse_mode="HTML",
            reply_markup=get_ad_action_keyboard(ad.id)
        )

@dp.callback_query(F.data.startswith("approve_"))
async def approve_ad_callback(callback: CallbackQuery):
    """Approve ad"""
    user = await db.get_user(callback.from_user.id)
    if not user or user.role not in ['admin', 'superadmin']:
        await callback.answer("❌ Sizda huquq yo'q!", show_alert=True)
        return
    
    ad_id = int(callback.data.split("_")[1])
    ad = await db.get_ad(ad_id)
    
    if not ad:
        await callback.answer("❌ E'lon topilmadi!", show_alert=True)
        return
    
    # Update ad status
    await db.update_ad_status(ad_id, 'approved')
    
    # Post to channel
    await post_ad_to_channel(ad)
    
    # Update message
    await callback.message.edit_text(
        f"✅ <b>E'lon tasdiqlandi va kanalga joylandi!</b>\n\n"
        f"📝 <b>Sarlavha:</b> {ad.title}",
        parse_mode="HTML"
    )
    
    # Notify user
    try:
        await bot.send_message(
            ad.user_id,
            f"🎉 <b>E'loningiz tasdiqlandi!</b>\n\n"
            f"📝 E'lon: {ad.title}\n"
            f"📢 E'loningiz kanalda e'lon qilindi.",
            parse_mode="HTML"
        )
    except:
        pass

async def post_ad_to_channel(ad: Ad):
    """Post approved ad to channel"""
    user = await db.get_user(ad.user_id)
    
    channel_text = f"""
💼 <b>{ad.title}</b>

🏷 <b>Kategoriya:</b> {ad.category}

📄 <b>Tavsif:</b>
{ad.description}

📞 <b>Aloqa:</b> {ad.contact}

📅 <b>E'lon sanasi:</b> {ad.created_at.strftime('%d.%m.%Y')}

#ish #vacancy #{ad.category.replace(' ', '_')}
"""
    
    try:
        await bot.send_message(
            CHANNEL_ID,
            channel_text,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to post to channel: {e}")

@dp.callback_query(F.data.startswith("reject_"))
async def reject_ad_callback(callback: CallbackQuery):
    """Reject ad"""
    user = await db.get_user(callback.from_user.id)
    if not user or user.role not in ['admin', 'superadmin']:
        await callback.answer("❌ Sizda huquq yo'q!", show_alert=True)
        return
    
    ad_id = int(callback.data.split("_")[1])
    ad = await db.get_ad(ad_id)
    
    if not ad:
        await callback.answer("❌ E'lon topilmadi!", show_alert=True)
        return
    
    # Update ad status
    await db.update_ad_status(ad_id, 'rejected')
    
    # Update message
    await callback.message.edit_text(
        f"❌ <b>E'lon rad etildi!</b>\n\n"
        f"📝 <b>Sarlavha:</b> {ad.title}",
        parse_mode="HTML"
    )
    
    # Notify user
    try:
        await bot.send_message(
            ad.user_id,
            f"😔 <b>E'loningiz rad etildi</b>\n\n"
            f"📝 E'lon: {ad.title}\n"
            f"💡 E'loningizni qaytadan ko'rib chiqib, yangi e'lon bering.",
            parse_mode="HTML"
        )
    except:
        pass

@dp.message(F.text == "📊 Statistika")
async def statistics_handler(message: Message):
    """Show statistics to admin"""
    user = await db.get_user(message.from_user.id)
    if not user or user.role not in ['admin', 'superadmin']:
        await message.answer("❌ Sizda ushbu bo'limga kirish huquqi yo'q.")
        return
    
    stats = await db.get_statistics()
    
    text = f"""
📊 <b>Bot statistikasi</b>

👥 <b>Foydalanuvchilar:</b> {stats['total_users']}
📋 <b>Jami e'lonlar:</b> {stats['total_ads']}

📈 <b>E'lonlar holati bo'yicha:</b>
⏳ Ko'rib chiqilmoqda: {stats['pending_ads']}
✅ Tasdiqlangan: {stats['approved_ads']}
❌ Rad etilgan: {stats['rejected_ads']}

📅 <b>Bugungi e'lonlar:</b> {stats['today_ads']}
👤 <b>Bugungi yangi foydalanuvchilar:</b> {stats['today_users']}

🏷 <b>Eng mashhur kategoriyalar:</b>
"""
    
    for category, count in stats['popular_categories']:
        text += f"• {category}: {count} ta\n"
    
    await message.answer(text, parse_mode="HTML")

# Background task to clean old ads
async def cleanup_old_ads():
    """Clean ads older than 7 days"""
    while True:
        try:
            await db.cleanup_old_ads()
            logger.info("Old ads cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning old ads: {e}")
        
        # Wait 24 hours
        await asyncio.sleep(24 * 60 * 60)

# Main function
async def main():
    """Main function"""
    # Initialize database
    await db.init_db()
    
    # Start cleanup task
    asyncio.create_task(cleanup_old_ads())
    
    # Start bot
    logger.info("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")