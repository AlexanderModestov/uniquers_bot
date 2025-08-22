from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from bot.config import Config
from bot.supabase_client import SupabaseClient
import logging
import json

class RAGPipeline:
    def __init__(self, supabase_client: SupabaseClient):
        self.supabase_client = supabase_client
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=Config.OPENAI_API_KEY,
            model="text-embedding-3-large"
        )
        self.llm = ChatOpenAI(
            openai_api_key=Config.OPENAI_API_KEY,
            model="gpt-4.1-mini",
            temperature=0.1
        )
        
        # Custom prompt template for RAG
        self.prompt_template = PromptTemplate(
            template=Config.RAG_PROMPT_TEMPLATE,
            input_variables=["context", "question"]
        )
    
    async def get_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for given text"""
        try:
            embeddings = await self.embeddings.aembed_query(text)
            return embeddings
        except Exception as e:
            logging.error(f"Error generating embeddings: {e}")
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
            query_embeddings = await self.get_embeddings(question)
            if not query_embeddings:
                return {
                    "answer": "Sorry, I couldn't process your question. Please try again.",
                    "sources": [],
                    "error": "embedding_failed"
                }
            
            # Apply user filters
            search_limit = 5
            if user_settings:
                search_limit = user_settings.get('search_results_limit', 5)
            
            # Search in user's content
            print(f"🤖 RAG Pipeline: Searching for content with limit={search_limit}")
            search_results = await self.supabase_client.search_content(
                user_id=user_id,
                query_embedding=query_embeddings,
                limit=search_limit
            )
            print(f"🤖 RAG Pipeline: Search returned {len(search_results)} results")
            
            if not search_results:
                return {
                    "answer": "I couldn't find relevant information in your content library to answer this question. Try uploading more documents or asking about different topics.",
                    "sources": [],
                    "error": "no_results"
                }
            
            # Apply content type filters if specified
            if user_settings and user_settings.get('content_filter'):
                content_filter = user_settings['content_filter']
                if content_filter == 'documents_only':
                    search_results = [r for r in search_results if r['type'] == 'document']
                elif content_filter == 'videos_only':
                    search_results = [r for r in search_results if r['type'] == 'video']
                elif content_filter == 'favorites_only':
                    search_results = [r for r in search_results if r.get('is_favorite')]
            
            # Prepare context for LLM
            context_parts = []
            sources = []
            
            for result in search_results:
                if result['type'] == 'document':
                    context_parts.append(f"Document '{result['title']}':\n{result['content_text'][:1000]}...")
                    sources.append({
                        'type': 'document',
                        'title': result['title'],
                        'similarity': result.get('similarity', 0),
                        'file_path': result.get('file_path')
                    })
                elif result['type'] == 'video':
                    context_parts.append(f"Video '{result['title']}':\n{result['transcript'][:1000]}...")
                    sources.append({
                        'type': 'video',
                        'title': result['title'],
                        'similarity': result.get('similarity', 0),
                        'video_url': result.get('video_url')
                    })
            
            context = "\n\n---\n\n".join(context_parts)
            
            # Generate answer using LLM
            prompt = self.prompt_template.format(context=context, question=question)
            
            try:
                response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
                answer = response.content.strip()
            except Exception as llm_error:
                logging.error(f"LLM generation error: {llm_error}")
                answer = "I found relevant information but couldn't generate a proper answer. Please try rephrasing your question."
            
            # Apply answer style based on user preferences
            if user_settings and user_settings.get('answer_style'):
                answer = await self._apply_answer_style(answer, user_settings['answer_style'])
            
            return {
                "answer": answer,
                "sources": sources,
                "context_used": len(search_results),
                "total_available": len(search_results)
            }
            
        except Exception as e:
            logging.error(f"Error in RAG pipeline: {e}")
            return {
                "answer": "An error occurred while processing your question. Please try again.",
                "sources": [],
                "error": str(e)
            }
    
    async def _apply_answer_style(self, answer: str, style: str) -> str:
        """Apply user-preferred answer style"""
        if style == "concise":
            style_prompt = f"Make this answer more concise and to-the-point:\n\n{answer}"
        elif style == "detailed":
            style_prompt = f"Expand this answer with more details and explanations:\n\n{answer}"
        elif style == "step-by-step":
            style_prompt = f"Reformat this answer as clear step-by-step instructions if applicable:\n\n{answer}"
        else:
            return answer
        
        try:
            response = await self.llm.ainvoke([{"role": "user", "content": style_prompt}])
            return response.content.strip()
        except Exception as e:
            logging.error(f"Error applying answer style: {e}")
            return answer
    
    async def save_query_to_history(self, user_id: int, question: str, answer: str, sources: List[Dict]) -> Optional[Dict]:
        """Save query and answer to history (disabled - no QueryHistory table)"""
        # Disabled since query_history table doesn't exist
        return None
    
    async def generate_embeddings_for_content(self, content: str, content_type: str = "document") -> List[float]:
        """Generate embeddings for document or video content"""
        try:
            # Prepare content for embedding (truncate if too long)
            max_length = 8000  # Leave room for tokenization
            if len(content) > max_length:
                content = content[:max_length] + "..."
            
            embeddings = await self.embeddings.aembed_query(content)
            return embeddings
        except Exception as e:
            logging.error(f"Error generating content embeddings: {e}")
            return []