"""
Pydantic models for LangChain structured output parsing.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class MCQQuestion(BaseModel):
    """Multiple choice question structure."""
    question: str = Field(description="The question text")
    options: List[str] = Field(description="List of 4 answer options")
    correct: int = Field(description="Index of correct answer (1-4)")
    explanation: str = Field(description="Explanation of the correct answer")


class FillInBlankQuestion(BaseModel):
    """Fill-in-the-blank question structure."""
    question: str = Field(description="Question text with blank")
    answer: str = Field(description="Correct answer (1-3 words)")
    explanation: str = Field(description="Explanation of the answer")


class DescriptiveQuestion(BaseModel):
    """Descriptive/short answer question structure."""
    question: str = Field(description="Descriptive question text")
    sample_answer: str = Field(description="Sample answer with key points")
    key_points: List[str] = Field(description="List of key points that must be covered")
    explanation: str = Field(description="What makes this a good answer")


class QuizGenerationOutput(BaseModel):
    """Structure for quiz generation JSON output."""
    mcq: List[MCQQuestion] = Field(default_factory=list, description="Multiple choice questions")
    blanks: List[FillInBlankQuestion] = Field(default_factory=list, description="Fill-in-the-blank questions")
    descriptive: List[DescriptiveQuestion] = Field(default_factory=list, description="Descriptive questions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "mcq": [
                    {
                        "question": "What is RSA?",
                        "options": ["A cipher", "An encryption algorithm", "A hash function", "A protocol"],
                        "correct": 2,
                        "explanation": "RSA is a public-key encryption algorithm"
                    }
                ],
                "blanks": [],
                "descriptive": []
            }
        }


class QuizErrorOutput(BaseModel):
    """Structure for quiz generation error output."""
    error: str = Field(description="Error type: 'insufficient_content' or 'out_of_scope'")
    message: str = Field(description="Error message explaining the issue")


class TopicBreakdown(BaseModel):
    """Topic breakdown structure."""
    topic: str = Field(description="Topic name")
    questions: int = Field(description="Number of questions for this topic")


class QuizDescriptionOutput(BaseModel):
    """Structure for quiz description parsing output."""
    topic: str = Field(description="Main topic or combined topics")
    total_questions: int = Field(description="Total number of questions")
    num_mcq: int = Field(description="Number of multiple choice questions")
    num_blanks: int = Field(description="Number of fill-in-the-blank questions")
    num_descriptive: int = Field(description="Number of descriptive questions")
    topic_breakdown: List[TopicBreakdown] = Field(default_factory=list, description="Breakdown by topic")


class QuizDescriptionError(BaseModel):
    """Structure for quiz description parsing error."""
    error: str = Field(description="Error type: 'out_of_scope'")
    message: str = Field(description="Error message")


class GradingBreakdown(BaseModel):
    """Grading score breakdown."""
    content_coverage_score: int = Field(description="Content coverage score (0-70)")
    accuracy_score: int = Field(description="Accuracy score (0-20)")
    clarity_score: int = Field(description="Clarity score (0-10)")
    extra_content_penalty: int = Field(description="Penalty for extra content (0 or negative)")


class GradingOutput(BaseModel):
    """Structure for AI grading output."""
    score: int = Field(description="Total score (0-100)")
    breakdown: GradingBreakdown = Field(description="Score breakdown")
    points_covered: List[str] = Field(default_factory=list, description="Key points found in answer")
    points_missed: List[str] = Field(default_factory=list, description="Key points not found")
    extra_content: List[str] = Field(default_factory=list, description="Irrelevant topics mentioned")
    feedback: str = Field(description="Feedback explaining the score")
    suggestions: List[str] = Field(default_factory=list, description="Specific improvements needed")


class ContextEvaluationOutput(BaseModel):
    """Structure for context sufficiency evaluation."""
    code: int = Field(description="Evaluation code: 0 = not NS related, 1 = NS related but context insufficient, 2 = NS related and context sufficient")
    reason: str = Field(description="Brief explanation for the evaluation code")

