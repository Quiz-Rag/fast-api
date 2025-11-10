"""
Temporary test script to query ChromaDB directly and see what's returned.
Run this to debug why chat isn't finding documents.
"""

import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.chroma_service import ChromaService
import re


def clean_query(text: str) -> str:
    """Clean query text for better search."""
    cleaned = re.sub(r'[^\w\s]', ' ', text)
    cleaned = ' '.join(cleaned.split())
    return cleaned


def test_chromadb_query():
    """Test ChromaDB query with RSA question."""
    
    print("=" * 80)
    print("🧪 CHROMADB QUERY TEST")
    print("=" * 80)
    
    # Initialize ChromaService
    print("\n1️⃣  Initializing ChromaService...")
    chroma = ChromaService()
    print("   ✅ ChromaService initialized")
    
    # Check collections
    print("\n2️⃣  Checking available collections...")
    try:
        collections = chroma.client.list_collections()
        print(f"   📚 Found {len(collections)} collections:")
        
        total_docs = 0
        for collection in collections:
            count = collection.count()
            total_docs += count
            print(f"      - {collection.name}: {count} documents")
        
        print(f"   📊 Total documents: {total_docs}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Test query
    question = "What is RSA encryption?"
    cleaned_question = clean_query(question)
    
    print(f"\n3️⃣  Testing query...")
    print(f"   📝 Original: '{question}'")
    print(f"   🧹 Cleaned:  '{cleaned_question}'")
    
    # Query ChromaDB
    print(f"\n4️⃣  Querying ChromaDB (requesting 20 results)...")
    try:
        results = chroma.search_documents(
            query=cleaned_question,
            collection_name=None,  # Search all collections
            n_results=20
        )
        
        if not results:
            print("   ❌ No results returned!")
            return
        
        # Check documents
        if results.get('documents'):
            doc_count = len(results['documents'][0])
            print(f"   ✅ Received {doc_count} documents")
            
            # Show distances/similarities
            if results.get('distances'):
                distances = results['distances'][0]
                print(f"\n5️⃣  Similarity scores (1.0 = perfect match):")
                for i, dist in enumerate(distances[:10]):  # Show first 10
                    similarity = 1 - dist
                    print(f"      Doc {i+1}: {similarity:.4f}")
            
            # Show document previews
            print(f"\n6️⃣  Document previews:")
            documents = results['documents'][0]
            for i, doc in enumerate(documents[:5]):  # Show first 5
                preview = doc[:150].replace('\n', ' ')
                if len(doc) > 150:
                    preview += "..."
                print(f"\n   📄 Document {i+1} ({len(doc)} chars):")
                print(f"      {preview}")
            
            # Check if RSA is mentioned
            print(f"\n7️⃣  Checking for 'RSA' mentions...")
            rsa_count = 0
            for i, doc in enumerate(documents):
                if 'RSA' in doc.upper():
                    rsa_count += 1
                    print(f"      ✅ Document {i+1} mentions RSA")
            
            if rsa_count == 0:
                print(f"      ⚠️  No documents mention RSA!")
            else:
                print(f"      ✅ {rsa_count}/{doc_count} documents mention RSA")
            
            # Combine context
            print(f"\n8️⃣  Combined context statistics:")
            context = "\n\n".join(documents)
            word_count = len(context.split())
            char_count = len(context)
            print(f"      📝 Total words: {word_count}")
            print(f"      📝 Total characters: {char_count}")
            print(f"      📝 Average doc length: {char_count // doc_count} chars")
            
        else:
            print("   ❌ No documents in results!")
        
    except Exception as e:
        print(f"   ❌ Error during query: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_chromadb_query()
