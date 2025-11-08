# FastAPI Document Processing - Integration Specifications

## Quick Summary
An asynchronous document processing API that accepts PDF/PPTX files, processes them in the background (extracts text, creates embeddings, stores in vector database), and provides job status tracking.

---

## Base URL
```
http://localhost:8000
```

---

## API Endpoints

### 1. Upload Document & Start Processing

**Endpoint:** `POST /api/start-embedding`

**Description:** Upload a document (PDF or PPTX) and receive a job ID immediately. Processing happens asynchronously in the background.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body Parameters:
  - `file` (File, required): PDF or PPTX file
  - `collection_name` (string, optional): Name for the document collection (defaults to filename)

**Response:** `202 Accepted`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Job created successfully. Use job_id to check status."
}
```

**Fetch Example:**
```typescript
const formData = new FormData();
formData.append('file', fileObject);
formData.append('collection_name', 'my_documents'); // optional

const response = await fetch('http://localhost:8000/api/start-embedding', {
  method: 'POST',
  body: formData,
});

const { job_id } = await response.json();
```

**Error Responses:**
- `400`: Invalid file type
- `500`: Server error

---

### 2. Check Job Status

**Endpoint:** `GET /api/job-status/{job_id}`

**Description:** Get the current status and progress of a processing job. Poll this endpoint every 2-3 seconds to track progress.

**Request:**
- Method: `GET`
- URL Parameter: `job_id` (UUID string)

**Response:** `200 OK`

**Status Types:**
- `queued`: Job created, waiting to be processed
- `processing`: Currently being processed (includes progress)
- `completed`: Successfully completed (includes metadata)
- `failed`: Processing failed (includes error message)

**Response Examples:**

**Queued:**
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

**Processing:**
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

**Completed:**
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

**Failed:**
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

**Fetch Example:**
```typescript
const response = await fetch(`http://localhost:8000/api/job-status/${jobId}`);
const job = await response.json();

console.log(`Status: ${job.status}`);
console.log(`Progress: ${job.progress?.percentage}%`);
```

**Error Responses:**
- `404`: Job not found

---

### 3. Health Check

**Endpoint:** `GET /api/health`

**Description:** Check if the API is running and healthy.

**Response:** `200 OK`
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

## TypeScript Types

```typescript
// Job Status Types
type JobStatus = 'queued' | 'processing' | 'completed' | 'failed';

// Upload Response
interface UploadResponse {
  job_id: string;
  status: 'queued';
  message: string;
}

// Job Progress
interface JobProgress {
  current_step: string;
  percentage: number;
  chunks_processed: number;
  total_chunks: number;
}

// Job Metadata (only present when completed)
interface JobMetadata {
  chunks_count: number;
  text_length: number;
  processing_time_seconds: number;
}

// Complete Job Status
interface Job {
  job_id: string;
  status: JobStatus;
  file_name: string;
  file_type: 'pdf' | 'pptx';
  collection_name: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  progress: JobProgress | null;
  metadata: JobMetadata | null;
  error: string | null;
}
```

---

## Processing Flow

```
1. User selects file
   ↓
2. Upload file via POST /api/start-embedding
   ↓
3. Receive job_id immediately (non-blocking)
   ↓
4. Start polling GET /api/job-status/{job_id} every 2-3 seconds
   ↓
5. Show progress to user (0% → 100%)
   ↓
6. When status === 'completed', stop polling and show success
   OR
   When status === 'failed', stop polling and show error
```

---

## React/Next.js Implementation Guide

### Step 1: Create API Service

```typescript
// lib/api.ts
const API_BASE_URL = 'http://localhost:8000';

export async function uploadDocument(
  file: File,
  collectionName?: string
): Promise<{ job_id: string }> {
  const formData = new FormData();
  formData.append('file', file);
  if (collectionName) {
    formData.append('collection_name', collectionName);
  }

  const response = await fetch(`${API_BASE_URL}/api/start-embedding`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Upload failed');
  }

  return response.json();
}

export async function getJobStatus(jobId: string): Promise<Job> {
  const response = await fetch(`${API_BASE_URL}/api/job-status/${jobId}`);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Job not found');
    }
    throw new Error('Failed to fetch job status');
  }

  return response.json();
}

export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  return response.json();
}
```

### Step 2: Create Upload Component

```typescript
'use client';

import { useState, useEffect } from 'react';
import { uploadDocument, getJobStatus } from '@/lib/api';
import type { Job } from '@/types';

export default function DocumentUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [collectionName, setCollectionName] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Handle file upload
  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const result = await uploadDocument(file, collectionName || undefined);
      setJobId(result.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  // Poll job status
  useEffect(() => {
    if (!jobId) return;

    let isActive = true;

    const pollStatus = async () => {
      try {
        const jobData = await getJobStatus(jobId);

        if (isActive) {
          setJob(jobData);

          // Stop polling if completed or failed
          if (jobData.status === 'completed' || jobData.status === 'failed') {
            isActive = false;
            return;
          }

          // Continue polling
          setTimeout(pollStatus, 2000);
        }
      } catch (err) {
        console.error('Error polling status:', err);
        if (isActive) {
          setTimeout(pollStatus, 2000);
        }
      }
    };

    pollStatus();

    return () => {
      isActive = false;
    };
  }, [jobId]);

  return (
    <div className="max-w-md mx-auto p-6">
      <h2 className="text-2xl font-bold mb-4">Upload Document</h2>

      {!jobId ? (
        // Upload Form
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              Select File (PDF or PPTX)
            </label>
            <input
              type="file"
              accept=".pdf,.pptx"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm border rounded p-2"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Collection Name (Optional)
            </label>
            <input
              type="text"
              value={collectionName}
              onChange={(e) => setCollectionName(e.target.value)}
              placeholder="my_documents"
              className="block w-full border rounded p-2"
            />
          </div>

          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? 'Uploading...' : 'Upload & Process'}
          </button>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded text-sm">
              {error}
            </div>
          )}
        </div>
      ) : (
        // Job Status Display
        <div className="space-y-4">
          <div className="p-3 bg-gray-50 rounded">
            <p className="text-xs text-gray-600 mb-1">Job ID:</p>
            <p className="font-mono text-xs break-all">{jobId}</p>
          </div>

          {job && (
            <>
              {/* Status Badge */}
              <div className="flex items-center justify-between">
                <span className="font-medium">Status:</span>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  job.status === 'completed' ? 'bg-green-100 text-green-800' :
                  job.status === 'failed' ? 'bg-red-100 text-red-800' :
                  job.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {job.status.toUpperCase()}
                </span>
              </div>

              {/* Progress Bar */}
              {job.progress && job.status !== 'completed' && job.status !== 'failed' && (
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-gray-700">
                      {job.progress.current_step.replace(/_/g, ' ')}
                    </span>
                    <span className="font-medium">
                      {job.progress.percentage.toFixed(0)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2.5">
                    <div
                      className="bg-blue-600 h-2.5 rounded-full transition-all duration-500"
                      style={{ width: `${job.progress.percentage}%` }}
                    />
                  </div>
                  {job.progress.total_chunks > 0 && (
                    <p className="text-xs text-gray-500 mt-2">
                      Processing: {job.progress.chunks_processed} / {job.progress.total_chunks} chunks
                    </p>
                  )}
                </div>
              )}

              {/* Success Message */}
              {job.status === 'completed' && job.metadata && (
                <div className="p-4 bg-green-50 border border-green-200 rounded">
                  <p className="text-green-800 font-semibold mb-2 flex items-center">
                    <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    Processing Complete!
                  </p>
                  <div className="text-sm text-green-700 space-y-1">
                    <p>• File: {job.file_name}</p>
                    <p>• Chunks created: {job.metadata.chunks_count}</p>
                    <p>• Text length: {job.metadata.text_length.toLocaleString()} characters</p>
                    <p>• Processing time: {job.metadata.processing_time_seconds}s</p>
                    <p>• Collection: {job.collection_name}</p>
                  </div>
                </div>
              )}

              {/* Error Message */}
              {job.status === 'failed' && (
                <div className="p-4 bg-red-50 border border-red-200 rounded">
                  <p className="text-red-800 font-semibold mb-2 flex items-center">
                    <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                    Processing Failed
                  </p>
                  <p className="text-sm text-red-700">{job.error}</p>
                </div>
              )}

              {/* Reset Button */}
              {(job.status === 'completed' || job.status === 'failed') && (
                <button
                  onClick={() => {
                    setJobId(null);
                    setJob(null);
                    setFile(null);
                    setCollectionName('');
                  }}
                  className="w-full bg-gray-600 text-white py-2 px-4 rounded hover:bg-gray-700"
                >
                  Upload Another Document
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
```

---

## Key Implementation Notes

### 1. **Non-Blocking Upload**
- Upload returns immediately with `job_id`
- Don't wait for processing to complete
- Response time: < 1 second

### 2. **Polling Strategy**
- Poll every 2-3 seconds using `setInterval` or recursive `setTimeout`
- Stop polling when `status === 'completed'` or `status === 'failed'`
- Use `useEffect` cleanup to prevent memory leaks

### 3. **Progress Display**
- Show `progress.percentage` (0-100)
- Display `progress.current_step` (e.g., "text_extraction", "generating_embeddings")
- Show chunks progress: `chunks_processed / total_chunks`

### 4. **Error Handling**
```typescript
try {
  const response = await fetch(url);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  const data = await response.json();
} catch (err) {
  // Handle both network and API errors
  console.error(err);
}
```

### 5. **File Validation**
- Client-side: Check file type (`.pdf`, `.pptx`) and size (< 50MB)
- Server validates as well, but client-side is better UX

### 6. **Job Lifecycle**
```
QUEUED (0%)
  → PROCESSING (1-99%)
    → COMPLETED (100%) with metadata
    OR
    → FAILED with error message
```

---

## Processing Steps

The API processes documents through these steps:

| Step | Progress % | Description |
|------|-----------|-------------|
| `queued` | 0% | Job created, waiting for worker |
| `text_extraction` | 0-25% | Extracting text from PDF/PPTX |
| `chunking` | 50% | Splitting text into chunks |
| `generating_embeddings` | 75% | Creating embeddings with OpenAI |
| `storing` | 90% | Saving to ChromaDB |
| `completed` | 100% | Done! |

Average processing time: **10-60 seconds** depending on document size.

---

## Testing the API

### Quick Test with cURL

```bash
# 1. Upload a document
curl -X POST "http://localhost:8000/api/start-embedding" \
  -F "file=@test.pdf" \
  -F "collection_name=test"

# Response: {"job_id":"abc-123-def","status":"queued","message":"..."}

# 2. Check status (replace with your job_id)
curl "http://localhost:8000/api/job-status/abc-123-def"

# 3. Health check
curl "http://localhost:8000/api/health"
```

---

## Environment Requirements

The API requires:
- **Redis** running on `localhost:6379`
- **OpenAI API Key** configured
- **FastAPI server** running on port `8000`
- **Celery worker** processing jobs in background

If any service is down, the `/api/health` endpoint will indicate the issue.

---

## CORS

CORS is enabled for all origins. In production, this should be restricted:

```python
# Current (Development)
allow_origins=["*"]

# Production
allow_origins=["https://yourdomain.com"]
```

---

## Important Notes

1. **Job Expiry**: Jobs are stored for 24 hours, then auto-deleted
2. **File Cleanup**: Uploaded files are deleted after processing
3. **Retry Logic**: Failed jobs retry automatically (max 3 times) for transient errors
4. **Max File Size**: 50 MB
5. **Supported Types**: PDF and PPTX only
6. **Collection Names**: Auto-generated from filename if not provided (lowercase, underscores)

---

## Summary

**Upload Flow:**
```typescript
1. User selects file
2. POST /api/start-embedding → get job_id
3. Poll GET /api/job-status/{job_id} every 2s
4. Display progress bar
5. When complete, show results or error
```

**What you need to build:**
- File upload form with drag-and-drop (optional)
- Progress bar showing percentage
- Job status display (queued/processing/completed/failed)
- Success message with metadata
- Error message display
- "Upload another" button to reset

**API Endpoints to integrate:**
- `POST /api/start-embedding` (upload)
- `GET /api/job-status/{job_id}` (poll status)
- `GET /api/health` (optional health check)

---

**API Base URL:** `http://localhost:8000`
**Interactive Docs:** `http://localhost:8000/docs`
