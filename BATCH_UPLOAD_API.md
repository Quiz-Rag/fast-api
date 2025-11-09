# Batch Document Upload API Specification

**Base URL:** `http://localhost:8000`  
**Version:** 2.0.0  
**Last Updated:** November 9, 2025

---

## 📋 Overview

Upload multiple documents (up to 10 files) in a single request for batch processing. All files are processed asynchronously and stored in the same ChromaDB collection.

**Key Features:**
- ✅ Upload 2-10 files simultaneously
- ✅ Single job ID for tracking
- ✅ Unified progress tracking
- ✅ Per-file status and error handling
- ✅ Continue processing if one file fails

---

## 🚀 Endpoints

### 1. Batch Upload (Single File - Existing)

**Endpoint:** `POST /api/start-embedding`

**Request:**
```bash
curl -X POST "http://localhost:8000/api/start-embedding" \
  -F "file=@document.pdf" \
  -F "collection_name=my_collection"
```

**Response:** `202 Accepted`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Job created successfully. Use job_id to check status."
}
```

---

### 2. Batch Upload (Multiple Files - NEW!) 🆕

**Endpoint:** `POST /api/start-embedding-batch`

**Description:** Upload multiple files (2-10) for batch processing into a single collection.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `files` | List[File] | ✅ Yes | 2-10 PDF or PPTX files |
| `collection_name` | string | ❌ No | Collection name for all files (defaults to timestamp) |

**Validation Rules:**
- Minimum files: 2
- Maximum files: 10
- Per-file size limit: 50 MB
- Total batch size limit: 200 MB
- Allowed types: `.pdf`, `.pptx`

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/start-embedding-batch" \
  -F "files=@lecture1.pdf" \
  -F "files=@lecture2.pdf" \
  -F "files=@lecture3.pdf" \
  -F "collection_name=network_security_course"
```

**JavaScript/TypeScript Example:**
```typescript
async function uploadBatchFiles(files: File[], collectionName?: string) {
  const formData = new FormData();
  
  // Add all files (use 'files' as field name, not 'file')
  files.forEach(file => {
    formData.append('files', file);
  });
  
  if (collectionName) {
    formData.append('collection_name', collectionName);
  }
  
  const response = await fetch('http://localhost:8000/api/start-embedding-batch', {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return await response.json();
}

// Usage
const files = [file1, file2, file3]; // File objects from input
const result = await uploadBatchFiles(files, 'my_course');
console.log(`Job ID: ${result.job_id}`);
```

**Success Response:** `202 Accepted`
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "queued",
  "total_files": 3,
  "message": "Batch processing started for 3 files"
}
```

**Error Responses:**

**400 Bad Request - Too Few Files:**
```json
{
  "detail": "Minimum 2 files required for batch upload"
}
```

**400 Bad Request - Too Many Files:**
```json
{
  "detail": "Maximum 10 files allowed per batch"
}
```

**400 Bad Request - Invalid File Type:**
```json
{
  "detail": "File 'document.txt' has invalid type. Allowed types: PDF, PPTX"
}
```

**400 Bad Request - File Too Large:**
```json
{
  "detail": "File 'large-presentation.pptx' exceeds 50MB limit"
}
```

**400 Bad Request - Batch Too Large:**
```json
{
  "detail": "Total batch size (215.3MB) exceeds 200MB limit"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Error creating batch job: [error details]"
}
```

---

### 3. Check Job Status

**Endpoint:** `GET /api/job-status/{job_id}`

**Description:** Check processing status. Returns different structure for batch vs single file jobs.

**Single File Job Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "file_name": "document.pdf",
  "file_type": "pdf",
  "collection_name": "my_documents",
  "created_at": "2025-11-09T10:30:00.000000",
  "started_at": "2025-11-09T10:30:05.000000",
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

**Batch Job Response (QUEUED):**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "queued",
  "is_batch": true,
  "total_files": 3,
  "processed_files": 0,
  "current_file": null,
  "files": [
    {
      "name": "lecture1.pdf",
      "status": "pending",
      "chunks": 0,
      "error": null
    },
    {
      "name": "lecture2.pdf",
      "status": "pending",
      "chunks": 0,
      "error": null
    },
    {
      "name": "lecture3.pdf",
      "status": "pending",
      "chunks": 0,
      "error": null
    }
  ],
  "collection_name": "network_security_course",
  "created_at": "2025-11-09T10:30:00.000000",
  "started_at": null,
  "completed_at": null,
  "error": null
}
```

**Batch Job Response (PROCESSING - File 2 of 3):**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "processing",
  "is_batch": true,
  "total_files": 3,
  "processed_files": 1,
  "current_file": "lecture2.pdf",
  "current_file_progress": {
    "current_step": "generating_embeddings",
    "percentage": 60.0,
    "chunks_processed": 18,
    "total_chunks": 30
  },
  "overall_progress": 43.33,
  "files": [
    {
      "name": "lecture1.pdf",
      "status": "completed",
      "chunks": 42,
      "error": null
    },
    {
      "name": "lecture2.pdf",
      "status": "processing",
      "chunks": 0,
      "error": null
    },
    {
      "name": "lecture3.pdf",
      "status": "pending",
      "chunks": 0,
      "error": null
    }
  ],
  "collection_name": "network_security_course",
  "created_at": "2025-11-09T10:30:00.000000",
  "started_at": "2025-11-09T10:30:05.000000",
  "completed_at": null,
  "error": null
}
```

**Batch Job Response (COMPLETED - All Files Successful):**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "is_batch": true,
  "total_files": 3,
  "processed_files": 3,
  "current_file": null,
  "overall_progress": 100.0,
  "files": [
    {
      "name": "lecture1.pdf",
      "status": "completed",
      "chunks": 42,
      "error": null
    },
    {
      "name": "lecture2.pdf",
      "status": "completed",
      "chunks": 38,
      "error": null
    },
    {
      "name": "lecture3.pdf",
      "status": "completed",
      "chunks": 45,
      "error": null
    }
  ],
  "collection_name": "network_security_course",
  "created_at": "2025-11-09T10:30:00.000000",
  "started_at": "2025-11-09T10:30:05.000000",
  "completed_at": "2025-11-09T10:32:15.000000",
  "metadata": {
    "total_chunks": 125,
    "total_text_length": 45000,
    "processing_time_seconds": 130.5,
    "successful_files": 3,
    "failed_files": 0
  },
  "error": null
}
```

**Batch Job Response (PARTIALLY COMPLETED - 1 File Failed):**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "partially_completed",
  "is_batch": true,
  "total_files": 3,
  "processed_files": 3,
  "current_file": null,
  "overall_progress": 100.0,
  "files": [
    {
      "name": "lecture1.pdf",
      "status": "completed",
      "chunks": 42,
      "error": null
    },
    {
      "name": "lecture2.pdf",
      "status": "failed",
      "chunks": 0,
      "error": "No text could be extracted from the document"
    },
    {
      "name": "lecture3.pdf",
      "status": "completed",
      "chunks": 45,
      "error": null
    }
  ],
  "collection_name": "network_security_course",
  "created_at": "2025-11-09T10:30:00.000000",
  "started_at": "2025-11-09T10:30:05.000000",
  "completed_at": "2025-11-09T10:32:15.000000",
  "metadata": {
    "total_chunks": 87,
    "total_text_length": 31000,
    "processing_time_seconds": 130.5,
    "successful_files": 2,
    "failed_files": 1
  },
  "error": null
}
```

**Job Status Values:**
- `queued` - Job created, waiting for worker
- `processing` - Currently processing files
- `completed` - All files processed successfully
- `partially_completed` - Some files succeeded, some failed
- `failed` - All files failed or job error

**File Status Values:**
- `pending` - Not yet started
- `processing` - Currently being processed
- `completed` - Successfully processed
- `failed` - Processing failed

---

## 📊 Frontend Integration

### Complete React Component Example

```typescript
'use client';

import { useState, useEffect } from 'react';

interface BatchFile {
  name: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  chunks: number;
  error: string | null;
}

interface FileProgress {
  current_step: string;
  percentage: number;
  chunks_processed: number;
  total_chunks: number;
}

interface BatchJob {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'partially_completed' | 'failed';
  is_batch: boolean;
  total_files: number;
  processed_files: number;
  current_file: string | null;
  current_file_progress?: FileProgress;
  overall_progress: number;
  files: BatchFile[];
  collection_name: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  metadata?: {
    total_chunks: number;
    total_text_length: number;
    processing_time_seconds: number;
    successful_files: number;
    failed_files: number;
  };
  error: string | null;
}

export default function BatchDocumentUpload() {
  const [files, setFiles] = useState<File[]>([]);
  const [collectionName, setCollectionName] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<BatchJob | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Upload files
  const handleUpload = async () => {
    if (files.length < 2) {
      setError('Please select at least 2 files');
      return;
    }

    if (files.length > 10) {
      setError('Maximum 10 files allowed');
      return;
    }

    setUploading(true);
    setError(null);

    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    if (collectionName) {
      formData.append('collection_name', collectionName);
    }

    try {
      const response = await fetch('http://localhost:8000/api/start-embedding-batch', {
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
          if (
            data.status === 'completed' || 
            data.status === 'partially_completed' || 
            data.status === 'failed'
          ) {
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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    setFiles(selectedFiles);
    setError(null);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'failed': return 'bg-red-100 text-red-800';
      case 'processing': return 'bg-blue-100 text-blue-800';
      case 'partially_completed': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">Batch Document Upload</h2>

      {!jobId ? (
        <div className="space-y-4">
          <div>
            <label className="block mb-2 font-semibold">
              Select Files (2-10 files, PDF or PPTX)
            </label>
            <input
              type="file"
              accept=".pdf,.pptx"
              multiple
              onChange={handleFileChange}
              className="block w-full"
            />
            {files.length > 0 && (
              <p className="text-sm text-gray-600 mt-2">
                {files.length} file(s) selected
              </p>
            )}
          </div>

          {files.length > 0 && (
            <div className="border rounded p-3 bg-gray-50">
              <p className="font-semibold mb-2">Selected Files:</p>
              <ul className="text-sm space-y-1">
                {files.map((file, idx) => (
                  <li key={idx} className="flex justify-between">
                    <span>{file.name}</span>
                    <span className="text-gray-500">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <label className="block mb-2 font-semibold">
              Collection Name (Optional)
            </label>
            <input
              type="text"
              value={collectionName}
              onChange={(e) => setCollectionName(e.target.value)}
              placeholder="network_security_course"
              className="block w-full px-3 py-2 border rounded"
            />
          </div>

          <button
            onClick={handleUpload}
            disabled={files.length < 2 || uploading}
            className="w-full bg-blue-500 text-white py-2 px-4 rounded disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? 'Uploading...' : `Upload ${files.length} Files`}
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
              {/* Overall Status */}
              <div className="p-4 border rounded">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-semibold">Overall Status:</span>
                  <span className={`px-2 py-1 rounded text-sm ${getStatusColor(job.status)}`}>
                    {job.status.toUpperCase().replace('_', ' ')}
                  </span>
                </div>

                {/* Overall Progress */}
                {job.status === 'processing' && (
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Processing {job.processed_files} of {job.total_files} files</span>
                      <span>{job.overall_progress?.toFixed(0) || 0}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div
                        className="bg-blue-500 h-3 rounded-full transition-all duration-300"
                        style={{ width: `${job.overall_progress || 0}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Current File Progress */}
                {job.current_file && job.current_file_progress && (
                  <div className="mt-3 p-3 bg-blue-50 rounded">
                    <p className="text-sm font-semibold text-blue-800 mb-2">
                      Currently processing: {job.current_file}
                    </p>
                    <div className="text-xs text-blue-700">
                      <p>{job.current_file_progress.current_step.replace('_', ' ')}</p>
                      <div className="flex justify-between mt-1">
                        <span>
                          Chunks: {job.current_file_progress.chunks_processed} / {job.current_file_progress.total_chunks}
                        </span>
                        <span>{job.current_file_progress.percentage.toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Completion Summary */}
                {(job.status === 'completed' || job.status === 'partially_completed') && job.metadata && (
                  <div className={`mt-3 p-3 rounded ${
                    job.status === 'completed' ? 'bg-green-50' : 'bg-yellow-50'
                  }`}>
                    <p className={`text-sm font-semibold mb-2 ${
                      job.status === 'completed' ? 'text-green-800' : 'text-yellow-800'
                    }`}>
                      {job.status === 'completed' ? '✓ All Files Processed' : '⚠ Partially Completed'}
                    </p>
                    <div className={`text-xs space-y-1 ${
                      job.status === 'completed' ? 'text-green-700' : 'text-yellow-700'
                    }`}>
                      <p>Successful: {job.metadata.successful_files} files</p>
                      {job.metadata.failed_files > 0 && (
                        <p>Failed: {job.metadata.failed_files} files</p>
                      )}
                      <p>Total Chunks: {job.metadata.total_chunks}</p>
                      <p>Processing Time: {job.metadata.processing_time_seconds.toFixed(1)}s</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Individual File Status */}
              <div className="border rounded p-4">
                <h3 className="font-semibold mb-3">Files:</h3>
                <div className="space-y-2">
                  {job.files.map((file, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2 bg-gray-50 rounded"
                    >
                      <div className="flex-1">
                        <p className="text-sm font-medium">{file.name}</p>
                        {file.error && (
                          <p className="text-xs text-red-600 mt-1">{file.error}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-3">
                        {file.chunks > 0 && (
                          <span className="text-xs text-gray-600">
                            {file.chunks} chunks
                          </span>
                        )}
                        <span className={`px-2 py-1 rounded text-xs ${getStatusColor(file.status)}`}>
                          {file.status.toUpperCase()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={() => {
                  setJobId(null);
                  setJob(null);
                  setFiles([]);
                }}
                className="w-full bg-gray-500 text-white py-2 px-4 rounded hover:bg-gray-600"
              >
                Upload More Documents
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

---

## 🎯 Key Differences: Single vs Batch

| Feature | Single File | Batch (2-10 Files) |
|---------|-------------|-------------------|
| **Endpoint** | `/api/start-embedding` | `/api/start-embedding-batch` |
| **Field Name** | `file` | `files` (multiple) |
| **Min Files** | 1 | 2 |
| **Max Files** | 1 | 10 |
| **Response** | `job_id` | `job_id` + `total_files` |
| **Progress** | Single file progress | Per-file + overall progress |
| **Status Check** | Standard job object | Job object with `is_batch: true` |
| **Partial Failure** | N/A | Status: `partially_completed` |

---

## ⚠️ Important Notes

### 1. Partial Failures
If some files fail, the job continues processing remaining files. Final status will be `partially_completed`.

### 2. Progress Calculation
```
Overall Progress = (processed_files / total_files) * 100

Example: Processing file 3 of 10
Overall Progress = (2 / 10) * 100 = 20%
(Plus current file's progress within that 10% slice)
```

### 3. Collection Storage
All files in a batch are stored in the **same ChromaDB collection**. This allows unified search across all uploaded documents.

### 4. Polling Strategy
- Poll every **2 seconds** during processing
- Stop polling when status is `completed`, `partially_completed`, or `failed`

### 5. Error Handling
```typescript
try {
  const result = await uploadBatchFiles(files, collectionName);
  // Monitor job_id
} catch (error) {
  // Handle validation errors, network errors
  if (error.message.includes('Minimum 2 files')) {
    // Show user-friendly message
  }
}
```

---

## 📝 Validation Summary

| Validation | Limit | Error Message |
|------------|-------|---------------|
| Min files | 2 | "Minimum 2 files required for batch upload" |
| Max files | 10 | "Maximum 10 files allowed per batch" |
| File type | PDF, PPTX | "File 'X' has invalid type. Allowed types: PDF, PPTX" |
| Per-file size | 50 MB | "File 'X' exceeds 50MB limit" |
| Total batch size | 200 MB | "Total batch size (X MB) exceeds 200MB limit" |

---

## 🚀 Quick Start

**1. Upload 3 files:**
```bash
curl -X POST "http://localhost:8000/api/start-embedding-batch" \
  -F "files=@file1.pdf" \
  -F "files=@file2.pdf" \
  -F "files=@file3.pdf" \
  -F "collection_name=my_collection"
```

**2. Get job_id from response:**
```json
{"job_id": "a1b2c3d4-...", "status": "queued", "total_files": 3}
```

**3. Poll status every 2 seconds:**
```bash
curl "http://localhost:8000/api/job-status/a1b2c3d4-..."
```

**4. Check completion:**
- `status: "completed"` - All files processed ✅
- `status: "partially_completed"` - Some failed ⚠️
- `status: "failed"` - All failed ❌

---

## 📊 Status Flow Diagram

```
Upload Request
      ↓
   QUEUED (all files pending)
      ↓
   PROCESSING
      ├─ File 1: processing → completed ✓
      ├─ File 2: processing → completed ✓
      ├─ File 3: processing → failed ✗
      └─ File 4: processing → completed ✓
      ↓
   PARTIALLY_COMPLETED (3/4 succeeded)
```

---

**Version:** 2.0.0  
**Last Updated:** November 9, 2025  
**Contact:** Check `/docs` for interactive API testing
