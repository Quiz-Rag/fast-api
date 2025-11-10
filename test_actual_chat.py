"""
Test the actual chat service with RSA query.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.tutor_service import TutorService
from dotenv import load_dotenv

load_dotenv()

async def test():
    print("="*80)
    print("Testing Actual Chat Service with RSA Query")
    print("="*80)
    
    tutor = TutorService()
    
    question = "what is asymmetric encryption"
    
    print(f"\n📝 Question: {question}")
    print(f"\n🔍 Retrieving context...")
    
    # Get context
    context = await tutor.retrieve_context(question, chat_history=[])
    
    print(f"\n📊 Context Retrieved:")
    print(f"   - Length: {len(context)} characters")
    print(f"   - Words: {len(context.split())} words")
    
    # Check RSA mentions
    rsa_count = context.lower().count('rsa') + context.lower().count('rivest')
    print(f"   - RSA mentions: {rsa_count}")
    
    print(f"\n📄 Context Preview (first 1000 chars):")
    print("-" * 80)
    print(context[:1000])
    print("...")
    print("-" * 80)
    
    if rsa_count > 0:
        print(f"\n✅ Context contains RSA information")
        # Find RSA context
        lower_context = context.lower()
        rsa_pos = lower_context.find('rsa')
        if rsa_pos >= 0:
            start = max(0, rsa_pos - 200)
            end = min(len(context), rsa_pos + 300)
            print(f"\n📌 RSA Context Extract:")
            print("-" * 80)
            print(context[start:end])
            print("-" * 80)
    else:
        print(f"\n❌ Context does NOT contain RSA information!")
    
    print(f"\n💬 Generating LLM response...")
    
    # Build messages
    system_prompt = tutor.build_system_prompt()
    user_message = tutor.build_context_message(context, question)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    # Generate response
    response = await tutor.ai.generate_text(
        messages=messages,
        temperature=0.7,
        max_tokens=300
    )
    
    print(f"\n✅ LLM Response:")
    print("=" * 80)
    print(response)
    print("=" * 80)
    
    # Analyze
    print(f"\n🔍 Analysis:")
    if "don't have" in response.lower() or "not mentioned" in response.lower():
        print("   ❌ LLM says no information available")
    else:
        print("   ✅ LLM provided an answer!")

if __name__ == "__main__":
    asyncio.run(test())
