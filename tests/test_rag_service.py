"""
Tests for the RAG service.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.rag_service import RAGService

class TestRAGService:
    """Tests for the RAGService class."""
    
    def setup_method(self):
        """Set up the test environment."""
        self.service = RAGService()
    
    @patch("app.services.rag_service.WeaviateVectorStore")
    def test_get_vector_store(self, mock_vector_store):
        """Test vector store creation."""
        # Mock the weaviate client
        self.service.weaviate_client = MagicMock()
        
        # Get the vector store
        vector_store = self.service.get_vector_store("test_user_id")
        
        # Check that the vector store was created
        mock_vector_store.assert_called_once()
    
    @patch("app.services.rag_service.RAGService.get_vector_store")
    @patch("app.services.rag_service.VectorStoreIndex")
    @patch("app.services.rag_service.VectorIndexRetriever")
    def test_get_query_engine(self, mock_retriever, mock_index, mock_get_vector_store):
        """Test query engine creation."""
        # Mock the vector store
        mock_vector_store = MagicMock()
        mock_get_vector_store.return_value = mock_vector_store
        
        # Mock the index
        mock_index_instance = MagicMock()
        mock_index.from_vector_store.return_value = mock_index_instance
        
        # Mock the retriever
        mock_retriever_instance = MagicMock()
        mock_retriever.return_value = mock_retriever_instance
        
        # Get the query engine
        query_engine = self.service.get_query_engine("test_user_id", ["test_file_id"])
        
        # Check that the methods were called
        mock_get_vector_store.assert_called_once()
        mock_index.from_vector_store.assert_called_once()
        mock_retriever.assert_called_once()
    
    @patch("app.services.rag_service.RAGService.get_query_engine")
    async def test_query_documents(self, mock_get_query_engine):
        """Test document querying."""
        # Mock the query engine
        mock_engine = MagicMock()
        mock_response = MagicMock()
        mock_response.source_nodes = []
        mock_engine.query.return_value = mock_response
        mock_get_query_engine.return_value = mock_engine
        
        # Query the documents
        result = await self.service.query_documents(
            query="test query",
            user_id="test_user_id",
            file_ids=["test_file_id"]
        )
        
        # Check the result
        assert result["query"] == "test query"
        assert result["user_id"] == "test_user_id"
        assert result["file_ids"] == ["test_file_id"]
        
        # Verify that the methods were called
        mock_get_query_engine.assert_called_once()
        mock_engine.query.assert_called_once_with("test query")
