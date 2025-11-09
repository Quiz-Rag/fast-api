"""
ChromaDB service for retrieving relevant content.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from app.config import settings
import os
from typing import Dict, Any, Optional


class ChromaService:
    """Service for interacting with ChromaDB."""
    
    def __init__(self):
        """Initialize ChromaDB client."""
        if not os.path.exists(settings.chroma_db_path):
            raise ValueError(f"ChromaDB path not found: {settings.chroma_db_path}")
        
        self.client = chromadb.PersistentClient(
            path=settings.chroma_db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        self.embedding_function = DefaultEmbeddingFunction()
    
    def search_documents(
        self,
        query: str,
        collection_name: Optional[str] = None,
        n_results: int = 10
    ) -> Dict[str, Any]:
        """
        Search for relevant documents in ChromaDB.
        
        Args:
            query: Search query text
            collection_name: Specific collection to search (if None, searches first available)
            n_results: Number of results to return
            
        Returns:
            Dictionary with documents, metadatas, distances
        """
        try:
            # Get collection
            if collection_name:
                collection = self.client.get_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function
                )
            else:
                # Get first available collection
                collections = self.client.list_collections()
                if not collections:
                    raise ValueError("No collections found in ChromaDB")
                collection = self.client.get_collection(
                    name=collections[0].name,
                    embedding_function=self.embedding_function
                )
            
            # Perform search
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            return results
            
        except ValueError as e:
            raise ValueError(f"Collection error: {str(e)}")
        except Exception as e:
            raise Exception(f"ChromaDB search failed: {str(e)}")
    
    def list_collections(self):
        """List all available collections."""
        try:
            return self.client.list_collections()
        except Exception as e:
            raise Exception(f"Failed to list collections: {str(e)}")
