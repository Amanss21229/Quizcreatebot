import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

QUIZ_GROUP_LINK = "https://t.me/+YourQuizGroupLink"
QUIZ_GROUP_ID = None

class ChallengeState(Enum):
    WAITING = "waiting"
    LANGUAGE_SELECT = "language_select"
    QUIZ_TYPE_SELECT = "quiz_type_select"
    TIMER_SELECT = "timer_select"
    RUNNING = "running"
    COMPLETED = "completed"

@dataclass
class ChallengeParticipant:
    user_id: int
    first_name: str
    username: Optional[str]
    correct: int = 0
    wrong: int = 0
    unattempted: int = 0
    
    @property
    def score(self) -> int:
        return (self.correct * 4) - (self.wrong * 1)

@dataclass
class ChallengeSession:
    challenge_id: str
    chapter: str
    challenger_id: int
    challenger_name: str
    challenger_username: Optional[str]
    created_at: datetime
    state: ChallengeState = ChallengeState.WAITING
    language: str = "english"
    quiz_type: str = "neet"
    timer_seconds: int = 30
    accepted_users: List[int] = field(default_factory=list)
    question_count: int = 15
    countdown_task: Optional[asyncio.Task] = None
    quiz_start_time: Optional[datetime] = None
    chat_id: Optional[int] = None
    participants: Dict[int, 'ChallengeParticipant'] = field(default_factory=dict)
    poll_correct_options: Dict[str, int] = field(default_factory=dict)
    questions_sent: int = 0

class ChallengeManager:
    def __init__(self):
        self.active_challenge: Optional[ChallengeSession] = None
        self.challenge_queue: List[ChallengeSession] = []
        self.pending_challenges: Dict[str, ChallengeSession] = {}
        self.quiz_group_link = QUIZ_GROUP_LINK
        self.quiz_group_id = QUIZ_GROUP_ID
        self._lock = asyncio.Lock()
    
    def set_quiz_group(self, group_id: int, group_link: str):
        self.quiz_group_id = group_id
        self.quiz_group_link = group_link
    
    def generate_challenge_id(self) -> str:
        return f"CH{uuid.uuid4().hex[:8].upper()}"
    
    async def create_challenge(self, user_id: int, user_name: str, username: Optional[str], chapter: str) -> ChallengeSession:
        challenge_id = self.generate_challenge_id()
        challenge = ChallengeSession(
            challenge_id=challenge_id,
            chapter=chapter,
            challenger_id=user_id,
            challenger_name=user_name,
            challenger_username=username,
            created_at=datetime.now()
        )
        self.pending_challenges[challenge_id] = challenge
        return challenge
    
    def get_challenge_start_message(self, challenge: ChallengeSession) -> Tuple[str, InlineKeyboardMarkup]:
        message = (
            f"🔥 <b>CHALLENGE INITIATED!</b> 🔥\n\n"
            f"⚔️ <b>{challenge.challenger_name}</b> has thrown down the gauntlet!\n\n"
            f"📚 <b>Topic:</b> {challenge.chapter}\n"
            f"⏱️ <b>15 Power-Packed Questions</b>\n\n"
            f"⭐ <i>Quiz will start in 60 seconds after accepting your challenge!</i>\n\n"
            f"🎯 <b>Are you brave enough to accept?</b>\n"
            f"💪 Show your friends what you're made of!"
        )
        
        keyboard = [
            [InlineKeyboardButton(
                "🎁 Give Challenge To Your Friends",
                switch_inline_query=f"challenge_{challenge.challenge_id}"
            )],
            [InlineKeyboardButton(
                "🏟️ CHALLENGE GROUND",
                url=self.quiz_group_link
            )]
        ]
        
        return message, InlineKeyboardMarkup(keyboard)
    
    def get_challenge_share_message(self, challenge: ChallengeSession) -> Tuple[str, InlineKeyboardMarkup]:
        message = (
            f"⚡ <b>YOU'VE BEEN CHALLENGED!</b> ⚡\n\n"
            f"🗡️ <b>{challenge.challenger_name}</b> thinks they can beat you!\n\n"
            f"📚 <b>Battle Topic:</b> {challenge.chapter}\n"
            f"❓ <b>15 Mind-Bending Questions</b>\n\n"
            f"⭐ <i>Challenge will start in 60 seconds after you accept!</i>\n\n"
            f"🔥 Do you have what it takes?\n"
            f"💥 Prove your knowledge and claim victory!"
        )
        
        keyboard = [
            [InlineKeyboardButton(
                "✅ Accept The Challenge",
                url=self.quiz_group_link
            )],
            [InlineKeyboardButton(
                "🎁 Challenge Your Friends Also",
                switch_inline_query=f"challenge_{challenge.challenge_id}"
            )]
        ]
        
        return message, InlineKeyboardMarkup(keyboard)
    
    def get_inline_result_message(self, challenge: ChallengeSession) -> str:
        return (
            f"⚡ YOU'VE BEEN CHALLENGED! ⚡\n\n"
            f"🗡️ {challenge.challenger_name} thinks they can beat you!\n\n"
            f"📚 Battle Topic: {challenge.chapter}\n"
            f"❓ 15 Mind-Bending Questions\n\n"
            f"⭐ Challenge will start in 60 seconds after you accept!\n\n"
            f"🔥 Do you have what it takes?\n"
            f"💥 Prove your knowledge and claim victory!"
        )
    
    async def add_to_queue(self, challenge: ChallengeSession) -> int:
        async with self._lock:
            if self.active_challenge is None:
                self.active_challenge = challenge
                return 0
            else:
                self.challenge_queue.append(challenge)
                return len(self.challenge_queue)
    
    async def is_challenge_running(self) -> bool:
        return self.active_challenge is not None and self.active_challenge.state == ChallengeState.RUNNING
    
    async def get_queue_position(self, challenge_id: str) -> int:
        for i, c in enumerate(self.challenge_queue):
            if c.challenge_id == challenge_id:
                return i + 1
        return -1
    
    async def complete_current_challenge(self) -> Optional[ChallengeSession]:
        async with self._lock:
            if self.active_challenge:
                self.active_challenge.state = ChallengeState.COMPLETED
            
            if self.challenge_queue:
                self.active_challenge = self.challenge_queue.pop(0)
                return self.active_challenge
            else:
                self.active_challenge = None
                return None
    
    def get_language_selection_message(self) -> Tuple[str, InlineKeyboardMarkup]:
        message = (
            "🌐 <b>SELECT QUIZ LANGUAGE</b> 🌐\n\n"
            "📖 Choose your preferred language for the quiz:\n\n"
            "⭐ <i>Questions will be displayed in your selected language!</i>"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🇮🇳 हिंदी", callback_data="challenge_lang_hindi"),
                InlineKeyboardButton("🇬🇧 English", callback_data="challenge_lang_english")
            ]
        ]
        
        return message, InlineKeyboardMarkup(keyboard)
    
    def get_quiz_type_selection_message(self) -> Tuple[str, InlineKeyboardMarkup]:
        message = (
            "📚 <b>SELECT QUIZ TYPE</b> 📚\n\n"
            "🎯 Choose your examination level:\n\n"
            "💉 <b>NEET</b> - Medical Entrance\n"
            "⚙️ <b>JEE</b> - Engineering Entrance\n\n"
            "⭐ <i>Level will be mentioned in each question!</i>"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("💉 NEET", callback_data="challenge_type_neet"),
                InlineKeyboardButton("⚙️ JEE", callback_data="challenge_type_jee")
            ]
        ]
        
        return message, InlineKeyboardMarkup(keyboard)
    
    def get_timer_selection_message(self) -> Tuple[str, InlineKeyboardMarkup]:
        message = (
            "⏱️ <b>SELECT TIMER PER QUESTION</b> ⏱️\n\n"
            "⚡ Choose how much time you want for each question:\n\n"
            "💡 <i>Faster = More challenging!</i>"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("⚡ 15 sec", callback_data="challenge_timer_15"),
                InlineKeyboardButton("🔥 30 sec", callback_data="challenge_timer_30")
            ],
            [
                InlineKeyboardButton("⏰ 45 sec", callback_data="challenge_timer_45"),
                InlineKeyboardButton("🐢 60 sec", callback_data="challenge_timer_60")
            ]
        ]
        
        return message, InlineKeyboardMarkup(keyboard)
    
    def get_challenge_starting_message(self, seconds: int = 60) -> str:
        return (
            f"🚀 <b>CHALLENGE ACCEPTED!</b> 🚀\n\n"
            f"⏳ <b>Quiz Starting in {seconds} Seconds!</b>\n\n"
            f"📝 Get ready to test your knowledge!\n"
            f"🏆 May the best scholar win!\n\n"
            f"⭐ <i>Stay focused and give your best!</i>"
        )
    
    def get_quiz_busy_message(self) -> str:
        return (
            "⚠️ <b>Another Challenge is LIVE!</b> ⚠️\n\n"
            "🔴 Currently another quiz challenge is running.\n"
            "📋 Your challenge has been added to the queue!\n\n"
            "⏳ <i>Your challenge will start after the current one ends.</i>"
        )
    
    def get_next_challenge_message(self, seconds: int = 60) -> str:
        return (
            f"🎉 <b>Challenge Complete!</b> 🎉\n\n"
            f"⏰ <b>Next Challenge Starting in {seconds} Seconds!</b>\n\n"
            f"🔥 Get ready for the next battle!\n"
            f"💪 Keep your spirits high!"
        )
    
    def get_leaderboard_message(self, participants: List[dict], challenge: ChallengeSession) -> str:
        if not participants:
            return (
                "📊 <b>CHALLENGE LEADERBOARD</b> 📊\n\n"
                "😔 No participants in this challenge.\n\n"
                "💡 <i>Want to challenge your friends? Use /challenge command!</i>"
            )
        
        message = "🏆 <b>CHALLENGE LEADERBOARD</b> 🏆\n\n"
        message += f"📚 <b>Topic:</b> {challenge.chapter}\n"
        message += f"📝 <b>Quiz Type:</b> {challenge.quiz_type.upper()}\n\n"
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, p in enumerate(participants[:10]):
            rank_emoji = medals[i] if i < 3 else f"{i+1}."
            name = p.get('name', 'Unknown')
            score = p.get('score', 0)
            correct = p.get('correct', 0)
            wrong = p.get('wrong', 0)
            unattempted = p.get('unattempted', 0)
            
            message += f"{rank_emoji} <b>{name}</b>\n"
            message += f"   📊 Score: <b>{score}</b> | ✅ {correct} | ❌ {wrong} | ⏭️ {unattempted}\n\n"
        
        message += "━━━━━━━━━━━━━━━━━━━━\n"
        message += "<b>Scoring:</b> ✅ +4 | ❌ -1 | ⏭️ 0\n\n"
        message += "💡 <i>Want to challenge your friends? Use /challenge command!</i>"
        
        return message
    
    def record_poll_answer(self, poll_id: str, user_id: int, first_name: str, 
                           username: Optional[str], selected_option: int):
        """Record a poll answer for the active challenge."""
        if not self.active_challenge:
            return
        
        challenge = self.active_challenge
        
        if poll_id not in challenge.poll_correct_options:
            return
        
        correct_option = challenge.poll_correct_options[poll_id]
        
        if user_id not in challenge.participants:
            challenge.participants[user_id] = ChallengeParticipant(
                user_id=user_id,
                first_name=first_name,
                username=username
            )
        
        participant = challenge.participants[user_id]
        
        if selected_option == correct_option:
            participant.correct += 1
        else:
            participant.wrong += 1
    
    def register_poll(self, poll_id: str, correct_option: int):
        """Register a poll with its correct option."""
        if self.active_challenge:
            self.active_challenge.poll_correct_options[poll_id] = correct_option
    
    def get_sorted_participants(self, challenge: ChallengeSession) -> List[dict]:
        """Get sorted participants by score."""
        participants_list = []
        total_questions = challenge.questions_sent
        
        for p in challenge.participants.values():
            p.unattempted = total_questions - (p.correct + p.wrong)
            participants_list.append({
                'user_id': p.user_id,
                'name': p.first_name,
                'username': p.username,
                'score': p.score,
                'correct': p.correct,
                'wrong': p.wrong,
                'unattempted': p.unattempted
            })
        
        participants_list.sort(key=lambda x: (-x['score'], x['name']))
        return participants_list

challenge_manager = ChallengeManager()
