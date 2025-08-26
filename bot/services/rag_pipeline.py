from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import PromptTemplate
from bot.config import Config
from bot.supabase_client import SupabaseClient
import logging

class RAGPipeline:
    def __init__(self, supabase_client: SupabaseClient):
        self.supabase_client = supabase_client
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=Config.OPENAI_API_KEY,
            model=Config.EMBEDDING_MODEL
        )
        self.llm = ChatOpenAI(
            openai_api_key=Config.OPENAI_API_KEY,
            model=Config.GPT_MODEL,
            temperature=0.1
        )
        
        # Custom prompt template for RAG
        self.prompt_template = PromptTemplate(
            template=Config.RAG_PROMPT_TEMPLATE,
            input_variables=["context", "question"]
        )
    
    async def get_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for given text"""
        logging.info(f"🔍 RAG Step 1: Query Embedding - Processing text (length: {len(text)} chars)")
        try:
            embeddings = await self.embeddings.aembed_query(text)
            logging.info(f"✅ RAG Step 1: Query Embedding - Successfully generated {len(embeddings)} dimension vector")
            return embeddings
        except Exception as e:
            logging.error(f"❌ RAG Step 1: Query Embedding - Error: {e}")
            return []
    
    async def search_and_answer(self, user_id: int, question: str, user_settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main RAG pipeline: search content and generate answer
        
        Args:
            user_id: User's database ID
            question: User's question
            user_settings: User preferences (answer style, filters, etc.)
            
        Returns:
            Dict with answer, sources, and metadata
        """
        try:
            # Generate query embeddings
            logging.info(f"🚀 RAG Pipeline: Starting for user_id={user_id}, question='{question[:100]}{'...' if len(question) > 100 else ''}'")
            query_embeddings = await self.get_embeddings(question)
            if not query_embeddings:
                logging.error(f"❌ RAG Pipeline: Failed at embedding step")
                return {
                    "answer": "Sorry, I couldn't process your question. Please try again.",
                    "sources": [],
                    "error": "embedding_failed"
                }
            
            # Apply user filters
            search_limit = Config.SEARCH_LIMIT
            
            # Search in user's content
            logging.info(f"🔎 RAG Step 2: Vector Search - Searching user content with limit={search_limit}")
            search_results = await self.supabase_client.search_content(
                user_id=user_id,
                query_embedding=query_embeddings,
                limit=search_limit
            )
            
            # Prepare context for LLM
            logging.info(f"📝 RAG Step 3: Context Preparation - Processing {len(search_results)} sources")
            context_parts = []
            sources = []
            
            for i, result in enumerate(search_results):
                context_parts.append(result['content_text'])
                sources.append({
                    'type': result.get('type'),
                    'title': result.get('title'),
                    'file_id': result.get('file_id')
                })
            
            context = "\n\n---\n\n".join(context_parts)
            logging.info(f"✅ RAG Step 3: Context Preparation - Created context with {len(context)} total chars")
            
            # Generate answer using LLM
            prompt = self.prompt_template.format(context=context, question=question)
            
            try:
                response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
                answer = response.content.strip()
                logging.info(f"✅ RAG Step 4: Answer Generation - Generated answer length: {len(answer)} chars")
            except Exception as llm_error:
                logging.error(f"❌ RAG Step 4: Answer Generation - LLM error: {llm_error}")
                answer = "I found relevant information but couldn't generate a proper answer. Please try rephrasing your question."
            
            
            logging.info(f"🎯 RAG Step 5: Response Formatting - Preparing final response with {len(sources)} sources")
            result = {
                "answer": answer,
                "sources": sources,
                "context_used": len(search_results),
                "total_available": len(search_results)
            }
            logging.info(f"✅ RAG Pipeline: Completed successfully for user_id={user_id}")
            return result
            
        except Exception as e:
            logging.error(f"Error in RAG pipeline: {e}")
            return {
                "answer": "An error occurred while processing your question. Please try again.",
                "sources": [],
                "error": str(e)
            }
    
    
    async def save_query_to_history(self, user_id: int, question: str, answer: str, sources: List[Dict]) -> Optional[Dict]:
        """Save query and answer to history (disabled - no QueryHistory table)"""
        # Disabled since query_history table doesn't exist
        return None
    
 #   async def generate_embeddings_for_content(self, content: str, content_type: str = "document") -> List[float]:
 #       """Generate embeddings for document or video content"""
 #       try:
 #           # Prepare content for embedding (truncate if too long)
 #           max_length = 8000  # Leave room for tokenization
 #           if len(content) > max_length:
 #               content = content[:max_length] + "..."
            
 #           embeddings = await self.embeddings.aembed_query(content)
 #           return embeddings
 #       except Exception as e:
 #           logging.error(f"Error generating content embeddings: {e}")
 #           return []