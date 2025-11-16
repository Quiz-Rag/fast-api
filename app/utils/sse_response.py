"""
Server-Sent Events (SSE) utilities for streaming responses.
"""

import json
import asyncio
from typing import AsyncGenerator
import logging

logger = logging.getLogger(__name__)


def format_sse_message(data: dict) -> str:
    """
    Format a message for Server-Sent Events protocol.
    
    Args:
        data: Dictionary to send as SSE message
    
    Returns:
        Formatted SSE message string
    """
    return f"data: {json.dumps(data)}\n\n"


async def stream_tokens(
    token_generator: AsyncGenerator[str, None],
    session_id: str
) -> AsyncGenerator[str, None]:
    """
    Stream tokens as SSE messages.
    
    Args:
        token_generator: Async generator yielding tokens
        session_id: Chat session ID
    
    Yields:
        SSE formatted messages
    """
    try:
        total_tokens = 0
        
        # Stream each token
        async for token in token_generator:
            if token:
                total_tokens += 1
                yield format_sse_message({
                    "type": "token",
                    "content": token,
                    "session_id": session_id
                })
                
                # Small delay to prevent overwhelming client
                await asyncio.sleep(0.01)
        
        # Send completion message
        yield format_sse_message({
            "type": "done",
            "session_id": session_id,
            "tokens_used": total_tokens
        })
        
        logger.info(f"Streamed {total_tokens} tokens for session {session_id}")
        
    except Exception as e:
        logger.error(f"Error streaming tokens: {str(e)}")
        yield format_sse_message({
            "type": "error",
            "message": str(e),
            "session_id": session_id
        })


def create_error_sse(error_message: str, session_id: str = None) -> str:
    """
    Create an SSE error message.
    
    Args:
        error_message: Error description
        session_id: Optional session ID
    
    Returns:
        Formatted SSE error message
    """
    return format_sse_message({
        "type": "error",
        "message": error_message,
        "session_id": session_id
    })


def create_start_sse(session_id: str) -> str:
    """
    Create an SSE start message.
    
    Args:
        session_id: Chat session ID
    
    Returns:
        Formatted SSE start message
    """
    return format_sse_message({
        "type": "start",
        "session_id": session_id
    })


def create_debug_sse(
    session_id: str,
    retrieved_docs_count: int,
    context_length: int,
    context_preview: str,
    rsa_mentions: int = 0
) -> str:
    """
    Create an SSE debug message with context information.
    
    Args:
        session_id: Chat session ID
        retrieved_docs_count: Number of documents retrieved
        context_length: Total length of context
        context_preview: Preview of context (first 500 chars)
        rsa_mentions: Number of docs mentioning RSA
    
    Returns:
        Formatted SSE debug message
    """
    return format_sse_message({
        "type": "debug",
        "session_id": session_id,
        "retrieved_docs_count": retrieved_docs_count,
        "context_length": context_length,
        "context_preview": context_preview,
        "rsa_mentions": rsa_mentions
    })


def create_citation_sse(session_id: str, citations: list) -> str:
    """
    Create an SSE citation message.
    
    Args:
        session_id: Chat session ID
        citations: List of citation dictionaries
    
    Returns:
        Formatted SSE citation message
    """
    return format_sse_message({
        "type": "citation",
        "session_id": session_id,
        "citations": citations
    })


def create_message_sse(session_id: str, content: str, citations: list = None) -> str:
    """
    Create an SSE message with content and citations.
    
    Args:
        session_id: Chat session ID
        content: Message content
        citations: Optional list of citations
    
    Returns:
        Formatted SSE message
    """
    data = {
        "type": "message",
        "session_id": session_id,
        "content": content
    }
    if citations:
        data["citations"] = citations
    return format_sse_message(data)


def create_done_sse(session_id: str) -> str:
    """
    Create an SSE done message.
    
    Args:
        session_id: Chat session ID
    
    Returns:
        Formatted SSE done message
    """
    return format_sse_message({
        "type": "done",
        "session_id": session_id
    })
