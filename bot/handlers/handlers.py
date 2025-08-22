import logging
from aiogram import Router, types, F
from aiogram.enums import ChatAction
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.services.rag_pipeline import RAGPipeline
import urllib.parse

# Import UserState from commands
from bot.commands.commands import UserState

# Create routers for question handling
question_router = Router()
query_router = Router()

# In-memory storage for pagination (in production, use Redis or database)
user_pagination_data = {}


@question_router.message(F.text)
async def handle_user_question(message: types.Message, state: FSMContext, supabase_client):
    """Handle user questions with RAG pipeline"""
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение с вашим запросом.")
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
            question=message.text
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


# Handle regular text messages as questions
@question_router.message(F.text, ~StateFilter(UserState.help))
async def handle_regular_message(message: types.Message, state: FSMContext, supabase_client):
    """Handle regular text messages as questions"""
    # Set state and redirect to question handler
    await state.set_state(UserState.help)
    await handle_user_question(message, state, supabase_client)



'''
-------------------------------------------------------------------------------------------------------
from aiogram import types
from aiogram import F
from aiogram.enums import ChatAction
import tempfile
import os
import gc
from faster_whisper import WhisperModel
from configs.states import UserState
import platform

# Set OpenMP environment variables before any other imports
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

# Function to clear memory (OS-specific)
def clear_memory():
    gc.collect()
    if platform.system() == 'Darwin':  # macOS
        import subprocess
        subprocess.run(['purge'], capture_output=True)
    elif platform.system() == 'Linux':  # Linux
        import ctypes
        try:
            ctypes.CDLL('libc.so.6').malloc_trim(0)
        except:
            pass

# Initialize the model with more specific parameters
model = WhisperModel(
    model_size_or_path="tiny",
    device="cpu",
    compute_type="int8",
    download_root=os.path.expanduser("~/.cache/whisper")  # Use home directory
)


@dp.message(F.voice | F.audio)
async def handle_audio(message: types.Message) -> None:
    if model is None:
        await message.reply("Sorry, voice recognition is currently unavailable.")
        return

    temp_file = None
    await message.bot.send_chat_action(
            chat_id=message.from_user.id, 
            action=ChatAction.TYPING
    )

    # Get the file
    file_id = message.voice.file_id if message.voice else message.audio.file_id
    file = await message.bot.get_file(file_id)
        
    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
        await message.bot.download_file(file.file_path, temp_file.name)
            
        clear_memory()  # Clear memory before transcription
                
        # More conservative transcription settings
        segments, _ = model.transcribe(
                temp_file.name,
                language="ru",
                beam_size=1,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=1000,
                    speech_pad_ms=100
                ),
                condition_on_previous_text=False,
                no_speech_threshold=0.6    
        )
                
        # Combine all segments
        transcribed_text = " ".join([segment.text for segment in segments]).strip()
                
        clear_memory()  # Clear memory after transcription

        # Use the RAG chain to generate a response
        response, question, chunks = rag_query(transcribed_text)

        # Ensure response is a string
        if not isinstance(response, str):
            response = str(response)

        # Send the response back to the user
        await message.answer(response)
        db.insert_resquest(message.from_user.id, question, response,  chunks)

'''