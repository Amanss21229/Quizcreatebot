# Testing Guide for AUTO QUIZ CREATE BOT

## Local Testing

### Prerequisites
- Python 3.11+ installed
- API keys configured in environment variables

### Running Locally

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Set Environment Variables**:
Create a `.env` file (copy from `.env.example`):
```bash
cp .env.example .env
```

Edit `.env` and add your actual keys:
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GOOGLE_API_KEY=your_google_api_key_here
```

3. **Run the Bot**:
```bash
python -m bot.main
```

Or use the helper script:
```bash
python run.py
```

4. **Test on Telegram**:
- Open Telegram
- Search for your bot
- Start testing commands

---

## Manual Testing Checklist

### Basic Commands
- [ ] `/start` - Displays welcome message
- [ ] `/help` - Shows help information
- [ ] `/cquiz` without args - Shows error message

### Valid Quiz Generation
- [ ] `/cquiz Cell Biology 5` - Generates 5 questions
- [ ] `/cquiz Human Physiology 10` - Generates 10 questions
- [ ] `/cquiz Thermodynamics 1` - Generates 1 question (minimum)
- [ ] `/cquiz Chemical Bonding 20` - Generates 20 questions (maximum)

### Error Handling
- [ ] `/cquiz` - Shows usage error
- [ ] `/cquiz NoChapter` - Shows missing number error
- [ ] `/cquiz Test abc` - Shows invalid number error
- [ ] `/cquiz Test 0` - Shows out of range error (too few)
- [ ] `/cquiz Test 25` - Shows out of range error (too many)
- [ ] `/cquiz Test -5` - Shows out of range error (negative)

### Quiz Format Validation
- [ ] Each question has watermark 【~@DrQuizRobot】
- [ ] Each question has exactly 4 options (A, B, C, D)
- [ ] Questions are sent as Telegram polls/quizzes
- [ ] Correct answer is marked in the quiz
- [ ] Explanation is provided when available

### Subject Coverage
Test questions from different subjects:
- [ ] Biology chapter (e.g., Cell Biology, Genetics)
- [ ] Physics chapter (e.g., Thermodynamics, Optics)
- [ ] Chemistry chapter (e.g., Chemical Bonding, Organic Chemistry)

---

## Automated Testing

### Unit Tests (Future Enhancement)

Create `tests/test_quiz_generator.py`:
```python
import pytest
from bot.quiz_generator import QuizGenerator

def test_quiz_generator_initialization():
    qg = QuizGenerator()
    assert qg.model is not None

def test_generate_quiz():
    qg = QuizGenerator()
    questions = qg.generate_quiz("Cell Biology", 2)
    assert len(questions) == 2
    assert all('question' in q for q in questions)
    assert all('options' in q for q in questions)
    assert all(len(q['options']) == 4 for q in questions)

def test_format_with_watermark():
    qg = QuizGenerator()
    question_data = {
        'question': 'Test question?',
        'options': ['A', 'B', 'C', 'D'],
        'correct_answer': 1
    }
    formatted = qg.format_question_with_watermark(1, question_data)
    assert '【~@DrQuizRobot】' in formatted
    assert 'Test question?' in formatted
```

Run tests:
```bash
pytest tests/
```

---

## Component Testing

### Test Configuration
```bash
python -c "from bot.config import TELEGRAM_BOT_TOKEN, GOOGLE_API_KEY, WATERMARK; print('✅ Config OK')"
```

### Test Quiz Generator
```bash
python -c "
from bot.quiz_generator import QuizGenerator
qg = QuizGenerator()
questions = qg.generate_quiz('Test Chapter', 2)
print(f'Generated {len(questions)} questions')
"
```

### Test Telegram Bot Connectivity
```bash
python -c "
from telegram import Bot
from bot.config import TELEGRAM_BOT_TOKEN
bot = Bot(token=TELEGRAM_BOT_TOKEN)
me = bot.get_me()
print(f'Bot connected: {me.username}')
"
```

---

## Performance Testing

### Response Time
Test how long it takes to generate quizzes of different sizes:

```bash
python -c "
import time
from bot.quiz_generator import QuizGenerator

qg = QuizGenerator()

for n in [1, 5, 10, 20]:
    start = time.time()
    questions = qg.generate_quiz('Cell Biology', n)
    duration = time.time() - start
    print(f'{n} questions: {duration:.2f}s')
"
```

Expected times (approximate):
- 1 question: 2-4 seconds
- 5 questions: 4-8 seconds
- 10 questions: 8-15 seconds
- 20 questions: 15-30 seconds

---

## Question Quality Testing

### Manual Review Checklist
Review generated questions for:
- [ ] Scientific accuracy
- [ ] NEET-appropriate difficulty
- [ ] Clear wording
- [ ] No ambiguous options
- [ ] Relevant to specified chapter
- [ ] Proper grammar and spelling
- [ ] All 4 options are plausible

### Sample Test Chapters
Test with these NCERT chapters:

**Biology:**
- Cell: The Unit of Life
- Biomolecules
- Human Physiology
- Reproduction in Organisms
- Genetics and Evolution

**Physics:**
- Thermodynamics
- Optics
- Modern Physics
- Electrostatics
- Current Electricity

**Chemistry:**
- Chemical Bonding
- Thermodynamics
- Equilibrium
- Organic Chemistry Basics
- Coordination Compounds

---

## Load Testing

### Simulate Multiple Users
```python
# Create a script to simulate concurrent quiz requests
import asyncio
from telegram import Bot

async def simulate_user(bot, chat_id, chapter, n_questions):
    # Simulate user requesting quiz
    pass

# Run multiple concurrent simulations
```

---

## Integration Testing

### Full Flow Test
1. User sends `/cquiz Cell Biology 5`
2. Bot acknowledges request
3. Bot generates 5 questions
4. Bot sends 5 quizzes with proper formatting
5. Bot sends completion message

### Test Script
```python
# tests/test_integration.py
import asyncio
from telegram import Update
from telegram.ext import Application
from bot.main import create_quiz

async def test_full_quiz_flow():
    # Mock update and context
    # Test command handler
    # Verify all steps complete successfully
    pass
```

---

## Error Recovery Testing

Test bot behavior when:
- [ ] API key is invalid
- [ ] Network connection lost
- [ ] Gemini API rate limit exceeded
- [ ] Invalid chapter name provided
- [ ] Gemini returns malformed JSON
- [ ] Telegram API is down

---

## Deployment Testing

Before going live:
1. [ ] Test on staging/test bot first
2. [ ] Verify environment variables in production
3. [ ] Check logs are accessible
4. [ ] Confirm bot responds to commands
5. [ ] Generate sample quizzes
6. [ ] Monitor for 24 hours
7. [ ] Check error rates

---

## Monitoring

### Metrics to Track
- Total commands received
- Success rate of quiz generation
- Average response time
- Error frequency
- Most requested chapters
- User engagement stats

### Logging
All important events are logged:
```python
logger.info(f"Generating quiz: chapter='{chapter}', questions={num_questions}")
logger.error(f"Error in create_quiz: {e}")
```

Check logs for:
- Startup messages
- Command processing
- API calls
- Errors and exceptions

---

## Troubleshooting Tests

If tests fail, check:
1. Environment variables are set
2. API keys are valid
3. Network connectivity
4. Python version (3.11+)
5. All dependencies installed
6. Bot token permissions

---

## Test Data

Example chapters that should work:
- "Cell Biology"
- "Human Physiology"
- "Thermodynamics"
- "Chemical Bonding"
- "Genetics"
- "Optics"
- "Organic Chemistry"

---

## Coverage Goals

Aim for:
- [ ] 100% of commands tested
- [ ] All error paths validated
- [ ] Edge cases covered
- [ ] Different chapter types tested
- [ ] Various question counts verified

---

## Next Steps

After testing:
1. Document any issues found
2. Fix bugs and retest
3. Optimize slow operations
4. Add automated tests
5. Set up CI/CD pipeline

**Happy Testing! 🧪**
