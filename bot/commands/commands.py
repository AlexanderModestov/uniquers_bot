import logging
import os
import json
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from bot.messages import Messages
from bot.config import Config
from bot.services.notification_scheduler import NotificationScheduler

# States for FSM
class UserState(StatesGroup):
    help = State()
    waiting_for_question = State()

# Create routers for commands
start_router = Router()
content_router = Router()

@start_router.message(CommandStart())
async def cmd_start(message: types.Message, supabase_client):
    """Start command handler"""
    user_name = message.from_user.first_name
    await message.answer(Messages.START_CMD["welcome"](user_name))
    
    try:
        # Register user in Supabase
        await supabase_client.create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
    except Exception as e:
        logging.warning(f"User registration error: {e}")

@start_router.message(Command("about"))
async def about(message: types.Message):
    """About command handler"""
    await message.answer(
        Messages.ABOUT_MESSAGE,
        parse_mode="Markdown"
    )

@content_router.message(Command('materials'))
async def list_materials(message: types.Message):
    """Open webapp with all materials and category buttons"""
    try:
        # Create inline keyboard with category buttons
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Все материалы", web_app=WebAppInfo(url=f"{Config.WEBAPP_URL}"))],
            [InlineKeyboardButton(text="🎥 Видео эфиры", web_app=WebAppInfo(url=f"{Config.WEBAPP_URL}/videos"))],
            #[InlineKeyboardButton(text="🎙️ Подкасты", web_app=WebAppInfo(url=f"{Config.WEBAPP_URL}/podcasts"))],
            [InlineKeyboardButton(text="📄 Статьи", web_app=WebAppInfo(url=f"{Config.WEBAPP_URL}/texts"))]
        ])
        
        # Log the webapp access
        print(f"📚 Materials command: User {message.from_user.id} ({message.from_user.username}) accessing materials webapp")
        logging.info(f"Materials command: User {message.from_user.id} accessing materials webapp")
        
        await message.answer(
            "📚 Здесь вы можете изучить все материалы. Выберите категорию:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Error in list_materials: {e}")
        await message.answer("Ошибка при загрузке материалов.")

@content_router.message(Command('quiz'))
async def quiz_command(message: types.Message):
    """Quiz command - show topic selection with pagination"""
    try:
        await show_quiz_topics(message, page=0)
    except Exception as e:
        logging.error(f"Error in quiz_command: {e}")
        await message.answer("Ошибка при загрузке квиза.")

async def show_quiz_topics(message: types.Message, page: int = 0, edit_message: bool = False):
    """Show quiz topics with pagination"""
    try:
        # Load topics from video_descriptions.json
        config_path = os.path.join(os.path.dirname(__file__), '..', 'configs', 'video_descriptions.json')
        if not os.path.exists(config_path):
            await message.answer("Ошибка: файл с темами не найден.")
            return
            
        with open(config_path, 'r', encoding='utf-8') as f:
            video_data = json.load(f)
        
        topics = video_data.get('videos', {})
        if not topics:
            await message.answer("Ошибка: темы не найдены.")
            return
        
        # Exclude "Жить или выживать: разбор" from quiz list
        filtered_topics = {k: v for k, v in topics.items() if v['name'] != "Жить или выживать: разбор"}
        topic_items = list(filtered_topics.items())
        topics_per_page = 5
        total_pages = (len(topic_items) + topics_per_page - 1) // topics_per_page
        
        # Ensure page is within bounds
        page = max(0, min(page, total_pages - 1))
        
        # Get topics for current page
        start_idx = page * topics_per_page
        end_idx = start_idx + topics_per_page
        current_topics = topic_items[start_idx:end_idx]
        
        # Create inline buttons for topics (one per row)
        buttons = []
        for topic_key, topic_info in current_topics:
            button = InlineKeyboardButton(
                text=f"📝 {topic_info['name']}",
                web_app=WebAppInfo(url=f"{Config.WEBAPP_URL}/api/quiz-html/{topic_info['file_id']}")
            )
            buttons.append([button])
        
        # Add navigation buttons if needed
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"quiz_page_{page-1}"
            ))
        
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(
                text="Далее ➡️",
                callback_data=f"quiz_page_{page+1}"
            ))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Log quiz access
        if not edit_message:
            print(f"📝 Quiz command: User {message.from_user.id} ({message.from_user.username}) accessing quiz topics")
            logging.info(f"Quiz command: User {message.from_user.id} accessing quiz topics")
        
        text = (
            f"📝 *Выберите тему для квиза:*\n\n"
            f"Пройдите тест по одной из психологических тем эфиров\n\n"
            f"Страница {page + 1} из {total_pages}"
        )
        
        if edit_message:
            await message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
    except Exception as e:
        logging.error(f"Error in show_quiz_topics: {e}")
        if edit_message:
            await message.edit_text("Ошибка при загрузке квиза.")
        else:
            await message.answer("Ошибка при загрузке квиза.")

@content_router.message(Command('booking'))
async def schedule_command(message: types.Message):
    """Handle booking command"""
    # Create available dates for next 7 days
    dates = [(datetime.now() + timedelta(days=x)).strftime("%Y-%m-%d") for x in range(1, 8)]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📅 {date}", callback_data=f"date_{date}")] 
        for date in dates
    ])
    
    await message.answer("Выберите дату сессии:", reply_markup=keyboard)

@content_router.callback_query(lambda c: c.data.startswith('date_'))
async def process_date_selection(callback_query: types.CallbackQuery):
    """Handle date selection for booking"""
    selected_date = callback_query.data.replace('date_', '')
    time_slots = ["10:00", "14:00", "16:00"]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🕐 {slot}", callback_data=f"slot_{selected_date}_{slot}")] 
        for slot in time_slots
    ])
    
    await callback_query.message.edit_text(
        f"Дата: {selected_date}\nВыберите удобное время:",
        reply_markup=keyboard
    )

@content_router.callback_query(lambda c: c.data.startswith('slot_'))
async def process_slot_selection(callback_query: types.CallbackQuery, supabase_client):
    """Handle time slot selection for booking"""
    try:
        _, date, time = callback_query.data.split('_', 2)
        
        user = await supabase_client.get_user_by_telegram_id(callback_query.from_user.id)
        if user:
            # Here you would save the booking to your database
            # For now, just confirm the booking
            await callback_query.message.edit_text(
                f"✅ Ваша сессия на {date} в {time} подтверждена!\n\n"
                "В назначенное время мы Вас ждем."
            )
        else:
            await callback_query.message.edit_text("Ошибка: пользователь не найден.")
            
    except Exception as e:
        logging.error(f"Error processing slot selection: {e}")
        await callback_query.message.edit_text("Произошла ошибка при бронировании.")

@content_router.message(Command('subscribe'))
async def subscribe_command(message: types.Message):
    """Handle subscription command"""
    await message.answer(
        "⚙️ Функционал подписки в разработке и скоро будет доступен!\n\n"
        "В будущем оформив подписку, Вы получите безлимитный доступ к материалам.", 
        parse_mode="HTML"
    )

@content_router.message(Command('settings'))
async def settings_command(message: types.Message, supabase_client):
    """Settings command handler"""
    try:
        # Get current user settings from database
        user = await supabase_client.get_user_by_telegram_id(message.from_user.id)
        
        if user:
            audio_status = "🔊 Аудио" if user.isAudio else "📝 Текст"
            notif_status = "🔔 Включены" if user.notification else "🔕 Отключены"
            
            # Dynamic buttons based on current settings
            if user.isAudio:
                format_button_text = "📝 Выбрать текстовые ответы"
                format_callback = "format_text"
            else:
                format_button_text = "🎧 Выбрать аудиоответы"
                format_callback = "format_audio"
            
            if user.notification:
                notif_button_text = "🔕 Отключить уведомления"
                notif_callback = "notifications_off"
            else:
                notif_button_text = "🔔 Включить уведомления"
                notif_callback = "notifications_on"
        else:
            audio_status = "📝 Текст"
            notif_status = "🔕 Отключены"
            format_button_text = "🎧 Выбрать аудиоответы"
            format_callback = "format_audio"
            notif_button_text = "🔔 Включить уведомления"
            notif_callback = "notifications_on"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=format_button_text, callback_data=format_callback)],
            [InlineKeyboardButton(text=notif_button_text, callback_data=notif_callback)]
        ])
        
        settings_text = (
            "⚙️ <b>Настройки</b>\n\n"
            "<b>Текущие настройки:</b>\n"
            f"💬 Формат ответов: {audio_status}\n"
            f"🔔 Уведомления: {notif_status}\n\n"
            "Выберите действие:"
        )
        
        await message.answer(
            settings_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error in settings command: {e}")
        await message.answer("Произошла ошибка при загрузке настроек")



@content_router.callback_query(lambda c: c.data == 'setting_quiz')
async def setting_quiz(callback_query: types.CallbackQuery):
    """Handle quiz setting"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Начать квиз", callback_data="start_quiz")],
        [InlineKeyboardButton(text="📊 Мои результаты", callback_data="quiz_results")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_settings")]
    ])
    
    await callback_query.message.edit_text(
        "📝 <b>Прохождение квиза по темам эфира</b>\n\nПроверьте свои знания по темам эфира:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@content_router.callback_query(lambda c: c.data == 'back_to_settings')
async def back_to_settings(callback_query: types.CallbackQuery, supabase_client):
    """Go back to main settings menu"""
    try:
        # Get current user settings from database
        user = await supabase_client.get_user_by_telegram_id(callback_query.from_user.id)
        
        if user:
            audio_status = "🔊 Аудио" if user.isAudio else "📝 Текст"
            notif_status = "🔔 Включены" if user.notification else "🔕 Отключены"
            
            # Dynamic buttons based on current settings
            if user.isAudio:
                format_button_text = "📝 Выбрать текстовые ответы"
                format_callback = "format_text"
            else:
                format_button_text = "🎧 Выбрать аудиоответы"
                format_callback = "format_audio"
            
            if user.notification:
                notif_button_text = "🔕 Отключить уведомления"
                notif_callback = "notifications_off"
            else:
                notif_button_text = "🔔 Включить уведомления"
                notif_callback = "notifications_on"
        else:
            audio_status = "📝 Текст"
            notif_status = "🔕 Отключены"
            format_button_text = "🎧 Выбрать аудиоответы"
            format_callback = "format_audio"
            notif_button_text = "🔔 Включить уведомления"
            notif_callback = "notifications_on"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=format_button_text, callback_data=format_callback)],
            [InlineKeyboardButton(text=notif_button_text, callback_data=notif_callback)]
        ])
        
        settings_text = (
            "⚙️ <b>Настройки</b>\n\n"
            "<b>Текущие настройки:</b>\n"
            f"💬 Формат ответов: {audio_status}\n"
            f"🔔 Уведомления: {notif_status}\n\n"
            "Выберите действие:"
        )
        
        try:
            await callback_query.message.edit_text(
                settings_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as edit_error:
            # Handle case when message content is the same (Telegram error)
            if "message is not modified" in str(edit_error):
                # Message content is identical, just acknowledge the callback
                pass
            else:
                # Re-raise other errors
                raise edit_error
    except Exception as e:
        logging.error(f"Error in back_to_settings: {e}")
        await callback_query.answer("Произошла ошибка при загрузке настроек")

@content_router.callback_query(lambda c: c.data in ['format_text', 'format_audio'])
async def handle_format_selection(callback_query: types.CallbackQuery, supabase_client):
    """Handle response format selection"""
    is_audio = callback_query.data == 'format_audio'
    format_type = "аудио" if is_audio else "текстовом"
    
    try:
        # Save user preference to database
        user_data = {
            'telegram_id': callback_query.from_user.id,
            'isAudio': is_audio
        }
        
        await supabase_client.create_or_update_user(user_data)
        
        # Show brief confirmation and redirect back to settings
        await callback_query.answer(f"✅ Формат изменен на {format_type}")
        
        # Redirect back to settings menu
        await back_to_settings(callback_query, supabase_client)
    except Exception as e:
        logging.error(f"Error saving format preference: {e}")
        await callback_query.answer("Произошла ошибка при сохранении настроек")

@content_router.callback_query(lambda c: c.data in ['notifications_on', 'notifications_off'])
async def handle_notifications_selection(callback_query: types.CallbackQuery, supabase_client):
    """Handle notifications setting selection"""
    notifications_enabled = callback_query.data == 'notifications_on'
    
    try:
        if notifications_enabled:
            # Show notification frequency options when enabling notifications
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📅 Каждый день", callback_data="notif_freq_daily")],
                [InlineKeyboardButton(text="💼 Только рабочие дни", callback_data="notif_freq_weekdays")],
                [InlineKeyboardButton(text="🏖️ Только выходные", callback_data="notif_freq_weekends")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_settings")]
            ])
            
            await callback_query.message.edit_text(
                "🔔 <b>Настройка уведомлений</b>\n\n"
                "Выберите частоту получения уведомлений:",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            # Disable notifications completely
            user_data = {
                'telegram_id': callback_query.from_user.id,
                'notification': False
            }
            
            await supabase_client.create_or_update_user(user_data)
            
            # Clear notification settings
            user = await supabase_client.get_user_by_telegram_id(callback_query.from_user.id)
            if user:
                await supabase_client.create_or_update_notification_settings(user.id, {})
            
            await callback_query.answer("✅ Уведомления отключены")
            await back_to_settings(callback_query, supabase_client)
            
    except Exception as e:
        logging.error(f"Error saving notification preference: {e}")
        await callback_query.answer("Произошла ошибка при сохранении настроек")

@content_router.callback_query(lambda c: c.data.startswith('notif_freq_'))
async def handle_notification_frequency_selection(callback_query: types.CallbackQuery, supabase_client):
    """Handle notification frequency selection"""
    try:
        user = await supabase_client.get_user_by_telegram_id(callback_query.from_user.id)
        if not user:
            await callback_query.answer("Ошибка: пользователь не найден")
            return
            
        # Enable notifications in user table
        user_data = {
            'telegram_id': callback_query.from_user.id,
            'notification': True
        }
        await supabase_client.create_or_update_user(user_data)
        
        # Parse selected frequency
        frequency_map = {
            'notif_freq_daily': ('daily', 'каждый день'),
            'notif_freq_weekdays': ('weekdays', 'только рабочие дни'),
            'notif_freq_weekends': ('weekends', 'только выходные')
        }
        
        if callback_query.data in frequency_map:
            frequency_key, frequency_name = frequency_map[callback_query.data]
            
            # Show time selection with all 24 hours - first page (00-11)
            await show_time_selection(callback_query, frequency_key, frequency_name, page=0)
        else:
            await callback_query.answer("❌ Неизвестная частота уведомлений")
        
    except Exception as e:
        logging.error(f"Error saving notification frequency: {e}")
        await callback_query.answer("Произошла ошибка при сохранении настроек")

async def show_time_selection(callback_query: types.CallbackQuery, frequency_key: str, frequency_name: str, page: int = 0):
    """Show time selection with pagination (12 hours per page)"""
    try:
        hours_per_page = 12
        total_pages = 2  # 0-11 and 12-23
        
        # Ensure page is within bounds
        page = max(0, min(page, total_pages - 1))
        
        # Get hours for current page
        start_hour = page * hours_per_page
        end_hour = start_hour + hours_per_page
        
        # Create time buttons (3 per row)
        buttons = []
        current_row = []
        
        for hour in range(start_hour, end_hour):
            hour_text = f"{hour:02d}:00"
            button = InlineKeyboardButton(
                text=hour_text,
                callback_data=f"notif_time_{frequency_key}_{hour:02d}:00"
            )
            current_row.append(button)
            
            # Add 3 buttons per row
            if len(current_row) == 3:
                buttons.append(current_row)
                current_row = []
        
        # Add remaining buttons if any
        if current_row:
            buttons.append(current_row)
        
        # Add navigation buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="⬅️ Предыдущие",
                callback_data=f"time_page_{frequency_key}_{frequency_name}_{page-1}"
            ))
        
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(
                text="Следующие ➡️",
                callback_data=f"time_page_{frequency_key}_{frequency_name}_{page+1}"
            ))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        # Add back button
        buttons.append([InlineKeyboardButton(text="⬅️ Назад к частоте", callback_data="notifications_on")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        page_info = f"({start_hour:02d}:00 - {end_hour-1:02d}:00)" if end_hour <= 24 else f"({start_hour:02d}:00 - 23:00)"
        
        await callback_query.message.edit_text(
            f"🕐 <b>Выбор времени уведомлений</b>\n\n"
            f"Частота: {frequency_name}\n"
            f"Выберите час {page_info}:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logging.error(f"Error in show_time_selection: {e}")
        await callback_query.message.edit_text("Ошибка при отображении времени")

@content_router.callback_query(lambda c: c.data.startswith('time_page_'))
async def handle_time_page_navigation(callback_query: types.CallbackQuery):
    """Handle time selection pagination"""
    try:
        # Parse callback data: time_page_{frequency_key}_{frequency_name}_{page}
        parts = callback_query.data.split('_', 4)
        if len(parts) >= 5:
            frequency_key = parts[2]
            frequency_name = parts[3]
            page = int(parts[4])
            
            await show_time_selection(callback_query, frequency_key, frequency_name, page)
            await callback_query.answer()
        
    except Exception as e:
        logging.error(f"Error in time page navigation: {e}")
        await callback_query.answer("Ошибка при навигации")

@content_router.callback_query(lambda c: c.data.startswith('notif_time_'))
async def handle_notification_time_selection(callback_query: types.CallbackQuery, supabase_client):
    """Handle final notification time selection"""
    try:
        # Parse callback data: notif_time_{frequency}_{time}
        parts = callback_query.data.split('_', 3)
        if len(parts) >= 4:
            frequency = parts[2]
            time = parts[3]
            
            user = await supabase_client.get_user_by_telegram_id(callback_query.from_user.id)
            if not user:
                await callback_query.answer("Ошибка: пользователь не найден")
                return
            
            # Save complete notification settings
            notification_settings = {
                'frequency': frequency,
                'time': time
            }
            
            await supabase_client.create_or_update_notification_settings(user.id, notification_settings)
            
            # Show confirmation
            frequency_names = {
                'daily': 'каждый день',
                'weekdays': 'рабочие дни',
                'weekends': 'выходные'
            }
            frequency_name = frequency_names.get(frequency, frequency)
            
            await callback_query.answer(f"✅ Уведомления настроены: {frequency_name} в {time}")
            await back_to_settings(callback_query, supabase_client)
        
    except Exception as e:
        logging.error(f"Error saving notification time: {e}")
        await callback_query.answer("Произошла ошибка при сохранении времени")

@content_router.callback_query(lambda c: c.data.startswith('quiz_page_'))
async def handle_quiz_pagination(callback_query: types.CallbackQuery):
    """Handle quiz pagination"""
    try:
        # Extract page number from callback data
        page = int(callback_query.data.replace('quiz_page_', ''))
        
        # Show quiz topics for the requested page
        await show_quiz_topics(callback_query.message, page=page, edit_message=True)
        
        # Answer callback query
        await callback_query.answer()
        
    except Exception as e:
        logging.error(f"Error in handle_quiz_pagination: {e}")
        await callback_query.answer("Ошибка при навигации по страницам")

@content_router.callback_query(lambda c: c.data in ['start_quiz', 'quiz_results'])
async def handle_quiz_actions(callback_query: types.CallbackQuery):
    """Handle quiz actions"""
    if callback_query.data == 'start_quiz':
        await callback_query.message.edit_text(
            "🎯 <b>Квиз в разработке</b>\n\n"
            "Функционал квиза по темам эфира скоро будет доступен!\n"
            "Следите за обновлениями.",
            parse_mode="HTML"
        )
    else:  # quiz_results
        await callback_query.message.edit_text(
            "📊 <b>Результаты квиза</b>\n\n"
            "У вас пока нет результатов квизов.\n"
            "Пройдите квиз, чтобы увидеть свои достижения!",
            parse_mode="HTML"
        )

@content_router.callback_query(lambda c: c.data == 'materials_web_app')
async def handle_materials_web_app(callback_query: types.CallbackQuery):
    """Handle web app materials selection"""
    try:
        webapp_url = f"{Config.WEBAPP_URL}"
        webapp_button = InlineKeyboardButton(
            text="🌐 Открыть Web App",
            web_app=WebAppInfo(url=webapp_url)
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[webapp_button]])
        
        await callback_query.message.edit_text(
            "🌐 <b>Web App</b>\n\n"
            "Интерактивные материалы и приложения для обучения.\n"
            "Нажмите кнопку ниже для доступа к веб-приложению:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error in materials_web_app: {e}")
        await callback_query.answer("Ошибка при загрузке веб-приложения")

@content_router.callback_query(lambda c: c.data == 'materials_videos')
async def handle_materials_videos(callback_query: types.CallbackQuery):
    """Handle videos materials selection"""
    try:
        webapp_url = f"{Config.WEBAPP_URL}/videos"
        webapp_button = InlineKeyboardButton(
            text="🎥 Открыть видео",
            web_app=WebAppInfo(url=webapp_url)
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[webapp_button]])
        
        await callback_query.message.edit_text(
            "🎥 <b>Videos</b>\n\n"
            "Видеоуроки, записи лекций и обучающие материалы.\n"
            "Нажмите кнопку ниже для просмотра видеоматериалов:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error in materials_videos: {e}")
        await callback_query.answer("Ошибка при загрузке видео")

@content_router.callback_query(lambda c: c.data == 'materials_texts')
async def handle_materials_texts(callback_query: types.CallbackQuery):
    """Handle texts materials selection"""
    try:
        webapp_url = f"{Config.WEBAPP_URL}/texts"
        webapp_button = InlineKeyboardButton(
            text="📝 Открыть тексты",
            web_app=WebAppInfo(url=webapp_url)
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[webapp_button]])
        
        await callback_query.message.edit_text(
            "📝 <b>Texts</b>\n\n"
            "Статьи, конспекты, учебные материалы и документация.\n"
            "Нажмите кнопку ниже для доступа к текстовым материалам:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error in materials_texts: {e}")
        await callback_query.answer("Ошибка при загрузке текстов")

@content_router.callback_query(lambda c: c.data == 'materials_podcasts')
async def handle_materials_podcasts(callback_query: types.CallbackQuery):
    """Handle podcasts materials selection"""
    try:
        webapp_url = f"{Config.WEBAPP_URL}/podcasts"
        webapp_button = InlineKeyboardButton(
            text="🎧 Открыть подкасты",
            web_app=WebAppInfo(url=webapp_url)
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[webapp_button]])
        
        await callback_query.message.edit_text(
            "🎧 <b>Podcasts</b>\n\n"
            "Аудиоматериалы, подкасты и записи обсуждений.\n"
            "Нажмите кнопку ниже для прослушивания подкастов:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error in materials_podcasts: {e}")
        await callback_query.answer("Ошибка при загрузке подкастов")


@content_router.message(Command('help'))
async def command_request(message: types.Message, state: FSMContext) -> None:
    """Help command - initiate question asking"""
    await message.answer("Пожалуйста, напиши Ваш вопрос в свободной форме и <b>одним сообщением</b>!", parse_mode="HTML")
    await state.set_state(UserState.help)

# Request help - send to admin
@content_router.message(UserState.help)
async def help(message: types.Message, state: FSMContext):
    """Send message to admin"""
    user_mention = f"[{message.from_user.full_name}](tg://user?id={message.from_user.id})"
    await message.answer("Ваше сообщение принято. Ожидайте ответа в течении суток. Спасибо, что вы с нами.")
    await state.clear()
    
    # Send to admin if admin ID is configured
    if Config.TELEGRAM_ADMIN_ID and Config.TELEGRAM_ADMIN_ID != 0:
        try:
            await message.bot.send_message(
                chat_id=Config.TELEGRAM_ADMIN_ID,
                text=f"Пользователь {user_mention} спрашивает:\n\n{message.text}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Error sending message to admin: {e}")

@content_router.message(Command('test_notification'))
async def test_notification_command(message: types.Message, supabase_client):
    """Test notification command - for admin use"""
    try:
        scheduler = NotificationScheduler(message.bot, supabase_client)
        success = await scheduler.send_test_notification(message.from_user.id)
        
        if success:
            await message.answer("✅ Тестовое уведомление отправлено!")
        else:
            await message.answer("❌ Ошибка при отправке тестового уведомления")
            
    except Exception as e:
        logging.error(f"Error in test notification: {e}")
        await message.answer("❌ Произошла ошибка")

@content_router.message(Command('send_notifications'))
async def manual_send_notifications_command(message: types.Message, supabase_client):
    """Manual notification sending command - for admin use"""
    try:
        scheduler = NotificationScheduler(message.bot, supabase_client)
        result = await scheduler.send_notifications_now()
        
        if result['status'] == 'completed':
            await message.answer(
                f"✅ Уведомления отправлены!\n\n"
                f"📊 Статистика:\n"
                f"• Успешно: {result['users_notified']}\n"
                f"• Ошибки: {result['failed_notifications']}\n"
                f"• Всего пользователей: {result['total_users']}\n"
                f"• Время: {result['time']}\n"
                f"• День недели: {result['weekday']}"
            )
        elif result['status'] == 'success':
            await message.answer(f"ℹ️ {result['message']}")
        else:
            await message.answer(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
            
    except Exception as e:
        logging.error(f"Error in manual send notifications: {e}")
        await message.answer("❌ Произошла ошибка при отправке уведомлений")

@content_router.message(Command('notification_status'))
async def notification_status_command(message: types.Message, supabase_client):
    """Check notification system status - for admin use"""
    try:
        scheduler = NotificationScheduler(message.bot, supabase_client)
        status = await scheduler.get_notification_status()
        
        if 'error' in status:
            await message.answer(f"❌ Ошибка: {status['error']}")
        else:
            await message.answer(
                f"📊 <b>Статус системы уведомлений</b>\n\n"
                f"🕐 Текущее время: {status['current_time']}\n"
                f"📅 День недели: {status['current_weekday']}\n"
                f"👥 Пользователей с уведомлениями: {status['total_users_with_notifications']}\n"
                f"⏰ Запланировано сейчас: {status['users_scheduled_now']}\n"
                f"🔄 Планировщик работает: {'Да' if status['scheduler_running'] else 'Нет'}",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logging.error(f"Error in notification status: {e}")
        await message.answer("❌ Произошла ошибка при получении статуса")