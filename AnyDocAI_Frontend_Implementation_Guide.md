# AnyDocAI Frontend Implementation Guide

This guide outlines how to implement the frontend chat page for AnyDocAI using the new API endpoints.

## Chat Page Implementation Overview

The chat page is the core of the AnyDocAI application, allowing users to interact with their documents through AI-powered conversations. Here's how to implement it using the new API endpoints.

## Key Components and API Usage

### 1. Authentication & Session Management

**Components:**
- Login/Register forms
- Authentication state management
- Session persistence

**APIs to Use:**
- `/api/register` - For new user registration
- `/api/login` - For user authentication
- `/api/me` - To verify current user and get user details
- `/api/status` - To check authentication status

**Implementation Notes:**
- Store authentication token in localStorage or secure cookie
- Add token to all subsequent API requests
- Implement authentication state in a context provider

### 2. Document Management Sidebar

**Components:**
- Document list
- Upload button
- Document preview
- Document selection for chat

**APIs to Use:**
- `/api/upload` - For uploading new documents
- `/api/list` - To fetch all user documents
- `/api/{file_id}/preview` - To show document previews
- `/api/{file_id}` (DELETE) - To remove documents

**Implementation Notes:**
- Show upload progress during document upload
- Allow multiple document selection for chat sessions
- Display document metadata (name, type, size)

### 3. Chat Session Management

**Components:**
- Session list
- Create new session button
- Session selection
- Session management (rename, delete)

**APIs to Use:**
- `/api/sessions` (GET) - To list all chat sessions
- `/api/sessions` (POST) - To create new chat sessions
- `/api/sessions/{session_id}` (DELETE) - To delete sessions
- `/api/sessions/{session_id}/documents` (GET) - To get documents in a session
- `/api/sessions/{session_id}/documents` (PUT) - To add documents to a session
- `/api/sessions/{session_id}/documents/{document_id}` (DELETE) - To remove documents from a session

**Implementation Notes:**
- Allow creating empty sessions or sessions with documents
- Show document thumbnails in session list
- Enable drag-and-drop for adding documents to sessions

### 4. Chat Interface

**Components:**
- Message list
- Message input
- AI response rendering
- Source citation display
- Chart/visualization rendering

**APIs to Use:**
- `/api/sessions/{session_id}/messages` (GET) - To fetch message history
- `/api/sessions/{session_id}/messages` (POST) - To send new messages
- `/api/sessions/{session_id}/suggestions` - To get AI-generated question suggestions

**Implementation Notes:**
- Implement optimistic UI updates for sent messages
- Show typing indicators during AI response generation
- Render markdown in AI responses
- Display source citations with links to original documents
- Render charts when chart_data is present in responses

### 5. Agent Mode Toggle

**Components:**
- Agent mode toggle switch
- Agent capabilities explanation

**APIs to Use:**
- Same message endpoint with `use_agent` parameter:
  - `/api/sessions/{session_id}/messages` (POST) with `use_agent: true`

**Implementation Notes:**
- Clearly indicate when agent mode is active
- Explain the difference between regular chat and agent mode
- Show examples of agent capabilities (data analysis, chart generation)

### 6. Suggested Questions (New Feature)

**Components:**
- Suggestion chips/buttons
- Suggestion loading state

**APIs to Use:**
- `/api/sessions/{session_id}/suggestions` - To get AI-generated suggestions based on document content

**Implementation Notes:**
- Show suggestions when a new chat session is created with documents
- Display suggestions as clickable chips/buttons
- Send the suggestion text as a message when clicked
- Show loading state while suggestions are being generated

### 7. Advanced Document Processing (Optional)

**Components:**
- Advanced upload options
- Processing method selection

**APIs to Use:**
- `/api/llama-index/upload` - For specialized document processing
- `/api/llama-index/query` - For direct document querying with advanced options

**Implementation Notes:**
- Only expose these options to advanced users
- Provide UI for selecting processing options
- Explain the benefits of different processing methods

## Implementation Flow

1. **Initial Load:**
   - Authenticate user with `/api/status` and `/api/me`
   - Load document list with `/api/list`
   - Load session list with `/api/sessions`

2. **Creating a New Chat:**
   - Create session with `/api/sessions`
   - Add documents with `/api/sessions/{session_id}/documents`
   - Get suggestions with `/api/sessions/{session_id}/suggestions`

3. **Chat Interaction:**
   - Load message history with `/api/sessions/{session_id}/messages`
   - Send messages with `/api/sessions/{session_id}/messages`
   - Toggle agent mode as needed
   - Display responses with source citations and visualizations

4. **Document Management:**
   - Upload documents as needed with `/api/upload`
   - Add/remove documents from sessions as needed

## Special Considerations

### 1. Error Handling

- Implement proper error handling for all API calls
- Show user-friendly error messages
- Provide retry options for failed operations
- Handle authentication errors and redirect to login

### 2. Loading States

- Show loading indicators for all async operations
- Implement skeleton loaders for initial data fetching
- Use typing indicators during AI response generation

### 3. Responsive Design

- Ensure the chat interface works well on mobile devices
- Implement collapsible sidebars for document and session lists
- Optimize message display for different screen sizes

### 4. Performance Optimization

- Implement pagination for large message histories
- Lazy load document previews
- Cache session and document data
- Debounce user input in message field

## Legacy API Support

If you need to support the legacy chat API for backward compatibility:

- `/api/message` - For one-off queries without creating a session

This can be useful for quick document queries without the overhead of session management.

## Conclusion

By following this implementation guide, you can create a comprehensive chat interface for AnyDocAI that leverages all the new API endpoints, including the suggestions feature we recently implemented. The modular approach allows for incremental development and easy maintenance.

Focus on creating a seamless user experience with proper loading states, error handling, and responsive design to make the chat interface intuitive and efficient.


AnyDocAI Chat Page Implementation Workflow
Here's the complete workflow for implementing the chat page in AnyDocAI, detailing which APIs to call at each step:

Initial Page Load
Authentication Check
Call /api/status to verify if user is authenticated
If not authenticated, redirect to login page
If authenticated, proceed with loading data
Load User Information
Call /api/me to get current user details
Display user information in the UI (name, avatar, etc.)
Load Chat Sessions
Call /api/sessions (GET) to retrieve all user's chat sessions
Display sessions in the sidebar, sorted by most recent
Load Documents Library
Call /api/list to get all user's uploaded documents
Display documents in a separate tab or section for easy access
Session Selection / Creation
Select Existing Session
When user clicks on a session in the sidebar:
Call /api/sessions/{session_id}/messages to load message history
Call /api/sessions/{session_id}/documents to get documents attached to this session
Display messages in the chat area and documents in the document panel
Create New Session
When user clicks "New Chat":
Show session creation dialog with name input and document selection
Call /api/sessions (POST) with session name and selected document IDs
After creation, load the new empty session
Document Selection for New Session
Allow user to select documents from their library
Alternatively, allow direct upload for new session:
Call /api/upload with file data
Once upload completes, add the new document ID to the session
New Session Initialization
Get Suggested Questions
For a new session with documents but no messages:
Call /api/sessions/{session_id}/suggestions to get AI-generated question suggestions
Display these as clickable chips/buttons above the message input
When user clicks a suggestion, use it as the message text
Chat Interaction
Send Message
When user types a message and hits send:
Call /api/sessions/{session_id}/messages (POST) with message text and agent mode toggle
Include use_agent: true parameter if agent mode is enabled
Show loading/typing indicator while waiting for response
Display Response
When response is received:
Display the AI response with proper formatting (markdown)
If response includes sources, display them with links to the source documents
If response includes chart_data, render the appropriate visualization
Message History Management
Load more messages when user scrolls up (implement pagination)
Automatically scroll to bottom when new messages arrive
Document Management During Chat
Add Documents to Session
When user wants to add documents to the current session:
Show document selection dialog with library
Call /api/sessions/{session_id}/documents (PUT) with selected document IDs
Update the document panel to show newly added documents
Remove Documents from Session
When user removes a document from the session:
Call /api/sessions/{session_id}/documents/{document_id} (DELETE)
Update the document panel to reflect changes
Document Preview
When user clicks on a document in the session:
Call /api//{file_id}/preview to get document preview
Display preview in a modal or side panel
Agent Mode
Toggle Agent Mode
Provide a toggle switch for agent mode
When enabled, all subsequent messages use use_agent: true parameter
Visually indicate when agent mode is active
Potentially show different UI elements for agent capabilities (chart options, etc.)
Session Management
Delete Session
When user wants to delete a session:
Show confirmation dialog
Call /api/sessions/{session_id} (DELETE)
Update session list and navigate to another session or create new
Rename Session
If you implement session renaming:
Call appropriate API endpoint (this may be a custom extension)
Update session list to reflect new name
Advanced Features (Optional)
Advanced Document Processing
For power users, provide access to LlamaIndex endpoints:
Call /api/llama-index/upload for specialized document processing
Call /api/llama-index/query for direct document querying with advanced options
Direct Document Query (Legacy Support)
For quick one-off queries without session context:
Call /api/message with document IDs and query
Display response without saving to a session
Error Handling
API Error Handling
Implement proper error handling for all API calls
Show user-friendly error messages
Provide retry options for failed operations
Handle authentication errors (redirect to login)
Real-time Updates (If Supported)
WebSocket Connection (If Available)
Connect to WebSocket for real-time updates
Update UI when new messages or sessions are created
Show typing indicators in real-time
This workflow covers the complete implementation of the chat page, from initial load to all user interactions, using the new API endpoints. The implementation focuses on creating a seamless user experience while efficiently using the backend APIs.