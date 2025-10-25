# AUTO QUIZ CREATE BOT 🎓

A Telegram bot that generates NEET-relevant medical entrance exam questions from NCERT Class 11th and 12th textbooks using Google's Gemini AI.

## Features

- 🎯 Generate NEET-standard MCQs from NCERT chapters
- 📚 Covers Biology, Physics, and Chemistry (Class 11 & 12)
- ✅ Telegram native quiz format with correct answers
- 🔖 Custom watermark: 【~@DrQuizRobot】
- 📊 1-20 questions per quiz
- ⚡ Powered by Google Gemini AI

## Usage

### Commands

- `/start` - Welcome message and instructions
- `/help` - Show help information
- `/cquiz [chapter name] [number of questions]` - Generate a quiz

### Examples

```
/cquiz Human Physiology 5
/cquiz Thermodynamics 10
/cquiz Biomolecules 8
/cquiz Chemical Bonding 12
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Google API Key (for Gemini AI)

### Local Development

1. Clone the repository:
```bash
git clone <your-repo-url>
cd <your-repo-name>
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

4. Add your API keys to `.env`:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GOOGLE_API_KEY=your_google_api_key_here
```

5. Run the bot:
```bash
python -m bot.main
```

## Deployment on Render

### Method 1: Using render.yaml (Recommended)

1. Push your code to GitHub
2. Connect your GitHub repository to Render
3. Render will automatically detect `render.yaml`
4. Add environment variables in Render dashboard:
   - `TELEGRAM_BOT_TOKEN`
   - `GOOGLE_API_KEY`
5. Deploy!

### Method 2: Manual Setup

1. Create a new Web Service on Render
2. Connect your repository
3. Configure:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m bot.main`
4. Add environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `GOOGLE_API_KEY`
5. Deploy!

## Getting API Keys

### Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the bot token provided

### Google Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the generated API key

## Project Structure

```
.
├── bot/
│   ├── __init__.py
│   ├── config.py          # Configuration and environment variables
│   ├── main.py            # Main bot logic and command handlers
│   └── quiz_generator.py  # Quiz generation using Gemini AI
├── .env.example           # Example environment variables
├── render.yaml            # Render deployment configuration
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## How It Works

1. User sends `/cquiz [chapter] [number]` command
2. Bot validates the input (1-20 questions)
3. Gemini AI generates NEET-level MCQs based on the chapter
4. Questions are sent as Telegram polls/quizzes
5. Each question includes the watermark 【~@DrQuizRobot】
6. Correct answers are marked in the quiz format

## Technical Details

- **Bot Framework**: python-telegram-bot (v22.5)
- **AI Model**: Google Gemini 2.5 Flash
- **Language**: Python 3.11
- **Deployment**: Render (or any Python hosting platform)

## Error Handling

The bot includes comprehensive error handling for:
- Invalid chapter names
- Out of range question numbers (must be 1-20)
- API failures
- Malformed responses
- Network issues

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the MIT License.

## Support

For issues or questions, please open an issue on GitHub or contact the maintainer.

---

**Made with ❤️ for NEET aspirants**
