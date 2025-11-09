# 📦 Installation & Setup Guide

Complete guide to install and run the Network Security Quiz & Document Processing API.

---

## 📋 Prerequisites

Before you begin, ensure you have:

- ✅ **Python 3.9 or higher**
- ✅ **pip** (Python package manager)
- ✅ **Redis Server**
- ✅ **Git** (for cloning the repository)
- ✅ **Groq API Key** (free - get from https://console.groq.com/)

---

## 🚀 Installation Steps

### Step 1: Clone the Repository

```bash
git clone https://github.com/Quiz-Rag/fast-api.git
cd fast-api
```

---

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**What gets installed:**
- FastAPI & Uvicorn (API server)
- Celery & Redis (job queue)
- SQLAlchemy (database)
- ChromaDB (vector storage)
- Groq SDK (AI quiz generation)
- PyPDF2, python-pptx (document processing)
- LangChain (text processing)
- And more...

**Expected output:**
```
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 celery-5.3.4 ...
```

---

### Step 3: Install and Start Redis

Redis is required for the job queue system.

#### **macOS** (using Homebrew):
```bash
# Install Redis
brew install redis

# Start Redis server
brew services start redis

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

#### **Ubuntu/Debian**:
```bash
# Install Redis
sudo apt update
sudo apt install redis-server

# Start Redis
sudo systemctl start redis

# Enable auto-start on boot
sudo systemctl enable redis

# Verify
redis-cli ping
```

#### **Windows**:
```bash
# Download Redis from: https://github.com/microsoftarchive/redis/releases
# Or use WSL2 and follow Linux instructions

# Alternative: Use Docker
docker run -d -p 6379:6379 redis:alpine
```

#### **Docker** (any platform):
```bash
docker run -d --name redis -p 6379:6379 redis:alpine
```

---

### Step 4: Get Groq API Key

The API uses Groq (free) for AI-powered quiz generation.

1. Visit: **https://console.groq.com/**
2. Sign up (free account)
3. Go to **API Keys** section
4. Click **Create API Key**
5. Copy the key (starts with `gsk_...`)

---

### Step 5: Configure Environment

The `.env` file is already configured. Just update your Groq API key:

```bash
# Open .env file
nano .env   # or use any text editor
```

**Update this line:**
```env
GROQ_API_KEY=gsk_YOUR_ACTUAL_API_KEY_HERE
```

**Other settings (already configured):**
- ✅ Database path: `./app/data/quizzes.db`
- ✅ ChromaDB path: `./chroma_db`
- ✅ Redis URL: `redis://localhost:6379/0`
- ✅ Max file size: 50MB
- ✅ Allowed types: PDF, PPTX

Save and close the file.

---

### Step 6: Create Required Directories

```bash
# Create necessary directories
mkdir -p ./app/data
mkdir -p ./chroma_db
mkdir -p ./storage/uploads
```

---

## ✅ Verify Installation

Check that everything is installed correctly:

```bash
# Check Python version
python --version
# Should be 3.9 or higher

# Check pip packages
pip list | grep fastapi
pip list | grep celery
pip list | grep chromadb

# Check Redis
redis-cli ping
# Should return: PONG
```

---

## 🎯 Running the Application

You need **3 terminal windows** running simultaneously.

### Terminal 1️⃣: Start Redis Server

```bash
# If not already running
redis-server

# OR (if using Homebrew on macOS)
brew services start redis

# OR (if using Docker)
docker start redis
```

**Expected output:**
```
                _._                                                  
           _.-``__ ''-._                                             
      _.-``    `.  `_.  ''-._           Redis 7.x.x (...)
  .-`` .-```.  ```\/    _.,_ ''-._                                  
 (    '      ,       .-`  | `,    )     Running in standalone mode
 |`-._`-...-` __...-.``-._|'` _.-'|     Port: 6379
 |    `-._   `._    /     _.-'    |     PID: xxxxx
  `-._    `-._  `-./  _.-'    _.-'                                   
 |`-._`-._    `-.__.-'    _.-'_.-'|                                  
 |    `-._`-._        _.-'_.-'    |           https://redis.io       
  `-._    `-._`-.__.-'_.-'    _.-'                                   
 |`-._`-._    `-.__.-'    _.-'_.-'|                                  
 |    `-._`-._        _.-'_.-'    |                                  
  `-._    `-._`-.__.-'_.-'    _.-'                                   
      `-._    `-.__.-'    _.-'                                       
          `-._        _.-'                                           
              `-.__.-'                                               

Ready to accept connections
```

---

### Terminal 2️⃣: Start FastAPI Server

```bash
# Navigate to project directory
cd fast-api

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Will watch for changes in these directories: ['/Users/...']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Server URLs:**
- 🌐 API: http://localhost:8000
- 📚 Swagger Docs: http://localhost:8000/docs
- 📖 ReDoc: http://localhost:8000/redoc

---

### Terminal 3️⃣: Start Celery Worker

```bash
# Navigate to project directory
cd fast-api

# Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info
```

**Expected output:**
```
 -------------- celery@YourMachine v5.3.4 (emerald-rush)
--- ***** ----- 
-- ******* ---- Darwin-23.x.x-arm64-arm-64bit 2025-11-09 ...
- *** --- * --- 
- ** ---------- [config]
- ** ---------- .> app:         app.workers.celery_app:0x...
- ** ---------- .> transport:   redis://localhost:6379/0
- ** ---------- .> results:     redis://localhost:6379/1
- *** --- * --- .> concurrency: 8 (prefork)
-- ******* ---- .> task events: OFF
--- ***** ----- 
 -------------- [queues]
                .> celery           exchange=celery(direct) key=celery

[tasks]
  . app.workers.tasks.process_document_task
  . app.workers.tasks.process_batch_embedding_task

[2025-11-09 ...] [MainProcess] mingle: searching for neighbors
[2025-11-09 ...] [MainProcess] mingle: all alone
[2025-11-09 ...] [MainProcess] celery@YourMachine ready.
```

---

## 🧪 Test the Installation

### Test 1: Check API Health

```bash
curl http://localhost:8000/api/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-09T...",
  "redis": "connected",
  "chroma_db_path": "./chroma_db",
  "allowed_file_types": ["pdf", "pptx"],
  "max_file_size_mb": 50.0
}
```

---

### Test 2: Upload a Document

```bash
# Create a test file
echo "Network security is the practice of protecting networks from attacks." > test.txt

# Upload it
curl -X POST "http://localhost:8000/api/start-embedding" \
  -F "file=@test.txt" \
  -F "collection_name=test_collection"
```

**Expected response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Job created successfully. Use job_id to check status."
}
```

**Check job status:**
```bash
curl "http://localhost:8000/api/job-status/550e8400-e29b-41d4-a716-446655440000"
```

---

### Test 3: Generate a Quiz

```bash
curl -X POST "http://localhost:8000/api/quiz/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "network security",
    "total_questions": 3,
    "num_mcq": 2,
    "num_blanks": 1,
    "num_descriptive": 0,
    "difficulty": "easy"
  }'
```

**Expected response:**
```json
{
  "quiz_id": 1,
  "topic": "network security",
  "total_questions": 3,
  "mcq_questions": [...],
  "blank_questions": [...],
  "created_at": "2025-11-09T..."
}
```

---

### Test 4: Batch Upload

```bash
# Create multiple test files
echo "Document 1 content" > doc1.txt
echo "Document 2 content" > doc2.txt
echo "Document 3 content" > doc3.txt

# Upload batch
curl -X POST "http://localhost:8000/api/start-embedding-batch" \
  -F "files=@doc1.txt" \
  -F "files=@doc2.txt" \
  -F "files=@doc3.txt" \
  -F "collection_name=batch_test"
```

---

## ✅ Installation Complete!

If all tests pass, your installation is successful! 🎉

**You can now:**
- ✅ Upload documents (PDF, PPTX)
- ✅ Generate AI-powered quizzes
- ✅ Batch upload multiple files
- ✅ Track quiz attempts
- ✅ View analytics

---

## 🛑 Stopping the Services

```bash
# Terminal 1 - Stop Redis
Ctrl + C
# Or if using Homebrew:
brew services stop redis

# Terminal 2 - Stop FastAPI
Ctrl + C

# Terminal 3 - Stop Celery
Ctrl + C
```

---

## 🔧 Troubleshooting

### Problem: Redis Connection Error

**Error:** `Error connecting to Redis`

**Solution:**
```bash
# Check if Redis is running
redis-cli ping

# If not running, start it
redis-server
# or
brew services start redis
```

---

### Problem: Port 8000 Already in Use

**Error:** `Address already in use`

**Solution:**
```bash
# Kill the process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use a different port
uvicorn app.main:app --reload --port 8001
```

---

### Problem: Groq API Key Error

**Error:** `401 Unauthorized` or `Invalid API key`

**Solution:**
1. Check your API key in `.env` file
2. Make sure it starts with `gsk_`
3. Get a new key from https://console.groq.com/
4. Restart the FastAPI server after updating

---

### Problem: ModuleNotFoundError

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or install specific package
pip install fastapi uvicorn
```

---

### Problem: Celery Worker Not Processing

**Error:** Jobs stay in "queued" status

**Solution:**
1. Check Celery worker is running (Terminal 3)
2. Check Redis is running: `redis-cli ping`
3. Restart Celery worker:
   ```bash
   Ctrl + C
   celery -A app.workers.celery_app worker --loglevel=info --pool=solo
   ```

---

### Problem: Database Permission Error

**Error:** `Permission denied: './app/data/quizzes.db'`

**Solution:**
```bash
# Create directory with proper permissions
mkdir -p ./app/data
chmod 755 ./app/data

# Remove and recreate database
rm -f ./app/data/quizzes.db
# Database will be recreated on next server start
```

---

## 📚 Next Steps

1. **Read the API Documentation:**
   - Open http://localhost:8000/docs in your browser
   - Or read `API_SPECIFICATION.md`

2. **Try Batch Upload:**
   - Read `BATCH_UPLOAD_API.md`
   - Upload multiple PDFs/PowerPoints

3. **Generate Quizzes:**
   - Read `QUIZ_SETUP.md`
   - Create AI-powered quizzes from your documents

4. **Integrate with Frontend:**
   - Use the TypeScript examples in documentation
   - Check `API_SPECIFICATION.md` for all endpoints

---

## 💡 Tips

- **Development Mode:** The `--reload` flag auto-restarts the server on code changes
- **Monitoring:** Use http://localhost:8000/docs to test APIs interactively
- **Logs:** Check terminal windows for detailed logs and errors
- **Database:** SQLite database file is at `./app/data/quizzes.db`
- **Vector Store:** ChromaDB data is stored in `./chroma_db/`

---

## 🆘 Need Help?

- **API Docs:** http://localhost:8000/docs
- **GitHub Issues:** https://github.com/Quiz-Rag/fast-api/issues
- **Documentation:** Check all `.md` files in the project root

---

**Installation completed successfully? Start building! 🚀**
