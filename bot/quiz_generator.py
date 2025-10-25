import google.generativeai as genai
from typing import List, Dict
import json
import re
from bot.config import GOOGLE_API_KEY, WATERMARK

genai.configure(api_key=GOOGLE_API_KEY)

class QuizGenerator:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def generate_quiz(self, chapter: str, num_questions: int) -> List[Dict]:
        """
        Generate NEET-relevant MCQs for a given chapter.
        
        Args:
            chapter: Name of the NCERT chapter (Class 11 or 12)
            num_questions: Number of questions to generate (1-20)
        
        Returns:
            List of dictionaries containing question data
        """
        prompt = self._create_prompt(chapter, num_questions)
        
        try:
            response = self.model.generate_content(prompt)
            questions = self._parse_response(response.text, num_questions)
            return questions
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating quiz: {e}")
            raise
    
    def _create_prompt(self, chapter: str, num_questions: int) -> str:
        """Create a detailed prompt for Gemini to generate NEET-level MCQs."""
        return f"""You are an expert NEET (National Eligibility cum Entrance Test - UG) medical entrance exam question creator with access to NEET Previous Year Questions (PYQs) database.

Generate exactly {num_questions} Multiple Choice Questions (MCQs) for the chapter: "{chapter}" from NCERT Class 11th or 12th.

CRITICAL REQUIREMENTS:
1. MUST use ACTUAL NEET UG Previous Year Questions (PYQs) from 2015-2024
2. Questions MUST be from official NEET UG exam papers or NEET-standard test series
3. Each question must be NEET-difficulty level (medical entrance exam standard)
4. Cover Biology, Physics, or Chemistry topics from NCERT Class 11 & 12
5. Each question must have EXACTLY 4 options
6. Questions should test conceptual understanding and application
7. Include year information if it's a PYQ (e.g., "NEET 2023")

Output format (JSON array):
[
  {{
    "question": "Which of the following is the powerhouse of the cell? (NEET 2019)",
    "options": [
      "Nucleus",
      "Mitochondria",
      "Ribosome",
      "Golgi apparatus"
    ],
    "correct_answer": 1,
    "explanation": "Mitochondria is called the powerhouse of the cell as it produces ATP through cellular respiration."
  }}
]

STRICT FORMATTING RULES:
- correct_answer is the index (0-3) of the correct option
- Question text must be clear and unambiguous
- Options must be concise (preferably under 50 characters each)
- Each option should be a complete standalone answer
- Ensure scientific accuracy and proper terminology
- Prioritize questions from NEET PYQs and official sources

Generate exactly {num_questions} NEET PYQ-based questions now in valid JSON format."""
    
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
    
    def format_question_with_watermark(self, question_num: int, question_data: Dict) -> str:
        """Format a single question with watermark for display."""
        formatted = f"{question_num}. {question_data['question']}\n\n"
        formatted += f"{WATERMARK}\n"
        
        option_labels = ['A', 'B', 'C', 'D']
        for i, option in enumerate(question_data['options']):
            formatted += f"{option_labels[i]}) {option}\n"
        
        return formatted
