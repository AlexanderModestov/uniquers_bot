"""
Configuration settings for the project.
"""

import os
from dotenv import load_dotenv
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from supabase import create_client, Client
from langchain_community.vectorstores import SupabaseVectorStore

# Load environment variables from .env file
load_dotenv(override=True)

# Telegram Bot settings
TOKEN = os.getenv("TOKEN")

# Set up vectorstore
BASE_DIR = Path(__file__).parent.parent

# Webapp settings
WEBAPP_BASE_URL = os.getenv("WEBAPP_BASE_URL")

# Database settings
DATABASE = os.getenv("DATABASE")
DB_USER = os.getenv("DB_USER")
PASSWORD = os.getenv("PASSWORD")
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
DB_SCHEMA = os.getenv("DB_SCHEMA")

# Subscription settings
DEFAULT_SUBSCRIPTION_DAYS = int(os.getenv("DEFAULT_SUBSCRIPTION_DAYS", "30"))
FREE_REQUESTS_LIMIT = int(os.getenv("FREE_REQUESTS_LIMIT", "10"))

# API settings
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
TEMPERATURE = os.getenv("TEMPERATURE")

# Supabase settings
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Models settings
MODEL_OPENAI = os.getenv("MODEL_OPENAI")
MODEL_OPENAI_EMBEDDINGS = os.getenv("MODEL_OPENAI_EMBEDDINGS")

# Other configuration settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

####################################################################
LANGSMITH_TRACING=os.getenv("LANGSMITH_TRACING")
LANGSMITH_ENDPOINT=os.getenv("LANGSMITH_ENDPOINT")
LANGSMITH_API_KEY=os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT=os.getenv("LANGSMITH_PROJECT")
LANGCHAIN_VERBOSE=os.getenv("LANGCHAIN_VERBOSE")

# Admin users
MANAGER = os.getenv("MANAGER")  # Replace with actual admin user ID(s)

# Initialize models and vectorstore
model = ChatOpenAI(temperature=TEMPERATURE, model=MODEL_OPENAI, openai_api_key=OPENAI_API_KEY)
embeddings = OpenAIEmbeddings(model=MODEL_OPENAI_EMBEDDINGS, openai_api_key=OPENAI_API_KEY)

# Set up Supabase client and vectorstore
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
vectorstore = SupabaseVectorStore(
    client=supabase,
    embedding=embeddings,
    table_name="documents",
    query_name="match_documents"
)
retriever = vectorstore.as_retriever()

# When creating the retriever:
#retriever = vectorstore.as_retriever(
#    search_type="similarity",
#    search_kwargs={"k": 4}
#)

# Define prompt template
prompt = ChatPromptTemplate.from_template("""
Вы - система, которая сохраняет уникальный стиль общения и подачу психолога из эфиров. 
Ваша задача - воспроизвести тот же терапевтический подход и манеру коммуникации при формировании ответов.

Анализ эфиров:
Выделите характерные речевые обороты и выражения психолога
Сохраните особенности объяснения сложных концепций
Отметьте типичные примеры и метафоры

Формирование ответа:
Используйте тот же тон и манеру речи
Сохраняйте баланс профессионального и доступного языка
Применяйте характерные для психолога обороты речи
Включайте его типичные примеры и аналогии.
                                          
Ответь на вопрос, используя только предоставленный ниже контекст.
Если в контексте нет информации для ответа, напиши: "Данный вопрос не содержится в моей базе знаний."

Контекст:
{context}

Вопрос: {question}
""")

