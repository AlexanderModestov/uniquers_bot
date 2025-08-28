import asyncio
import logging
import random
from datetime import datetime
from typing import List, Dict, Any
from aiogram import Bot
from bot.supabase_client.client import SupabaseClient

class NotificationService:
    def __init__(self, bot: Bot, supabase_client: SupabaseClient):
        self.bot = bot
        self.supabase_client = supabase_client
    
    # Warm and motivational messages in Russian
    MOTIVATIONAL_MESSAGES = [
        "🌅 Доброе утро! Новый день — новые возможности для роста и развития. Какую цель поставите себе сегодня?",
        "☀️ Привет! Помните: каждый маленький шаг к своей мечте приближает вас к успеху. Вы уже на правильном пути!",
        "🌸 Прекрасного дня! Сегодня отличная возможность узнать что-то новое и стать лучше, чем вчера.",
        "💫 Здравствуйте! Ваше желание развиваться вдохновляет. Какой навык хотите улучшить сегодня?",
        "🌺 Доброго времени суток! Помните: самые великие достижения начинаются с одного решения действовать.",
        "🦋 Привет! Вы уже делаете важный шаг, инвестируя в свое развитие. Продолжайте в том же духе!",
        "🌟 Замечательного дня! Каждый день — это шанс написать новую главу своей истории успеха.",
        "🌻 Доброе утро! Ваша настойчивость в обучении — это ключ к достижению всех ваших целей.",
        "✨ Прекрасного дня! Помните: знания — это инвестиция, которая всегда окупается с лихвой.",
        "🎯 Привет! Сегодня новая возможность стать экспертом в том, что вам действительно интересно.",
        "🌈 Доброго времени суток! Ваше стремление к росту — это то, что отличает вас от остальных.",
        "💎 Здравствуйте! Каждый урок, который вы изучаете, делает вас более ценным специалистом.",
        "🚀 Отличного дня! Ваши усилия в обучении сегодня — это ваш успех завтра.",
        "🌙 Доброго вечера! Даже вечером можно найти время для саморазвития. Вы молодец!",
        "⭐ Привет! Ваша целеустремленность в изучении нового материала достойна восхищения."
    ]
    
    EVENING_MESSAGES = [
        "🌅 Завтра новый день! Подготовьтесь к нему, изучив что-то полезное сегодня вечером.",
        "🌙 Доброго вечера! Время для спокойного изучения и подготовки к завтрашним достижениям.",
        "✨ Вечер — идеальное время для рефлексии и планирования следующих шагов в обучении.",
        "🌆 Прекрасного вечера! Завершите день чем-то полезным для вашего развития.",
        "🌟 Доброго вечера! Даже 15 минут обучения перед сном могут изменить ваше завтра."
    ]
    
    def get_motivational_message(self, hour: int) -> str:
        """Get appropriate motivational message based on time of day"""
        if 18 <= hour <= 23:  # Evening messages
            return random.choice(self.EVENING_MESSAGES)
        else:  # General motivational messages
            return random.choice(self.MOTIVATIONAL_MESSAGES)
    
    async def send_notification_to_user(self, telegram_id: int, message: str) -> bool:
        """Send notification to a specific user"""
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode="HTML"
            )
            logging.info(f"Notification sent to user {telegram_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to send notification to user {telegram_id}: {e}")
            return False
    
    async def send_scheduled_notifications(self) -> Dict[str, Any]:
        """Send notifications to all users who should receive them now"""
        try:
            current_time = datetime.now()
            current_hour = f"{current_time.hour:02d}:00"
            current_weekday = current_time.strftime('%A').lower()
            
            logging.info(f"Checking notifications for {current_hour} on {current_weekday}")
            
            # Get users who should receive notifications
            users_to_notify = await self.supabase_client.get_users_for_notification(
                current_hour, current_weekday
            )
            
            if not users_to_notify:
                logging.info("No users to notify at this time")
                return {
                    "status": "success",
                    "users_notified": 0,
                    "message": "No users scheduled for notifications"
                }
            
            # Send notifications
            successful_sends = 0
            failed_sends = 0
            
            for user in users_to_notify:
                telegram_id = user['telegram_id']
                username = user.get('username', 'Unknown')
                
                # Get appropriate message based on time
                motivational_message = self.get_motivational_message(current_time.hour)
                
                # Add personal touch if username available
                if username and username != 'Unknown':
                    personal_greeting = f"Привет, {username}! "
                    message = personal_greeting + motivational_message
                else:
                    message = motivational_message
                
                
                success = await self.send_notification_to_user(telegram_id, message)
                
                if success:
                    successful_sends += 1
                    logging.info(f"✅ Notification sent to {username} ({telegram_id})")
                else:
                    failed_sends += 1
                    logging.error(f"❌ Failed to send notification to {username} ({telegram_id})")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
            
            result = {
                "status": "completed",
                "users_notified": successful_sends,
                "failed_notifications": failed_sends,
                "total_users": len(users_to_notify),
                "time": current_hour,
                "weekday": current_weekday
            }
            
            logging.info(f"Notification batch completed: {successful_sends}/{len(users_to_notify)} successful")
            return result
            
        except Exception as e:
            logging.error(f"Error in send_scheduled_notifications: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_notification(self, telegram_id: int) -> bool:
        """Send a test notification to a specific user"""
        test_message = (
            "🧪 <b>Тестовое уведомление</b>\n\n"
            "Это тестовое сообщение для проверки системы уведомлений. "
            "Если вы получили это сообщение, значит уведомления работают корректно!"
        )
        
        return await self.send_notification_to_user(telegram_id, test_message)