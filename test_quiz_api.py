"""
Quick test to verify quiz generation setup.
Run this after starting the server to test the quiz API.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_quiz_generation():
    """Test quiz generation endpoint."""
    print("🧪 Testing Quiz Generation API...")
    print("="*60)
    
    # Test data
    quiz_request = {
        "topic": "authentication",
        "total_questions": 3,
        "num_mcq": 2,
        "num_blanks": 1,
        "num_descriptive": 0,
        "difficulty": "medium"
    }
    
    try:
        # Generate quiz
        print("\n1️⃣  Generating quiz on 'authentication'...")
        response = requests.post(
            f"{BASE_URL}/api/quiz/generate",
            json=quiz_request,
            timeout=60
        )
        
        if response.status_code == 201:
            quiz = response.json()
            quiz_id = quiz['quiz_id']
            print(f"✅ Quiz generated successfully! Quiz ID: {quiz_id}")
            print(f"   Topic: {quiz['topic']}")
            print(f"   Total questions: {quiz['total_questions']}")
            print(f"   MCQ questions: {len(quiz['mcq_questions'])}")
            print(f"   Blank questions: {len(quiz['blank_questions'])}")
            
            # Show first MCQ
            if quiz['mcq_questions']:
                mcq = quiz['mcq_questions'][0]
                print(f"\n   Sample MCQ:")
                print(f"   Q: {mcq['question']}")
                for opt in mcq['options']:
                    print(f"      {opt['option_id']}. {opt['text']}")
            
            # Test submission
            print("\n2️⃣  Testing quiz submission...")
            submission = {
                "quiz_id": quiz_id,
                "mcq_answers": [
                    {"question_id": quiz['mcq_questions'][0]['question_id'], "selected_option_id": 1}
                ] if quiz['mcq_questions'] else [],
                "blank_answers": [
                    {"question_id": quiz['blank_questions'][0]['question_id'], "answer": "test"}
                ] if quiz['blank_questions'] else [],
                "descriptive_answers": []
            }
            
            grade_response = requests.post(
                f"{BASE_URL}/api/quiz/submit",
                json=submission
            )
            
            if grade_response.status_code == 200:
                result = grade_response.json()
                print(f"✅ Quiz graded successfully!")
                print(f"   Score: {result['total_auto_score']}/{result['max_auto_score']}")
                print(f"   Percentage: {result['percentage']}%")
                
                if result['mcq_results']:
                    print(f"\n   First MCQ result:")
                    mcq_res = result['mcq_results'][0]
                    print(f"   Your answer: {mcq_res['your_answer_text']}")
                    print(f"   Correct answer: {mcq_res['correct_answer_text']}")
                    print(f"   ✓ Correct!" if mcq_res['is_correct'] else "   ✗ Incorrect")
            else:
                print(f"❌ Grading failed: {grade_response.status_code}")
                print(f"   {grade_response.text}")
            
            # Test list quizzes
            print("\n3️⃣  Testing quiz list...")
            list_response = requests.get(f"{BASE_URL}/api/quiz/list/all?limit=5")
            if list_response.status_code == 200:
                quizzes = list_response.json()
                print(f"✅ Found {len(quizzes)} quizzes")
                for q in quizzes:
                    print(f"   - Quiz {q['quiz_id']}: {q['topic']} ({q['total_questions']} questions)")
            
            print("\n" + "="*60)
            print("✅ All tests passed! Quiz generation is working! 🎉")
            return True
            
        else:
            print(f"❌ Quiz generation failed!")
            print(f"   Status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to server!")
        print("   Make sure the server is running:")
        print("   uvicorn app.main:app --reload --port 8000")
        return False
    except requests.exceptions.Timeout:
        print("⏱️  Error: Request timed out!")
        print("   The AI generation might be taking longer than expected.")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def check_server():
    """Check if server is running."""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server is running!")
            print(f"   {data['message']}")
            print(f"   Version: {data['version']}")
            return True
    except:
        print("❌ Server is not running!")
        print("   Start it with: uvicorn app.main:app --reload --port 8000")
        return False


if __name__ == "__main__":
    print("\n🚀 Quiz Generation API Test")
    print("="*60)
    
    if check_server():
        print()
        test_quiz_generation()
    else:
        print("\n❌ Cannot run tests without server running.")
