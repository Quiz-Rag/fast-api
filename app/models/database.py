"""
SQLAlchemy database models for quiz storage.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class QuestionType(enum.Enum):
    """Question type enumeration."""
    MCQ = "mcq"
    BLANK = "blank"
    DESCRIPTIVE = "descriptive"


class Quiz(Base):
    """Quiz table - stores quiz metadata."""
    __tablename__ = "quizzes"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    topic = Column(String(255), nullable=False, index=True)
    total_questions = Column(Integer, nullable=False)
    num_mcq = Column(Integer, nullable=False)
    num_blanks = Column(Integer, nullable=False)
    num_descriptive = Column(Integer, nullable=False)
    difficulty = Column(String(50), default="medium")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")


class Question(Base):
    """Question table - stores all question types."""
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    question_type = Column(SQLEnum(QuestionType), nullable=False)
    question_text = Column(Text, nullable=False)
    question_order = Column(Integer, nullable=False)
    
    # For MCQ - storing options with IDs
    option_a_id = Column(Integer, default=1)
    option_a = Column(Text, nullable=True)
    option_b_id = Column(Integer, default=2)
    option_b = Column(Text, nullable=True)
    option_c_id = Column(Integer, default=3)
    option_c = Column(Text, nullable=True)
    option_d_id = Column(Integer, default=4)
    option_d = Column(Text, nullable=True)
    correct_option_id = Column(Integer, nullable=True)  # 1, 2, 3, or 4
    
    # For Blanks
    correct_answer = Column(Text, nullable=True)
    
    # For Descriptive
    sample_answer = Column(Text, nullable=True)
    key_points = Column(Text, nullable=True)  # JSON string of list
    
    # Common
    explanation = Column(Text, nullable=True)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="questions")


class QuizAttempt(Base):
    """Quiz attempt table - stores user submissions and scores."""
    __tablename__ = "quiz_attempts"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Optional: User identification (for future multi-user support)
    user_id = Column(String(255), nullable=True, index=True)
    user_name = Column(String(255), nullable=True)
    
    # Scores
    mcq_score = Column(Integer, default=0)
    blank_score = Column(Integer, default=0)
    descriptive_score = Column(Integer, default=0)  # AI-graded descriptive score
    total_score = Column(Integer, default=0)
    max_score = Column(Integer, nullable=False)
    percentage = Column(Float, nullable=False)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    time_taken_seconds = Column(Integer, nullable=True)  # Time to complete quiz
    
    # Store answers as JSON strings
    mcq_answers_json = Column(Text, nullable=True)  # JSON string
    blank_answers_json = Column(Text, nullable=True)  # JSON string
    descriptive_answers_json = Column(Text, nullable=True)  # JSON string
    
    # Relationships
    quiz = relationship("Quiz", backref="attempts")
    user_answers = relationship("UserAnswer", back_populates="attempt", cascade="all, delete-orphan")


class UserAnswer(Base):
    """Detailed answer storage for granular tracking."""
    __tablename__ = "user_answers"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    
    # Answer data
    selected_option_id = Column(Integer, nullable=True)  # For MCQ (1-4)
    text_answer = Column(Text, nullable=True)  # For blanks/descriptive
    is_correct = Column(Boolean, nullable=True)  # For auto-graded questions (MCQ/blanks)
    
    # Timestamps
    answered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    attempt = relationship("QuizAttempt", back_populates="user_answers")
    question = relationship("Question")
    ai_grading = relationship("DescriptiveGrading", back_populates="user_answer", uselist=False, cascade="all, delete-orphan")


class DescriptiveGrading(Base):
    """AI grading details for descriptive answers."""
    __tablename__ = "descriptive_gradings"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_answer_id = Column(Integer, ForeignKey("user_answers.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Scores
    total_score = Column(Integer, nullable=False)  # 0-100
    content_coverage_score = Column(Integer, default=0)  # 0-70
    accuracy_score = Column(Integer, default=0)  # 0-20
    clarity_score = Column(Integer, default=0)  # 0-10
    extra_content_penalty = Column(Integer, default=0)  # negative or 0
    
    # Analysis (stored as JSON strings)
    points_covered = Column(Text, nullable=True)  # JSON array
    points_missed = Column(Text, nullable=True)  # JSON array
    extra_content = Column(Text, nullable=True)  # JSON array
    feedback = Column(Text, nullable=True)
    suggestions = Column(Text, nullable=True)  # JSON array
    
    # Metadata
    graded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    model_used = Column(String(100), nullable=True)  # e.g., "llama-3.1-8b-instant"
    is_ai_graded = Column(Boolean, default=True)  # False if manual grading needed
    
    # Relationships
    user_answer = relationship("UserAnswer", back_populates="ai_grading")
