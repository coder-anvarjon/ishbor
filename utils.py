import re
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from aiogram.types import User as TgUser
from database import Database, User, Ad

class BotUtils:
    """Utility functions for the bot"""
    
    def __init__(self, db: Database):
        self.db = db
    
    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """Validate phone number format"""
        # Remove all non-digit characters
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Check if it's a valid Uzbek phone number or international format
        patterns = [
            r'^\+998\d{9}$',  # +998901234567
            r'^998\d{9}$',    # 998901234567
            r'^\d{9}$',       # 901234567
            r'^\+\d{10,15}$'  # International format
        ]
        
        return any(re.match(pattern, cleaned) for pattern in patterns)
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate Telegram username format"""
        pattern = r'^@[a-zA-Z0-9_]{5,32}$'
        return re.match(pattern, username) is not None
    
    @staticmethod
    def validate_contact(contact: str) -> bool:
        """Validate contact information (phone or username)"""
        return (BotUtils.validate_phone_number(contact) or 
                BotUtils.validate_username(contact))
    
    @staticmethod
    def format_phone_number(phone: str) -> str:
        """Format phone number to standard format"""
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Add +998 prefix if needed
        if cleaned.startswith('998') and len(cleaned) == 12:
            return '+' + cleaned
        elif cleaned.isdigit() and len(cleaned) == 9:
            return '+998' + cleaned
        else:
            return phone  # Return as is if can't format
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 50) -> str:
        """Truncate text to specified length"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML special characters"""
        return (text.replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;"))
    
    @staticmethod
    def get_status_emoji(status: str) -> str:
        """Get emoji for ad status"""
        emoji_map = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌',
            'expired': '⌛️'
        }
        return emoji_map.get(status, '❓')
    
    @staticmethod
    def get_status_text(status: str, lang: str = 'uz') -> str:
        """Get status text in specified language"""
        if lang == 'uz':
            status_map = {
                'pending': "Ko'rib chiqilmoqda",
                'approved': 'Tasdiqlangan',
                'rejected': 'Rad etilgan',
                'expired': 'Muddati tugagan'
            }
        else:  # English
            status_map = {
                'pending': 'Pending',
                'approved': 'Approved',
                'rejected': 'Rejected',
                'expired': 'Expired'
            }
        return status_map.get(status, 'Unknown')
    
    @staticmethod
    def format_date(dt: datetime, format_type: str = 'short') -> str:
        """Format datetime to readable string"""
        if format_type == 'short':
            return dt.strftime('%d.%m.%Y')
        elif format_type == 'long':
            return dt.strftime('%d.%m.%Y %H:%M')
        elif format_type == 'time_ago':
            now = datetime.utcnow()
            diff = now - dt
            
            if diff.days > 0:
                return f"{diff.days} kun oldin"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} soat oldin"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} daqiqa oldin"
            else:
                return "Hozirgina"
        else:
            return dt.strftime('%d.%m.%Y %H:%M')
    
    @staticmethod
    def generate_ad_preview(ad: Ad, user: User = None) -> str:
        """Generate ad preview text"""
        preview = f"""
📝 <b>{ad.title}</b>
🏷 {ad.category}
📄 {BotUtils.truncate_text(ad.description, 100)}
📞 {ad.contact}
"""
        if user:
            preview += f"👤 {user.full_name}\n"
        
        preview += f"📅 {BotUtils.format_date(ad.created_at)}"
        return preview
    
    @staticmethod
    def generate_channel_post(ad: Ad) -> str:
        """Generate formatted text for channel post"""
        return f"""
💼 <b>{ad.title}</b>

🏷 <b>Kategoriya:</b> {ad.category}

📄 <b>Tavsif:</b>
{ad.description}

📞 <b>Aloqa:</b> {ad.contact}

📅 <b>E'lon sanasi:</b> {BotUtils.format_date(ad.created_at)}

#ish #vacancy #{ad.category.replace(' ', '_').replace('/', '_')}
"""
    
    async def check_user_spam(self, user_id: int, hours: int = 1, max_ads: int = 5) -> bool:
        """Check if user is spamming (too many ads in short time)"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # This would need to be implemented in the database class
        # For now, return False (not spam)
        return False
    
    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        user = await self.db.get_user(user_id)
        if not user:
            return {}
        
        ads = await self.db.get_user_ads(user_id)
        
        stats = {
            'total_ads': len(ads),
            'approved_ads': len([ad for ad in ads if ad.status == 'approved']),
            'pending_ads': len([ad for ad in ads if ad.status == 'pending']),
            'rejected_ads': len([ad for ad in ads if ad.status == 'rejected']),
            'categories_used': list(set(ad.category for ad in ads)),
            'member_since': BotUtils.format_date(user.created_at),
            'last_ad_date': BotUtils.format_date(max(ad.created_at for ad in ads)) if ads else None
        }
        
        return stats
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text input"""
        # Remove extra whitespaces
        text = ' '.join(text.split())
        
        # Remove potentially harmful characters
        text = text.replace('\u202e', '')  # Right-to-left override
        text = text.replace('\u200b', '')  # Zero-width space
        
        return text.strip()
    
    @staticmethod
    def is_valid_telegram_id(telegram_id: str) -> bool:
        """Validate Telegram ID format"""
        try:
            tid = int(telegram_id)
            # Telegram IDs are typically 9-10 digits
            return 10000000 <= tid <= 9999999999
        except ValueError:
            return False
    
    async def backup_database(self) -> Dict[str, Any]:
        """Create a simple backup of important data"""
        try:
            users = await self.db.get_all_users()
            ads = await self.db.get_all_ads()
            
            backup_data = {
                'backup_date': datetime.utcnow().isoformat(),
                'users': [
                    {
                        'telegram_id': user.telegram_id,
                        'full_name': user.full_name,
                        'role': user.role,
                        'created_at': user.created_at.isoformat()
                    }
                    for user in users
                ],
                'ads': [
                    {
                        'id': ad.id,
                        'user_id': ad.user_id,
                        'title': ad.title,
                        'description': ad.description,
                        'category': ad.category,
                        'contact': ad.contact,
                        'status': ad.status,
                        'created_at': ad.created_at.isoformat()
                    }
                    for ad in ads
                ]
            }
            
            return backup_data
            
        except Exception as e:
            return {'error': str(e)}

class RateLimiter:
    """Simple rate limiter for bot actions"""
    
    def __init__(self):
        self.user_actions = {}  # user_id -> [timestamps]
    
    def is_rate_limited(self, user_id: int, max_actions: int = 10, 
                       time_window: int = 60) -> bool:
        """Check if user is rate limited"""
        now = datetime.utcnow()
        
        if user_id not in self.user_actions:
            self.user_actions[user_id] = []
        
        # Clean old timestamps
        cutoff_time = now - timedelta(seconds=time_window)
        self.user_actions[user_id] = [
            timestamp for timestamp in self.user_actions[user_id]
            if timestamp > cutoff_time
        ]
        
        # Check if user exceeds rate limit
        if len(self.user_actions[user_id]) >= max_actions:
            return True
        
        # Record current action
        self.user_actions[user_id].append(now)
        return False
    
    def clear_user_actions(self, user_id: int):
        """Clear user's action history"""
        self.user_actions.pop(user_id, None)

class MessageBuilder:
    """Helper class for building formatted messages"""
    
    @staticmethod
    def build_user_profile(user: User, stats: Dict[str, Any]) -> str:
        """Build user profile message"""
        return f"""
👤 <b>Foydalanuvchi profili</b>

📛 <b>Ism:</b> {user.full_name}
🆔 <b>ID:</b> <code>{user.telegram_id}</code>
👑 <b>Rol:</b> {user.role}
📅 <b>Ro'yxatdan o'tgan:</b> {BotUtils.format_date(user.created_at)}

📊 <b>Statistika:</b>
📋 Jami e'lonlar: {stats.get('total_ads', 0)}
✅ Tasdiqlangan: {stats.get('approved_ads', 0)}
⏳ Ko'rib chiqilmoqda: {stats.get('pending_ads', 0)}
❌ Rad etilgan: {stats.get('rejected_ads', 0)}

🏷 <b>Ishlatgan kategoriyalar:</b>
{', '.join(stats.get('categories_used', [])) if stats.get('categories_used') else 'Hali yo\'q'}
"""
    
    @staticmethod
    def build_admin_dashboard(stats: Dict[str, Any]) -> str:
        """Build admin dashboard message"""
        return f"""
📊 <b>Admin boshqaruv paneli</b>

👥 <b>Foydalanuvchilar:</b>
• Jami: {stats.get('total_users', 0)}
• Bugungi yangilar: {stats.get('today_users', 0)}

📋 <b>E'lonlar:</b>
• Jami: {stats.get('total_ads', 0)}
• ⏳ Kutilmoqda: {stats.get('pending_ads', 0)}
• ✅ Tasdiqlangan: {stats.get('approved_ads', 0)}
• ❌ Rad etilgan: {stats.get('rejected_ads', 0)}
• 📅 Bugungi: {stats.get('today_ads', 0)}

🏷 <b>Mashhur kategoriyalar:</b>
"""

# Global rate limiter instance
rate_limiter = RateLimiter()