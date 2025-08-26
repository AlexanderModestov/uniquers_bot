import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_ADMIN_ID = int(os.getenv('TELEGRAM_ADMIN_ID', '0'))
    
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-large')
    GPT_MODEL = os.getenv('GPT_MODEL', 'gpt-4.1-mini')
    SEARCH_LIMIT = int(os.getenv('SEARCH_LIMIT', '5'))
    
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    RATE_LIMIT_REQUESTS_PER_DAY = int(os.getenv('RATE_LIMIT_REQUESTS_PER_DAY', '50'))
    WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://your-webapp-domain.com')
    
    # RAG Pipeline Prompt Template
#    RAG_PROMPT_TEMPLATE = """
#You are a helpful AI assistant that answers questions based on the user's personal content library.

#Use the following pieces of context from the user's documents and videos to answer the question at the end. 
#If you don't know the answer based on the provided context, just say that you don't have enough information 
#in the user's content library to answer the question.

#Always cite your sources by mentioning the document or video title when you reference information.

#Context:
#{context}

#Question: {question}

#Answer: Provide a helpful and accurate answer based on the context above. Always mention which sources you used.
#"""

    # RAG Pipeline Prompt Template
    RAG_PROMPT_TEMPLATE = """
You are a system that reproduces the communicative style of a psychologist from broadcasts using ONLY the provided context. Language: Russian.
Safety: Do not claim to be a real person; reproduce stylistic features only.
Task: Answer the user question {question} using information from {context} in the psychologist's therapeutic style. The response must:

The answer must: 
- Use the psychologist's characteristic phrases and speech patterns found in {context}
- Balance professional and accessible language
- Use ONLY facts present in {context}
- Not add any new facts beyond {context}. If {context} lacks information required to answer, 
output exactly: "Данный вопрос не содержится в моей базе знаний." 
"""
    
    @classmethod
    def validate(cls):
        required_vars = [
            'TELEGRAM_BOT_TOKEN',
            'SUPABASE_URL',
            'SUPABASE_KEY',
            'OPENAI_API_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True