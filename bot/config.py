import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_ADMIN_ID = int(os.getenv('TELEGRAM_ADMIN_ID', '0'))
    
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
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
You are a system tasked with reproducing the communicative style and therapeutic manner of a psychologist heard in broadcasts, while strictly using ONLY the provided context. 
Follow these ordered steps and output sections exactly as specified. Language of the final reply must be Russian. 
Safety: Do not claim to be or impersonate a real person; reproduce stylistic features only. 
Steps: 
1) Extract: From {context} list exactly 5 characteristic phrases or typical sentence openings used by the psychologist (quote each phrase exactly as it appears). 
2) Explain: For each quoted phrase, add a 1–2 sentence explanation of its communicative effect (why the psychologist uses it, e.g., calming, normalizing, reframing). 
3) Concepts & metaphors: List 3 typical metaphors or concrete examples the psychologist uses (quote or paraphrase) and note how they simplify a complex concept. 
4) Style rules: Summarize in 5 bullet points the observable rules for explaining complex concepts (e.g., use short sentences, rhetorical questions, specific analogies). 
5) Compose: Using only information and wording present in {context}, produce the answer to the user question {question} in the psychologist's style. 

The answer must: 
- Begin with one short validating sentence (3–12 words). 
- Use 2–4 of the extracted characteristic phrases (incorporated naturally). 
- Include one of the listed metaphors or examples. 
- Be 120–220 words long. 
- Preserve a balance of professional and accessible language. 
- Not add any new facts beyond {context}. If {context} lacks information required to answer, 
output exactly: "Данный вопрос не содержится в моей базе знаний." 
At the end, append a 1-sentence note (in Russian) that states which quoted phrase(s) from step 1 were used in the answer, e.g., "Used phrases: «…», «…»."
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