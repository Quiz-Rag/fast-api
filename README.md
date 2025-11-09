# Quiz Generation & Document Processing API

A comprehensive FastAPI-based system for document processing, AI-powered quiz generation, and automated grading with batch upload support.

## 🎯 Features

### Document Processing
- ✅ **Single File Upload** - Upload PDF/PPTX documents for text extraction and embedding
- 🆕 **Batch Upload** - Upload 2-10 files simultaneously for efficient processing
- ✅ **Async Processing** - Non-blocking uploads with background workers (Celery)
- ✅ **Progress Tracking** - Real-time progress updates for document processing
- ✅ **Vector Storage** - ChromaDB for semantic search capabilities

### Quiz Generation & Management
- ✅ **AI-Powered Quiz Generation** - Create quizzes from uploaded documents using Groq LLM
- ✅ **Multiple Question Types** - MCQ, Fill-in-the-blank, and Descriptive questions
- ✅ **Automatic Grading** - Instant grading for MCQ and fill-in-the-blank questions
- ✅ **Quiz Attempt Tracking** - Store and retrieve user quiz attempts
- ✅ **Analytics Dashboard** - Quiz performance statistics and insights
- ✅ **User Progress Tracking** - Monitor individual user quiz history

### Technical Features
- ✅ **RESTful API** - Clean, well-documented API endpoints
- ✅ **Interactive Documentation** - Swagger UI and ReDoc
- ✅ **Queue Management** - Redis-based job queue with Celery workers
- ✅ **Database Integration** - SQLAlchemy for persistent storage
- ✅ **Error Handling** - Comprehensive error handling and validation

## 📋 Setup Instructions

### Prerequisites

- Python 3.8+ installed on your system
- Redis server installed and running
- OpenAI API key (for embeddings) or Groq API key (for quiz generation)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fast-api
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   ```

3. **Activate virtual environment**
   - **Linux/macOS:**
     ```bash
     source venv/bin/activate
     ```
   - **Windows:**
     ```bash
     venv\Scripts\activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

   Required environment variables:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here  # Optional
   REDIS_URL=redis://localhost:6379/0
   DATABASE_URL=sqlite:///./quiz.db
   ```

## 🚀 Running the Application

The system requires three separate processes to run:

### Terminal 1: Start Redis Server
```bash
redis-server
```

### Terminal 2: Start FastAPI Server
```bash
source venv/bin/activate  # Activate virtual environment
uvicorn app.main:app --reload --port 8000
```

### Terminal 3: Start Celery Worker
```bash
source venv/bin/activate  # Activate virtual environment
celery -A app.workers.celery_app worker --loglevel=info
```

### (Optional) Terminal 4: Start Flower (Celery Monitoring)
```bash
source venv/bin/activate
celery -A app.workers.celery_app flower
# Access at http://localhost:5555
```

### Access Points
- **API Base URL:** http://localhost:8000
- **Interactive Documentation:** http://localhost:8000/docs (Swagger UI)
- **Alternative Documentation:** http://localhost:8000/redoc
- **Flower Dashboard:** http://localhost:5555 (if running)

## 📚 API Endpoints

### Health & Info
- `GET /` - Root endpoint with API information
- `GET /api/health` - Health check with system status

### Document Processing
- `POST /api/start-embedding` - Upload single document (PDF/PPTX)
- 🆕 `POST /api/start-embedding-batch` - **Upload multiple documents (2-10 files)**
- `GET /api/job-status/{job_id}` - Check processing status
- `GET /api/search` - Search documents in ChromaDB
- `GET /api/collections` - List all collections

### Quiz Management
- `POST /api/quiz/generate` - Generate AI-powered quiz
- `POST /api/quiz/submit` - Submit quiz answers for grading
- `GET /api/quiz/{quiz_id}` - Get specific quiz
- `GET /api/quiz/list/all` - List all quizzes

### Quiz Attempt Tracking 🆕
- `GET /api/quiz/{quiz_id}/attempts` - Get all attempts for a quiz
- `GET /api/quiz/attempt/{attempt_id}` - Get specific attempt details
- `GET /api/quiz/user/{user_id}/attempts` - Get user's quiz history

### Analytics 🆕
- `GET /api/quiz/{quiz_id}/analytics` - Get quiz performance statistics

## 📖 Documentation

Detailed API specifications are available in:
- **`API_SPECIFICATION.md`** - Complete API documentation for quiz and document features
- **`BATCH_UPLOAD_API.md`** - Batch upload feature documentation with React examples
- **`QUIZ_SETUP.md`** - Quiz generation and grading setup guide
- **`QUICKSTART.md`** - Quick start guide for common operations

## 🎯 Quick Start Examples

### 1. Upload a Single Document
```bash
curl -X POST "http://localhost:8000/api/start-embedding" \
  -F "file=@document.pdf" \
  -F "collection_name=my_documents"
```

### 2. Upload Multiple Documents (Batch) 🆕
```bash
curl -X POST "http://localhost:8000/api/start-embedding-batch" \
  -F "files=@lecture1.pdf" \
  -F "files=@lecture2.pdf" \
  -F "files=@lecture3.pdf" \
  -F "collection_name=course_materials"
```

### 3. Check Processing Status
```bash
curl "http://localhost:8000/api/job-status/{job_id}"
```

### 4. Generate a Quiz
```bash
curl -X POST "http://localhost:8000/api/quiz/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "SQL Injection",
    "total_questions": 5,
    "num_mcq": 3,
    "num_blanks": 1,
    "num_descriptive": 1,
    "difficulty": "medium",
    "collection_name": "my_documents"
  }'
```

### 5. Submit Quiz Answers
```bash
curl -X POST "http://localhost:8000/api/quiz/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "quiz_id": 1,
    "user_id": "user123",
    "user_name": "John Doe",
    "mcq_answers": [{"question_id": 1, "selected_option_id": 2}],
    "blank_answers": [{"question_id": 4, "answer": "input"}],
    "descriptive_answers": []
  }'
```

## 🏗️ Project Structure

```
fast-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration and settings
│   ├── api/
│   │   ├── routes.py        # Document processing endpoints
│   │   └── quiz_routes.py   # Quiz management endpoints
│   ├── models/
│   │   ├── job.py           # Job/Task models (with batch support)
│   │   ├── database.py      # Quiz database models
│   │   └── quiz_schemas.py  # Quiz request/response schemas
│   ├── services/
│   │   ├── ai_service.py    # Groq AI integration
│   │   ├── chroma_service.py # ChromaDB operations
│   │   ├── embed_utils.py   # Text extraction and chunking
│   │   ├── quiz_service.py  # Quiz generation and grading
│   │   └── queue_manager.py # Redis job queue management
│   ├── workers/
│   │   ├── celery_app.py    # Celery configuration
│   │   └── tasks.py         # Background tasks (single & batch)
│   └── db/
│       └── database.py      # Database connection
├── storage/
│   └── uploads/             # Temporary file storage
├── chroma_db/               # ChromaDB vector storage
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (create from .env.example)
├── README.md               # This file
├── API_SPECIFICATION.md    # Complete API docs
├── BATCH_UPLOAD_API.md     # Batch upload docs
└── QUIZ_SETUP.md           # Quiz setup guide
```

## 🔧 Technology Stack

- **FastAPI** - Modern, fast web framework for APIs
- **Celery** - Distributed task queue for async processing
- **Redis** - Message broker and cache
- **ChromaDB** - Vector database for semantic search
- **SQLAlchemy** - SQL toolkit and ORM
- **Pydantic** - Data validation using Python type annotations
- **Groq** - LLM API for quiz generation
- **LangChain** - Framework for LLM applications
- **PyPDF2** - PDF text extraction
- **python-pptx** - PowerPoint text extraction

## 🎓 Use Cases

### For Educators
- Upload lecture slides and generate quizzes automatically
- Track student performance and quiz analytics
- Create varied question types (MCQ, fill-in-the-blank, descriptive)

### For Students
- Take quizzes and get instant feedback
- Review past attempts and learn from mistakes
- Search through course materials semantically

### For Developers
- Build quiz applications with ready-to-use API
- Integrate document processing into existing systems
- Leverage batch processing for efficient workflows