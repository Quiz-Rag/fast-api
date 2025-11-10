# 🤖 Chat Tutor API Documentation - Frontend Integration Guide

**API Version:** 2.0  
**Last Updated:** November 10, 2025  
**Base URL:** `http://localhost:8000/api`

---

## 📋 Overview

The Chat Tutor API provides an interactive, AI-powered tutor bot for Network Security topics with:
- ✅ Real-time streaming responses (Server-Sent Events)
- ✅ Conversation history tracking
- ✅ Friendly, educational personality
- ✅ Prompt injection protection
- ✅ Network Security domain restriction

---

## 🔐 Security Features

### **Input Protection:**
- Automatic sanitization of user messages
- Prompt injection pattern removal
- Domain restriction (NS topics only)

### **Rate Limiting:**
- Maximum 50 messages per session
- Session validation on every request

### **Data Privacy:**
- Session-based conversations
- Optional user identification
- Message history stored securely

---

## 🚀 Quick Start

### **1. Start a Chat Session**
```javascript
const response = await fetch('/api/chat/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_name: 'Alice'  // Optional
  })
});

const data = await response.json();
console.log(data.session_id);  // Save this!
console.log(data.greeting);    // Display to user
```

### **2. Send a Message (with SSE)**
```javascript
const eventSource = new EventSource(
  `/api/chat/message?session_id=${sessionId}&message=${encodeURIComponent(question)}`
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'token') {
    appendToken(data.content);  // Show typing effect
  } else if (data.type === 'done') {
    eventSource.close();
  } else if (data.type === 'error') {
    showError(data.message);
    eventSource.close();
  }
};
```

---

## 📡 API Endpoints

### **1. Start Chat Session**

**Endpoint:** `POST /api/chat/start`

**Description:** Create a new chat session and receive greeting message.

**Request Body:**
```json
{
  "user_id": "user123",      // Optional: User identifier
  "user_name": "Alice"        // Optional: User display name
}
```

**Response:** `201 Created`
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "greeting": "Hello Alice! 👋\n\nI'm your Network Security tutor assistant...",
  "started_at": "2025-11-10T12:30:45.123456"
}
```

**Example (JavaScript):**
```javascript
async function startChat(userName) {
  const response = await fetch('/api/chat/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_name: userName })
  });
  
  if (!response.ok) {
    throw new Error('Failed to start chat');
  }
  
  return await response.json();
}
```

**Example (cURL):**
```bash
curl -X POST "http://localhost:8000/api/chat/start" \
  -H "Content-Type: application/json" \
  -d '{"user_name": "Alice"}'
```

---

### **2. Send Message (SSE Stream)**

**Endpoint:** `POST /api/chat/message`

**Description:** Send a message and receive streaming response via Server-Sent Events.

**⚠️ IMPORTANT:** This endpoint returns a **streaming response**, not JSON!

**Request Body:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "What is SQL injection?"
}
```

**Response:** `200 OK` with `Content-Type: text/event-stream`

**SSE Event Types:**

#### **Event 1: Start**
```
data: {"type": "start", "session_id": "550e8400..."}

```

#### **Event 2: Token (repeated)**
```
data: {"type": "token", "content": "SQL ", "session_id": "550e8400..."}

data: {"type": "token", "content": "injection ", "session_id": "550e8400..."}

data: {"type": "token", "content": "is...", "session_id": "550e8400..."}

```

#### **Event 3: Done**
```
data: {"type": "done", "session_id": "550e8400...", "tokens_used": 145}

```

#### **Event 4: Error (if occurs)**
```
data: {"type": "error", "message": "Session not found", "session_id": "550e8400..."}

```

**Example (JavaScript with EventSource):**
```javascript
function sendMessage(sessionId, message) {
  // Note: EventSource only supports GET, so we need a workaround
  // Option 1: Use fetch with POST and manual SSE parsing
  
  return new Promise((resolve, reject) => {
    fetch('/api/chat/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message })
    }).then(response => {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';
      
      function readStream() {
        reader.read().then(({ done, value }) => {
          if (done) {
            resolve(fullResponse);
            return;
          }
          
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n\n');
          
          lines.forEach(line => {
            if (line.startsWith('data: ')) {
              const data = JSON.parse(line.substring(6));
              
              switch (data.type) {
                case 'token':
                  fullResponse += data.content;
                  onToken(data.content);  // Your callback
                  break;
                case 'done':
                  onComplete(fullResponse);  // Your callback
                  break;
                case 'error':
                  reject(new Error(data.message));
                  break;
              }
            }
          });
          
          readStream();
        });
      }
      
      readStream();
    });
  });
}
```

**Example (React Hook):**
```typescript
import { useState, useCallback } from 'react';

export function useChatStream() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [response, setResponse] = useState('');
  
  const sendMessage = useCallback(async (sessionId: string, message: string) => {
    setIsStreaming(true);
    setResponse('');
    
    const res = await fetch('/api/chat/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message })
    });
    
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.substring(6));
          
          if (data.type === 'token') {
            setResponse(prev => prev + data.content);
          } else if (data.type === 'error') {
            throw new Error(data.message);
          } else if (data.type === 'done') {
            setIsStreaming(false);
            return;
          }
        }
      }
    }
  }, []);
  
  return { sendMessage, isStreaming, response };
}
```

---

### **3. Get Chat History**

**Endpoint:** `GET /api/chat/{session_id}/history`

**Description:** Retrieve full conversation history for a session.

**Parameters:**
- `session_id` (path): UUID of the chat session

**Response:** `200 OK`
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    {
      "role": "assistant",
      "content": "Hello! 👋 I'm your Network Security tutor...",
      "created_at": "2025-11-10T12:30:45.123456",
      "tokens_used": null
    },
    {
      "role": "user",
      "content": "What is SQL injection?",
      "created_at": "2025-11-10T12:31:20.654321",
      "tokens_used": null
    },
    {
      "role": "assistant",
      "content": "SQL injection is a web security vulnerability...",
      "created_at": "2025-11-10T12:31:25.789012",
      "tokens_used": 145
    }
  ],
  "message_count": 3,
  "started_at": "2025-11-10T12:30:45.123456",
  "last_message_at": "2025-11-10T12:31:25.789012"
}
```

**Example (JavaScript):**
```javascript
async function getChatHistory(sessionId) {
  const response = await fetch(`/api/chat/${sessionId}/history`);
  
  if (!response.ok) {
    throw new Error('Failed to get history');
  }
  
  return await response.json();
}
```

**Example (cURL):**
```bash
curl "http://localhost:8000/api/chat/550e8400-e29b-41d4-a716-446655440000/history"
```

---

### **4. Get Session Info**

**Endpoint:** `GET /api/chat/{session_id}/info`

**Description:** Get basic information about a session without full history.

**Parameters:**
- `session_id` (path): UUID of the chat session

**Response:** `200 OK`
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user123",
  "user_name": "Alice",
  "message_count": 10,
  "started_at": "2025-11-10T12:30:45.123456",
  "last_message_at": "2025-11-10T12:45:20.123456",
  "is_active": true
}
```

**Example (JavaScript):**
```javascript
async function getSessionInfo(sessionId) {
  const response = await fetch(`/api/chat/${sessionId}/info`);
  return await response.json();
}
```

---

### **5. End Chat Session**

**Endpoint:** `DELETE /api/chat/{session_id}`

**Description:** Mark a chat session as inactive (soft delete).

**Parameters:**
- `session_id` (path): UUID of the chat session

**Response:** `204 No Content`

**Example (JavaScript):**
```javascript
async function endChat(sessionId) {
  const response = await fetch(`/api/chat/${sessionId}`, {
    method: 'DELETE'
  });
  
  if (!response.ok) {
    throw new Error('Failed to end session');
  }
}
```

**Example (cURL):**
```bash
curl -X DELETE "http://localhost:8000/api/chat/550e8400-e29b-41d4-a716-446655440000"
```

---

## 🎨 Complete React Component Example

```typescript
import React, { useState, useEffect, useRef } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export function ChatTutor() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Start chat session
  useEffect(() => {
    async function startChat() {
      const response = await fetch('/api/chat/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_name: 'Student' })
      });
      
      const data = await response.json();
      setSessionId(data.session_id);
      
      setMessages([{
        role: 'assistant',
        content: data.greeting,
        timestamp: data.started_at
      }]);
    }
    
    startChat();
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentResponse]);

  // Send message
  async function sendMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || !sessionId || isStreaming) return;

    const userMessage = input.trim();
    setInput('');
    
    // Add user message
    setMessages(prev => [...prev, {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    }]);

    setIsStreaming(true);
    setCurrentResponse('');

    try {
      const response = await fetch('/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: userMessage
        })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.substring(6));

            if (data.type === 'token') {
              setCurrentResponse(prev => prev + data.content);
            } else if (data.type === 'done') {
              // Save complete response
              setMessages(prev => [...prev, {
                role: 'assistant',
                content: currentResponse,
                timestamp: new Date().toISOString()
              }]);
              setCurrentResponse('');
              setIsStreaming(false);
            } else if (data.type === 'error') {
              alert('Error: ' + data.message);
              setCurrentResponse('');
              setIsStreaming(false);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error:', error);
      setIsStreaming(false);
      setCurrentResponse('');
    }
  }

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <div className="role">{msg.role === 'user' ? '👤' : '🤖'}</div>
            <div className="content">{msg.content}</div>
          </div>
        ))}
        
        {/* Streaming response */}
        {currentResponse && (
          <div className="message assistant streaming">
            <div className="role">🤖</div>
            <div className="content">
              {currentResponse}
              <span className="cursor">▋</span>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={sendMessage} className="input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask me about Network Security..."
          disabled={isStreaming}
          maxLength={500}
        />
        <button type="submit" disabled={isStreaming || !input.trim()}>
          {isStreaming ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  );
}
```

---

## ❌ Error Handling

### **Common Error Responses:**

#### **1. Session Not Found (404)**
```json
{
  "detail": "Session 550e8400... not found"
}
```

#### **2. Session Inactive (400)**
```json
{
  "detail": "Session is no longer active"
}
```

#### **3. Message Limit Reached (400)**
```json
{
  "detail": "Session message limit reached (50 messages)"
}
```

#### **4. Invalid Input (400)**
```json
{
  "detail": "Message is too short or contains only invalid characters"
}
```

### **Error Handling Pattern:**

```typescript
async function handleChatError(response: Response) {
  if (!response.ok) {
    const error = await response.json();
    
    switch (response.status) {
      case 404:
        // Session not found - restart chat
        return startNewSession();
      
      case 400:
        if (error.detail.includes('limit reached')) {
          // Show message limit warning
          alert('Chat session limit reached. Starting new session...');
          return startNewSession();
        }
        // Other validation errors
        alert(error.detail);
        break;
      
      case 500:
        // Server error
        alert('Server error. Please try again.');
        break;
    }
    
    throw new Error(error.detail);
  }
}
```

---

## 🧪 Testing Examples

### **Test 1: Start and Send Message**
```bash
# 1. Start session
SESSION_ID=$(curl -s -X POST "http://localhost:8000/api/chat/start" \
  -H "Content-Type: application/json" \
  -d '{"user_name": "Test User"}' | jq -r '.session_id')

echo "Session ID: $SESSION_ID"

# 2. Send message (view streaming response)
curl -X POST "http://localhost:8000/api/chat/message" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"What is encryption?\"}"
```

### **Test 2: Get History**
```bash
curl "http://localhost:8000/api/chat/$SESSION_ID/history" | jq
```

### **Test 3: End Session**
```bash
curl -X DELETE "http://localhost:8000/api/chat/$SESSION_ID"
```

---

## 💡 Best Practices

### **1. Session Management**
```javascript
// Store session ID in localStorage or state management
localStorage.setItem('chatSessionId', sessionId);

// Retrieve on page load
const savedSessionId = localStorage.getItem('chatSessionId');
if (savedSessionId) {
  // Validate session still exists
  checkSessionValidity(savedSessionId);
}
```

### **2. Message Validation**
```javascript
function validateMessage(message) {
  if (!message || message.trim().length < 3) {
    return 'Message must be at least 3 characters';
  }
  if (message.length > 500) {
    return 'Message must be less than 500 characters';
  }
  return null;
}
```

### **3. Streaming Performance**
```javascript
// Buffer tokens for smoother animation
let tokenBuffer = '';
let bufferTimeout;

function bufferToken(token) {
  tokenBuffer += token;
  
  clearTimeout(bufferTimeout);
  bufferTimeout = setTimeout(() => {
    displayTokens(tokenBuffer);
    tokenBuffer = '';
  }, 50); // Update UI every 50ms
}
```

### **4. Retry Logic**
```javascript
async function sendMessageWithRetry(sessionId, message, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await sendMessage(sessionId, message);
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
}
```

---

## 🎯 Quick Reference

| Endpoint | Method | Purpose | Streaming |
|----------|--------|---------|-----------|
| `/api/chat/start` | POST | Create session | No |
| `/api/chat/message` | POST | Send message | **Yes (SSE)** |
| `/api/chat/{id}/history` | GET | Get history | No |
| `/api/chat/{id}/info` | GET | Session info | No |
| `/api/chat/{id}` | DELETE | End session | No |

---

## 📝 TypeScript Types

```typescript
// Request types
interface ChatStartRequest {
  user_id?: string;
  user_name?: string;
}

interface ChatMessageRequest {
  session_id: string;
  message: string;
}

// Response types
interface ChatStartResponse {
  session_id: string;
  greeting: string;
  started_at: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  tokens_used?: number;
}

interface ChatHistoryResponse {
  session_id: string;
  messages: ChatMessage[];
  message_count: number;
  started_at: string;
  last_message_at: string;
}

interface ChatSessionInfo {
  session_id: string;
  user_id?: string;
  user_name?: string;
  message_count: number;
  started_at: string;
  last_message_at: string;
  is_active: boolean;
}

// SSE event types
interface SSEToken {
  type: 'token';
  content: string;
  session_id: string;
}

interface SSEDone {
  type: 'done';
  session_id: string;
  tokens_used: number;
}

interface SSEError {
  type: 'error';
  message: string;
  session_id: string;
}

type SSEEvent = SSEToken | SSEDone | SSEError;
```

---

## 🆘 Troubleshooting

### **Issue: SSE Connection Closes Immediately**
**Solution:** Check CORS headers and ensure no nginx buffering:
```javascript
headers: {
  'Cache-Control': 'no-cache',
  'X-Accel-Buffering': 'no'
}
```

### **Issue: Tokens Not Streaming**
**Solution:** Use proper stream reading, don't await full response:
```javascript
// ❌ Wrong
const data = await response.json();

// ✅ Correct
const reader = response.body.getReader();
// Process chunks as they arrive
```

### **Issue: Session Expired**
**Solution:** Implement session validation before sending:
```javascript
const info = await fetch(`/api/chat/${sessionId}/info`);
if (!info.ok) {
  // Start new session
}
```

---

**🎉 Ready to integrate! Check `/docs` for interactive API testing.**
