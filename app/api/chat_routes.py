"""
API routes for chat/tutor functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.chat_service import ChatService
from app.services.tutor_service import TutorService
from app.security.input_sanitizer import sanitize_chat_message
from app.models.chat_schemas import *
from app.models.database import ChatRole
from app.utils.sse_response import stream_tokens, create_error_sse, create_start_sse, create_debug_sse
import logging

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/start", response_model=ChatStartResponse, status_code=status.HTTP_201_CREATED)
async def start_chat_session(
    request: ChatStartRequest,
    db: Session = Depends(get_db)
):
    """
    Start a new chat session with the tutor bot.
    
    Returns session ID and greeting message.
    """
    try:
        chat_service = ChatService()
        tutor_service = TutorService()
        
        # Create new session
        session = chat_service.create_session(
            db=db,
            user_id=request.user_id,
            user_name=request.user_name
        )
        
        # Get greeting
        greeting = tutor_service.get_greeting_message(request.user_name)
        
        # Save greeting as first message
        chat_service.add_message(
            db=db,
            session_id=session.session_id,
            role=ChatRole.ASSISTANT,
            content=greeting
        )
        
        return ChatStartResponse(
            session_id=session.session_id,
            greeting=greeting,
            started_at=session.started_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error starting chat session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start chat session: {str(e)}"
        )


@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    db: Session = Depends(get_db)
):
    """
    Send a message and receive streaming response via Server-Sent Events.
    
    Returns: StreamingResponse with text/event-stream content type
    """
    chat_service = ChatService()
    tutor_service = TutorService()
    
    # Validate session
    is_valid, error = chat_service.validate_session(db, request.session_id)
    if not is_valid:
        return StreamingResponse(
            iter([create_error_sse(error, request.session_id)]),
            media_type="text/event-stream"
        )
    
    # Sanitize input
    sanitized_message = sanitize_chat_message(request.message)
    
    if not sanitized_message or len(sanitized_message) < 3:
        return StreamingResponse(
            iter([create_error_sse(
                "Message is too short or contains only invalid characters",
                request.session_id
            )]),
            media_type="text/event-stream"
        )
    
    try:
        # Save user message
        chat_service.add_message(
            db=db,
            session_id=request.session_id,
            role=ChatRole.USER,
            content=sanitized_message
        )
        
        # Get chat history for context
        chat_history = chat_service.get_recent_context(
            db=db,
            session_id=request.session_id,
            limit=8  # Last 4 exchanges
        )
        
        # Retrieve relevant course content
        context = await tutor_service.retrieve_context(
            question=sanitized_message,
            chat_history=chat_history
        )
        
        # Calculate debug information
        context_length = len(context)
        context_preview = context[:500] if context else "[No context retrieved]"
        rsa_mentions = context.lower().count('rsa') + context.lower().count('rivest') if context else 0
        doc_count = context.count('---') + 1 if context else 0  # Rough estimate based on separator
        
        # Build system prompt
        system_prompt = tutor_service.build_system_prompt()
        
        # Build messages for LLM
        messages = chat_history.copy()
        
        # Add current question with context
        current_message = tutor_service.build_context_message(context, sanitized_message)
        messages.append({
            "role": "user",
            "content": current_message
        })
        
        # Stream response from AI
        async def generate_response():
            try:
                # Send start message
                yield create_start_sse(request.session_id)
                
                # Send debug message with context info
                yield create_debug_sse(
                    session_id=request.session_id,
                    retrieved_docs_count=doc_count,
                    context_length=context_length,
                    context_preview=context_preview,
                    rsa_mentions=rsa_mentions
                )
                
                # Collect full response for saving
                full_response = ""
                
                # Stream tokens
                token_generator = tutor_service.ai.stream_chat_response(
                    messages=messages,
                    system_prompt=system_prompt
                )
                
                async for sse_message in stream_tokens(token_generator, request.session_id):
                    yield sse_message
                    
                    # Parse to collect full response
                    import json
                    try:
                        data = json.loads(sse_message.split("data: ", 1)[1])
                        if data.get("type") == "token":
                            full_response += data.get("content", "")
                        elif data.get("type") == "done":
                            # Save assistant's response to database
                            chat_service.add_message(
                                db=db,
                                session_id=request.session_id,
                                role=ChatRole.ASSISTANT,
                                content=full_response.strip(),
                                tokens_used=data.get("tokens_used")
                            )
                    except:
                        pass
                        
            except Exception as e:
                logger.error(f"Error generating response: {str(e)}")
                yield create_error_sse(str(e), request.session_id)
        
        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
        
    except Exception as e:
        logger.error(f"Error in send_message: {str(e)}")
        return StreamingResponse(
            iter([create_error_sse(str(e), request.session_id)]),
            media_type="text/event-stream"
        )


@router.get("/{session_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get chat history for a session.
    
    Returns all messages in chronological order.
    """
    try:
        chat_service = ChatService()
        
        # Get session
        session = chat_service.get_session(db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        # Get messages
        messages = chat_service.get_chat_history(db, session_id)
        
        # Format response
        formatted_messages = [
            ChatMessageResponse(
                role=msg.role.value,
                content=msg.content,
                created_at=msg.created_at.isoformat(),
                tokens_used=msg.tokens_used
            )
            for msg in messages
        ]
        
        return ChatHistoryResponse(
            session_id=session.session_id,
            messages=formatted_messages,
            message_count=session.message_count,
            started_at=session.started_at.isoformat(),
            last_message_at=session.last_message_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_chat_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    End a chat session (mark as inactive).
    """
    try:
        chat_service = ChatService()
        
        success = chat_service.end_session(db, session_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending chat session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{session_id}/info", response_model=ChatSessionInfo)
async def get_session_info(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get basic information about a chat session.
    """
    try:
        chat_service = ChatService()
        
        session = chat_service.get_session(db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        return ChatSessionInfo(
            session_id=session.session_id,
            user_id=session.user_id,
            user_name=session.user_name,
            message_count=session.message_count,
            started_at=session.started_at.isoformat(),
            last_message_at=session.last_message_at.isoformat(),
            is_active=session.is_active
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
