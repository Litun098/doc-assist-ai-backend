# AnyDocAI Todo List

This document outlines features and APIs that need to be implemented in future iterations of the AnyDocAI application.

## Backend API Endpoints to Implement

### User Profile Management
- **PUT /api/auth/update-profile**: Update user profile information
  - Request: `{ full_name, email }`
  - Response: Updated user information
  - Status: Not implemented

- **PUT /api/auth/change-password**: Change user password
  - Request: `{ current_password, new_password }`
  - Response: Success message
  - Status: Not implemented

- **POST /api/auth/enable-2fa**: Enable two-factor authentication
  - Response: 2FA setup information (QR code, backup codes)
  - Status: Not implemented

- **POST /api/auth/verify-2fa**: Verify two-factor authentication
  - Request: `{ code }`
  - Response: Success message
  - Status: Not implemented

- **DELETE /api/auth/disable-2fa**: Disable two-factor authentication
  - Request: `{ code }`
  - Response: Success message
  - Status: Not implemented

- **DELETE /api/auth/delete-account**: Delete user account
  - Request: `{ password }`
  - Response: Success message
  - Status: Not implemented

### Document Management
- **DELETE /api/documents/{document_id}**: Delete a document
  - Status: Implemented

### Chat Session Management
- **PUT /api/chat/sessions/{session_id}**: Update a chat session (rename, etc.)
  - Request: `{ name }`
  - Response: Updated session information
  - Status: Not implemented

- **GET /api/chat/sessions/{session_id}**: Get a specific chat session
  - Response: Session details
  - Status: Implemented in frontend, needs backend implementation

- **GET /api/chat/sessions/{session_id}/documents**: Get documents in a session
  - Response: List of documents in the session
  - Status: Implemented in frontend, needs backend implementation

## Frontend Features to Implement

### User Profile Page
- ✅ Create a profile page where users can view their information
- Implement profile update functionality (requires backend API)
- Implement form validation for profile updates
- Add ability to change password (requires backend API)
- Add two-factor authentication setup (requires backend API)
- Add account deletion functionality (requires backend API)
- Add profile picture upload functionality (requires backend API)

### Document Management
- Implement document deletion functionality
- Add document preview functionality
- Implement document search functionality

### Chat Session Management
- Implement session renaming functionality (requires backend API)
- ✅ Add ability to add/remove documents from existing sessions
- ✅ Implement session deletion with confirmation

## Infrastructure Improvements

### Authentication
- Implement email verification flow
- Add password reset functionality
- Implement social login options (Google, GitHub)

### Performance
- Implement caching for frequently accessed data
- Optimize document processing for large files
- Add pagination for document and session lists

### Security
- Implement rate limiting for API endpoints
- Add CSRF protection
- Implement proper error handling and logging

## Testing
- Add unit tests for backend services
- Add integration tests for API endpoints
- Add end-to-end tests for critical user flows
