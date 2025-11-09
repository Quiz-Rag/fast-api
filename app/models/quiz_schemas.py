"""
Pydantic models for quiz API requests and responses.
"""

from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from datetime import datetime


# ============= REQUEST MODELS =============

class QuizGenerateRequest(BaseModel):
    """
    Request model for quiz generation.
    
    Supports two modes:
    1. Natural Language Mode (Recommended):
       - quiz_description: Free-form text describing what you want
       - difficulty: easy/medium/hard
    
    2. Structured Mode (Backward Compatible):
       - topic, total_questions, num_mcq, num_blanks, num_descriptive
       - difficulty: easy/medium/hard
    
    Examples:
    - "I want 10 questions: 5 from encryption, 3 from RSA, 2 from SQL injection. 
       Make 6 MCQs, 3 fill-in-blanks, and 1 descriptive."
    - "Create a quiz with 8 questions on network security focusing on firewalls 
       and intrusion detection. 5 MCQs and 3 descriptive questions."
    """
    # Natural language mode (recommended)
    quiz_description: Optional[str] = Field(
        None, 
        min_length=10, 
        max_length=1000,
        description="Natural language description of the quiz you want to generate"
    )
    
    # Structured mode (backward compatible - all optional if quiz_description provided)
    topic: Optional[str] = Field(None, min_length=1, max_length=255, description="Topic for the quiz")
    total_questions: Optional[int] = Field(None, ge=1, le=20, description="Total number of questions")
    num_mcq: Optional[int] = Field(None, ge=0, description="Number of MCQ questions")
    num_blanks: Optional[int] = Field(None, ge=0, description="Number of fill-in-the-blank questions")
    num_descriptive: Optional[int] = Field(None, ge=0, description="Number of descriptive questions")
    
    # Common field
    difficulty: Optional[str] = Field("medium", pattern="^(easy|medium|hard)$", description="Quiz difficulty level")
    
    @model_validator(mode='after')
    def validate_quiz_request(self):
        """Validate that either quiz_description or structured fields are provided."""
        has_description = self.quiz_description is not None
        has_structured = all([
            self.topic is not None,
            self.total_questions is not None,
            self.num_mcq is not None,
            self.num_blanks is not None,
            self.num_descriptive is not None
        ])
        
        # Must have either description or all structured fields
        if not has_description and not has_structured:
            raise ValueError(
                'Either provide quiz_description (natural language) OR all structured fields '
                '(topic, total_questions, num_mcq, num_blanks, num_descriptive)'
            )
        
        # If using structured mode, validate question sum
        if has_structured and not has_description:
            total = self.num_mcq + self.num_blanks + self.num_descriptive
            if total != self.total_questions:
                raise ValueError(
                    f'Sum of questions ({total}) must equal total_questions ({self.total_questions})'
                )
        
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
    quiz_description: Optional[str] = None  # Natural language description if used
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


class DescriptiveScoreBreakdown(BaseModel):
    """Breakdown of descriptive answer score."""
    content_coverage_score: int = 0  # 0-70
    accuracy_score: int = 0          # 0-20
    clarity_score: int = 0           # 0-10
    extra_content_penalty: int = 0   # 0 or negative


class DescriptiveResult(BaseModel):
    """Descriptive grading result with AI grading."""
    question_id: int
    question: str
    your_answer: str
    sample_answer: str
    key_points: List[str] = []
    explanation: str
    
    # AI Grading fields
    score: Optional[int] = None  # 0-100, None if not graded
    max_score: int = 100
    breakdown: Optional[DescriptiveScoreBreakdown] = None
    points_covered: List[str] = []
    points_missed: List[str] = []
    extra_content: List[str] = []
    feedback: str = ""
    suggestions: List[str] = []
    is_ai_graded: bool = False


class QuizGradingResponse(BaseModel):
    """Complete quiz grading response."""
    attempt_id: int
    quiz_id: int
    topic: str
    total_questions: int
    mcq_results: List[MCQResult]
    blank_results: List[BlankResult]
    descriptive_results: List[DescriptiveResult]
    
    # Individual scores
    mcq_score: int
    blank_score: int
    descriptive_score: int = 0  # AI-graded descriptive score
    
    # Totals
    total_auto_score: int  # MCQ + Blanks only (for backward compatibility)
    total_score: int  # MCQ + Blanks + Descriptive
    max_auto_score: int  # Max for MCQ + Blanks
    max_score: int  # Max including descriptive
    percentage: float  # Based on total_score/max_score
    
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
    descriptive_score: int = 0
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
    descriptive_score: int = 0
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
