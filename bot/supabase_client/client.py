import asyncio
from typing import List, Optional, Dict, Any
from supabase import create_client, Client
from .models import User

class SupabaseClient:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.client: Client = create_client(supabase_url, supabase_key)
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        try:
            response = self.client.table('users').select('*').eq('telegram_id', telegram_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    async def create_or_update_user(self, user_data: Dict[str, Any]) -> Optional[User]:
        try:
            existing_user = await self.get_user_by_telegram_id(user_data['telegram_id'])
            
            if existing_user:
                response = self.client.table('users').update(user_data).eq('telegram_id', user_data['telegram_id']).execute()
            else:
                response = self.client.table('users').insert(user_data).execute()
            
            if response.data:
                return User(**response.data[0])
            return None
        except Exception as e:
            print(f"Error creating/updating user: {e}")
            return None
    
    async def search_content(self, user_id: int, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        try:
            results = []
            
            # Try to search documents and videos, handle missing tables gracefully
            try:
                # Your documents table has: id, content, embedding, metadata, ingestion_date
                # No user_id column, so get all documents for now
                doc_response = self.client.table('documents').select('*').limit(limit).execute()
                if doc_response.data:
                    print(f"🔍 RAG Search: Found {len(doc_response.data)} documents in database")
                    # Map your schema to expected format
                    for doc in doc_response.data:
                        confidence = 0.8  # Fixed confidence level for now
                        metadata = doc.get('metadata', {})
                        # Try to get filename from metadata, fallback to other fields
                        filename = (metadata.get('filename') or 
                                  metadata.get('file_name') or 
                                  metadata.get('source') or 
                                  metadata.get('title') or 
                                  f'Document {doc.get("id", "")}')
                        print(f"📄 Document found: ID={doc.get('id')}, Filename='{filename}', Confidence={confidence}")
                        results.append({
                            'id': doc.get('id'),
                            'title': filename,  # Use filename as title for sources
                            'content_text': doc.get('content', ''),
                            'type': 'document',
                            'similarity': confidence,
                            'metadata': metadata
                        })
                else:
                    print("🔍 RAG Search: No documents found in database")
            except Exception as e:
                print(f"Error accessing documents table: {e}")
                pass
                
            try:
                video_response = self.client.table('video_contents').select('*').eq('user_id', user_id).limit(limit).execute()
                if video_response.data:
                    results.extend([{**video, 'type': 'video', 'similarity': 0.8} for video in video_response.data])
            except Exception:
                pass  # Video contents table doesn't exist or has wrong schema
            
            return results[:limit]
            
        except Exception as e:
            print(f"Error searching content: {e}")
            return []
    
    
    async def create_user(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None) -> Optional[User]:
        """Create user only if doesn't exist - for handlers compatibility"""
        # Check if user already exists
        existing_user = await self.get_user_by_telegram_id(telegram_id)
        if existing_user:
            return existing_user  # Don't update, just return existing user
            
        # Only create new user if doesn't exist
        user_data = {
            'telegram_id': telegram_id,
            'username': username
        }
        # Remove None values to avoid column errors
        user_data = {k: v for k, v in user_data.items() if v is not None}
        
        try:
            response = self.client.table('users').insert(user_data).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None