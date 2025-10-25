import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from bot.config import TELEGRAM_BOT_TOKEN, MIN_QUESTIONS, MAX_QUESTIONS
from bot.quiz_generator import QuizGenerator

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

quiz_gen = QuizGenerator()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    welcome_message = """
🎓 Welcome to AUTO QUIZ CREATE BOT! 【~@DrQuizRobot】

I generate NEET-relevant medical entrance exam questions from NCERT Class 11th and 12th textbooks.

📚 How to use:
/cquiz [chapter name] [number of questions]

📖 Examples:
/cquiz Human Physiology 5
/cquiz Thermodynamics 10
/cquiz Cell Biology 15

✅ Features:
• NEET-standard MCQs
• Questions from NCERT Biology, Physics & Chemistry
• 4 options per question
• Quiz format with correct answers
• 1-20 questions per request

📝 Subjects Covered:
• Biology (Class 11 & 12)
• Physics (Class 11 & 12)
• Chemistry (Class 11 & 12)

Start creating your quiz now! 🚀
"""
    await update.message.reply_text(welcome_message)

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
        
        await update.message.reply_text(
            f"🔄 Generating {num_questions} NEET-level questions for '{chapter}'...\n"
            f"Please wait a moment... 【~@DrQuizRobot】"
        )
        
        logger.info(f"Generating quiz: chapter='{chapter}', questions={num_questions}")
        questions = quiz_gen.generate_quiz(chapter, num_questions)
        
        if not questions:
            await update.message.reply_text(
                "❌ Failed to generate questions. Please try again with a different chapter name."
            )
            return
        
        for i, q in enumerate(questions, 1):
            try:
                await update.message.reply_poll(
                    question=f"{i}. {q['question']}\n\n【~@DrQuizRobot】",
                    options=q['options'],
                    type='quiz',
                    correct_option_id=q['correct_answer'],
                    is_anonymous=False,
                    explanation=q.get('explanation', ''),
                )
            except Exception as e:
                logger.error(f"Error sending quiz {i}: {e}")
                formatted = quiz_gen.format_question_with_watermark(i, q)
                formatted += f"\n✅ Correct Answer: {chr(65 + q['correct_answer'])}) {q['options'][q['correct_answer']]}"
                await update.message.reply_text(formatted)
        
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

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cquiz", create_quiz))
    
    application.add_error_handler(error_handler)
    
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
