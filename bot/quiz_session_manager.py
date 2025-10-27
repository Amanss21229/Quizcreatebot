import asyncio
import time
from typing import Dict, List, Optional
from datetime import datetime
import logging
from bot.config import NEET_CORRECT_MARKS, NEET_WRONG_MARKS, NEET_UNATTEMPTED_MARKS

logger = logging.getLogger(__name__)


class QuizSession:
    def __init__(self, chat_id: int, chapter: str, questions: List[Dict], is_private_chat: bool = False, time_per_question: int = 45):
        self.chat_id = chat_id
        self.chapter = chapter
        self.questions = questions
        self.current_question_index = 0
        self.participants = {}
        self.start_time = time.time()
        self.question_start_time = None
        self.current_poll_id = None
        self.is_active = True
        self.is_private_chat = is_private_chat
        self.auto_advance_task = None
        self.time_per_question = time_per_question
        
    def start_question(self, poll_id: str):
        self.question_start_time = time.time()
        self.current_poll_id = poll_id
        
    def record_answer(self, user_id: int, user_name: str, option_id: int, time_taken: float):
        if user_id not in self.participants:
            self.participants[user_id] = {
                'user_id': user_id,
                'user_name': user_name,
                'total_score': 0,
                'correct_answers': 0,
                'wrong_answers': 0,
                'unattempted': 0,
                'total_time': 0.0,
                'answers': {}
            }
        
        question_index = self.current_question_index
        correct_answer = self.questions[question_index]['correct_answer']
        is_correct = (option_id == correct_answer)
        
        participant = self.participants[user_id]
        
        if question_index in participant['answers']:
            old_answer = participant['answers'][question_index]
            
            if old_answer['is_correct']:
                participant['correct_answers'] -= 1
                participant['total_score'] -= NEET_CORRECT_MARKS
            else:
                participant['wrong_answers'] -= 1
                participant['total_score'] -= NEET_WRONG_MARKS
            
            participant['total_time'] -= old_answer['time_taken']
        
        participant['answers'][question_index] = {
            'option_id': option_id,
            'is_correct': is_correct,
            'time_taken': time_taken
        }
        
        if is_correct:
            participant['correct_answers'] += 1
            participant['total_score'] += NEET_CORRECT_MARKS
        else:
            participant['wrong_answers'] += 1
            participant['total_score'] += NEET_WRONG_MARKS
        
        participant['total_time'] += time_taken
        
    def mark_unattempted(self):
        question_index = self.current_question_index
        for user_id, data in self.participants.items():
            if question_index not in data['answers']:
                data['unattempted'] += 1
                data['answers'][question_index] = {
                    'option_id': None,
                    'is_correct': False,
                    'time_taken': 0
                }
    
    def next_question(self):
        self.mark_unattempted()
        self.current_question_index += 1
        self.current_poll_id = None
        self.question_start_time = None
        return self.current_question_index < len(self.questions)
    
    def get_current_question(self):
        if self.current_question_index < len(self.questions):
            return self.questions[self.current_question_index]
        return None
    
    def is_finished(self):
        return self.current_question_index >= len(self.questions)
    
    def get_leaderboard_data(self):
        self.mark_unattempted()
        
        leaderboard = []
        for user_id, data in self.participants.items():
            leaderboard.append({
                'user_id': data['user_id'],
                'user_name': data['user_name'],
                'total_score': data['total_score'],
                'total_attempted': data['correct_answers'] + data['wrong_answers'],
                'correct_answers': data['correct_answers'],
                'wrong_answers': data['wrong_answers'],
                'unattempted': data['unattempted'],
                'total_time': data['total_time'],
                'accuracy': (data['correct_answers'] / (data['correct_answers'] + data['wrong_answers']) * 100) if (data['correct_answers'] + data['wrong_answers']) > 0 else 0
            })
        
        leaderboard.sort(key=lambda x: (x['total_score'], -x['total_time']), reverse=True)
        
        for rank, participant in enumerate(leaderboard, 1):
            participant['rank'] = rank
        
        return leaderboard


class QuizSessionManager:
    def __init__(self):
        self.active_sessions: Dict[int, QuizSession] = {}
        
    def create_session(self, chat_id: int, chapter: str, questions: List[Dict], is_private_chat: bool = False, time_per_question: int = 45) -> QuizSession:
        if chat_id in self.active_sessions:
            self.active_sessions[chat_id].is_active = False
        
        session = QuizSession(chat_id, chapter, questions, is_private_chat, time_per_question)
        self.active_sessions[chat_id] = session
        logger.info(f"Created quiz session for chat {chat_id} (private={is_private_chat}) with {len(questions)} questions, time={time_per_question}s")
        return session
    
    def get_session(self, chat_id: int) -> Optional[QuizSession]:
        return self.active_sessions.get(chat_id)
    
    def get_session_by_poll(self, poll_id: str) -> Optional[QuizSession]:
        for session in self.active_sessions.values():
            if session.current_poll_id == poll_id and session.is_active:
                return session
        return None
    
    def end_session(self, chat_id: int):
        if chat_id in self.active_sessions:
            self.active_sessions[chat_id].is_active = False
            logger.info(f"Ended quiz session for chat {chat_id}")
            del self.active_sessions[chat_id]
    
    def has_active_session(self, chat_id: int) -> bool:
        return chat_id in self.active_sessions and self.active_sessions[chat_id].is_active


quiz_session_manager = QuizSessionManager()
