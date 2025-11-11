import logging
import random
import asyncio
import time
import os
from functools import wraps
from datetime import datetime, time as dt_time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, PollAnswerHandler, filters, ContextTypes
from bot.config import TELEGRAM_BOT_TOKEN, MIN_QUESTIONS, MAX_QUESTIONS, ADMIN_USER_IDS
from aiohttp import web
from bot.quiz_generator import QuizGenerator
from bot.force_join import force_join_manager
from bot.stats_manager import stats_manager
from bot.admin_manager import AdminManager
from bot.welcome_manager import welcome_manager
from bot.language_manager import language_manager
from bot.song_lyrics import get_personalized_message_template, get_tagall_question
from bot.tagall_manager import tagall_manager
from bot.anonymous_verifier import anonymous_verifier
from bot.quiz_session_manager import quiz_session_manager
from bot.leaderboard_generator import generate_leaderboard_message, generate_quiz_complete_message
from bot.good_morning_manager import good_morning_manager
from bot.quiz_lock_manager import quiz_lock_manager
from bot.live_quiz_manager import live_quiz_coordinator
from bot.database import db_pool, QuizSessionRepository

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
        
        # Check if this is a verified anonymous admin execution
        # If so, use the verified user instead of checking again
        if context.user_data.get('verified_user_id'):
            user_id = context.user_data['verified_user_id']
            # Clear the verification data after use
            context.user_data.pop('verified_user_id', None)
            context.user_data.pop('verified_user', None)
            
            # User is already verified as admin, execute the command
            return await func(update, context)
        
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

def group_admin_only(func):
    """Decorator: In groups, only admins can use. In private chats, anyone can use."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        
        # In private chats, allow everyone
        if chat.type == 'private':
            return await func(update, context)
        
        # In groups/supergroups, check admin permissions
        if chat.type in ['group', 'supergroup']:
            # Check if this is a verified anonymous admin execution
            if context.user_data.get('verified_user_id'):
                user_id = context.user_data['verified_user_id']
                # Clear the verification data after use
                context.user_data.pop('verified_user_id', None)
                context.user_data.pop('verified_user', None)
                
                # User is already verified as admin, execute the command
                return await func(update, context)
            
            # Check if this is an anonymous admin
            if anonymous_verifier.is_anonymous_admin(update):
                # Send verification button
                command_name = update.message.text.split()[0] if update.message.text else "command"
                await anonymous_verifier.require_verification(
                    update, context, command_name, func
                )
                return
            
            # Get user_id
            if not update.effective_user:
                await update.message.reply_text("❌ Unable to identify user.")
                return
            
            user_id = update.effective_user.id
            
            # Check if user is bot admin
            if admin_manager.is_admin(user_id):
                return await func(update, context)
            
            # Check if user is group admin
            try:
                member = await context.bot.get_chat_member(chat.id, user_id)
                if member.status in ['creator', 'administrator']:
                    return await func(update, context)
            except:
                pass
            
            await update.message.reply_text("❌ This command is only available for group admins in groups.")
            return
        
        # Default: execute the function
        return await func(update, context)
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
╔══════════════════════════╗
║ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ ㅤㅤ  ❣️
║ ㅤㅤ✨Welcome Toㅤㅤㅤㅤㅤㅤㅤㅤㅤ ㅤ❣️
║ㅤ   ㅤㅤㅤ𝙉𝙀𝙀𝙏 𝙌𝙐𝙄𝙕𝙕𝙄𝙉𝙂 𝘽𝙊𝙏📊✨️   ㅤ❣️
║ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ ㅤㅤㅤㅤㅤ  ㅤ❣️
╚══════════════════════════╝

🎯 **Your Personal NEET Preparation Partner!**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌅 **Start Your Day Right!**
Wake up to motivating **Good Morning wishes** that keep you energized and focused on your NEET goals! 💪

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 **Smart Quiz System**

🔹 **Instant Quizzes** - Create custom quizzes anytime
   • 1-20 questions per session
   • Any NCERT chapter from Class 11 & 12
   
🔹 **Timer Challenges** - Test yourself under pressure!
   • 20 questions with customizable timer ⏱️
   • Choose: 15s, 30s, 45s, or 60s per question
   • Real exam simulation
   • Leaderboard rankings 🏆

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎓 **Premium Question Bank**

✅ **NEET Previous Year Questions (2015-2024)**
✅ **NCERT-based MCQs** - Physics, Chemistry, Biology
✅ **Detailed Explanations** for every answer
✅ **Interactive Quiz Polls** - Click & learn!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **Ask Anything, Anytime!**

Got doubts? Use **/explain** command to get:
   • Detailed AI-powered explanations 🤖
   • Step-by-step solutions 📝
   • Concept clarity on any topic 💭
   
Reply to any quiz with /explain for instant answers!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👋 **Group Features**

🎉 Auto **welcome messages** for new members
📢 Keep your study group active & engaged
🤝 Perfect for collaborative learning

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 **Multiple Languages** | 🎯 **NEET Pattern** | ⚡ **Instant Results**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📖 **Need Help?** Type /help to explore all commands

🚀 **Ready to ace NEET?** Start your first quiz now!

【~@DrQuizRobot】
"""
    
    keyboard = [
        [InlineKeyboardButton("➕ Add Me To Your Group", url="https://t.me/DrQuizRobot?startgroup=true")],
        [
            InlineKeyboardButton("👨‍💻 Meet the Developer", url="https://t.me/Aman_personalBot"),
            InlineKeyboardButton("📢 Get Bot Updates", url="https://t.me/DrQuizRobotUpdates")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

@check_force_join
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when the command /help is issued."""
    help_text = """
╔═══════════════════════════════╗
║   📚 **NEET QUIZZING BOT**   ║
║         【~@DrQuizRobot】        ║
╚═══════════════════════════════╝

🎯 **Your Ultimate NEET Preparation Companion!**

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 **QUIZ COMMANDS**

🔹 `/cquiz [chapter] [number]`
   Create instant quiz with custom questions
   • Range: 1-20 questions
   • Format: Interactive quiz polls
   • Example: `/cquiz Human Physiology 5`

🔹 `/quiz [chapter]`
   Start 20-question timed quiz session
   • Choose your time: 15s, 30s, 45s, or 60s per question
   • Auto-advance: Questions move automatically
   • Leaderboard: Rankings at the end
   • Example: `/quiz Thermodynamics`

🔹 `/end`
   End timer quiz early and show leaderboard
   • Shows current standings
   • Displays your score
   • Great for practice sessions

🔹 `/stopquiz`
   Stop quiz without showing leaderboard
   • Immediately cancels quiz
   • No score recording
   • Start fresh anytime

🔹 `/explain [question/topic]`
   Get detailed AI-powered explanations
   • Ask about any concept
   • Reply to quiz questions for explanation
   • Example: `/explain What is photosynthesis?`
   • Or reply to any poll with `/explain`

━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️ **SETTINGS & CUSTOMIZATION**

🌐 `/language`
   Switch quiz language (Hindi/English)
   • Questions in your preferred language
   • Explanations in same language
   • Saves per group/chat preference

━━━━━━━━━━━━━━━━━━━━━━━━━━━

👥 **GROUP MANAGEMENT COMMANDS**

🔹 `/welcomeon` - Configure welcome messages
   • Customize group welcome text
   • Auto-greet new members
   • Admin/Group Admin only

🔹 `/welcomeoff` - Disable welcome messages
   • Turn off auto-greeting
   • Admin/Group Admin only

🔹 `/tagall [message]` - Tag all members
   • Notify everyone in group
   • Great for announcements
   • Permission-based access

🔹 `/allowtagall user` - Grant users to /tagall access
   • Admin/Group Admin only

🔹 `/allowtagall admin` - only admin has /tagall access
   • Admin/Group Admin only

🔹 `/myid` - user can check thir Info.
   • works in all groups
   • Customizable message
   • work in Bot also

🔹 `/developer` - Meet The Bot Developer 
   • Contact With Developer 
   • work in group as well in bot also
   
🔹️ `/botsupport` - Get Support From Admin
   • Get support from admins or developer 
   • work in groups as well bot also

🔹️ '/help' - Know About All the Bot commands 
   • Know how the bot works.
   • how the commands work
   
🔹️ '/donate' - Donate to the Support
   • Support The bot and the community 

━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 **NEET SCORING PATTERN**

✅ Correct Answer: **+4 marks**
❌ Wrong Answer: **-1 mark**
⚪ Not Attempted: **0 marks**

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 **SUBJECTS COVERED**

🧬 Biology (Class 11 & 12)
⚛️ Physics (Class 11 & 12)
🧪 Chemistry (Class 11 & 12)

✨ All from NCERT textbooks & NEET PYQs (2015-2024)

━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **QUICK TIPS**

• Questions are from authentic NEET papers
• All quizzes follow NEET exam pattern
• Interactive polls for better engagement
• Instant feedback on answers
• Perfect for group study sessions

━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆘 Need Support? Use /botsupport
📢 Stay Updated: @DrQuizRobotUpdates
👨‍💻 Developer: @Aman_personalBot

━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 **Start Your NEET Journey Today!**
Type /start to begin creating quizzes!

【~@DrQuizRobot】
"""
    await update.message.reply_text(help_text)

@check_force_join
async def botsupport_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send bot support message with button to contact developer."""
    support_message = """
🆘 **Need Help with the Bot?**

Having issues or questions about NEET Quizzing Bot?

Our developer is here to help you! 👨‍💻

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **Common Issues We Can Help With:**

• Bot not responding to commands
• Quiz generation problems
• Group setup assistance
• Feature requests
• Bug reports
• General questions

━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 Click the button below to contact our developer directly for personalized support!

【~@DrQuizRobot】
"""
    
    keyboard = [
        [InlineKeyboardButton("👨‍💻 Contact Developer", url="https://t.me/Aman_personalBot")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(support_message, reply_markup=reply_markup)

@check_force_join
async def developer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send developer information message with buttons."""
    developer_message = """╔═══════════════════════════════════╗
║   🚀 𝗠𝗘𝗘𝗧 𝗧𝗛𝗘 𝗗𝗘𝗩𝗘𝗟𝗢𝗣𝗘𝗥 🚀   ║
╚═══════════════════════════════════╝

👋 Namaste 🇮🇳! ✨

🎯 Meet Aman - The visionary behind this This NEET QUIZZING BOT

⚡ Who is Aman?
🏢 Founder & CEO of 『Sᴀɴsᴀ Fᴇᴇʟ』
✈️ Owner Of AimAi 【Your Personal Ai Tutor For Neet & Jee Preparation】
🎓 working On Different Projects. 
💻 Tech Innovator building educational solutions

🌟 What Makes Him Special?
✅ Created this FREE quiz bot for students like you
✅ Personally reviews every feature for student benefit  
✅ Available for 1-on-1 chatting, to know the suggestions ideas and feedback 
✅ Passionate about making Student's struggle & preparation affordable

═══════════════════════════════════
Let's connect with Aman Directly, privately and securely!
"""
    
    keyboard = [
        [InlineKeyboardButton("👨‍💻 Meet the Developer", url="https://t.me/Aman_personalBot")],
        [InlineKeyboardButton("📢 Checkout the Updates", url="https://t.me/founderofsansa")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(developer_message, reply_markup=reply_markup)

@check_force_join
async def donate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send donation message with button to donation bot."""
    user_first_name = update.effective_user.first_name
    
    donate_message = f"""╔═════════════════════════════════════╗
║  💝 𝗦𝗨𝗣𝗣𝗢𝗥𝗧 𝗢𝗨𝗥 𝗠𝗜𝗦𝗦𝗜𝗢𝗡 💝  ║
╚═════════════════════════════════════╝

🌟 Hey {user_first_name}! ✨

🎯 Your Support Makes Dreams Come True!

💡 Every donation helps thousands of students:
✅ Access FREE quality quiz questions daily
✅ Improve their preparation with instant scoring  
✅ Compete with peers in real-time leaderboards
✅ Get closer to their Dream COLLEGE! 🏥

🚀 Why Your Support Matters:
🔥 Server hosting & maintenance costs
⚡ Adding new features & improvements  
📚 Creating more educational content
🛡️ Ensuring 100% uptime for students

💖 We've Created Something Special For You:

🤖 Secure Donation Bot: @DrQuizDonationRobot
🔒 100% Safe & Transparent transactions
🎁 Special Recognition for our supporters  
📊 Impact Reports - See how you're helping students!

════════════════════════════════════════

🌈 "Education is the most powerful weapon which you can use to change the world" - Nelson Mandela

💝 Your kindness today shapes a Student's journey tomorrow!

🙏 Thank you for believing in education and our mission!
"""
    
    keyboard = [
        [InlineKeyboardButton("💝 Donate Us", url="https://t.me/DrQuizDonationRobot")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(donate_message, reply_markup=reply_markup)

@check_force_join
async def create_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /cquiz command to generate a quiz."""
    chat_id = update.effective_chat.id
    lock_acquired = False
    
    try:
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "╔═══════════════════════════════╗\n"
                "║      ❌ INVALID FORMAT ❌       ║\n"
                "╚═══════════════════════════════╝\n\n"
                "📝 **Usage:**\n"
                "/cquiz [chapter name] [number]\n\n"
                "📖 **Example:**\n"
                "• /cquiz Human Physiology 5\n"
                "• /cquiz Thermodynamics 10\n\n"
                "【~@DrQuizRobot】"
            )
            return
        
        if quiz_lock_manager.is_locked(chat_id):
            lock_info = quiz_lock_manager.get_lock_info(chat_id)
            quiz_type_msg = "timer quiz" if lock_info.quiz_type == "timer_quiz" else "quiz"
            await update.message.reply_text(
                "╔═══════════════════════════════╗\n"
                "║   ⚠️ QUIZ IN PROGRESS ⚠️      ║\n"
                "╚═══════════════════════════════╝\n\n"
                f"🎮 A {quiz_type_msg} is currently active!\n\n"
                "⏳ **Please:**\n"
                "• Wait for current quiz to complete\n"
                "• Or use /stopquiz to end it\n\n"
                "📌 Only one quiz can run at a time per group.\n\n"
                "【~@DrQuizRobot】"
            )
            return
        
        num_questions_str = context.args[-1]
        chapter_parts = context.args[:-1]
        chapter = ' '.join(chapter_parts)
        
        try:
            num_questions = int(num_questions_str)
        except ValueError:
            await update.message.reply_text(
                "╔═══════════════════════════════╗\n"
                "║    ❌ INVALID NUMBER ❌         ║\n"
                "╚═══════════════════════════════╝\n\n"
                f"🔢 You entered: '{num_questions_str}'\n\n"
                "✅ Please provide a number between 1 and 20.\n\n"
                "【~@DrQuizRobot】"
            )
            return
        
        if num_questions < MIN_QUESTIONS or num_questions > MAX_QUESTIONS:
            await update.message.reply_text(
                "╔═══════════════════════════════╗\n"
                "║   ⚠️ OUT OF RANGE ⚠️          ║\n"
                "╚═══════════════════════════════╝\n\n"
                f"🔢 You requested: **{num_questions}** questions\n\n"
                f"✅ Valid range: **{MIN_QUESTIONS} - {MAX_QUESTIONS}** questions\n\n"
                "Please choose a number within the range.\n\n"
                "【~@DrQuizRobot】"
            )
            return
        
        if not quiz_lock_manager.acquire_lock(chat_id, "cquiz"):
            await update.message.reply_text(
                "╔═══════════════════════════════╗\n"
                "║   ⚠️ QUIZ IN PROGRESS ⚠️      ║\n"
                "╚═══════════════════════════════╝\n\n"
                "🎮 Another quiz is currently active!\n\n"
                "⏳ Please wait for it to complete.\n\n"
                "【~@DrQuizRobot】"
            )
            return
        
        lock_acquired = True
        
        # Get language setting for this chat
        language = language_manager.get_language(chat_id)
        
        await update.message.reply_text(
            "╔═══════════════════════════════╗\n"
            "║   ⚡ QUIZ GENERATION ⚡        ║\n"
            "╚═══════════════════════════════╝\n\n"
            f"📚 Chapter: **{chapter}**\n"
            f"📝 Questions: **{num_questions}**\n\n"
            "🔄 Generating NEET-level questions...\n"
            "⏳ Please wait a moment...\n\n"
            "【~@DrQuizRobot】"
        )
        
        logger.info(f"Generating quiz: chapter='{chapter}', questions={num_questions}, language={language}")
        questions = quiz_gen.generate_quiz(chapter, num_questions, language)
        
        if not questions:
            if lock_acquired:
                quiz_lock_manager.release_lock(chat_id)
            await update.message.reply_text(
                "╔═══════════════════════════════╗\n"
                "║   ❌ GENERATION FAILED ❌      ║\n"
                "╚═══════════════════════════════╝\n\n"
                "😔 Could not generate questions\n\n"
                "💡 **Try:**\n"
                "• Check chapter name spelling\n"
                "• Use NCERT Class 11/12 chapters\n"
                "• Try a different topic\n\n"
                "【~@DrQuizRobot】"
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
            "╔═══════════════════════════════╗\n"
            "║    ✅ QUIZ COMPLETE! ✅         ║\n"
            "╚═══════════════════════════════╝\n\n"
            f"🎉 Successfully sent **{len(questions)}** questions!\n\n"
            f"📚 Chapter: **{chapter}**\n\n"
            "🎯 Answer all questions carefully!\n"
            "🏆 Good luck with your preparation!\n\n"
            "【~@DrQuizRobot】"
        )
        
        if lock_acquired:
            quiz_lock_manager.release_lock(chat_id)
        
    except ValueError as e:
        logger.error(f"Value error in create_quiz: {e}")
        if lock_acquired:
            quiz_lock_manager.release_lock(chat_id)
        await update.message.reply_text(
            "╔═══════════════════════════════╗\n"
            "║   ❌ GENERATION FAILED ❌      ║\n"
            "╚═══════════════════════════════╝\n\n"
            "😔 Could not generate quiz\n\n"
            "💡 **Please check:**\n"
            "• Chapter name is correct\n"
            "• It's from NCERT Class 11/12\n"
            "• Spelling is accurate\n\n"
            "【~@DrQuizRobot】"
        )
    except Exception as e:
        logger.error(f"Error in create_quiz: {e}")
        if lock_acquired:
            quiz_lock_manager.release_lock(chat_id)
        await update.message.reply_text(
            "╔═══════════════════════════════╗\n"
            "║      ❌ ERROR ❌               ║\n"
            "╚═══════════════════════════════╝\n\n"
            "⚠️ An unexpected error occurred\n\n"
            "🔄 Please try again in a moment\n\n"
            "【~@DrQuizRobot】"
        )

@check_force_join
async def timed_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /quiz command to start a timed quiz session with 20 questions."""
    chat_id = None
    lock_acquired = False
    
    try:
        chat_id = update.effective_chat.id
        is_private_chat = update.effective_chat.type == 'private'
        
        if quiz_session_manager.has_active_session(chat_id) or quiz_lock_manager.is_locked(chat_id):
            lock_info = quiz_lock_manager.get_lock_info(chat_id)
            quiz_type_msg = "cquiz" if lock_info and lock_info.quiz_type == "cquiz" else "timer quiz"
            await update.message.reply_text(
                "╔═══════════════════════════════╗\n"
                "║   ⚠️ QUIZ ALREADY ACTIVE ⚠️   ║\n"
                "╚═══════════════════════════════╝\n\n"
                f"🎮 A {quiz_type_msg} is already running!\n\n"
                "⏳ Please wait for it to finish\n"
                "🛑 Or use /stopquiz to cancel\n\n"
                "【~@DrQuizRobot】"
            )
            return
        
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "╔═══════════════════════════════╗\n"
                "║      ❌ INVALID FORMAT ❌       ║\n"
                "╚═══════════════════════════════╝\n\n"
                "📝 **Usage:**\n"
                "/quiz [chapter name]\n\n"
                "📖 **Examples:**\n"
                "• /quiz Human Physiology\n"
                "• /quiz Thermodynamics\n\n"
                "ℹ️ **Info:**\n"
                "• 20 questions per quiz\n"
                "• Choose your own time per question\n"
                "• Leaderboard at the end\n\n"
                "【~@DrQuizRobot】"
            )
            return
        
        chapter = ' '.join(context.args)
        
        language = language_manager.get_language(chat_id)
        
        quiz_mode = "instant advance" if is_private_chat else "timer-based"
        await update.message.reply_text(
            "╔═══════════════════════════════╗\n"
            "║  🎯 TIMED QUIZ SESSION 🎯     ║\n"
            "╚═══════════════════════════════╝\n\n"
            f"📚 **Chapter:** {chapter}\n"
            f"📝 **Questions:** 20\n"
            f"{'⚡ **Mode:** Instant advance' if is_private_chat else '🔄 **Mode:** Auto-advance'}\n"
            f"🏆 **Leaderboard:** Yes\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚡ Generating NEET PYQs...\n"
            "⏳ Please wait...\n\n"
            "【~@DrQuizRobot】"
        )
        
        logger.info(f"Generating 20 questions for timed quiz: chapter='{chapter}', language={language}, mode={quiz_mode}")
        questions = quiz_gen.generate_quiz(chapter, 20, language)
        
        if not questions or len(questions) < 20:
            await update.message.reply_text(
                "╔═══════════════════════════════╗\n"
                "║   ❌ GENERATION FAILED ❌      ║\n"
                "╚═══════════════════════════════╝\n\n"
                "😔 Could not generate 20 questions\n\n"
                "💡 **Try:**\n"
                "• Different chapter name\n"
                "• Check spelling\n"
                "• Use NCERT topics\n\n"
                "【~@DrQuizRobot】"
            )
            return
        
        context.chat_data['pending_quiz'] = {
            'chapter': chapter,
            'questions': questions,
            'is_private_chat': is_private_chat
        }
        
        keyboard = [
            [
                InlineKeyboardButton("⏱️ 15 sec", callback_data="quiz_time_15"),
                InlineKeyboardButton("⏱️ 30 sec", callback_data="quiz_time_30")
            ],
            [
                InlineKeyboardButton("⏱️ 45 sec", callback_data="quiz_time_45"),
                InlineKeyboardButton("⏱️ 60 sec", callback_data="quiz_time_60")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "╔═══════════════════════════════╗\n"
            "║   ⏱️ SELECT TIME PER QUIZ ⏱️  ║\n"
            "╚═══════════════════════════════╝\n\n"
            "🎯 Quiz is ready to start!\n\n"
            "⏱️ Please choose time per question:\n\n"
            "【~@DrQuizRobot】",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in timed_quiz_command: {e}", exc_info=True)
        if chat_id and lock_acquired:
            quiz_lock_manager.release_lock(chat_id)
        if chat_id:
            await update.message.reply_text(
                "╔═══════════════════════════════╗\n"
                "║      ❌ ERROR ❌               ║\n"
                "╚═══════════════════════════════╝\n\n"
                "⚠️ Could not start quiz\n\n"
                "🔄 Please try again later\n\n"
                "【~@DrQuizRobot】"
            )
        if chat_id and quiz_session_manager.has_active_session(chat_id):
            quiz_session_manager.end_session(chat_id)

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
            open_period=session.time_per_question,
            explanation=question_data.get('explanation', '')[:200] if question_data.get('explanation') else None
        )
        
        session.start_question(message.poll.id)
        logger.info(f"Sent question {question_num}/20 for quiz in chat {chat_id}, poll_id={message.poll.id}, time={session.time_per_question}s")
        
        delay = session.time_per_question + 2
        task = asyncio.create_task(auto_advance_question(update, context, chat_id, delay))
        session.auto_advance_task = task
        
    except Exception as e:
        logger.error(f"Error sending next question: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text="╔═══════════════════════════════╗\n"
                 "║      ❌ ERROR ❌               ║\n"
                 "╚═══════════════════════════════╝\n\n"
                 "⚠️ Error sending question\n\n"
                 "🛑 Quiz ended\n\n"
                 "【~@DrQuizRobot】"
        )
        quiz_session_manager.end_session(chat_id)
        quiz_lock_manager.release_lock(chat_id)

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
        
        questions_answered = session.current_question_index
        if session.current_poll_id:
            questions_answered += 1
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=generate_quiz_complete_message(questions_answered)
        )
        
        await asyncio.sleep(2)
        
        leaderboard_data = session.get_leaderboard_data()
        leaderboard_message = generate_leaderboard_message(leaderboard_data, session.chapter, questions_answered)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=leaderboard_message,
            parse_mode='Markdown'
        )
        
        logger.info(f"Quiz completed for chat {chat_id}, participants: {len(leaderboard_data)}")
        
        stats_manager.record_quiz(questions_answered)
        
        quiz_session_manager.end_session(chat_id)
        quiz_lock_manager.release_lock(chat_id)
        
    except Exception as e:
        logger.error(f"Error finalizing quiz: {e}", exc_info=True)
        quiz_session_manager.end_session(chat_id)
        quiz_lock_manager.release_lock(chat_id)

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
        
        if poll_id in live_quiz_coordinator.poll_to_question_map:
            session_id, question_idx, group_id = live_quiz_coordinator.poll_to_question_map[poll_id]
            live_session = live_quiz_coordinator.active_session
            
            if live_session and live_session.session_id == session_id:
                question_english = live_session.questions_english[question_idx]
                is_correct = (option_id == int(question_english['correct_answer']))
                
                try:
                    chat = await context.bot.get_chat(group_id)
                    group_title = chat.title or f"Group {group_id}"
                except:
                    group_title = f"Group {group_id}"
                
                time_taken = 1.0
                
                live_session.record_answer(
                    user.id,
                    user.username,
                    user.first_name,
                    group_id,
                    group_title,
                    is_correct,
                    time_taken
                )
                
                logger.info(f"[LIVE QUIZ] Recorded answer from {user.first_name} (ID: {user.id}) in group {group_id}, correct: {is_correct}, question: {question_idx+1}/{live_session.get_question_count()}")
                return
        
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
            "╔═══════════════════════════════╗\n"
            "║    ❌ NO ACTIVE QUIZ ❌        ║\n"
            "╚═══════════════════════════════╝\n\n"
            "ℹ️ No quiz is running here\n\n"
            "💡 Start one with: /quiz [chapter]\n\n"
            "【~@DrQuizRobot】"
        )
        return
    
    quiz_session_manager.end_session(chat_id)
    quiz_lock_manager.release_lock(chat_id)
    
    await update.message.reply_text(
        "╔═══════════════════════════════╗\n"
        "║   🛑 QUIZ STOPPED 🛑          ║\n"
        "╚═══════════════════════════════╝\n\n"
        "✅ Quiz session ended\n\n"
        "🔄 Start new quiz anytime:\n"
        "/quiz [chapter name]\n\n"
        "【~@DrQuizRobot】"
    )

@check_force_join
async def end_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End the timer quiz and show leaderboard with current progress."""
    chat_id = update.effective_chat.id
    
    session = quiz_session_manager.get_session(chat_id)
    
    if not session or not session.is_active:
        await update.message.reply_text(
            "╔═══════════════════════════════╗\n"
            "║    ❌ NO ACTIVE QUIZ ❌        ║\n"
            "╚═══════════════════════════════╝\n\n"
            "ℹ️ No timer quiz is running\n\n"
            "💡 Start one with:\n"
            "/quiz [chapter name]\n\n"
            "【~@DrQuizRobot】"
        )
        return
    
    if session.auto_advance_task and not session.auto_advance_task.done():
        session.auto_advance_task.cancel()
        logger.info(f"Cancelled auto-advance task for chat {chat_id}")
    
    questions_answered = session.current_question_index
    if session.current_poll_id:
        questions_answered += 1
    
    await finalize_quiz(update, context, chat_id)

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

@admin_only
async def startlivequiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a global live quiz across all groups (admin only)."""
    if live_quiz_coordinator.has_active_session():
        await update.message.reply_text(
            "⚠️ A global live quiz is already in progress!\n\n"
            "Please wait for the current session to complete before starting a new one."
        )
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ Invalid format!\n\n"
            "Usage: /startlivequiz <chapter name>\n\n"
            "Example: /startlivequiz Thermodynamics\n"
            "Example: /startlivequiz Human Physiology\n\n"
            "This will start a global live quiz across ALL groups!"
        )
        return
    
    chapter = ' '.join(context.args)
    admin_id = update.effective_user.id
    
    keyboard = [
        [
            InlineKeyboardButton("📝 10 Questions", callback_data=f"livequiz_count_10_{chapter}"),
            InlineKeyboardButton("📝 15 Questions", callback_data=f"livequiz_count_15_{chapter}"),
            InlineKeyboardButton("📝 20 Questions", callback_data=f"livequiz_count_20_{chapter}")
        ],
        [
            InlineKeyboardButton("📝 25 Questions", callback_data=f"livequiz_count_25_{chapter}"),
            InlineKeyboardButton("📝 30 Questions", callback_data=f"livequiz_count_30_{chapter}"),
            InlineKeyboardButton("📝 35 Questions", callback_data=f"livequiz_count_35_{chapter}")
        ],
        [
            InlineKeyboardButton("📝 40 Questions", callback_data=f"livequiz_count_40_{chapter}"),
            InlineKeyboardButton("📝 45 Questions", callback_data=f"livequiz_count_45_{chapter}"),
            InlineKeyboardButton("📝 50 Questions", callback_data=f"livequiz_count_50_{chapter}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"╔═══════════════════════════════════╗\n"
        f"║  📝 SELECT QUESTION COUNT 📝      ║\n"
        f"╚═══════════════════════════════════╝\n\n"
        f"📚 **Chapter:** {chapter}\n"
        f"🌍 **Type:** GLOBAL LIVE QUIZ\n\n"
        f"🎯 Choose how many questions:\n\n"
        f"【~@DrQuizRobot】",
        reply_markup=reply_markup
    )

async def livequiz_count_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle question count selection for live quiz."""
    query = update.callback_query
    await query.answer()
    
    if not admin_manager.is_admin(query.from_user.id):
        await query.edit_message_text("❌ Only admins can start live quizzes!")
        return
    
    if live_quiz_coordinator.has_active_session():
        await query.edit_message_text(
            "⚠️ A global live quiz is already in progress!\n\n"
            "Please wait for the current session to complete before starting a new one."
        )
        return
    
    data = query.data
    parts = data.split('_')
    question_count = int(parts[2])
    chapter = '_'.join(parts[3:])
    
    keyboard = [
        [
            InlineKeyboardButton("⚡ 15 seconds", callback_data=f"livequiz_time_{question_count}_15_{chapter}"),
            InlineKeyboardButton("🔥 30 seconds", callback_data=f"livequiz_time_{question_count}_30_{chapter}")
        ],
        [
            InlineKeyboardButton("⏱️ 45 seconds", callback_data=f"livequiz_time_{question_count}_45_{chapter}"),
            InlineKeyboardButton("🎯 60 seconds", callback_data=f"livequiz_time_{question_count}_60_{chapter}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"╔═══════════════════════════════════╗\n"
        f"║  ⏱️ SELECT TIME PER QUESTION ⏱️  ║\n"
        f"╚═══════════════════════════════════╝\n\n"
        f"📚 **Chapter:** {chapter}\n"
        f"📝 **Questions:** {question_count} MCQs\n"
        f"🌍 **Type:** GLOBAL LIVE QUIZ\n\n"
        f"⏱️ Choose how much time per question:\n\n"
        f"【~@DrQuizRobot】",
        reply_markup=reply_markup
    )

async def livequiz_time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle time selection for live quiz."""
    query = update.callback_query
    await query.answer()
    
    if not admin_manager.is_admin(query.from_user.id):
        await query.edit_message_text("❌ Only admins can start live quizzes!")
        return
    
    if live_quiz_coordinator.has_active_session():
        await query.edit_message_text(
            "⚠️ A global live quiz is already in progress!\n\n"
            "Please wait for the current session to complete before starting a new one."
        )
        return
    
    data = query.data
    parts = data.split('_')
    question_count = int(parts[2])
    time_seconds = int(parts[3])
    chapter = '_'.join(parts[4:])
    
    live_quiz_coordinator.question_duration = time_seconds
    
    admin_id = query.from_user.id
    
    await query.edit_message_text(
        f"🔄 Generating quiz for chapter: **{chapter}**\n\n"
        f"📝 Questions: **{question_count} MCQs**\n"
        f"⏱️ Time per question: **{time_seconds} seconds**\n\n"
        f"Please wait while I prepare {question_count} NEET-level questions in both languages..."
    )
    
    try:
        # Generate questions in both English and Hindi
        questions_english = quiz_gen.generate_quiz(chapter, question_count, 'english')
        
        if not questions_english:
            await query.edit_message_text(
                f"❌ Failed to generate English questions for chapter: {chapter}\n\n"
                f"Please check the chapter name and try again."
            )
            return
        
        await query.edit_message_text(
            f"🔄 English questions generated! Now translating to Hindi...\n\n"
            f"📝 Questions: **{question_count} MCQs**\n"
            f"⏱️ Time per question: **{time_seconds} seconds**"
        )
        
        questions_hindi = quiz_gen.translate_questions(questions_english)
        
        if not questions_hindi or len(questions_hindi) != len(questions_english):
            await query.edit_message_text(
                f"❌ Failed to translate questions to Hindi for chapter: {chapter}\n\n"
                f"Please try again."
            )
            return
        
        session = live_quiz_coordinator.create_session(chapter, questions_english, questions_hindi, admin_id)
        
        all_groups = list(stats_manager.get_all_groups())
        
        if not all_groups:
            await query.edit_message_text(
                "⚠️ No groups found!\n\n"
                "The bot needs to be added to groups first before starting a global quiz."
            )
            return
        
        await query.edit_message_text(
            f"✅ Quiz generated successfully!\n\n"
            f"📚 Chapter: {chapter}\n"
            f"📝 Questions: {question_count} MCQs (English + Hindi)\n"
            f"⏱️ Time/Question: {time_seconds}s\n"
            f"🌍 Target Groups: {len(all_groups)} groups\n\n"
            f"⏰ Sending 1-minute countdown now..."
        )
        
        sent_count = await live_quiz_coordinator.send_countdown_reminder(
            context, all_groups, chapter, question_count
        )
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                f"✅ Countdown sent to {sent_count}/{len(all_groups)} groups!\n\n"
                f"⏱️ Quiz will start in 1 minute...\n\n"
                f"Global leaderboard will be shared after quiz completion!"
            )
        )
        
        session.countdown_task = asyncio.create_task(
            live_quiz_coordinator.start_quiz_after_countdown(
                context, session, all_groups, quiz_gen, 
                quiz_lock_manager, stats_manager, language_manager
            )
        )
        
    except Exception as e:
        logger.error(f"Error starting live quiz: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                f"❌ Error starting live quiz: {str(e)}\n\n"
                f"Please try again or contact support."
            )
        )

@admin_only
async def endlivequiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End the active live quiz early (admin only)."""
    try:
        success, message = await live_quiz_coordinator.end_live_quiz_early(context, quiz_lock_manager)
        
        if success:
            await update.message.reply_text(
                "╔═══════════════════════════════════╗\n"
                "║   ✅ LIVE QUIZ ENDED ✅           ║\n"
                "╚═══════════════════════════════════╝\n\n"
                f"📢 {message}\n\n"
                "🏆 Leaderboards have been sent to all groups!\n\n"
                "【~@DrQuizRobot】"
            )
        else:
            await update.message.reply_text(
                "╔═══════════════════════════════════╗\n"
                "║   ⚠️ CANNOT END QUIZ ⚠️           ║\n"
                "╚═══════════════════════════════════╝\n\n"
                f"📢 {message}\n\n"
                "【~@DrQuizRobot】"
            )
    
    except Exception as e:
        logger.error(f"Error ending live quiz: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Error ending live quiz: {str(e)}\n\n"
            f"Please try again or contact support."
        )

@admin_only
async def forceliveleaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force send global live quiz leaderboard to all groups (admin only)."""
    try:
        if not live_quiz_coordinator.active_session:
            await update.message.reply_text(
                "⚠️ No global live quiz session found!\n\n"
                "There must be a completed or active quiz to send leaderboards."
            )
            return
        
        session = live_quiz_coordinator.active_session
        
        if not session.is_completed and not session.participants:
            await update.message.reply_text(
                "⚠️ Quiz has no participants yet!\n\n"
                "Wait for quiz to have some participants before forcing leaderboard."
            )
            return
        
        await update.message.reply_text(
            "🔄 Forcing leaderboard generation...\n\n"
            "Please wait while I send leaderboards to all groups..."
        )
        
        # Mark unattempted questions for all participants
        for user_id in session.participants.keys():
            session.mark_unattempted(user_id, session.get_question_count())
        
        # Get sorted participants with global ranks
        sorted_participants = session.get_sorted_participants()
        
        # Create global rank mapping
        global_rank_map = {}
        for rank, participant in enumerate(sorted_participants, 1):
            global_rank_map[participant.user_id] = rank
        
        # Send leaderboards to all groups
        sent_count = 0
        error_count = 0
        
        for group_id, group_state in session.group_states.items():
            try:
                # Send global leaderboard
                global_leaderboard = live_quiz_coordinator.generate_global_leaderboard(session, sorted_participants)
                await context.bot.send_message(
                    chat_id=group_id,
                    text=global_leaderboard,
                    parse_mode='Markdown'
                )
                
                await asyncio.sleep(0.5)
                
                # Send group-specific leaderboard
                group_leaderboard = live_quiz_coordinator.generate_group_leaderboard(
                    session, group_id, group_state.group_title, global_rank_map
                )
                if group_leaderboard:
                    await context.bot.send_message(
                        chat_id=group_id,
                        text=group_leaderboard,
                        parse_mode='Markdown'
                    )
                
                sent_count += 1
                await asyncio.sleep(0.3)
                
            except Exception as e:
                logger.error(f"Failed to force send leaderboard to group {group_id}: {e}")
                error_count += 1
        
        await update.message.reply_text(
            "╔═══════════════════════════════════╗\n"
            "║   ✅ LEADERBOARDS SENT ✅         ║\n"
            "╚═══════════════════════════════════╝\n\n"
            f"📊 Successfully sent to: {sent_count} groups\n"
            f"❌ Failed: {error_count} groups\n\n"
            f"🏆 Total Participants: {len(session.participants)}\n\n"
            "【~@DrQuizRobot】"
        )
    
    except Exception as e:
        logger.error(f"Error forcing leaderboard: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Error forcing leaderboard: {str(e)}\n\n"
            f"Please try again or contact support."
        )

@admin_only
async def fgloballeaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force send global leaderboard for a specific quiz ID to all groups (admin only)."""
    try:
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "❌ Invalid format!\n\n"
                "Usage: /fgloballeaderboard GQ0001\n\n"
                "Example: /fgloballeaderboard GQ0042\n\n"
                "This will send the global leaderboard for quiz GQ0042 to all groups.\n\n"
                "Note: Only works for quizzes completed in the current bot session.\n\n"
                "【~@DrQuizRobot】"
            )
            return
        
        quiz_id = context.args[0].upper()
        
        await update.message.reply_text(
            f"🔄 Sending global leaderboard for quiz {quiz_id}...\n\n"
            "Please wait while I send the leaderboard to all groups..."
        )
        
        success, message = await live_quiz_coordinator.force_send_global_leaderboard(
            context, quiz_id, force_join_manager
        )
        
        if success:
            await update.message.reply_text(
                "╔═══════════════════════════════════╗\n"
                "║   ✅ LEADERBOARD SENT ✅          ║\n"
                "╚═══════════════════════════════════╝\n\n"
                f"📊 {message}\n\n"
                "【~@DrQuizRobot】"
            )
        else:
            await update.message.reply_text(
                "╔═══════════════════════════════════╗\n"
                "║   ⚠️ FAILED ⚠️                    ║\n"
                "╚═══════════════════════════════════╝\n\n"
                f"📢 {message}\n\n"
                "【~@DrQuizRobot】"
            )
    
    except Exception as e:
        logger.error(f"Error in fgloballeaderboard: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Error sending leaderboard: {str(e)}\n\n"
            f"Please try again or contact support."
        )

@admin_only
async def fgroupleaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force send group leaderboards for a specific quiz ID to all groups (admin only)."""
    try:
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "❌ Invalid format!\n\n"
                "Usage: /fgroupleaderboard GQ0001\n\n"
                "Example: /fgroupleaderboard GQ0042\n\n"
                "This will send each group's leaderboard for quiz GQ0042 to all groups.\n\n"
                "Note: Only works for quizzes completed in the current bot session.\n\n"
                "【~@DrQuizRobot】"
            )
            return
        
        quiz_id = context.args[0].upper()
        
        await update.message.reply_text(
            f"🔄 Sending group leaderboards for quiz {quiz_id}...\n\n"
            "Please wait while I send the leaderboards to all groups..."
        )
        
        success, message = await live_quiz_coordinator.force_send_group_leaderboards(
            context, quiz_id, force_join_manager
        )
        
        if success:
            await update.message.reply_text(
                "╔═══════════════════════════════════╗\n"
                "║   ✅ LEADERBOARDS SENT ✅         ║\n"
                "╚═══════════════════════════════════╝\n\n"
                f"📊 {message}\n\n"
                "【~@DrQuizRobot】"
            )
        else:
            await update.message.reply_text(
                "╔═══════════════════════════════════╗\n"
                "║   ⚠️ FAILED ⚠️                    ║\n"
                "╚═══════════════════════════════════╝\n\n"
                f"📢 {message}\n\n"
                "【~@DrQuizRobot】"
            )
    
    except Exception as e:
        logger.error(f"Error in fgroupleaderboard: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Error sending leaderboards: {str(e)}\n\n"
            f"Please try again or contact support."
        )

async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Refresh and reset bot state (available to all users)."""
    try:
        user = update.effective_user
        is_admin = admin_manager.is_admin(user.id)
        
        await update.message.reply_text(
            "🔄 Refreshing bot...\n\n"
            "⏳ Please wait while I reset all systems..."
        )
        
        status_parts = []
        
        # Check for active live quiz (don't clear if running)
        if live_quiz_coordinator.active_session and live_quiz_coordinator.active_session.is_running:
            await update.message.reply_text(
                "⚠️ Global live quiz is currently running!\n\n"
                "Cannot refresh while quiz is active. Please wait for quiz to complete or ask admin to end it first."
            )
            return
        
        # Clear only inactive quiz sessions (safe for all users)
        cleared_sessions = 0
        sessions_to_remove = []
        for chat_id, session in list(quiz_session_manager.active_sessions.items()):
            if not session.is_active:
                sessions_to_remove.append(chat_id)
        
        for chat_id in sessions_to_remove:
            del quiz_session_manager.active_sessions[chat_id]
            cleared_sessions += 1
        
        if cleared_sessions > 0:
            status_parts.append(f"✅ Cleared {cleared_sessions} inactive quiz session(s)")
        
        # Admin-only: Clear ALL quiz locks (including active ones)
        if is_admin:
            cleared_locks = len(quiz_lock_manager.locks)
            if cleared_locks > 0:
                quiz_lock_manager.locks.clear()
                status_parts.append(f"✅ Released {cleared_locks} quiz lock(s) (admin)")
        else:
            # Regular users: Only inform about stuck locks
            if len(quiz_lock_manager.locks) > 0:
                status_parts.append(f"ℹ️ Found {len(quiz_lock_manager.locks)} quiz lock(s) - admin can clear these")
        
        # Refresh admin cache (safe for all users)
        await admin_manager.refresh_cache(context.bot)
        status_parts.append("✅ Refreshed admin cache")
        
        # Admin-only: Clear stuck live quiz session
        if is_admin:
            if live_quiz_coordinator.active_session and not live_quiz_coordinator.active_session.is_running:
                live_quiz_coordinator.active_session = None
                status_parts.append("✅ Cleared stuck live quiz session (admin)")
        
        # Log the refresh action
        logger.info(f"Bot refreshed by user {user.id} ({user.first_name}) - Admin: {is_admin}")
        
        status_message = "\n".join(status_parts) if status_parts else "✅ All systems already clean"
        
        await update.message.reply_text(
            "╔═══════════════════════════════════╗\n"
            "║   ✅ BOT REFRESHED ✅             ║\n"
            "╚═══════════════════════════════════╝\n\n"
            f"{status_message}\n\n"
            "🎉 Bot refresh completed!\n\n"
            "You can now use all commands normally.\n\n"
            "【~@DrQuizRobot】"
        )
    
    except Exception as e:
        logger.error(f"Error during bot refresh: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Error during refresh: {str(e)}\n\n"
            f"Bot may still be operational. Try again if issues persist."
        )

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

@group_admin_only
async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set quiz language preference. Anyone in private chat, admins only in groups."""
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
        "╔═══════════════════════════════╗\n"
        "║   🌐 LANGUAGE SETTINGS 🌐     ║\n"
        "╚═══════════════════════════════╝\n\n"
        f"📍 **Current Language:**\n{current_lang_text}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔄 **Choose Your Preferred Language:**\n\n"
        "• Questions will be in selected language\n"
        "• Explanations will match your choice\n"
        "• Settings saved per group/chat\n\n"
        "👇 **Select Language Below:**\n\n"
        "【~@DrQuizRobot】",
        reply_markup=reply_markup
    )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection callback."""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type
    
    # In private chats, everyone is authorized
    # In groups, only bot admins or group admins are authorized
    is_authorized = False
    
    if chat_type == 'private':
        is_authorized = True
    else:
        # Check bot admin
        if admin_manager.is_admin(user_id):
            is_authorized = True
        # Check group admin
        elif chat_type in ['group', 'supergroup']:
            try:
                member = await context.bot.get_chat_member(chat_id, user_id)
                if member.status in ['creator', 'administrator']:
                    is_authorized = True
            except:
                pass
    
    if not is_authorized:
        await query.edit_message_text(
            "╔═══════════════════════════════╗\n"
            "║   ❌ UNAUTHORIZED ❌           ║\n"
            "╚═══════════════════════════════╝\n\n"
            "🔒 Only admins can change language in groups\n\n"
            "【~@DrQuizRobot】"
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
        await query.edit_message_text(
            "╔═══════════════════════════════╗\n"
            "║   ❌ INVALID SELECTION ❌      ║\n"
            "╚═══════════════════════════════╝\n\n"
            "【~@DrQuizRobot】"
        )
        return
    
    # Set language preference
    language_manager.set_language(chat_id, language)
    
    chat_type = "group" if update.effective_chat.type in ['group', 'supergroup'] else "chat"
    
    await query.edit_message_text(
        "╔═══════════════════════════════╗\n"
        "║   ✅ LANGUAGE UPDATED ✅       ║\n"
        "╚═══════════════════════════════╝\n\n"
        f"{language_emoji} **Language:** {language_name}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "✨ **What Changed:**\n\n"
        f"• Quiz questions → {language_name}\n"
        f"• Explanations → {language_name}\n"
        f"• Settings saved for this {chat_type}\n\n"
        "🎯 All quizzes will now be in your preferred language!\n\n"
        "【~@DrQuizRobot】"
    )

async def quiz_time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quiz time selection callback."""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    if 'pending_quiz' not in context.chat_data:
        await query.edit_message_text(
            "╔═══════════════════════════════╗\n"
            "║   ❌ SESSION EXPIRED ❌        ║\n"
            "╚═══════════════════════════════╝\n\n"
            "⏳ Quiz session expired\n\n"
            "🔄 Please run /quiz command again\n\n"
            "【~@DrQuizRobot】"
        )
        return
    
    time_mapping = {
        "quiz_time_15": 15,
        "quiz_time_30": 30,
        "quiz_time_45": 45,
        "quiz_time_60": 60
    }
    
    if query.data not in time_mapping:
        await query.edit_message_text(
            "╔═══════════════════════════════╗\n"
            "║   ❌ INVALID SELECTION ❌      ║\n"
            "╚═══════════════════════════════╝\n\n"
            "【~@DrQuizRobot】"
        )
        return
    
    time_per_question = time_mapping[query.data]
    
    pending_quiz = context.chat_data['pending_quiz']
    chapter = pending_quiz['chapter']
    questions = pending_quiz['questions']
    is_private_chat = pending_quiz['is_private_chat']
    
    del context.chat_data['pending_quiz']
    
    if quiz_session_manager.has_active_session(chat_id) or quiz_lock_manager.is_locked(chat_id):
        await query.edit_message_text(
            "╔═══════════════════════════════╗\n"
            "║   ⚠️ QUIZ ALREADY ACTIVE ⚠️   ║\n"
            "╚═══════════════════════════════╝\n\n"
            "🎮 A quiz is already running!\n\n"
            "⏳ Please wait for it to finish\n\n"
            "【~@DrQuizRobot】"
        )
        return
    
    if not quiz_lock_manager.acquire_lock(chat_id, "timer_quiz"):
        await query.edit_message_text(
            "╔═══════════════════════════════╗\n"
            "║   ⚠️ QUIZ IN PROGRESS ⚠️      ║\n"
            "╚═══════════════════════════════╝\n\n"
            "🎮 Another quiz is currently active!\n\n"
            "⏳ Please wait for it to complete.\n\n"
            "【~@DrQuizRobot】"
        )
        return
    
    try:
        session = quiz_session_manager.create_session(chat_id, chapter, questions, is_private_chat, time_per_question)
        
        await query.edit_message_text(
            "╔═══════════════════════════════╗\n"
            "║   🎮 QUIZ STARTING NOW! 🎮    ║\n"
            "╚═══════════════════════════════╝\n\n"
            "🎯 **Instructions:**\n\n"
            f"⏱️ Answer within {time_per_question} seconds\n"
            "🔄 Auto-advance after timer\n"
            "🏆 Score tracked for leaderboard\n"
            "📊 Real-time rankings\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🍀 **Good luck!**\n"
            "💪 Give your best!\n\n"
            "【~@DrQuizRobot】"
        )
        
        await asyncio.sleep(2)
        
        await send_next_question(update, context, chat_id)
        
    except Exception as e:
        logger.error(f"Error starting quiz: {e}", exc_info=True)
        quiz_lock_manager.release_lock(chat_id)
        await query.edit_message_text(
            "╔═══════════════════════════════╗\n"
            "║      ❌ ERROR ❌               ║\n"
            "╚═══════════════════════════════╝\n\n"
            "⚠️ Failed to start quiz\n\n"
            "🔄 Please try again\n\n"
            "【~@DrQuizRobot】"
        )

async def tagall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tag all group members with funny questions."""
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
        # Get tracked members from database (members who have sent messages)
        members_data = tagall_manager.get_members_for_tagging(chat.id, exclude_admins=True)
        
        if not members_data:
            total_tracked = tagall_manager.get_member_count(chat.id)
            await update.message.reply_text(
                f"⚠️ No non-admin members tracked yet!\n\n"
                f"📊 Total tracked members: {total_tracked} (all are admins)\n\n"
                f"💡 How it works:\n"
                f"• Bot tracks users who send messages in this group\n"
                f"• Ask group members to send at least one message\n"
                f"• Then use /tagall to tag them all!\n\n"
                f"Note: Admins are excluded from tagging to avoid spam."
            )
            return
        
        # Shuffle to randomize questions
        import random
        random.shuffle(members_data)
        
        # Tag members in batches of 15
        batch_size = 15
        for i in range(0, len(members_data), batch_size):
            batch = members_data[i:i + batch_size]
            
            # Build message with user mentions and questions
            message_parts = []
            for member_data in batch:
                user_id = member_data['user_id']
                user_first_name = member_data['first_name']
                user_mention = f"[{user_first_name}](tg://user?id={user_id})"
                question = get_tagall_question()
                
                message_parts.append(f"{user_mention} : {question}")
            
            # Join with double newline for margin
            message = "\n\n".join(message_parts)
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )
        
        # Send summary
        await update.message.reply_text(
            f"✅ Tagged {len(members_data)} members with funny questions! 🎯\n\n"
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

async def forward_user_message_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward any user message from private chat to admin group."""
    ADMIN_GROUP_ID = -1003049872361
    
    try:
        # Only handle messages from private chats
        if update.effective_chat.type != 'private':
            return
        
        # Skip if no message or no user
        if not update.message or not update.effective_user:
            return
        
        # Skip commands (they are handled by command handlers)
        if update.message.text and update.message.text.startswith('/'):
            return
        
        user = update.effective_user
        user_id = user.id
        user_name = user.first_name
        username = f"@{user.username}" if user.username else "No username"
        
        # Create header message
        header = (
            f"📨 **New Message from User**\n\n"
            f"👤 Name: {user_name}\n"
            f"🆔 User ID: `{user_id}`\n"
            f"📛 Username: {username}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        
        # Send header to admin group
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=header
        )
        
        # Forward the actual message to admin group
        forwarded = await update.message.forward(ADMIN_GROUP_ID)
        
        # Store mapping of forwarded message to user for replies
        # Format: {forwarded_message_id: user_id}
        if 'message_mapping' not in context.bot_data:
            context.bot_data['message_mapping'] = {}
        
        context.bot_data['message_mapping'][forwarded.message_id] = user_id
        
        logger.info(f"Forwarded message from user {user_id} to admin group. Stored mapping: {forwarded.message_id} -> {user_id}")
        
    except Exception as e:
        logger.error(f"Error forwarding message to admin: {e}", exc_info=True)

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin replies in admin group and send them back to users."""
    ADMIN_GROUP_ID = -1003049872361
    
    try:
        # Only handle messages from admin group
        if update.effective_chat.id != ADMIN_GROUP_ID:
            return
        
        # Check if this is a reply to a message
        if not update.message or not update.message.reply_to_message:
            return
        
        # Get the message being replied to
        replied_to_message_id = update.message.reply_to_message.message_id
        
        # Check if we have a mapping for this message
        if 'message_mapping' not in context.bot_data:
            return
        
        message_mapping = context.bot_data['message_mapping']
        
        if replied_to_message_id not in message_mapping:
            # Not a forwarded user message, ignore
            return
        
        # Get the original user ID
        user_id = message_mapping[replied_to_message_id]
        
        logger.info(f"Admin replied to message {replied_to_message_id}. Sending reply to user {user_id}")
        
        # Send the admin's message to the user
        if update.message.text:
            await context.bot.send_message(
                chat_id=user_id,
                text=update.message.text
            )
        elif update.message.photo:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=update.message.photo[-1].file_id,
                caption=update.message.caption
            )
        elif update.message.video:
            await context.bot.send_video(
                chat_id=user_id,
                video=update.message.video.file_id,
                caption=update.message.caption
            )
        elif update.message.document:
            await context.bot.send_document(
                chat_id=user_id,
                document=update.message.document.file_id,
                caption=update.message.caption
            )
        elif update.message.audio:
            await context.bot.send_audio(
                chat_id=user_id,
                audio=update.message.audio.file_id,
                caption=update.message.caption
            )
        elif update.message.voice:
            await context.bot.send_voice(
                chat_id=user_id,
                voice=update.message.voice.file_id,
                caption=update.message.caption
            )
        elif update.message.sticker:
            await context.bot.send_sticker(
                chat_id=user_id,
                sticker=update.message.sticker.file_id
            )
        elif update.message.animation:
            await context.bot.send_animation(
                chat_id=user_id,
                animation=update.message.animation.file_id,
                caption=update.message.caption
            )
        else:
            # Copy the message as-is if it's something else
            await update.message.copy(chat_id=user_id)
        
        logger.info(f"Successfully sent admin reply to user {user_id}")
        
        # React to admin's message to confirm it was sent
        await update.message.reply_text("✅ Message sent to user!")
        
    except Exception as e:
        logger.error(f"Error handling admin reply: {e}", exc_info=True)
        try:
            await update.message.reply_text(f"❌ Error sending message to user: {str(e)}")
        except:
            pass

async def track_group_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track all users who send messages in groups for tagall functionality."""
    try:
        # Only track in groups
        if update.effective_chat.type not in ['group', 'supergroup']:
            return
        
        # Skip if no user
        if not update.effective_user:
            return
        
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # AUTO-TRACK GROUP: Add group to stats_manager for global quizzes
        stats_manager.add_group(chat_id)
        
        # Track the member (admin status updated periodically, not per-message)
        tagall_manager.track_member(
            chat_id=chat_id,
            user_id=user.id,
            first_name=user.first_name,
            username=user.username,
            is_bot=user.is_bot
        )
        
    except Exception as e:
        logger.error(f"Error tracking group member: {e}")

async def refresh_admin_cache(context: ContextTypes.DEFAULT_TYPE):
    """Periodically refresh admin status for all tracked groups."""
    try:
        # Get all tracked chat IDs
        tracked_chats = list(tagall_manager.tracked_members.keys())
        
        for chat_id_str in tracked_chats:
            try:
                chat_id = int(chat_id_str)
                
                # Get current administrators
                administrators = await context.bot.get_chat_administrators(chat_id)
                admin_ids = {admin.user.id for admin in administrators if not admin.user.is_bot}
                
                # Update admin status in batch
                tagall_manager.update_admin_status(chat_id, admin_ids)
                
            except Exception as e:
                logger.error(f"Error refreshing admins for chat {chat_id_str}: {e}")
        
        # Flush any pending saves
        tagall_manager.flush_pending_saves()
        
    except Exception as e:
        logger.error(f"Error in admin cache refresh: {e}")

async def send_good_morning_wishes(context: ContextTypes.DEFAULT_TYPE):
    """Send good morning wishes to all users and groups daily at 6 AM IST."""
    try:
        logger.info("Starting good morning wishes broadcast...")
        
        # Get all tracked users and groups from stats
        all_users = stats_manager.users
        all_groups = stats_manager.groups
        
        success_count = 0
        fail_count = 0
        
        # Send to all groups
        for group_id in all_groups:
            try:
                # Get language preference for the group
                language = language_manager.get_language(group_id)
                message = good_morning_manager.generate_good_morning_message(language)
                
                await context.bot.send_message(
                    chat_id=group_id,
                    text=message,
                    parse_mode='Markdown'
                )
                success_count += 1
                logger.info(f"Sent good morning to group {group_id}")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                fail_count += 1
                logger.error(f"Error sending good morning to group {group_id}: {e}")
        
        # Send to all users (private chats)
        for user_id in all_users:
            try:
                # Get language preference for the user
                language = language_manager.get_language(user_id)
                message = good_morning_manager.generate_good_morning_message(language)
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown'
                )
                success_count += 1
                logger.info(f"Sent good morning to user {user_id}")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                fail_count += 1
                logger.error(f"Error sending good morning to user {user_id}: {e}")
        
        logger.info(f"Good morning broadcast completed. Success: {success_count}, Failed: {fail_count}")
        
    except Exception as e:
        logger.error(f"Error in good morning wishes broadcast: {e}")

@check_force_join
async def explain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explain any question, topic, or reply to a message/quiz/poll/image."""
    try:
        chat_id = update.effective_chat.id
        language = language_manager.get_language(chat_id)
        
        # Check if this is a reply to a message
        if update.message.reply_to_message:
            replied_message = update.message.reply_to_message
            content_to_explain = None
            content_type = 'text'
            
            # Handle quiz/poll
            if replied_message.poll:
                poll = replied_message.poll
                content_to_explain = f"Question: {poll.question}\n\n"
                content_to_explain += "Options:\n"
                for i, option in enumerate(poll.options):
                    content_to_explain += f"{chr(65+i)}) {option.text}\n"
                if poll.type == 'quiz' and poll.correct_option_id is not None:
                    content_to_explain += f"\nCorrect Answer: {chr(65+poll.correct_option_id)}"
                content_type = 'quiz'
            
            # Handle text message
            elif replied_message.text:
                content_to_explain = replied_message.text
                content_type = 'text'
            
            # Handle image with caption
            elif replied_message.photo:
                if replied_message.caption:
                    content_to_explain = replied_message.caption
                    content_type = 'text'
                else:
                    await update.message.reply_text(
                        "╔═══════════════════════════════╗\n"
                        "║   ❌ CAPTION REQUIRED ❌       ║\n"
                        "╚═══════════════════════════════╝\n\n"
                        "📸 Image needs a caption!\n\n"
                        "💡 **How to:**\n"
                        "1. Add caption to image\n"
                        "2. Reply with /explain\n\n"
                        "📝 **Example:**\n"
                        "Caption: 'What is this diagram?'\n\n"
                        "【~@DrQuizRobot】"
                    )
                    return
            
            # Handle other message types
            else:
                await update.message.reply_text(
                    "╔═══════════════════════════════╗\n"
                    "║   ❌ UNSUPPORTED TYPE ❌       ║\n"
                    "╚═══════════════════════════════╝\n\n"
                    "✅ **I can explain:**\n"
                    "• Text messages\n"
                    "• Quiz questions\n"
                    "• Poll questions\n"
                    "• Images with captions\n\n"
                    "【~@DrQuizRobot】"
                )
                return
            
            if not content_to_explain:
                await update.message.reply_text(
                    "╔═══════════════════════════════╗\n"
                    "║   ❌ NO CONTENT FOUND ❌       ║\n"
                    "╚═══════════════════════════════╝\n\n"
                    "😔 Could not extract content\n\n"
                    "🔄 Try replying to different message\n\n"
                    "【~@DrQuizRobot】"
                )
                return
        
        # Handle direct text after /explain command
        elif context.args and len(context.args) > 0:
            content_to_explain = ' '.join(context.args)
            content_type = 'text'
        
        else:
            await update.message.reply_text(
                "╔═══════════════════════════════╗\n"
                "║      ❌ INVALID FORMAT ❌       ║\n"
                "╚═══════════════════════════════╝\n\n"
                "📝 **How to use /explain:**\n\n"
                "1️⃣ **Direct Question:**\n"
                "/explain [your question]\n\n"
                "2️⃣ **Reply to Message:**\n"
                "Reply to quiz/poll with /explain\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📖 **Examples:**\n\n"
                "• /explain What is mitochondria?\n"
                "• /explain Thermodynamics laws\n"
                "• Reply to quiz: /explain\n\n"
                "【~@DrQuizRobot】"
            )
            return
        
        # Send "generating" message
        generating_msg = await update.message.reply_text(
            "╔═══════════════════════════════╗\n"
            "║  🔍 GENERATING EXPLANATION 🔍 ║\n"
            "╚═══════════════════════════════╝\n\n"
            "⚡ AI is analyzing your question...\n"
            "⏳ Please wait a moment...\n\n"
            "【~@DrQuizRobot】"
        )
        
        # Generate explanation
        logger.info(f"Generating explanation for content: {content_to_explain[:100]}..., language={language}")
        raw_explanation = quiz_gen.generate_explanation(content_to_explain, content_type, language)
        
        # Delete "generating" message
        try:
            await generating_msg.delete()
        except:
            pass
        
        # Format explanation beautifully
        formatted_explanation = f"""╔═══════════════════════════════════════╗
║       💡 AI EXPLANATION 💡            ║
╚═══════════════════════════════════════╝

📚 **EXPLANATION:**

{raw_explanation}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 **KEY POINTS:**
✅ Focus on NCERT concepts
✅ Practice similar questions
✅ Understand the logic, not just memorize

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📖 Need more help? Ask another question!

【~@DrQuizRobot】"""
        
        # Send explanation (split if too long for Telegram)
        max_length = 4000
        if len(formatted_explanation) > max_length:
            # If too long, send raw explanation without heavy formatting
            simple_format = f"""💡 **EXPLANATION:**

{raw_explanation}

【~@DrQuizRobot】"""
            await update.message.reply_text(simple_format)
        else:
            await update.message.reply_text(formatted_explanation)
        
        logger.info(f"Successfully sent explanation for chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Error in explain_command: {e}", exc_info=True)
        await update.message.reply_text(
            "╔═══════════════════════════════╗\n"
            "║      ❌ ERROR ❌               ║\n"
            "╚═══════════════════════════════╝\n\n"
            "⚠️ Could not generate explanation\n\n"
            "🔄 Please try again later\n\n"
            "【~@DrQuizRobot】"
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")

async def post_init(application: Application) -> None:
    """Initialize database connection and inject repository into live quiz coordinator."""
    try:
        logger.info("Initializing database connection...")
        await db_pool.initialize()
        
        quiz_repo = QuizSessionRepository(db_pool)
        live_quiz_coordinator.set_repository(quiz_repo)
        
        logger.info("✅ Database and repository initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}", exc_info=True)
        raise

async def post_shutdown(application: Application) -> None:
    """Close database connection on shutdown."""
    try:
        logger.info("Closing database connection...")
        await db_pool.close()
        logger.info("✅ Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}", exc_info=True)

def main():
    """Start the bot."""
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    # User commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("botsupport", botsupport_command))
    application.add_handler(CommandHandler("developer", developer_command))
    application.add_handler(CommandHandler("donate", donate_command))
    application.add_handler(CommandHandler("cquiz", create_quiz))
    application.add_handler(CommandHandler("quiz", timed_quiz_command))
    application.add_handler(CommandHandler("stopquiz", stop_quiz_command))
    application.add_handler(CommandHandler("end", end_quiz_command))
    application.add_handler(CommandHandler("explain", explain_command))
    application.add_handler(CommandHandler("myid", myid_command))
    
    # Admin commands
    application.add_handler(CommandHandler("fjoin", fjoin_command))
    application.add_handler(CommandHandler("removefjoin", removefjoin_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("promote", promote_command))
    application.add_handler(CommandHandler("remove", remove_admin_command))
    application.add_handler(CommandHandler("adminlist", adminlist_command))
    application.add_handler(CommandHandler("startlivequiz", startlivequiz_command))
    application.add_handler(CommandHandler("endlivequiz", endlivequiz_command))
    application.add_handler(CommandHandler("forceliveleaderboard", forceliveleaderboard_command))
    application.add_handler(CommandHandler("fgloballeaderboard", fgloballeaderboard_command))
    application.add_handler(CommandHandler("fgroupleaderboard", fgroupleaderboard_command))
    
    # User utility commands
    application.add_handler(CommandHandler("refresh", refresh_command))
    
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
    
    # Message forwarding system: User -> Admin
    # Forward all non-command messages from private chats to admin group
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & ~filters.COMMAND,
            forward_user_message_to_admin
        ),
        group=0
    )
    
    # Message forwarding system: Admin -> User
    # Handle admin replies in admin group and send them to users
    ADMIN_GROUP_ID = -1003049872361
    application.add_handler(
        MessageHandler(
            filters.Chat(chat_id=ADMIN_GROUP_ID) & filters.REPLY,
            handle_admin_reply
        ),
        group=0
    )
    
    # Track all group messages for tagall functionality
    application.add_handler(MessageHandler(filters.ALL, track_group_members), group=1)
    
    # Poll answer handler for timed quiz
    application.add_handler(PollAnswerHandler(handle_poll_answer))
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(anonymous_verification_callback, pattern="^verify:"))
    application.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    application.add_handler(CallbackQueryHandler(quiz_time_callback, pattern="^quiz_time_"))
    application.add_handler(CallbackQueryHandler(livequiz_count_callback, pattern="^livequiz_count_"))
    application.add_handler(CallbackQueryHandler(livequiz_time_callback, pattern="^livequiz_time_"))
    application.add_handler(CallbackQueryHandler(check_membership_callback, pattern="^check_membership$"))
    
    application.add_error_handler(error_handler)
    
    # Schedule periodic admin cache refresh (every 5 minutes)
    application.job_queue.run_repeating(refresh_admin_cache, interval=300, first=60)
    
    # Schedule daily good morning wishes at 6:00 AM IST (00:30 UTC)
    # IST is UTC+5:30, so 6:00 AM IST = 00:30 UTC
    application.job_queue.run_daily(
        send_good_morning_wishes,
        time=dt_time(hour=0, minute=30, second=0),
        days=(0, 1, 2, 3, 4, 5, 6)
    )
    
    logger.info("Bot is starting...")
    
    # Check if we need to run a web server for health checks (for platforms like Render)
    port = os.environ.get('PORT')
    if port:
        # Run web server alongside bot polling for platforms that require a port
        asyncio.run(run_with_webserver(application, int(port)))
    else:
        # Just run polling (for local development or platforms that don't need a port)
        application.run_polling(allowed_updates=Update.ALL_TYPES)

async def health_check(request):
    """Health check endpoint for web service platforms."""
    return web.Response(text="Bot is running!")

async def run_with_webserver(application, port):
    """Run the Telegram bot polling alongside a web server for health checks."""
    # Start the telegram application
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    # Create and start web server
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    logger.info(f"Starting web server on port {port}...")
    await site.start()
    logger.info(f"Web server started! Health check available at http://0.0.0.0:{port}/health")
    
    # Keep running
    try:
        await asyncio.Event().wait()
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await runner.cleanup()

if __name__ == '__main__':
    main()
