"""
Test script to verify ChromaDB setup and basic operations.
"""

import chromadb
from chromadb.config import Settings
import os


def test_chroma_setup():
    """Test ChromaDB initialization and basic operations."""

    print("🔧 Testing ChromaDB Setup...\n")

    # Get the chroma_db path
    chroma_path = "./chroma_db"

    # Ensure directory exists
    os.makedirs(chroma_path, exist_ok=True)
    print(f"✓ ChromaDB directory: {chroma_path}")

    # Initialize ChromaDB client with persistent storage
    try:
        client = chromadb.PersistentClient(path=chroma_path)
        print("✓ ChromaDB client initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize ChromaDB client: {e}")
        return False

    # Create or get a test collection
    try:
        collection_name = "test_collection"

        # Delete collection if it exists (for clean testing)
        try:
            client.delete_collection(name=collection_name)
            print(f"✓ Deleted existing test collection")
        except:
            pass

        # Create new collection
        collection = client.create_collection(
            name=collection_name,
            metadata={"description": "Test collection for setup verification"}
        )
        print(f"✓ Created collection: {collection_name}")

    except Exception as e:
        print(f"✗ Failed to create collection: {e}")
        return False

    # Test adding documents
    try:
        test_docs = [
            "This is the first test document about AI.",
            "This is the second test document about machine learning.",
            "This is the third test document about data science."
        ]

        collection.add(
            documents=test_docs,
            ids=["doc1", "doc2", "doc3"],
            metadatas=[
                {"source": "test", "topic": "AI"},
                {"source": "test", "topic": "ML"},
                {"source": "test", "topic": "DS"}
            ]
        )
        print(f"✓ Added {len(test_docs)} test documents")

    except Exception as e:
        print(f"✗ Failed to add documents: {e}")
        return False

    # Test querying
    try:
        results = collection.query(
            query_texts=["Tell me about artificial intelligence"],
            n_results=2
        )
        print(f"✓ Query successful, found {len(results['documents'][0])} results")

        # Display results
        print("\n📊 Query Results:")
        for i, doc in enumerate(results['documents'][0]):
            print(f"  {i+1}. {doc[:80]}...")

    except Exception as e:
        print(f"✗ Failed to query: {e}")
        return False

    # Test collection stats
    try:
        count = collection.count()
        print(f"\n✓ Collection contains {count} documents")

    except Exception as e:
        print(f"✗ Failed to get collection stats: {e}")
        return False

    # List all collections
    try:
        collections = client.list_collections()
        print(f"✓ Total collections in database: {len(collections)}")
        for coll in collections:
            print(f"  - {coll.name}")

    except Exception as e:
        print(f"✗ Failed to list collections: {e}")
        return False

    # Cleanup test collection
    try:
        client.delete_collection(name=collection_name)
        print(f"\n✓ Cleaned up test collection")
    except Exception as e:
        print(f"⚠ Warning: Failed to cleanup test collection: {e}")

    print("\n✅ ChromaDB setup verified successfully!")
    print(f"\n📁 Database location: {os.path.abspath(chroma_path)}")

    return True


if __name__ == "__main__":
    success = test_chroma_setup()
    exit(0 if success else 1)
