"""
ChromaDB service for retrieving relevant content.
Supports both direct ChromaDB and LangChain vector store integration.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from app.config import settings
import os
from typing import Dict, Any, Optional, List

# LangChain imports
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings


class ChromaService:
    """Service for interacting with ChromaDB."""
    
    # Singleton pattern for ChromaDB client - shared across all instances
    _client_instance = None
    _client_lock = None
    
    def __init__(self):
        """Initialize ChromaDB client with OpenAI embeddings."""
        if not os.path.exists(settings.chroma_db_path):
            raise ValueError(f"ChromaDB path not found: {settings.chroma_db_path}")
        
        if not settings.openai_api_key:
            raise ValueError(
                "OpenAI API key is required for embeddings. "
                "Please set OPENAI_API_KEY in your .env file."
            )
        
        # Use singleton pattern for PersistentClient to avoid multiple instances
        if ChromaService._client_instance is None:
            import threading
            if ChromaService._client_lock is None:
                ChromaService._client_lock = threading.Lock()
            
            with ChromaService._client_lock:
                # Double-check pattern
                if ChromaService._client_instance is None:
                    ChromaService._client_instance = chromadb.PersistentClient(
                        path=settings.chroma_db_path,
                        settings=ChromaSettings(
                            anonymized_telemetry=False,
                            allow_reset=True
                        )
                    )
        
        # All instances share the same client
        self.client = ChromaService._client_instance
        self.embedding_function = OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key,
            model_name="text-embedding-3-small"
        )
    
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
            collection_name: Specific collection to search (if None, searches ALL collections)
            n_results: Number of results to return
            
        Returns:
            Dictionary with documents, metadatas, distances
        """
        try:
            # Get collections to search
            if collection_name:
                # Search specific collection
                collection = self.client.get_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function
                )
                results = collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    include=["documents", "metadatas", "distances"]
                )
                return results
            else:
                # Search ALL collections and combine results
                collections = self.client.list_collections()
                if not collections:
                    raise ValueError("No collections found in ChromaDB")
                
                all_documents = []
                all_metadatas = []
                all_distances = []
                
                # Search each collection
                for coll in collections:
                    try:
                        collection = self.client.get_collection(
                            name=coll.name,
                            embedding_function=self.embedding_function
                        )
                        
                        # Get results from this collection
                        coll_results = collection.query(
                            query_texts=[query],
                    n_results=n_results,
                            include=["documents", "metadatas", "distances"]
                        )
                        
                        # Combine results
                        if coll_results and coll_results.get('documents'):
                            all_documents.extend(coll_results['documents'][0])
                            all_metadatas.extend(coll_results.get('metadatas', [[]])[0])
                            all_distances.extend(coll_results.get('distances', [[]])[0])
                            
                    except Exception as e:
                        # Skip collections that cause errors
                        continue
                
                # Sort by distance (ascending - lower is better)
                if all_distances:
                    sorted_indices = sorted(range(len(all_distances)), key=lambda i: all_distances[i])
                    
                    # Take top n_results
                    sorted_indices = sorted_indices[:n_results]
                    
                    # Reorder results
                    sorted_documents = [all_documents[i] for i in sorted_indices]
                    sorted_metadatas = [all_metadatas[i] for i in sorted_indices]
                    sorted_distances = [all_distances[i] for i in sorted_indices]
                    
                    results = {
                        'documents': [sorted_documents],
                        'metadatas': [sorted_metadatas],
                        'distances': [sorted_distances]
                    }
                else:
                    results = {
                        'documents': [[]],
                        'metadatas': [[]],
                        'distances': [[]]
                    }
                
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
    
    def delete_all_collections(self) -> Dict[str, Any]:
        """
        Delete all collections from ChromaDB.
        WARNING: This will permanently delete all documents and embeddings!
        
        Returns:
            Dictionary with deletion results
        """
        try:
            collections = self.client.list_collections()
            deleted_collections = []
            errors = []
            
            for collection in collections:
                try:
                    collection_name = collection.name
                    self.client.delete_collection(name=collection_name)
                    deleted_collections.append(collection_name)
                except Exception as e:
                    errors.append({
                        "collection": collection.name,
                        "error": str(e)
                    })
            
            return {
                "deleted_count": len(deleted_collections),
                "deleted_collections": deleted_collections,
                "errors": errors,
                "message": f"Successfully deleted {len(deleted_collections)} collection(s)"
            }
        except Exception as e:
            raise Exception(f"Failed to delete collections: {str(e)}")
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a specific collection from ChromaDB.
        
        Args:
            collection_name: Name of the collection to delete
        
        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete_collection(name=collection_name)
            return True
        except Exception as e:
            raise Exception(f"Failed to delete collection '{collection_name}': {str(e)}")
    
    def extract_citations(self, metadatas: List[Dict]) -> List[Dict]:
        """
        Extract and format citation information from metadata.
        Uses slide_number only (lecture number). Deduplicates citations.
        
        Args:
            metadatas: List of metadata dictionaries from ChromaDB search
        
        Returns:
            List of citation dictionaries with slide_number
        """
        citations = []
        seen = set()  # Deduplicate citations
        
        for meta in metadatas:
            if not meta:
                continue
            
            source_file = meta.get("source_file") or meta.get("source", "Unknown")
            doc_type = meta.get("document_type", "unknown")
            
            # Get slide_number (preferred) or fallback to page_number for backward compatibility
            slide_num = meta.get("slide_number")
            if slide_num is None:
                slide_num = meta.get("page_number")  # Backward compatibility
            
            # Create unique key for citation (same slide = same citation)
            if slide_num is not None:
                key = (source_file, slide_num)
            else:
                key = (source_file, None)
            
            if key in seen:
                continue
            seen.add(key)
            
            citation = {
                "source_file": source_file,
                "document_type": doc_type,
                "slide_number": slide_num,  # Use slide_number only
                "collection": meta.get("collection_name") or meta.get("source", "Unknown")
            }
            citations.append(citation)
        
        return citations
    
    def get_langchain_vector_store(self, collection_name: Optional[str] = None):
        """
        Get LangChain ChromaDB vector store for RAG chains.
        Reuses the existing PersistentClient to avoid conflicts.
        
        Args:
            collection_name: Specific collection name (if None, uses first available collection)
        
        Returns:
            LangChain Chroma vector store instance
        
        Raises:
            ValueError: If collection not found
        """
        if not settings.openai_api_key:
            raise ValueError(
                "OpenAI API key is required for embeddings. "
                "Please set OPENAI_API_KEY in your .env file."
            )
        
        # Initialize OpenAI embeddings for LangChain
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.openai_api_key
        )
        
        # Determine collection to use
        # When passing client, don't pass persist_directory to avoid conflicts
        if collection_name:
            # Use specific collection - pass existing client to avoid creating new instance
            vector_store = Chroma(
                collection_name=collection_name,
                client=self.client,  # Reuse existing client (don't pass persist_directory when client is provided)
                embedding_function=embeddings
            )
        else:
            # Use first available collection (or create default)
            collections = self.client.list_collections()
            if not collections:
                raise ValueError("No collections found in ChromaDB")
            
            # Use first collection - pass existing client to avoid creating new instance
            first_collection = collections[0].name
            vector_store = Chroma(
                collection_name=first_collection,
                client=self.client,  # Reuse existing client (don't pass persist_directory when client is provided)
                embedding_function=embeddings
            )
        
        return vector_store
    
    def get_langchain_retriever(
        self,
        collection_name: Optional[str] = None,
        search_kwargs: Optional[Dict] = None
    ):
        """
        Get LangChain retriever from ChromaDB vector store.
        
        Args:
            collection_name: Specific collection name (if None, uses first available)
            search_kwargs: Additional search parameters (e.g., {"k": 10})
        
        Returns:
            LangChain retriever instance
        """
        vector_store = self.get_langchain_vector_store(collection_name)
        
        # Default search kwargs
        if search_kwargs is None:
            search_kwargs = {"k": 10}
        
        retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
        return retriever
