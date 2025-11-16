#!/usr/bin/env python3
"""
Script to count total embeddings, per-collection, and per-slide counts in ChromaDB.
"""

import sys
import os
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

def count_embeddings():
    """Count embeddings in all ChromaDB collections, grouped by collection and slide."""
    try:
        # Check if ChromaDB path exists
        if not os.path.exists(settings.chroma_db_path):
            print("❌ ChromaDB path not found:", settings.chroma_db_path)
            return
        
        # Check for OpenAI API key
        if not settings.openai_api_key:
            print("❌ OpenAI API key is required. Please set OPENAI_API_KEY in your .env file.")
            return
        
        # Create ChromaDB client
        client = chromadb.PersistentClient(
            path=settings.chroma_db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create embedding function
        embedding_function = OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key,
            model_name="text-embedding-3-small"
        )
        
        # List all collections
        collections = client.list_collections()
        
        if not collections:
            print("📊 Total embeddings: 0")
            print("No collections found in ChromaDB.")
            return
        
        print("=" * 70)
        print("📊 CHROMADB EMBEDDINGS COUNT")
        print("=" * 70)
        print()
        
        collection_counts = []
        total_embeddings = 0
        slide_counts = defaultdict(int)  # slide_number -> count
        
        # Count embeddings in each collection
        for collection in collections:
            try:
                col = client.get_collection(
                    name=collection.name,
                    embedding_function=embedding_function
                )
                count = col.count()
                total_embeddings += count
                
                # Get all documents to count by slide_number
                try:
                    # Get all data from collection
                    results = col.get(include=["metadatas"])
                    metadatas = results.get("metadatas", [])
                    
                    # Count by slide_number
                    collection_slide_counts = defaultdict(int)
                    for metadata in metadatas:
                        if metadata:
                            slide_num = metadata.get("slide_number")
                            # Fallback to page_number for backward compatibility
                            if slide_num is None:
                                slide_num = metadata.get("page_number")
                            
                            if slide_num is not None:
                                slide_key = f"Slide {slide_num}"
                                slide_counts[slide_key] += 1
                                collection_slide_counts[slide_key] += 1
                            else:
                                slide_counts["Unknown"] += 1
                                collection_slide_counts["Unknown"] += 1
                    
                    collection_counts.append({
                        "name": collection.name,
                        "count": count,
                        "slide_counts": dict(collection_slide_counts)
                    })
                except Exception as e:
                    # If we can't get metadata, just show total count
                    collection_counts.append({
                        "name": collection.name,
                        "count": count,
                        "slide_counts": None,
                        "error": f"Could not get slide breakdown: {str(e)}"
                    })
                    
            except Exception as e:
                print(f"⚠️  Error counting collection '{collection.name}': {str(e)}")
                collection_counts.append({
                    "name": collection.name,
                    "count": 0,
                    "error": str(e)
                })
        
        # Print results
        print(f"📊 Total embeddings: {total_embeddings}")
        print()
        print("=" * 70)
        print("PER-COLLECTION COUNTS:")
        print("=" * 70)
        
        for col_info in collection_counts:
            if "error" in col_info and "slide_counts" not in col_info:
                print(f"  ❌ {col_info['name']}: ERROR - {col_info['error']}")
            else:
                print(f"  📁 {col_info['name']}: {col_info['count']} embeddings")
                if col_info.get('slide_counts'):
                    for slide, slide_count in sorted(col_info['slide_counts'].items(), 
                                                     key=lambda x: (x[0] == "Unknown", 
                                                                   int(x[0].split()[-1]) if x[0] != "Unknown" and x[0].split()[-1].isdigit() else 999)):
                        print(f"      └─ {slide}: {slide_count} embeddings")
                elif "error" in col_info:
                    print(f"      ⚠️  {col_info['error']}")
        
        print()
        print("=" * 70)
        print("PER-SLIDE COUNTS (ACROSS ALL COLLECTIONS):")
        print("=" * 70)
        
        # Sort slides: Unknown last, then by slide number
        sorted_slides = sorted(slide_counts.items(), 
                              key=lambda x: (x[0] == "Unknown", 
                                            int(x[0].split()[-1]) if x[0] != "Unknown" and x[0].split()[-1].isdigit() else 999))
        
        for slide, count in sorted_slides:
            print(f"  {slide}: {count} embeddings")
        
        print()
        print("=" * 70)
        print(f"✅ Summary: {total_embeddings} total embeddings across {len(collection_counts)} collections")
        print(f"   {len(slide_counts)} unique slides")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    count_embeddings()

