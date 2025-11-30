from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import PromptTemplate
from bot.config import Config
from bot.supabase_client import SupabaseClient
from bot.services.llm_logger import LLMLogger, LLMRequestTimer
import logging

class RAGPipeline:
    def __init__(self, supabase_client: SupabaseClient):
        self.supabase_client = supabase_client
        self.llm_logger = LLMLogger(supabase_client)
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
    
    async def get_embeddings(self, text: str, user_id: Optional[int] = None) -> List[float]:
        """Generate embeddings for given text"""
        with LLMRequestTimer() as timer:
            try:
                embeddings = await self.embeddings.aembed_query(text)

                # Log the embedding request
                await self.llm_logger.log_embedding_request(
                    model=Config.EMBEDDING_MODEL,
                    input_text=text,
                    user_id=user_id,
                    tokens_total=len(text.split()),  # Rough estimate
                    latency_ms=timer.latency_ms,
                    success=True,
                    output_metadata={'embedding_dimensions': len(embeddings)}
                )

                return embeddings
            except Exception as e:
                # Log failed request
                await self.llm_logger.log_embedding_request(
                    model=Config.EMBEDDING_MODEL,
                    input_text=text,
                    user_id=user_id,
                    latency_ms=timer.latency_ms,
                    success=False,
                    error_message=str(e)
                )
                raise
    
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
        # Generate query embeddings
        query_embeddings = await self.get_embeddings(question, user_id=user_id)

        # Apply user filters
        search_limit = Config.SEARCH_LIMIT

        # Search in user's content
        search_results = await self.supabase_client.search_content(
            user_id=user_id,
            query_embedding=query_embeddings,
            limit=search_limit
        )

        # Prepare context for LLM
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

        # Generate answer using LLM
        prompt = self.prompt_template.format(context=context, question=question)

        with LLMRequestTimer() as timer:
            try:
                response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
                answer = response.content.strip()

                # Extract token usage if available
                tokens_prompt = None
                tokens_completion = None
                tokens_total = None

                if hasattr(response, 'response_metadata'):
                    usage = response.response_metadata.get('token_usage', {})
                    tokens_prompt = usage.get('prompt_tokens')
                    tokens_completion = usage.get('completion_tokens')
                    tokens_total = usage.get('total_tokens')

                # Log the chat request
                await self.llm_logger.log_chat_request(
                    model=Config.GPT_MODEL,
                    input_text=prompt,
                    output_text=answer,
                    user_id=user_id,
                    tokens_prompt=tokens_prompt,
                    tokens_completion=tokens_completion,
                    tokens_total=tokens_total,
                    latency_ms=timer.latency_ms,
                    success=True,
                    input_metadata={'question': question, 'context_chunks': len(search_results)},
                    output_metadata={'sources_count': len(sources)}
                )

            except Exception as e:
                # Log failed request
                await self.llm_logger.log_chat_request(
                    model=Config.GPT_MODEL,
                    input_text=prompt,
                    output_text=None,
                    user_id=user_id,
                    latency_ms=timer.latency_ms,
                    success=False,
                    error_message=str(e),
                    input_metadata={'question': question, 'context_chunks': len(search_results)}
                )
                raise

        result = {
            "answer": answer,
            "sources": sources,
            "context_used": len(search_results),
            "total_available": len(search_results)
        }
        return result
    
    
    async def save_query_to_history(self, user_id: int, question: str, answer: str, sources: List[Dict]) -> Optional[Dict]:
        """Save query and answer to history (disabled - no QueryHistory table)"""
        # Disabled since query_history table doesn't exist
        return None