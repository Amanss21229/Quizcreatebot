# AUTO QUIZ CREATE BOT

## Overview

A Telegram bot designed to generate NEET-relevant medical entrance exam questions from NCERT Class 11th and 12th textbooks. Utilizing Google's Gemini AI, the bot creates native Telegram quiz polls with multiple-choice questions covering Biology, Physics, and Chemistry, tailored to medical entrance exam standards. The project aims to provide an efficient and interactive study tool for NEET aspirants.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Application Structure

**Bot Framework**: Python-based Telegram bot leveraging the `python-telegram-bot` library with async/await for handling user interactions.

**Command Handler System**: Access control implemented with decorator-based permissions (`admin_only`, `bot_or_group_admin_only`, `group_admin_only`), including a special anonymous admin verification flow. The `group_admin_only` decorator allows everyone in private chats while restricting to admins in groups.

**Core Components**:

- **Quiz Generation Engine** (`quiz_generator.py`): Employs Google Gemini 2.5 Flash for AI-powered question generation, supporting bilingual output (English/Hindi), NEET-standard MCQs, detailed explanations (max 5 lines with NCERT references), and JSON response validation.
- **Admin Management** (`admin_manager.py`): Manages permanent and dynamic bot administrators with persistent storage.
- **Force Join System** (`force_join.py`): Verifies user membership in required channels/groups before quiz generation.
- **Statistics Tracking** (`stats_manager.py`): Monitors user, group, and quiz metrics.
- **Welcome System** (`welcome_manager.py`): Provides configurable, per-group welcome messages with Hindi shayari.
- **Language Management** (`language_manager.py`): Stores per-chat language preferences (Hindi/English) for quiz generation.
- **Tag All Feature** (`tagall_manager.py`): Tracks group members and allows admins to tag them with engaging questions, excluding other admins.
- **Anonymous Admin Verification** (`anonymous_verifier.py`): Handles Telegram's anonymous admin limitations via token-based inline verification.
- **Good Morning Wishes** (`good_morning_manager.py`): Automated daily motivational messages broadcast to all users and groups, with bilingual support and elegant formatting.
- **Quiz Lock Manager** (`quiz_lock_manager.py`): Ensures mutual exclusion, allowing only one quiz per group/chat at a time.
- **Global Live Quiz System** (`live_quiz_manager.py`): Facilitates synchronized quizzes across all groups simultaneously, including countdowns, real-time tracking, and a unified global leaderboard with NEET scoring.

### Data Persistence

**JSON File Storage**: All application data is stored in flat JSON files for simplicity and ease of deployment:
- `bot_stats.json`: User/group statistics.
- `bot_admins.json`: Dynamic admin user IDs.
- `force_join_data.json`: Required channels/groups.
- `data/language_settings.json`: Per-chat language preferences.
- `data/tagall_permissions.json`: Per-group tagall permissions.
- `data/tracked_members.json`: Member tracking database for the tagall feature.
- `data/welcome_groups.json`: Groups with enabled welcome messages.

### Configuration Management

**Environment Variables**: Sensitive credentials (e.g., `TELEGRAM_BOT_TOKEN`, `GOOGLE_API_KEY`, `ADMIN_USER_IDS`) are managed via `.env` files.

**Static Configuration** (`config.py`): Contains quiz parameters (e.g., `MIN_QUESTIONS`, `MAX_QUESTIONS`), watermark text, and permanent admin user IDs.

### Quiz Generation Workflow

The workflow involves user command parsing, force join verification, input validation, language detection, LLM prompt construction, Gemini API call for structured JSON, response parsing, Telegram native poll creation, and statistics updates. Quizzes support NEET scoring (+4 for correct, -1 for wrong, 0 for unattempted).

**Timed Quiz Feature**: The `/quiz` command now includes a customizable timer selection interface. After generating questions, users are presented with inline keyboard buttons to choose their preferred time per question (15s, 30s, 45s, or 60s). The selected timing is stored in the quiz session and applied consistently across all 20 questions, with auto-advance functionality using the chosen duration plus a 2-second buffer.

**Leaderboard Features**: All leaderboards (regular quiz and global live quiz) now display user names as clickable Telegram profile links using the format `[Name](tg://user?id=USER_ID)`, enabling easy access to participant profiles. Additionally, leaderboards include a help message informing users they can reply to any quiz question with `/explain` to receive detailed AI-powered explanations. All markdown special characters are properly escaped to ensure correct rendering across all user scenarios.

## External Dependencies

### Third-Party APIs

- **Google Gemini AI** (`google-generativeai`): Used for generating NEET-standard MCQ questions and explanations.
- **Telegram Bot API** (`python-telegram-bot`): Provides the core interface for bot operations, including command handling, poll creation, and group administration.

### Python Dependencies

- `python-telegram-bot`: The primary framework for Telegram bot development.
- `google-generativeai`: SDK for interacting with Google Gemini AI.
- `python-dotenv`: For managing environment variables.
- `APScheduler`: For scheduling recurring tasks like daily good morning messages.
- Standard Python libraries: `json`, `logging`, `datetime`, `pathlib`, `re`, `uuid`, `time`.

### Hosting Requirements

- **Deployment Platform**: Designed for Render.com as a web service.
- **Runtime Requirements**: Python 3.11+, persistent file storage, and continuous internet connectivity.