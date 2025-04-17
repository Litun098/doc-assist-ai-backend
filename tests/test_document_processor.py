"""
Tests for the document processor.
"""
import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

from app.services.document_processor import DocumentProcessor, ChunkingStrategy
from app.models.db_models import FileType
from config.config import settings

class TestDocumentProcessor:
    """Tests for the DocumentProcessor class."""
    
    def setup_method(self):
        """Set up the test environment."""
        self.processor = DocumentProcessor()
    
    def test_detect_file_type(self):
        """Test file type detection."""
        assert self.processor.detect_file_type("test.pdf") == FileType.PDF
        assert self.processor.detect_file_type("test.docx") == FileType.DOCX
        assert self.processor.detect_file_type("test.xlsx") == FileType.XLSX
        assert self.processor.detect_file_type("test.pptx") == FileType.PPTX
        assert self.processor.detect_file_type("test.txt") == FileType.TXT
        assert self.processor.detect_file_type("test.unknown") == FileType.OTHER
    
    def test_get_chunking_strategy(self):
        """Test chunking strategy selection."""
        assert self.processor.get_chunking_strategy(FileType.PDF) == ChunkingStrategy.TOPIC_BASED
        assert self.processor.get_chunking_strategy(FileType.DOCX) == ChunkingStrategy.TOPIC_BASED
        assert self.processor.get_chunking_strategy(FileType.TXT) == ChunkingStrategy.TOPIC_BASED
        assert self.processor.get_chunking_strategy(FileType.XLSX) == ChunkingStrategy.FIXED_SIZE
        assert self.processor.get_chunking_strategy(FileType.PPTX) == ChunkingStrategy.FIXED_SIZE
        assert self.processor.get_chunking_strategy(FileType.OTHER) == ChunkingStrategy.HYBRID
    
    @patch("app.services.document_processor.PDFReader")
    def test_get_document_loader(self, mock_pdf_reader):
        """Test document loader selection."""
        mock_pdf_reader.return_value = MagicMock()
        
        loader = self.processor.get_document_loader("test.pdf", FileType.PDF)
        assert isinstance(loader, MagicMock)
        
        # Add more tests for other file types
    
    @patch("app.services.document_processor.DocumentProcessor.load_document")
    @patch("app.services.document_processor.DocumentProcessor._chunk_documents")
    def test_process_document(self, mock_chunk_documents, mock_load_document):
        """Test document processing."""
        # Mock the load_document method
        mock_documents = [MagicMock()]
        mock_load_document.return_value = mock_documents
        
        # Mock the _chunk_documents method
        mock_nodes = [MagicMock()]
        mock_chunk_documents.return_value = mock_nodes
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".txt") as temp_file:
            # Process the document
            result = self.processor.process_document(
                file_path=temp_file.name,
                file_id="test_file_id",
                user_id="test_user_id"
            )
            
            # Check the result
            assert result["file_id"] == "test_file_id"
            assert result["user_id"] == "test_user_id"
            assert result["status"] == "success"
            
            # Verify that the methods were called
            mock_load_document.assert_called_once()
            mock_chunk_documents.assert_called_once()
