import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import asyncpg
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import func, desc

from config import DATABASE_URL

Base = declarative_base()

class User(Base):
    """User model"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default='user')  # user, admin, superadmin
    created_at = Column(DateTime, default=datetime.utcnow)
    is_blocked = Column(Boolean, default=False)

class Ad(Base):
    """Ad model"""
    __tablename__ = 'ads'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    contact = Column(String(100), nullable=False)
    status = Column(String(50), default='pending')  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    approved_by = Column(Integer, nullable=True)
    approved_at = Column(DateTime, nullable=True)

class BotSettings(Base):
    """Bot settings model"""
    __tablename__ = 'bot_settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Database:
    """Database operations class"""
    
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def init_db(self):
        """Initialize database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create default superadmin if not exists
        await self.create_default_superadmin()
    
    async def create_default_superadmin(self):
        """Create default superadmin user"""
        # Replace with your Telegram ID
        SUPERADMIN_ID = 123456789  # Your Telegram ID here
        
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == SUPERADMIN_ID)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                superadmin = User(
                    telegram_id=SUPERADMIN_ID,
                    full_name="SuperAdmin",
                    role="superadmin"
                )
                session.add(superadmin)
                await session.commit()
    
    # User operations
    async def create_user(self, telegram_id: int, full_name: str, role: str = 'user') -> User:
        """Create new user"""
        async with self.async_session() as session:
            user = User(
                telegram_id=telegram_id,
                full_name=full_name,
                role=role
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
    
    async def get_user(self, telegram_id: int) -> Optional[User]:
        """Get user by telegram ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
    
    async def update_user_role(self, telegram_id: int, role: str) -> bool:
        """Update user role"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                user.role = role
                await session.commit()
                return True
            return False
    
    async def get_admins(self) -> List[User]:
        """Get all admin users"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.role.in_(['admin', 'superadmin']))
            )
            return result.scalars().all()
    
    async def block_user(self, telegram_id: int) -> bool:
        """Block user"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                user.is_blocked = True
                await session.commit()
                return True
            return False
    
    # Ad operations
    async def create_ad(self, user_id: int, title: str, description: str, 
                       category: str, contact: str, status: str = 'pending') -> int:
        """Create new ad"""
        async with self.async_session() as session:
            ad = Ad(
                user_id=user_id,
                title=title,
                description=description,
                category=category,
                contact=contact,
                status=status
            )
            session.add(ad)
            await session.commit()
            await session.refresh(ad)
            return ad.id
    
    async def get_ad(self, ad_id: int) -> Optional[Ad]:
        """Get ad by ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Ad).where(Ad.id == ad_id)
            )
            return result.scalar_one_or_none()
    
    async def update_ad_status(self, ad_id: int, status: str, approved_by: int = None) -> bool:
        """Update ad status"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Ad).where(Ad.id == ad_id)
            )
            ad = result.scalar_one_or_none()
            
            if ad:
                ad.status = status
                if status == 'approved' and approved_by:
                    ad.approved_by = approved_by
                    ad.approved_at = datetime.utcnow()
                await session.commit()
                return True
            return False
    
    async def update_ad(self, ad_id: int, title: str = None, description: str = None, 
                       contact: str = None) -> bool:
        """Update ad fields"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Ad).where(Ad.id == ad_id)
            )
            ad = result.scalar_one_or_none()
            
            if ad:
                if title:
                    ad.title = title
                if description:
                    ad.description = description
                if contact:
                    ad.contact = contact
                await session.commit()
                return True
            return False
    
    async def delete_ad(self, ad_id: int) -> bool:
        """Delete ad"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Ad).where(Ad.id == ad_id)
            )
            ad = result.scalar_one_or_none()
            
            if ad:
                await session.delete(ad)
                await session.commit()
                return True
            return False
    
    async def get_user_ads(self, telegram_id: int) -> List[Ad]:
        """Get user's ads"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Ad).where(Ad.user_id == telegram_id)
                .order_by(desc(Ad.created_at))
            )
            return result.scalars().all()
    
    async def get_user_ads_today(self, telegram_id: int) -> List[Ad]:
        """Get user's ads created today"""
        today = datetime.utcnow().date()
        async with self.async_session() as session:
            result = await session.execute(
                select(Ad).where(
                    Ad.user_id == telegram_id,
                    func.date(Ad.created_at) == today
                )
            )
            return result.scalars().all()
    
    async def get_ads_by_status(self, status: str, limit: int = 50) -> List[Ad]:
        """Get ads by status"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Ad).where(Ad.status == status)
                .order_by(desc(Ad.created_at))
                .limit(limit)
            )
            return result.scalars().all()
    
    async def get_all_ads(self, limit: int = 100) -> List[Ad]:
        """Get all ads"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Ad).order_by(desc(Ad.created_at)).limit(limit)
            )
            return result.scalars().all()
    
    # Statistics
    async def get_statistics(self) -> Dict[str, Any]:
        """Get bot statistics"""
        async with self.async_session() as session:
            # Total users
            total_users_result = await session.execute(
                select(func.count(User.id))
            )
            total_users = total_users_result.scalar()
            
            # Total ads
            total_ads_result = await session.execute(
                select(func.count(Ad.id))
            )
            total_ads = total_ads_result.scalar()
            
            # Ads by status
            pending_ads_result = await session.execute(
                select(func.count(Ad.id)).where(Ad.status == 'pending')
            )
            pending_ads = pending_ads_result.scalar()
            
            approved_ads_result = await session.execute(
                select(func.count(Ad.id)).where(Ad.status == 'approved')
            )
            approved_ads = approved_ads_result.scalar()
            
            rejected_ads_result = await session.execute(
                select(func.count(Ad.id)).where(Ad.status == 'rejected')
            )
            rejected_ads = rejected_ads_result.scalar()
            
            # Today's stats
            today = datetime.utcnow().date()
            
            today_ads_result = await session.execute(
                select(func.count(Ad.id)).where(func.date(Ad.created_at) == today)
            )
            today_ads = today_ads_result.scalar()
            
            today_users_result = await session.execute(
                select(func.count(User.id)).where(func.date(User.created_at) == today)
            )
            today_users = today_users_result.scalar()
            
            # Popular categories
            popular_categories_result = await session.execute(
                select(Ad.category, func.count(Ad.id).label('count'))
                .where(Ad.status == 'approved')
                .group_by(Ad.category)
                .order_by(desc('count'))
                .limit(5)
            )
            popular_categories = popular_categories_result.all()
            
            return {
                'total_users': total_users,
                'total_ads': total_ads,
                'pending_ads': pending_ads,
                'approved_ads': approved_ads,
                'rejected_ads': rejected_ads,
                'today_ads': today_ads,
                'today_users': today_users,
                'popular_categories': popular_categories
            }
    
    # Cleanup operations
    async def cleanup_old_ads(self):
        """Delete ads older than 7 days"""
        week_ago = datetime.utcnow() - timedelta(days=7)
        async with self.async_session() as session:
            result = await session.execute(
                select(Ad).where(Ad.expires_at < week_ago)
            )
            old_ads = result.scalars().all()
            
            for ad in old_ads:
                await session.delete(ad)
            
            await session.commit()
            return len(old_ads)
    
    # Settings operations
    async def get_setting(self, key: str) -> Optional[str]:
        """Get bot setting"""
        async with self.async_session() as session:
            result = await session.execute(
                select(BotSettings).where(BotSettings.key == key)
            )
            setting = result.scalar_one_or_none()
            return setting.value if setting else None
    
    async def set_setting(self, key: str, value: str):
        """Set bot setting"""
        async with self.async_session() as session:
            result = await session.execute(
                select(BotSettings).where(BotSettings.key == key)
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                setting.value = value
                setting.updated_at = datetime.utcnow()
            else:
                setting = BotSettings(key=key, value=value)
                session.add(setting)
            
            await session.commit()
    
    # Advanced queries
    async def search_ads(self, query: str, category: str = None, 
                        status: str = 'approved') -> List[Ad]:
        """Search ads by title or description"""
        async with self.async_session() as session:
            conditions = [
                Ad.status == status,
                Ad.title.ilike(f'%{query}%') | Ad.description.ilike(f'%{query}%')
            ]
            
            if category:
                conditions.append(Ad.category == category)
            
            result = await session.execute(
                select(Ad).where(*conditions).order_by(desc(Ad.created_at))
            )
            return result.scalars().all()
    
    async def get_ads_by_category(self, category: str, 
                                 status: str = 'approved') -> List[Ad]:
        """Get ads by category"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Ad).where(
                    Ad.category == category,
                    Ad.status == status
                ).order_by(desc(Ad.created_at))
            )
            return result.scalars().all()
    
    async def get_recent_ads(self, days: int = 7, 
                           status: str = 'approved') -> List[Ad]:
        """Get recent ads"""
        since_date = datetime.utcnow() - timedelta(days=days)
        async with self.async_session() as session:
            result = await session.execute(
                select(Ad).where(
                    Ad.created_at >= since_date,
                    Ad.status == status
                ).order_by(desc(Ad.created_at))
            )
            return result.scalars().all()
    
    async def get_user_stats(self, telegram_id: int) -> Dict[str, Any]:
        """Get user statistics"""
        async with self.async_session() as session:
            # User's total ads
            total_ads_result = await session.execute(
                select(func.count(Ad.id)).where(Ad.user_id == telegram_id)
            )
            total_ads = total_ads_result.scalar()
            
            # User's approved ads
            approved_ads_result = await session.execute(
                select(func.count(Ad.id)).where(
                    Ad.user_id == telegram_id,
                    Ad.status == 'approved'
                )
            )
            approved_ads = approved_ads_result.scalar()
            
            # User's pending ads
            pending_ads_result = await session.execute(
                select(func.count(Ad.id)).where(
                    Ad.user_id == telegram_id,
                    Ad.status == 'pending'
                )
            )
            pending_ads = pending_ads_result.scalar()
            
            # User's rejected ads
            rejected_ads_result = await session.execute(
                select(func.count(Ad.id)).where(
                    Ad.user_id == telegram_id,
                    Ad.status == 'rejected'
                )
            )
            rejected_ads = rejected_ads_result.scalar()
            
            return {
                'total_ads': total_ads,
                'approved_ads': approved_ads,
                'pending_ads': pending_ads,
                'rejected_ads': rejected_ads
            }
    
    async def close(self):
        """Close database connection"""
        await self.engine.dispose()