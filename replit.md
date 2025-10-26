# AUTO QUIZ CREATE BOT

## Overview

A Telegram bot that generates NEET-relevant medical entrance exam questions from NCERT Class 11th and 12th textbooks using Google's Gemini AI. The bot creates native Telegram quiz polls with multiple-choice questions covering Biology, Physics, and Chemistry topics at medical entrance exam standards.

## Recent Changes

**October 26, 2025** (Latest Update - Part 8):
- ✅ **NEW FEATURE**: Global Live Quiz System
  - Bot admins can run synchronized quizzes across ALL groups simultaneously using `/startlivequiz <chapter>`
  - 5-minute countdown reminder sent to all groups before quiz starts
  - 20 questions broadcast simultaneously to all participating groups
  - 45-second timer per question with synchronized auto-advance
  - Real-time participant tracking across all groups globally
  - Unified global leaderboard showing rank, marks, attempts, accuracy, and time
  - NEET scoring pattern: +4 correct, -1 wrong, 0 unattempted
  - Poll-to-question mapping system for reliable answer tracking
  - Automatic cleanup of poll mappings to prevent memory leaks
  - Integrates with quiz lock manager to prevent concurrent quizzes
  - Created `live_quiz_manager.py` with LiveQuizCoordinator and LiveQuizSession classes
  - Beautiful decorated global leaderboard broadcast to all groups after completion

**October 26, 2025** (Latest Update - Part 7):
- ✅ **FIXED**: Anonymous Admin Verification Bug
  - Fixed critical bug where verified anonymous admins were still shown as "not admin"
  - Issue: Code was assigning Chat object instead of User object to effective_user
  - Now properly uses verified user from callback query (query.from_user)
  - Anonymous group owners can now successfully use admin commands after verification
  - Updated `anonymous_verifier.py` to correctly handle user object assignment

**October 26, 2025** (Part 6):
- ✅ **QUIZ MUTUAL EXCLUSION**: Implemented Quiz Lock Manager
  - Only one quiz can run at a time per group/chat (whether /cquiz or /quiz)
  - Created `quiz_lock_manager.py` for centralized quiz concurrency control
  - Both /cquiz and /quiz commands now check for active quizzes before starting
  - Informative messages when users try to start concurrent quizzes
  - Proper lock acquisition and release in all success and error paths
  - Prevents race conditions and ensures clean quiz state management
  - Production-ready with defensive error handling and lock leak prevention
  - **Fixed lock leak bug**: `/stopquiz` now properly releases quiz lock

**October 26, 2025** (Latest Update - Part 5):
- ✅ **NEW FEATURE**: Daily Good Morning Wishes at 6 AM IST
  - Automated daily broadcast to all users and groups at 6:00 AM Indian time
  - Beautiful, decorated messages with margins, emojis, and elegant formatting
  - 39 English and 15 Hindi motivational/inspirational quotes
  - Language-specific messages based on user/group preferences
  - Includes clickable "Aman" link to @Aman_PersonalBot
  - Scheduled using APScheduler with proper error handling
  - Created `good_morning_manager.py` for message generation
  - Broadcasts to all tracked users and groups automatically

**October 26, 2025** (Latest Update - Part 4):
- ✅ **NEW COMMAND**: `/explain` - Concise Question & Concept Explanations
  - Direct text explanations: `/explain [question or topic]`
  - Reply to messages with `/explain` to get explanations
  - Works with text messages, quizzes, polls, and images with captions
  - Explanations generated in selected language (Hindi/English via `/language`)
  - Uses Gemini AI for accurate, to-the-point NEET-focused explanations
  - Maximum 5 lines - concise, accurate, and exam-focused
  - Includes correct answer, key concept, and NCERT reference
  - Added explanation generator method in `quiz_generator.py`
  - Updated help command with `/explain` usage instructions

**October 26, 2025** (Latest Update - Part 3):
- ✅ **Implemented Member Tracking Database for /tagall**
  - Created persistent member tracking system (`data/tracked_members.json`)
  - Bot automatically tracks all users who send messages in groups
  - Stores user ID, first name, username, admin status, and last seen timestamp
  - `/tagall` command now uses tracked database instead of API calls
  - Works around Telegram Bot API limitation (cannot fetch full member list)
  - Members are tracked over time as they interact with the group
  - Admins are automatically excluded from tagging
  - Provides clear feedback when no non-admin members are tracked yet

**October 26, 2025** (Earlier - Part 2):
- ✅ **Modified /tagall Command**
  - Added 60+ funny, teasing, engaging questions in Hindi/Hinglish style
  - Updated format: `User mention : Question` with margin (double newline) between users
  - Batching: 15 users per message
  - Excludes bots and anonymous users

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
   - NEW: `generate_explanation()` method for concise concept/question explanations (max 5 lines)
   - Provides accurate, to-the-point explanations with NCERT references

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
   - Automatically tracks all group members who send messages
   - Persistent member database (`data/tracked_members.json`)
   - Tags members with funny Hindi/Hinglish questions
   - Configurable permissions (admin-only or all-users)
   - Uses text-mention format `[Name](tg://user?id=X)`
   - Excludes admins automatically from tagging
   - Batches of 15 members per message

8. **Anonymous Admin Verification** (`anonymous_verifier.py`):
   - Handles Telegram anonymous admin restrictions
   - Token-based verification with inline buttons
   - 5-minute timeout for pending verifications
   - DM-based verification flow

9. **Good Morning Wishes** (`good_morning_manager.py`):
   - Daily automated good morning messages at 6:00 AM IST
   - 39 English motivational quotes and 15 Hindi quotes
   - Beautiful formatting with decorative borders and emojis
   - Bilingual support based on user/group language preferences
   - Clickable link to @Aman_PersonalBot in every message
   - Scheduled broadcast to all tracked users and groups

### Data Persistence

**JSON File Storage**: All data stored in flat JSON files for simplicity:
- `bot_stats.json`: User/group stats, quiz metrics
- `bot_admins.json`: Dynamic admin user IDs
- `force_join_data.json`: Required channels/groups
- `data/language_settings.json`: Per-chat language preferences
- `data/tagall_permissions.json`: Per-group tagall permissions
- `data/tracked_members.json`: Member tracking database for tagall feature
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