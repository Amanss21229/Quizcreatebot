import google.generativeai as genai
from typing import List, Dict
import json
import re
from bot.config import GOOGLE_API_KEY, WATERMARK

genai.configure(api_key=GOOGLE_API_KEY)

class QuizGenerator:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def generate_quiz(self, chapter: str, num_questions: int, language: str = 'english') -> List[Dict]:
        """
        Generate NEET-relevant MCQs for a given chapter.
        
        Args:
            chapter: Name of the NCERT chapter (Class 11 or 12)
            num_questions: Number of questions to generate (1-20)
            language: Language for questions ('hindi' or 'english')
        
        Returns:
            List of dictionaries containing question data
        """
        prompt = self._create_prompt(chapter, num_questions, language)
        
        try:
            response = self.model.generate_content(prompt)
            questions = self._parse_response(response.text, num_questions)
            return questions
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating quiz: {e}")
            raise
    
    def _create_prompt(self, chapter: str, num_questions: int, language: str = 'english') -> str:
        """Create a detailed prompt for Gemini to generate NEET-level MCQs."""
        
        language_instruction = ""
        if language == 'hindi':
            language_instruction = "\n\nIMPORTANT: Generate ALL questions, options, and explanations in HINDI language (Devanagari script). Use proper Hindi scientific terminology."
        else:
            language_instruction = "\n\nIMPORTANT: Generate ALL questions, options, and explanations in ENGLISH language."
        
        return f"""You are an expert NEET (National Eligibility cum Entrance Test - UG) medical entrance exam question creator with complete access to:
1. NEET Previous Year Questions (PYQs) database (2015-2024)
2. Complete NCERT Class 11 & 12 textbooks (word-by-word)

Generate exactly {num_questions} Multiple Choice Questions (MCQs) for the chapter: "{chapter}" from NCERT Class 11th or 12th.
{language_instruction}

CRITICAL REQUIREMENTS - FOLLOW STRICTLY:

**For Biology Chapters:**
- 50% questions MUST be EXACT LINES from NCERT textbooks (word-to-word from the book)
- 50% questions MUST be NEET UG Previous Year Questions (PYQs) from 2015-2024
- NCERT questions should use the EXACT sentences/statements from NCERT books
- Example NCERT question: "According to NCERT, which of the following correctly describes mitochondria?" (then use exact NCERT book text)

**For Physics/Chemistry Chapters:**
- 100% questions MUST be ACTUAL NEET UG PYQs from 2015-2024
- Questions MUST be from official NEET UG exam papers

**General Requirements:**
1. Each question must have EXACTLY 4 options
2. Each question must be NEET-difficulty level (medical entrance exam standard)
3. Questions should test conceptual understanding and application
4. Include year information for PYQs (e.g., "NEET 2023", "NEET 2020")
5. For NCERT-based questions, mention "NCERT" in the question

Output format (JSON array):
[
  {{
    "question": "According to NCERT, mitochondria are known as the powerhouse of the cell because they:",
    "options": [
      "Store genetic information",
      "Produce ATP through cellular respiration",
      "Synthesize proteins",
      "Control cell division"
    ],
    "correct_answer": 1,
    "explanation": "NCERT states that mitochondria produce ATP through cellular respiration, hence called powerhouse of the cell."
  }},
  {{
    "question": "Which enzyme is responsible for unwinding the DNA double helix during replication? (NEET 2022)",
    "options": [
      "DNA polymerase",
      "Helicase",
      "Primase",
      "Ligase"
    ],
    "correct_answer": 1,
    "explanation": "Helicase unwinds the DNA double helix by breaking hydrogen bonds between base pairs."
  }}
]

STRICT FORMATTING RULES:
- correct_answer is the index (0-3) of the correct option
- Question text must be clear and unambiguous
- Options must be concise (under 60 characters each)
- Each option should be a complete standalone answer
- Ensure scientific accuracy using NCERT terminology
- For Biology: MIX NCERT exact-line questions WITH NEET PYQs (50-50 ratio)
- For Physics/Chemistry: ONLY NEET PYQs

Generate exactly {num_questions} questions now in valid JSON format."""
    
    def _parse_response(self, response_text: str, expected_count: int) -> List[Dict]:
        """Parse Gemini's response and extract quiz questions."""
        try:
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                questions_data = json.loads(json_match.group())
            else:
                questions_data = json.loads(response_text)
            
            if not isinstance(questions_data, list):
                raise ValueError("Response is not a list of questions")
            
            questions = []
            for i, q in enumerate(questions_data[:expected_count]):
                if not all(key in q for key in ['question', 'options', 'correct_answer']):
                    continue
                
                questions.append({
                    'question': q['question'],
                    'options': q['options'][:4],
                    'correct_answer': int(q['correct_answer']),
                    'explanation': q.get('explanation', '')
                })
            
            return questions
        
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error parsing response: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            raise ValueError("Failed to parse quiz questions from AI response")
    
    def translate_questions(self, questions_english: List[Dict]) -> List[Dict]:
        """
        Translate English questions to Hindi while maintaining the same structure and correct answers.
        
        Args:
            questions_english: List of questions in English
        
        Returns:
            List of the SAME questions translated to Hindi
        """
        prompt = f"""You are an expert translator specializing in NEET medical entrance exam content.

CRITICAL TASK: Translate the following questions from ENGLISH to HINDI (Devanagari script).

STRICT REQUIREMENTS:
1. Translate ONLY the question text and options - DO NOT change the correct_answer index
2. Keep the EXACT SAME structure and format
3. Use proper scientific Hindi terminology (देवनागरी लिपि)
4. Maintain the SAME correct answer index (0, 1, 2, or 3) - DO NOT MODIFY IT
5. Translate explanations as well if present
6. Keep all NEET year references and NCERT mentions in the questions

INPUT QUESTIONS (JSON):
{json.dumps(questions_english, ensure_ascii=False, indent=2)}

OUTPUT REQUIREMENTS:
- Return EXACT SAME JSON structure
- Translate question, options, and explanation to Hindi
- Keep correct_answer index UNCHANGED
- Use proper Hindi scientific terms
- Maintain array order

Generate the translated JSON now:"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Parse the translated questions
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                questions_hindi = json.loads(json_match.group())
            else:
                questions_hindi = json.loads(response_text)
            
            # Ensure correct_answer indices match
            for i, (eng_q, hin_q) in enumerate(zip(questions_english, questions_hindi)):
                hin_q['correct_answer'] = eng_q['correct_answer']
            
            return questions_hindi
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error translating questions: {e}")
            logger.error(f"Falling back to English questions")
            return questions_english
    
    def format_question_with_watermark(self, question_num: int, question_data: Dict) -> str:
        """Format a single question with watermark for display."""
        formatted = f"{question_num}. {question_data['question']}\n\n"
        formatted += f"{WATERMARK}\n"
        
        option_labels = ['A', 'B', 'C', 'D']
        for i, option in enumerate(question_data['options']):
            formatted += f"{option_labels[i]}) {option}\n"
        
        return formatted
    
    def generate_explanation(self, content: str, content_type: str = 'text', language: str = 'english') -> str:
        """
        Generate a detailed explanation for any question, topic, or content.
        
        Args:
            content: The question, text, or topic to explain
            content_type: Type of content ('text', 'quiz', 'poll', 'image_description')
            language: Language for explanation ('hindi' or 'english')
        
        Returns:
            Detailed explanation with answer (if applicable)
        """
        language_instruction = ""
        if language == 'hindi':
            language_instruction = "IMPORTANT: Generate the ENTIRE explanation in HINDI language (Devanagari script). Use proper Hindi scientific terminology. DO NOT use any mathematical symbols, LaTeX, or special characters."
        else:
            language_instruction = "IMPORTANT: Generate the ENTIRE explanation in ENGLISH language. DO NOT use any mathematical symbols, LaTeX, or special characters."
        
        prompt = f"""You are an expert NEET educator with complete knowledge of NCERT Class 11 & 12 textbooks and NEET exam patterns.

{language_instruction}

Content to explain: {content}

Provide a CLEAN, SIMPLE explanation in 1-10 LINES (adjust based on complexity):

CRITICAL FORMATTING RULES:
1. Use ONLY plain text - NO LaTeX, NO mathematical symbols like $, /, \\, etc.
2. Write numbers and formulas in simple text (e.g., "E = mc squared" not "E = mc^2")
3. If it's a question, state the correct answer FIRST in simple language
4. Give brief reasoning with key concept
5. Mention NCERT reference if applicable
6. Keep explanation between 1-10 lines based on question complexity
7. Use simple words that anyone can understand
8. NO special symbols, brackets, or formatting characters

FORBIDDEN CHARACTERS: $ / \\ ^ _ {{ }} [ ] * # ~

OUTPUT RULES:
- Simple sentences only
- Plain text explanation
- Clear and easy to understand
- No technical formatting symbols"""
        
        try:
            response = self.model.generate_content(prompt)
            raw_explanation = response.text.strip()
            
            # Clean up unwanted symbols
            cleaned_explanation = self._clean_explanation(raw_explanation)
            
            return cleaned_explanation
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating explanation: {e}")
            raise
    
    def _clean_explanation(self, text: str) -> str:
        """Clean unwanted symbols from AI-generated explanation."""
        # Remove common LaTeX and mathematical symbols
        text = re.sub(r'\$+', '', text)  # Remove $
        text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text)  # Remove LaTeX commands like \text{...}
        text = re.sub(r'\\[a-zA-Z]+', '', text)  # Remove LaTeX commands like \alpha
        text = re.sub(r'\^\{?[^}]*\}?', '', text)  # Remove superscripts
        text = re.sub(r'_\{?[^}]*\}?', '', text)  # Remove subscripts
        text = re.sub(r'[{}]', '', text)  # Remove braces
        text = re.sub(r'\[([^\]]+)\]', r'\1', text)  # Remove square brackets but keep content
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Remove bold markdown
        text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Remove italic markdown
        text = re.sub(r'##\s+', '', text)  # Remove markdown headers
        text = re.sub(r'~~([^~]+)~~', r'\1', text)  # Remove strikethrough
        
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove multiple newlines (keep max 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
