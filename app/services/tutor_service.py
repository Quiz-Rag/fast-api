"""
Tutor service for generating educational responses with personality.
"""

from app.services.ai_service import AIService
from app.services.chroma_service import ChromaService
from app.services.rag_service import RAGService
from app.services.prompts import PromptTemplates
from app.services.web_search_service import WebSearchService
from app.models.langchain_schemas import ContextEvaluationOutput
from app.config import settings
from typing import Dict, List, Optional
import logging
import json
import os
from datetime import datetime
from langchain_core.output_parsers import PydanticOutputParser

logger = logging.getLogger(__name__)


class TutorService:
    """Service for tutor bot personality and response generation."""
    
    def __init__(self):
        """Initialize AI, ChromaDB, RAG, and web search services."""
        self.ai = AIService()
        self.chroma = ChromaService()
        self.rag = RAGService()
        self.web_search = WebSearchService()
    
    def _normalize_filename(self, filename: str) -> str:
        """
        Normalize filename for chunk key creation.
        Removes timestamp prefix, file extension, and normalizes for consistent keys.
        
        Args:
            filename: Original filename (e.g., "1763044518.227065_Lecture 14_slides.pdf")
        
        Returns:
            Normalized filename (e.g., "Lecture 14_slides")
        """
        import re
        if not filename:
            return "Unknown"
        
        # Remove timestamp prefix (digits.digits_)
        normalized = re.sub(r'^\d+\.\d+_', '', filename)
        
        # Remove file extension
        normalized = normalized.replace('.pdf', '').replace('.pptx', '').replace('.pptx', '')
        
        # Strip any remaining whitespace
        normalized = normalized.strip()
        
        return normalized if normalized else "Unknown"
    
    def _format_human_readable_chunk_label(self, citation: Dict) -> str:
        """
        Format citation as human-readable chunk label.
        Returns simple "Slide X" format where X is the lecture number.
        
        Args:
            citation: Citation dict with source_file, slide_number
            
        Returns:
            Formatted string like "Slide 1" or "Slide 19"
        """
        slide_num = citation.get('slide_number')
        
        # Fallback: try to extract from page_number for backward compatibility
        if slide_num is None:
            slide_num = citation.get('page_number')
        
        # Fallback: try to extract from filename
        if slide_num is None:
            source_file = citation.get('source_file', '')
            import re
            lecture_match = re.search(r'Lecture\s+(\d+)', source_file, re.IGNORECASE)
            if lecture_match:
                slide_num = int(lecture_match.group(1))
        
        if slide_num is not None:
            return f"Slide {slide_num}"
        else:
            return "Slide Unknown"
    
    def get_greeting_message(self, user_name: str = None) -> str:
        """
        Get personalized greeting for new chat session.
        
        Args:
            user_name: Optional user name for personalization
        
        Returns:
            Greeting message
        """
        if user_name:
            return f"""Hey {user_name}! 👋 So glad you're here!

I'm your friendly Network Security tutor, and I'm here to help you learn! 

Ask me anything about:
• Encryption & Cryptography 🔐
• Web Security (SQL injection, XSS, CSRF) 🌐
• Network Protocols & Firewalls 🛡️
• Authentication & Authorization 🔑
• Secure Coding & Best Practices ✨

I'll give you clear, concise answers based on your course materials. Let's learn together! What's on your mind? 😊"""
        else:
            return """Hey there! 👋 So glad you're here!

I'm your friendly Network Security tutor, and I'm here to help you learn! 

Ask me anything about:
• Encryption & Cryptography 🔐
• Web Security (SQL injection, XSS, CSRF) 🌐
• Network Protocols & Firewalls 🛡️
• Authentication & Authorization 🔑
• Secure Coding & Best Practices ✨

I'll give you clear, concise answers based on your course materials. Let's learn together! What's on your mind? 😊"""
    
    def build_system_prompt(self) -> str:
        """
        Build hardened system prompt with tutor personality and security boundaries.
        
        Returns:
            System prompt string
        """
        return PromptTemplates.get_tutor_system_prompt()
    
    def format_citations(self, citations: List[Dict]) -> List[Dict]:
        """
        Format citations for human-readable display.
        Handles both ChromaDB citations (Slide X) and web citations (Website Name with URL).
        
        Args:
            citations: List of citation dictionaries from extract_citations() or web search
        
        Returns:
            List of citations with formatted string
        """
        formatted = []
        for citation in citations:
            # Check if this is a web citation (has URL)
            if citation.get("url"):
                # Web citation format: [Website Name](URL)
                source = citation.get("source", "Unknown Source")
                url = citation.get("url", "")
                formatted_str = f"[{source}]({url})"
                citation["formatted"] = formatted_str
                formatted.append(citation)
            else:
                # ChromaDB citation format: Slide X
                slide_num = citation.get("slide_number")
                
                # Fallback: try page_number for backward compatibility
                if slide_num is None:
                    slide_num = citation.get("page_number")
                
                # Fallback: try to extract from filename
                if slide_num is None:
                    source_file = citation.get("source_file", "")
                    import re
                    lecture_match = re.search(r'Lecture\s+(\d+)', source_file, re.IGNORECASE)
                    if lecture_match:
                        slide_num = int(lecture_match.group(1))
                
                if slide_num is not None:
                    formatted_str = f"Slide {slide_num}"
                else:
                    formatted_str = "Slide Unknown"
                
                citation["formatted"] = formatted_str
                formatted.append(citation)
        
        return formatted
    
    async def retrieve_context(self, question: str, chat_history: list = None) -> Dict:
        """
        Retrieve relevant course content from ChromaDB with citations.
        Uses chat history to enrich search query for follow-up questions.
        
        Args:
            question: Current user question
            chat_history: Previous messages for context
        
        Returns:
            Dictionary with 'content' (str) and 'citations' (List[Dict])
        """
        try:
            # Extract key technical terms for better search
            import re
            
            # Common security terms that should be searched directly
            technical_terms = ['RSA', 'AES', 'DES', 'SHA', 'MD5', 'SSL', 'TLS', 'HTTPS', 'XSS', 'CSRF', 'SQL', 
                             'firewall', 'encryption', 'hash', 'cipher', 'authentication', 'authorization']
            
            # Check if question contains key technical terms
            question_upper = question.upper()
            found_terms = [term for term in technical_terms if term.upper() in question_upper]
            
            # Clean the query
            clean_question = re.sub(r'[^\w\s]', ' ', question)
            clean_question = ' '.join(clean_question.split())  # Normalize whitespace
            
            # Build optimized search query
            if found_terms:
                # Prioritize technical terms in search
                search_query = ' '.join(found_terms) + ' ' + clean_question
                logger.info(f"🎯 Key terms detected: {found_terms}")
            else:
                search_query = clean_question
            
            # For follow-up questions, enrich with recent context
            if chat_history and len(chat_history) > 0:
                # Get last 2 user messages for context
                recent_context = []
                for msg in reversed(chat_history[-4:]):  # Last 4 messages (2 pairs)
                    if msg["role"] == "user":
                        recent_context.append(msg["content"])
                
                if recent_context:
                    # Combine recent questions for better search
                    search_query = search_query + " " + " ".join(recent_context[:2])
            
            logger.info(f"Searching for: '{question}' → query: '{search_query[:150]}...')")
            
            # Use LangChain retriever to get documents
            retriever = self.rag.get_retriever(
                collection_name=None,  # Search all collections
                k=3  # Top 3 chunks for focused retrieval
            )
            
            logger.info("=" * 60)
            logger.info("**** FETCHING RELEVANT DOCS ****")
            logger.info(f"Using embedding model: text-embedding-3-small (OpenAI)")
            logger.info(f"Retriever config: k=3, collection_name=None (all collections)")
            logger.info("=" * 60)
            
            # Retrieve documents using LangChain (LangChain 1.0+ uses invoke/ainvoke)
            retrieved_docs = retriever.invoke(search_query)
            
            if not retrieved_docs:
                logger.warning(f"No documents found for: '{question}'")
                logger.info("=" * 60)
                logger.info("**** NO DOCUMENTS RETRIEVED FROM CHROMADB ****")
                logger.info("=" * 60)
                
                # Check if question is network security related and trigger web search
                if self.web_search.is_network_security_related(question):
                    logger.info("Question is network security related, performing web search...")
                    web_results = self.web_search.search_web(question, max_results=3)
                    
                    if web_results.get("content") and web_results.get("citations"):
                        logger.info(f"Web search found {len(web_results['citations'])} results")
                        # Format web citations
                        formatted_web_citations = self.format_citations(web_results["citations"])
                        return {
                            "content": web_results["content"],
                            "citations": formatted_web_citations,
                            "chunk_mapping": {},
                            "chunk_key_mapping": {},
                            "human_readable_mapping": {},
                            "chunk_citations": [],
                            "is_web_search": True
                        }
                    else:
                        logger.warning("Web search returned no results")
                
                return {"content": "", "citations": [], "chunk_mapping": {}, "chunk_key_mapping": {}, "human_readable_mapping": {}, "chunk_citations": []}
            
            # Extract documents, metadatas, and distances from LangChain documents
            documents = [doc.page_content for doc in retrieved_docs]
            metadatas = [doc.metadata for doc in retrieved_docs]
            # LangChain doesn't provide distances directly, so we'll use None
            distances = [None] * len(retrieved_docs)
            
            logger.info(f"Retrieved {len(documents)} documents for context using LangChain")
            logger.info("=" * 60)
            logger.info(f"**** FETCHED {len(documents)} RELEVANT DOCS USING text-embedding-3-small MODEL ****")
            
            # Log each document
            for i, (doc, meta) in enumerate(zip(documents, metadatas), start=1):
                source_file = meta.get("source_file", "Unknown") if meta else "Unknown"
                doc_type = meta.get("document_type", "unknown") if meta else "unknown"
                slide_num = meta.get("slide_number") if meta else None
                # Fallback for backward compatibility
                if slide_num is None:
                    slide_num = meta.get("page_number") if meta else None
                doc_length = len(doc)
                
                if slide_num is not None:
                    logger.info(f"Doc {i}: {source_file} (Slide {slide_num}) - {doc_length} chars")
                else:
                    logger.info(f"Doc {i}: {source_file} ({doc_type}) - {doc_length} chars")
            
            logger.info("=" * 60)
            
            # Extract citations from metadata
            all_citations = self.chroma.extract_citations(metadatas)
            formatted_citations = self.format_citations(all_citations)
            
            # Create chunk-to-citation mapping
            # Each chunk gets a number and its citation info
            chunk_citations = []
            chunk_mapping = {}  # Maps chunk number to citation
            chunk_key_mapping = {}  # Maps chunk key (filename_slide_number) to citation
            human_readable_mapping = {}  # Maps human-readable label to citation
            
            for i, (doc, meta) in enumerate(zip(documents, metadatas), start=1):
                # Get citation for this chunk
                if meta:
                    citation_list = self.chroma.extract_citations([meta])
                    if citation_list:
                        citation = citation_list[0]
                        formatted_cit = self.format_citations([citation])[0] if citation else None
                    else:
                        formatted_cit = None
                else:
                    formatted_cit = None
                
                if formatted_cit:
                    chunk_citations.append({
                        "chunk_number": i,
                        "citation": formatted_cit,
                        "distance": distances[i-1] if distances and i-1 < len(distances) else None
                    })
                    # Store the full citation dict (not just formatted string) for later matching
                    chunk_mapping[i] = citation  # Store original citation dict, not formatted string
                    
                    # Create human-readable label
                    human_readable_label = self._format_human_readable_chunk_label(citation)
                    human_readable_mapping[human_readable_label] = citation
                    
                    # Create chunk key: filename_slide_number
                    source_file = citation.get('source_file', 'Unknown')
                    normalized_filename = self._normalize_filename(source_file)
                    slide_num = citation.get('slide_number')
                    # Fallback for backward compatibility
                    if slide_num is None:
                        slide_num = citation.get('page_number')
                    
                    if slide_num is not None:
                        chunk_key = f"{normalized_filename}_{slide_num}"
                    else:
                        chunk_key = f"{normalized_filename}_{i}"  # Fallback to chunk number
                    
                    # Store mapping from chunk key to citation
                    chunk_key_mapping[chunk_key] = citation
            
            # Build context with human-readable labels: [Slide 1]: content
            numbered_chunks = []
            for i, (doc, meta) in enumerate(zip(documents, metadatas), start=1):
                citation = chunk_mapping.get(i)
                if citation:
                    # Create human-readable label
                    human_readable_label = self._format_human_readable_chunk_label(citation)
                    
                    # Format as: [Lecture 1, Slide 5]: content
                    numbered_chunks.append(f"[{human_readable_label}]:\n{doc}")
                else:
                    # Fallback if no citation
                    numbered_chunks.append(f"[Unknown]:\n{doc}")
            
            content = "\n\n".join(numbered_chunks)
            
            # Limit to 2000 words for chat context
            words = content.split()
            if len(words) > 2000:
                content = " ".join(words[:2000])
            
            # Save retrieved embeddings to JSON for debugging
            try:
                json_dir = "./json"
                os.makedirs(json_dir, exist_ok=True)
                
                # Create filename with question first, then timestamp
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
                # Sanitize question for filename (remove special chars, limit length)
                safe_question = "".join(c for c in question[:100] if c.isalnum() or c in (' ', '-', '_', '?')).strip()
                safe_question = safe_question.replace(' ', '_').replace('?', '')
                # Limit to 80 chars to avoid very long filenames
                safe_question = safe_question[:80]
                filename = f"{safe_question}_{timestamp}.json"
                filepath = os.path.join(json_dir, filename)
                
                # Prepare data to save
                saved_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "question": question,
                    "search_query": search_query,
                    "retrieved_documents_count": len(retrieved_docs),
                    "documents": []
                }
                
                # Add each retrieved document with full details
                for i, (doc, meta) in enumerate(zip(documents, metadatas), start=1):
                    doc_data = {
                        "chunk_number": i,
                        "content": doc,
                        "content_length": len(doc),
                        "metadata": meta if meta else {},
                        "citation": chunk_mapping.get(i, {}),
                        "human_readable_label": self._format_human_readable_chunk_label(chunk_mapping.get(i, {})) if chunk_mapping.get(i) else "Unknown"
                    }
                    saved_data["documents"].append(doc_data)
                
                # Add context information
                saved_data["context"] = {
                    "formatted_content": content,
                    "content_length": len(content),
                    "word_count": len(words),
                    "truncated": len(words) > 2000
                }
                
                # Add citations info
                saved_data["citations"] = {
                    "total_count": len(formatted_citations),
                    "all_citations": formatted_citations,
                    "chunk_citations": chunk_citations
                }
                
                # Save to JSON file
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(saved_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Saved retrieved embeddings to: {filepath}")
                
            except Exception as e:
                logger.error(f"Failed to save embeddings to JSON: {str(e)}")
            
            return {
                "content": content,
                "citations": formatted_citations,  # All citations (for fallback)
                "chunk_mapping": chunk_mapping,  # Map chunk number to citation (backward compatibility)
                "chunk_key_mapping": chunk_key_mapping,  # Map chunk key (filename_slide_number) to citation
                "human_readable_mapping": human_readable_mapping,  # Map human-readable label to citation
                "chunk_citations": chunk_citations  # List with chunk numbers and citations (for fallback)
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve context: {str(e)}")
            return {"content": "", "citations": [], "chunk_mapping": {}, "chunk_key_mapping": {}, "human_readable_mapping": {}, "chunk_citations": []}
    
    async def _check_context_sufficiency(self, question: str, context: str) -> int:
        """
        Evaluate if question is network security related and if context is sufficient.
        Uses structured LLM output to determine evaluation code.
        
        Args:
            question: User's question
            context: Retrieved context from ChromaDB
            
        Returns:
            Evaluation code: 0 (not NS related), 1 (NS related but context insufficient), 2 (NS related and context sufficient)
        """
        try:
            from langchain_groq import ChatGroq
            from langchain_core.output_parsers import PydanticOutputParser
            
            if not settings.groq_api_key:
                logger.warning("Groq API key not configured, skipping context evaluation")
                return 2  # Default to sufficient if can't evaluate
            
            # Create parser for structured output
            parser = PydanticOutputParser(pydantic_object=ContextEvaluationOutput)
            
            # Get evaluation prompt template
            prompt_template = PromptTemplates.get_context_evaluation_prompt()
            
            # Create LLM
            llm = ChatGroq(
                model_name=settings.groq_model,
                groq_api_key=settings.groq_api_key,
                temperature=0.1
            )
            
            # Create chain with structured output
            chain = prompt_template | llm | parser
            result = chain.invoke({
                "question": question,
                "context": context if context else "[No context provided]"
            })
            
            logger.info(f"Context evaluation: code={result.code}, reason={result.reason}")
            return result.code
            
        except Exception as e:
            logger.error(f"Error evaluating context sufficiency: {e}")
            # Default to code 2 (sufficient) if evaluation fails to avoid unnecessary web searches
            return 2
    
    def format_chat_history(self, messages: list) -> list:
        """
        Format chat history for LLM context.
        Keep last 10 messages to maintain conversation context.
        
        Args:
            messages: List of chat messages from database
        
        Returns:
            Formatted messages for LLM
        """
        # Get last 10 messages
        recent_messages = messages[-10:] if len(messages) > 10 else messages
        
        # Format for LLM
        formatted = []
        for msg in recent_messages:
            formatted.append({
                "role": msg.role.value if hasattr(msg.role, 'value') else msg.role,
                "content": msg.content
            })
        
        return formatted
    
    def build_context_message(self, context: str, question: str, chat_history: list = None) -> str:
        """
        Build the user message with context and question.
        Context should already have human-readable chunk labels.
        
        Args:
            context: Retrieved course materials with human-readable labels
            question: User's question
            chat_history: Previous chat messages for context
        
        Returns:
            Formatted message string
        """
        # Format chat history for prompt
        chat_history_str = ""
        if chat_history and len(chat_history) > 0:
            # Format last few messages for context
            history_parts = []
            for msg in chat_history[-4:]:  # Last 4 messages (2 exchanges)
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    history_parts.append(f"Previous question: {content}")
                elif role == "assistant":
                    history_parts.append(f"Previous answer: {content}")
            chat_history_str = "\n".join(history_parts) if history_parts else ""
        
        # Use prompt template
        template = PromptTemplates.get_tutor_context_prompt()
        return template.format(
            context=context, 
            question=question,
            chat_history=chat_history_str
        ) if context else f"""STUDENT QUESTION:
{question}

IMPORTANT: No course materials were found for this question.

You MUST respond with: "I don't have that information in your course materials. Please check with your instructor or upload relevant documents about this topic."

DO NOT provide general knowledge answers. ONLY use course materials."""
    
    def extract_citations_from_response(self, llm_response: str, chunk_mapping: Dict[int, Dict]) -> List[Dict]:
        """
        Extract citations mentioned in LLM response by parsing slide references.
        
        Looks for patterns like:
        - "[Slide 5]"
        - "[Slide 2]"
        - "[Slide 5] and [Slide 13]"
        
        Args:
            llm_response: Full LLM response text
            chunk_mapping: Dictionary mapping chunk number to citation
        
        Returns:
            List of citation dictionaries that were mentioned
        """
        import re
        
        found_citations = []
        seen_citations = set()
        
        # Pattern to match citations in response
        # Matches: "Slide X" format (simple format)
        # Also handles variations like "Slide X" in brackets [Slide X]
        patterns = [
            r'\[Slide\s+(\d+)\]',  # [Slide 5] or [Slide 19]
            r'(?:^|\s)Slide\s+(\d+)(?:\s|$|,|\.)',  # Slide 5 or Slide 19 (standalone)
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, llm_response, re.IGNORECASE)
            for match in matches:
                # Extract slide number (pattern returns tuple, get first element)
                if isinstance(match, tuple):
                    slide_num = int(match[0])
                else:
                    slide_num = int(match)
                
                # Try to find matching citation in chunk_mapping by slide_number
                matching_citation = None
                for chunk_num, citation in chunk_mapping.items():
                    cit_slide = citation.get('slide_number')
                    # Fallback for backward compatibility
                    if cit_slide is None:
                        cit_slide = citation.get('page_number')
                    
                    if cit_slide == slide_num:
                        matching_citation = citation
                        break
                
                if matching_citation:
                    # Create citation key using slide_number
                    citation_key = (matching_citation.get('source_file'), slide_num)
                    
                    if citation_key not in seen_citations:
                        seen_citations.add(citation_key)
                        
                        # Check if filename matches (handle timestamp prefixes and variations)
                        # Remove timestamp pattern if present (digits. digits_)
                        import re
                        cit_base = matching_citation.get('source_file', '').lower()
                        cit_base_clean = re.sub(r'^\d+\.\d+_', '', cit_base)
                        
                        # Found matching citation by slide_number
                        found_citations.append(matching_citation)
        
        return found_citations
    
    def extract_chunk_keys_from_response(
        self, 
        llm_response: str, 
        chunk_key_mapping: Dict[str, Dict],
        chunk_citations: List[Dict] = None,
        chunk_mapping: Dict[int, Dict] = None
    ) -> List[Dict]:
        """
        Extract chunk keys (filename_slide_number) from LLM response.
        Returns citations for mentioned chunk keys.
        
        Falls back to top chunks by distance if no keys are found.
        
        Args:
            llm_response: Full LLM response text
            chunk_key_mapping: Dictionary mapping chunk key to citation
            chunk_citations: List of chunk citations with distance (for fallback)
            chunk_mapping: Dictionary mapping chunk number to citation (for fallback)
        
        Returns:
            List of citation dictionaries for mentioned chunk keys
        """
        import re
        
        found_citations = []
        seen_citations = set()
        
        # Direct matching: Look for chunk keys in the response
        # Try to find exact or near-exact matches from chunk_key_mapping
        for chunk_key in chunk_key_mapping.keys():
            # Try exact match (case-insensitive)
            if chunk_key.lower() in llm_response.lower():
                if chunk_key not in seen_citations:
                    seen_citations.add(chunk_key)
                    citation = chunk_key_mapping[chunk_key]
                    found_citations.append(citation)
                    continue
            
            # Try with spaces/underscores normalized
            normalized_key = chunk_key.replace('_', ' ').replace('  ', ' ')
            if normalized_key.lower() in llm_response.lower():
                if chunk_key not in seen_citations:
                    seen_citations.add(chunk_key)
                    citation = chunk_key_mapping[chunk_key]
                    found_citations.append(citation)
        
        # Also try pattern matching for chunk keys with format: filename_number
        # Pattern: word(s) followed by underscore and number
        pattern = r'([A-Za-z0-9\s]+?)_(\d+)'
        matches = re.findall(pattern, llm_response, re.IGNORECASE)
        
        for match in matches:
            if len(match) == 2:
                prefix = match[0].strip()
                number = match[1].strip()
                
                # Try to match against chunk keys
                for chunk_key in chunk_key_mapping.keys():
                    # Normalize for comparison
                    normalized_key = chunk_key.lower().replace(' ', '_').replace('__', '_')
                    normalized_prefix = prefix.lower().replace(' ', '_')
                    
                    # Check if this could be the chunk key
                    # Match if prefix is in key and number matches
                    if normalized_prefix in normalized_key and f"_{number}" in chunk_key:
                        if chunk_key not in seen_citations:
                            seen_citations.add(chunk_key)
                            citation = chunk_key_mapping[chunk_key]
                            found_citations.append(citation)
        
        # If no chunk keys found, use fallback: top 1-2 chunks by distance
        if not found_citations and chunk_citations and chunk_mapping:
            logger.info("No chunk keys found in LLM response, using fallback: top chunks by distance")
            # Sort by distance (lower is better) and take top 1-2
            sorted_chunks = sorted(
                [c for c in chunk_citations if c.get('distance') is not None],
                key=lambda x: x['distance']
            )[:2]
            
            # Get citations for top chunks
            for chunk_info in sorted_chunks:
                chunk_num = chunk_info.get('chunk_number')
                if chunk_num and chunk_num in chunk_mapping:
                    citation = chunk_mapping[chunk_num]
                    # Avoid duplicates - use slide_number only
                    slide_num = citation.get('slide_number')
                    if slide_num is None:
                        slide_num = citation.get('page_number')  # Backward compatibility
                    citation_key = (
                        citation.get('source_file'),
                        slide_num
                    )
                    if citation_key not in seen_citations:
                        seen_citations.add(citation_key)
                        found_citations.append(citation)
        
        return found_citations
    
    def extract_human_readable_citations(
        self,
        llm_response: str,
        human_readable_mapping: Dict[str, Dict]
    ) -> List[Dict]:
        """
        Extract human-readable citations from LLM response.
        Parses patterns like "Slide 1" or "[Slide 5]".
        
        Args:
            llm_response: Full LLM response text
            human_readable_mapping: Dictionary mapping human-readable label to citation
            
        Returns:
            List of citation dictionaries that were mentioned
        """
        import re
        
        found_citations = []
        seen_citations = set()
        
        # Pattern to match simple "Slide X" format
        patterns = [
            r'\[Slide\s+(\d+)\]',  # [Slide 5] or [Slide 19]
            r'(?:^|\s)Slide\s+(\d+)(?:\s|$|,|\.)',  # Slide 5 or Slide 19 (standalone)
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, llm_response, re.IGNORECASE)
            for match in matches:
                # Extract slide number
                if isinstance(match, tuple):
                    slide_num = int(match[0])
                else:
                    slide_num = int(match)
                
                # Create label to match against human_readable_mapping
                label = f"Slide {slide_num}"
                
                # Try exact match first
                if label in human_readable_mapping:
                    citation = human_readable_mapping[label]
                    citation_key = (
                        citation.get('source_file'),
                        citation.get('slide_number')
                    )
                    if citation_key not in seen_citations:
                        seen_citations.add(citation_key)
                        found_citations.append(citation)
                    continue
                
                # Try case-insensitive match
                for mapping_label, citation in human_readable_mapping.items():
                    if mapping_label.lower() == label.lower():
                        citation_key = (
                            citation.get('source_file'),
                            citation.get('slide_number')
                        )
                        if citation_key not in seen_citations:
                            seen_citations.add(citation_key)
                            found_citations.append(citation)
                        break
        
        return found_citations
    
    def extract_used_chunks(self, llm_response: str) -> List[int]:
        """
        Extract chunk numbers mentioned in LLM response (fallback method).
        
        Looks for patterns like:
        - "CHUNK_1"
        - "CHUNK_1 and CHUNK_3"
        - "Based on CHUNK_1, CHUNK_2, and CHUNK_5"
        - "chunk 1" (case insensitive)
        
        Args:
            llm_response: Full LLM response text
        
        Returns:
            List of chunk numbers (1-indexed) that were used
        """
        import re
        
        # Pattern to match CHUNK_X or chunk X
        patterns = [
            r'CHUNK_(\d+)',  # CHUNK_1, CHUNK_2, etc.
            r'chunk\s+(\d+)',  # chunk 1, chunk 2 (case insensitive)
            r'Chunk\s+(\d+)',  # Chunk 1, Chunk 2
        ]
        
        used_chunks = set()
        
        for pattern in patterns:
            matches = re.findall(pattern, llm_response, re.IGNORECASE)
            for match in matches:
                try:
                    chunk_num = int(match)
                    if chunk_num > 0:  # Valid chunk number
                        used_chunks.add(chunk_num)
                except ValueError:
                    continue
        
        return sorted(list(used_chunks))
    
    def filter_citations_by_chunks(self, used_chunks: List[int], chunk_mapping: Dict[int, Dict]) -> List[Dict]:
        """
        Filter citations to only include those for chunks that were actually used.
        
        Args:
            used_chunks: List of chunk numbers that were used
            chunk_mapping: Dictionary mapping chunk number to citation
        
        Returns:
            Filtered list of citations
        """
        if not used_chunks or not chunk_mapping:
            return []
        
        used_citations = []
        seen_citations = set()
        
        for chunk_num in used_chunks:
            citation = chunk_mapping.get(chunk_num)
            if citation:
                # Create unique key for citation (same source + slide = same citation)
                slide_num = citation.get('slide_number')
                if slide_num is None:
                    slide_num = citation.get('page_number')  # Backward compatibility
                citation_key = (
                    citation.get('source_file'),
                    slide_num
                )
                
                if citation_key not in seen_citations:
                    seen_citations.add(citation_key)
                    used_citations.append(citation)
        
        return used_citations
