import logging
import random
import asyncio
import time
from functools import wraps
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, PollAnswerHandler, filters, ContextTypes
from bot.config import TELEGRAM_BOT_TOKEN, MIN_QUESTIONS, MAX_QUESTIONS, ADMIN_USER_IDS
from bot.quiz_generator import QuizGenerator
from bot.force_join import force_join_manager
from bot.stats_manager import stats_manager
from bot.admin_manager import AdminManager
from bot.welcome_manager import welcome_manager
from bot.language_manager import language_manager
from bot.song_lyrics import get_personalized_message_template
from bot.tagall_manager import tagall_manager
from bot.anonymous_verifier import anonymous_verifier
from bot.quiz_session_manager import quiz_session_manager
from bot.leaderboard_generator import generate_leaderboard_message, generate_quiz_complete_message

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

quiz_gen = QuizGenerator()
admin_manager = AdminManager(ADMIN_USER_IDS)

def admin_only(func):
    """Decorator to restrict command to admins only."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not admin_manager.is_admin(user_id):
            await update.message.reply_text("❌ This command is only available for admins.")
            return
        return await func(update, context)
    return wrapper

def bot_or_group_admin_only(func):
    """Decorator to restrict command to bot admins or group admins only."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        
        # Check if this is an anonymous admin (must check before accessing effective_user)
        if anonymous_verifier.is_anonymous_admin(update):
            # Send verification button
            command_name = update.message.text.split()[0] if update.message.text else "command"
            await anonymous_verifier.require_verification(
                update, context, command_name, func
            )
            return
        
        # Get user_id (safe to access now since we've handled anonymous case)
        if not update.effective_user:
            await update.message.reply_text("❌ Unable to identify user.")
            return
        
        user_id = update.effective_user.id
        
        # Check if user is bot admin
        if admin_manager.is_admin(user_id):
            return await func(update, context)
        
        # Check if command is in a group and user is group admin
        if chat.type in ['group', 'supergroup']:
            try:
                member = await context.bot.get_chat_member(chat.id, user_id)
                if member.status in ['creator', 'administrator']:
                    return await func(update, context)
            except:
                pass
        
        await update.message.reply_text("❌ This command is only available for bot admins or group admins.")
        return
    return wrapper

def check_force_join(func):
    """Decorator to check if user has joined required groups/channels."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Track user
        stats_manager.add_user(user_id)
        
        # Track group if message is from a group
        if update.effective_chat.type in ['group', 'supergroup']:
            stats_manager.add_group(update.effective_chat.id)
        
        # Skip check for admins
        if admin_manager.is_admin(user_id):
            return await func(update, context)
        
        # Check membership
        is_member, not_joined = await force_join_manager.check_user_membership(user_id, context)
        
        if not is_member:
            message = "⚠️ Please join the following groups/channels to use this bot:\n\n"
            for group in not_joined:
                message += f"📢 {group['title']}\n"
            
            keyboard = force_join_manager.create_join_buttons(not_joined)
            await update.message.reply_text(message, reply_markup=keyboard)
            return
        
        return await func(update, context)
    return wrapper

@check_force_join
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    welcome_message = """
🎓 Welcome to AUTO QUIZ CREATE BOT! 【~@DrQuizRobot】

I generate NEET UG Previous Year Questions (PYQs) and exam-standard MCQs from NCERT Class 11th and 12th textbooks.

📚 How to use:
/cquiz [chapter name] [number of questions]

📖 Examples:
/cquiz Human Physiology 5
/cquiz Thermodynamics 10
/cquiz Cell Biology 15

✅ Features:
• NEET UG PYQs (2015-2024)
• NEET-standard clickable quiz polls
• Questions from official NEET exam papers
• Interactive quiz format with instant feedback
• 4 options per question
• 1-20 questions per request

📝 Subjects Covered:
• Biology (Class 11 & 12)
• Physics (Class 11 & 12)
• Chemistry (Class 11 & 12)

Start creating your NEET PYQ quiz now! 🚀
"""
    await update.message.reply_text(welcome_message)

@check_force_join
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when the command /help is issued."""
    help_text = """
📖 AUTO QUIZ CREATE BOT - Help

Command Format:
/cquiz [chapter name] [number of questions]

Examples:
• /cquiz Human Physiology 5
• /cquiz Thermodynamics 10
• /cquiz Biomolecules 8
• /cquiz Chemical Bonding 12

Valid Inputs:
• Chapter: Any NCERT Class 11/12 chapter (Biology, Physics, Chemistry)
• Questions: 1-20 questions per quiz

Need help? Just type /start to see examples!
"""
    await update.message.reply_text(help_text)

@check_force_join
async def create_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /cquiz command to generate a quiz."""
    try:
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "❌ Invalid format!\n\n"
                "Usage: /cquiz [chapter name] [number of questions]\n"
                "Example: /cquiz Human Physiology 5"
            )
            return
        
        num_questions_str = context.args[-1]
        chapter_parts = context.args[:-1]
        chapter = ' '.join(chapter_parts)
        
        try:
            num_questions = int(num_questions_str)
        except ValueError:
            await update.message.reply_text(
                f"❌ Invalid number of questions: '{num_questions_str}'\n"
                "Please provide a number between 1 and 20."
            )
            return
        
        if num_questions < MIN_QUESTIONS or num_questions > MAX_QUESTIONS:
            await update.message.reply_text(
                f"❌ Number of questions must be between {MIN_QUESTIONS} and {MAX_QUESTIONS}.\n"
                f"You requested: {num_questions}"
            )
            return
        
        # Get language setting for this chat
        chat_id = update.effective_chat.id
        language = language_manager.get_language(chat_id)
        
        await update.message.reply_text(
            f"🔄 Generating {num_questions} NEET-level questions for '{chapter}'...\n"
            f"Please wait a moment... 【~@DrQuizRobot】"
        )
        
        logger.info(f"Generating quiz: chapter='{chapter}', questions={num_questions}, language={language}")
        questions = quiz_gen.generate_quiz(chapter, num_questions, language)
        
        if not questions:
            await update.message.reply_text(
                "❌ Failed to generate questions. Please try again with a different chapter name."
            )
            return
        
        for i, q in enumerate(questions, 1):
            try:
                # Ensure options are strings and properly formatted
                options = [str(opt).strip() for opt in q['options'][:4]]
                
                # Add watermark to question text
                question_text = f"{i}. {q['question']}\n\n【~@DrQuizRobot】"
                
                # Telegram quiz questions have a 300 character limit
                if len(question_text) > 300:
                    question_text = f"{i}. {q['question'][:270]}...\n\n【~@DrQuizRobot】"
                
                # Send the poll in quiz format
                await update.message.reply_poll(
                    question=question_text,
                    options=options,
                    type='quiz',
                    correct_option_id=int(q['correct_answer']),
                    is_anonymous=False,
                    explanation=q.get('explanation', '')[:200] if q.get('explanation') else None,
                )
                logger.info(f"Successfully sent quiz poll {i}/{len(questions)}")
                
            except Exception as e:
                logger.error(f"Error sending quiz poll {i}: {e}", exc_info=True)
                logger.error(f"Question data: {q}")
                # Fallback to text format only if poll fails
                formatted = quiz_gen.format_question_with_watermark(i, q)
                formatted += f"\n✅ Correct Answer: {chr(65 + q['correct_answer'])}) {q['options'][q['correct_answer']]}"
                await update.message.reply_text(formatted)
                logger.warning(f"Sent question {i} as text instead of poll")
        
        # Track quiz statistics
        stats_manager.record_quiz(len(questions))
        
        await update.message.reply_text(
            f"✅ Quiz complete! {len(questions)} questions sent.\n"
            f"Chapter: {chapter} 【~@DrQuizRobot】"
        )
        
    except ValueError as e:
        logger.error(f"Value error in create_quiz: {e}")
        await update.message.reply_text(
            "❌ Failed to generate quiz. Please check the chapter name and try again.\n"
            "Make sure it's a valid NCERT Class 11/12 chapter."
        )
    except Exception as e:
        logger.error(f"Error in create_quiz: {e}")
        await update.message.reply_text(
            "❌ An error occurred while generating the quiz. Please try again later."
        )

@check_force_join
async def timed_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /quiz command to start a timed quiz session with 20 questions."""
    try:
        chat_id = update.effective_chat.id
        is_private_chat = update.effective_chat.type == 'private'
        
        if quiz_session_manager.has_active_session(chat_id):
            await update.message.reply_text(
                "⚠️ A quiz is already running in this chat!\n\n"
                "Please wait for it to finish or use /stopquiz to cancel it.\n\n"
                "【~@DrQuizRobot】"
            )
            return
        
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "❌ Invalid format!\n\n"
                "Usage: /quiz [chapter name]\n\n"
                "Example: /quiz Human Physiology\n"
                "Example: /quiz Thermodynamics\n\n"
                "This will start a 20-question timed quiz with 45 seconds per question.\n\n"
                "【~@DrQuizRobot】"
            )
            return
        
        chapter = ' '.join(context.args)
        
        language = language_manager.get_language(chat_id)
        
        quiz_mode = "instant advance" if is_private_chat else "timer-based"
        await update.message.reply_text(
            f"🎯 Starting Timed Quiz Session!\n\n"
            f"📚 Chapter: {chapter}\n"
            f"📝 Questions: 20\n"
            f"⏱️ Time per question: 45 seconds\n"
            f"{'⚡ Instant advance after answering!' if is_private_chat else '🔄 Auto-advance after timer expires!'}\n"
            f"🏆 Leaderboard at the end!\n\n"
            f"⚡ Generating NEET PYQ & NCERT questions...\n\n"
            f"【~@DrQuizRobot】"
        )
        
        logger.info(f"Generating 20 questions for timed quiz: chapter='{chapter}', language={language}, mode={quiz_mode}")
        questions = quiz_gen.generate_quiz(chapter, 20, language)
        
        if not questions or len(questions) < 20:
            await update.message.reply_text(
                "❌ Failed to generate 20 questions. Please try again with a different chapter name.\n\n"
                "【~@DrQuizRobot】"
            )
            return
        
        session = quiz_session_manager.create_session(chat_id, chapter, questions, is_private_chat)
        
        await update.message.reply_text(
            "╔═══════════════════════════════╗\n"
            "║   🎮 **QUIZ STARTING NOW!** 🎮   ║\n"
            "╚═══════════════════════════════╝\n\n"
            "📢 Answer each question within 45 seconds!\n"
            "🔄 Questions will auto-advance after timer expires\n"
            "🏆 Your score will be tracked for the leaderboard!\n\n"
            "Good luck! 🍀\n\n"
            "【~@DrQuizRobot】"
        )
        
        await asyncio.sleep(2)
        
        await send_next_question(update, context, chat_id)
        
    except Exception as e:
        logger.error(f"Error in timed_quiz_command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred while starting the quiz. Please try again later.\n\n"
            "【~@DrQuizRobot】"
        )
        if quiz_session_manager.has_active_session(update.effective_chat.id):
            quiz_session_manager.end_session(update.effective_chat.id)

async def send_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Send the next question in the quiz session."""
    try:
        session = quiz_session_manager.get_session(chat_id)
        
        if not session or session.is_finished():
            return
        
        question_data = session.get_current_question()
        
        if not question_data:
            await finalize_quiz(update, context, chat_id)
            return
        
        question_num = session.current_question_index + 1
        
        question_text = f"Q{question_num}/20: {question_data['question']}\n\n【~@DrQuizRobot】"
        
        if len(question_text) > 300:
            question_text = f"Q{question_num}/20: {question_data['question'][:250]}...\n\n【~@DrQuizRobot】"
        
        options = [str(opt).strip() for opt in question_data['options'][:4]]
        
        message = await context.bot.send_poll(
            chat_id=chat_id,
            question=question_text,
            options=options,
            type='quiz',
            correct_option_id=int(question_data['correct_answer']),
            is_anonymous=False,
            open_period=45,
            explanation=question_data.get('explanation', '')[:200] if question_data.get('explanation') else None
        )
        
        session.start_question(message.poll.id)
        logger.info(f"Sent question {question_num}/20 for quiz in chat {chat_id}, poll_id={message.poll.id}")
        
        task = asyncio.create_task(auto_advance_question(update, context, chat_id, 47))
        session.auto_advance_task = task
        
    except Exception as e:
        logger.error(f"Error sending next question: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Error sending question. Ending quiz.\n\n【~@DrQuizRobot】"
        )
        quiz_session_manager.end_session(chat_id)

async def auto_advance_question(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, delay: int):
    """Auto-advance to next question after delay."""
    await asyncio.sleep(delay)
    
    session = quiz_session_manager.get_session(chat_id)
    
    if not session or not session.is_active:
        return
    
    has_more = session.next_question()
    
    if has_more:
        await send_next_question(update, context, chat_id)
    else:
        await finalize_quiz(update, context, chat_id)

async def finalize_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Finalize quiz and send leaderboard."""
    try:
        session = quiz_session_manager.get_session(chat_id)
        
        if not session:
            return
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=generate_quiz_complete_message(20)
        )
        
        await asyncio.sleep(2)
        
        leaderboard_data = session.get_leaderboard_data()
        leaderboard_message = generate_leaderboard_message(leaderboard_data, session.chapter, 20)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=leaderboard_message,
            parse_mode='Markdown'
        )
        
        logger.info(f"Quiz completed for chat {chat_id}, participants: {len(leaderboard_data)}")
        
        stats_manager.record_quiz(20)
        
        quiz_session_manager.end_session(chat_id)
        
    except Exception as e:
        logger.error(f"Error finalizing quiz: {e}", exc_info=True)
        quiz_session_manager.end_session(chat_id)

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle poll answers and track user scores."""
    try:
        poll_answer = update.poll_answer
        poll_id = poll_answer.poll_id
        user = poll_answer.user
        option_ids = poll_answer.option_ids
        
        if not option_ids:
            return
        
        option_id = option_ids[0]
        
        session = quiz_session_manager.get_session_by_poll(poll_id)
        
        if not session:
            return
        
        if session.question_start_time is None:
            return
        
        time_taken = time.time() - session.question_start_time
        
        user_name = user.first_name or user.username or f"User{user.id}"
        
        session.record_answer(user.id, user_name, option_id, time_taken)
        
        logger.info(f"Recorded answer from {user_name} (ID: {user.id}) for poll {poll_id}, option: {option_id}, time: {time_taken:.2f}s")
        
        if session.is_private_chat:
            if session.auto_advance_task and not session.auto_advance_task.done():
                session.auto_advance_task.cancel()
                logger.info(f"Cancelled auto-advance for private chat {session.chat_id}, advancing immediately")
            
            has_more = session.next_question()
            
            if has_more:
                await send_next_question(update, context, session.chat_id)
            else:
                await finalize_quiz(update, context, session.chat_id)
        
    except Exception as e:
        logger.error(f"Error handling poll answer: {e}", exc_info=True)

@check_force_join
async def stop_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop the current quiz session."""
    chat_id = update.effective_chat.id
    
    if not quiz_session_manager.has_active_session(chat_id):
        await update.message.reply_text(
            "❌ No active quiz session in this chat.\n\n"
            "【~@DrQuizRobot】"
        )
        return
    
    quiz_session_manager.end_session(chat_id)
    
    await update.message.reply_text(
        "🛑 Quiz session stopped!\n\n"
        "You can start a new quiz anytime with /quiz [chapter name]\n\n"
        "【~@DrQuizRobot】"
    )

@admin_only
async def fjoin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to add a group/channel to force join list."""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ Invalid format!\n\n"
            "Usage:\n"
            "/fjoin @username (for public channels)\n"
            "/fjoin -1001234567890 (numeric chat ID)\n"
            "/fjoin https://t.me/publicchannel (public link)\n"
            "/fjoin https://t.me/+PrivateInviteCode -1001234567890 (private invite + chat ID)\n\n"
            "For private groups/channels:\n"
            "1. Get the invite link\n"
            "2. Get the chat ID (forward a message to @userinfobot)\n"
            "3. Use both: /fjoin <invite_link> <chat_id>"
        )
        return
    
    identifier = context.args[0]
    chat_id_provided = context.args[1] if len(context.args) > 1 else None
    
    chat_id = None
    chat_title = None
    invite_link = None
    
    # Handle private invite links (https://t.me/+xxxx)
    if identifier.startswith('https://t.me/+') or identifier.startswith('https://t.me/joinchat/'):
        if not chat_id_provided:
            await update.message.reply_text(
                "❌ For private invite links, you must also provide the chat ID!\n\n"
                "Usage: /fjoin <invite_link> <chat_id>\n\n"
                "Example: /fjoin https://t.me/+AbCdEf123 -1001234567890\n\n"
                "To get the chat ID:\n"
                "1. Forward any message from the group/channel to @userinfobot\n"
                "2. It will show you the chat ID"
            )
            return
        
        # Use provided chat ID
        try:
            chat = await context.bot.get_chat(chat_id_provided)
            chat_id = str(chat.id)
            chat_title = chat.title or "Private Group/Channel"
            invite_link = identifier
        except Exception as e:
            await update.message.reply_text(
                f"❌ Cannot access chat with ID {chat_id_provided}\n\n"
                f"Make sure:\n"
                f"• The bot is a member/admin of the group/channel\n"
                f"• The chat ID is correct\n\n"
                f"Error: {e}"
            )
            return
    else:
        # Try to get chat information for public channels or numeric IDs
        try:
            if identifier.startswith('@'):
                chat = await context.bot.get_chat(identifier)
            elif identifier.startswith('https://t.me/'):
                username = identifier.replace('https://t.me/', '').split('?')[0]
                if username.startswith('+'):
                    await update.message.reply_text(
                        "❌ Private invite link detected!\n\n"
                        "Please provide both the invite link AND chat ID:\n"
                        "/fjoin <invite_link> <chat_id>"
                    )
                    return
                chat = await context.bot.get_chat(f'@{username}')
            else:
                # Numeric chat ID
                chat = await context.bot.get_chat(identifier)
            
            chat_id = str(chat.id)
            chat_title = chat.title or chat.username or "Unknown"
            
            # Generate invite link
            try:
                invite_link = await context.bot.export_chat_invite_link(chat_id)
            except Exception as export_error:
                logger.warning(f"Cannot export invite link for {chat_id}: {export_error}")
                # Use the provided link or create one for public channels
                if identifier.startswith('https://t.me/'):
                    invite_link = identifier
                elif identifier.startswith('@'):
                    invite_link = f"https://t.me/{identifier[1:]}"
                else:
                    await update.message.reply_text(
                        f"❌ Cannot generate invite link!\n\n"
                        f"The bot needs 'Invite Users' permission OR you must provide:\n"
                        f"/fjoin <invite_link> {chat_id}\n\n"
                        f"Error: {export_error}"
                    )
                    return
        
        except Exception as e:
            logger.error(f"Error getting chat info: {e}")
            await update.message.reply_text(
                f"❌ Cannot access chat: {identifier}\n\n"
                f"Make sure:\n"
                f"• The bot is admin in the group/channel\n"
                f"• The username/ID is correct\n\n"
                f"For private groups, use:\n"
                f"/fjoin <invite_link> <chat_id>"
            )
            return
    
    # Add to force join list
    if chat_id and invite_link:
        success = force_join_manager.add_force_join(chat_id, invite_link, chat_title)
        
        if success:
            current_groups = force_join_manager.get_force_join_groups()
            await update.message.reply_text(
                f"✅ Successfully added to force join list!\n\n"
                f"📢 {chat_title}\n"
                f"🆔 Chat ID: {chat_id}\n"
                f"🔗 {invite_link}\n\n"
                f"Total force join groups: {len(current_groups)}/5"
            )
        else:
            await update.message.reply_text(
                "❌ Failed to add group/channel!\n\n"
                "Possible reasons:\n"
                "• Already in force join list\n"
                "• Maximum limit (5) reached"
            )
    else:
        await update.message.reply_text("❌ Missing required information (chat_id or invite_link)")

@admin_only
async def removefjoin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to remove a group/channel from force join list."""
    if not context.args or len(context.args) < 1:
        current_groups = force_join_manager.get_force_join_groups()
        if not current_groups:
            await update.message.reply_text("📭 No groups in force join list.")
            return
        
        message = "📋 Current force join groups:\n\n"
        for i, group in enumerate(current_groups, 1):
            message += f"{i}. {group['title']}\n"
            message += f"   ID: {group['chat_id']}\n"
            message += f"   Link: {group['invite_link']}\n\n"
        
        message += "Usage: /removefjoin @username or chat_id or invite_link"
        await update.message.reply_text(message)
        return
    
    identifier = context.args[0]
    
    # Try to remove by identifier or by resolving chat ID
    success = force_join_manager.remove_force_join(identifier)
    
    if not success:
        try:
            # Try to resolve chat ID
            if identifier.startswith('@'):
                chat = await context.bot.get_chat(identifier)
            elif identifier.startswith('https://t.me/'):
                username = identifier.replace('https://t.me/', '').split('?')[0]
                chat = await context.bot.get_chat(f'@{username}')
            else:
                chat = await context.bot.get_chat(identifier)
            
            chat_id = str(chat.id)
            success = force_join_manager.remove_force_join(chat_id)
        except:
            pass
    
    if success:
        current_groups = force_join_manager.get_force_join_groups()
        await update.message.reply_text(
            f"✅ Successfully removed from force join list!\n\n"
            f"Remaining groups: {len(current_groups)}/5"
        )
    else:
        await update.message.reply_text(
            "❌ Group/channel not found in force join list!\n\n"
            "Use /removefjoin without arguments to see current list."
        )

async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send user their Telegram user ID."""
    user_id = update.effective_user.id
    username = update.effective_user.username or "No username"
    first_name = update.effective_user.first_name or ""
    
    await update.message.reply_text(
        f"👤 Your Telegram Information:\n\n"
        f"🆔 User ID: `{user_id}`\n"
        f"👤 Name: {first_name}\n"
        f"📧 Username: @{username}\n\n"
        f"Use this ID to configure bot admins in config.py"
    )

@admin_only
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed bot statistics (admin only)."""
    stats = stats_manager.get_stats()
    
    # Calculate uptime
    start_time = datetime.fromisoformat(stats['start_time'])
    uptime = datetime.now() - start_time
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    message = f"""
📊 **BOT STATISTICS** 【~@DrQuizRobot】

👥 **Users & Groups:**
• Total Users: {stats['total_users']}
• Total Groups: {stats['total_groups']}

📚 **Quiz Statistics:**
• Total Quizzes Generated: {stats['total_quizzes']}
• Total Questions Sent: {stats['total_questions']}

⏱️ **Uptime:**
• Days: {days}
• Hours: {hours}
• Minutes: {minutes}

👨‍💼 **Admins:**
• Total Admins: {len(admin_manager.get_all_admins())}

📢 **Force Join Groups:**
• Active: {len(force_join_manager.get_force_join_groups())}/5

📅 **Started:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    await update.message.reply_text(message)

@admin_only
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast a message to all users and groups (admin only)."""
    # Check if this is a reply to a message
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Please reply to a message/media you want to broadcast!\n\n"
            "Usage: Reply to any message (text/photo/video/poll/etc.) with /broadcast"
        )
        return
    
    replied_msg = update.message.reply_to_message
    stats = stats_manager.get_stats()
    
    total_users = stats['total_users']
    total_groups = stats['total_groups']
    total_targets = total_users + total_groups
    
    await update.message.reply_text(
        f"📢 Starting broadcast...\n\n"
        f"Targets: {total_users} users + {total_groups} groups = {total_targets} total\n\n"
        f"This may take a few minutes..."
    )
    
    success_count = 0
    failed_count = 0
    blocked_count = 0
    
    # Broadcast to all users
    for user_id in stats['users_list']:
        try:
            # Forward the message
            await replied_msg.copy(chat_id=user_id)
            success_count += 1
        except Exception as e:
            error_msg = str(e).lower()
            if 'blocked' in error_msg or 'deactivated' in error_msg:
                blocked_count += 1
            else:
                failed_count += 1
            logger.warning(f"Failed to send broadcast to user {user_id}: {e}")
    
    # Broadcast to all groups
    for group_id in stats['groups_list']:
        try:
            await replied_msg.copy(chat_id=group_id)
            success_count += 1
        except Exception as e:
            failed_count += 1
            logger.warning(f"Failed to send broadcast to group {group_id}: {e}")
    
    # Send report
    await update.message.reply_text(
        f"✅ Broadcast Complete!\n\n"
        f"📊 Results:\n"
        f"✅ Successful: {success_count}\n"
        f"❌ Failed: {failed_count}\n"
        f"🚫 Blocked/Deleted: {blocked_count}\n"
        f"📈 Total Attempted: {total_targets}"
    )

@admin_only
async def promote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Promote a user to admin (admin only)."""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ Invalid format!\n\n"
            "Usage: /promote <user_id>\n\n"
            "Example: /promote 123456789\n\n"
            "Get user ID using /myid command or @userinfobot"
        )
        return
    
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID! Must be a number.")
        return
    
    # Try to get user info
    try:
        user = await context.bot.get_chat(user_id)
        user_name = user.first_name or user.username or f"User {user_id}"
    except:
        user_name = f"User {user_id}"
    
    # Add to admins
    if admin_manager.add_admin(user_id):
        await update.message.reply_text(
            f"✅ Successfully promoted to admin!\n\n"
            f"👤 {user_name}\n"
            f"🆔 ID: {user_id}\n\n"
            f"Total admins: {len(admin_manager.get_all_admins())}"
        )
    else:
        await update.message.reply_text(
            f"ℹ️ User is already an admin!\n\n"
            f"👤 {user_name}\n"
            f"🆔 ID: {user_id}"
        )

@admin_only
async def remove_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove admin privileges from a user (admin only)."""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ Invalid format!\n\n"
            "Usage: /remove <user_id>\n\n"
            "Example: /remove 123456789\n\n"
            "Note: Permanent admins cannot be removed."
        )
        return
    
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID! Must be a number.")
        return
    
    # Try to get user info
    try:
        user = await context.bot.get_chat(user_id)
        user_name = user.first_name or user.username or f"User {user_id}"
    except:
        user_name = f"User {user_id}"
    
    # Check if permanent admin
    if admin_manager.is_permanent_admin(user_id):
        await update.message.reply_text(
            f"❌ Cannot remove permanent admin!\n\n"
            f"👤 {user_name}\n"
            f"🆔 ID: {user_id}\n\n"
            f"Permanent admins are set in config.py"
        )
        return
    
    # Remove from admins
    if admin_manager.remove_admin(user_id):
        await update.message.reply_text(
            f"✅ Successfully removed admin privileges!\n\n"
            f"👤 {user_name}\n"
            f"🆔 ID: {user_id}\n\n"
            f"Remaining admins: {len(admin_manager.get_all_admins())}"
        )
    else:
        await update.message.reply_text(
            f"ℹ️ User is not an admin!\n\n"
            f"👤 {user_name}\n"
            f"🆔 ID: {user_id}"
        )

@admin_only
async def adminlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all bot admins (admin only)."""
    all_admins = admin_manager.get_all_admins()
    
    if not all_admins:
        await update.message.reply_text("📭 No admins configured.")
        return
    
    message = "👥 **BOT ADMINS LIST** 【~@DrQuizRobot】\n\n"
    
    for i, admin_id in enumerate(all_admins, 1):
        is_permanent = admin_manager.is_permanent_admin(admin_id)
        admin_type = "🔒 Permanent" if is_permanent else "👤 Dynamic"
        
        # Try to get admin info
        try:
            user = await context.bot.get_chat(admin_id)
            name = user.first_name or "Unknown"
            username = f"@{user.username}" if user.username else "No username"
            
            message += f"{i}. {admin_type}\n"
            message += f"   👤 Name: {name}\n"
            message += f"   📧 Username: {username}\n"
            message += f"   🆔 ID: `{admin_id}`\n\n"
        except Exception as e:
            message += f"{i}. {admin_type}\n"
            message += f"   🆔 ID: `{admin_id}`\n"
            message += f"   ⚠️ Cannot fetch info\n\n"
    
    message += f"📊 Total Admins: {len(all_admins)}"
    
    await update.message.reply_text(message)

@bot_or_group_admin_only
async def welcomeon_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enable welcome messages in a group (bot admin or group admin only)."""
    chat = update.effective_chat
    
    # Check if command is in a group
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text(
            "❌ This command can only be used in groups!"
        )
        return
    
    # Enable welcome for this group
    if welcome_manager.enable_welcome(chat.id):
        await update.message.reply_text(
            f"✅ Welcome messages enabled for {chat.title}!\n\n"
            f"New members will be greeted with a warm welcome and shayari. 🎉"
        )
    else:
        await update.message.reply_text(
            f"ℹ️ Welcome messages are already enabled for {chat.title}."
        )

@bot_or_group_admin_only
async def welcomeoff_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disable welcome messages in a group (bot admin or group admin only)."""
    chat = update.effective_chat
    
    # Check if command is in a group
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text(
            "❌ This command can only be used in groups!"
        )
        return
    
    # Disable welcome for this group
    if welcome_manager.disable_welcome(chat.id):
        await update.message.reply_text(
            f"✅ Welcome messages disabled for {chat.title}!\n\n"
            f"New members will not receive welcome messages."
        )
    else:
        await update.message.reply_text(
            f"ℹ️ Welcome messages are already disabled for {chat.title}."
        )

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome new members to the group."""
    chat = update.effective_chat
    
    # Check if welcome is enabled for this group
    if not welcome_manager.is_welcome_enabled(chat.id):
        return
    
    # Get new members
    new_members = update.message.new_chat_members
    
    for member in new_members:
        # Skip if the new member is a bot
        if member.is_bot:
            continue
        
        # Get member name
        member_name = member.first_name or member.username or "Friend"
        
        # Get random shayari
        shayari = welcome_manager.get_random_shayari()
        
        # Create welcome message
        welcome_message = (
            f"🎉 Welcome {member_name} to {chat.title}! 🎉\n\n"
            f"{shayari}\n\n"
            f"【~@DrQuizRobot】"
        )
        
        await update.message.reply_text(welcome_message)

@bot_or_group_admin_only
async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set quiz language preference (bot admin or group admin only)."""
    chat = update.effective_chat
    current_language = language_manager.get_language(chat.id)
    
    # Create inline keyboard with language options
    keyboard = [
        [
            InlineKeyboardButton("🇮🇳 हिन्दी (Hindi)", callback_data="lang_hindi"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_english")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_lang_text = "Hindi (हिन्दी)" if current_language == 'hindi' else "English"
    
    await update.message.reply_text(
        f"🌐 **Language Selection** 【~@DrQuizRobot】\n\n"
        f"Current Language: {current_lang_text}\n\n"
        f"Choose your preferred language for quiz questions:\n"
        f"👇 Select a language below",
        reply_markup=reply_markup
    )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection callback."""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Check if user is bot admin or group admin
    is_authorized = False
    
    # Check bot admin
    if admin_manager.is_admin(user_id):
        is_authorized = True
    # Check group admin
    elif update.effective_chat.type in ['group', 'supergroup']:
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status in ['creator', 'administrator']:
                is_authorized = True
        except:
            pass
    
    if not is_authorized:
        await query.edit_message_text(
            "❌ Only bot admins or group admins can change language settings."
        )
        return
    
    # Extract language from callback data
    if query.data == "lang_hindi":
        language = "hindi"
        language_name = "Hindi (हिन्दी)"
        language_emoji = "🇮🇳"
    elif query.data == "lang_english":
        language = "english"
        language_name = "English"
        language_emoji = "🇬🇧"
    else:
        await query.edit_message_text("❌ Invalid language selection.")
        return
    
    # Set language preference
    language_manager.set_language(chat_id, language)
    
    chat_type = "group" if update.effective_chat.type in ['group', 'supergroup'] else "chat"
    
    await query.edit_message_text(
        f"✅ Language Updated! {language_emoji}\n\n"
        f"Language set to: **{language_name}**\n\n"
        f"All quiz questions in this {chat_type} will now be generated in {language_name}.\n\n"
        f"【~@DrQuizRobot】"
    )

async def tagall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tag all group members with personalized fun messages."""
    chat = update.effective_chat
    user_id = update.effective_user.id
    
    # Check if command is in a group
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text(
            "❌ This command can only be used in groups!"
        )
        return
    
    # Check if user is bot admin
    is_bot_admin = admin_manager.is_admin(user_id)
    
    # Check if user is group admin
    is_group_admin = False
    try:
        member = await context.bot.get_chat_member(chat.id, user_id)
        if member.status in ['creator', 'administrator']:
            is_group_admin = True
    except:
        pass
    
    # Check permission using tagall_manager
    if not tagall_manager.can_use_tagall(chat.id, user_id, is_bot_admin, is_group_admin):
        permission_type = tagall_manager.get_permission(chat.id)
        if permission_type == 'admin':
            await update.message.reply_text(
                "❌ Only admins can use this command!\n\n"
                "Group admins can change this with /allowtagall user"
            )
        else:
            await update.message.reply_text(
                "❌ You don't have permission to use this command."
            )
        return
    
    try:
        await update.message.reply_text(
            "🎯 Starting to tag all members with fun personalized messages...\n\n"
            "Please wait... 【~@DrQuizRobot】"
        )
        
        # Get all chat administrators (due to Telegram API limitations, we can only get admins)
        administrators = await context.bot.get_chat_administrators(chat.id)
        
        # Collect all members (excluding bots and anonymous)
        members_to_tag = []
        for admin in administrators:
            # Skip bots
            if admin.user.is_bot:
                continue
            
            # Skip anonymous admins  
            if hasattr(admin, 'is_anonymous') and admin.is_anonymous:
                continue
                
            members_to_tag.append(admin.user)
        
        # Track tagged users
        tagged_count = 0
        failed_count = 0
        
        # Tag each member with personalized message
        for member in members_to_tag:
            try:
                # Get user's first name
                user_first_name = member.first_name
                
                # Create mention link
                user_mention = f"[{user_first_name}](tg://user?id={member.id})"
                
                # Get personalized message template from helper function
                message_template = get_personalized_message_template()
                
                # Replace {name} with mention
                message = message_template.replace("{name}", user_mention)
                message += f"\n\n【~@DrQuizRobot】"
                
                await update.message.reply_text(
                    message,
                    parse_mode='Markdown'
                )
                tagged_count += 1
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to tag user {admin.user.id}: {e}")
        
        # Try to get recent members from chat (limited by Telegram API)
        # Note: Full member list requires chat admin permissions and may not work for large groups
        try:
            # For smaller groups, we can try to get chat members
            # This is limited and may not work for all groups
            chat_member_count = await context.bot.get_chat_member_count(chat.id)
            
            await update.message.reply_text(
                f"✅ Tagging Complete! 【~@DrQuizRobot】\n\n"
                f"📊 Summary:\n"
                f"✅ Tagged: {tagged_count} members\n"
                f"📈 Total Members: {chat_member_count}\n\n"
                f"💡 Note: Due to Telegram limitations, only administrators and recently active members can be tagged.\n\n"
                f"【~@DrQuizRobot】"
            )
        except:
            await update.message.reply_text(
                f"✅ Tagging Complete! 【~@DrQuizRobot】\n\n"
                f"📊 Tagged: {tagged_count} members\n"
                f"❌ Failed: {failed_count}\n\n"
                f"【~@DrQuizRobot】"
            )
            
    except Exception as e:
        logger.error(f"Error in tagall command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while tagging members. "
            "Please make sure the bot has necessary permissions."
        )

@bot_or_group_admin_only
async def allowtagall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set who can use /tagall command (bot admin or group admin only)."""
    chat = update.effective_chat
    
    # Check if command is in a group
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text(
            "❌ This command can only be used in groups!"
        )
        return
    
    # Check arguments
    if not context.args or len(context.args) < 1:
        current_permission = tagall_manager.get_permission(chat.id)
        permission_text = "All Users" if current_permission == 'user' else "Admins Only"
        
        await update.message.reply_text(
            f"⚙️ **TagAll Permission Settings** 【~@DrQuizRobot】\n\n"
            f"Current Setting: **{permission_text}**\n\n"
            f"Usage:\n"
            f"• /allowtagall user - Allow all members to use /tagall\n"
            f"• /allowtagall admin - Allow only admins to use /tagall\n\n"
            f"Example: /allowtagall user"
        )
        return
    
    permission_type = context.args[0].lower()
    
    if permission_type not in ['user', 'admin']:
        await update.message.reply_text(
            "❌ Invalid option!\n\n"
            "Please use:\n"
            "• /allowtagall user - Allow all members\n"
            "• /allowtagall admin - Allow only admins"
        )
        return
    
    # Set permission
    tagall_manager.set_permission(chat.id, permission_type)
    
    if permission_type == 'user':
        await update.message.reply_text(
            f"✅ Permission Updated! 【~@DrQuizRobot】\n\n"
            f"📢 All members of **{chat.title}** can now use /tagall command.\n\n"
            f"Everyone can tag members with beautiful messages! 🎉"
        )
    else:
        await update.message.reply_text(
            f"✅ Permission Updated! 【~@DrQuizRobot】\n\n"
            f"🔒 Only admins of **{chat.title}** can use /tagall command.\n\n"
            f"Bot admins and group admins have access. 👮"
        )

async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback when user clicks 'I Joined - Check Again' button."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Check membership
    is_member, not_joined = await force_join_manager.check_user_membership(user_id, context)
    
    if is_member:
        await query.edit_message_text(
            "✅ Great! You've joined all required groups/channels.\n\n"
            "You can now use the bot. Send /start to begin! 🚀"
        )
    else:
        message = "⚠️ You still need to join the following groups/channels:\n\n"
        for group in not_joined:
            message += f"📢 {group['title']}\n"
        
        keyboard = force_join_manager.create_join_buttons(not_joined)
        await query.edit_message_text(message, reply_markup=keyboard)

async def anonymous_verification_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback when anonymous admin clicks verification button."""
    query = update.callback_query
    
    if not query.data or not query.data.startswith("verify:"):
        await query.answer("❌ Invalid verification token!", show_alert=True)
        return
    
    token = query.data.split(":", 1)[1]
    user_id = update.effective_user.id
    
    await anonymous_verifier.verify_and_execute(
        query=query,
        user_id=user_id,
        token=token,
        bot=context.bot
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # User commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cquiz", create_quiz))
    application.add_handler(CommandHandler("quiz", timed_quiz_command))
    application.add_handler(CommandHandler("stopquiz", stop_quiz_command))
    application.add_handler(CommandHandler("myid", myid_command))
    
    # Admin commands
    application.add_handler(CommandHandler("fjoin", fjoin_command))
    application.add_handler(CommandHandler("removefjoin", removefjoin_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("promote", promote_command))
    application.add_handler(CommandHandler("remove", remove_admin_command))
    application.add_handler(CommandHandler("adminlist", adminlist_command))
    
    # Welcome commands (bot admin or group admin)
    application.add_handler(CommandHandler("welcomeon", welcomeon_command))
    application.add_handler(CommandHandler("welcomeoff", welcomeoff_command))
    
    # Language command (bot admin or group admin)
    application.add_handler(CommandHandler("language", language_command))
    
    # Tag all commands (bot admin or group admin)
    application.add_handler(CommandHandler("tagall", tagall_command))
    application.add_handler(CommandHandler("allowtagall", allowtagall_command))
    
    # New member handler
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    
    # Poll answer handler for timed quiz
    application.add_handler(PollAnswerHandler(handle_poll_answer))
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(anonymous_verification_callback, pattern="^verify:"))
    application.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    application.add_handler(CallbackQueryHandler(check_membership_callback, pattern="^check_membership$"))
    
    application.add_error_handler(error_handler)
    
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
