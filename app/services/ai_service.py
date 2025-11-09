"""
AI service for quiz generation using Groq API.
"""

from groq import Groq
from app.config import settings
import json
from typing import Dict, Any


class AIService:
    """Service for interacting with Groq AI API."""
    
    def __init__(self):
        """Initialize Groq client."""
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY not set in environment variables")
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model
    
    def _create_prompt(
        self,
        topic: str,
        content: str,
        num_mcq: int,
        num_blanks: int,
        num_descriptive: int,
        difficulty: str
    ) -> str:
        """Create structured prompt for quiz generation."""
        
        prompt = f"""You are an expert Network Security instructor creating a quiz.

CONTENT FROM COURSE MATERIALS:
{content}

TASK:
Create a quiz on the topic "{topic}" with the following specifications:
- {num_mcq} Multiple Choice Questions (MCQ) with 4 options each
- {num_blanks} Fill-in-the-Blank questions
- {num_descriptive} Descriptive/Short Answer questions
- Difficulty Level: {difficulty}

IMPORTANT RULES:
1. Base ALL questions STRICTLY on the provided content above
2. Do NOT include any information not present in the content
3. MCQs must have exactly 4 options with only ONE clearly correct answer
4. For MCQs, use correct field with value 1, 2, 3, or 4 (NOT A, B, C, D)
5. Fill-in-the-blank answers should be 1-3 words maximum
6. Descriptive questions should require 2-3 sentence answers
7. Include detailed explanations for each question
8. Ensure questions test understanding, not just memorization

OUTPUT FORMAT (JSON only, no other text):
{{
  "mcq": [
    {{
      "question": "Question text here?",
      "options": ["Option 1 text", "Option 2 text", "Option 3 text", "Option 4 text"],
      "correct": 1,
      "explanation": "Detailed explanation why option 1 is correct"
    }}
  ],
  "blanks": [
    {{
      "question": "Question with _____ to fill",
      "answer": "correct answer",
      "explanation": "Explanation of the answer"
    }}
  ],
  "descriptive": [
    {{
      "question": "Descriptive question text?",
      "sample_answer": "A good sample answer with key points",
      "key_points": ["Key point 1", "Key point 2", "Key point 3"],
      "explanation": "What makes this a good answer"
    }}
  ]
}}

CRITICAL: The "correct" field for MCQ must be a number (1, 2, 3, or 4), NOT a letter.

GENERATE THE QUIZ NOW (JSON only):"""
        
        return prompt
    
    async def generate_quiz(
        self,
        topic: str,
        content: str,
        num_mcq: int,
        num_blanks: int,
        num_descriptive: int,
        difficulty: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate quiz using Groq API.
        
        Returns:
            Dictionary with mcq, blanks, and descriptive questions
        """
        prompt = self._create_prompt(
            topic, content, num_mcq, num_blanks, num_descriptive, difficulty
        )
        
        try:
            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert quiz generator. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=4000,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            # Parse response
            content = response.choices[0].message.content
            quiz_data = json.loads(content)
            
            # Validate structure
            if 'mcq' not in quiz_data:
                quiz_data['mcq'] = []
            if 'blanks' not in quiz_data:
                quiz_data['blanks'] = []
            if 'descriptive' not in quiz_data:
                quiz_data['descriptive'] = []
            
            return quiz_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse AI response as JSON: {str(e)}")
        except Exception as e:
            raise Exception(f"AI generation failed: {str(e)}")
