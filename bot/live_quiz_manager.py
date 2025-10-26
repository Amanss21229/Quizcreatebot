import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

@dataclass
class ParticipantStats:
    """Statistics for a single participant in the global quiz"""
    user_id: int
    username: Optional[str]
    first_name: str
    group_id: int
    group_title: str
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
    
    def __init__(self, session_id: str, chapter: str, questions: List[dict], admin_id: int):
        self.session_id = session_id
        self.chapter = chapter
        self.questions = questions
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
        """Record a user's answer"""
        if user_id not in self.participants:
            self.participants[user_id] = ParticipantStats(
                user_id=user_id,
                username=username,
                first_name=first_name,
                group_id=group_id,
                group_title=group_title
            )
            self.user_answers[user_id] = []
        
        participant = self.participants[user_id]
        
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
        self.question_duration = 45  # seconds per question
        self.poll_to_question_map: Dict[str, tuple] = {}  # poll_id -> (session_id, question_index)
    
    def has_active_session(self) -> bool:
        """Check if there's an active live quiz session"""
        return self.active_session is not None and not self.active_session.is_completed
    
    def create_session(self, chapter: str, questions: List[dict], admin_id: int) -> LiveQuizSession:
        """Create a new live quiz session"""
        session_id = f"live_{int(datetime.now().timestamp())}"
        session = LiveQuizSession(session_id, chapter, questions, admin_id)
        self.active_session = session
        self.session_history.append(session_id)
        logger.info(f"Created live quiz session {session_id} for chapter: {chapter}")
        return session
    
    async def send_countdown_reminder(self, context: ContextTypes.DEFAULT_TYPE, 
                                     group_ids: List[int], chapter: str):
        """Send 5-minute countdown reminder to all groups and users"""
        reminder_message = f"""
╔═══════════════════════════════════╗
║   🔴 LIVE QUIZ STARTING SOON! 🔴  ║
╚═══════════════════════════════════╝

⏰ **COUNTDOWN: 5 MINUTES**

🎯 **Chapter:** {chapter}
📝 **Questions:** 20 MCQs
⏱️ **Timer:** 45 seconds per question
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

⏳ Quiz starts in **5 minutes**...

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
                                         stats_manager):
        """Wait 5 minutes then start the quiz in all groups"""
        try:
            # Wait 5 minutes (300 seconds)
            await asyncio.sleep(300)
            
            # Start the quiz
            await self.broadcast_quiz_start(
                context, session, group_ids, quiz_gen, 
                quiz_lock_manager, stats_manager
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
                                   stats_manager):
        """Start the quiz simultaneously in all groups"""
        session.is_running = True
        session.start_time = datetime.now()
        
        start_message = f"""
╔═══════════════════════════════════╗
║   🔴 LIVE QUIZ STARTING NOW! 🔴   ║
╚═══════════════════════════════════╝

📚 **Chapter:** {session.chapter}
⏱️ **45 seconds per question**
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
        await self.broadcast_questions(context, session, quiz_lock_manager)
    
    async def broadcast_questions(self, context: ContextTypes.DEFAULT_TYPE,
                                  session: LiveQuizSession,
                                  quiz_lock_manager):
        """Broadcast questions to all active groups with synchronized timing"""
        for idx, question in enumerate(session.questions):
            question_num = idx + 1
            
            # Broadcast this question to all active groups
            for group_id, group_state in session.group_states.items():
                if not group_state.active:
                    continue
                
                try:
                    # Send poll
                    poll_message = await context.bot.send_poll(
                        chat_id=group_id,
                        question=f"Q{question_num}/20: {question['question']}",
                        options=question['options'],
                        type='quiz',
                        correct_option_id=question['correct_option_index'],
                        is_anonymous=False,
                        open_period=self.question_duration
                    )
                    
                    poll_id = poll_message.poll.id
                    group_state.poll_ids.append(poll_id)
                    group_state.current_question_index = idx
                    
                    # Register poll in global map for easy lookup
                    self.poll_to_question_map[poll_id] = (session.session_id, idx, group_id)
                    
                    logger.info(f"Sent live quiz Q{question_num} to group {group_id}, poll_id: {poll_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to send question {question_num} to group {group_id}: {e}")
                    group_state.error_count += 1
                    if group_state.error_count >= 3:
                        session.deactivate_group(group_id)
            
            # Wait for question duration before next question
            if question_num < len(session.questions):
                await asyncio.sleep(self.question_duration + 2)  # +2 seconds buffer
        
        # All questions sent, wait a bit then finalize
        await asyncio.sleep(5)
        await self.finalize_session(context, session, quiz_lock_manager)
    
    async def finalize_session(self, context: ContextTypes.DEFAULT_TYPE,
                               session: LiveQuizSession,
                               quiz_lock_manager):
        """Finalize the session and send global leaderboard"""
        session.is_running = False
        session.is_completed = True
        session.end_time = datetime.now()
        
        # Mark unattempted questions for all participants
        for user_id in session.participants.keys():
            session.mark_unattempted(user_id, len(session.questions))
        
        # Generate and send global leaderboard
        leaderboard_message = self.generate_global_leaderboard(session)
        
        # Send to all groups
        for group_id, group_state in session.group_states.items():
            try:
                await context.bot.send_message(
                    chat_id=group_id,
                    text=leaderboard_message
                )
                
                # Release lock
                quiz_lock_manager.release_lock(group_id)
                
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Failed to send leaderboard to group {group_id}: {e}")
        
        logger.info(f"Live quiz session {session.session_id} completed with {len(session.participants)} participants")
        
        # Clean up poll mappings to avoid memory leaks
        polls_to_remove = [poll_id for poll_id, (sess_id, _, _) in self.poll_to_question_map.items() 
                          if sess_id == session.session_id]
        for poll_id in polls_to_remove:
            del self.poll_to_question_map[poll_id]
        
        logger.info(f"Cleaned up {len(polls_to_remove)} poll mappings for session {session.session_id}")
        
        # Clear active session
        self.active_session = None
    
    def generate_global_leaderboard(self, session: LiveQuizSession) -> str:
        """Generate beautifully formatted global leaderboard"""
        sorted_participants = session.get_sorted_participants()
        group_stats = session.get_group_stats()
        
        # Header
        leaderboard = f"""
╔═══════════════════════════════════╗
║   🏆 GLOBAL LIVE QUIZ RESULTS 🏆  ║
║      Chapter: {session.chapter[:20]}       ║
╚═══════════════════════════════════╝

📈 **Total Participants:** {len(session.participants)} students
🌍 **Groups Participated:** {len(group_stats)} groups
📚 **Total Questions:** {len(session.questions)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # Top participants
        medal_emojis = ["🥇", "🥈", "🥉"]
        
        for rank, participant in enumerate(sorted_participants[:50], 1):  # Top 50
            medal = medal_emojis[rank - 1] if rank <= 3 else f"🏅 #{rank}"
            
            username_display = f"@{participant.username}" if participant.username else participant.first_name
            
            leaderboard += f"""
{medal} **{username_display}**
   📊 Score: {participant.score:+d} marks
   ✅ Correct: {participant.correct}/{len(session.questions)} | ❌ Wrong: {participant.wrong} | ⏱️ Avg Time: {participant.total_time/max(participant.total_attempts, 1):.1f}s
   🏛️ From: {participant.group_title[:25]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # Footer
        if len(sorted_participants) > 50:
            leaderboard += f"\n... and {len(sorted_participants) - 50} more participants!\n\n"
        
        leaderboard += "\n🎉 Congratulations to all participants!\n\n【~@DrQuizRobot】"
        
        return leaderboard


# Global instance
live_quiz_coordinator = LiveQuizCoordinator()
