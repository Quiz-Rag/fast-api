"""
Custom LangChain memory integration with SQLite database.
Integrates LangChain's BaseChatMessageHistory with existing ChatMessage table.
"""

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from sqlalchemy.orm import Session
from app.models.database import ChatMessage, ChatRole
from typing import List
import logging

logger = logging.getLogger(__name__)


class SQLiteChatMessageHistory(BaseChatMessageHistory):
    """
    Custom LangChain chat message history that uses SQLite database.
    Integrates with existing ChatMessage table.
    """
    
    def __init__(self, session_id: str, db: Session):
        """
        Initialize SQLite chat message history.
        
        Args:
            session_id: Chat session ID (UUID)
            db: SQLAlchemy database session
        """
        self.session_id = session_id
        self.db = db
    
    @property
    def messages(self) -> List[BaseMessage]:
        """Load messages from database and convert to LangChain format."""
        try:
            # Get messages from database
            db_messages = self.db.query(ChatMessage).filter(
                ChatMessage.session_id == self.session_id,
                ChatMessage.role.in_([ChatRole.USER, ChatRole.ASSISTANT, ChatRole.SYSTEM])
            ).order_by(
                ChatMessage.created_at.asc()
            ).all()
            
            # Convert to LangChain messages
            langchain_messages = []
            for msg in db_messages:
                if msg.role == ChatRole.USER:
                    langchain_messages.append(HumanMessage(content=msg.content))
                elif msg.role == ChatRole.ASSISTANT:
                    langchain_messages.append(AIMessage(content=msg.content))
                elif msg.role == ChatRole.SYSTEM:
                    langchain_messages.append(SystemMessage(content=msg.content))
            
            return langchain_messages
        except Exception as e:
            logger.error(f"Error loading messages from database: {e}")
            return []
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the database."""
        try:
            # Determine role from message type
            if isinstance(message, HumanMessage):
                role = ChatRole.USER
            elif isinstance(message, AIMessage):
                role = ChatRole.ASSISTANT
            elif isinstance(message, SystemMessage):
                role = ChatRole.SYSTEM
            else:
                # Default to user
                role = ChatRole.USER
            
            # Create database message
            db_message = ChatMessage(
                session_id=self.session_id,
                role=role,
                content=message.content
            )
            
            self.db.add(db_message)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error adding message to database: {e}")
            self.db.rollback()
            raise
    
    def clear(self) -> None:
        """Clear all messages for this session."""
        try:
            self.db.query(ChatMessage).filter(
                ChatMessage.session_id == self.session_id
            ).delete()
            self.db.commit()
        except Exception as e:
            logger.error(f"Error clearing messages: {e}")
            self.db.rollback()
            raise

