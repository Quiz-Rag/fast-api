"""
RAG (Retrieval-Augmented Generation) service using LangChain 1.0+.
Uses LCEL (LangChain Expression Language) for modern RAG chains.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document
from typing import List, Dict, Any, Optional
from app.services.chroma_service import ChromaService
from app.services.ai_service import AIService
from app.services.langchain_memory import SQLiteChatMessageHistory
from app.services.prompts import PromptTemplates
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class RAGService:
    """Service for RAG operations using LangChain 1.0+ LCEL."""
    
    def __init__(self):
        """Initialize RAG service with ChromaDB and AI services."""
        self.chroma = ChromaService()
        self.ai = AIService()
    
    def _format_docs_with_citations(self, docs: List[Document]) -> str:
        """Format retrieved documents with human-readable citations. Uses 'Slide X' format."""
        formatted = []
        for doc in docs:
            metadata = doc.metadata
            slide_num = metadata.get("slide_number")
            # Fallback for backward compatibility
            if slide_num is None:
                slide_num = metadata.get("page_number")
            
            # Create human-readable label
            if slide_num is not None:
                label = f"Slide {slide_num}"
            else:
                source_file = metadata.get("source_file", "Unknown")
                label = source_file
            
            formatted.append(f"[{label}]:\n{doc.page_content}")
        
        return "\n\n".join(formatted)
    
    def create_rag_chain(
        self,
        retriever,
        prompt_template: ChatPromptTemplate
    ):
        """
        Create a RAG chain using LCEL (LangChain Expression Language).
        
        Args:
            retriever: LangChain retriever
            prompt_template: Chat prompt template
        
        Returns:
            Runnable chain
        """
        def format_docs(docs: List[Document]) -> str:
            """Format retrieved documents."""
            return self._format_docs_with_citations(docs)
        
        # Build RAG chain using LCEL
        rag_chain = (
            {
                "context": retriever | format_docs,
                "question": RunnablePassthrough()
            }
            | prompt_template
            | self.ai.llm
            | StrOutputParser()
        )
        
        return rag_chain
    
    def create_conversational_rag_chain(
        self,
        session_id: str,
        db: Session,
        collection_name: Optional[str] = None,
        k: int = 10
    ):
        """
        Create a conversational RAG chain with memory using LCEL.
        
        Args:
            session_id: Chat session ID
            db: Database session
            collection_name: ChromaDB collection name (None = all collections)
            k: Number of documents to retrieve
        
        Returns:
            Runnable chain for conversational RAG
        """
        # Get retriever
        retriever = self.chroma.get_langchain_retriever(
            collection_name=collection_name,
            search_kwargs={"k": k}
        )
        
        # Get memory
        memory = SQLiteChatMessageHistory(session_id=session_id, db=db)
        
        # Get prompt template
        prompt_template = PromptTemplates.get_tutor_context_prompt()
        
        # Format documents with citations
        def format_docs(docs: List[Document]) -> str:
            return self._format_docs_with_citations(docs)
        
        # Get chat history from memory
        def get_chat_history() -> str:
            """Extract chat history from memory for context."""
            messages = memory.messages
            if len(messages) <= 1:  # Only current question
                return ""
            
            # Get last few messages (excluding current)
            history_messages = messages[:-1]
            history_str = []
            for msg in history_messages[-4:]:  # Last 4 messages (2 exchanges)
                if isinstance(msg, HumanMessage):
                    history_str.append(f"Human: {msg.content}")
                elif isinstance(msg, AIMessage):
                    history_str.append(f"Assistant: {msg.content}")
            
            return "\n".join(history_str) if history_str else ""
        
        # Build conversational RAG chain using LCEL
        # Use RunnableLambda for proper LCEL composition
        def retrieve_and_format(question: str) -> Dict[str, Any]:
            """Retrieve documents and format with context."""
            docs = retriever.invoke(question)  # LangChain 1.0+ uses invoke instead of get_relevant_documents
            return {
                "context": format_docs(docs),
                "question": question,
                "chat_history": get_chat_history()
            }
        
        conversational_chain = (
            RunnableLambda(lambda x: retrieve_and_format(x["question"]))
            | prompt_template
            | self.ai.llm
            | StrOutputParser()
        )
        
        return conversational_chain
    
    async def retrieve_for_quiz(
        self,
        topic: str,
        collection_name: Optional[str] = None,
        k: int = 20
    ) -> str:
        """
        Retrieve documents for quiz generation using LangChain retriever.
        
        Args:
            topic: Topic to search for
            collection_name: ChromaDB collection name (None = all collections)
            k: Number of documents to retrieve
        
        Returns:
            Combined content from retrieved documents
        """
        try:
            # Get retriever
            retriever = self.chroma.get_langchain_retriever(
                collection_name=collection_name,
                search_kwargs={"k": k}
            )
            
            # Retrieve documents (LangChain 1.0+ uses invoke instead of get_relevant_documents)
            docs = retriever.invoke(topic)
            
            # Combine documents
            content = "\n\n".join([doc.page_content for doc in docs])
            
            # Limit to 3000 words
            words = content.split()
            if len(words) > 3000:
                content = " ".join(words[:3000])
                logger.info(f"Content truncated to 3000 words for quiz generation")
            
            logger.info(f"Retrieved {len(docs)} documents for quiz generation")
            return content
            
        except Exception as e:
            logger.error(f"Error retrieving documents for quiz: {e}")
            raise
    
    async def chat_with_rag(
        self,
        question: str,
        session_id: str,
        db: Session,
        collection_name: Optional[str] = None,
        k: int = 10
    ) -> Dict[str, Any]:
        """
        Chat with RAG using LangChain conversational RAG chain (LCEL).
        
        Args:
            question: User question
            session_id: Chat session ID
            db: Database session
            collection_name: ChromaDB collection name
            k: Number of documents to retrieve
        
        Returns:
            Dictionary with answer, source_documents, and citations
        """
        try:
            # Get retriever for source documents
            retriever = self.chroma.get_langchain_retriever(
                collection_name=collection_name,
                search_kwargs={"k": k}
            )
            
            # Retrieve documents for citations (LangChain 1.0+ uses invoke instead of get_relevant_documents)
            source_docs = retriever.invoke(question)
            
            # Create chain
            chain = self.create_conversational_rag_chain(
                session_id=session_id,
                db=db,
                collection_name=collection_name,
                k=k
            )
            
            # Invoke chain
            answer = await chain.ainvoke({"question": question})
            
            # Extract citations from source documents
            citations = []
            seen_citations = set()
            for doc in source_docs:
                metadata = doc.metadata
                source_file = metadata.get("source_file", "Unknown")
                doc_type = metadata.get("document_type", "unknown")
                slide_num = metadata.get("slide_number")
                # Fallback for backward compatibility
                if slide_num is None:
                    slide_num = metadata.get("page_number")
                
                # Create unique key for deduplication (use slide_number only)
                citation_key = (source_file, slide_num)
                if citation_key in seen_citations:
                    continue
                seen_citations.add(citation_key)
                
                citation = {
                    "source_file": source_file,
                    "document_type": doc_type,
                    "slide_number": slide_num,
                    "collection": metadata.get("collection_name", "Unknown")
                }
                citations.append(citation)
            
            return {
                "answer": answer,
                "source_documents": source_docs,
                "citations": citations
            }
            
        except Exception as e:
            logger.error(f"Error in chat_with_rag: {e}")
            raise
    
    def get_retriever(
        self,
        collection_name: Optional[str] = None,
        k: int = 10
    ):
        """
        Get a LangChain retriever for direct use.
        
        Args:
            collection_name: ChromaDB collection name
            k: Number of documents to retrieve
        
        Returns:
            LangChain retriever instance
        """
        return self.chroma.get_langchain_retriever(
            collection_name=collection_name,
            search_kwargs={"k": k}
        )

