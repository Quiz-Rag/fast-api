"""
API routes for quiz generation and grading.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.quiz_service import QuizService
from app.models.quiz_schemas import *
from typing import List
import logging

router = APIRouter(prefix="/quiz", tags=["quiz"])
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def generate_quiz(
    request: QuizGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a quiz on a specific topic with AI-powered security.
    
    **Features:**
    - Natural language quiz descriptions or structured parameters
    - Retrieves relevant content from ChromaDB based on topic
    - Uses Groq AI to generate questions
    - Saves quiz to database with answers
    - Returns questions WITHOUT answers to frontend
    
    **Security:**
    - Input sanitization to prevent prompt injection
    - Restricted to Network Security topics only
    - Requires sufficient course material (similarity threshold 0.6)
    - Minimum 3 relevant documents required
    
    **Error Responses:**
    - 400: Out of scope topic or invalid request
    - 404: Insufficient course material
    - 500: Internal server error
    
    **Note:** Answers are stored server-side and only revealed after submission.
    """
    try:
        quiz_service = QuizService()
        return await quiz_service.generate_quiz(request, db)
    except HTTPException:
        # Re-raise HTTPException from service layer (already has proper status and detail)
        raise
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error in generate_quiz: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the quiz. Please try again."
        )


@router.post("/submit", response_model=QuizGradingResponse)
async def submit_quiz(
    submission: QuizSubmission,
    db: Session = Depends(get_db)
):
    """
    Submit quiz answers and get grading results.
    
    - Takes quiz_id and answers for all questions
    - Compares with correct answers stored in database
    - Auto-grades MCQ and fill-in-the-blank questions
    - AI-grades descriptive questions with detailed feedback
    - Provides detailed explanations for all questions
    """
    try:
        quiz_service = QuizService()
        return await quiz_service.grade_quiz(submission, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve a previously generated quiz (without answers).
    
    Useful for:
    - Reviewing quiz questions
    - Retaking a quiz
    - Sharing quiz with others
    """
    try:
        quiz_service = QuizService()
        return quiz_service.get_quiz(quiz_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/list/all", response_model=List[QuizListItem])
async def list_quizzes(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    List all generated quizzes with basic information.
    
    - Supports pagination with skip and limit
    - Returns quiz metadata (topic, question count, date)
    - Ordered by most recent first
    """
    try:
        quiz_service = QuizService()
        return quiz_service.list_quizzes(skip, limit, db)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{quiz_id}/attempts", response_model=List[QuizAttemptSummary])
async def get_quiz_attempts(
    quiz_id: int,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get all attempts for a specific quiz.
    
    - Shows summary of each attempt (score, user, timestamp)
    - Useful for tracking quiz performance
    - Supports pagination
    """
    try:
        quiz_service = QuizService()
        return quiz_service.get_quiz_attempts(quiz_id, skip, limit, db)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/attempt/{attempt_id}", response_model=QuizAttemptDetail)
async def get_attempt_detail(
    attempt_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific quiz attempt.
    
    - Returns all questions, answers, and results
    - Useful for reviewing past attempts
    - Includes explanations and correct answers
    """
    try:
        quiz_service = QuizService()
        return quiz_service.get_attempt_detail(attempt_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{quiz_id}/analytics", response_model=QuizAnalytics)
async def get_quiz_analytics(
    quiz_id: int,
    db: Session = Depends(get_db)
):
    """
    Get analytics for a specific quiz.
    
    - Shows average score, highest/lowest scores
    - Average time taken
    - Total attempts
    - Completion rate
    """
    try:
        quiz_service = QuizService()
        return quiz_service.get_quiz_analytics(quiz_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/user/{user_id}/attempts", response_model=List[QuizAttemptSummary])
async def get_user_attempts(
    user_id: str,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get all quiz attempts by a specific user.
    
    - Shows all quizzes taken by the user
    - Ordered by most recent first
    - Supports pagination
    - Useful for user progress tracking
    """
    try:
        quiz_service = QuizService()
        return quiz_service.get_user_attempts(user_id, skip, limit, db)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
