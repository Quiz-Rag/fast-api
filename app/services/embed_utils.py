"""
Document processing utilities for PDF and PPTX files.
Handles text extraction, chunking, embedding generation, and ChromaDB storage.
Uses ChromaDB's native default embedding function (all-MiniLM-L6-v2) - FREE and local.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import PyPDF2
from pptx import Presentation
from typing import List
import os

from app.config import settings


def extract_text_from_pptx(file_path: str) -> str:
    """
    Extract text from a PowerPoint (PPTX) file.

    Args:
        file_path: Path to the PPTX file

    Returns:
        Extracted text as a single string
    """
    prs = Presentation(file_path)
    text_parts = []

    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text_parts.append(shape.text)

    return "\n".join(text_parts)


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file.

    Args:
        file_path: Path to the PDF file

    Returns:
        Extracted text as a single string
    """
    text_parts = []

    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)

        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

    return "\n".join(text_parts)


def chunk_text(text: str) -> List[Document]:
    """
    Split text into smaller chunks using RecursiveCharacterTextSplitter.

    Args:
        text: Input text to split

    Returns:
        List of Document objects containing text chunks
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )

    docs = splitter.create_documents([text])
    return docs


def store_in_chroma(
    docs: List[Document],
    collection_name: str = "default_collection"
):
    """
    Store document chunks in ChromaDB with embeddings.
    Uses ChromaDB's native default embedding function (all-MiniLM-L6-v2) automatically.

    Args:
        docs: List of Document objects to store
        collection_name: Name of the ChromaDB collection

    Returns:
        ChromaDB collection instance
    """
    
    # Ensure ChromaDB directory exists
    os.makedirs(settings.chroma_db_path, exist_ok=True)

    # Create ChromaDB client with native default embeddings
    try:
        client = chromadb.PersistentClient(
            path=settings.chroma_db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Get or create collection (uses all-MiniLM-L6-v2 by default)
        # Using default embedding function explicitly
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        embedding_function = DefaultEmbeddingFunction()

        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function
        )
    except Exception as e:
        print(f"Error creating ChromaDB client/collection: {e}")
        raise

    # Prepare data for ChromaDB
    documents = [doc.page_content for doc in docs]
    ids = [f"{collection_name}_{i}" for i in range(len(docs))]

    # Ensure each document has non-empty metadata (ChromaDB requirement)
    metadatas = []
    for i, doc in enumerate(docs):
        if doc.metadata and len(doc.metadata) > 0:
            metadatas.append(doc.metadata)
        else:
            # Provide default metadata if empty
            metadatas.append({"chunk_index": i, "source": collection_name})

    # Add documents (embeddings generated automatically by ChromaDB)
    collection.add(
        documents=documents,
        ids=ids,
        metadatas=metadatas
    )

    return collection


def process_document(
    file_path: str,
    file_type: str,
    collection_name: str = "default_collection"
) -> dict:
    """
    Complete pipeline to process a document: extract text, chunk, embed, and store.

    Args:
        file_path: Path to the document file
        file_type: Type of file ('pdf' or 'pptx')
        collection_name: Name for the ChromaDB collection

    Returns:
        Dictionary with processing results
    """
    # Extract text based on file type
    if file_type == "pdf":
        text = extract_text_from_pdf(file_path)
    elif file_type == "pptx":
        text = extract_text_from_pptx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    if not text or len(text.strip()) == 0:
        raise ValueError("No text could be extracted from the document")

    # Chunk the text
    docs = chunk_text(text)

    # Store in ChromaDB (this will also generate embeddings)
    vector_store = store_in_chroma(docs, collection_name)

    return {
        "chunks_count": len(docs),
        "collection_name": collection_name,
        "text_length": len(text),
    }
