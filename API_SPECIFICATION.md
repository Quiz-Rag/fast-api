# Document Processing API - Queue-Based Architecture

## Base Information

**Base URL**: `http://localhost:8000`
**API Prefix**: `/api`
**Documentation**: `http://localhost:8000/docs` (Interactive Swagger UI)
**Version**: 1.0.0

---

## Architecture Overview

This API uses an **asynchronous queue-based architecture** with Celery + Redis:

1. **Upload File** → Returns job_id immediately (non-blocking)
2. **Background Worker** → Processes job asynchronously
3. **Poll Status** → Check progress and get results

```
Client → POST /api/start-embedding → Returns job_id
                                           ↓
                                      (Queue Job)
                                           ↓
                              Celery Worker Processes
                                           ↓
Client → GET /api/job-status/{id} → Get Status/Progress
```

---

## API Endpoints

### 1. Start Embedding (Upload & Queue)

#### `POST /api/start-embedding`

Upload a document file and start the embedding process. **Returns immediately** with a job ID.

**Request**:
- **Content-Type**: `multipart/form-data`
- **Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File | ✅ Yes | PDF or PPTX document to process |
| `collection_name` | string | ❌ No | ChromaDB collection name (defaults to filename without extension) |

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/api/start-embedding" \
  -F "file=@document.pdf" \
  -F "collection_name=my_documents"
```

**JavaScript/TypeScript Example**:
```typescript
const formData = new FormData();
formData.append('file', fileObject);
formData.append('collection_name', 'my_documents'); // Optional

const response = await fetch('http://localhost:8000/api/start-embedding', {
  method: 'POST',
  body: formData,
});

const data = await response.json();
console.log(data.job_id); // Save this to check status later
```

**Success Response**: `202 Accepted`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Job created successfully. Use job_id to check status."
}
```

**Error Responses**:

**400 Bad Request** - Invalid file type
```json
{
  "detail": "File type not allowed. Allowed types: pdf, pptx"
}
```

**500 Internal Server Error** - Job creation failed
```json
{
  "detail": "Error creating job: [error message]"
}
```

---

### 2. Check Job Status

#### `GET /api/job-status/{job_id}`

Check the processing status and progress of a job.

**Parameters**:
- **Path Parameter**: `job_id` (UUID string)

**cURL Example**:
```bash
curl "http://localhost:8000/api/job-status/550e8400-e29b-41d4-a716-446655440000"
```

**JavaScript/TypeScript Example**:
```typescript
const jobId = "550e8400-e29b-41d4-a716-446655440000";

const response = await fetch(`http://localhost:8000/api/job-status/${jobId}`);
const job = await response.json();

console.log(`Status: ${job.status}`);
console.log(`Progress: ${job.progress?.percentage}%`);
```

**Response Examples**:

#### Status: QUEUED
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "file_name": "document.pdf",
  "file_type": "pdf",
  "collection_name": "my_documents",
  "created_at": "2025-11-04T10:30:00.000000",
  "started_at": null,
  "completed_at": null,
  "progress": null,
  "metadata": null,
  "error": null
}
```

#### Status: PROCESSING
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "file_name": "document.pdf",
  "file_type": "pdf",
  "collection_name": "my_documents",
  "created_at": "2025-11-04T10:30:00.000000",
  "started_at": "2025-11-04T10:30:05.000000",
  "completed_at": null,
  "progress": {
    "current_step": "generating_embeddings",
    "percentage": 75.0,
    "chunks_processed": 30,
    "total_chunks": 40
  },
  "metadata": null,
  "error": null
}
```

#### Status: COMPLETED
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "file_name": "document.pdf",
  "file_type": "pdf",
  "collection_name": "my_documents",
  "created_at": "2025-11-04T10:30:00.000000",
  "started_at": "2025-11-04T10:30:05.000000",
  "completed_at": "2025-11-04T10:30:45.000000",
  "progress": {
    "current_step": "completed",
    "percentage": 100.0,
    "chunks_processed": 42,
    "total_chunks": 42
  },
  "metadata": {
    "chunks_count": 42,
    "text_length": 15000,
    "processing_time_seconds": 40.5
  },
  "error": null
}
```

#### Status: FAILED
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "file_name": "document.pdf",
  "file_type": "pdf",
  "collection_name": "my_documents",
  "created_at": "2025-11-04T10:30:00.000000",
  "started_at": "2025-11-04T10:30:05.000000",
  "completed_at": "2025-11-04T10:30:15.000000",
  "progress": {
    "current_step": "text_extraction",
    "percentage": 25.0,
    "chunks_processed": 0,
    "total_chunks": 0
  },
  "metadata": null,
  "error": "No text could be extracted from the document"
}
```

**Error Response**: `404 Not Found`
```json
{
  "detail": "Job not found"
}
```

---

### 3. Health Check

#### `GET /api/health`

Check API health and system status.

**cURL Example**:
```bash
curl "http://localhost:8000/api/health"
```

**Response**: `200 OK`
```json
{
  "status": "healthy",
  "timestamp": "2025-11-04T10:30:00.000000",
  "redis": "connected",
  "chroma_db_path": "./chroma_db",
  "allowed_file_types": ["pdf", "pptx"],
  "max_file_size_mb": 50.0
}
```

---

## Data Models (TypeScript Interfaces)

### JobResponse
```typescript
interface JobResponse {
  job_id: string;      // UUID format
  status: string;      // "queued"
  message: string;     // Success message
}
```

### Job (Full Status)
```typescript
type JobStatus = "queued" | "processing" | "completed" | "failed";

interface JobProgress {
  current_step: string;       // e.g., "text_extraction", "chunking", "generating_embeddings"
  percentage: number;         // 0-100
  chunks_processed: number;
  total_chunks: number;
}

interface JobMetadata {
  chunks_count: number;
  text_length: number;
  processing_time_seconds: number;
}

interface Job {
  job_id: string;
  status: JobStatus;
  file_name: string;
  file_type: string;              // "pdf" | "pptx"
  collection_name: string;
  created_at: string;             // ISO 8601 datetime
  started_at: string | null;      // ISO 8601 datetime
  completed_at: string | null;    // ISO 8601 datetime
  progress: JobProgress | null;
  metadata: JobMetadata | null;   // Only present when completed
  error: string | null;           // Only present when failed
}
```

### HealthResponse
```typescript
interface HealthResponse {
  status: string;
  timestamp: string;
  redis: string;
  chroma_db_path: string;
  allowed_file_types: string[];
  max_file_size_mb: number;
}
```

---

## Job Status Flow

```
QUEUED
  ↓
PROCESSING (with progress updates)
  ↓
COMPLETED (with metadata)
  or
FAILED (with error message)
```

### Processing Steps & Progress

| Step | Progress % | Description |
|------|-----------|-------------|
| `queued` | 0% | Job created, waiting for worker |
| `text_extraction` | 0-25% | Extracting text from PDF/PPTX |
| `chunking` | 50% | Splitting text into chunks |
| `generating_embeddings` | 75% | Creating embeddings with OpenAI |
| `storing` | 90% | Saving embeddings to ChromaDB |
| `completed` | 100% | Processing finished successfully |

---

## Integration Examples

### React/Next.js Complete Example

```typescript
'use client';

import { useState, useEffect } from 'react';

interface Job {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  file_name: string;
  progress?: {
    current_step: string;
    percentage: number;
    chunks_processed: number;
    total_chunks: number;
  } | null;
  metadata?: {
    chunks_count: number;
    text_length: number;
    processing_time_seconds: number;
  } | null;
  error?: string | null;
}

export default function DocumentUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [collectionName, setCollectionName] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Upload file and get job ID
  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    if (collectionName) {
      formData.append('collection_name', collectionName);
    }

    try {
      const response = await fetch('http://localhost:8000/api/start-embedding', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const data = await response.json();
      setJobId(data.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  // Poll job status
  useEffect(() => {
    if (!jobId) return;

    const pollStatus = async () => {
      try {
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
