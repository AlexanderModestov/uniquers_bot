from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class User(BaseModel):
    id: Optional[int] = None
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = 'en'
    settings: Dict[str, Any] = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None