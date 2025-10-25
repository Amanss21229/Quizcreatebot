import google.generativeai as genai
from typing import List, Dict
import json
import re
from bot.config import GOOGLE_API_KEY, WATERMARK

genai.configure(api_key=GOOGLE_API_KEY)

class QuizGenerator:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
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
            print(f"Error generating quiz: {e}")
            raise
    
    def _create_prompt(self, chapter: str, num_questions: int) -> str:
        """Create a detailed prompt for Gemini to generate NEET-level MCQs."""
        return f"""You are an expert NEET (National Eligibility cum Entrance Test) medical entrance exam question creator.

Generate exactly {num_questions} Multiple Choice Questions (MCQs) from the NCERT Class 11th or 12th chapter: "{chapter}".

Requirements:
1. Questions MUST be NEET-standard difficulty level (medical entrance exam)
2. Questions should cover Biology, Physics, or Chemistry topics from NCERT Class 11 & 12
3. Include previous year NEET questions (PYQs) when relevant to the chapter
4. Each question must have exactly 4 options labeled A, B, C, D
5. Mark the correct answer clearly
6. Questions should test conceptual understanding, not just memorization

Output format (JSON array):
[
  {{
    "question": "What is the powerhouse of the cell?",
    "options": [
      "Nucleus",
      "Mitochondria",
      "Ribosome",
      "Golgi apparatus"
    ],
    "correct_answer": 1,
    "explanation": "Brief explanation why this is correct"
  }}
]

IMPORTANT: 
- correct_answer is the index (0-3) of the correct option
- Questions should be clinically relevant and NEET-focused
- Ensure scientific accuracy
- Use proper terminology

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
            print(f"Error parsing response: {e}")
            print(f"Response text: {response_text[:500]}")
            raise ValueError("Failed to parse quiz questions from AI response")
    
    def format_question_with_watermark(self, question_num: int, question_data: Dict) -> str:
        """Format a single question with watermark for display."""
        formatted = f"{question_num}. {question_data['question']}\n\n"
        formatted += f"{WATERMARK}\n"
        
        option_labels = ['A', 'B', 'C', 'D']
        for i, option in enumerate(question_data['options']):
            formatted += f"{option_labels[i]}) {option}\n"
        
        return formatted
