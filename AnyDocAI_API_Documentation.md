# AnyDocAI API Documentation

This document provides comprehensive documentation for all AnyDocAI API endpoints, including request/response examples and implementation guidance for frontend development.

## Table of Contents

1. [Authentication APIs](#authentication-apis)
2. [Document APIs](#document-apis)
3. [Chat APIs](#chat-apis)
4. [Agent APIs](#agent-apis)
5. [Implementation Examples](#implementation-examples)

## Base URL

All API endpoints are prefixed with `/api`.

## Authentication APIs

### Register User

Register a new user in the system.

- **Endpoint**: `POST /api/auth/register`
- **When to use**: During user signup
- **Authentication**: None required

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "John Doe",
  "plan": "free",
  "created_at": "2023-05-11T17:39:35.000Z"
}
```

### Login User

Authenticate a user and get an access token.

- **Endpoint**: `POST /api/auth/login`
- **When to use**: When user logs in
- **Authentication**: None required

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "plan": "free",
  "created_at": "2023-05-11T17:39:35.000Z",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Get Current User

Get information about the currently authenticated user.

- **Endpoint**: `GET /api/auth/me`
- **When to use**: To verify authentication or get user details
- **Authentication**: Bearer token required

**Request Headers**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "John Doe",
  "plan": "free",
  "created_at": "2023-05-11T17:39:35.000Z"
}
```

## Document APIs

### Upload Document

Upload a document for processing.

- **Endpoint**: `POST /api/documents/upload`
- **When to use**: When user wants to upload a new document
- **Authentication**: Bearer token required
- **Content Type**: `multipart/form-data`

**Request**:
```
file: [Binary file data]
```

**Response**:
```json
{
  "id": "ec3fadb9-4d33-407b-b576-171f65e3056d",
  "file_name": "example.pdf",
  "file_type": "pdf",
  "file_size": 1048576,
  "status": "pending",
  "created_at": "2023-05-11T17:39:35.000Z"
}
```

### List Documents

Get a list of all documents uploaded by the user.

- **Endpoint**: `GET /api/documents`
- **When to use**: To display user's document library
- **Authentication**: Bearer token required

**Response**:
```json
{
  "documents": [
    {
      "id": "ec3fadb9-4d33-407b-b576-171f65e3056d",
      "file_name": "example.pdf",
      "file_type": "pdf",
      "file_size": 1048576,
      "status": "processed",
      "created_at": "2023-05-11T17:39:35.000Z"
    },
    {
      "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "file_name": "data.xlsx",
      "file_type": "xlsx",
      "file_size": 524288,
      "status": "processed",
      "created_at": "2023-05-10T14:30:22.000Z"
    }
  ],
  "total": 2
}
```

### Get Document Details

Get details about a specific document.

- **Endpoint**: `GET /api/documents/{document_id}`
- **When to use**: When displaying document details
- **Authentication**: Bearer token required

**Response**:
```json
{
  "id": "ec3fadb9-4d33-407b-b576-171f65e3056d",
  "file_name": "example.pdf",
  "file_type": "pdf",
  "file_size": 1048576,
  "status": "processed",
  "created_at": "2023-05-11T17:39:35.000Z",
  "page_count": 15,
  "has_images": true
}
```

### Delete Document

Delete a document from the system.

- **Endpoint**: `DELETE /api/documents/{document_id}`
- **When to use**: When user wants to remove a document
- **Authentication**: Bearer token required

**Response**:
```json
{
  "id": "ec3fadb9-4d33-407b-b576-171f65e3056d",
  "status": "deleted",
  "message": "Document deleted successfully"
}
```

## Chat APIs

### Create Chat Session

Create a new chat session, optionally with documents.

- **Endpoint**: `POST /api/chat/sessions`
- **When to use**: When starting a new chat
- **Authentication**: Bearer token required

**Request Body**:
```json
{
  "name": "Research Analysis",
  "document_ids": ["ec3fadb9-4d33-407b-b576-171f65e3056d", "7c9e6679-7425-40de-944b-e07fc1f90ae7"]
}
```

**Response**:
```json
{
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Research Analysis",
  "document_ids": ["ec3fadb9-4d33-407b-b576-171f65e3056d", "7c9e6679-7425-40de-944b-e07fc1f90ae7"],
  "created_at": "2023-05-11T17:39:35.000Z"
}
```

### List Chat Sessions

Get a list of all chat sessions for the user.

- **Endpoint**: `GET /api/chat/sessions`
- **When to use**: When displaying chat history
- **Authentication**: Bearer token required

**Response**:
```json
{
  "sessions": [
    {
      "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "Research Analysis",
      "created_at": "2023-05-11T17:39:35.000Z",
      "last_message_at": "2023-05-11T18:42:12.000Z",
      "document_ids": ["ec3fadb9-4d33-407b-b576-171f65e3056d", "7c9e6679-7425-40de-944b-e07fc1f90ae7"]
    }
  ]
}
```

### Get Session Messages

Get all messages for a specific chat session.

- **Endpoint**: `GET /api/chat/sessions/{session_id}/messages`
- **When to use**: When opening a chat session
- **Authentication**: Bearer token required

**Response**:
```json
{
  "messages": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "role": "user",
      "content": "What are the key findings in these documents?",
      "timestamp": "2023-05-11T17:40:35.000Z",
      "metadata": {}
    },
    {
      "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "role": "assistant",
      "content": "Based on the documents, the key findings are...",
      "timestamp": "2023-05-11T17:40:38.000Z",
      "metadata": {
        "sources": [
          {
            "text": "The study found that...",
            "metadata": {
              "file_id": "ec3fadb9-4d33-407b-b576-171f65e3056d",
              "page_number": 5
            }
          }
        ]
      }
    }
  ]
}
```

### Send Message

Send a message in a chat session.

- **Endpoint**: `POST /api/chat/sessions/{session_id}/messages`
- **When to use**: When user sends a message in chat
- **Authentication**: Bearer token required

**Request Body**:
```json
{
  "message": "Summarize the main points in these documents",
  "use_agent": false
}
```

**Response**:
```json
{
  "response": "Based on the documents, the main points are...",
  "message": "Summarize the main points in these documents",
  "file_ids": ["ec3fadb9-4d33-407b-b576-171f65e3056d", "7c9e6679-7425-40de-944b-e07fc1f90ae7"],
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2023-05-11T17:45:22.000Z",
  "sources": [
    {
      "text": "The document states that...",
      "metadata": {
        "file_id": "ec3fadb9-4d33-407b-b576-171f65e3056d",
        "page_number": 3
      },
      "score": 0.92
    }
  ]
}
```

### Get Suggested Queries

Get suggested queries based on documents in a chat session.

- **Endpoint**: `GET /api/chat/sessions/{session_id}/suggestions`
- **When to use**: When a user creates a new chat session with documents but has no previous messages
- **Authentication**: Bearer token required

**Response**:
```json
{
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "suggestions": [
    "What are the key findings in the research paper?",
    "Can you analyze the sales data in the Excel spreadsheet?",
    "What are the main conclusions from these documents?",
    "How do the quarterly results compare to previous years?",
    "What recommendations are made in the report?"
  ]
}
```

### Add Documents to Session

Add documents to an existing chat session.

- **Endpoint**: `PUT /api/chat/sessions/{session_id}/documents`
- **When to use**: When user wants to add more documents to an existing chat
- **Authentication**: Bearer token required

**Request Body**:
```json
{
  "document_ids": ["9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"]
}
```

**Response**:
```json
{
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "document_ids": ["ec3fadb9-4d33-407b-b576-171f65e3056d", "7c9e6679-7425-40de-944b-e07fc1f90ae7", "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"],
  "added_document_ids": ["9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"],
  "updated_at": "2023-05-11T18:30:00.000Z"
}
```

### Remove Document from Session

Remove a document from a chat session.

- **Endpoint**: `DELETE /api/chat/sessions/{session_id}/documents/{document_id}`
- **When to use**: When user wants to remove a document from the current chat
- **Authentication**: Bearer token required

**Response**:
```json
{
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "document_ids": ["ec3fadb9-4d33-407b-b576-171f65e3056d"],
  "removed_document_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "updated_at": "2023-05-11T18:35:00.000Z"
}
```

## Agent APIs

### Process Agent Request

Process a request using the agent's advanced capabilities.

- **Endpoint**: `POST /api/agent/process`
- **When to use**: For complex queries requiring multi-step reasoning, data analysis, or chart generation
- **Authentication**: Bearer token required

**Request Body**:
```json
{
  "content": "Analyze the sales data and create a chart showing quarterly trends",
  "file_ids": ["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

**Response**:
```json
{
  "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "role": "assistant",
  "content": "I've analyzed the sales data and created a chart showing quarterly trends. The data shows a 15% increase in Q3 compared to Q2...",
  "created_at": "2023-05-11T18:40:00.000Z",
  "file_ids": ["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "agent_result": {
    "response": "I've analyzed the sales data and created a chart showing quarterly trends...",
    "chart_data": {
      "type": "line",
      "data": {
        "labels": ["Q1", "Q2", "Q3", "Q4"],
        "datasets": [
          {
            "label": "Sales 2023",
            "data": [12500, 17800, 20500, 23100]
          }
        ]
      }
    }
  }
}
```

## Implementation Examples

### Authentication Flow

```javascript
// Registration
const registerUser = async (userData) => {
  try {
    const response = await axios.post('/api/auth/register', userData);
    localStorage.setItem('token', response.data.token);
    return response.data;
  } catch (error) {
    console.error('Registration failed:', error);
    throw error;
  }
};

// Login
const loginUser = async (credentials) => {
  try {
    const response = await axios.post('/api/auth/login', credentials);
    localStorage.setItem('token', response.data.token);
    return response.data;
  } catch (error) {
    console.error('Login failed:', error);
    throw error;
  }
};

// Setting up axios with authentication
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to all requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);
```

### Document Upload and Management

```javascript
// Upload a document
const uploadDocument = async (file) => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        console.log(`Upload progress: ${percentCompleted}%`);
        // Update UI with progress
      },
    });

    return response.data;
  } catch (error) {
    console.error('Document upload failed:', error);
    throw error;
  }
};

// List all documents
const listDocuments = async () => {
  try {
    const response = await api.get('/documents');
    return response.data.documents;
  } catch (error) {
    console.error('Failed to fetch documents:', error);
    throw error;
  }
};

// Delete a document
const deleteDocument = async (documentId) => {
  try {
    const response = await api.delete(`/documents/${documentId}`);
    return response.data;
  } catch (error) {
    console.error('Failed to delete document:', error);
    throw error;
  }
};
```

### Chat Session Management

```javascript
// Create a new chat session
const createChatSession = async (name, documentIds = []) => {
  try {
    const response = await api.post('/chat/sessions', {
      name,
      document_ids: documentIds
    });
    return response.data;
  } catch (error) {
    console.error('Failed to create chat session:', error);
    throw error;
  }
};

// List all chat sessions
const listChatSessions = async () => {
  try {
    const response = await api.get('/chat/sessions');
    return response.data.sessions;
  } catch (error) {
    console.error('Failed to fetch chat sessions:', error);
    throw error;
  }
};

// Get messages for a session
const getChatMessages = async (sessionId) => {
  try {
    const response = await api.get(`/chat/sessions/${sessionId}/messages`);
    return response.data.messages;
  } catch (error) {
    console.error('Failed to fetch chat messages:', error);
    throw error;
  }
};

// Send a message in a chat session
const sendChatMessage = async (sessionId, message, useAgent = false) => {
  try {
    const response = await api.post(`/chat/sessions/${sessionId}/messages`, {
      message,
      use_agent: useAgent
    });
    return response.data;
  } catch (error) {
    console.error('Failed to send message:', error);
    throw error;
  }
};

// Get suggested queries for a new chat session
const getSuggestedQueries = async (sessionId) => {
  try {
    const response = await api.get(`/chat/sessions/${sessionId}/suggestions`);
    return response.data.suggestions;
  } catch (error) {
    console.error('Failed to fetch suggestions:', error);
    return []; // Return empty array as fallback
  }
};
```

### Agent Functionality

```javascript
// Process a request with the agent
const processAgentRequest = async (content, fileIds, sessionId) => {
  try {
    const response = await api.post('/agent/process', {
      content,
      file_ids: fileIds,
      session_id: sessionId
    });

    return response.data;
  } catch (error) {
    console.error('Agent processing failed:', error);
    throw error;
  }
};

// Render a chart from agent response
const renderChart = (chartData, containerId) => {
  if (!chartData) return null;

  // Using Chart.js as an example
  const ctx = document.getElementById(containerId).getContext('2d');
  return new Chart(ctx, {
    type: chartData.type,
    data: chartData.data,
    options: chartData.options || {}
  });
};
```

### Complete Chat Interface Example

```javascript
// React component example for a chat interface
const ChatInterface = ({ sessionId }) => {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [useAgent, setUseAgent] = useState(false);

  // Load messages and suggestions when component mounts
  useEffect(() => {
    const loadChatData = async () => {
      try {
        const messagesData = await getChatMessages(sessionId);
        setMessages(messagesData);

        // If no messages, get suggestions
        if (messagesData.length === 0) {
          const suggestionsData = await getSuggestedQueries(sessionId);
          setSuggestions(suggestionsData);
        }
      } catch (error) {
        console.error('Error loading chat data:', error);
      }
    };

    loadChatData();
  }, [sessionId]);

  // Handle sending a message
  const handleSendMessage = async (content) => {
    try {
      setLoading(true);

      // Optimistically add user message to UI
      const userMessage = {
        id: Date.now().toString(),
        role: 'user',
        content,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, userMessage]);
      setNewMessage('');

      // Send to API
      const response = await sendChatMessage(sessionId, content, useAgent);

      // Add assistant response to UI
      const assistantMessage = {
        id: response.id || Date.now().toString() + '-assistant',
        role: 'assistant',
        content: response.response,
        timestamp: response.timestamp,
        metadata: {
          sources: response.sources || [],
          chart_data: response.chart_data
        }
      };

      setMessages(prev => [...prev, assistantMessage]);

      // If there's chart data, render it
      if (response.chart_data) {
        renderChart(response.chart_data, 'chart-container');
      }

    } catch (error) {
      console.error('Error sending message:', error);
      // Show error to user
    } finally {
      setLoading(false);
      // Clear suggestions after first message
      setSuggestions([]);
    }
  };

  // Handle clicking a suggestion
  const handleSuggestionClick = (suggestion) => {
    handleSendMessage(suggestion);
  };

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {messages.map(message => (
          <div key={message.id} className={`message ${message.role}`}>
            <div className="message-content">{message.content}</div>
            {message.metadata?.sources && message.metadata.sources.length > 0 && (
              <div className="sources">
                <h4>Sources:</h4>
                {message.metadata.sources.map((source, index) => (
                  <div key={index} className="source">
                    {source.text}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="message assistant loading">
            <div className="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        )}
      </div>

      {suggestions.length > 0 && (
        <div className="suggestions">
          <h3>Suggested questions:</h3>
          <div className="suggestion-chips">
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                className="suggestion-chip"
                onClick={() => handleSuggestionClick(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      <div id="chart-container" className="chart-container"></div>

      <div className="message-input">
        <div className="agent-toggle">
          <label>
            <input
              type="checkbox"
              checked={useAgent}
              onChange={() => setUseAgent(!useAgent)}
            />
            Use Agent Mode
          </label>
        </div>

        <textarea
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          placeholder="Type your message..."
          disabled={loading}
        />

        <button
          onClick={() => handleSendMessage(newMessage)}
          disabled={!newMessage.trim() || loading}
        >
          Send
        </button>
      </div>
    </div>
  );
};
```

## Best Practices for Frontend Implementation

### Error Handling

Always implement proper error handling for API calls:

1. **User-friendly error messages**: Transform technical error messages into user-friendly notifications
2. **Retry mechanisms**: For transient errors like network issues
3. **Fallback content**: Show fallback UI when data can't be loaded

```javascript
// Example of enhanced error handling
const sendMessageWithErrorHandling = async (sessionId, message, useAgent) => {
  try {
    // Show loading state
    setLoading(true);

    // Try to send the message
    const response = await sendChatMessage(sessionId, message, useAgent);
    return response;
  } catch (error) {
    // Check for specific error types
    if (error.response) {
      // Server responded with an error status
      switch (error.response.status) {
        case 401:
          // Unauthorized - redirect to login
          showNotification("Your session has expired. Please log in again.");
          redirectToLogin();
          break;
        case 404:
          // Session not found
          showNotification("Chat session not found. It may have been deleted.");
          break;
        case 429:
          // Rate limiting
          showNotification("You've sent too many messages. Please wait a moment and try again.");
          break;
        default:
          showNotification("An error occurred while sending your message. Please try again.");
      }
    } else if (error.request) {
      // Network error
      showNotification("Network error. Please check your connection and try again.");
    } else {
      // Other errors
      showNotification("An unexpected error occurred. Please try again.");
    }

    // Log for debugging
    console.error("Message error details:", error);

    // Rethrow or return error info
    throw error;
  } finally {
    // Always clean up loading state
    setLoading(false);
  }
};
```

### Performance Optimization

1. **Debounce user input**: Prevent excessive API calls during typing
2. **Pagination**: Implement pagination for listing documents and chat sessions
3. **Caching**: Cache document lists and chat sessions to reduce API calls
4. **Lazy loading**: Load chat history in chunks as the user scrolls

### Security Considerations

1. **Token storage**: Store authentication tokens securely (HttpOnly cookies when possible)
2. **Input validation**: Validate all user inputs before sending to the API
3. **Content Security Policy**: Implement CSP to prevent XSS attacks
4. **Sensitive data**: Don't store sensitive document content in local storage

## Conclusion

This documentation provides a comprehensive guide to implementing the AnyDocAI frontend using the available API endpoints. By following these guidelines and examples, you can create a robust, user-friendly interface for document chat and analysis.

Key points to remember:

1. **Authentication** is required for most endpoints
2. **Document management** is the foundation of the application
3. **Chat sessions** organize conversations around specific documents
4. **Agent mode** provides advanced capabilities for complex queries
5. **Suggested queries** help users get started with new documents

For any additional questions or clarifications, please refer to the backend code or contact the development team.
