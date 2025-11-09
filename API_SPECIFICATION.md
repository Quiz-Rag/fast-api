# Quiz Generation API - Complete Specification# Quiz API - Complete Integration Specification# Document Processing API - Queue-Based Architecture



**Base URL:** `http://localhost:8000`  

**API Version:** 1.0.0  

**Last Updated:** November 9, 2025**Base URL:** `http://localhost:8000`  ## Base Information



---**Version:** 1.0.0  



## 📋 Table of Contents**Updated:** November 9, 2025**Base URL**: `http://localhost:8000`



1. [Authentication](#authentication)**API Prefix**: `/api`

2. [Quiz Generation](#quiz-generation)

3. [Quiz Submission & Grading](#quiz-submission--grading)Pass this document to your LLM for frontend integration.**Documentation**: `http://localhost:8000/docs` (Interactive Swagger UI)

4. [Quiz Management](#quiz-management)

5. [Attempt Tracking](#attempt-tracking)**Version**: 1.0.0

6. [Analytics](#analytics)

7. [Error Handling](#error-handling)---

8. [Data Models](#data-models)

---

---

## 📋 Endpoints Summary

## 🔐 Authentication

## Architecture Overview

**Current Status:** No authentication required (optional user_id/user_name can be provided)

| Endpoint | Method | Description |

**Future:** Can be extended to support JWT tokens or session-based authentication.

|----------|--------|-------------|This API uses an **asynchronous queue-based architecture** with Celery + Redis:

---

| `/api/quiz/generate` | POST | Generate new quiz |

## 🎯 Quiz Generation

| `/api/quiz/submit` | POST | Submit & grade quiz |1. **Upload File** → Returns job_id immediately (non-blocking)

### 1. Generate New Quiz

| `/api/quiz/{quiz_id}` | GET | Get quiz by ID |2. **Background Worker** → Processes job asynchronously

**Endpoint:** `POST /api/quiz/generate`

| `/api/quiz/list/all` | GET | List all quizzes |3. **Poll Status** → Check progress and get results

**Description:** Generates a new quiz on a specific topic using AI. Retrieves relevant content from ChromaDB and creates questions based on user specifications.



**Request Body:**

```json---```

{

  "topic": "string",              // Required: Topic for the quiz (e.g., "SQL Injection")Client → POST /api/start-embedding → Returns job_id

  "total_questions": 5,           // Required: Total number of questions (1-20)

  "num_mcq": 3,                   // Required: Number of MCQ questions## 🔌 1. Generate Quiz                                           ↓

  "num_blanks": 1,                // Required: Number of fill-in-the-blank questions

  "num_descriptive": 1,           // Required: Number of descriptive questions                                      (Queue Job)

  "difficulty": "medium",         // Optional: "easy", "medium", or "hard" (default: "medium")

  "collection_name": "string"     // Optional: Specific ChromaDB collection to search**POST** `/api/quiz/generate`                                           ↓

}

```                              Celery Worker Processes



**Validation Rules:**Creates a new quiz with AI-generated questions.                                           ↓

- `total_questions` must equal `num_mcq + num_blanks + num_descriptive`

- `total_questions` max: 20Client → GET /api/job-status/{id} → Get Status/Progress

- All question counts must be >= 0

**Request:**```

**Response:** `201 Created`

```json```json

{

  "quiz_id": 1,{---

  "topic": "SQL Injection",

  "total_questions": 5,  "topic": "SQL injection",

  "num_mcq": 3,

  "num_blanks": 1,  "total_questions": 5,## API Endpoints

  "num_descriptive": 1,

  "difficulty": "medium",  "num_mcq": 3,

  "mcq_questions": [

    {  "num_blanks": 1,### 1. Start Embedding (Upload & Queue)

      "question_id": 1,

      "question": "What is SQL Injection?",  "num_descriptive": 1,

      "options": [

        {"option_id": 1, "text": "A type of malware"},  "difficulty": "medium"#### `POST /api/start-embedding`

        {"option_id": 2, "text": "A web vulnerability"},

        {"option_id": 3, "text": "A database feature"},}

        {"option_id": 4, "text": "A network protocol"}

      ]```Upload a document file and start the embedding process. **Returns immediately** with a job ID.

    }

  ],

  "blank_questions": [

    {**Response (201):****Request**:

      "question_id": 4,

      "question": "SQL Injection exploits vulnerabilities in _____ validation."```json- **Content-Type**: `multipart/form-data`

    }

  ],{- **Parameters**:

  "descriptive_questions": [

    {  "quiz_id": 1,

      "question_id": 5,

      "question": "Explain how prepared statements prevent SQL injection."  "topic": "SQL injection",| Parameter | Type | Required | Description |

    }

  ],  "total_questions": 5,|-----------|------|----------|-------------|

  "created_at": "2025-11-09T00:00:00"

}  "num_mcq": 3,| `file` | File | ✅ Yes | PDF or PPTX document to process |

```

  "num_blanks": 1,| `collection_name` | string | ❌ No | ChromaDB collection name (defaults to filename without extension) |

**Note:** ⚠️ **Answers are NOT included in the response** (stored server-side only)

  "num_descriptive": 1,

**Error Responses:**

- `400 Bad Request` - Invalid request (validation failed)  "difficulty": "medium",**cURL Example**:

- `500 Internal Server Error` - AI generation failed or no content found

  "mcq_questions": [```bash

**Example (cURL):**

```bash    {curl -X POST "http://localhost:8000/api/start-embedding" \

curl -X POST "http://localhost:8000/api/quiz/generate" \

  -H "Content-Type: application/json" \      "question_id": 1,  -F "file=@document.pdf" \

  -d '{

    "topic": "Kerberos Authentication",      "question": "What is SQL injection?",  -F "collection_name=my_documents"

    "total_questions": 3,

    "num_mcq": 2,      "options": [```

    "num_blanks": 1,

    "num_descriptive": 0,        {"option_id": 1, "text": "A type of malware"},

    "difficulty": "easy"

  }'        {"option_id": 2, "text": "A web vulnerability"},**JavaScript/TypeScript Example**:

```

        {"option_id": 3, "text": "A database feature"},```typescript

---

        {"option_id": 4, "text": "A network protocol"}const formData = new FormData();

## ✅ Quiz Submission & Grading

      ]formData.append('file', fileObject);

### 2. Submit Quiz for Grading

    }formData.append('collection_name', 'my_documents'); // Optional

**Endpoint:** `POST /api/quiz/submit`

  ],

**Description:** Submits quiz answers, grades them automatically (MCQ & blanks), and saves the attempt to the database.

  "blank_questions": [const response = await fetch('http://localhost:8000/api/start-embedding', {

**Request Body:**

```json    {  method: 'POST',

{

  "quiz_id": 1,                       // Required: Quiz ID to submit      "question_id": 4,  body: formData,

  "user_id": "user123",               // Optional: User identifier (for tracking)

  "user_name": "John Doe",            // Optional: User display name      "question": "SQL injection exploits _____ validation."});

  "time_taken_seconds": 120,          // Optional: Time taken to complete (in seconds)

  "mcq_answers": [    }

    {

      "question_id": 1,  ],const data = await response.json();

      "selected_option_id": 2         // Must be 1, 2, 3, or 4

    }  "descriptive_questions": [console.log(data.job_id); // Save this to check status later

  ],

  "blank_answers": [    {```

    {

      "question_id": 4,      "question_id": 5,

      "answer": "input"               // Text answer

    }      "question": "Explain how prepared statements prevent SQL injection."**Success Response**: `202 Accepted`

  ],

  "descriptive_answers": [    }```json

    {

      "question_id": 5,  ],{

      "answer": "Prepared statements separate SQL code from data..."

    }  "created_at": "2025-11-09T12:34:56"  "job_id": "550e8400-e29b-41d4-a716-446655440000",

  ]

}}  "status": "queued",

```

```  "message": "Job created successfully. Use job_id to check status."

**Response:** `200 OK`

```json}

{

  "attempt_id": 1,                    // NEW: Unique attempt ID**⚠️ Important:** Response does NOT include answers (security feature).```

  "quiz_id": 1,

  "topic": "SQL Injection",

  "total_questions": 3,

  "mcq_results": [---**Error Responses**:

    {

      "question_id": 1,

      "question": "What is SQL Injection?",

      "your_answer": 2,## 🔌 2. Submit Quiz**400 Bad Request** - Invalid file type

      "your_answer_text": "A web vulnerability",

      "correct_answer": 2,```json

      "correct_answer_text": "A web vulnerability",

      "is_correct": true,**POST** `/api/quiz/submit`{

      "explanation": "SQL Injection is indeed a web application vulnerability..."

    }  "detail": "File type not allowed. Allowed types: pdf, pptx"

  ],

  "blank_results": [Submit answers and get grading results.}

    {

      "question_id": 4,```

      "question": "SQL Injection exploits vulnerabilities in _____ validation.",

      "your_answer": "input",**Request:**

      "correct_answer": "input",

      "is_correct": true,```json**500 Internal Server Error** - Job creation failed

      "explanation": "Input validation is crucial..."

    }{```json

  ],

  "descriptive_results": [  "quiz_id": 1,{

    {

      "question_id": 5,  "mcq_answers": [  "detail": "Error creating job: [error message]"

      "question": "Explain how prepared statements prevent SQL injection.",

      "your_answer": "Prepared statements separate SQL code from data...",    {"question_id": 1, "selected_option_id": 2}}

      "sample_answer": "Prepared statements use parameterized queries...",

      "key_points": [  ],```

        "Separates code from data",

        "Uses placeholders",  "blank_answers": [

        "Prevents code injection"

      ],    {"question_id": 4, "answer": "input"}---

      "explanation": "Good answer covering key concepts"

    }  ],

  ],

  "mcq_score": 1,  "descriptive_answers": [### 2. Check Job Status

  "blank_score": 1,

  "total_auto_score": 2,    {"question_id": 5, "answer": "Prepared statements separate SQL code..."}

  "max_auto_score": 2,

  "percentage": 100.0,  ]#### `GET /api/job-status/{job_id}`

  "time_taken_seconds": 120,          // NEW: Time taken

  "submitted_at": "2025-11-09T00:00:00"  // NEW: Submission timestamp}

}

``````Check the processing status and progress of a job.



**Auto-Grading:**

- ✅ **MCQ:** Exact match on `selected_option_id`

- ✅ **Blanks:** Case-insensitive, whitespace-trimmed comparison**Response (200):****Parameters**:

- ⚠️ **Descriptive:** Not auto-graded (returns sample answer for manual review)

```json- **Path Parameter**: `job_id` (UUID string)

---

{

## 📚 Quiz Management

  "quiz_id": 1,**cURL Example**:

### 3. Get Quiz by ID

  "topic": "SQL injection",```bash

**Endpoint:** `GET /api/quiz/{quiz_id}`

  "total_questions": 5,curl "http://localhost:8000/api/job-status/550e8400-e29b-41d4-a716-446655440000"

**Response:** `200 OK` - Returns quiz WITHOUT answers

  "mcq_results": [```

### 4. List All Quizzes

    {

**Endpoint:** `GET /api/quiz/list/all?skip=0&limit=10`

      "question_id": 1,**JavaScript/TypeScript Example**:

**Response:** Array of quiz summaries

      "question": "What is SQL injection?",```typescript

---

      "your_answer": 2,const jobId = "550e8400-e29b-41d4-a716-446655440000";

## 📊 Attempt Tracking (NEW!)

      "your_answer_text": "A web vulnerability",

### 5. Get Quiz Attempts

      "correct_answer": 2,const response = await fetch(`http://localhost:8000/api/job-status/${jobId}`);

**Endpoint:** `GET /api/quiz/{quiz_id}/attempts?skip=0&limit=10`

      "correct_answer_text": "A web vulnerability",const job = await response.json();

**Description:** Get all attempts for a specific quiz with scores and user info.

      "is_correct": true,

**Response:** `200 OK`

```json      "explanation": "SQL injection is a web vulnerability..."console.log(`Status: ${job.status}`);

[

  {    }console.log(`Progress: ${job.progress?.percentage}%`);

    "attempt_id": 2,

    "quiz_id": 4,  ],```

    "user_id": "user456",

    "user_name": "Another User",  "blank_results": [

    "mcq_score": 2,

    "blank_score": 1,    {**Response Examples**:

    "total_score": 3,

    "max_score": 3,      "question_id": 4,

    "percentage": 100.0,

    "time_taken_seconds": 90,      "question": "SQL injection exploits _____ validation.",#### Status: QUEUED

    "submitted_at": "2025-11-09T00:05:00"

  }      "your_answer": "input",```json

]

```      "correct_answer": "input",{



### 6. Get Attempt Detail      "is_correct": true,  "job_id": "550e8400-e29b-41d4-a716-446655440000",



**Endpoint:** `GET /api/quiz/attempt/{attempt_id}`      "explanation": "Input validation is crucial..."  "status": "queued",



**Description:** Get full details of a specific attempt (all questions and answers).    }  "file_name": "document.pdf",



**Response:** Full attempt details with all questions, user answers, correct answers, and explanations.  ],  "file_type": "pdf",



### 7. Get User Attempts  "descriptive_results": [  "collection_name": "my_documents",



**Endpoint:** `GET /api/quiz/user/{user_id}/attempts?skip=0&limit=10`    {  "created_at": "2025-11-04T10:30:00.000000",



**Description:** Get all quizzes attempted by a specific user.      "question_id": 5,  "started_at": null,



**Use Case:** User progress tracking, quiz history.      "question": "Explain how prepared statements prevent SQL injection.",  "completed_at": null,



---      "your_answer": "Prepared statements separate SQL code...",  "progress": null,



## 📈 Analytics (NEW!)      "sample_answer": "Prepared statements prevent injection...",  "metadata": null,



### 8. Get Quiz Analytics      "key_points": ["Separates SQL from data", "Uses parameters"],  "error": null



**Endpoint:** `GET /api/quiz/{quiz_id}/analytics`      "explanation": "Good understanding demonstrated."}



**Description:** Get statistical analytics for a quiz.    }```



**Response:** `200 OK`  ],

```json

{  "mcq_score": 3,#### Status: PROCESSING

  "quiz_id": 4,

  "topic": "Kerberos",  "blank_score": 1,```json

  "total_attempts": 2,

  "average_score": 66.66,  "total_auto_score": 4,{

  "highest_score": 100.0,

  "lowest_score": 33.33,  "max_auto_score": 4,  "job_id": "550e8400-e29b-41d4-a716-446655440000",

  "average_time_seconds": 105.0,

  "completion_rate": 100.0  "percentage": 100.0  "status": "processing",

}

```}  "file_name": "document.pdf",



**Use Cases:**```  "file_type": "pdf",

- Identify difficult quizzes (low average scores)

- Track quiz popularity (total attempts)  "collection_name": "my_documents",

- Measure effectiveness (completion rate)

- Find time-consuming quizzes (average time)---  "created_at": "2025-11-04T10:30:00.000000",



---  "started_at": "2025-11-04T10:30:05.000000",



## 🔄 Frontend Integration Flow## 🔌 3. Get Quiz  "completed_at": null,



### Step 1: Generate Quiz  "progress": {

```javascript

const quiz = await fetch('/api/quiz/generate', {**GET** `/api/quiz/{quiz_id}`    "current_step": "generating_embeddings",

  method: 'POST',

  headers: {'Content-Type': 'application/json'},    "percentage": 75.0,

  body: JSON.stringify({

    topic: 'SQL Injection',Retrieve quiz without answers.    "chunks_processed": 30,

    total_questions: 5,

    num_mcq: 3,    "total_chunks": 40

    num_blanks: 1,

    num_descriptive: 1,**Example:** `/api/quiz/1`  },

    difficulty: 'medium'

  })  "metadata": null,

}).then(r => r.json());

**Response (200):** Same as generate response  "error": null

// Save quiz.quiz_id for submission

```}



### Step 2: Display Quiz---```

```javascript

// Display MCQ with radio buttons (option_id: 1-4)

quiz.mcq_questions.forEach(q => {

  renderMCQ(q.question_id, q.question, q.options);## 🔌 4. List Quizzes#### Status: COMPLETED

});

```json

// Display blanks with text inputs

quiz.blank_questions.forEach(q => {**GET** `/api/quiz/list/all?skip=0&limit=10`{

  renderBlank(q.question_id, q.question);

});  "job_id": "550e8400-e29b-41d4-a716-446655440000",



// Display descriptive with textareas**Response (200):**  "status": "completed",

quiz.descriptive_questions.forEach(q => {

  renderDescriptive(q.question_id, q.question);```json  "file_name": "document.pdf",

});

```[  "file_type": "pdf",



### Step 3: Submit Quiz  {  "collection_name": "my_documents",

```javascript

const result = await fetch('/api/quiz/submit', {    "quiz_id": 1,  "created_at": "2025-11-04T10:30:00.000000",

  method: 'POST',

  headers: {'Content-Type': 'application/json'},    "topic": "SQL injection",  "started_at": "2025-11-04T10:30:05.000000",

  body: JSON.stringify({

    quiz_id: quiz.quiz_id,    "total_questions": 5,  "completed_at": "2025-11-04T10:30:45.000000",

    user_id: currentUser?.id,           // Optional

    user_name: currentUser?.name,       // Optional    "difficulty": "medium",  "progress": {

    time_taken_seconds: elapsedSeconds,

    mcq_answers: collectMCQAnswers(),    "created_at": "2025-11-09T12:34:56"    "current_step": "completed",

    blank_answers: collectBlankAnswers(),

    descriptive_answers: collectDescriptiveAnswers()  }    "percentage": 100.0,

  })

}).then(r => r.json());]    "chunks_processed": 42,



// Save result.attempt_id for later review```    "total_chunks": 42

```

  },

### Step 4: Display Results

```javascript---  "metadata": {

// Show score

console.log(`Score: ${result.percentage}%`);    "chunks_count": 42,



// Show MCQ feedback## 📦 TypeScript Types    "text_length": 15000,

result.mcq_results.forEach(r => {

  showFeedback(r.question, r.your_answer_text,     "processing_time_seconds": 40.5

               r.correct_answer_text, r.is_correct, r.explanation);

});```typescript  },

```

// Requests  "error": null

### Step 5: View History

```javascriptinterface QuizGenerateRequest {}

// Get user's attempt history

const history = await fetch(`/api/quiz/user/${userId}/attempts`)  topic: string;```

  .then(r => r.json());

  total_questions: number;  // Must equal num_mcq + num_blanks + num_descriptive

// Review specific attempt

const attempt = await fetch(`/api/quiz/attempt/${attemptId}`)  num_mcq: number;#### Status: FAILED

  .then(r => r.json());

```  num_blanks: number;```json



---  num_descriptive: number;{



## 📦 Complete API Endpoint List  difficulty?: "easy" | "medium" | "hard";  "job_id": "550e8400-e29b-41d4-a716-446655440000",



| Endpoint | Method | Description | New? |  collection_name?: string;  "status": "failed",

|----------|--------|-------------|------|

| `/api/quiz/generate` | POST | Generate quiz with AI | ✅ |}  "file_name": "document.pdf",

| `/api/quiz/submit` | POST | Submit & grade (saves attempt) | ✅ Updated |

| `/api/quiz/{id}` | GET | Get quiz by ID | ✅ |  "file_type": "pdf",

| `/api/quiz/list/all` | GET | List all quizzes | ✅ |

| `/api/quiz/{id}/attempts` | GET | Get quiz attempts | 🆕 NEW |interface QuizSubmission {  "collection_name": "my_documents",

| `/api/quiz/attempt/{id}` | GET | Get attempt detail | 🆕 NEW |

| `/api/quiz/user/{id}/attempts` | GET | Get user's attempts | 🆕 NEW |  quiz_id: number;  "created_at": "2025-11-04T10:30:00.000000",

| `/api/quiz/{id}/analytics` | GET | Get quiz analytics | 🆕 NEW |

  mcq_answers: { question_id: number; selected_option_id: number }[];  "started_at": "2025-11-04T10:30:05.000000",

---

  blank_answers: { question_id: number; answer: string }[];  "completed_at": "2025-11-04T10:30:15.000000",

## 🎯 Key Changes from Previous Version

  descriptive_answers: { question_id: number; answer: string }[];  "progress": {

### What's New:

1. ✅ **Attempt Tracking** - All quiz submissions are now saved to database}    "current_step": "text_extraction",

2. ✅ **User Attribution** - Optional `user_id` and `user_name` in submissions

3. ✅ **Time Tracking** - Optional `time_taken_seconds` for quiz completion time    "percentage": 25.0,

4. ✅ **Attempt History** - View all attempts for a quiz

5. ✅ **User History** - Track individual user progress// Responses    "chunks_processed": 0,

6. ✅ **Analytics** - Quiz performance statistics

7. ✅ **Attempt Review** - Review past attempts with full detailsinterface QuizResponse {    "total_chunks": 0



### Updated Response Fields:  quiz_id: number;  },

- **Submit endpoint** now returns:

  - `attempt_id` - Unique identifier for this attempt  topic: string;  "metadata": null,

  - `time_taken_seconds` - Time taken if provided

  - `submitted_at` - Timestamp of submission  total_questions: number;  "error": "No text could be extracted from the document"



---  num_mcq: number;}



## ⚠️ Error Handling  num_blanks: number;```



| Code | Meaning | Example |  num_descriptive: number;

|------|---------|---------|

| `200` | Success | Request completed |  difficulty: string;**Error Response**: `404 Not Found`

| `201` | Created | Quiz generated |

| `400` | Bad Request | Validation failed |  mcq_questions: MCQQuestion[];```json

| `404` | Not Found | Quiz/attempt not found |

| `422` | Validation Error | Invalid input format |  blank_questions: BlankQuestion[];{

| `500` | Server Error | AI generation failed |

  descriptive_questions: DescriptiveQuestion[];  "detail": "Job not found"

---

  created_at: string;}

## 🔐 Security Features

}```

1. ✅ **Hidden Answers** - Not sent to frontend on generation

2. ✅ **Server-Side Grading** - All grading on backend

3. ✅ **Numeric Option IDs** - Uses 1-4 instead of A-D

4. ✅ **Attempt Logging** - All submissions trackedinterface MCQQuestion {---

5. ✅ **Anonymous Support** - User fields are optional

  question_id: number;

---

  question: string;### 3. Health Check

## 📊 Database Schema (for reference)

  options: { option_id: number; text: string }[];

### Tables:

- `quizzes` - Quiz definitions}#### `GET /api/health`

- `questions` - Questions with correct answers

- `quiz_attempts` - User submissions and scores (NEW!)

- `user_answers` - Detailed answer tracking (NEW!)

interface BlankQuestion {Check API health and system status.

---

  question_id: number;

## 📞 Resources

  question: string;**cURL Example**:

- **Interactive API Docs:** http://localhost:8000/docs

- **Alternative Docs:** http://localhost:8000/redoc}```bash

- **Health Check:** http://localhost:8000/api/health

curl "http://localhost:8000/api/health"

---

interface DescriptiveQuestion {```

**Last Updated:** November 9, 2025  

**Version:** 2.0.0 (with Attempt Tracking)  question_id: number;


  question: string;**Response**: `200 OK`

}```json

{

interface QuizGradingResponse {  "status": "healthy",

  quiz_id: number;  "timestamp": "2025-11-04T10:30:00.000000",

  topic: string;  "redis": "connected",

  total_questions: number;  "chroma_db_path": "./chroma_db",

  mcq_results: MCQResult[];  "allowed_file_types": ["pdf", "pptx"],

  blank_results: BlankResult[];  "max_file_size_mb": 50.0

  descriptive_results: DescriptiveResult[];}

  mcq_score: number;```

  blank_score: number;

  total_auto_score: number;---

  max_auto_score: number;

  percentage: number;## Data Models (TypeScript Interfaces)

}

### JobResponse

interface MCQResult {```typescript

  question_id: number;interface JobResponse {

  question: string;  job_id: string;      // UUID format

  your_answer: number;  status: string;      // "queued"

  your_answer_text: string;  message: string;     // Success message

  correct_answer: number;}

  correct_answer_text: string;```

  is_correct: boolean;

  explanation: string;### Job (Full Status)

}```typescript

type JobStatus = "queued" | "processing" | "completed" | "failed";

interface BlankResult {

  question_id: number;interface JobProgress {

  question: string;  current_step: string;       // e.g., "text_extraction", "chunking", "generating_embeddings"

  your_answer: string;  percentage: number;         // 0-100

  correct_answer: string;  chunks_processed: number;

  is_correct: boolean;  total_chunks: number;

  explanation: string;}

}

interface JobMetadata {

interface DescriptiveResult {  chunks_count: number;

  question_id: number;  text_length: number;

  question: string;  processing_time_seconds: number;

  your_answer: string;}

  sample_answer: string;

  key_points: string[];interface Job {

  explanation: string;  job_id: string;

}  status: JobStatus;

```  file_name: string;

  file_type: string;              // "pdf" | "pptx"

---  collection_name: string;

  created_at: string;             // ISO 8601 datetime

## 🚀 React Integration Example  started_at: string | null;      // ISO 8601 datetime

  completed_at: string | null;    // ISO 8601 datetime

```typescript  progress: JobProgress | null;

// API Service  metadata: JobMetadata | null;   // Only present when completed

const API_URL = 'http://localhost:8000';  error: string | null;           // Only present when failed

}

export const quizApi = {```

  async generateQuiz(request: QuizGenerateRequest): Promise<QuizResponse> {

    const res = await fetch(`${API_URL}/api/quiz/generate`, {### HealthResponse

      method: 'POST',```typescript

      headers: { 'Content-Type': 'application/json' },interface HealthResponse {

      body: JSON.stringify(request),  status: string;

    });  timestamp: string;

    if (!res.ok) throw new Error(await res.text());  redis: string;

    return res.json();  chroma_db_path: string;

  },  allowed_file_types: string[];

  max_file_size_mb: number;

  async submitQuiz(submission: QuizSubmission): Promise<QuizGradingResponse> {}

    const res = await fetch(`${API_URL}/api/quiz/submit`, {```

      method: 'POST',

      headers: { 'Content-Type': 'application/json' },---

      body: JSON.stringify(submission),

    });## Job Status Flow

    if (!res.ok) throw new Error(await res.text());

    return res.json();```

  },QUEUED

  ↓

  async getQuiz(id: number): Promise<QuizResponse> {PROCESSING (with progress updates)

    const res = await fetch(`${API_URL}/api/quiz/${id}`);  ↓

    if (!res.ok) throw new Error(await res.text());COMPLETED (with metadata)

    return res.json();  or

  },FAILED (with error message)

```

  async listQuizzes(skip = 0, limit = 10) {

    const res = await fetch(`${API_URL}/api/quiz/list/all?skip=${skip}&limit=${limit}`);### Processing Steps & Progress

    if (!res.ok) throw new Error(await res.text());

    return res.json();| Step | Progress % | Description |

  },|------|-----------|-------------|

};| `queued` | 0% | Job created, waiting for worker |

| `text_extraction` | 0-25% | Extracting text from PDF/PPTX |

// Component Usage| `chunking` | 50% | Splitting text into chunks |

function QuizPage() {| `generating_embeddings` | 75% | Creating embeddings with OpenAI |

  const [quiz, setQuiz] = useState<QuizResponse | null>(null);| `storing` | 90% | Saving embeddings to ChromaDB |

  const [loading, setLoading] = useState(false);| `completed` | 100% | Processing finished successfully |



  const handleGenerate = async () => {---

    setLoading(true);

    try {## Integration Examples

      const newQuiz = await quizApi.generateQuiz({

        topic: "SQL injection",### React/Next.js Complete Example

        total_questions: 5,

        num_mcq: 3,```typescript

        num_blanks: 1,'use client';

        num_descriptive: 1,

        difficulty: "medium",import { useState, useEffect } from 'react';

      });

      setQuiz(newQuiz);interface Job {

    } catch (err) {  job_id: string;

      console.error('Failed:', err);  status: 'queued' | 'processing' | 'completed' | 'failed';

    } finally {  file_name: string;

      setLoading(false);  progress?: {

    }    current_step: string;

  };    percentage: number;

    chunks_processed: number;

  const handleSubmit = async (answers: QuizSubmission) => {    total_chunks: number;

    const results = await quizApi.submitQuiz(answers);  } | null;

    console.log('Score:', results.percentage);  metadata?: {

  };    chunks_count: number;

    text_length: number;

  return <div>{/* UI components */}</div>;    processing_time_seconds: number;

}  } | null;

```  error?: string | null;

}

---

export default function DocumentUpload() {

## ⚠️ Important Notes  const [file, setFile] = useState<File | null>(null);

  const [collectionName, setCollectionName] = useState('');

1. **Answers Security**: Generation response does NOT include answers  const [jobId, setJobId] = useState<string | null>(null);

2. **Option IDs**: MCQ options use numbers (1-4), not letters (A-D)  const [job, setJob] = useState<Job | null>(null);

3. **Blank Grading**: Case-insensitive, whitespace-trimmed  const [uploading, setUploading] = useState(false);

4. **Descriptive**: NOT auto-graded, sample answer provided  const [error, setError] = useState<string | null>(null);

5. **Generation Time**: 10-30 seconds (AI processing)

6. **Validation**: `total_questions` must equal sum of question types  // Upload file and get job ID

  const handleUpload = async () => {

---    if (!file) return;



## 🔍 Error Responses    setUploading(true);

    setError(null);

```typescript

// 422 Validation Error    const formData = new FormData();

{    formData.append('file', file);

  "detail": [    if (collectionName) {

    {      formData.append('collection_name', collectionName);

      "type": "value_error",    }

      "loc": ["body", "total_questions"],

      "msg": "Sum of questions must equal total_questions"    try {

    }      const response = await fetch('http://localhost:8000/api/start-embedding', {

  ]        method: 'POST',

}        body: formData,

      });

// 404 Not Found

{      if (!response.ok) {

  "detail": "Quiz not found"        const errorData = await response.json();

}        throw new Error(errorData.detail || 'Upload failed');

      }

// 500 Server Error

{      const data = await response.json();

  "detail": "Failed to retrieve content: No content found for topic"      setJobId(data.job_id);

}    } catch (err) {

```      setError(err instanceof Error ? err.message : 'Upload failed');

    } finally {

---      setUploading(false);

    }

## 📚 Additional Resources  };



- **Swagger UI**: http://localhost:8000/docs  // Poll job status

- **API Root**: http://localhost:8000/  useEffect(() => {

    if (!jobId) return;

---

    const pollStatus = async () => {

**Ready for frontend integration! 🚀**      try {

        const response = await fetch(`http://localhost:8000/api/job-status/${jobId}`);
        if (response.ok) {
          const data = await response.json();
          setJob(data);

          // Stop polling if completed or failed
          if (data.status === 'completed' || data.status === 'failed') {
            return;
          }
        }
      } catch (err) {
        console.error('Error polling status:', err);
      }
    };

    // Poll every 2 seconds
    const interval = setInterval(pollStatus, 2000);
    pollStatus(); // Initial poll

    return () => clearInterval(interval);
  }, [jobId]);

  return (
    <div className="p-6 max-w-md mx-auto">
      <h2 className="text-2xl font-bold mb-4">Upload Document</h2>

      {!jobId ? (
        <div className="space-y-4">
          <div>
            <label className="block mb-2">Select File (PDF or PPTX)</label>
            <input
              type="file"
              accept=".pdf,.pptx"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full"
            />
          </div>

          <div>
            <label className="block mb-2">Collection Name (Optional)</label>
            <input
              type="text"
              value={collectionName}
              onChange={(e) => setCollectionName(e.target.value)}
              placeholder="my_documents"
              className="block w-full px-3 py-2 border rounded"
            />
          </div>

          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="w-full bg-blue-500 text-white py-2 px-4 rounded disabled:opacity-50"
          >
            {uploading ? 'Uploading...' : 'Upload & Process'}
          </button>

          {error && (
            <div className="p-3 bg-red-100 text-red-700 rounded">
              {error}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="p-4 bg-gray-50 rounded">
            <p className="text-sm text-gray-600">Job ID:</p>
            <p className="font-mono text-sm break-all">{jobId}</p>
          </div>

          {job && (
            <div className="space-y-3">
              <div className="p-4 border rounded">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold">Status:</span>
                  <span className={`px-2 py-1 rounded text-sm ${
                    job.status === 'completed' ? 'bg-green-100 text-green-800' :
                    job.status === 'failed' ? 'bg-red-100 text-red-800' :
                    job.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {job.status.toUpperCase()}
                  </span>
                </div>

                <p className="text-sm text-gray-600">
                  File: {job.file_name}
                </p>

                {job.progress && (
                  <div className="mt-3">
                    <div className="flex justify-between text-sm mb-1">
                      <span>{job.progress.current_step.replace('_', ' ')}</span>
                      <span>{job.progress.percentage.toFixed(0)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${job.progress.percentage}%` }}
                      />
                    </div>
                    {job.progress.total_chunks > 0 && (
                      <p className="text-xs text-gray-500 mt-1">
                        Chunks: {job.progress.chunks_processed} / {job.progress.total_chunks}
                      </p>
                    )}
                  </div>
                )}

                {job.status === 'completed' && job.metadata && (
                  <div className="mt-3 p-3 bg-green-50 rounded">
                    <p className="text-sm text-green-800 font-semibold mb-2">
                      ✓ Processing Complete
                    </p>
                    <div className="text-xs text-green-700 space-y-1">
                      <p>Chunks: {job.metadata.chunks_count}</p>
                      <p>Text Length: {job.metadata.text_length.toLocaleString()} chars</p>
                      <p>Processing Time: {job.metadata.processing_time_seconds}s</p>
                    </div>
                  </div>
                )}

                {job.status === 'failed' && job.error && (
                  <div className="mt-3 p-3 bg-red-50 rounded">
                    <p className="text-sm text-red-800 font-semibold mb-1">
                      ✗ Processing Failed
                    </p>
                    <p className="text-xs text-red-700">{job.error}</p>
                  </div>
                )}
              </div>

              <button
                onClick={() => {
                  setJobId(null);
                  setJob(null);
                  setFile(null);
                }}
                className="w-full bg-gray-500 text-white py-2 px-4 rounded"
              >
                Upload Another Document
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

### Polling with Async/Await

```typescript
async function uploadAndWaitForCompletion(file: File, collectionName?: string) {
  // Step 1: Upload file
  const formData = new FormData();
  formData.append('file', file);
  if (collectionName) {
    formData.append('collection_name', collectionName);
  }

  const uploadResponse = await fetch('http://localhost:8000/api/start-embedding', {
    method: 'POST',
    body: formData,
  });

  const { job_id } = await uploadResponse.json();

  // Step 2: Poll for completion
  while (true) {
    const statusResponse = await fetch(`http://localhost:8000/api/job-status/${job_id}`);
    const job = await statusResponse.json();

    console.log(`Status: ${job.status}, Progress: ${job.progress?.percentage}%`);

    if (job.status === 'completed') {
      console.log('Success!', job.metadata);
      return job;
    }

    if (job.status === 'failed') {
      throw new Error(job.error);
    }

    // Wait 2 seconds before next poll
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
}

// Usage
try {
  const result = await uploadAndWaitForCompletion(fileObject, 'my_docs');
  console.log(`Created ${result.metadata.chunks_count} chunks`);
} catch (error) {
  console.error('Processing failed:', error);
}
```

---

## File Specifications

### Supported File Types
- ✅ **PDF** (.pdf)
- ✅ **PowerPoint** (.pptx)

### File Size Limits
- **Maximum**: 50 MB (52,428,800 bytes)

### Collection Naming
- If not provided, defaults to filename without extension
- Spaces replaced with underscores
- Converted to lowercase
- Example: "My Document.pdf" → "my_document"

---

## Processing Pipeline Details

When a job is processed, these steps occur:

1. **Text Extraction** (0-25%)
   - PDF: Uses PyPDF2 to extract text from all pages
   - PPTX: Uses python-pptx to extract text from all slides

2. **Text Chunking** (50%)
   - RecursiveCharacterTextSplitter
   - Chunk size: 1000 characters
   - Chunk overlap: 200 characters

3. **Embedding Generation** (75%)
   - OpenAI API call to generate embeddings
   - Each chunk gets a vector representation

4. **Storage** (90%)
   - Store embeddings in ChromaDB
   - Organize by collection name
   - Persist to disk

5. **Completion** (100%)
   - Update job status
   - Add metadata
   - Clean up temporary files

**Average Processing Time**: 10-60 seconds (depending on document size)

---

## Error Handling

### Client-Side Error Handling

```typescript
try {
  const response = await fetch('http://localhost:8000/api/start-embedding', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();

    switch (response.status) {
      case 400:
        // Validation error (wrong file type, etc.)
        console.error('Validation error:', error.detail);
        break;
      case 404:
        // Job not found
        console.error('Job not found');
        break;
      case 500:
        // Server error
        console.error('Server error:', error.detail);
        break;
      default:
        console.error('Unexpected error:', error);
    }

    throw new Error(error.detail);
  }

  const data = await response.json();
  // Success handling

} catch (err) {
  // Network errors or parsing errors
  console.error('Network error:', err);
}
```

---

## Setup & Running

### Prerequisites
1. **Redis** must be running on `localhost:6379`
2. **OpenAI API Key** configured in `.env`

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
nano .env
```

### Running the System

**Terminal 1 - Start Redis**:
```bash
redis-server
```

**Terminal 2 - Start FastAPI Server**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 3 - Start Celery Worker**:
```bash
celery -A app.workers.celery_app worker --loglevel=info
```

**Optional - Start Flower (Celery Monitoring)**:
```bash
celery -A app.workers.celery_app flower
# Access at http://localhost:5555
```

---

## Testing with cURL

### Upload a document
```bash
curl -X POST "http://localhost:8000/api/start-embedding" \
  -F "file=@test.pdf" \
  -F "collection_name=test_collection"

# Response:
# {"job_id":"550e8400-e29b-41d4-a716-446655440000","status":"queued","message":"Job created successfully. Use job_id to check status."}
```

### Check job status
```bash
curl "http://localhost:8000/api/job-status/550e8400-e29b-41d4-a716-446655440000"
```

### Health check
```bash
curl "http://localhost:8000/api/health"
```

---

## Important Notes for Integration

1. **Non-Blocking**: The upload endpoint returns immediately - don't wait for processing
2. **Polling**: Implement polling (every 1-3 seconds) to check job status
3. **Job Expiry**: Jobs are stored for 24 hours, then automatically deleted
4. **File Cleanup**: Uploaded files are automatically deleted after processing
5. **Retry Logic**: OpenAI API errors trigger automatic retries (max 3 attempts)
6. **CORS**: Currently allows all origins - configure for production
7. **Timeouts**: Set reasonable client-side timeouts (60s for upload, 5s for status checks)
8. **Error States**: Always handle `failed` status and display error messages to users

---

## CORS Configuration

The API allows all origins by default. For production, update [app/main.py](app/main.py):

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Questions or Issues?

- **Swagger UI**: `http://localhost:8000/docs` for interactive API testing
- **ReDoc**: `http://localhost:8000/redoc` for detailed documentation
- **Flower Dashboard**: `http://localhost:5555` for Celery monitoring (if running)

---

**API Version**: 1.0.0
**Last Updated**: 2025-11-04
