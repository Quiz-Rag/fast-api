"""
AI-powered grading service for descriptive quiz answers.
Uses Groq LLM to compare user answers with expected answers.
"""

import json
from typing import List, Dict, Optional
from groq import Groq
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class AIGradingService:
    """Service for AI-powered descriptive answer grading."""
    
    def __init__(self):
        """Initialize Groq client."""
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model
    
    async def grade_descriptive_answer(
        self,
        question: str,
        expected_answer: str,
        user_answer: str,
        key_points: Optional[List[str]] = None
    ) -> Dict:
        """
        Grade a descriptive answer using Groq LLM.
        
        Args:
            question: The question text
            expected_answer: The correct/expected answer
            user_answer: The student's submitted answer
            key_points: List of key concepts that must be covered
        
        Returns:
            Dictionary with score, breakdown, analysis, and feedback
        """
        if not key_points:
            key_points = []
        
        # Calculate points per key point
        points_per_key_point = 70 // len(key_points) if key_points else 70
        
        # Build key points list
        key_points_text = "\n".join([f"{i+1}. {point}" for i, point in enumerate(key_points)])
        
        prompt = f"""You are an expert educational grader. Grade the student's answer strictly but fairly.

QUESTION:
{question}

EXPECTED ANSWER (Reference):
{expected_answer}

KEY POINTS (Required):
{key_points_text if key_points else "No specific key points provided - grade based on overall accuracy and completeness"}

STUDENT'S ANSWER:
{user_answer}

GRADING RUBRIC:
1. Content Coverage (70 points max):
   - Award points proportionally based on key points covered
   - Each key point = {points_per_key_point} points
   - Missing key point = deduct proportionally

2. Accuracy (20 points max):
   - 20 points: Completely accurate information
   - 15 points: Mostly accurate with minor errors
   - 10 points: Some inaccuracies
   - 5 points: Significant inaccuracies
   - 0 points: Completely wrong information

3. Clarity & Structure (10 points max):
   - 10 points: Well-organized, clear explanation
   - 7 points: Understandable but could be clearer
   - 5 points: Somewhat confusing
   - 2 points: Very unclear

4. Extra/Irrelevant Content Penalty:
   - Deduct 3-10 points for significant off-topic content
   - No penalty for minor elaboration that's still relevant

SCORING RULES:
- Start with 0 and add points for what's present
- Full marks (100) ONLY if ALL key points covered accurately
- Deduct for missing key points proportionally
- Deduct for extra irrelevant content
- Be strict: Don't give full marks for "good enough"

Respond ONLY with valid JSON (no markdown, no code blocks):
{{
    "score": <integer 0-100>,
    "breakdown": {{
        "content_coverage_score": <0-70>,
        "accuracy_score": <0-20>,
        "clarity_score": <0-10>,
        "extra_content_penalty": <0 or negative integer>
    }},
    "points_covered": [<list of key points found in student answer>],
    "points_missed": [<list of key points NOT found>],
    "extra_content": [<list of irrelevant topics mentioned>],
    "feedback": "<2-3 sentences explaining the score>",
    "suggestions": [<specific improvements needed>]
}}"""

        try:
            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert educational grader. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,  # Low temperature for consistent grading
                max_tokens=800
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            # Parse JSON response
            result = json.loads(content)
            
            # Validate score
            score = result.get("score", 0)
            if score < 0:
                score = 0
            elif score > 100:
                score = 100
            
            return {
                "score": score,
                "breakdown": {
                    "content_coverage_score": result.get("breakdown", {}).get("content_coverage_score", 0),
                    "accuracy_score": result.get("breakdown", {}).get("accuracy_score", 0),
                    "clarity_score": result.get("breakdown", {}).get("clarity_score", 0),
                    "extra_content_penalty": result.get("breakdown", {}).get("extra_content_penalty", 0)
                },
                "points_covered": result.get("points_covered", []),
                "points_missed": result.get("points_missed", []),
                "extra_content": result.get("extra_content", []),
                "feedback": result.get("feedback", ""),
                "suggestions": result.get("suggestions", []),
                "is_ai_graded": True
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI grading response: {e}")
            logger.error(f"Response content: {content}")
            # Fallback
            return self._create_fallback_response(
                f"Unable to parse AI response. Manual review required."
            )
        
        except Exception as e:
            logger.error(f"Error during AI grading: {e}")
            return self._create_fallback_response(
                f"Auto-grading unavailable. Error: {str(e)}"
            )
    
    def _create_fallback_response(self, error_message: str) -> Dict:
        """Create fallback response when AI grading fails."""
        return {
            "score": None,
            "breakdown": {
                "content_coverage_score": 0,
                "accuracy_score": 0,
                "clarity_score": 0,
                "extra_content_penalty": 0
            },
            "points_covered": [],
            "points_missed": [],
            "extra_content": [],
            "feedback": error_message,
            "suggestions": ["Manual review required"],
            "is_ai_graded": False
        }


# Global instance
ai_grading_service = AIGradingService()
