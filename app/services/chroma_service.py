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

    # --------------------------------------------
    #  THIS METHOD MUST BE OUTSIDE __init__
    # --------------------------------------------
    def retrieve_with_citations(self, query: str, collection_name: Optional[str] = None, n_results: int = 4):
        """
        Returns both:
        - combined context text
        - citation metadata list
        """
        results = self.search_documents(
            query=query,
            collection_name=collection_name,
            n_results=n_results
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        # Build combined context
        context = "\n\n".join(docs) if docs else ""

        # Build citation objects
        citations = []
        for m in metas:
            if isinstance(m, dict):
                loc = m.get("location")
            else:
                loc = None
            citations.append({"location": loc})

        return context, citations

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
