"""
Quiz service for generating and grading quizzes.
"""

from sqlalchemy.orm import Session
from app.models.database import Quiz, Question, QuestionType, QuizAttempt, UserAnswer, DescriptiveGrading
from app.models.quiz_schemas import *
from app.services.chroma_service import ChromaService
from app.services.rag_service import RAGService
from app.services.ai_service import AIService
from app.services.ai_grading_service import ai_grading_service
from app.security.input_sanitizer import sanitize_quiz_description
from app.config import settings
from fastapi import HTTPException
import json
import asyncio
import random
from typing import List, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class QuizService:
    """Service for quiz generation and grading."""
    
    # Predefined list of available topics (95 topics)
    AVAILABLE_TOPICS = [
        "Basic Concepts of Network Security",
        "Security Requirements",
        "Security Architecture",
        "Security Attacks",
        "Active Attacks",
        "Passive Attacks",
        "Human Factors in Security and Design",
        "Model of Network Security",
        "Symmetric Encryption Principles",
        "Symmetric Encryption Attacks",
        "Cryptanalysis",
        "Encryption Schemes",
        "Types of Encryption",
        "DES (Data Encryption Standard)",
        "Triple DES (3DES)",
        "AES (Advanced Encryption Standard)",
        "Encryption Criteria and Evaluation",
        "Stream Cipher",
        "Block Cipher",
        "Random Numbers",
        "Properties of Random Numbers",
        "Entropy",
        "True Random Number Generator",
        "Pseudorandom Number Generator",
        "Random Number Generation Algorithms",
        "Random Number Security",
        "RSA Encryption",
        # Public-Key Cryptography topics
        "Public-Key Cryptography",
        "Conventional Cryptography and Pros & Cons",
        "Public-Key Cryptography - Encryption and Definition",
        "Encryption Steps",
        "Public-Key Cryptography - Signature",
        "Public-Key Application",
        "TLS 1.2 – Use Public Key for Session Key Exchange",
        "Security of Public Key Schemes",
        "RSA Public-key Encryption",
        "RSA Key Setup",
        "RSA Key Generation",
        "RSA Example & RSA Use",
        "Correctness of RSA",
        "Attack Approaches",
        "RSA Decryption With Message Blinding",
        "A Simple Attack on Textbook RSA",
        "Homomorphic Encryption",
        "Application of Homomorphic Encryption",
        # Message Authentication topics
        "Message Authentication",
        "Message Encryption",
        "Reasons to Avoid Encryption Authentication",
        "Hash Function",
        "One Use Case - Using Hash Function",
        "Requirements for Secure Hash Functions",
        "Hash Function: Collision Resistance",
        "Hash Function: Examples",
        "Length Extension Attacks",
        "Merkle-Damgard Scheme",
        "Do Hashes Provide Integrity?",
        "Man-in-the-Middle Attack",
        "Message Authentication Code",
        "MACs: Usage & Definition",
        "Randomized MAC (Non-Deterministic)",
        "Existentially Unforgeable",
        "Example: HMAC",
        "HMAC(K, M)",
        "HMAC Procedure",
        "HMAC Properties",
        "Do MACs Provide Integrity?",
        # Authenticated Encryption topics
        "Authenticated Encryption Definition",
        "Authenticated Encryption: Scratchpad",
        "MAC-then-Encrypt or Encrypt-then-MAC?",
        "TLS 1.0 \"Lucky 13\" Attack",
        "Authenticated Encryption: Summary",
        # Digital Signature topics
        "Digital Signature",
        "Digital Signatures: Definition",
        "RSA Signature",
        "RSA Probabilistic Digital Signature Scheme (RSA-PSS)",
        "RSA Signatures: Correctness",
        "RSA Digital Signature: Security",
        "Hybrid Encryption",
        # Authentication topics
        "Remote User Authentication Principles",
        "Means of User Authentication",
        "News about Bitcoins",
        "Ways to Achieve Symmetric Key Distribution",
        "Many-to-Many Authentication",
        # Kerberos topics
        "Kerberos: Threats",
        "Kerberos: Requirements",
        "A Simple Authentication Dialogue",
        "A More Secure Authentication Dialogue",
        "Ticket Hijacking",
        "No Server Authentication",
        "Kerberos v4 - Once Per User Logon Session",
        "Kerberos v4 - Once Per Service Session",
        "Overview of Kerberos",
        "Important Ideas in Kerberos",
        "Kerberos in Large Networks",
        "Practical Uses of Kerberos"
    ]
    
    # Available difficulty levels
    AVAILABLE_DIFFICULTIES = ["easy", "medium", "hard"]
    
    def __init__(self):
        """Initialize services."""
        self.chroma = ChromaService()
        self.rag = RAGService()
        self.ai = AIService()
    
    async def _retrieve_content(self, topic: str) -> str:
        """
        Retrieve top 20 most relevant documents from ChromaDB.
        Let the LLM handle content validation and relevance filtering.
        Supports multi-topic queries (comma-separated topics).
        
        Args:
            topic: Topic to search for (can be single topic or multiple topics like "Topic1, Topic2, and Topic3")
            
        Returns:
            Combined content from top documents
            
        Raises:
            HTTPException: If no documents found at all
        """
        try:
            import re
            
            # Check if multi-topic (contains "and" or multiple commas)
            is_multi_topic = ", and " in topic or (topic.count(",") >= 2)
            
            if is_multi_topic:
                # Multi-topic: search each topic separately and combine results
                topic_list = [t.strip() for t in topic.replace(" and ", ",").split(",")]
                all_documents = []
                
                logger.info(f"Multi-topic query detected: {topic_list}")
                
                for single_topic in topic_list:
                    try:
                        # Clean query for better embedding
                        clean_topic = re.sub(r'[^\w\s]', ' ', single_topic)
                        clean_topic = ' '.join(clean_topic.split())  # Normalize whitespace
                        
                        # Use LangChain retriever
                        retriever = self.rag.get_retriever(collection_name=None, k=10)
                        docs = retriever.invoke(clean_topic)  # LangChain 1.0+ uses invoke instead of get_relevant_documents
                        if docs:
                            all_documents.extend([doc.page_content for doc in docs])
                    except Exception as e:
                        logger.warning(f"Failed to search topic '{single_topic}': {e}")
                
                # Deduplicate and limit to top 20
                unique_docs = list(dict.fromkeys(all_documents))[:20]
                if not unique_docs:
                    raise HTTPException(
                        status_code=404,
                        detail="No course material found for selected topics. Please upload relevant documents first."
                    )
                documents = unique_docs
                logger.info(f"Retrieved {len(documents)} unique documents from {len(topic_list)} topics")
            else:
                # Single topic - existing logic
                # Clean query for better embedding
                clean_topic = re.sub(r'[^\w\s]', ' ', topic)
                clean_topic = ' '.join(clean_topic.split())  # Normalize whitespace
                
                logger.info(f"Searching for topic: '{topic}' (cleaned: '{clean_topic}')")
                
                # Use LangChain retriever to get top 20 documents
                retriever = self.rag.get_retriever(
                    collection_name=None,  # Search all collections
                    k=20  # Get top 20, let LLM decide what's relevant
                )
                
                retrieved_docs = retriever.invoke(clean_topic)  # LangChain 1.0+ uses invoke instead of get_relevant_documents
                
                if not retrieved_docs:
                    raise HTTPException(
                        status_code=404,
                        detail=f"I don't have any course material in the database. Please upload relevant documents first."
                    )
                
                documents = [doc.page_content for doc in retrieved_docs]
                logger.info(f"Retrieved {len(documents)} documents using LangChain retriever")
            
            # Combine all documents - no filtering, let LLM handle it
            content = "\n\n".join(documents)
            
            # Limit content length (approximately 3000 words for LLM context)
            words = content.split()
            if len(words) > 3000:
                content = " ".join(words[:3000])
                logger.info(f"Content truncated to 3000 words for LLM context")
            
            logger.info(f"✓ Passing {len(documents)} documents to LLM for validation")
            return content
            
        except HTTPException:
            raise  # Re-raise HTTP exceptions as-is
        except Exception as e:
            logger.error(f"Failed to retrieve content: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve course content: {str(e)}"
            )
    
    def _select_random_topics(self, count: int = 3) -> List[str]:
        """Select random topics from predefined list using random indices."""
        if len(self.AVAILABLE_TOPICS) < count:
            raise ValueError(f"Not enough topics available (need {count}, have {len(self.AVAILABLE_TOPICS)})")
        selected = random.sample(self.AVAILABLE_TOPICS, count)
        logger.info(f"Randomly selected {count} topics: {selected}")
        return selected
    
    def _select_random_difficulty(self) -> str:
        """Select random difficulty from predefined list."""
        difficulty = random.choice(self.AVAILABLE_DIFFICULTIES)
        logger.info(f"Randomly selected difficulty: {difficulty}")
        return difficulty
    
    def _combine_topics_string(self, selected_topics: List[str]) -> str:
        """Combine topics into readable string format."""
        if len(selected_topics) == 1:
            return selected_topics[0]
        elif len(selected_topics) == 2:
            return f"{selected_topics[0]} and {selected_topics[1]}"
        else:
            return ", ".join(selected_topics[:-1]) + f", and {selected_topics[-1]}"
    
    def _randomize_question_distribution(self, total_questions: int) -> Tuple[int, int, int]:
        """Randomly distribute questions across types with weighted distribution."""
        if total_questions < 3:
            # Simple distribution for small quizzes
            num_mcq = max(1, total_questions // 2)
            num_blanks = max(0, (total_questions - num_mcq) // 2)
            num_descriptive = total_questions - num_mcq - num_blanks
        else:
            # Ensure at least 1 of each type
            num_mcq = 1
            num_blanks = 1
            num_descriptive = 1
            remaining = total_questions - 3
            
            # Weighted random: MCQ=55%, Blanks=35%, Descriptive=10%
            for _ in range(remaining):
                rand = random.random()
                if rand < 0.55:
                    num_mcq += 1
                elif rand < 0.90:
                    num_blanks += 1
                else:
                    num_descriptive += 1
        
        logger.info(f"Random distribution: MCQ={num_mcq}, Blanks={num_blanks}, Descriptive={num_descriptive}")
        return (num_mcq, num_blanks, num_descriptive)
    
    async def generate_quiz(
        self,
        request: QuizGenerateRequest,
        db: Session
    ) -> QuizResponse:
        """
        Generate quiz and save to database.
        Supports random mode, natural language, and structured input.
        Returns quiz WITHOUT answers.
        
        Raises:
            HTTPException: For various error conditions (404, 400, 500)
        """
        # Handle random mode - everything is auto-selected
        if request.random:
            # Select 3 random topics from predefined list
            selected_topics = self._select_random_topics(3)
            topic = self._combine_topics_string(selected_topics)
            
            # Select random difficulty
            difficulty = self._select_random_difficulty()
            
            # Randomize question distribution
            total_questions = request.total_questions or 10
            num_mcq, num_blanks, num_descriptive = self._randomize_question_distribution(total_questions)
            
            quiz_description = f"Random quiz covering {topic}"
            
            logger.info(f"Random quiz: topics={selected_topics}, difficulty={difficulty}, "
                       f"distribution=({num_mcq}, {num_blanks}, {num_descriptive}), "
                       f"total={total_questions}")
        # Determine mode and parse if needed
        elif request.quiz_description:
            # Sanitize input to prevent prompt injection
            sanitized_description = sanitize_quiz_description(request.quiz_description)
            
            if not sanitized_description or len(sanitized_description) < 10:
                raise HTTPException(
                    status_code=400,
                    detail="Quiz description is too short or contains only invalid characters. "
                           "Please provide a meaningful description of the quiz you want."
                )
            
            # Natural language mode - parse description
            parsed = await self.ai.parse_quiz_description(
                sanitized_description,
                request.difficulty or "medium"
            )
            
            # Check if AI detected out-of-scope topic
            if "error" in parsed:
                error_type = parsed.get("error")
                message = parsed.get("message", "Invalid quiz request")
                
                if error_type == "out_of_scope":
                    raise HTTPException(status_code=400, detail=message)
                else:
                    raise HTTPException(status_code=400, detail=message)
            
            # Use parsed values
            topic = parsed["topic"]
            total_questions = parsed["total_questions"]
            num_mcq = parsed["num_mcq"]
            num_blanks = parsed["num_blanks"]
            num_descriptive = parsed["num_descriptive"]
            difficulty = request.difficulty or "medium"
            quiz_description = sanitized_description
        else:
            # Structured mode - use provided values
            topic = request.topic
            total_questions = request.total_questions
            num_mcq = request.num_mcq
            num_blanks = request.num_blanks
            num_descriptive = request.num_descriptive
            difficulty = request.difficulty or "medium"
            quiz_description = None
        
        # 1. Retrieve relevant content from ChromaDB (with threshold filtering)
        content = await self._retrieve_content(topic)
        
        # 2. Generate quiz using AI (with security boundaries)
        ai_response = await self.ai.generate_quiz(
            topic=topic,
            content=content,
            num_mcq=num_mcq,
            num_blanks=num_blanks,
            num_descriptive=num_descriptive,
            difficulty=difficulty
        )
        
        # 3. Check if AI returned an error
        if isinstance(ai_response, dict) and "error" in ai_response:
            error_type = ai_response.get("error")
            message = ai_response.get("message", "Failed to generate quiz")
            
            if error_type == "insufficient_content":
                raise HTTPException(status_code=404, detail=message)
            elif error_type == "out_of_scope":
                raise HTTPException(status_code=400, detail=message)
            else:
                raise HTTPException(status_code=500, detail=message)
        
        # 4. Create quiz in database
        quiz_db = Quiz(
            quiz_description=quiz_description,
            topic=topic,
            total_questions=total_questions,
            num_mcq=num_mcq,
            num_blanks=num_blanks,
            num_descriptive=num_descriptive,
            difficulty=difficulty
        )
        db.add(quiz_db)
        db.flush()  # Get quiz ID
        
        # 4. Save MCQ questions
        for idx, mcq in enumerate(ai_response.get('mcq', [])):
            question = Question(
                quiz_id=quiz_db.id,
                question_type=QuestionType.MCQ,
                question_text=mcq['question'],
                question_order=idx + 1,
                option_a_id=1,
                option_a=mcq['options'][0],
                option_b_id=2,
                option_b=mcq['options'][1],
                option_c_id=3,
                option_c=mcq['options'][2],
                option_d_id=4,
                option_d=mcq['options'][3],
                correct_option_id=mcq['correct'],
                explanation=mcq['explanation']
            )
            db.add(question)
        
        # 5. Save Blank questions
        for idx, blank in enumerate(ai_response.get('blanks', [])):
            question = Question(
                quiz_id=quiz_db.id,
                question_type=QuestionType.BLANK,
                question_text=blank['question'],
                question_order=num_mcq + idx + 1,
                correct_answer=blank['answer'],
                explanation=blank['explanation']
            )
            db.add(question)
        
        # 6. Save Descriptive questions
        for idx, desc in enumerate(ai_response.get('descriptive', [])):
            question = Question(
                quiz_id=quiz_db.id,
                question_type=QuestionType.DESCRIPTIVE,
                question_text=desc['question'],
                question_order=num_mcq + num_blanks + idx + 1,
                sample_answer=desc['sample_answer'],
                key_points=json.dumps(desc['key_points']),
                explanation=desc['explanation']
            )
            db.add(question)
        
        db.commit()
        db.refresh(quiz_db)
        
        # 7. Return quiz WITHOUT answers
        return self._build_response_without_answers(quiz_db)
    
    def _build_response_without_answers(self, quiz_db: Quiz) -> QuizResponse:
        """Build response WITHOUT answers for frontend."""
        mcq_questions = []
        blank_questions = []
        descriptive_questions = []
        
        for q in sorted(quiz_db.questions, key=lambda x: x.question_order):
            if q.question_type == QuestionType.MCQ:
                options = [
                    MCQOption(option_id=q.option_a_id, text=q.option_a),
                    MCQOption(option_id=q.option_b_id, text=q.option_b),
                    MCQOption(option_id=q.option_c_id, text=q.option_c),
                    MCQOption(option_id=q.option_d_id, text=q.option_d)
                ]
                mcq_questions.append(MCQQuestionResponse(
                    question_id=q.id,
                    question=q.question_text,
                    options=options
                ))
            
            elif q.question_type == QuestionType.BLANK:
                blank_questions.append(BlankQuestionResponse(
                    question_id=q.id,
                    question=q.question_text
                ))
            
            elif q.question_type == QuestionType.DESCRIPTIVE:
                descriptive_questions.append(DescriptiveQuestionResponse(
                    question_id=q.id,
                    question=q.question_text
                ))
        
        return QuizResponse(
            quiz_id=quiz_db.id,
            quiz_description=quiz_db.quiz_description,
            topic=quiz_db.topic,
            total_questions=quiz_db.total_questions,
            num_mcq=quiz_db.num_mcq,
            num_blanks=quiz_db.num_blanks,
            num_descriptive=quiz_db.num_descriptive,
            difficulty=quiz_db.difficulty,
            mcq_questions=mcq_questions,
            blank_questions=blank_questions,
            descriptive_questions=descriptive_questions,
            created_at=quiz_db.created_at.isoformat()
        )
    
    async def grade_quiz(
        self,
        submission: QuizSubmission,
        db: Session
    ) -> QuizGradingResponse:
        """
        Grade submitted quiz by comparing with stored answers.
        Also saves the attempt to database.
        """
        # Load quiz from database
        quiz = db.query(Quiz).filter(Quiz.id == submission.quiz_id).first()
        if not quiz:
            raise ValueError("Quiz not found")
        
        # Create question lookup
        questions = {q.id: q for q in quiz.questions}
        
        # Grade MCQs
        mcq_results = []
        mcq_score = 0
        
        for mcq_answer in submission.mcq_answers:
            question = questions.get(mcq_answer.question_id)
            if not question or question.question_type != QuestionType.MCQ:
                continue
            
            is_correct = question.correct_option_id == mcq_answer.selected_option_id
            if is_correct:
                mcq_score += 1
            
            # Get option texts
            options_map = {
                1: question.option_a,
                2: question.option_b,
                3: question.option_c,
                4: question.option_d
            }
            
            mcq_results.append(MCQResult(
                question_id=question.id,
                question=question.question_text,
                your_answer=mcq_answer.selected_option_id,
                your_answer_text=options_map.get(mcq_answer.selected_option_id, ""),
                correct_answer=question.correct_option_id,
                correct_answer_text=options_map.get(question.correct_option_id, ""),
                is_correct=is_correct,
                explanation=question.explanation
            ))
        
        # Grade Blanks (case-insensitive, strip whitespace)
        blank_results = []
        blank_score = 0
        
        for blank_answer in submission.blank_answers:
            question = questions.get(blank_answer.question_id)
            if not question or question.question_type != QuestionType.BLANK:
                continue
            
            user_answer = blank_answer.answer.strip().lower()
            correct_answer = question.correct_answer.strip().lower()
            is_correct = user_answer == correct_answer
            
            if is_correct:
                blank_score += 1
            
            blank_results.append(BlankResult(
                question_id=question.id,
                question=question.question_text,
                your_answer=blank_answer.answer,
                correct_answer=question.correct_answer,
                is_correct=is_correct,
                explanation=question.explanation
            ))
        
        # Descriptive questions - AI-powered grading
        descriptive_results = []
        descriptive_score = 0
        max_descriptive_score = 0
        
        for desc_answer in submission.descriptive_answers:
            question = questions.get(desc_answer.question_id)
            if not question or question.question_type != QuestionType.DESCRIPTIVE:
                continue
            
            # Parse key points
            key_points = json.loads(question.key_points) if question.key_points else []
            
            # Grade using AI
            grading_result = await ai_grading_service.grade_descriptive_answer(
                question=question.question_text,
                expected_answer=question.sample_answer or "",
                user_answer=desc_answer.answer,
                key_points=key_points
            )
            
            # Add to descriptive score if AI grading succeeded
            if grading_result.get("is_ai_graded") and grading_result.get("score") is not None:
                descriptive_score += grading_result["score"]
                max_descriptive_score += 100
            
            # Create result with AI grading details
            descriptive_results.append(DescriptiveResult(
                question_id=question.id,
                question=question.question_text,
                your_answer=desc_answer.answer,
                sample_answer=question.sample_answer or "",
                key_points=key_points,
                explanation=question.explanation or "",
                score=grading_result.get("score"),
                max_score=100,
                breakdown=DescriptiveScoreBreakdown(**grading_result.get("breakdown", {})) if grading_result.get("breakdown") else None,
                points_covered=grading_result.get("points_covered", []),
                points_missed=grading_result.get("points_missed", []),
                extra_content=grading_result.get("extra_content", []),
                feedback=grading_result.get("feedback", ""),
                suggestions=grading_result.get("suggestions", []),
                is_ai_graded=grading_result.get("is_ai_graded", False)
            ))
        
        # Calculate total scores including descriptive
        total_auto_score = mcq_score + blank_score  # For backward compatibility
        max_auto_score = quiz.num_mcq + quiz.num_blanks
        total_score = mcq_score + blank_score + descriptive_score
        max_score = quiz.num_mcq + quiz.num_blanks + max_descriptive_score
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        
        # Save attempt to database
        attempt = QuizAttempt(
            quiz_id=quiz.id,
            user_id=submission.user_id,
            user_name=submission.user_name,
            mcq_score=mcq_score,
            blank_score=blank_score,
            descriptive_score=descriptive_score,
            total_score=total_score,
            max_score=max_score,
            percentage=round(percentage, 2),
            time_taken_seconds=submission.time_taken_seconds,
            mcq_answers_json=json.dumps([ans.dict() for ans in submission.mcq_answers]),
            blank_answers_json=json.dumps([ans.dict() for ans in submission.blank_answers]),
            descriptive_answers_json=json.dumps([ans.dict() for ans in submission.descriptive_answers]),
            submitted_at=datetime.utcnow()
        )
        db.add(attempt)
        db.flush()  # Get attempt ID
        
        # Save individual user answers for detailed tracking
        for mcq_answer in submission.mcq_answers:
            question = questions.get(mcq_answer.question_id)
            if question and question.question_type == QuestionType.MCQ:
                user_answer = UserAnswer(
                    attempt_id=attempt.id,
                    question_id=question.id,
                    selected_option_id=mcq_answer.selected_option_id,
                    is_correct=question.correct_option_id == mcq_answer.selected_option_id
                )
                db.add(user_answer)
        
        for blank_answer in submission.blank_answers:
            question = questions.get(blank_answer.question_id)
            if question and question.question_type == QuestionType.BLANK:
                is_correct = blank_answer.answer.strip().lower() == question.correct_answer.strip().lower()
                user_answer = UserAnswer(
                    attempt_id=attempt.id,
                    question_id=question.id,
                    text_answer=blank_answer.answer,
                    is_correct=is_correct
                )
                db.add(user_answer)
        
        # Save descriptive answers with AI grading
        for idx, desc_answer in enumerate(submission.descriptive_answers):
            question = questions.get(desc_answer.question_id)
            if question and question.question_type == QuestionType.DESCRIPTIVE:
                user_answer = UserAnswer(
                    attempt_id=attempt.id,
                    question_id=question.id,
                    text_answer=desc_answer.answer,
                    is_correct=None  # Not applicable for descriptive
                )
                db.add(user_answer)
                db.flush()  # Get user_answer ID
                
                # Save AI grading details
                if idx < len(descriptive_results):
                    result = descriptive_results[idx]
                    if result.is_ai_graded and result.score is not None:
                        ai_grading = DescriptiveGrading(
                            user_answer_id=user_answer.id,
                            total_score=result.score,
                            content_coverage_score=result.breakdown.content_coverage_score if result.breakdown else 0,
                            accuracy_score=result.breakdown.accuracy_score if result.breakdown else 0,
                            clarity_score=result.breakdown.clarity_score if result.breakdown else 0,
                            extra_content_penalty=result.breakdown.extra_content_penalty if result.breakdown else 0,
                            points_covered=json.dumps(result.points_covered),
                            points_missed=json.dumps(result.points_missed),
                            extra_content=json.dumps(result.extra_content),
                            feedback=result.feedback,
                            suggestions=json.dumps(result.suggestions),
                            model_used=settings.groq_model,
                            is_ai_graded=True,
                            graded_at=datetime.utcnow()
                        )
                        db.add(ai_grading)
        
        db.commit()
        db.refresh(attempt)
        
        return QuizGradingResponse(
            attempt_id=attempt.id,
            quiz_id=quiz.id,
            topic=quiz.topic,
            total_questions=quiz.total_questions,
            mcq_results=mcq_results,
            blank_results=blank_results,
            descriptive_results=descriptive_results,
            mcq_score=mcq_score,
            blank_score=blank_score,
            descriptive_score=descriptive_score,
            total_auto_score=total_auto_score,
            total_score=total_score,
            max_auto_score=max_auto_score,
            max_score=max_score,
            percentage=round(percentage, 2),
            time_taken_seconds=submission.time_taken_seconds,
            submitted_at=attempt.submitted_at.isoformat()
        )
    
    def get_quiz(self, quiz_id: int, db: Session) -> QuizResponse:
        """Get quiz by ID without answers."""
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise ValueError("Quiz not found")
        return self._build_response_without_answers(quiz)
    
    def list_quizzes(
        self,
        skip: int,
        limit: int,
        db: Session
    ) -> List[QuizListItem]:
        """List all quizzes."""
        quizzes = db.query(Quiz).order_by(Quiz.created_at.desc()).offset(skip).limit(limit).all()
        return [
            QuizListItem(
                quiz_id=q.id,
                topic=q.topic,
                total_questions=q.total_questions,
                difficulty=q.difficulty,
                created_at=q.created_at.isoformat()
            )
            for q in quizzes
        ]
    
    def get_quiz_attempts(
        self,
        quiz_id: int,
        skip: int,
        limit: int,
        db: Session
    ) -> List[QuizAttemptSummary]:
        """Get all attempts for a specific quiz."""
        attempts = db.query(QuizAttempt)\
            .filter(QuizAttempt.quiz_id == quiz_id)\
            .order_by(QuizAttempt.submitted_at.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()
        
        return [
            QuizAttemptSummary(
                attempt_id=att.id,
                quiz_id=att.quiz_id,
                user_id=att.user_id,
                user_name=att.user_name,
                mcq_score=att.mcq_score,
                blank_score=att.blank_score,
                total_score=att.total_score,
                max_score=att.max_score,
                percentage=att.percentage,
                time_taken_seconds=att.time_taken_seconds,
                submitted_at=att.submitted_at.isoformat()
            )
            for att in attempts
        ]
    
    def get_attempt_detail(
        self,
        attempt_id: int,
        db: Session
    ) -> QuizAttemptDetail:
        """Get detailed information about a specific attempt."""
        attempt = db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id).first()
        if not attempt:
            raise ValueError("Attempt not found")
        
        quiz = attempt.quiz
        
        # Reconstruct results from stored answers
        mcq_answers = json.loads(attempt.mcq_answers_json) if attempt.mcq_answers_json else []
        blank_answers = json.loads(attempt.blank_answers_json) if attempt.blank_answers_json else []
        descriptive_answers = json.loads(attempt.descriptive_answers_json) if attempt.descriptive_answers_json else []
        
        # Get questions
        questions = {q.id: q for q in quiz.questions}
        
        # Rebuild MCQ results
        mcq_results = []
        for ans in mcq_answers:
            question = questions.get(ans['question_id'])
            if question:
                options_map = {
                    1: question.option_a,
                    2: question.option_b,
                    3: question.option_c,
                    4: question.option_d
                }
                is_correct = question.correct_option_id == ans['selected_option_id']
                mcq_results.append(MCQResult(
                    question_id=question.id,
                    question=question.question_text,
                    your_answer=ans['selected_option_id'],
                    your_answer_text=options_map.get(ans['selected_option_id'], ""),
                    correct_answer=question.correct_option_id,
                    correct_answer_text=options_map.get(question.correct_option_id, ""),
                    is_correct=is_correct,
                    explanation=question.explanation
                ))
        
        # Rebuild blank results
        blank_results = []
        for ans in blank_answers:
            question = questions.get(ans['question_id'])
            if question:
                is_correct = ans['answer'].strip().lower() == question.correct_answer.strip().lower()
                blank_results.append(BlankResult(
                    question_id=question.id,
                    question=question.question_text,
                    your_answer=ans['answer'],
                    correct_answer=question.correct_answer,
                    is_correct=is_correct,
                    explanation=question.explanation
                ))
        
        # Rebuild descriptive results
        descriptive_results = []
        for ans in descriptive_answers:
            question = questions.get(ans['question_id'])
            if question:
                descriptive_results.append(DescriptiveResult(
                    question_id=question.id,
                    question=question.question_text,
                    your_answer=ans['answer'],
                    sample_answer=question.sample_answer,
                    key_points=json.loads(question.key_points) if question.key_points else [],
                    explanation=question.explanation
                ))
        
        return QuizAttemptDetail(
            attempt_id=attempt.id,
            quiz_id=quiz.id,
            quiz_topic=quiz.topic,
            user_id=attempt.user_id,
            user_name=attempt.user_name,
            mcq_score=attempt.mcq_score,
            blank_score=attempt.blank_score,
            total_score=attempt.total_score,
            max_score=attempt.max_score,
            percentage=attempt.percentage,
            time_taken_seconds=attempt.time_taken_seconds,
            submitted_at=attempt.submitted_at.isoformat(),
            mcq_results=mcq_results,
            blank_results=blank_results,
            descriptive_results=descriptive_results
        )
    
    def get_quiz_analytics(
        self,
        quiz_id: int,
        db: Session
    ) -> QuizAnalytics:
        """Get analytics for a specific quiz."""
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise ValueError("Quiz not found")
        
        attempts = db.query(QuizAttempt).filter(QuizAttempt.quiz_id == quiz_id).all()
        
        if not attempts:
            return QuizAnalytics(
                quiz_id=quiz.id,
                topic=quiz.topic,
                total_attempts=0,
                average_score=0.0,
                highest_score=0.0,
                lowest_score=0.0,
                average_time_seconds=None,
                completion_rate=0.0
            )
        
        percentages = [att.percentage for att in attempts]
        times = [att.time_taken_seconds for att in attempts if att.time_taken_seconds is not None]
        
        return QuizAnalytics(
            quiz_id=quiz.id,
            topic=quiz.topic,
            total_attempts=len(attempts),
            average_score=round(sum(percentages) / len(percentages), 2),
            highest_score=max(percentages),
            lowest_score=min(percentages),
            average_time_seconds=round(sum(times) / len(times), 2) if times else None,
            completion_rate=100.0  # All attempts in DB are completed
        )
    
    def get_user_attempts(
        self,
        user_id: str,
        skip: int,
        limit: int,
        db: Session
    ) -> List[QuizAttemptSummary]:
        """Get all attempts by a specific user."""
        attempts = db.query(QuizAttempt)\
            .filter(QuizAttempt.user_id == user_id)\
            .order_by(QuizAttempt.submitted_at.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()
        
        return [
            QuizAttemptSummary(
                attempt_id=att.id,
                quiz_id=att.quiz_id,
                user_id=att.user_id,
                user_name=att.user_name,
                mcq_score=att.mcq_score,
                blank_score=att.blank_score,
                total_score=att.total_score,
                max_score=att.max_score,
                percentage=att.percentage,
                time_taken_seconds=att.time_taken_seconds,
                submitted_at=att.submitted_at.isoformat()
            )
            for att in attempts
        ]
