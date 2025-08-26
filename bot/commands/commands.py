import logging
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from bot.messages import Messages
from bot.config import Config

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

@content_router.message(Command('videos'))
async def list_videos(message: types.Message):
    """Open webapp for videos"""
    try:
        # Create webapp button
        webapp_url = f"{Config.WEBAPP_URL}/videos"
        
        # Log the webapp URL
        print(f"🎥 Videos command: User {message.from_user.id} ({message.from_user.username}) requesting webapp URL: {webapp_url}")
        logging.info(f"Videos command: User {message.from_user.id} requesting webapp URL: {webapp_url}")
        
        webapp_button = InlineKeyboardButton(
            text="🎥 Открыть видео",
            web_app=WebAppInfo(url=webapp_url)
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[webapp_button]])
        
        await message.answer(
            "🎥 Нажмите кнопку ниже, чтобы открыть видео материалы:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Error in list_videos: {e}")
        await message.answer("Ошибка при загрузке видео.")

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
async def settings_command(message: types.Message):
    """Settings command handler"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Выбор формата ответа", callback_data="setting_response_format")],
        [InlineKeyboardButton(text="🔔 Настройка нотификаций", callback_data="setting_notifications")],
        [InlineKeyboardButton(text="📝 Прохождение квиза по темам эфира", callback_data="setting_quiz")]
    ])
    
    await message.answer(
        "⚙️ <b>Настройки</b>\n\nВыберите раздел для настройки:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@content_router.callback_query(lambda c: c.data == 'setting_response_format')
async def setting_response_format(callback_query: types.CallbackQuery):
    """Handle response format setting"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Текстовое сообщение", callback_data="format_text")],
        [InlineKeyboardButton(text="🎵 Аудио сообщение", callback_data="format_audio")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_settings")]
    ])
    
    await callback_query.message.edit_text(
        "💬 <b>Выбор формата ответа</b>\n\nВыберите предпочтительный формат для получения ответов:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@content_router.callback_query(lambda c: c.data == 'setting_notifications')
async def setting_notifications(callback_query: types.CallbackQuery):
    """Handle notifications setting"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔔 Включить уведомления", callback_data="notifications_on")],
        [InlineKeyboardButton(text="🔕 Отключить уведомления", callback_data="notifications_off")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_settings")]
    ])
    
    await callback_query.message.edit_text(
        "🔔 <b>Настройка нотификаций</b>\n\nНастройте получение уведомлений о новых материалах:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

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
async def back_to_settings(callback_query: types.CallbackQuery):
    """Go back to main settings menu"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Выбор формата ответа", callback_data="setting_response_format")],
        [InlineKeyboardButton(text="🔔 Настройка нотификаций", callback_data="setting_notifications")],
        [InlineKeyboardButton(text="📝 Прохождение квиза по темам эфира", callback_data="setting_quiz")]
    ])
    
    await callback_query.message.edit_text(
        "⚙️ <b>Настройки</b>\n\nВыберите раздел для настройки:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@content_router.callback_query(lambda c: c.data in ['format_text', 'format_audio'])
async def handle_format_selection(callback_query: types.CallbackQuery, supabase_client):
    """Handle response format selection"""
    format_type = "текстовом" if callback_query.data == 'format_text' else "аудио"
    
    try:
        # Here you would save the user preference to database
        # For now, just confirm the selection
        await callback_query.message.edit_text(
            f"✅ Формат ответов изменен на <b>{format_type}</b>\n\n"
            "Теперь ответы будут приходить в выбранном формате.",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error saving format preference: {e}")
        await callback_query.answer("Произошла ошибка при сохранении настроек")

@content_router.callback_query(lambda c: c.data in ['notifications_on', 'notifications_off'])
async def handle_notifications_selection(callback_query: types.CallbackQuery, supabase_client):
    """Handle notifications setting selection"""
    status = "включены" if callback_query.data == 'notifications_on' else "отключены"
    
    try:
        # Here you would save the notification preference to database
        # For now, just confirm the selection
        await callback_query.message.edit_text(
            f"✅ Уведомления <b>{status}</b>\n\n"
            "Настройка сохранена успешно.",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error saving notification preference: {e}")
        await callback_query.answer("Произошла ошибка при сохранении настроек")

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

@content_router.message(Command('materials'))
async def materials_command(message: types.Message):
    """Materials command - show content categories"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Web App", callback_data="materials_web_app")],
        [InlineKeyboardButton(text="🎥 Videos", callback_data="materials_videos")],
        [InlineKeyboardButton(text="📝 Texts", callback_data="materials_texts")],
        [InlineKeyboardButton(text="🎧 Podcasts", callback_data="materials_podcasts")]
    ])
    
    await message.answer(
        "📚 <b>Материалы</b>\n\n"
        "Выберите тип материалов для изучения:\n\n"
        "🌐 <b>Web App</b> - интерактивные материалы и приложения\n"
        "🎥 <b>Videos</b> - видеоуроки и записи\n" 
        "📝 <b>Texts</b> - статьи и текстовые материалы\n"
        "🎧 <b>Podcasts</b> - аудиоматериалы и подкасты",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

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