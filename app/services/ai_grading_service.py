"""
AI-powered grading service for descriptive quiz answers.
Uses LangChain ChatOpenAI to compare user answers with expected answers.
"""

from typing import List, Dict, Optional
from app.config import settings
import logging

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from app.models.langchain_schemas import GradingOutput
from app.services.prompts import PromptTemplates

logger = logging.getLogger(__name__)


class AIGradingService:
    """Service for AI-powered descriptive answer grading."""
    
    def __init__(self):
        """Initialize LangChain ChatOpenAI."""
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set in environment variables")
        
        # Initialize LangChain ChatOpenAI
        self.llm = ChatOpenAI(
            model=settings.openai_llm_model,
            temperature=0.2,
            openai_api_key=settings.openai_api_key
        )
        # Initialize output parser
        self.grading_parser = PydanticOutputParser(pydantic_object=GradingOutput)
        
        self.model = settings.openai_llm_model
    
    async def grade_descriptive_answer(
        self,
        question: str,
        expected_answer: str,
        user_answer: str,
        key_points: Optional[List[str]] = None
    ) -> Dict:
        """
        Grade a descriptive answer using OpenAI GPT-4 LLM.
        
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
        key_points_text = "\n".join([f"{i+1}. {point}" for i, point in enumerate(key_points)]) if key_points else "No specific key points provided - grade based on overall accuracy and completeness"
        
        # Use prompt template
        prompt = PromptTemplates.get_grading_prompt().format(
            question=question,
            expected_answer=expected_answer,
            key_points=key_points_text,
            user_answer=user_answer,
            points_per_key_point=points_per_key_point
        )

        try:
            # Use LangChain with structured output
            system_prompt = "You are an expert educational grader. Always respond with valid JSON only."
            human_prompt = prompt
            
            chat_prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", human_prompt)
            ])
            
            chain = chat_prompt | self.llm.with_config({"temperature": 0.2, "max_tokens": 800}) | self.grading_parser
            result = await chain.ainvoke({})
            
            # Convert Pydantic model to dict
            grading_data = result.model_dump()
            
            # Validate score
            score = grading_data.get("score", 0)
            if score < 0:
                score = 0
            elif score > 100:
                score = 100
            grading_data["score"] = score
            grading_data["is_ai_graded"] = True
            
            return grading_data
            
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
