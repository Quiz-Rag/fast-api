"""
Pydantic models for quiz API requests and responses.
"""

from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from datetime import datetime


# ============= REQUEST MODELS =============

class QuizGenerateRequest(BaseModel):
    """Request model for quiz generation."""
    topic: str = Field(..., min_length=1, max_length=255, description="Topic for the quiz")
    total_questions: int = Field(..., ge=1, le=20, description="Total number of questions")
    num_mcq: int = Field(..., ge=0, description="Number of MCQ questions")
    num_blanks: int = Field(..., ge=0, description="Number of fill-in-the-blank questions")
    num_descriptive: int = Field(..., ge=0, description="Number of descriptive questions")
    difficulty: Optional[str] = Field("medium", pattern="^(easy|medium|hard)$")
    collection_name: Optional[str] = Field(None, description="ChromaDB collection to search in")
    
    @model_validator(mode='after')
    def validate_question_sum(self):
        """Validate that sum of question types equals total_questions."""
        total = self.num_mcq + self.num_blanks + self.num_descriptive
        
        if total != self.total_questions:
            raise ValueError(f'Sum of questions ({total}) must equal total_questions ({self.total_questions})')
        return self


# ============= RESPONSE MODELS (WITHOUT ANSWERS) =============

class MCQOption(BaseModel):
    """MCQ option with ID."""
    option_id: int
    text: str


class MCQQuestionResponse(BaseModel):
    """MCQ question response - NO CORRECT ANSWER."""
    question_id: int
    question: str
    options: List[MCQOption]


class BlankQuestionResponse(BaseModel):
    """Fill-in-blank question response - NO ANSWER."""
    question_id: int
    question: str


class DescriptiveQuestionResponse(BaseModel):
    """Descriptive question response - NO SAMPLE ANSWER."""
    question_id: int
    question: str


class QuizResponse(BaseModel):
    """Quiz response - questions only, no answers."""
    quiz_id: int
    topic: str
    total_questions: int
    num_mcq: int
    num_blanks: int
    num_descriptive: int
    difficulty: str
    mcq_questions: List[MCQQuestionResponse]
    blank_questions: List[BlankQuestionResponse]
    descriptive_questions: List[DescriptiveQuestionResponse]
    created_at: str


# ============= SUBMISSION MODELS =============

class MCQAnswer(BaseModel):
    """MCQ answer submission."""
    question_id: int
    selected_option_id: int = Field(..., ge=1, le=4)


class BlankAnswer(BaseModel):
    """Blank answer submission."""
    question_id: int
    answer: str


class DescriptiveAnswer(BaseModel):
    """Descriptive answer submission."""
    question_id: int
    answer: str


class QuizSubmission(BaseModel):
    """Complete quiz submission."""
    quiz_id: int
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    user_name: Optional[str] = Field(None, description="Optional user name")
    mcq_answers: List[MCQAnswer] = []
    blank_answers: List[BlankAnswer] = []
    descriptive_answers: List[DescriptiveAnswer] = []
    time_taken_seconds: Optional[int] = Field(None, description="Time taken to complete quiz in seconds")


# ============= GRADING RESPONSE =============

class MCQResult(BaseModel):
    """MCQ grading result."""
    question_id: int
    question: str
    your_answer: int
    your_answer_text: str
    correct_answer: int
    correct_answer_text: str
    is_correct: bool
    explanation: str


class BlankResult(BaseModel):
    """Blank grading result."""
    question_id: int
    question: str
    your_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str


class DescriptiveResult(BaseModel):
    """Descriptive grading result."""
    question_id: int
    question: str
    your_answer: str
    sample_answer: str
    key_points: List[str]
    explanation: str


class QuizGradingResponse(BaseModel):
    """Complete quiz grading response."""
    attempt_id: int
    quiz_id: int
    topic: str
    total_questions: int
    mcq_results: List[MCQResult]
    blank_results: List[BlankResult]
    descriptive_results: List[DescriptiveResult]
    mcq_score: int
    blank_score: int
    total_auto_score: int
    max_auto_score: int
    percentage: float
    time_taken_seconds: Optional[int] = None
    submitted_at: str


class QuizListItem(BaseModel):
    """Quiz list item."""
    quiz_id: int
    topic: str
    total_questions: int
    difficulty: str
    created_at: str


# ============= QUIZ ATTEMPT MODELS =============

class QuizAttemptSummary(BaseModel):
    """Summary of a quiz attempt."""
    attempt_id: int
    quiz_id: int
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    mcq_score: int
    blank_score: int
    total_score: int
    max_score: int
    percentage: float
    time_taken_seconds: Optional[int] = None
    submitted_at: str


class QuizAttemptDetail(BaseModel):
    """Detailed quiz attempt with all answers."""
    attempt_id: int
    quiz_id: int
    quiz_topic: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    mcq_score: int
    blank_score: int
    total_score: int
    max_score: int
    percentage: float
    time_taken_seconds: Optional[int] = None
    submitted_at: str
    mcq_results: List[MCQResult]
    blank_results: List[BlankResult]
    descriptive_results: List[DescriptiveResult]


class QuizAnalytics(BaseModel):
    """Analytics for a specific quiz."""
    quiz_id: int
    topic: str
    total_attempts: int
    average_score: float
    highest_score: float
    lowest_score: float
    average_time_seconds: Optional[float] = None
    completion_rate: float  # percentage of users who completed
