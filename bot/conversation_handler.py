import logging
import json
import re
import asyncio
from typing import Dict, Optional, Tuple, List
import google.generativeai as genai
from bot.config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

genai.configure(api_key=GOOGLE_API_KEY)

class ConversationState:
    def __init__(self):
        self.intent = None
        self.chapter = None
        self.num_questions = None
        self.timer_duration = None
        self.topic = None
        self.quiz_type = None
        self.awaiting_input = None
        self.context = []
    
    def to_dict(self):
        return {
            'intent': self.intent,
            'chapter': self.chapter,
            'num_questions': self.num_questions,
            'timer_duration': self.timer_duration,
            'topic': self.topic,
            'quiz_type': self.quiz_type,
            'awaiting_input': self.awaiting_input,
            'context': self.context
        }
    
    @classmethod
    def from_dict(cls, data):
        state = cls()
        state.intent = data.get('intent')
        state.chapter = data.get('chapter')
        state.num_questions = data.get('num_questions')
        state.timer_duration = data.get('timer_duration')
        state.topic = data.get('topic')
        state.quiz_type = data.get('quiz_type')
        state.awaiting_input = data.get('awaiting_input')
        state.context = data.get('context', [])
        return state

class ConversationAI:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.conversation_states: Dict[Tuple[int, int], ConversationState] = {}
    
    def _get_state_key(self, chat_id: int, user_id: int) -> Tuple[int, int]:
        return (chat_id, user_id)
    
    def get_or_create_state(self, chat_id: int, user_id: int) -> ConversationState:
        key = self._get_state_key(chat_id, user_id)
        if key not in self.conversation_states:
            self.conversation_states[key] = ConversationState()
        return self.conversation_states[key]
    
    def clear_state(self, chat_id: int, user_id: int):
        key = self._get_state_key(chat_id, user_id)
        if key in self.conversation_states:
            del self.conversation_states[key]
    
    async def understand_intent(self, message: str, state: ConversationState) -> Tuple[str, Dict]:
        prompt = f"""You are a helpful AI assistant for a NEET/JEE quiz bot. Analyze the user's message and determine their intent.

Available features:
1. start_quiz - User wants to take a NEET quiz (cquiz or timed quiz)
2. jee_quiz - User wants to take a JEE quiz specifically
3. stop_quiz - User wants to stop/end the current quiz
4. explain_topic - User wants explanation of a topic/concept
5. change_language - User wants to change language
6. general_chat - General conversation or greeting
7. help - User needs help/commands

User message: "{message}"

Previous context: {json.dumps(state.context[-3:] if state.context else [])}

Respond ONLY with a JSON object:
{{
    "intent": "intent_name",
    "confidence": 0.0-1.0,
    "extracted_info": {{
        "chapter": "chapter name if mentioned",
        "topic": "topic if asking for explanation",
        "num_questions": "number if mentioned",
        "quiz_type": "cquiz, timed_quiz, or jeequiz"
    }},
    "needs_clarification": true/false,
    "clarification_needed": "what info is missing"
}}"""
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self.model.generate_content, prompt)
            result_text = response.text.strip()
            
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(result_text)
            
            return result.get('intent', 'general_chat'), result
        except Exception as e:
            logger.error(f"Intent understanding error: {e}")
            return 'general_chat', {'intent': 'general_chat', 'confidence': 0.5}
    
    async def generate_response(self, message: str, intent: str, analysis: Dict, state: ConversationState, chat_id: int, user_id: int) -> Tuple[str, Optional[str]]:
        extracted = analysis.get('extracted_info', {})
        
        if state.awaiting_input:
            return await self._handle_awaited_input(message, state, chat_id, user_id)
        
        if intent == 'start_quiz':
            return await self._handle_quiz_request(message, extracted, state, chat_id, user_id)
        elif intent == 'jee_quiz':
            return await self._handle_jee_quiz_request(message, extracted, state, chat_id, user_id)
        elif intent == 'stop_quiz':
            return await self._handle_stop_quiz(message, state, chat_id, user_id)
        elif intent == 'explain_topic':
            return await self._handle_explanation_request(message, extracted, state, chat_id, user_id)
        elif intent == 'change_language':
            return await self._handle_language_change(state)
        elif intent == 'help':
            response = "Aap mujhse NEET/JEE quiz le sakte ho, koi topic samajh sakte ho, ya language change kar sakte ho! Kya madad chahiye? 😊"
            state.context.append({'role': 'user', 'message': message})
            state.context.append({'role': 'assistant', 'message': response})
            return response, None
        else:
            return await self._handle_general_chat(message, state)
    
    async def _handle_quiz_request(self, message: str, extracted: Dict, state: ConversationState, chat_id: int, user_id: int) -> Tuple[str, Optional[str]]:
        state.intent = 'start_quiz'
        state.context.append({'role': 'user', 'message': message})
        
        chapter = extracted.get('chapter') or state.chapter
        num_questions = extracted.get('num_questions') or state.num_questions
        quiz_type = extracted.get('quiz_type') or state.quiz_type
        
        if not quiz_type:
            state.awaiting_input = 'quiz_type'
            response = (
                "Main aapke liye quiz laga sakta hoon! 📚\n\n"
                "Aapko kaisi quiz chahiye?\n"
                "1️⃣ Timer wali quiz (20 questions, competitive)\n"
                "2️⃣ Simple quiz (aap khud questions choose karo)\n\n"
                "Batao kaun si lagau? 😊"
            )
            state.context.append({'role': 'assistant', 'message': response})
            return (response, None)
        
        if not chapter:
            state.awaiting_input = 'chapter'
            state.quiz_type = quiz_type
            response = (
                "Bilkul! Quiz lagata hoon 🎯\n\n"
                "Kis chapter ka quiz lagau?\n"
                "For example: Human Physiology, Thermodynamics, Cell Biology\n\n"
                "Chapter ka naam batao! 📖"
            )
            state.context.append({'role': 'assistant', 'message': response})
            return (response, None)
        
        state.chapter = chapter
        state.quiz_type = quiz_type
        
        if quiz_type == 'cquiz' and not num_questions:
            state.awaiting_input = 'num_questions'
            response = (
                f"Perfect! {chapter} ka quiz lagata hoon 👍\n\n"
                "Kitne questions chahiye? (1-20 ke beech)\n"
                "Example: 5, 10, 15\n\n"
                "Number batao! 🔢"
            )
            state.context.append({'role': 'assistant', 'message': response})
            return (response, None)
        
        if quiz_type == 'cquiz':
            state.num_questions = num_questions or 10
            command = f"/cquiz {state.chapter} {state.num_questions}"
        else:
            command = f"/quiz {state.chapter}"
        
        response = (
            f"Chalo shuru karte hain! 🚀\n\n"
            f"📚 Chapter: {chapter}\n"
            f"{'📝 Questions: ' + str(state.num_questions) if quiz_type == 'cquiz' else '📝 Questions: 20'}\n"
            f"{'⏱️ Timer: Aap choose karenge' if quiz_type != 'cquiz' else '✨ Type: Custom Quiz'}\n\n"
            f"Quiz loading... ⏳"
        )
        state.context.append({'role': 'assistant', 'message': response, 'command': command})
        self.clear_state(chat_id, user_id)
        
        return (response, command)
    
    async def _handle_explanation_request(self, message: str, extracted: Dict, state: ConversationState, chat_id: int, user_id: int) -> Tuple[str, Optional[str]]:
        state.intent = 'explain_topic'
        state.context.append({'role': 'user', 'message': message})
        
        topic = extracted.get('topic')
        if not topic:
            topic_match = re.search(r'(?:what is|kya hai|explain|samjhao)\s+(.+)', message, re.IGNORECASE)
            if topic_match:
                topic = topic_match.group(1).strip()
        
        if not topic:
            state.awaiting_input = 'topic'
            response = (
                "Main aapko koi bhi topic explain kar sakta hoon! 📖\n\n"
                "Kaun sa topic samajhna hai?\n"
                "Example: Photosynthesis, Newton's Laws, Respiration\n\n"
                "Topic ka naam batao! 💡"
            )
            state.context.append({'role': 'assistant', 'message': response})
            return (response, None)
        
        state.topic = topic
        command = f"/explain {topic}"
        response = (
            f"Bilkul! Main '{topic}' explain karta hoon 📚\n\n"
            f"Explanation aa rahi hai... ⏳"
        )
        state.context.append({'role': 'assistant', 'message': response, 'command': command})
        self.clear_state(chat_id, user_id)
        
        return (response, command)
    
    async def _handle_jee_quiz_request(self, message: str, extracted: Dict, state: ConversationState, chat_id: int, user_id: int) -> Tuple[str, Optional[str]]:
        """Handle request for JEE quiz."""
        state.intent = 'jee_quiz'
        state.context.append({'role': 'user', 'message': message})
        
        chapter = extracted.get('chapter') or state.chapter
        num_questions_raw = extracted.get('num_questions') or state.num_questions
        
        # Parse and validate num_questions
        num_questions = None
        if num_questions_raw:
            try:
                if isinstance(num_questions_raw, str):
                    num_match = re.search(r'\d+', num_questions_raw)
                    if num_match:
                        num_questions = int(num_match.group())
                else:
                    num_questions = int(num_questions_raw)
            except (ValueError, AttributeError):
                num_questions = None
        
        if not chapter:
            state.awaiting_input = 'jee_chapter'
            response = (
                "JEE quiz lagata hoon! 🎯\n\n"
                "Kis chapter ka JEE level quiz chahiye?\n"
                "Example: Mechanics, Thermodynamics, Calculus\n\n"
                "Chapter batao! 📖"
            )
            state.context.append({'role': 'assistant', 'message': response})
            return (response, None)
        
        if not num_questions or num_questions < 1 or num_questions > 50:
            state.awaiting_input = 'jee_num_questions'
            state.chapter = chapter
            response = (
                f"Perfect! {chapter} ka JEE quiz lagata hoon 🚀\n\n"
                "Kitne questions chahiye? (1-50 ke beech)\n"
                "Example: 10, 15, 20\n\n"
                "Number batao! 🔢"
            )
            state.context.append({'role': 'assistant', 'message': response})
            return (response, None)
        
        state.chapter = chapter
        state.num_questions = num_questions
        command = f"/jeequiz {chapter} {num_questions}"
        
        response = (
            f"JEE quiz start ho raha hai! 🎯\n\n"
            f"📚 Chapter: {chapter}\n"
            f"📝 Questions: {num_questions}\n"
            f"🎯 90% Mains + 10% Advanced\n\n"
            f"Quiz loading... ⏳"
        )
        state.context.append({'role': 'assistant', 'message': response, 'command': command})
        self.clear_state(chat_id, user_id)
        
        return (response, command)
    
    async def _handle_stop_quiz(self, message: str, state: ConversationState, chat_id: int, user_id: int) -> Tuple[str, Optional[str]]:
        """Handle request to stop the current quiz."""
        state.intent = 'stop_quiz'
        state.context.append({'role': 'user', 'message': message})
        
        response = (
            "Quiz abhi stop kar raha hoon! 🛑\n\n"
            "Ruko thoda..."
        )
        
        state.context.append({'role': 'assistant', 'message': response, 'command': '/stopquiz'})
        self.clear_state(chat_id, user_id)
        
        return (response, '/stopquiz')
    
    async def _handle_language_change(self, state: ConversationState) -> Tuple[str, Optional[str]]:
        return (
            "Language change kar sakte ho! 🌐\n\n"
            "Language settings khol raha hoon...",
            "/language"
        )
    
    async def _handle_general_chat(self, message: str, state: ConversationState) -> Tuple[str, Optional[str]]:
        state.context.append({'role': 'user', 'message': message})
        
        greetings = ['hi', 'hello', 'hey', 'namaste', 'hii', 'hlo']
        if any(greet in message.lower() for greet in greetings):
            response = (
                "Namaste! 🙏 Main aapki NEET preparation mein madad karne ke liye hoon!\n\n"
                "Main kya kar sakta hoon?\n"
                "📝 Quiz laga sakta hoon\n"
                "📖 Topics explain kar sakta hoon\n"
                "🌐 Language change kar sakta hoon\n\n"
                "Batao kya chahiye? 😊"
            )
            state.context.append({'role': 'assistant', 'message': response})
            return (response, None)
        
        prompt = f"""You are a friendly NEET quiz bot assistant. Respond to this message in a helpful, friendly way in Hinglish (mix of Hindi and English).
Keep response short (2-3 lines). Guide user towards bot features: quizzes, explanations, or help.

User message: "{message}"

Response:"""
        
        try:
            loop = asyncio.get_event_loop()
            ai_response = await loop.run_in_executor(None, self.model.generate_content, prompt)
            response = ai_response.text.strip()
            state.context.append({'role': 'assistant', 'message': response})
            return response, None
        except:
            response = (
                "Main aapki madad ke liye hoon! 😊\n"
                "Quiz chahiye? Ya koi topic samajhna hai? Batao!"
            )
            state.context.append({'role': 'assistant', 'message': response})
            return (response, None)
    
    async def _handle_awaited_input(self, message: str, state: ConversationState, chat_id: int, user_id: int) -> Tuple[str, Optional[str]]:
        awaiting = state.awaiting_input
        state.awaiting_input = None
        
        if awaiting == 'quiz_type':
            if any(word in message.lower() for word in ['timer', 'timed', '1', 'competitive', 'leaderboard']):
                state.quiz_type = 'timed_quiz'
            else:
                state.quiz_type = 'cquiz'
            
            state.context.append({'role': 'user', 'message': message})
            return await self._handle_quiz_request(message, {}, state, chat_id, user_id)
        
        elif awaiting == 'chapter':
            state.chapter = message.strip()
            state.context.append({'role': 'user', 'message': message})
            return await self._handle_quiz_request(message, {}, state, chat_id, user_id)
        
        elif awaiting == 'num_questions':
            try:
                num = int(re.search(r'\d+', message).group())
                if 1 <= num <= 20:
                    state.num_questions = num
                    state.context.append({'role': 'user', 'message': message})
                    return await self._handle_quiz_request(message, {}, state, chat_id, user_id)
                else:
                    state.awaiting_input = 'num_questions'
                    response = (
                        "Please 1 se 20 ke beech number batao! 😊\n"
                        "Example: 5, 10, 15"
                    )
                    state.context.append({'role': 'assistant', 'message': response})
                    return (response, None)
            except:
                state.awaiting_input = 'num_questions'
                response = (
                    "Mujhe ek number chahiye (1-20 ke beech) 🔢\n"
                    "Example: 10"
                )
                state.context.append({'role': 'assistant', 'message': response})
                return (response, None)
        
        elif awaiting == 'topic':
            state.topic = message.strip()
            state.context.append({'role': 'user', 'message': message})
            return await self._handle_explanation_request(message, {}, state, chat_id, user_id)
        
        elif awaiting == 'jee_chapter':
            state.chapter = message.strip()
            state.context.append({'role': 'user', 'message': message})
            return await self._handle_jee_quiz_request(message, {}, state, chat_id, user_id)
        
        elif awaiting == 'jee_num_questions':
            num_match = re.search(r'\d+', message)
            if not num_match:
                state.awaiting_input = 'jee_num_questions'
                response = (
                    "Mujhe ek number chahiye (1-50 ke beech) 🔢\n"
                    "Example: 15"
                )
                state.context.append({'role': 'assistant', 'message': response})
                return (response, None)
            
            try:
                num = int(num_match.group())
                if 1 <= num <= 50:
                    state.num_questions = num
                    state.context.append({'role': 'user', 'message': message})
                    return await self._handle_jee_quiz_request(message, {}, state, chat_id, user_id)
                else:
                    state.awaiting_input = 'jee_num_questions'
                    response = (
                        "Please 1 se 50 ke beech number batao! 😊\n"
                        "Example: 10, 20, 30"
                    )
                    state.context.append({'role': 'assistant', 'message': response})
                    return (response, None)
            except (ValueError, AttributeError):
                state.awaiting_input = 'jee_num_questions'
                response = (
                    "Mujhe ek valid number chahiye (1-50 ke beech) 🔢\n"
                    "Example: 15"
                )
                state.context.append({'role': 'assistant', 'message': response})
                return (response, None)
        
        return await self._handle_general_chat(message, state)

conversation_ai = ConversationAI()
