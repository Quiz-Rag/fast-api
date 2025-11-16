#!/usr/bin/env python3
"""
Script to clean/reset ChromaDB by deleting all collections.
This allows re-uploading documents with the new citation metadata structure.

WARNING: This will permanently delete all documents and embeddings!

Usage:
    python clean_chromadb.py           # Interactive mode (requires confirmation)
    python clean_chromadb.py --force    # Non-interactive mode (auto-confirms)
"""

import sys
import os
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.chroma_service import ChromaService
from app.config import settings


def clean_chromadb(force: bool = False):
    """Delete all collections from ChromaDB."""
    print("🧹 ChromaDB Cleanup Script")
    print("=" * 50)
    
    # Check if ChromaDB exists
    if not os.path.exists(settings.chroma_db_path):
        print(f"❌ ChromaDB path not found: {settings.chroma_db_path}")
        print("   ChromaDB may not have been initialized yet.")
        return False
    
    try:
        # Initialize ChromaService
        chroma_service = ChromaService()
        
        # List current collections
        collections = chroma_service.list_collections()
        
        if not collections:
            print("✅ ChromaDB is already empty - no collections to delete.")
            return True
        
        print(f"\n📋 Found {len(collections)} collection(s):")
        for coll in collections:
            try:
                collection = chroma_service.client.get_collection(coll.name)
                count = collection.count()
                print(f"   - {coll.name} ({count} documents)")
            except:
                print(f"   - {coll.name} (count unknown)")
        
        # Confirm deletion
        if not force:
            print("\n⚠️  WARNING: This will permanently delete ALL collections and documents!")
            response = input("   Type 'DELETE' to confirm: ")
            
            if response != "DELETE":
                print("❌ Cleanup cancelled.")
                return False
        else:
            print("\n⚠️  WARNING: Deleting ALL collections and documents (--force mode)")
        
        # Delete all collections
        print("\n🗑️  Deleting collections...")
        result = chroma_service.delete_all_collections()
        
        print(f"\n✅ {result['message']}")
        print(f"   Deleted collections: {', '.join(result['deleted_collections'])}")
        
        if result['errors']:
            print(f"\n⚠️  Errors encountered:")
            for error in result['errors']:
                print(f"   - {error['collection']}: {error['error']}")
        
        print("\n✅ ChromaDB cleanup completed!")
        print("   You can now upload new documents with citation metadata support.")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during cleanup: {str(e)}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean ChromaDB by deleting all collections")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt and delete all collections automatically"
    )
    args = parser.parse_args()
    
    success = clean_chromadb(force=args.force)
    sys.exit(0 if success else 1)

