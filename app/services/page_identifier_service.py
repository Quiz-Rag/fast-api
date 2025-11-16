"""
Service for identifying page numbers from reference text using LLM.
"""

import logging
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.models.langchain_schemas import PageNumberOutput
from app.services.embed_utils import extract_text_from_pdf, extract_text_from_pptx
from app.services.prompts import PromptTemplates

logger = logging.getLogger(__name__)


class PageIdentifierService:
    """Service for identifying page numbers from reference text."""
    
    def __init__(self):
        """Initialize ChatOpenAI client."""
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set in environment variables")
        
        self.llm = ChatOpenAI(
            model=settings.openai_llm_model,
            temperature=0.3,  # Lower temperature for more accurate page identification
            openai_api_key=settings.openai_api_key
        )
        self.parser = PydanticOutputParser(pydantic_object=PageNumberOutput)
    
    async def identify_page_number(
        self,
        file_path: str,
        ref_text: str,
        file_type: str
    ) -> Optional[int]:
        """
        Identify the page number where ref_text appears in the file.
        
        Args:
            file_path: Path to the PDF or PPTX file
            ref_text: Reference text to find in the file
            file_type: "pdf" or "pptx"
        
        Returns:
            Page number (first occurrence) or None if not found or error
        """
        if not ref_text or len(ref_text.strip()) < 20:
            logger.debug("Ref text too short, skipping page identification")
            return None
        
        try:
            # Extract all pages/slides from file
            if file_type == "pdf":
                pages = extract_text_from_pdf(file_path)
            elif file_type == "pptx":
                pages = extract_text_from_pptx(file_path)
            else:
                logger.warning(f"Unsupported file type: {file_type}")
                return None
            
            if not pages:
                logger.warning(f"No pages/slides extracted from {file_path}")
                return None
            
            # Format pages for LLM
            pages_text = ""
            for page_num, page_text in pages:
                # Truncate very long pages to avoid token limits
                truncated_text = page_text[:2000] if len(page_text) > 2000 else page_text
                pages_text += f"Page {page_num}:\n{truncated_text}\n\n"
            
            # Get prompt template
            chat_prompt = PromptTemplates.get_page_identification_prompt()
            
            # Create chain with structured output
            chain = chat_prompt | self.llm | self.parser
            
            # Call LLM (async) with template variables
            result = await chain.ainvoke({
                "pages_text": pages_text,
                "ref_text": ref_text
            })
            
            page_number = result.page_number
            
            logger.info(f"Identified page number {page_number} for ref_text (first {50} chars: {ref_text[:50]}...)")
            
            return page_number
            
        except Exception as e:
            logger.error(f"Error identifying page number: {str(e)}")
            return None

