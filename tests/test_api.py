"""
Tests for the API endpoints.
"""
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app

client = TestClient(app)

class TestDocumentsAPI:
    """Tests for the documents API endpoints."""
    
    @patch("app.api.routes.documents.document_processor.process_document")
    def test_upload_document(self, mock_process_document):
        """Test document upload endpoint."""
        # Mock the process_document method
        mock_process_document.return_value = {
            "file_id": "test_file_id",
            "file_type": "txt",
            "file_name": "test.txt",
            "user_id": "test_user_id",
            "status": "success"
        }
        
        # Create a test file
        test_file_content = b"Test file content"
        
        # Make the request
        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.txt", test_file_content, "text/plain")},
            data={"user_id": "test_user_id"}
        )
        
        # Check the response
        assert response.status_code == 200
        data = response.json()
        assert data["file_name"] == "test.txt"
        assert data["status"] == "processing"
    
    def test_list_documents(self):
        """Test document listing endpoint."""
        # Make the request
        response = client.get("/api/documents/list/test_user_id")
        
        # Check the response
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data

class TestChatAPI:
    """Tests for the chat API endpoints."""
    
    @patch("app.api.routes.chat.simple_combined_agent.process_request")
    async def test_chat_message_with_agent(self, mock_process_request):
        """Test chat message endpoint with agent."""
        # Mock the process_request method
        mock_process_request.return_value = {
            "response": "Test response",
            "query": "Test message",
            "file_ids": ["test_file_id"],
            "user_id": "test_user_id",
            "timestamp": "2023-01-01T00:00:00"
        }
        
        # Make the request
        response = client.post(
            "/api/chat/message",
            json={
                "message": "Test message",
                "user_id": "test_user_id",
                "file_ids": ["test_file_id"],
                "use_agent": True
            }
        )
        
        # Check the response
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Test response"
        assert data["message"] == "Test message"
    
    @patch("app.api.routes.chat.rag_service.chat_with_documents")
    async def test_chat_message_with_rag(self, mock_chat_with_documents):
        """Test chat message endpoint with RAG."""
        # Mock the chat_with_documents method
        mock_chat_with_documents.return_value = {
            "response": "Test response",
            "message": "Test message",
            "file_ids": ["test_file_id"],
            "user_id": "test_user_id",
            "timestamp": "2023-01-01T00:00:00",
            "sources": []
        }
        
        # Make the request
        response = client.post(
            "/api/chat/message",
            json={
                "message": "Test message",
                "user_id": "test_user_id",
                "file_ids": ["test_file_id"],
                "use_agent": False
            }
        )
        
        # Check the response
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Test response"
        assert data["message"] == "Test message"

class TestUsersAPI:
    """Tests for the users API endpoints."""
    
    def test_register_user(self):
        """Test user registration endpoint."""
        # Make the request
        response = client.post(
            "/api/users/register",
            json={
                "email": "test@example.com",
                "password": "password123",
                "name": "Test User"
            }
        )
        
        # Check the response
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"
    
    def test_login_user(self):
        """Test user login endpoint."""
        # Make the request
        response = client.post(
            "/api/users/login",
            json={
                "email": "test@example.com",
                "password": "password123"
            }
        )
        
        # Check the response
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "token" in data
