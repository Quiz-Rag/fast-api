"""
Pydantic models for chat API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# ============= REQUEST MODELS =============

class ChatStartRequest(BaseModel):
    """Request to start a new chat session."""
    user_id: Optional[str] = Field(None, max_length=100)
    user_name: Optional[str] = Field(None, max_length=200)


class ChatMessageRequest(BaseModel):
    """Request to send a message in chat."""
    session_id: str = Field(..., min_length=36, max_length=36, description="UUID of the chat session")
    message: str = Field(..., min_length=1, max_length=500, description="User's question or message")


# ============= RESPONSE MODELS =============

class ChatStartResponse(BaseModel):
    """Response when starting a new chat session."""
    session_id: str
    greeting: str
    started_at: str


class ChatMessageResponse(BaseModel):
    """Individual message in chat history."""
    role: str  # "user" or "assistant"
    content: str
    created_at: str
    tokens_used: Optional[int] = None


class ChatHistoryResponse(BaseModel):
    """Response containing chat history."""
    session_id: str
    messages: List[ChatMessageResponse]
    message_count: int
    started_at: str
    last_message_at: str


class ChatSessionInfo(BaseModel):
    """Basic info about a chat session."""
    session_id: str
    user_id: Optional[str]
    user_name: Optional[str]
    message_count: int
    started_at: str
    last_message_at: str
    is_active: bool


# ============= SSE STREAM MODELS =============

class SSETokenMessage(BaseModel):
    """SSE message for streaming tokens."""
    type: str = "token"
    content: str


class SSEDoneMessage(BaseModel):
    """SSE message indicating stream completion."""
    type: str = "done"
    tokens_used: Optional[int] = None


class SSEErrorMessage(BaseModel):
    """SSE message for errors."""
    type: str = "error"
    message: str


class SSEDebugMessage(BaseModel):
    """SSE message with debug information."""
    type: str = "debug"
    retrieved_docs_count: int
    context_length: int
    context_preview: str
    rsa_mentions: int
