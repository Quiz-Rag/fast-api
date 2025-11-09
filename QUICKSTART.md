# 🚀 Quick Start - Quiz Generation Feature

## Prerequisites
- ✅ Python virtual environment activated
- ✅ Dependencies installed (`groq`, `sqlalchemy`)
- ✅ ChromaDB with network security content
- ✅ Groq API key (free from https://console.groq.com/)

---

## Step 1: Get Groq API Key (2 minutes)

1. Go to: https://console.groq.com/
2. Sign up (free account)
3. Navigate to: **API Keys** section
4. Click: **Create API Key**
5. Copy the key (starts with `gsk_...`)

---

## Step 2: Configure Environment (1 minute)

```bash
# Navigate to project
cd "/Users/salishkumar/Desktop/uni/third-semester/network security/project/fast-api"

# Create/edit .env file
nano .env
```

Add this line:
```bash
GROQ_API_KEY=gsk_your_actual_key_here
```

Save and exit (Ctrl+X, then Y, then Enter)

---

## Step 3: Start the Server (1 minute)

```bash
# Activate virtual environment (if not already)
source venv/bin/activate

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

You should see:
```
✓ Upload directory: ./storage/uploads
✓ ChromaDB path: ./chroma_db
✓ Database path: ./app/data/quizzes.db
✓ Database tables created
✓ Application started successfully
```

---

## Step 4: Test the API (2 minutes)

### Option A: Using Swagger UI (Recommended)

1. Open browser: http://localhost:8000/docs
2. Find: **POST /api/quiz/generate**
3. Click: **"Try it out"**
4. Use this example:

```json
{
  "topic": "authentication",
  "total_questions": 3,
  "num_mcq": 2,
  "num_blanks": 1,
  "num_descriptive": 0,
  "difficulty": "medium"
}
```

5. Click: **"Execute"**
6. Wait 10-30 seconds for AI generation
7. See your quiz (without answers)!

### Option B: Using Test Script

```bash
# In a new terminal
cd "/Users/salishkumar/Desktop/uni/third-semester/network security/project/fast-api"
source venv/bin/activate
python test_quiz_api.py
```

### Option C: Using cURL

```bash
curl -X POST "http://localhost:8000/api/quiz/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Kerberos",
    "total_questions": 2,
    "num_mcq": 2,
    "num_blanks": 0,
    "num_descriptive": 0,
    "difficulty": "easy"
  }'
```

---

## Step 5: Submit and Grade Quiz

Copy the `quiz_id` from the response, then:

### Using Swagger UI:

1. Find: **POST /api/quiz/submit**
2. Click: **"Try it out"**
3. Use this example (replace question_ids with yours):

```json
{
  "quiz_id": 1,
  "mcq_answers": [
    {"question_id": 1, "selected_option_id": 2},
    {"question_id": 2, "selected_option_id": 1}
  ],
  "blank_answers": [],
  "descriptive_answers": []
}
```

4. Click: **"Execute"**
5. See your score and correct answers!

---

## 🎯 Example Quiz Topics

Try these topics (based on your network security content):
- `"SQL injection"`
- `"Kerberos authentication"`
- `"public key cryptography"`
- `"buffer overflow"`
- `"man in the middle attack"`
- `"SSL/TLS"`
- `"cross-site scripting"`

---

## 📝 API Response Examples

### Quiz Generation (Questions Only)
```json
{
  "quiz_id": 1,
  "topic": "Kerberos",
  "total_questions": 2,
  "mcq_questions": [
    {
      "question_id": 1,
      "question": "What is Kerberos used for?",
      "options": [
        {"option_id": 1, "text": "Database management"},
        {"option_id": 2, "text": "Network authentication"},
        {"option_id": 3, "text": "File encryption"},
        {"option_id": 4, "text": "Web hosting"}
      ]
    }
  ]
}
```

### Grading (Answers Revealed)
```json
{
  "quiz_id": 1,
  "mcq_results": [
    {
      "question_id": 1,
      "your_answer": 2,
      "correct_answer": 2,
      "is_correct": true,
      "your_answer_text": "Network authentication",
      "correct_answer_text": "Network authentication",
      "explanation": "Kerberos is a network authentication protocol..."
    }
  ],
  "mcq_score": 2,
  "total_auto_score": 2,
  "max_auto_score": 2,
  "percentage": 100.0
}
```

---

## 🐛 Troubleshooting

### Server won't start?
```bash
# Check if port 8000 is already in use
lsof -ti:8000 | xargs kill -9

# Then restart
uvicorn app.main:app --reload --port 8000
```

### "GROQ_API_KEY not set" error?
```bash
# Verify .env file exists and has the key
cat .env | grep GROQ_API_KEY

# Should show: GROQ_API_KEY=gsk_...
```

### "No content found for topic" error?
- Your ChromaDB might be empty
- Try a more general topic like "authentication"
- Check if you've uploaded documents to ChromaDB

### AI generation takes too long?
- First generation can take 20-30 seconds
- Subsequent ones are usually faster (10-15 seconds)
- Groq is generally very fast compared to other providers

---

## 📊 What's Happening Behind the Scenes?

1. **Your request** → FastAPI receives topic
2. **ChromaDB search** → Finds relevant content (15 chunks max)
3. **Groq AI** → Generates questions based on content
4. **Database** → Saves quiz WITH answers to SQLite
5. **Response** → Returns quiz WITHOUT answers to you
6. **You submit** → Server compares with stored answers
7. **Grading** → Auto-grades and returns results with explanations

---

## ✅ Success Indicators

You'll know it's working when you see:
- ✅ Server starts without errors
- ✅ Database file created at `app/data/quizzes.db`
- ✅ Quiz generates within 30 seconds
- ✅ Questions returned without answers
- ✅ Submission returns correct answers and score

---

## 🎉 You're Ready!

Your quiz generation API is fully operational!

**Next steps:**
1. ✅ Generate a few test quizzes
2. ✅ Try different topics
3. ✅ Test grading with different answers
4. ✅ Integrate with your frontend

**For detailed documentation:**
- See: `QUIZ_SETUP.md`
- See: `IMPLEMENTATION_SUMMARY.md`

**Happy Quiz Generating! 🚀**
