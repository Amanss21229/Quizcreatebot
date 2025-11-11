import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def escape_markdown(text: str) -> str:
    """Escape Markdown special characters in text."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    return text


@dataclass
class ParticipantStats:
    """Statistics for a single participant in the global quiz"""
    user_id: int
    username: Optional[str]
    first_name: str
    group_id: int
    group_title: str
    registered_group_id: int = 0
    correct: int = 0
    wrong: int = 0
    unattempted: int = 0
    total_time: float = 0.0
    answer_times: List[float] = field(default_factory=list)
    
    @property
    def score(self) -> int:
        """Calculate NEET score: +4 correct, -1 wrong, 0 unattempted"""
        return (self.correct * 4) - (self.wrong * 1)
    
    @property
    def total_attempts(self) -> int:
        return self.correct + self.wrong
    
    @property
    def negative_marks(self) -> int:
        return self.wrong * -1

@dataclass
class GroupQuizState:
    """State of quiz in a specific group"""
    group_id: int
    group_title: str
    auto_advance_task: Optional[asyncio.Task] = None
    current_question_index: int = 0
    poll_ids: List[str] = field(default_factory=list)
    active: bool = True
    error_count: int = 0

class LiveQuizSession:
    """Represents a global live quiz session"""
    
    def __init__(self, session_id: str, chapter: str, questions_english: List[dict], 
                 questions_hindi: List[dict], admin_id: int, global_quiz_id: str = None):
        self.session_id = session_id
        self.global_quiz_id = global_quiz_id  # Human-readable ID like GQ1234
        self.chapter = chapter
        self.questions_english = questions_english
        self.questions_hindi = questions_hindi
        self.admin_id = admin_id
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.countdown_task: Optional[asyncio.Task] = None
        self.quiz_task: Optional[asyncio.Task] = None
        
        # Track all groups participating
        self.group_states: Dict[int, GroupQuizState] = {}
        
        # Track all participants across all groups
        self.participants: Dict[int, ParticipantStats] = {}
        
        # Track which question each user answered correctly
        self.user_answers: Dict[int, List[bool]] = {}
        
        self.is_running = False
        self.is_completed = False
    
    def get_questions(self, language: str = 'english') -> List[dict]:
        """Get questions in the specified language"""
        return self.questions_hindi if language == 'hindi' else self.questions_english
    
    def get_question_count(self) -> int:
        """Get total number of questions"""
        return len(self.questions_english)
    
    def add_group(self, group_id: int, group_title: str):
        """Add a group to the session"""
        if group_id not in self.group_states:
            self.group_states[group_id] = GroupQuizState(
                group_id=group_id,
                group_title=group_title
            )
    
    def deactivate_group(self, group_id: int):
        """Mark a group as inactive (e.g., if quiz was stopped manually)"""
        if group_id in self.group_states:
            self.group_states[group_id].active = False
    
    def record_answer(self, user_id: int, username: Optional[str], first_name: str, 
                     group_id: int, group_title: str, is_correct: bool, time_taken: float):
        """Record a user's answer - only counts answers from user's first participating group"""
        if user_id not in self.participants:
            self.participants[user_id] = ParticipantStats(
                user_id=user_id,
                username=username,
                first_name=first_name,
                group_id=group_id,
                group_title=group_title,
                registered_group_id=group_id
            )
            self.user_answers[user_id] = []
        
        participant = self.participants[user_id]
        
        if participant.registered_group_id != group_id:
            logger.info(f"User {user_id} trying to answer from different group {group_id}, but registered in {participant.registered_group_id}. Ignoring.")
            return
        
        if is_correct:
            participant.correct += 1
        else:
            participant.wrong += 1
        
        participant.answer_times.append(time_taken)
        participant.total_time += time_taken
        self.user_answers[user_id].append(is_correct)
    
    def mark_unattempted(self, user_id: int, question_count: int):
        """Mark remaining questions as unattempted for a user"""
        if user_id in self.participants:
            answered = len(self.user_answers.get(user_id, []))
            self.participants[user_id].unattempted = question_count - answered
    
    def get_sorted_participants(self) -> List[ParticipantStats]:
        """Get participants sorted by score (descending), then by time (ascending)"""
        participants_list = list(self.participants.values())
        # Sort by score (descending), then by total_time (ascending)
        participants_list.sort(key=lambda p: (-p.score, p.total_time))
        return participants_list
    
    def get_group_stats(self) -> Dict[int, int]:
        """Get participant count per group"""
        group_counts = {}
        for participant in self.participants.values():
            group_id = participant.group_id
            group_counts[group_id] = group_counts.get(group_id, 0) + 1
        return group_counts


class LiveQuizCoordinator:
    """Coordinates global live quiz sessions across all groups"""
    
    def __init__(self):
        self.active_session: Optional[LiveQuizSession] = None
        self.session_history: List[str] = []
        self.question_duration = 60  # seconds per question (default 1 minute)
        self.poll_to_question_map: Dict[str, tuple] = {}  # poll_id -> (session_id, question_index)
        
        # Storage for completed quiz sessions
        self.completed_quizzes: Dict[str, LiveQuizSession] = {}  # global_quiz_id -> session
        
        # Database repository for persistent storage
        self.quiz_repository = None
    
    def set_repository(self, repository):
        """Set the QuizSessionRepository for database persistence."""
        self.quiz_repository = repository
        logger.info("✅ QuizSessionRepository injected into LiveQuizCoordinator")
        self.quiz_id_counter = self._load_quiz_counter()
        self._load_completed_quizzes()
    
    def _load_quiz_counter(self) -> int:
        """Load the quiz ID counter from file"""
        try:
            if os.path.exists('data/quiz_id_counter.json'):
                with open('data/quiz_id_counter.json', 'r') as f:
                    data = json.load(f)
                    return data.get('counter', 1)
        except Exception as e:
            logger.error(f"Failed to load quiz counter: {e}")
        return 1
    
    def _save_quiz_counter(self):
        """Save the quiz ID counter to file"""
        try:
            os.makedirs('data', exist_ok=True)
            with open('data/quiz_id_counter.json', 'w') as f:
                json.dump({'counter': self.quiz_id_counter}, f)
        except Exception as e:
            logger.error(f"Failed to save quiz counter: {e}")
    
    def _load_completed_quizzes(self):
        """Load last 50 completed quizzes from file into memory
        
        Note: This loads only metadata. Full session data (participants, etc.) 
        is only available during the same runtime. Force-send commands work 
        only for quizzes completed in the current session.
        """
        try:
            if os.path.exists('data/completed_global_quizzes.json'):
                with open('data/completed_global_quizzes.json', 'r') as f:
                    data = json.load(f)
                    logger.info(f"Loaded metadata for {len(data)} completed quizzes from storage")
                    logger.info("Note: Force-send leaderboards only work for quizzes completed in current session")
        except Exception as e:
            logger.error(f"Failed to load completed quizzes: {e}")
    
    async def _save_completed_quiz(self, session: LiveQuizSession):
        """Save a completed quiz to database with 1-hour retention"""
        try:
            if not self.quiz_repository:
                logger.warning("Quiz repository not available, falling back to JSON storage")
                self._save_completed_quiz_to_json(session)
                return
            
            # Store in memory for immediate access
            self.completed_quizzes[session.global_quiz_id] = session
            
            # Prepare quiz data
            quiz_data = {
                'quiz_id': session.global_quiz_id,
                'session_id': session.session_id,
                'chapter': session.chapter,
                'start_time': session.start_time.isoformat() if session.start_time else None,
                'end_time': session.end_time.isoformat() if session.end_time else None,
                'question_count': session.get_question_count(),
                'questions_english': session.questions_english,
                'questions_hindi': session.questions_hindi
            }
            
            # Prepare participant data
            participants = []
            for user_id, stats in session.participants.items():
                participants.append({
                    'user_id': stats.user_id,
                    'username': stats.username,
                    'first_name': stats.first_name,
                    'group_id': stats.registered_group_id,
                    'score': stats.score,
                    'correct': stats.correct,
                    'wrong': stats.wrong,
                    'unattempted': stats.unattempted,
                    'total_time': stats.total_time
                })
            
            # Prepare group data
            groups = []
            for group_id, group_state in session.group_states.items():
                group_participants = [p for p in session.participants.values() 
                                    if p.registered_group_id == group_id]
                groups.append({
                    'group_id': group_id,
                    'group_title': group_state.group_title,
                    'participant_count': len(group_participants)
                })
            
            # Save to database
            success = await self.quiz_repository.save_quiz_session(
                quiz_id=session.global_quiz_id,
                question_count=session.get_question_count(),
                time_per_question=self.question_duration,
                quiz_data=quiz_data,
                participants=participants,
                groups=groups
            )
            
            if success:
                logger.info(f"✅ Saved quiz {session.global_quiz_id} to database (expires in 1 hour)")
            else:
                logger.warning(f"⚠️ Failed to save quiz {session.global_quiz_id} to database, using JSON fallback")
                self._save_completed_quiz_to_json(session)
            
            # Keep only last 50 in memory (remove oldest)
            if len(self.completed_quizzes) > 50:
                # Sort by insertion order (oldest first) and remove the oldest ones
                all_keys = list(self.completed_quizzes.keys())
                oldest_keys = all_keys[:len(all_keys) - 50]
                for key in oldest_keys:
                    self.completed_quizzes.pop(key, None)
            
            logger.info(f"Quiz {session.global_quiz_id} stored in memory")
        
        except Exception as e:
            logger.error(f"Error saving completed quiz: {e}", exc_info=True)
            # Fallback to JSON on any error
            self._save_completed_quiz_to_json(session)
    
    def _save_completed_quiz_to_json(self, session: LiveQuizSession):
        """Fallback method to save quiz to JSON file"""
        try:
            os.makedirs('data', exist_ok=True)
            
            quiz_data = {
                'quiz_id': session.global_quiz_id,
                'session_id': session.session_id,
                'chapter': session.chapter,
                'start_time': session.start_time.isoformat() if session.start_time else None,
                'end_time': session.end_time.isoformat() if session.end_time else None,
                'question_count': session.get_question_count(),
                'participant_count': len(session.participants),
                'group_ids': list(session.group_states.keys())
            }
            
            if os.path.exists('data/completed_global_quizzes.json'):
                with open('data/completed_global_quizzes.json', 'r') as f:
                    all_quizzes = json.load(f)
            else:
                all_quizzes = []
            
            all_quizzes.insert(0, quiz_data)
            all_quizzes = all_quizzes[:100]
            
            with open('data/completed_global_quizzes.json', 'w') as f:
                json.dump(all_quizzes, f, indent=2)
            
            self.completed_quizzes[session.global_quiz_id] = session
            
            logger.info(f"Saved quiz {session.global_quiz_id} to JSON file")
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}", exc_info=True)
    
    def has_active_session(self) -> bool:
        """Check if there's an active live quiz session"""
        return self.active_session is not None and not self.active_session.is_completed
    
    def create_session(self, chapter: str, questions_english: List[dict], 
                       questions_hindi: List[dict], admin_id: int) -> LiveQuizSession:
        """Create a new live quiz session with both English and Hindi questions"""
        session_id = f"live_{int(datetime.now().timestamp())}"
        
        global_quiz_id = f"GQ{self.quiz_id_counter:04d}"
        self.quiz_id_counter += 1
        self._save_quiz_counter()
        
        session = LiveQuizSession(session_id, chapter, questions_english, questions_hindi, admin_id, global_quiz_id)
        self.active_session = session
        self.session_history.append(session_id)
        logger.info(f"Created live quiz session {session_id} ({global_quiz_id}) for chapter: {chapter} with {len(questions_english)} questions")
        return session
    
    async def send_countdown_reminder(self, context: ContextTypes.DEFAULT_TYPE, 
                                     group_ids: List[int], chapter: str, question_count: int):
        """Send 1-minute countdown reminder to all groups and users"""
        reminder_message = f"""
╔═══════════════════════════════════╗
║   🔴 LIVE QUIZ STARTING SOON! 🔴  ║
╚═══════════════════════════════════╝

⏰ **COUNTDOWN: 1 MINUTE**

🎯 **Chapter:** {chapter}
📝 **Questions:** {question_count} MCQs
⏱️ **Timer:** {self.question_duration} seconds per question
🌍 **Type:** GLOBAL LIVE QUIZ

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **What is Global Live Quiz?**

🌟 All groups compete simultaneously
🏆 One unified leaderboard across all groups
⚡ Same questions, same timing for everyone
🎖️ Prove you're the best among ALL students!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ **Get Ready!**

✅ Turn on notifications
✅ Keep your group active
✅ Be ready to answer quickly
✅ Aim for the top rank!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ Quiz starts in **1 minute**...

【~@DrQuizRobot】
"""
        
        # Send to all groups
        sent_count = 0
        for group_id in group_ids:
            try:
                await context.bot.send_message(
                    chat_id=group_id,
                    text=reminder_message
                )
                sent_count += 1
                await asyncio.sleep(0.2)  # Rate limiting
            except Exception as e:
                logger.error(f"Failed to send reminder to group {group_id}: {e}")
        
        logger.info(f"Sent countdown reminders to {sent_count}/{len(group_ids)} groups")
        return sent_count
    
    async def start_quiz_after_countdown(self, context: ContextTypes.DEFAULT_TYPE, 
                                         session: LiveQuizSession, 
                                         group_ids: List[int],
                                         quiz_gen,
                                         quiz_lock_manager,
                                         stats_manager,
                                         language_manager):
        """Wait 1 minute then start the quiz in all groups"""
        try:
            # Wait 1 minute (60 seconds)
            await asyncio.sleep(60)
            
            # Start the quiz
            await self.broadcast_quiz_start(
                context, session, group_ids, quiz_gen, 
                quiz_lock_manager, stats_manager, language_manager
            )
            
        except asyncio.CancelledError:
            logger.info("Countdown was cancelled")
        except Exception as e:
            logger.error(f"Error during countdown: {e}")
    
    async def broadcast_quiz_start(self, context: ContextTypes.DEFAULT_TYPE,
                                   session: LiveQuizSession,
                                   group_ids: List[int],
                                   quiz_gen,
                                   quiz_lock_manager,
                                   stats_manager,
                                   language_manager):
        """Start the quiz simultaneously in all groups"""
        session.is_running = True
        session.start_time = datetime.now()
        
        start_message = f"""
╔═══════════════════════════════════╗
║   🔴 LIVE QUIZ STARTING NOW! 🔴   ║
╚═══════════════════════════════════╝

📚 **Chapter:** {session.chapter}
⏱️ **{self.question_duration} seconds per question**
🌍 **Competing with ALL groups!**

Good luck! 🍀

【~@DrQuizRobot】
"""
        
        # Send start message and register groups
        for group_id in group_ids:
            try:
                # Get group info
                chat = await context.bot.get_chat(group_id)
                group_title = chat.title or f"Group {group_id}"
                
                # Add group to session
                session.add_group(group_id, group_title)
                
                # Acquire lock for this group
                quiz_lock_manager.acquire_lock(group_id, "global_live")
                
                # Send start message
                await context.bot.send_message(
                    chat_id=group_id,
                    text=start_message
                )
                
                await asyncio.sleep(0.2)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Failed to start quiz in group {group_id}: {e}")
                session.deactivate_group(group_id)
        
        # Now broadcast questions one by one
        logger.info(f"Starting to broadcast {session.get_question_count()} questions to {len(session.group_states)} groups")
        try:
            await self.broadcast_questions(context, session, quiz_lock_manager, language_manager)
        except Exception as e:
            logger.error(f"Fatal error broadcasting questions: {e}", exc_info=True)
            # Send error message to all groups and release locks
            error_msg = f"❌ Error broadcasting questions: {str(e)}\n\nPlease contact support."
            for group_id in session.group_states.keys():
                try:
                    await context.bot.send_message(chat_id=group_id, text=error_msg)
                except:
                    pass
                finally:
                    # Always release lock even if sending error message fails
                    quiz_lock_manager.release_lock(group_id)
            
            # Clear the active session since quiz failed
            session.is_completed = True
            self.active_session = None
            logger.info(f"Cleared failed session {session.session_id}")
    
    async def broadcast_questions(self, context: ContextTypes.DEFAULT_TYPE,
                                  session: LiveQuizSession,
                                  quiz_lock_manager,
                                  language_manager):
        """Broadcast questions to all active groups with synchronized timing and language support"""
        num_questions = session.get_question_count()
        logger.info(f"broadcast_questions called with {num_questions} questions")
        
        # Pre-fetch language preferences for all groups
        group_languages = {}
        for group_id in session.group_states.keys():
            group_languages[group_id] = language_manager.get_language(group_id)
            logger.info(f"Group {group_id} language preference: {group_languages[group_id]}")
        
        for idx in range(num_questions):
            question_num = idx + 1
            logger.info(f"Broadcasting question {question_num}/{num_questions}")
            
            # Broadcast this question to all active groups
            for group_id, group_state in session.group_states.items():
                if not group_state.active:
                    logger.warning(f"Group {group_id} is not active, skipping")
                    continue
                
                try:
                    # Get the appropriate language version for this group
                    group_lang = group_languages.get(group_id, 'english')
                    questions = session.get_questions(group_lang)
                    question = questions[idx]
                    
                    logger.info(f"Sending Q{question_num} to group {group_id} in {group_lang}")
                    
                    # Send poll
                    poll_message = await context.bot.send_poll(
                        chat_id=group_id,
                        question=f"Q{question_num}/{num_questions}: {question['question']}",
                        options=question['options'],
                        type='quiz',
                        correct_option_id=int(question['correct_answer']),
                        is_anonymous=False,
                        open_period=self.question_duration
                    )
                    
                    poll_id = poll_message.poll.id
                    group_state.poll_ids.append(poll_id)
                    group_state.current_question_index = idx
                    
                    # Register poll in global map for easy lookup
                    self.poll_to_question_map[poll_id] = (session.session_id, idx, group_id)
                    
                    logger.info(f"Sent live quiz Q{question_num} to group {group_id}, poll_id: {poll_id}, lang: {group_lang}")
                    
                except Exception as e:
                    logger.error(f"Failed to send question {question_num} to group {group_id}: {e}")
                    group_state.error_count += 1
                    if group_state.error_count >= 3:
                        session.deactivate_group(group_id)
            
            # Wait for question duration before next question
            if question_num < num_questions:
                await asyncio.sleep(self.question_duration + 2)  # +2 seconds buffer
        
        # All questions sent, wait a bit then finalize
        await asyncio.sleep(5)
        await self.finalize_session(context, session, quiz_lock_manager)
    
    async def finalize_session(self, context: ContextTypes.DEFAULT_TYPE,
                               session: LiveQuizSession,
                               quiz_lock_manager):
        """Finalize the session and send global + group-specific leaderboards"""
        try:
            session.is_running = False
            session.is_completed = True
            session.end_time = datetime.now()
            
            # Mark unattempted questions for all participants
            for user_id in session.participants.keys():
                session.mark_unattempted(user_id, session.get_question_count())
            
            # Save completed quiz to storage
            await self._save_completed_quiz(session)
            
            # Get sorted participants with global ranks
            sorted_participants = session.get_sorted_participants()
            
            # Create global rank mapping
            global_rank_map = {}
            for rank, participant in enumerate(sorted_participants, 1):
                global_rank_map[participant.user_id] = rank
            
            # Generate and send leaderboards to all groups with retry logic
            failed_groups = []
            for group_id, group_state in session.group_states.items():
                try:
                    # Send global leaderboard (top 50)
                    global_leaderboard = self.generate_global_leaderboard(session, sorted_participants)
                    await context.bot.send_message(
                        chat_id=group_id,
                        text=global_leaderboard,
                        parse_mode='Markdown'
                    )
                    logger.info(f"Sent global leaderboard for {session.global_quiz_id} to group {group_id}")
                    
                    await asyncio.sleep(0.5)
                    
                    # Send group-specific leaderboard (may be multiple messages)
                    group_leaderboard_messages = self.generate_group_leaderboard(
                        session, group_id, group_state.group_title, global_rank_map
                    )
                    if group_leaderboard_messages:
                        for message in group_leaderboard_messages:
                            await context.bot.send_message(
                                chat_id=group_id,
                                text=message,
                                parse_mode='Markdown'
                            )
                            await asyncio.sleep(0.3)
                        logger.info(f"Sent group leaderboard ({len(group_leaderboard_messages)} message(s)) for {session.global_quiz_id} to group {group_id}")
                    
                    await asyncio.sleep(0.3)
                    
                except Exception as e:
                    logger.error(f"Failed to send leaderboard to group {group_id}: {e}", exc_info=True)
                    failed_groups.append(group_id)
                finally:
                    # ALWAYS release lock, even if leaderboard sending failed
                    quiz_lock_manager.release_lock(group_id)
                    logger.info(f"Released quiz lock for group {group_id} after live quiz completion")
            
            if failed_groups:
                logger.warning(f"Failed to send leaderboards to {len(failed_groups)} groups for quiz {session.global_quiz_id}. Use /fgloballeaderboard or /fgroupleaderboard to retry.")
            
            logger.info(f"Live quiz session {session.session_id} ({session.global_quiz_id}) completed with {len(session.participants)} participants")
            
            # Clean up poll mappings to avoid memory leaks
            polls_to_remove = [poll_id for poll_id, (sess_id, _, _) in self.poll_to_question_map.items() 
                              if sess_id == session.session_id]
            for poll_id in polls_to_remove:
                del self.poll_to_question_map[poll_id]
            
            logger.info(f"Cleaned up {len(polls_to_remove)} poll mappings for session {session.session_id}")
            
        finally:
            # ALWAYS clear active session, even if there were errors
            self.active_session = None
            logger.info(f"Cleared active session {session.session_id}")
    
    def generate_global_leaderboard(self, session: LiveQuizSession, sorted_participants: List[ParticipantStats]) -> str:
        """Generate beautifully formatted global leaderboard with top 50 performers"""
        group_stats = session.get_group_stats()
        
        # Header
        chapter_display = session.chapter[:25] if len(session.chapter) <= 25 else session.chapter[:22] + "..."
        leaderboard = f"""
╔═══════════════════════════════════════╗
║    🏆 GLOBAL LIVE QUIZ RESULTS 🏆    ║
║       Chapter: {chapter_display}       
╚═══════════════════════════════════════╝

🆔 **QUIZ ID:** `{session.global_quiz_id}`

📊 **QUIZ STATISTICS**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 Participants: {len(session.participants)} | 🌍 Groups: {len(group_stats)}
📚 Questions: {session.get_question_count()} MCQs | ⏱️ Timer: {self.question_duration}s/Q

🏅 **TOP 50 PERFORMERS GLOBALLY**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # Top participants with detailed stats (limit to 50)
        medal_emojis = ["🥇", "🥈", "🥉"]
        max_display = min(50, len(sorted_participants))
        
        for rank, participant in enumerate(sorted_participants[:max_display], 1):
            # Rank display with medals
            if rank <= 3:
                rank_display = medal_emojis[rank - 1]
            elif rank <= 10:
                rank_display = f"🎖️#{rank}"
            else:
                rank_display = f"🏅#{rank}"
            
            # User display - use first name instead of username
            first_name_display = participant.first_name
            if len(first_name_display) > 20:
                first_name_display = first_name_display[:17] + "..."
            
            # Make name clickable (escape markdown chars)
            escaped_name = escape_markdown(first_name_display)
            clickable_name = f"[{escaped_name}](tg://user?id={participant.user_id})"
            
            # Calculate detailed stats
            total_score = participant.score
            correct_marks = participant.correct * 4
            negative_marks = participant.wrong * -1
            total_attempted = participant.total_attempts
            total_time = participant.total_time
            
            # Format group name
            group_name = participant.group_title[:18] if len(participant.group_title) <= 18 else participant.group_title[:15] + "..."
            
            leaderboard += f"""
{rank_display} **{clickable_name}**
   💯 Score: {total_score:+d} | ✅ {participant.correct} ❌ {participant.wrong} ⏭️ {participant.unattempted}
   ⏱️ {total_time:.1f}s | 🏛️ {group_name}

"""
        
        # Footer
        if len(sorted_participants) > max_display:
            leaderboard += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💬 +{len(sorted_participants) - max_display} more participants competed!\n\n"
        
        leaderboard += """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 **SCORING: NEET PATTERN**
✅ Correct = +4 | ❌ Wrong = -1 | ⏭️ Skip = 0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **Need Explanation?**
Reply to any quiz question with `/explain`
to get detailed AI-powered explanation!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Check your group's detailed leaderboard below! 👇

【~@DrQuizRobot】
"""
        
        return leaderboard
    
    def generate_group_leaderboard(self, session: LiveQuizSession, group_id: int, 
                                   group_title: str, global_rank_map: dict) -> List[str]:
        """Generate beautifully formatted group-specific leaderboard with global ranks
        Returns a list of message strings to handle Telegram's 4096 character limit"""
        # Filter participants from this group
        group_participants = [
            p for p in session.participants.values() 
            if p.registered_group_id == group_id
        ]
        
        if not group_participants:
            return []
        
        # Sort by score (descending), then by time (ascending)
        group_participants.sort(key=lambda p: (-p.score, p.total_time))
        
        # Header with group name
        group_name_display = group_title[:30] if len(group_title) <= 30 else group_title[:27] + "..."
        header = f"""
╔═══════════════════════════════════════╗
║       🏛️ YOUR GROUP LEADERBOARD       ║
╚═══════════════════════════════════════╝

📍 **GROUP:** {group_name_display}
👥 **PARTICIPANTS:** {len(group_participants)}
📚 **CHAPTER:** {session.chapter[:25]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
       🎯 **DETAILED PERFORMANCE** 🎯
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        
        messages = []
        current_message = header
        
        # Categorize participants by performance
        top_performers = []
        good_performers = []
        average_performers = []
        need_improvement = []
        
        for participant in group_participants:
            accuracy = (participant.correct / (participant.correct + participant.wrong) * 100) if (participant.correct + participant.wrong) > 0 else 0
            if accuracy >= 80 and participant.score > 0:
                top_performers.append(participant)
            elif accuracy >= 60 or participant.score > 0:
                good_performers.append(participant)
            elif participant.total_attempts > 0:
                average_performers.append(participant)
            else:
                need_improvement.append(participant)
        
        # Display all participants with detailed stats in decorated boxes
        MAX_MESSAGE_LENGTH = 3500  # Leave buffer for safety
        
        for group_rank, participant in enumerate(group_participants, 1):
            global_rank = global_rank_map.get(participant.user_id, "N/A")
            
            # Rank emoji
            if group_rank == 1:
                rank_emoji = "👑"
            elif group_rank == 2:
                rank_emoji = "🥈"
            elif group_rank == 3:
                rank_emoji = "🥉"
            elif group_rank <= 5:
                rank_emoji = "⭐"
            else:
                rank_emoji = "📍"
            
            # User display - prioritize first_name over username
            username_display = participant.first_name
            if len(username_display) > 20:
                username_display = username_display[:17] + "..."
            
            # Make name clickable (escape markdown chars)
            escaped_name = escape_markdown(username_display)
            clickable_name = f"[{escaped_name}](tg://user?id={participant.user_id})"
            
            # Performance indicator
            accuracy = (participant.correct / (participant.correct + participant.wrong) * 100) if (participant.correct + participant.wrong) > 0 else 0
            if accuracy >= 80:
                perf_emoji = "🔥"
            elif accuracy >= 60:
                perf_emoji = "💪"
            elif accuracy >= 40:
                perf_emoji = "📈"
            else:
                perf_emoji = "📊"
            
            # Calculate stats
            total_score = participant.score
            correct = participant.correct
            wrong = participant.wrong
            unattempted = participant.unattempted
            total_attempted = participant.total_attempts
            time_taken = participant.total_time
            
            # Create compact decorated box for each user
            participant_entry = f"""╭{'─' * 38}╮
│ {rank_emoji} **{clickable_name}** {perf_emoji}
├─ 🏆 Ranks: 🌍 Global **#{global_rank}** │ 🏛️ Group **#{group_rank}**
├─ 💯 Score: **{total_score:+d}** │ ✅ {correct} │ ❌ {wrong} │ ⏭️ {unattempted}
├─ 📊 Accuracy: {accuracy:.1f}% │ ⏱️ {time_taken:.1f}s
╰{'─' * 38}╯

"""
            
            # Check if adding this participant would exceed limit
            if len(current_message) + len(participant_entry) > MAX_MESSAGE_LENGTH:
                # Save current message and start a new one
                messages.append(current_message)
                current_message = f"**📋 Group Leaderboard (continued...)**\n\n" + participant_entry
            else:
                current_message += participant_entry
        
        # Footer with motivational message
        footer = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **GROUP PERFORMANCE SUMMARY**

🔥 Top Performers (≥80%): {len(top_performers)}
💪 Good Performers (≥60%): {len(good_performers)}
📈 Average Performers: {len(average_performers)}
📊 Room for Improvement: {len(need_improvement)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **TIPS FOR IMPROVEMENT:**
✅ Review wrong answers using /explain
📚 Focus on NCERT concepts
⏱️ Practice time management
🎯 Attempt all questions

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎉 Great effort, team! Keep practicing! 💪

【~@DrQuizRobot】
"""
        
        # Add footer to last message or create new message if it doesn't fit
        if len(current_message) + len(footer) > MAX_MESSAGE_LENGTH:
            messages.append(current_message)
            messages.append(footer)
        else:
            current_message += footer
            messages.append(current_message)
        
        return messages
    
    async def end_live_quiz_early(self, context: ContextTypes.DEFAULT_TYPE, quiz_lock_manager):
        """End the live quiz early and send leaderboard for questions answered so far"""
        if not self.active_session or self.active_session.is_completed:
            return False, "No active live quiz to end."
        
        session = self.active_session
        
        # Cancel countdown task if quiz hasn't started yet
        if session.countdown_task and not session.countdown_task.done() and not session.is_running:
            session.countdown_task.cancel()
            logger.info("Cancelled countdown task")
            return False, "Live quiz hasn't started yet. Countdown cancelled."
        
        # Send end message to all groups
        end_message = """
╔═══════════════════════════════════╗
║   ⚠️ LIVE QUIZ ENDED EARLY ⚠️     ║
╚═══════════════════════════════════╝

📢 **Quiz has been stopped by admin**

⏱️ Calculating results for questions answered so far...

【~@DrQuizRobot】
"""
        
        for group_id, group_state in session.group_states.items():
            try:
                await context.bot.send_message(
                    chat_id=group_id,
                    text=end_message
                )
                await asyncio.sleep(0.2)
            except Exception as e:
                logger.error(f"Failed to send end message to group {group_id}: {e}")
        
        # Wait a moment before sending leaderboard
        await asyncio.sleep(2)
        
        # Calculate questions answered
        max_question_index = 0
        for group_state in session.group_states.values():
            if group_state.current_question_index > max_question_index:
                max_question_index = group_state.current_question_index
        
        questions_answered = max_question_index + 1
        
        # Update session to reflect actual questions asked
        session.questions = session.questions[:questions_answered]
        
        # Finalize session with early end
        await self.finalize_session(context, session, quiz_lock_manager)
        
        logger.info(f"Live quiz ended early after {questions_answered} questions")
        return True, f"Live quiz ended successfully. Leaderboard sent for {questions_answered} questions."
    
    async def get_quiz_by_id(self, global_quiz_id: str) -> Optional[LiveQuizSession]:
        """Get a completed quiz by its global quiz ID (checks memory first, then database)"""
        # Check in-memory cache first
        if global_quiz_id in self.completed_quizzes:
            return self.completed_quizzes[global_quiz_id]
        
        # If not in memory and repository is available, fetch from database
        if self.quiz_repository:
            try:
                quiz_data_dict = await self.quiz_repository.get_quiz_session(global_quiz_id)
                if quiz_data_dict:
                    logger.info(f"Retrieved quiz {global_quiz_id} from database")
                    # Reconstruct LiveQuizSession from database data
                    session = self._reconstruct_session_from_db(quiz_data_dict)
                    # Store in memory for future access
                    self.completed_quizzes[global_quiz_id] = session
                    return session
            except Exception as e:
                logger.error(f"Error fetching quiz from database: {e}", exc_info=True)
        
        return None
    
    def _reconstruct_session_from_db(self, quiz_data: dict) -> LiveQuizSession:
        """Reconstruct a LiveQuizSession object from database data"""
        from datetime import datetime
        
        data = quiz_data['quiz_data']
        session = LiveQuizSession(
            session_id=data['session_id'],
            chapter=data['chapter'],
            questions_english=data['questions_english'],
            questions_hindi=data['questions_hindi'],
            admin_id=0,  # Not stored in DB
            global_quiz_id=data['quiz_id']
        )
        
        session.is_completed = True
        session.is_running = False
        session.start_time = datetime.fromisoformat(data['start_time']) if data.get('start_time') else None
        session.end_time = datetime.fromisoformat(data['end_time']) if data.get('end_time') else None
        
        # Reconstruct participants
        for p_data in quiz_data.get('participants', []):
            stats = ParticipantStats(
                user_id=p_data['user_id'],
                username=p_data.get('username'),
                first_name=p_data['first_name'],
                group_id=p_data['group_id'],
                group_title=p_data.get('group_title', ''),
                registered_group_id=p_data['group_id'],
                correct=p_data['correct'],
                wrong=p_data['wrong'],
                unattempted=p_data['unattempted'],
                total_time=p_data.get('total_time', 0.0)
            )
            session.participants[p_data['user_id']] = stats
        
        # Reconstruct group states
        for g_data in quiz_data.get('groups', []):
            session.group_states[g_data['group_id']] = GroupQuizState(
                group_id=g_data['group_id'],
                group_title=g_data['group_title']
            )
        
        return session
    
    async def force_send_global_leaderboard(self, context: ContextTypes.DEFAULT_TYPE, 
                                           global_quiz_id: str, force_join_manager) -> tuple[bool, str]:
        """Force send global leaderboard for a specific quiz to all groups
        
        Note: Only works for quizzes completed in the current bot session.
        """
        # Validate quiz ID format
        import re
        if not re.match(r'^GQ\d{4}$', global_quiz_id):
            return False, f"❌ Invalid quiz ID format. Expected format: GQ0001"
        
        session = await self.get_quiz_by_id(global_quiz_id)
        if not session:
            return False, f"❌ Quiz {global_quiz_id} not found or expired (quizzes are stored for 1 hour after completion)."
        
        if not session.is_completed:
            return False, f"❌ Quiz {global_quiz_id} is not completed yet."
        
        # Get sorted participants with global ranks
        sorted_participants = session.get_sorted_participants()
        
        # Generate global leaderboard
        global_leaderboard = self.generate_global_leaderboard(session, sorted_participants)
        
        # Get all groups from force_join_manager
        all_groups = force_join_manager.get_all_groups()
        
        sent_count = 0
        failed_count = 0
        
        for group_id in all_groups:
            try:
                await context.bot.send_message(
                    chat_id=group_id,
                    text=global_leaderboard,
                    parse_mode='Markdown'
                )
                sent_count += 1
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"Failed to send global leaderboard to group {group_id}: {e}")
                failed_count += 1
        
        return True, f"✅ Global leaderboard for quiz {global_quiz_id} sent to {sent_count} groups. Failed: {failed_count}"
    
    async def force_send_group_leaderboards(self, context: ContextTypes.DEFAULT_TYPE, 
                                           global_quiz_id: str, force_join_manager) -> tuple[bool, str]:
        """Force send group-specific leaderboards for a specific quiz to all groups
        
        Note: Only works for quizzes completed in the current bot session.
        """
        # Validate quiz ID format
        import re
        if not re.match(r'^GQ\d{4}$', global_quiz_id):
            return False, f"❌ Invalid quiz ID format. Expected format: GQ0001"
        
        session = await self.get_quiz_by_id(global_quiz_id)
        if not session:
            return False, f"❌ Quiz {global_quiz_id} not found or expired (quizzes are stored for 1 hour after completion)."
        
        if not session.is_completed:
            return False, f"❌ Quiz {global_quiz_id} is not completed yet."
        
        # Get sorted participants with global ranks
        sorted_participants = session.get_sorted_participants()
        
        # Create global rank mapping
        global_rank_map = {}
        for rank, participant in enumerate(sorted_participants, 1):
            global_rank_map[participant.user_id] = rank
        
        # Get all groups from force_join_manager
        all_groups = force_join_manager.get_all_groups()
        
        sent_count = 0
        failed_count = 0
        no_participants_count = 0
        
        for group_id in all_groups:
            try:
                # Get group title from session group_states or use a default
                group_title = session.group_states.get(group_id, type('obj', (object,), {'group_title': 'Group'})).group_title
                
                # Generate group-specific leaderboard (may be multiple messages)
                group_leaderboard_messages = self.generate_group_leaderboard(
                    session, group_id, group_title, global_rank_map
                )
                
                if group_leaderboard_messages:
                    for message in group_leaderboard_messages:
                        await context.bot.send_message(
                            chat_id=group_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                        await asyncio.sleep(0.3)
                    sent_count += 1
                else:
                    no_participants_count += 1
                
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"Failed to send group leaderboard to group {group_id}: {e}")
                failed_count += 1
        
        return True, f"✅ Group leaderboards for quiz {global_quiz_id} sent to {sent_count} groups. No participants: {no_participants_count}, Failed: {failed_count}"


# Global instance
live_quiz_coordinator = LiveQuizCoordinator()
