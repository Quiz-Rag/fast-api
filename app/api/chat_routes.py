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
from app.utils.sse_response import stream_tokens, create_error_sse, create_start_sse, create_debug_sse, create_citation_sse, create_message_sse, create_done_sse
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
        logger.info("=" * 60)
        logger.info("**** CHAT SESSION INITIATED ****")
        logger.info(f"User ID: {request.user_id}")
        logger.info(f"User Name: {request.user_name}")
        logger.info("=" * 60)
        
        chat_service = ChatService()
        tutor_service = TutorService()
        
        # Create new session
        session = chat_service.create_session(
            db=db,
            user_id=request.user_id,
            user_name=request.user_name
        )
        
        logger.info(f"Session created: {session.session_id}")
        
        # Get greeting
        greeting = tutor_service.get_greeting_message(request.user_name)
        
        # Save greeting as first message
        chat_service.add_message(
            db=db,
            session_id=session.session_id,
            role=ChatRole.ASSISTANT,
            content=greeting
        )
        
        logger.info(f"Greeting message saved to session {session.session_id}")
        logger.info("=" * 60)
        
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
        logger.info("=" * 60)
        logger.info("**** RECEIVED QUESTION ****")
        logger.info(f"Session ID: {request.session_id}")
        logger.info(f"Question: {sanitized_message}")
        logger.info("=" * 60)
        
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
        
        logger.info(f"Chat history loaded: {len(chat_history)} messages")
        
        # Retrieve relevant course content with citations
        context_result = await tutor_service.retrieve_context(
            question=sanitized_message,
            chat_history=chat_history
        )
        
        context = context_result.get("content", "")
        all_citations = context_result.get("citations", [])
        chunk_mapping = context_result.get("chunk_mapping", {})
        chunk_key_mapping = context_result.get("chunk_key_mapping", {})
        human_readable_mapping = context_result.get("human_readable_mapping", {})
        chunk_citations = context_result.get("chunk_citations", [])
        is_web_search = context_result.get("is_web_search", False)
        
        # Evaluate context sufficiency if we have ChromaDB context (not web search)
        evaluation_code = 2  # Default to sufficient
        if context and not is_web_search:
            logger.info("Evaluating context sufficiency...")
            evaluation_code = await tutor_service._check_context_sufficiency(sanitized_message, context)
            logger.info(f"Context evaluation code: {evaluation_code}")
        
        # Handle evaluation codes
        if evaluation_code == 0:
            # Question is not network security related
            logger.info("Question is not network security related (code=0)")
            async def generate_response():
                yield create_start_sse(request.session_id)
                yield create_message_sse(
                    session_id=request.session_id,
                    content="I'm here to help with Network Security topics only! Do you have any questions about encryption, web security, or network protocols?",
                    citations=[]
                )
                yield create_done_sse(request.session_id)
            return StreamingResponse(generate_response(), media_type="text/event-stream")
        
        # If code is 1 (NS related but context insufficient), trigger web search
        if evaluation_code == 1 and not is_web_search:
            logger.info("Context insufficient (code=1), performing web search...")
            web_results = tutor_service.web_search.search_web(sanitized_message, max_results=3)
            
            if web_results.get("content") and web_results.get("citations"):
                logger.info(f"Web search found {len(web_results['citations'])} results")
                # Replace context with web search results
                context = web_results["content"]
                # Format web citations
                all_citations = tutor_service.format_citations(web_results["citations"])
                is_web_search = True
                # Clear ChromaDB mappings since we're using web search
                chunk_mapping = {}
                chunk_key_mapping = {}
                human_readable_mapping = {}
                chunk_citations = []
        
        # Initially show all citations (will be filtered after LLM response)
        citations = all_citations
        
        # Calculate debug information
        context_length = len(context)
        context_preview = context[:500] if context else "[No context retrieved]"
        rsa_mentions = context.lower().count('rsa') + context.lower().count('rivest') if context else 0
        doc_count = len(citations) if citations else (context.count('---') + 1 if context else 0)
        
        # Build system prompt
        system_prompt = tutor_service.build_system_prompt()
        
        # Build messages for LLM
        messages = chat_history.copy()
        
        # Add current question with context
        current_message = tutor_service.build_context_message(
            context=context, 
            question=sanitized_message,
            chat_history=chat_history
        )
        messages.append({
            "role": "user",
            "content": current_message
        })
        
        logger.info(f"Built context message (length: {len(current_message)} chars)")
        logger.info(f"Total messages for LLM: {len(messages)}")
        
        # Stream response from AI
        async def generate_response():
            try:
                # Initialize citations (will be filtered later if LLM mentions chunks)
                current_citations = citations
                
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
                
                # Don't send citations yet - wait until we know which chunks LLM used
                # Citations will be sent after LLM response is complete
                
                # Collect full response for saving and parsing
                full_response = ""
                
                logger.info("=" * 60)
                logger.info(f"**** PASSED TO LLM (Model: {tutor_service.ai.model}) ****")
                logger.info(f"System prompt length: {len(system_prompt)} chars")
                logger.info(f"Messages count: {len(messages)}")
                logger.info("=" * 60)
                
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
                            # For web search results, use all citations (no extraction needed)
                            if is_web_search:
                                current_citations = all_citations
                                logger.info(f"✅ Web search citations, showing {len(current_citations)} citations")
                            else:
                                # Parse LLM response to find which citations were mentioned
                                # Try human-readable format first (primary method)
                                extracted_citations = tutor_service.extract_human_readable_citations(
                                    full_response,
                                    human_readable_mapping
                                )
                                
                                # Fallback to chunk key parsing if human-readable didn't find anything
                                if not extracted_citations:
                                    extracted_citations = tutor_service.extract_chunk_keys_from_response(
                                        full_response, 
                                        chunk_key_mapping,
                                        chunk_citations,
                                        chunk_mapping
                                    )
                                
                                if extracted_citations:
                                    current_citations = extracted_citations
                                    logger.info(f"✅ LLM mentioned citations, showing {len(current_citations)} citations")
                                else:
                                    # Final fallback: use top 1-2 citations
                                    current_citations = all_citations[:2] if len(all_citations) > 2 else all_citations
                                    logger.warning(f"⚠️ No citations found, using top {len(current_citations)} citations as fallback")
                            
                            # Format citations for frontend
                            if current_citations:
                                citation_list = []
                                for cit in current_citations:
                                    # Handle web citations (have URL)
                                    if cit.get("url"):
                                        citation_list.append({
                                            "source": cit.get("source", "Unknown"),
                                            "url": cit.get("url", ""),
                                            "formatted": cit.get("formatted", f"[{cit.get('source', 'Unknown')}]({cit.get('url', '')})")
                                        })
                                    else:
                                        # Handle ChromaDB citations
                                        citation_list.append({
                                            "source_file": cit.get("source_file", "Unknown"),
                                            "document_type": cit.get("document_type", "unknown"),
                                            "page_number": cit.get("page_number"),
                                            "slide_number": cit.get("slide_number"),
                                            "formatted": cit.get("formatted", cit.get("source_file", "Unknown"))
                                        })
                                yield create_citation_sse(request.session_id, citation_list)
                                logger.info(f"Sent {len(citation_list)} filtered citations to frontend")
                            
                            # Save assistant's response to database
                            chat_service.add_message(
                                db=db,
                                session_id=request.session_id,
                                role=ChatRole.ASSISTANT,
                                content=full_response.strip(),
                                tokens_used=data.get("tokens_used")
                            )
                            
                            logger.info("=" * 60)
                            logger.info("**** LLM RESPONDED ****")
                            logger.info(f"Response length: {len(full_response)} chars")
                            logger.info(f"Response preview: {full_response[:200]}...")
                            logger.info("=" * 60)
                            
                            logger.info("=" * 60)
                            logger.info("**** QUESTION ANSWER ****")
                            logger.info(f"Question: {sanitized_message}")
                            logger.info(f"Answer: {full_response.strip()}")
                            logger.info("=" * 60)
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
