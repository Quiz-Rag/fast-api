"""
Chat service for managing conversation sessions and history.
"""

from sqlalchemy.orm import Session
from app.models.database import ChatSession, ChatMessage, ChatRole
from app.models.chat_schemas import *
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing chat sessions and messages."""
    
    def create_session(
        self,
        db: Session,
        user_id: str = None,
        user_name: str = None
    ) -> ChatSession:
        """
        Create a new chat session.
        
        Args:
            db: Database session
            user_id: Optional user identifier
            user_name: Optional user name
        
        Returns:
            Created ChatSession
        """
        session_id = str(uuid.uuid4())
        
        session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            user_name=user_name,
            started_at=datetime.utcnow(),
            last_message_at=datetime.utcnow(),
            message_count=0,
            is_active=True
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        logger.info(f"Created chat session: {session_id}")
        return session
    
    def get_session(self, db: Session, session_id: str) -> ChatSession:
        """
        Get chat session by ID.
        
        Args:
            db: Database session
            session_id: UUID of the session
        
        Returns:
            ChatSession or None
        """
        return db.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()
    
    def add_message(
        self,
        db: Session,
        session_id: str,
        role: ChatRole,
        content: str,
        tokens_used: int = None
    ) -> ChatMessage:
        """
        Add a message to a chat session.
        
        Args:
            db: Database session
            session_id: UUID of the session
            role: Message role (USER or ASSISTANT)
            content: Message content
            tokens_used: Optional token count
        
        Returns:
            Created ChatMessage
        """
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            tokens_used=tokens_used,
            created_at=datetime.utcnow()
        )
        
        db.add(message)
        
        # Update session
        session = self.get_session(db, session_id)
        if session:
            session.message_count += 1
            session.last_message_at = datetime.utcnow()
        
        db.commit()
        db.refresh(message)
        
        return message
    
    def get_chat_history(
        self,
        db: Session,
        session_id: str,
        limit: int = 50
    ) -> list[ChatMessage]:
        """
        Get chat history for a session.
        
        Args:
            db: Database session
            session_id: UUID of the session
            limit: Maximum number of messages to return
        
        Returns:
            List of ChatMessage objects
        """
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(
            ChatMessage.created_at.asc()
        ).limit(limit).all()
        
        return messages
    
    def end_session(self, db: Session, session_id: str) -> bool:
        """
        Mark a session as inactive.
        
        Args:
            db: Database session
            session_id: UUID of the session
        
        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(db, session_id)
        if session:
            session.is_active = False
            db.commit()
            logger.info(f"Ended chat session: {session_id}")
            return True
        return False
    
    def validate_session(self, db: Session, session_id: str) -> tuple[bool, str]:
        """
        Validate if a session exists and is active.
        
        Args:
            db: Database session
            session_id: UUID of the session
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        session = self.get_session(db, session_id)
        
        if not session:
            return False, f"Session {session_id} not found"
        
        if not session.is_active:
            return False, "Session is no longer active"
        
        # Rate limit: max 50 messages per session
        if session.message_count >= 50:
            return False, "Session message limit reached (50 messages)"
        
        return True, ""
    
    def get_recent_context(
        self,
        db: Session,
        session_id: str,
        limit: int = 10
    ) -> list[dict]:
        """
        Get recent messages for context (formatted for LLM).
        
        Args:
            db: Database session
            session_id: UUID of the session
            limit: Number of recent messages
        
        Returns:
            List of formatted messages
        """
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id,
            ChatMessage.role.in_([ChatRole.USER, ChatRole.ASSISTANT])
        ).order_by(
            ChatMessage.created_at.desc()
        ).limit(limit).all()
        
        # Reverse to chronological order
        messages = list(reversed(messages))
        
        # Format for LLM
        formatted = []
        for msg in messages:
            formatted.append({
                "role": msg.role.value,
                "content": msg.content
            })
        
        return formatted
