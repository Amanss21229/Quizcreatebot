import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class QuizLock:
    def __init__(self, chat_id: int, quiz_type: str):
        self.chat_id = chat_id
        self.quiz_type = quiz_type
        self.locked_at = datetime.now()
        
    def __repr__(self):
        return f"QuizLock(chat_id={self.chat_id}, type={self.quiz_type}, locked_at={self.locked_at})"


class QuizLockManager:
    def __init__(self):
        self.locks: Dict[int, QuizLock] = {}
        
    def acquire_lock(self, chat_id: int, quiz_type: str) -> bool:
        if chat_id in self.locks:
            logger.warning(f"Cannot acquire lock for chat {chat_id}: already locked by {self.locks[chat_id].quiz_type}")
            return False
        
        self.locks[chat_id] = QuizLock(chat_id, quiz_type)
        logger.info(f"Acquired quiz lock for chat {chat_id}, type={quiz_type}")
        return True
    
    def release_lock(self, chat_id: int):
        if chat_id in self.locks:
            quiz_type = self.locks[chat_id].quiz_type
            del self.locks[chat_id]
            logger.info(f"Released quiz lock for chat {chat_id}, was type={quiz_type}")
        else:
            logger.warning(f"Attempted to release non-existent lock for chat {chat_id}")
    
    def is_locked(self, chat_id: int) -> bool:
        return chat_id in self.locks
    
    def get_lock_info(self, chat_id: int) -> Optional[QuizLock]:
        return self.locks.get(chat_id)


quiz_lock_manager = QuizLockManager()
