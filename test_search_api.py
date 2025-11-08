#!/usr/bin/env python3
"""
Test script to validate the search API functionality and ChromaDB connection.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
import os

# Test ChromaDB connection and list collections
def test_chromadb():
    try:
        chroma_db_path = "./chroma_db"
        
        print(f"Testing ChromaDB connection at: {chroma_db_path}")
        print(f"Directory exists: {os.path.exists(chroma_db_path)}")
        
        # Create ChromaDB client
        client = chromadb.PersistentClient(
            path=chroma_db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # List all collections
        collections = client.list_collections()
        print(f"\nFound {len(collections)} collections:")
        
        for collection in collections:
            print(f"- Collection: {collection.name}")
            print(f"  ID: {collection.id}")
            
            # Get collection details
            try:
                col = client.get_collection(collection.name)
                count = col.count()
                print(f"  Document count: {count}")
                
                # Test a sample query if there are documents
                if count > 0:
                    print(f"  Testing sample query...")
                    results = col.query(
                        query_texts=["test query"],
                        n_results=min(3, count),
                        include=["documents", "metadatas", "distances"]
                    )
                    print(f"  Query returned {len(results['documents'][0])} results")
                    
                    # Show first result as example
                    if results['documents'][0]:
                        first_doc = results['documents'][0][0]
                        first_distance = results['distances'][0][0] if results['distances'] else 'N/A'
                        print(f"  First result preview: {first_doc[:100]}...")
                        print(f"  Distance: {first_distance}")
                        
            except Exception as e:
                print(f"  Error getting collection details: {e}")
            
            print()
        
        if not collections:
            print("No collections found. You may need to upload and process documents first.")
            
    except Exception as e:
        print(f"Error testing ChromaDB: {e}")

if __name__ == "__main__":
    test_chromadb()