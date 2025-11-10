"""
End-to-end test script for chat flow debugging.
Tests the complete flow: Question → ChromaDB → Context → LLM → Response
"""

import sys
import os
import asyncio
import re

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.chroma_service import ChromaService
from app.services.ai_service import AIService
from groq import Groq
from app.config import settings


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def clean_query(text: str) -> str:
    """Clean query text for better search."""
    cleaned = re.sub(r'[^\w\s]', ' ', text)
    cleaned = ' '.join(cleaned.split())
    return cleaned


async def test_chat_flow():
    """Test the complete chat flow end-to-end."""
    
    # Test question
    question = "What is RSA encryption and why is it needed?"
    
    print_section("🧪 CHAT FLOW DEBUG TEST")
    print(f"\n📝 Question: '{question}'")
    
    # STEP 1: Clean the query
    print_section("STEP 1: QUERY CLEANING")
    cleaned_question = clean_query(question)
    print(f"Original: {question}")
    print(f"Cleaned:  {cleaned_question}")
    
    # STEP 2: Search ChromaDB
    print_section("STEP 2: CHROMADB SEARCH")
    
    chroma = ChromaService()
    
    # Check collections
    print("\n📚 Collections:")
    collections = chroma.client.list_collections()
    total_docs = 0
    for coll in collections:
        count = coll.count()  # Call the method
        total_docs += count
        print(f"   - {coll.name}: {count} documents")
    print(f"\n📊 Total: {total_docs} documents across {len(collections)} collections")
    
    # Search
    print(f"\n🔍 Searching for: '{cleaned_question}'")
    results = chroma.search_documents(
        query=cleaned_question,
        collection_name=None,
        n_results=20
    )
    
    # Analyze results
    if not results or not results.get('documents'):
        print("❌ NO RESULTS RETURNED!")
        return
    
    documents = results['documents']
    distances = results.get('distances', [])
    
    print(f"\n✅ Retrieved {len(documents)} documents")
    
    # Show top 10 with distances
    print("\n📈 Top 10 Results (lower distance = better match):")
    for i in range(min(10, len(documents))):
        dist = distances[i] if i < len(distances) else "N/A"
        preview = documents[i][:100].replace('\n', ' ')
        has_rsa = "🔐 RSA" if 'rsa' in documents[i].lower() or 'rivest' in documents[i].lower() else ""
        print(f"   {i+1}. Distance: {dist:.4f} {has_rsa}")
        print(f"      {preview}...")
    
    # Check RSA mentions
    rsa_count = sum(1 for doc in documents if 'rsa' in doc.lower() or 'rivest' in doc.lower())
    print(f"\n🔐 Documents mentioning RSA: {rsa_count}/{len(documents)}")
    
    if rsa_count > 0:
        print("\n📄 RSA-related documents:")
        for i, doc in enumerate(documents):
            if 'rsa' in doc.lower() or 'rivest' in doc.lower():
                print(f"\n   Document {i+1}:")
                # Find and show RSA context
                lower_doc = doc.lower()
                rsa_pos = lower_doc.find('rsa')
                if rsa_pos >= 0:
                    start = max(0, rsa_pos - 100)
                    end = min(len(doc), rsa_pos + 200)
                    context = doc[start:end].replace('\n', ' ')
                    print(f"      ...{context}...")
    
    # STEP 3: Build context
    print_section("STEP 3: CONTEXT BUILDING")
    
    context = "\n\n---\n\n".join(documents)
    context_words = len(context.split())
    context_chars = len(context)
    
    print(f"📝 Context statistics:")
    print(f"   - Total words: {context_words}")
    print(f"   - Total characters: {context_chars}")
    print(f"   - Documents combined: {len(documents)}")
    
    # Limit context (like in production)
    if context_words > 4000:
        words = context.split()
        context = " ".join(words[:4000])
        print(f"   - Truncated to: 4000 words")
    
    print(f"\n📄 Context preview (first 500 chars):")
    print(context[:500])
    print("...")
    
    # Check if RSA is in final context
    if 'rsa' in context.lower() or 'rivest' in context.lower():
        print("\n✅ RSA information IS present in context")
    else:
        print("\n❌ RSA information is NOT in context!")
    
    # STEP 4: Build system prompt
    print_section("STEP 4: SYSTEM PROMPT")
    
    system_prompt = """You are a friendly, supportive Network Security tutor assistant.

STRICT ANSWER REQUIREMENTS (UNBREAKABLE):
1. ONLY answer using the provided course materials below
2. If information is NOT in the course materials, respond: "I don't have that information in your course materials."
3. Keep answers CONCISE (3-4 sentences maximum)
4. Be FRIENDLY and SUPPORTIVE

IMPORTANT: Use ONLY the CONTEXT provided below."""
    
    print(f"System prompt length: {len(system_prompt)} chars")
    
    # STEP 5: Build user message
    print_section("STEP 5: USER MESSAGE TO LLM")
    
    user_message = f"""COURSE MATERIALS (YOUR ONLY SOURCE - USE THESE TO ANSWER):
{context}

STUDENT QUESTION:
{question}

CRITICAL INSTRUCTIONS:
1. Answer ONLY using the course materials above
2. If the answer is NOT in the course materials, respond: "I don't have that information in your course materials."
3. Keep your answer CONCISE (3-4 sentences maximum)
4. Be FRIENDLY and SUPPORTIVE"""
    
    print(f"User message length: {len(user_message)} chars")
    print(f"User message words: {len(user_message.split())} words")
    
    # Check if RSA is mentioned in user message
    if 'rsa' in user_message.lower():
        print("✅ RSA is mentioned in the user message to LLM")
    else:
        print("❌ RSA is NOT in the user message to LLM!")
    
    # STEP 6: Call LLM
    print_section("STEP 6: LLM CALL")
    
    print("Calling Groq API...")
    
    try:
        client = Groq(api_key=settings.groq_api_key)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )
        
        llm_response = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        print(f"\n✅ LLM Response received ({tokens_used} tokens):")
        print("-" * 80)
        print(llm_response)
        print("-" * 80)
        
        # STEP 7: Analyze response
        print_section("STEP 7: RESPONSE ANALYSIS")
        
        response_lower = llm_response.lower()
        
        checks = {
            "Contains RSA": 'rsa' in response_lower or 'rivest' in response_lower,
            "Says 'don't have'": "don't have" in response_lower,
            "Says 'no information'": "no information" in response_lower,
            "Says 'course materials'": "course materials" in response_lower,
            "Mentions encryption": "encryption" in response_lower or "encrypt" in response_lower,
            "Mentions public key": "public key" in response_lower or "public-key" in response_lower
        }
        
        print("\n📊 Response Analysis:")
        for check, result in checks.items():
            status = "✅" if result else "❌"
            print(f"   {status} {check}")
        
    except Exception as e:
        print(f"\n❌ LLM call failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # FINAL DIAGNOSIS
    print_section("🔬 FINAL DIAGNOSIS")
    
    print("\n1️⃣  ChromaDB Search:")
    if len(documents) >= 10:
        print(f"   ✅ Retrieved {len(documents)} documents")
    else:
        print(f"   ⚠️  Only {len(documents)} documents retrieved")
    
    print("\n2️⃣  RSA Content:")
    if rsa_count > 0:
        print(f"   ✅ {rsa_count} documents mention RSA")
    else:
        print(f"   ❌ NO documents mention RSA!")
    
    print("\n3️⃣  Context:")
    if 'rsa' in context.lower():
        print(f"   ✅ RSA is in the context sent to LLM")
    else:
        print(f"   ❌ RSA is NOT in the context!")
    
    print("\n4️⃣  LLM Response:")
    if 'rsa' in llm_response.lower():
        print(f"   ✅ LLM mentioned RSA in response")
    else:
        print(f"   ❌ LLM did NOT mention RSA")
    
    if "don't have" in llm_response.lower():
        print(f"   ⚠️  LLM says it doesn't have the information")
    
    print("\n" + "="*80)
    print("  🎯 RECOMMENDED FIXES")
    print("="*80)
    
    if rsa_count == 0:
        print("\n❌ PROBLEM: No RSA content in ChromaDB!")
        print("\n   FIX OPTIONS:")
        print("   1. Re-upload lecture slides about RSA/Public Key Cryptography")
        print("   2. Check if slides were properly embedded")
        print("   3. Verify document chunking didn't split RSA content badly")
    elif 'rsa' not in context.lower():
        print("\n❌ PROBLEM: RSA docs found but not in context!")
        print("\n   FIX OPTIONS:")
        print("   1. Documents have low similarity scores (not ranking high)")
        print("   2. Increase n_results to retrieve more documents")
        print("   3. Improve query cleaning/embedding matching")
    else:
        print("\n❌ PROBLEM: Context has RSA but LLM not using it!")
        print("\n   FIX OPTIONS:")
        print("   1. System prompt is TOO strict - LLM being over-cautious")
        print("   2. Reduce strictness in system prompt")
        print("   3. Make instructions clearer about using context")
        print("   4. Context might be too long - LLM losing info in middle")


if __name__ == "__main__":
    print("\n🚀 Starting Chat Flow Debug Test...\n")
    asyncio.run(test_chat_flow())
    print("\n✅ Test Complete!\n")
