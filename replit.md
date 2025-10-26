# AUTO QUIZ CREATE BOT

## Overview

A Telegram bot that generates NEET-relevant medical entrance exam questions from NCERT Class 11th and 12th textbooks using Google's Gemini AI. The bot creates native Telegram quiz polls with multiple-choice questions covering Biology, Physics, and Chemistry topics at medical entrance exam standards.

## Recent Changes

**October 26, 2025** (Latest Update - Part 2):
- ✅ **Modified /tagall Command**
  - Added 60+ funny, teasing, engaging questions in Hindi/Hinglish style
  - Updated format: `User mention : Question` with margin (double newline) between users
  - Batching: 15 users per message
  - Excludes bots and anonymous users
  - ⚠️ **Telegram API Limitation**: Bot API can only see administrators and recently active members
  - Non-admin members cannot be detected unless they've recently sent messages
  - Added clear error message explaining this limitation

**October 26, 2025** (Latest Update - Part 1):
- ✅ **NEET Scoring Pattern Implemented**
  - Correct answers now give +4 marks (instead of +1)
  - Wrong answers now give -1 mark (instead of 0)
  - Unattempted questions give 0 marks
  - Added NEET scoring constants to `config.py`
  - Updated `quiz_session_manager.py` to use NEET scoring pattern
- ✅ **NEW COMMAND**: `/end` - End Timer Quiz Early
  - Works only during active timer quiz sessions
  - Stops the quiz immediately and shows leaderboard
  - Displays results for questions answered so far
  - Cancels auto-advance task gracefully
- ✅ **Updated Help Command**
  - Added documentation for `/end` command
  - Explained NEET scoring pattern to users
  - Improved command examples and formatting
- ✅ **Fixed** `finalize_quiz` function to use actual question count instead of hardcoded 20

**October 26, 2025** (Earlier):
- ✅ **NEW FEATURE**: Timed Quiz Sessions with Leaderboard
  - Added `/quiz [chapter]` command for 20-question timed quiz sessions
  - Each question has 45-second timer with auto-advance
  - **Smart Advancement**: Private chats advance instantly after answering; Groups wait for full timer
  - Real-time participant tracking and score calculation
  - Beautiful premium leaderboard with rankings, accuracy, and time stats
  - Enhanced quiz generator: Biology gets 50% NCERT exact-line + 50% NEET PYQs
  - Physics/Chemistry gets 100% NEET PYQs (2015-2024)
  - Fixed double-counting when users change poll answers
  - Added Markdown escaping for safe leaderboard rendering
- ✅ Created `quiz_session_manager.py` for session state management
- ✅ Created `leaderboard_generator.py` with premium formatting
- ✅ Added `/stopquiz` command to cancel active quiz sessions

**October 25, 2025**:
- ✅ Implemented anonymous admin verification system for Telegram groups
- ✅ Updated `bot_or_group_admin_only` decorator to handle anonymous admins safely
- ✅ Added verification callback handler to process anonymous admin verification buttons
- ✅ Fixed critical bug: Moved anonymous admin check before accessing `effective_user.id` to prevent crashes
- ✅ Bot now sends verification buttons when anonymous admins use admin commands
- ✅ Added safety guard to check `effective_user` exists before accessing its properties

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Application Structure

**Bot Framework**: Python-based Telegram bot using python-telegram-bot library with async/await patterns for handling user interactions and commands.

**Command Handler System**: Decorator-based access control with three permission levels:
- `admin_only`: Restricts to permanent/dynamic bot admins
- `bot_or_group_admin_only`: Allows bot admins or group/channel admins
- Anonymous admin verification: Special handling for anonymous group admins using inline verification buttons

**Core Components**:

1. **Quiz Generation Engine** (`quiz_generator.py`): 
   - Uses Google Gemini 2.5 Flash model for AI-powered question generation
   - Supports bilingual output (English/Hindi)
   - Generates NEET-standard MCQs with detailed explanations
   - Validates and parses JSON responses from LLM

2. **Admin Management** (`admin_manager.py`):
   - Dual-tier system: permanent admins (configured) + dynamic admins (runtime)
   - Persistent storage in `bot_admins.json`
   - Add/remove admin capabilities for authorized users

3. **Force Join System** (`force_join.py`):
   - Manages required channel/group memberships (max 5)
   - Verifies user membership before allowing quiz generation
   - Persistent storage in `force_join_data.json`
   - Inline keyboard prompts for non-members

4. **Statistics Tracking** (`stats_manager.py`):
   - Tracks unique users, groups, quiz counts, question counts
   - Persistent storage in `bot_stats.json`
   - Runtime metrics since bot start time

5. **Welcome System** (`welcome_manager.py`):
   - Configurable per-group welcome messages
   - Hindi shayari/poetic greetings collection
   - Opt-in per group via admin commands

6. **Language Management** (`language_manager.py`):
   - Per-chat language preferences (Hindi/English)
   - Affects quiz question generation language
   - Stored in `data/language_settings.json`

7. **Tag All Feature** (`tagall_manager.py`):
   - Mentions all group members in a single message
   - Configurable permissions (admin-only or all-users)
   - Uses silent mentions to avoid spam notifications

8. **Anonymous Admin Verification** (`anonymous_verifier.py`):
   - Handles Telegram anonymous admin restrictions
   - Token-based verification with inline buttons
   - 5-minute timeout for pending verifications
   - DM-based verification flow

### Data Persistence

**JSON File Storage**: All data stored in flat JSON files for simplicity:
- `bot_stats.json`: User/group stats, quiz metrics
- `bot_admins.json`: Dynamic admin user IDs
- `force_join_data.json`: Required channels/groups
- `data/language_settings.json`: Per-chat language preferences
- `data/tagall_permissions.json`: Per-group tagall permissions
- `data/welcome_groups.json`: Groups with welcome messages enabled

**Design Rationale**: Chosen over databases for:
- Simple deployment without database setup
- Easy backup and version control
- Sufficient for expected scale (hundreds of users/groups)
- Direct file access for debugging

### Configuration Management

**Environment Variables**: Sensitive credentials stored in `.env`:
- `TELEGRAM_BOT_TOKEN`: Bot authentication
- `GOOGLE_API_KEY`: Gemini AI access
- `ADMIN_USER_IDS`: Optional permanent admin IDs

**Static Configuration** (`config.py`):
- Quiz parameters (MIN_QUESTIONS=1, MAX_QUESTIONS=20)
- Watermark text for questions
- Permanent admin user IDs

### Quiz Generation Workflow

1. User sends `/cquiz [chapter] [count]` command
2. Force join verification (if configured)
3. Input validation (chapter name, question count 1-20)
4. Language detection from chat settings
5. LLM prompt construction with NEET-specific requirements
6. Gemini API call with structured JSON response format
7. Response parsing and validation
8. Telegram native poll creation with correct answer marking
9. Stats update (quiz count, question count)

## External Dependencies

### Third-Party APIs

**Google Gemini AI** (`google-generativeai` package):
- Model: gemini-2.5-flash
- Purpose: Generate NEET-standard MCQ questions
- Response format: Structured JSON with questions, options, answers, explanations
- Authentication: API key via environment variable

**Telegram Bot API** (`python-telegram-bot` library):
- Async interface for bot operations
- Handles commands, callbacks, message handlers
- Native quiz/poll creation
- Group administration APIs (member status checks)
- Inline keyboard interactions

### Python Dependencies

Core libraries (from deployment context):
- `python-telegram-bot`: Telegram bot framework
- `google-generativeai`: Gemini AI SDK  
- `python-dotenv`: Environment variable management
- Standard library: `json`, `logging`, `datetime`, `pathlib`, `re`, `uuid`, `time`

### Hosting Requirements

**Deployment Platform**: Designed for Render.com (documented in DEPLOYMENT.md):
- `render.yaml` configuration for automatic deployment
- Web service type (keeps bot alive)
- Environment variables configured in Render dashboard
- No database required (file-based storage)

**Runtime Requirements**:
- Python 3.11+
- Persistent file storage for JSON data files
- Outbound HTTPS for Telegram/Google APIs
- Always-on service (long-polling mode)