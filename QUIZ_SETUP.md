# Quiz Generation Feature - Setup Guide

## 🎯 What's New

The API now includes AI-powered quiz generation using Groq! Generate quizzes on any network security topic with:
- ✅ Multiple Choice Questions (MCQs)
- ✅ Fill-in-the-Blank Questions
- ✅ Descriptive Questions
- ✅ Automatic grading for MCQ and blanks
- ✅ Stored in SQLite database
- ✅ Answers hidden from frontend until submission

---

## 📦 New Dependencies

The following packages have been added:
- `groq>=0.4.0` - AI quiz generation
- `sqlalchemy>=2.0.0` - Database ORM

---

## 🔑 Getting Groq API Key (FREE)

1. **Sign up at Groq**: https://console.groq.com/
2. **Go to API Keys section**
3. **Create new API key**
4. **Copy the key** (starts with `gsk_...`)

---

## ⚙️ Setup Instructions

### 1. Add Groq API Key to .env

Create or update your `.env` file:

```bash
# Copy from example
cp .env.example .env

# Edit .env and add your Groq API key
nano .env
```

Add this line with your actual key:
```
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
```

### 2. Verify Installation

Dependencies should already be installed. If not:
```bash
source venv/bin/activate
pip install groq sqlalchemy
```

### 3. Run the Application

```bash
# Activate virtual environment
source venv/bin/activate

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

The database will be automatically created at `app/data/quizzes.db`

---

## 📚 API Endpoints

### Generate Quiz
```bash
POST /api/quiz/generate
```

**Request:**
```json
{
  "topic": "SQL Injection",
  "total_questions": 5,
  "num_mcq": 3,
  "num_blanks": 1,
  "num_descriptive": 1,
  "difficulty": "medium",
  "collection_name": "lecture_23_slides"
}
```

**Response (NO ANSWERS):**
```json
{
  "quiz_id": 1,
  "topic": "SQL Injection",
  "total_questions": 5,
  "mcq_questions": [
    {
      "question_id": 1,
      "question": "What is SQL Injection?",
      "options": [
        {"option_id": 1, "text": "A type of malware"},
        {"option_id": 2, "text": "A web vulnerability"},
        {"option_id": 3, "text": "A database feature"},
        {"option_id": 4, "text": "A network protocol"}
      ]
    }
  ],
  "blank_questions": [...],
  "descriptive_questions": [...]
}
```

### Submit Quiz for Grading
```bash
POST /api/quiz/submit
```

**Request:**
```json
{
  "quiz_id": 1,
  "mcq_answers": [
    {"question_id": 1, "selected_option_id": 2}
  ],
  "blank_answers": [
    {"question_id": 4, "answer": "input"}
  ],
  "descriptive_answers": [
    {"question_id": 5, "answer": "Prepared statements..."}
  ]
}
```

**Response (WITH ANSWERS & SCORE):**
```json
{
  "quiz_id": 1,
  "topic": "SQL Injection",
  "mcq_results": [
    {
      "question_id": 1,
      "question": "What is SQL Injection?",
      "your_answer": 2,
      "your_answer_text": "A web vulnerability",
      "correct_answer": 2,
      "correct_answer_text": "A web vulnerability",
      "is_correct": true,
      "explanation": "SQL Injection is a web security vulnerability..."
    }
  ],
  "mcq_score": 3,
  "blank_score": 1,
  "total_auto_score": 4,
  "max_auto_score": 4,
  "percentage": 100.0
}
```

### Get Quiz by ID
```bash
GET /api/quiz/{quiz_id}
```

### List All Quizzes
```bash
GET /api/quiz/list/all?skip=0&limit=10
```

---

## 🧪 Testing

### Using cURL

**Generate Quiz:**
```bash
curl -X POST "http://localhost:8000/api/quiz/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Kerberos Authentication",
    "total_questions": 3,
    "num_mcq": 2,
    "num_blanks": 1,
    "num_descriptive": 0,
    "difficulty": "medium"
  }'
```

**Submit Quiz:**
```bash
curl -X POST "http://localhost:8000/api/quiz/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "quiz_id": 1,
    "mcq_answers": [
      {"question_id": 1, "selected_option_id": 2}
    ],
    "blank_answers": [
      {"question_id": 3, "answer": "ticket"}
    ]
  }'
```

### Using Swagger UI

1. Go to: http://localhost:8000/docs
2. Find the `/api/quiz/generate` endpoint
3. Click "Try it out"
4. Fill in the request body
5. Click "Execute"

---

## 🗄️ Database Structure

### Tables Created:

**quizzes**
- `id` - Primary key
- `topic` - Quiz topic
- `total_questions`, `num_mcq`, `num_blanks`, `num_descriptive`
- `difficulty` - easy/medium/hard
- `created_at` - Timestamp

**questions**
- `id` - Primary key
- `quiz_id` - Foreign key to quizzes
- `question_type` - MCQ/BLANK/DESCRIPTIVE
- `question_text` - The question
- `option_a/b/c/d` - MCQ options (with IDs 1-4)
- `correct_option_id` - Correct answer (1-4)
- `correct_answer` - Blank answer
- `sample_answer`, `key_points` - Descriptive answers
- `explanation` - Explanation for all types

---

## 🔒 Security Features

✅ **Answers stored server-side only**  
✅ **Frontend never sees correct answers until submission**  
✅ **Can't cheat by inspecting network**  
✅ **Grading happens server-side**  
✅ **Option IDs prevent answer manipulation**

---

## 🐛 Troubleshooting

### Error: "GROQ_API_KEY not set"
- Make sure `.env` file exists
- Check that `GROQ_API_KEY=...` is set correctly
- Restart the application after updating .env

### Error: "No content found for topic"
- Make sure you have uploaded documents to ChromaDB
- Check that the topic exists in your uploaded content
- Try a more general topic (e.g., "authentication" instead of "oauth2")

### Error: "Failed to parse AI response"
- The AI model might be having issues
- Try again (sometimes it works on retry)
- Check your Groq API key is valid

### Database locked
- Only one process can write to SQLite at a time
- Make sure you don't have multiple instances running

---

## 📊 How It Works

1. **User requests quiz** → API receives topic and question requirements
2. **Content retrieval** → Searches ChromaDB for relevant content on topic
3. **AI generation** → Groq AI generates questions based on content
4. **Database storage** → Quiz and answers saved to SQLite
5. **Response** → Returns quiz WITHOUT answers to frontend
6. **User submits** → API compares answers with stored correct answers
7. **Grading** → Auto-grades MCQ/blanks, returns results with explanations

---

## 🎓 Example Topics

Based on network security course content:
- "Kerberos authentication"
- "SQL injection"
- "Cross-site scripting"
- "Buffer overflow"
- "Man in the middle attack"
- "Public key cryptography"
- "Digital signatures"
- "SSL/TLS"

---

## 📝 Notes

- Maximum 20 questions per quiz (configurable in config.py)
- Retrieves top 15 content chunks from ChromaDB (configurable)
- Groq model: `llama-3.1-70b-versatile` (fast and free)
- Database path: `app/data/quizzes.db`
- Supports pagination for quiz listing

---

## 🚀 Next Steps

1. ✅ Get Groq API key
2. ✅ Add to .env file
3. ✅ Start the application
4. ✅ Test quiz generation via Swagger UI
5. ✅ Integrate with your frontend

**Happy Quiz Generating! 🎉**
