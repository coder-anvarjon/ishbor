import asyncio
from typing import List
from aiogram import types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import Database, User, Ad
from config import MESSAGES

# Admin-specific states
class AdminStates(StatesGroup):
    waiting_for_new_admin_id = State()
    waiting_for_edit_title = State()
    waiting_for_edit_description = State()
    waiting_for_edit_contact = State()
    waiting_for_broadcast_message = State()

class AdminHandlers:
    def __init__(self, bot, db: Database):
        self.bot = bot
        self.db = db
    
    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin or superadmin"""
        user = await self.db.get_user(user_id)
        return user and user.role in ['admin', 'superadmin']
    
    async def is_superadmin(self, user_id: int) -> bool:
        """Check if user is superadmin"""
        user = await self.db.get_user(user_id)
        return user and user.role == 'superadmin'
    
    def get_admin_management_keyboard(self):
        """Admin management keyboard for superadmin"""
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="add_admin")],
                [InlineKeyboardButton(text="👥 Adminlar ro'yxati", callback_data="list_admins")],
                [InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="broadcast")],
                [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_main")]
            ]
        )
        return keyboard
    
    def get_admin_list_keyboard(self, admins: List[User]):
        """Generate keyboard with admin list"""
        keyboard = []
        for admin in admins:
            if admin.role == 'admin':  # Don't show superadmins in removal list
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"❌ {admin.full_name}",
                        callback_data=f"remove_admin_{admin.telegram_id}"
                    )
                ])
        keyboard.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_management")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    async def handle_admin_management(self, callback: CallbackQuery):
        """Handle admin management menu"""
        if not await self.is_superadmin(callback.from_user.id):
            await callback.answer("❌ Sizda huquq yo'q!", show_alert=True)
            return
        
        text = """
👥 <b>Admin boshqaruv</b>

Bu bo'limda siz:
• Yangi adminlar qo'shishingiz
• Mavjud adminlarni ko'rishingiz
• Adminlarni olib tashlashingiz
• Barcha foydalanuvchilarga xabar yuborishingiz mumkin
"""
        
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=self.get_admin_management_keyboard()
        )
    
    async def handle_add_admin(self, callback: CallbackQuery, state: FSMContext):
        """Start add admin process"""
        if not await self.is_superadmin(callback.from_user.id):
            await callback.answer("❌ Sizda huquq yo'q!", show_alert=True)
            return
        
        await state.set_state(AdminStates.waiting_for_new_admin_id)
        await callback.message.edit_text(
            "👤 <b>Yangi admin qo'shish</b>\n\n"
            "Admin qilmoqchi bo'lgan foydalanuvchining Telegram ID raqamini yuboring:\n\n"
            "<i>Misol: 123456789</i>\n\n"
            "❌ Bekor qilish uchun /cancel buyrug'ini yuboring",
            parse_mode="HTML"
        )
    
    async def process_new_admin_id(self, message: Message, state: FSMContext):
        """Process new admin ID"""
        try:
            admin_id = int(message.text.strip())
        except ValueError:
            await message.answer("❌ Noto'g'ri format! Faqat raqam kiriting.")
            return
        
        # Check if user exists
        user = await self.db.get_user(admin_id)
        if not user:
            await message.answer("❌ Bu ID bilan foydalanuvchi topilmadi!")
            return
        
        if user.role in ['admin', 'superadmin']:
            await message.answer("❌ Bu foydalanuvchi allaqachon admin!")
            return
        
        # Update user role
        success = await self.db.update_user_role(admin_id, 'admin')
        if success:
            await message.answer(
                f"✅ <b>Yangi admin qo'shildi!</b>\n\n"
                f"👤 {user.full_name} (ID: {admin_id})",
                parse_mode="HTML"
            )
            
            # Notify new admin
            try:
                await self.bot.send_message(
                    admin_id,
                    "🎉 <b>Tabriklaymiz!</b>\n\n"
                    "Siz endi botning admini bo'ldingiz.\n"
                    "Admin panelga kirish uchun /start buyrug'ini yuboring.",
                    parse_mode="HTML"
                )
            except:
                pass
        else:
            await message.answer("❌ Xatolik yuz berdi!")
        
        await state.clear()
    
    async def handle_list_admins(self, callback: CallbackQuery):
        """Show admin list"""
        if not await self.is_superadmin(callback.from_user.id):
            await callback.answer("❌ Sizda huquq yo'q!", show_alert=True)
            return
        
        admins = await self.db.get_admins()
        
        if not admins:
            await callback.message.edit_text(
                "📭 Adminlar yo'q",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin_management")]]
                )
            )
            return
        
        text = "👥 <b>Adminlar ro'yxati:</b>\n\n"
        
        for admin in admins:
            role_emoji = "👑" if admin.role == "superadmin" else "👤"
            text += f"{role_emoji} {admin.full_name}\n"
            text += f"   ID: <code>{admin.telegram_id}</code>\n"
            text += f"   Role: {admin.role}\n\n"
        
        text += "<i>Admin o'chirish uchun pastdagi tugmalardan birini bosing:</i>"
        
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=self.get_admin_list_keyboard(admins)
        )
    
    async def handle_remove_admin(self, callback: CallbackQuery):
        """Remove admin"""
        if not await self.is_superadmin(callback.from_user.id):
            await callback.answer("❌ Sizda huquq yo'q!", show_alert=True)
            return
        
        admin_id = int(callback.data.split("_")[2])
        user = await self.db.get_user(admin_id)
        
        if not user:
            await callback.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
            return
        
        if user.role == 'superadmin':
            await callback.answer("❌ Superadminni olib tashlash mumkin emas!", show_alert=True)
            return
        
        # Update user role to regular user
        success = await self.db.update_user_role(admin_id, 'user')
        if success:
            await callback.answer(f"✅ {user.full_name} admin huquqidan mahrum qilindi!")
            
            # Notify removed admin
            try:
                await self.bot.send_message(
                    admin_id,
                    "📢 <b>Xabar</b>\n\n"
                    "Sizning admin huquqlaringiz olib tashlandi.",
                    parse_mode="HTML"
                )
            except:
                pass
            
            # Refresh admin list
            await self.handle_list_admins(callback)
        else:
            await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)
    
    async def handle_broadcast_start(self, callback: CallbackQuery, state: FSMContext):
        """Start broadcast message process"""
        if not await self.is_superadmin(callback.from_user.id):
            await callback.answer("❌ Sizda huquq yo'q!", show_alert=True)
            return
        
        await state.set_state(AdminStates.waiting_for_broadcast_message)
        await callback.message.edit_text(
            "📢 <b>Barcha foydalanuvchilarga xabar yuborish</b>\n\n"
            "Yubormoqchi bo'lgan xabaringizni yozing:\n\n"
            "<i>⚠️ Xabar barcha bot foydalanuvchilariga yuboriladi!</i>\n\n"
            "❌ Bekor qilish uchun /cancel buyrug'ini yuboring",
            parse_mode="HTML"
        )
    
    async def process_broadcast_message(self, message: Message, state: FSMContext):
        """Process broadcast message"""
        if not await self.is_superadmin(message.from_user.id):
            return
        
        broadcast_text = message.text
        
        # Get all users
        users = await self.db.get_all_users()
        
        if not users:
            await message.answer("❌ Foydalanuvchilar topilmadi!")
            await state.clear()
            return
        
        # Send confirmation
        confirm_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Ha, yuborish", callback_data="confirm_broadcast"),
                    InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_broadcast")
                ]
            ]
        )
        
        await state.update_data(broadcast_text=broadcast_text, users=users)
        
        await message.answer(
            f"📢 <b>Xabarni tasdiqlang:</b>\n\n"
            f"<i>{broadcast_text}</i>\n\n"
            f"👥 <b>Foydalanuvchilar soni:</b> {len(users)}\n\n"
            f"Xabarni yuborishni tasdiqlaysizmi?",
            parse_mode="HTML",
            reply_markup=confirm_keyboard
        )
    
    async def handle_confirm_broadcast(self, callback: CallbackQuery, state: FSMContext):
        """Handle broadcast confirmation"""
        data = await state.get_data()
        broadcast_text = data.get('broadcast_text')
        users = data.get('users', [])
        
        await callback.message.edit_text(
            f"📤 <b>Xabar yuborilmoqda...</b>\n\n"
            f"👥 Jami foydalanuvchilar: {len(users)}",
            parse_mode="HTML"
        )
        
        success_count = 0
        failed_count = 0
        
        # Send message to all users
        for user in users:
            try:
                await self.bot.send_message(
                    user.telegram_id,
                    f"📢 <b>Yangilik</b>\n\n{broadcast_text}",
                    parse_mode="HTML"
                )
                success_count += 1
                await asyncio.sleep(0.05)  # Rate limiting
            except Exception as e:
                failed_count += 1
                if "bot was blocked" not in str(e).lower():
                    # Log only non-blocking errors
                    print(f"Broadcast error for user {user.telegram_id}: {e}")
        
        # Send results
        await callback.message.edit_text(
            f"✅ <b>Xabar yuborish yakunlandi!</b>\n\n"
            f"📤 Muvaffaqiyatli: {success_count}\n"
            f"❌ Xatolik: {failed_count}\n\n"
            f"<i>Xatoliklar asosan bot bloklangan foydalanuvchilar tufayli.</i>",
            parse_mode="HTML"
        )
        
        await state.clear()
    
    async def handle_cancel_broadcast(self, callback: CallbackQuery, state: FSMContext):
        """Cancel broadcast"""
        await callback.message.edit_text("❌ Xabar yuborish bekor qilindi.")
        await state.clear()
    
    # Enhanced ad management for admins
    async def handle_edit_ad(self, callback: CallbackQuery):
        """Handle edit ad request"""
        if not await self.is_admin(callback.from_user.id):
            await callback.answer("❌ Sizda huquq yo'q!", show_alert=True)
            return
        
        ad_id = int(callback.data.split("_")[1])
        ad = await self.db.get_ad(ad_id)
        
        if not ad:
            await callback.answer("❌ E'lon topilmadi!", show_alert=True)
            return
        
        edit_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📝 Sarlavha", callback_data=f"edit_title_{ad_id}")],
                [InlineKeyboardButton(text="📄 Tavsif", callback_data=f"edit_desc_{ad_id}")],
                [InlineKeyboardButton(text="📞 Aloqa", callback_data=f"edit_contact_{ad_id}")],
                [InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"back_to_ad_{ad_id}")]
            ]
        )
        
        user = await self.db.get_user(ad.user_id)
        edit_text = f"""
✏️ <b>E'lonni tahrirlash</b>

👤 <b>Foydalanuvchi:</b> {user.full_name if user else 'Noma\'lum'}
📝 <b>Sarlavha:</b> {ad.title}
🏷 <b>Kategoriya:</b> {ad.category}
📄 <b>Tavsif:</b> {ad.description[:100]}{'...' if len(ad.description) > 100 else ''}
📞 <b>Aloqa:</b> {ad.contact}

Nimani tahrirlamoqchisiz?
"""
        
        await callback.message.edit_text(
            edit_text,
            parse_mode="HTML",
            reply_markup=edit_keyboard
        )
    
    async def handle_edit_title(self, callback: CallbackQuery, state: FSMContext):
        """Start edit title process"""
        if not await self.is_admin(callback.from_user.id):
            await callback.answer("❌ Sizda huquq yo'q!", show_alert=True)
            return
        
        ad_id = int(callback.data.split("_")[2])
        ad = await self.db.get_ad(ad_id)
        
        if not ad:
            await callback.answer("❌ E'lon topilmadi!", show_alert=True)
            return
        
        await state.set_state(AdminStates.waiting_for_edit_title)
        await state.update_data(edit_ad_id=ad_id)
        
        await callback.message.edit_text(
            f"📝 <b>Sarlavhani tahrirlash</b>\n\n"
            f"<b>Joriy sarlavha:</b> {ad.title}\n\n"
            f"Yangi sarlavhani kiriting:",
            parse_mode="HTML"
        )
    
    async def process_edit_title(self, message: Message, state: FSMContext):
        """Process new title"""
        if not await self.is_admin(message.from_user.id):
            return
        
        data = await state.get_data()
        ad_id = data.get('edit_ad_id')
        
        if not ad_id:
            await message.answer("❌ Xatolik yuz berdi!")
            await state.clear()
            return
        
        new_title = message.text.strip()
        
        if len(new_title) < 5 or len(new_title) > 100:
            await message.answer("❌ Sarlavha 5-100 belgi orasida bo'lishi kerak!")
            return
        
        # Update ad
        success = await self.db.update_ad(ad_id, title=new_title)
        
        if success:
            await message.answer(f"✅ Sarlavha yangilandi: {new_title}")
            
            # Notify ad owner
            ad = await self.db.get_ad(ad_id)
            if ad:
                try:
                    await self.bot.send_message(
                        ad.user_id,
                        f"✏️ <b>E'loningiz tahrirlandi</b>\n\n"
                        f"📝 Yangi sarlavha: {new_title}",
                        parse_mode="HTML"
                    )
                except:
                    pass
        else:
            await message.answer("❌ Xatolik yuz berdi!")
        
        await state.clear()
    
    async def handle_delete_ad(self, callback: CallbackQuery):
        """Delete ad"""
        if not await self.is_admin(callback.from_user.id):
            await callback.answer("❌ Sizda huquq yo'q!", show_alert=True)
            return
        
        ad_id = int(callback.data.split("_")[1])
        ad = await self.db.get_ad(ad_id)
        
        if not ad:
            await callback.answer("❌ E'lon topilmadi!", show_alert=True)
            return
        
        # Confirm deletion
        confirm_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"confirm_delete_{ad_id}"),
                    InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"back_to_ad_{ad_id}")
                ]
            ]
        )
        
        await callback.message.edit_text(
            f"🗑 <b>E'lonni o'chirish</b>\n\n"
            f"📝 <b>Sarlavha:</b> {ad.title}\n\n"
            f"❗️ Bu amalni bekor qilib bo'lmaydi!\n"
            f"E'lonni o'chirishni tasdiqlaysizmi?",
            parse_mode="HTML",
            reply_markup=confirm_keyboard
        )
    
    async def handle_confirm_delete(self, callback: CallbackQuery):
        """Confirm ad deletion"""
        ad_id = int(callback.data.split("_")[2])
        ad = await self.db.get_ad(ad_id)
        
        if not ad:
            await callback.answer("❌ E'lon topilmadi!", show_alert=True)
            return
        
        # Delete ad
        success = await self.db.delete_ad(ad_id)
        
        if success:
            await callback.message.edit_text(
                f"🗑 <b>E'lon o'chirildi!</b>\n\n"
                f"📝 <b>Sarlavha:</b> {ad.title}",
                parse_mode="HTML"
            )
            
            # Notify ad owner
            try:
                await self.bot.send_message(
                    ad.user_id,
                    f"🗑 <b>E'loningiz o'chirildi</b>\n\n"
                    f"📝 E'lon: {ad.title}\n"
                    f"💡 Agar bu xato bo'lsa, adminlar bilan bog'laning.",
                    parse_mode="HTML"
                )
            except:
                pass
        else:
            await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)
    
    async def handle_back_to_ad(self, callback: CallbackQuery):
        """Go back to ad details"""
        ad_id = int(callback.data.split("_")[3])
        
        # Re-show the ad with action buttons
        await self.show_ad_for_admin(callback, ad_id)
    
    async def show_ad_for_admin(self, callback: CallbackQuery, ad_id: int):
        """Show ad details for admin with action buttons"""
        ad = await self.db.get_ad(ad_id)
        
        if not ad:
            await callback.answer("❌ E'lon topilmadi!", show_alert=True)
            return
        
        user = await self.db.get_user(ad.user_id)
        
        ad_text = f"""
📋 <b>E'lon ma'lumotlari</b>

👤 <b>Foydalanuvchi:</b> {user.full_name if user else 'Noma\'lum'}
📝 <b>Sarlavha:</b> {ad.title}
🏷 <b>Kategoriya:</b> {ad.category}
📄 <b>Tavsif:</b> {ad.description}
📞 <b>Aloqa:</b> {ad.contact}
📊 <b>Holat:</b> {ad.status}

🕐 <b>Sana:</b> {ad.created_at.strftime('%d.%m.%Y %H:%M')}
"""
        
        # Create appropriate keyboard based on ad status
        keyboard_buttons = []
        
        if ad.status == 'pending':
            keyboard_buttons = [
                [
                    InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{ad_id}"),
                    InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{ad_id}")
                ],
                [
                    InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"edit_{ad_id}"),
                    InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delete_{ad_id}")
                ]
            ]
        else:
            keyboard_buttons = [
                [
                    InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"edit_{ad_id}"),
                    InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delete_{ad_id}")
                ]
            ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            ad_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )