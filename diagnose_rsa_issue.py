"""
Comprehensive end-to-end diagnostic script for RSA chat query.
This will trace every step from embedding to LLM response.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
import os
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def diagnostic_test():
    """Run complete diagnostic test for RSA query."""
    
    print("="*80)
    print("🔍 COMPREHENSIVE RSA CHAT DIAGNOSTIC TEST")
    print("="*80)
    
    # Test query
    test_query = "explain RSA encryption to me and why it is needed"
    
    # ============================================================
    # STEP 1: Check ChromaDB Setup
    # ============================================================
    print("\n" + "="*80)
    print("STEP 1: ChromaDB Setup Check")
    print("="*80)
    
    chroma_path = "./chroma_db"
    
    if not os.path.exists(chroma_path):
        print(f"❌ ChromaDB directory not found: {chroma_path}")
        return
    
    print(f"✅ ChromaDB path exists: {chroma_path}")
    
    # Create client
    client = chromadb.PersistentClient(
        path=chroma_path,
        settings=ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    
    embedding_function = DefaultEmbeddingFunction()
    
    # Get all collections
    collections = client.list_collections()
    print(f"\n📚 Total Collections: {len(collections)}")
    
    total_docs = 0
    collection_details = []
    
    for coll in collections:
        collection = client.get_collection(coll.name)
        count = collection.count()
        total_docs += count
        collection_details.append({
            'name': coll.name,
            'count': count,
            'collection': collection
        })
        print(f"   - {coll.name}: {count} documents")
    
    print(f"\n📊 Total Documents: {total_docs}")
    
    if total_docs == 0:
        print("❌ No documents in ChromaDB!")
        return
    
    # ============================================================
    # STEP 2: Test Embedding Search (Per Collection)
    # ============================================================
    print("\n" + "="*80)
    print("STEP 2: Search Each Collection for RSA Content")
    print("="*80)
    
    print(f"\n🔍 Query: '{test_query}'")
    
    all_results = []
    
    for coll_info in collection_details:
        collection = coll_info['collection']
        coll_name = coll_info['name']
        coll_count = coll_info['count']
        
        if coll_count == 0:
            continue
        
        print(f"\n📂 Searching collection: {coll_name} ({coll_count} docs)")
        
        try:
            # Query this collection
            n_results = min(20, coll_count)
            results = collection.query(
                query_texts=[test_query],
                n_results=n_results
            )
            
            # Extract documents and distances
            docs = results.get('documents', [[]])[0] if results.get('documents') else []
            distances = results.get('distances', [[]])[0] if results.get('distances') else []
            
            print(f"   Retrieved: {len(docs)} documents")
            
            # Check for RSA mentions
            rsa_count = 0
            rsa_docs = []
            
            for i, doc in enumerate(docs):
                doc_lower = doc.lower()
                if 'rsa' in doc_lower or 'rivest' in doc_lower:
                    rsa_count += 1
                    rsa_docs.append({
                        'index': i,
                        'distance': distances[i] if i < len(distances) else None,
                        'preview': doc[:200]
                    })
            
            print(f"   📌 Documents mentioning RSA: {rsa_count}/{len(docs)}")
            
            if rsa_docs:
                print(f"   RSA document details:")
                for rsa_doc in rsa_docs[:3]:  # Show first 3
                    print(f"      - Doc #{rsa_doc['index']}, distance: {rsa_doc['distance']:.4f}")
                    print(f"        Preview: {rsa_doc['preview']}...")
            
            # Store results for aggregation
            for i, doc in enumerate(docs):
                all_results.append({
                    'collection': coll_name,
                    'document': doc,
                    'distance': distances[i] if i < len(distances) else 999,
                    'similarity': 1 - distances[i] if i < len(distances) else 0
                })
                
        except Exception as e:
            print(f"   ❌ Error searching collection: {e}")
            import traceback
            traceback.print_exc()
    
    # ============================================================
    # STEP 3: Aggregate and Sort Results
    # ============================================================
    print("\n" + "="*80)
    print("STEP 3: Aggregate Results Across All Collections")
    print("="*80)
    
    if not all_results:
        print("❌ No results found across all collections!")
        return
    
    # Sort by distance (lower is better)
    all_results.sort(key=lambda x: x['distance'])
    
    # Take top 20
    top_20 = all_results[:20]
    
    print(f"\n📊 Top 20 Results Distribution:")
    collection_dist = {}
    for result in top_20:
        coll = result['collection']
        collection_dist[coll] = collection_dist.get(coll, 0) + 1
    
    for coll, count in sorted(collection_dist.items(), key=lambda x: x[1], reverse=True):
        print(f"   - {coll}: {count} documents")
    
    # Check RSA mentions in top 20
    rsa_in_top20 = sum(1 for r in top_20 if 'rsa' in r['document'].lower() or 'rivest' in r['document'].lower())
    print(f"\n📌 RSA mentions in top 20: {rsa_in_top20}")
    
    if rsa_in_top20 > 0:
        print(f"\n✅ GOOD: RSA content IS in top 20 results")
        print(f"   Showing RSA documents:")
        for i, result in enumerate(top_20):
            if 'rsa' in result['document'].lower() or 'rivest' in result['document'].lower():
                print(f"\n   #{i+1} (distance: {result['distance']:.4f}, similarity: {result['similarity']:.4f})")
                print(f"   Collection: {result['collection']}")
                print(f"   Content preview: {result['document'][:300]}...")
    else:
        print(f"\n❌ PROBLEM: RSA content NOT in top 20 results!")
        print(f"   This means either:")
        print(f"   1. No documents contain RSA information")
        print(f"   2. Embedding search is not ranking RSA docs high enough")
    
    # ============================================================
    # STEP 4: Build Context for LLM
    # ============================================================
    print("\n" + "="*80)
    print("STEP 4: Build Context String for LLM")
    print("="*80)
    
    # Combine documents
    context_docs = [r['document'] for r in top_20]
    context = "\n\n---\n\n".join(context_docs)
    
    context_length = len(context)
    word_count = len(context.split())
    
    print(f"\n📝 Context Statistics:")
    print(f"   - Total characters: {context_length:,}")
    print(f"   - Total words: {word_count:,}")
    print(f"   - Documents combined: {len(context_docs)}")
    
    # Count RSA mentions in context
    rsa_mentions = context.lower().count('rsa') + context.lower().count('rivest')
    print(f"   - RSA/Rivest mentions: {rsa_mentions}")
    
    # Show first 1000 chars of context
    print(f"\n📄 Context Preview (first 1000 chars):")
    print("-" * 80)
    print(context[:1000])
    print("-" * 80)
    
    if rsa_mentions == 0:
        print("\n❌ CRITICAL: No RSA mentions in context!")
        print("   LLM will not be able to answer the question.")
        return
    
    # ============================================================
    # STEP 5: Test LLM Response
    # ============================================================
    print("\n" + "="*80)
    print("STEP 5: Send to Groq LLM and Get Response")
    print("="*80)
    
    # Check API key
    groq_api_key = os.getenv('GROQ_API_KEY')
    if not groq_api_key:
        print("❌ GROQ_API_KEY not found in environment!")
        return
    
    print(f"✅ Groq API Key: {groq_api_key[:20]}...")
    
    # Create Groq client
    try:
        groq_client = Groq(api_key=groq_api_key)
        print("✅ Groq client created")
    except Exception as e:
        print(f"❌ Error creating Groq client: {e}")
        return
    
    # Build system prompt (matching tutor service)
    system_prompt = """You are a friendly, supportive Network Security tutor assistant.

STRICT ANSWER REQUIREMENTS:
1. ONLY answer using the provided course materials below
2. If information is NOT in the course materials, respond: "I don't have that information in your course materials."
3. Keep answers CONCISE (3-4 sentences maximum)
4. Be FRIENDLY and SUPPORTIVE

IMPORTANT: Use ONLY the CONTEXT provided below."""
    
    # Build user message with context
    user_message = f"""COURSE MATERIALS (YOUR ONLY SOURCE - USE THESE TO ANSWER):
{context}

STUDENT QUESTION:
{test_query}

CRITICAL INSTRUCTIONS:
1. Answer ONLY using the course materials above
2. If the answer is NOT in the course materials, respond: "I don't have that information in your course materials."
3. Keep your answer CONCISE (3-4 sentences maximum)
4. Be FRIENDLY and SUPPORTIVE"""
    
    print(f"\n📤 Sending request to Groq...")
    print(f"   Model: llama-3.1-8b-instant")
    print(f"   Temperature: 0.7")
    print(f"   Max tokens: 300")
    
    try:
        # Call Groq API
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        llm_response = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else None
        
        print(f"✅ Response received")
        if tokens_used:
            print(f"   Tokens used: {tokens_used}")
        
        print(f"\n💬 LLM Response:")
        print("=" * 80)
        print(llm_response)
        print("=" * 80)
        
        # Analyze response
        print(f"\n🔍 Response Analysis:")
        if "don't have" in llm_response.lower() or "not in" in llm_response.lower():
            print("   ❌ LLM says content NOT in course materials")
            print("   This is the problem!")
        else:
            print("   ✅ LLM provided an answer from course materials")
        
    except Exception as e:
        print(f"❌ Error calling Groq API: {e}")
        import traceback
        traceback.print_exc()
    
    # ============================================================
    # FINAL DIAGNOSIS
    # ============================================================
    print("\n" + "="*80)
    print("🎯 FINAL DIAGNOSIS & RECOMMENDATIONS")
    print("="*80)
    
    print(f"\n✅ Summary:")
    print(f"   - Total collections: {len(collections)}")
    print(f"   - Total documents: {total_docs}")
    print(f"   - Top 20 docs retrieved: {len(top_20)}")
    print(f"   - RSA mentions in top 20: {rsa_in_top20}")
    print(f"   - RSA mentions in context: {rsa_mentions}")
    
    if rsa_in_top20 > 0 and rsa_mentions > 0:
        print(f"\n✅ RSA content IS being retrieved and sent to LLM")
        print(f"\n🔧 If LLM still says 'no info', the problem is:")
        print(f"   1. Context is too noisy (RSA content buried in irrelevant text)")
        print(f"   2. LLM prompt is too strict")
        print(f"   3. LLM is not finding RSA info in the long context")
        print(f"\n💡 RECOMMENDED FIXES:")
        print(f"   ✓ Make system prompt less strict")
        print(f"   ✓ Emphasize using context more clearly")
        print(f"   ✓ Reduce temperature for more deterministic answers")
        print(f"   ✓ Put RSA content at beginning of context")
    else:
        print(f"\n❌ RSA content NOT being retrieved properly")
        print(f"\n🔧 Problem is in embedding search:")
        print(f"   1. Documents don't contain RSA info")
        print(f"   2. Query embedding not matching RSA content")
        print(f"   3. RSA docs have low similarity scores")
        print(f"\n💡 RECOMMENDED FIXES:")
        print(f"   ✓ Re-upload documents with RSA content")
        print(f"   ✓ Use better search query: 'RSA public key cryptography'")
        print(f"   ✓ Check if RSA content is actually in uploaded PDFs")
        print(f"   ✓ Increase n_results to get more docs")


if __name__ == "__main__":
    diagnostic_test()
