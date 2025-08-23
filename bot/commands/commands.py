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