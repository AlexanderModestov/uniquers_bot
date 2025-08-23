import logging
import tempfile
import os
from aiogram import Router, types, F
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from bot.services.rag_pipeline import RAGPipeline
import openai

# Create routers for question handling
question_router = Router()
query_router = Router()

# In-memory storage for pagination (in production, use Redis or database)
user_pagination_data = {}

async def transcribe_voice_cloud(message: types.Message) -> str:
    """Transcribe voice message using OpenAI Whisper API"""
    # Get the file
    file_id = message.voice.file_id if message.voice else message.audio.file_id
    file = await message.bot.get_file(file_id)
    
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
            await message.bot.download_file(file.file_path, temp_file.name)
            
            # Use OpenAI Whisper API for transcription (v1.0+ syntax)
            client = openai.AsyncOpenAI()
            with open(temp_file.name, 'rb') as audio_file:
                transcript = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ru"
                )
            
            return transcript.text.strip()
            
    finally:
        # Clean up temp file
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


@question_router.message(F.text | F.voice | F.audio)
async def handle_user_question(message: types.Message, state: FSMContext, supabase_client):
    """Handle user questions with RAG pipeline"""
    # Extract text from message (text or voice)
    user_text = None
    
    if message.text:
        user_text = message.text
    elif message.voice or message.audio:
        # Show processing message for voice
        processing_voice_message = await message.answer("🎤 Распознаю голосовое сообщение...")
        
        try:
            user_text = await transcribe_voice_cloud(message)
            await processing_voice_message.delete()
            
            if not user_text or user_text.strip() == "":
                await message.answer("Не удалось распознать речь. Попробуйте еще раз или отправьте текстовое сообщение.")
                return
                
        except Exception as e:
            logging.error(f"Error transcribing voice: {e}")
            await processing_voice_message.edit_text("Ошибка при распознавании голосового сообщения. Попробуйте еще раз.")
            return
    else:
        await message.answer("Пожалуйста, отправьте текстовое или голосовое сообщение с вашим запросом.")
        return
    
    # Show processing message
    processing_message = await message.answer("🤔 Обрабатываю ваш вопрос...")

        # Send typing action
    await message.bot.send_chat_action(
        chat_id=message.from_user.id, 
        action=ChatAction.TYPING
    )
    
    try:
        # Initialize RAG pipeline
        rag = RAGPipeline(supabase_client)
        
        # Get user from database
        user = await supabase_client.get_user_by_telegram_id(message.from_user.id)
        if not user:
            await processing_message.edit_text("Ошибка: пользователь не найден. Попробуйте команду /start")
            return
        
        # Process question through RAG
        result = await rag.search_and_answer(
            user_id=user['id'],
            question=user_text
        )
        
        if result.get('error'):
            await processing_message.edit_text(
                f"Произошла ошибка: {result.get('error', 'Неизвестная ошибка')}"
            )
            return
        
        # Format response with sources
        response_text = result['answer']
        
        # Create webapp buttons for sources
        keyboard = None
        if result.get('sources'):
            from bot.config import Config
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
            
            response_text += "\n\n📚 Источники:"
            buttons = []
            
            for i, source in enumerate(result['sources'][:3], 1):  # Limit to 3 sources
                source_type = "📄" if source['type'] == 'document' else "🎥"
                source_id = source.get('id', '')
                title = source['title']
                
                # Add source to text
                response_text += f"\n{i}. {source_type} {title}"
                
                # Create webapp button for the source
                webapp_url = f"{Config.WEBAPP_URL}/document/{source_id}"
                button = InlineKeyboardButton(
                    text=f"{source_type} {title}",
                    web_app=WebAppInfo(url=webapp_url)
                )
                buttons.append([button])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Send response without markdown to avoid parsing errors
        try:
            await processing_message.edit_text(response_text, reply_markup=keyboard, parse_mode="Markdown")
        except Exception as markdown_error:
            # Fallback: send without markdown if parsing fails
            print(f"Markdown parsing failed, sending as plain text: {markdown_error}")
            await processing_message.edit_text(response_text, reply_markup=keyboard)
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        await processing_message.edit_text(
            "Произошла ошибка при обработке вашего вопроса. Попробуйте еще раз или обратитесь к администратору."
        )


