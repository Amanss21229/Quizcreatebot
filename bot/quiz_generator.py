from groq import Groq
from typing import List, Dict
import json
import re
import logging
from bot.config import GROQ_API_KEY, WATERMARK

logger = logging.getLogger(__name__)

class QuizGenerator:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = "llama3-70b-8192"
    
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
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.7,
                max_tokens=4096
            )
            response_text = chat_completion.choices[0].message.content
            questions = self._parse_response(response_text, num_questions)
            return questions
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating quiz: {e}")
            raise
    
    def _create_prompt(self, chapter: str, num_questions: int, language: str = 'english') -> str:
        """Create a detailed prompt for Groq to generate NEET-level MCQs."""
        
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
        """Parse Groq's response and extract quiz questions."""
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
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.5,
                max_tokens=4096
            )
            response_text = chat_completion.choices[0].message.content.strip()
            
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
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.5,
                max_tokens=2048
            )
            raw_explanation = chat_completion.choices[0].message.content.strip()
            
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
    
    def generate_jee_quiz(self, chapter: str, num_questions: int, language: str = 'english') -> List[Dict]:
        """
        Generate JEE (Joint Entrance Examination) focused MCQs for a given chapter.
        
        Args:
            chapter: Name of the chapter from NCERT Class 11 or 12 (Physics, Chemistry, Mathematics)
            num_questions: Number of questions to generate
            language: Language for questions ('hindi' or 'english')
        
        Returns:
            List of dictionaries containing question data with metadata
        """
        prompt = self._create_jee_prompt(chapter, num_questions, language)
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.7,
                max_tokens=4096
            )
            response_text = chat_completion.choices[0].message.content
            questions = self._parse_jee_response(response_text, num_questions)
            return questions
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating JEE quiz: {e}")
            raise
    
    def _create_jee_prompt(self, chapter: str, num_questions: int, language: str = 'english') -> str:
        """Create a detailed prompt for Groq to generate JEE-level MCQs with metadata."""
        
        language_instruction = ""
        if language == 'hindi':
            language_instruction = "\n\nIMPORTANT: Generate ALL questions, options, and explanations in HINDI language (Devanagari script). Use proper Hindi scientific terminology."
        else:
            language_instruction = "\n\nIMPORTANT: Generate ALL questions, options, and explanations in ENGLISH language."
        
        return f"""You are an expert JEE (Joint Entrance Examination) question creator with complete access to:
1. JEE Main Previous Year Questions (PYQs) database (2015-2024)
2. JEE Advanced Previous Year Questions (PYQs) database (2015-2024)
3. Complete NCERT Class 11 & 12 textbooks for Physics, Chemistry, and Mathematics
4. Standard reference books: HC Verma (Concepts of Physics), DC Pandey (Understanding Physics), RD Sharma (Mathematics)

Generate exactly {num_questions} Multiple Choice Questions (MCQs) for the chapter: "{chapter}" from NCERT Class 11th or 12th.
{language_instruction}

CRITICAL REQUIREMENTS - FOLLOW STRICTLY:

**Question Distribution (MANDATORY):**
- 90% questions MUST be JEE MAINS level (appropriate for JEE Main exam standard)
- 10% questions MUST be JEE ADVANCED level (appropriate for JEE Advanced exam standard)

**Question Sources:**
- NCERT-based questions (conceptual from NCERT textbooks)
- JEE Main PYQs (2015-2024)
- JEE Advanced PYQs (2015-2024)
- Standard publications: HC Verma, DC Pandey, RD Sharma

**Metadata Requirements (CRITICAL):**
For EACH question, you MUST include:
1. "level": Either "Mains Level" or "Advanced Level"
2. "source": One of the following:
   - "PYQ JEE Main YYYY" (for JEE Main previous year questions, e.g., "PYQ JEE Main 2023")
   - "PYQ JEE Advanced YYYY" (for JEE Advanced previous year questions)
   - "HC Verma" (for questions from HC Verma)
   - "DC Pandey" (for questions from DC Pandey)
   - "RD Sharma" (for questions from RD Sharma)
   - "NCERT" (for NCERT-based conceptual questions)

**General Requirements:**
1. Each question must have EXACTLY 4 options
2. Questions should test conceptual understanding and problem-solving ability
3. Include numerical problems, conceptual questions, and application-based questions
4. Maintain proper JEE difficulty standards

Output format (JSON array with metadata):
[
  {{
    "question": "A particle moves in a circle of radius r with constant speed v. What is the magnitude of its acceleration?",
    "options": [
      "v²/r directed towards center",
      "v²/r directed away from center",
      "Zero",
      "v/r directed towards center"
    ],
    "correct_answer": 0,
    "explanation": "For uniform circular motion, centripetal acceleration = v²/r directed towards the center of the circle.",
    "metadata": {{
      "level": "Mains Level",
      "source": "NCERT"
    }}
  }},
  {{
    "question": "The de Broglie wavelength of an electron accelerated through a potential difference V is λ. What will be the de Broglie wavelength when the accelerating potential is increased to 4V? (PYQ JEE Main 2022)",
    "options": [
      "4λ",
      "2λ",
      "λ/2",
      "λ/4"
    ],
    "correct_answer": 2,
    "explanation": "de Broglie wavelength is inversely proportional to square root of V. When V becomes 4V, wavelength becomes λ/2.",
    "metadata": {{
      "level": "Mains Level",
      "source": "PYQ JEE Main 2022"
    }}
  }},
  {{
    "question": "A uniform rod of length L and mass M is pivoted at its center. Two forces each of magnitude F are applied as shown, one at distance L/4 and another at distance L/2 from the pivot, in opposite directions perpendicular to the rod. The net torque on the rod is: (HC Verma)",
    "options": [
      "FL/4",
      "FL/2",
      "3FL/4",
      "Zero"
    ],
    "correct_answer": 0,
    "explanation": "Net torque = F(L/2) - F(L/4) = FL/4. The torques are in opposite directions, so we subtract them.",
    "metadata": {{
      "level": "Advanced Level",
      "source": "HC Verma"
    }}
  }}
]

STRICT FORMATTING RULES:
- correct_answer is the index (0-3) of the correct option
- Question text must be clear and unambiguous
- Options must be concise (under 80 characters each)
- Each question MUST have a "metadata" object with "level" and "source"
- Level must be either "Mains Level" or "Advanced Level"
- Source must match one of the allowed sources listed above
- Ensure 90% questions are Mains Level and 10% are Advanced Level
- For PYQ questions, include the year in the source (e.g., "PYQ JEE Main 2023")
- For publication questions, mention the publication name in source

Generate exactly {num_questions} questions now in valid JSON format with proper metadata."""
    
    def _parse_jee_response(self, response_text: str, expected_count: int) -> List[Dict]:
        """Parse Gemini's response for JEE questions and extract metadata with strict validation."""
        try:
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                questions_data = json.loads(json_match.group())
            else:
                questions_data = json.loads(response_text)
            
            if not isinstance(questions_data, list):
                raise ValueError("Response is not a list of questions")
            
            allowed_sources = ['NCERT', 'HC Verma', 'DC Pandey', 'RD Sharma']
            pyq_pattern = re.compile(r'^PYQ JEE (Main|Advanced) (19|20)\d{2}$')
            
            questions = []
            malformed_count = 0
            
            for i, q in enumerate(questions_data):
                if not all(key in q for key in ['question', 'options', 'correct_answer']):
                    malformed_count += 1
                    logger.warning(f"Question {i+1} missing required keys: {list(q.keys())}")
                    continue
                
                if len(questions) >= expected_count:
                    break
                
                metadata = q.get('metadata', {})
                level = metadata.get('level', 'Mains Level')
                source = metadata.get('source', 'NCERT')
                
                if level not in ['Mains Level', 'Advanced Level']:
                    logger.warning(f"Invalid level '{level}' in question {i+1}, defaulting to Mains Level")
                    level = 'Mains Level'
                
                source_valid = False
                if source in allowed_sources:
                    source_valid = True
                elif pyq_pattern.match(source):
                    source_valid = True
                else:
                    logger.warning(f"Invalid source '{source}' in question {i+1}, defaulting to NCERT")
                    source = 'NCERT'
                
                questions.append({
                    'question': q['question'],
                    'options': q['options'][:4],
                    'correct_answer': int(q['correct_answer']),
                    'explanation': q.get('explanation', ''),
                    'metadata': {
                        'level': level,
                        'source': source
                    }
                })
            
            if len(questions) < expected_count:
                raise ValueError(
                    f"Insufficient valid questions: generated {len(questions)} out of {expected_count} requested "
                    f"({malformed_count} malformed questions skipped)"
                )
            
            expected_mains = round(expected_count * 0.9)
            expected_advanced = expected_count - expected_mains
            
            mains_indices = [i for i, q in enumerate(questions) if q['metadata']['level'] == 'Mains Level']
            advanced_indices = [i for i, q in enumerate(questions) if q['metadata']['level'] == 'Advanced Level']
            
            if len(mains_indices) != expected_mains or len(advanced_indices) != expected_advanced:
                logger.warning(
                    f"Correcting JEE distribution: Expected {expected_mains} Mains/{expected_advanced} Advanced, "
                    f"got {len(mains_indices)} Mains/{len(advanced_indices)} Advanced"
                )
                
                if len(mains_indices) < expected_mains:
                    needed = expected_mains - len(mains_indices)
                    if len(advanced_indices) < needed:
                        raise ValueError(
                            f"Cannot achieve 90/10 ratio: need {needed} more Mains but only "
                            f"{len(advanced_indices)} Advanced available"
                        )
                    for i in advanced_indices[:needed]:
                        questions[i]['metadata']['level'] = 'Mains Level'
                
                elif len(advanced_indices) < expected_advanced:
                    needed = expected_advanced - len(advanced_indices)
                    if len(mains_indices) < needed:
                        raise ValueError(
                            f"Cannot achieve 90/10 ratio: need {needed} more Advanced but only "
                            f"{len(mains_indices)} Mains available"
                        )
                    for i in mains_indices[:needed]:
                        questions[i]['metadata']['level'] = 'Advanced Level'
            
            final_mains = sum(1 for q in questions if q['metadata']['level'] == 'Mains Level')
            final_advanced = sum(1 for q in questions if q['metadata']['level'] == 'Advanced Level')
            logger.info(
                f"JEE quiz validated: {final_mains} Mains ({final_mains/expected_count*100:.0f}%), "
                f"{final_advanced} Advanced ({final_advanced/expected_count*100:.0f}%)"
            )
            
            return questions
        
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Error parsing JEE response: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            raise ValueError(f"Failed to parse JEE quiz questions: {str(e)}")
