"""
Document processing service using LlamaIndex.
Handles different file types and implements hybrid chunking strategies.
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

# LlamaIndex imports
from llama_index.core import Document as LlamaDocument
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SentenceSplitter, NodeParser
from llama_index.core.schema import MetadataMode
from llama_index.readers.file import PDFReader, DocxReader, PptxReader
from llama_index.readers.file.tabular import PandasExcelReader
from llama_index.readers.file.base import SimpleDirectoryReader

# Weaviate imports
from llama_index.vector_stores.weaviate import WeaviateVectorStore
import weaviate

# Local imports
from app.models.db_models import FileType
from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class ChunkingStrategy(str, Enum):
    """Enum for chunking strategies."""
    FIXED_SIZE = "fixed_size"
    TOPIC_BASED = "topic_based"
    HYBRID = "hybrid"

class DocumentProcessor:
    """Document processor service using LlamaIndex."""
    
    def __init__(self):
        """Initialize the document processor."""
        # Initialize Weaviate client if configured
        self.weaviate_client = None
        if settings.WEAVIATE_URL:
            try:
                auth_config = weaviate.AuthApiKey(api_key=settings.WEAVIATE_API_KEY) if settings.WEAVIATE_API_KEY else None
                self.weaviate_client = weaviate.Client(
                    url=f"https://{settings.WEAVIATE_URL}",
                    auth_client_secret=auth_config
                )
                logger.info(f"Connected to Weaviate at {settings.WEAVIATE_URL}")
            except Exception as e:
                logger.error(f"Error connecting to Weaviate: {str(e)}")
        
        # Initialize node parsers for different chunking strategies
        self.fixed_size_parser = SentenceSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        
        self.topic_based_parser = SentenceSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            paragraph_separator="\n\n",
            secondary_chunking_regex="|".join(settings.HEADING_PATTERNS)
        )
    
    def detect_file_type(self, file_path: str) -> FileType:
        """
        Detect the file type based on the file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            FileType enum value
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower().lstrip('.')
        
        if ext == 'pdf':
            return FileType.PDF
        elif ext in ['docx', 'doc']:
            return FileType.DOCX
        elif ext in ['xlsx', 'xls']:
            return FileType.XLSX
        elif ext in ['pptx', 'ppt']:
            return FileType.PPTX
        elif ext == 'txt':
            return FileType.TXT
        else:
            return FileType.OTHER
    
    def get_chunking_strategy(self, file_type: FileType) -> ChunkingStrategy:
        """
        Determine the chunking strategy based on file type.
        
        Args:
            file_type: FileType enum value
            
        Returns:
            ChunkingStrategy enum value
        """
        if file_type in settings.TOPIC_BASED_FILETYPES:
            return ChunkingStrategy.TOPIC_BASED
        elif file_type in settings.FIXED_SIZE_FILETYPES:
            return ChunkingStrategy.FIXED_SIZE
        else:
            return ChunkingStrategy.HYBRID
    
    def get_document_loader(self, file_path: str, file_type: FileType) -> Any:
        """
        Get the appropriate document loader based on file type.
        
        Args:
            file_path: Path to the file
            file_type: FileType enum value
            
        Returns:
            Document loader instance
        """
        if file_type == FileType.PDF:
            return PDFReader()
        elif file_type == FileType.DOCX:
            return DocxReader()
        elif file_type == FileType.XLSX:
            return PandasExcelReader()
        elif file_type == FileType.PPTX:
            return PptxReader()
        elif file_type == FileType.TXT:
            return SimpleDirectoryReader(input_files=[file_path])
        else:
            # Default to simple directory reader
            return SimpleDirectoryReader(input_files=[file_path])
    
    def load_document(self, file_path: str, file_type: Optional[FileType] = None) -> List[LlamaDocument]:
        """
        Load a document using the appropriate loader.
        
        Args:
            file_path: Path to the file
            file_type: FileType enum value (optional, will be detected if not provided)
            
        Returns:
            List of LlamaIndex Document objects
        """
        try:
            if file_type is None:
                file_type = self.detect_file_type(file_path)
            
            loader = self.get_document_loader(file_path, file_type)
            
            if file_type == FileType.TXT:
                # SimpleDirectoryReader returns documents directly
                documents = loader.load_data()
            else:
                # Other loaders need to be called with the file path
                documents = loader.load_data(file_path)
            
            # Add metadata to documents
            for doc in documents:
                doc.metadata.update({
                    "file_path": file_path,
                    "file_type": file_type.value,
                    "file_name": os.path.basename(file_path)
                })
            
            return documents
        
        except Exception as e:
            logger.error(f"Error loading document {file_path}: {str(e)}")
            raise
    
    def process_document(self, file_path: str, file_id: str, user_id: str) -> Dict[str, Any]:
        """
        Process a document: load, chunk, and index it.
        
        Args:
            file_path: Path to the file
            file_id: Unique ID for the file
            user_id: ID of the user who uploaded the file
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Detect file type
            file_type = self.detect_file_type(file_path)
            
            # Load document
            documents = self.load_document(file_path, file_type)
            
            if not documents:
                raise ValueError(f"No content could be extracted from {file_path}")
            
            # Determine chunking strategy
            chunking_strategy = self.get_chunking_strategy(file_type)
            
            # Process documents based on chunking strategy
            nodes = self._chunk_documents(documents, chunking_strategy)
            
            # Add additional metadata
            for node in nodes:
                node.metadata.update({
                    "file_id": file_id,
                    "user_id": user_id
                })
            
            # Index documents in Weaviate
            if self.weaviate_client:
                index_name = f"{settings.LLAMAINDEX_INDEX_NAME}_{user_id}"
                vector_store = WeaviateVectorStore(
                    weaviate_client=self.weaviate_client,
                    index_name=index_name,
                    text_key="text",
                    metadata_keys=["file_id", "file_type", "file_name", "user_id"]
                )
                
                storage_context = StorageContext.from_defaults(vector_store=vector_store)
                index = VectorStoreIndex(nodes, storage_context=storage_context)
                
                # Return processing results
                return {
                    "file_id": file_id,
                    "file_type": file_type.value,
                    "file_name": os.path.basename(file_path),
                    "user_id": user_id,
                    "num_chunks": len(nodes),
                    "index_name": index_name,
                    "chunking_strategy": chunking_strategy.value,
                    "status": "success"
                }
            else:
                # If Weaviate is not configured, return the nodes for in-memory usage
                return {
                    "file_id": file_id,
                    "file_type": file_type.value,
                    "file_name": os.path.basename(file_path),
                    "user_id": user_id,
                    "num_chunks": len(nodes),
                    "nodes": nodes,
                    "chunking_strategy": chunking_strategy.value,
                    "status": "success"
                }
        
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            return {
                "file_id": file_id,
                "file_path": file_path,
                "user_id": user_id,
                "status": "error",
                "error": str(e)
            }
    
    def _chunk_documents(self, documents: List[LlamaDocument], strategy: ChunkingStrategy) -> List[Any]:
        """
        Chunk documents based on the specified strategy.
        
        Args:
            documents: List of LlamaIndex Document objects
            strategy: ChunkingStrategy enum value
            
        Returns:
            List of document nodes
        """
        if strategy == ChunkingStrategy.FIXED_SIZE:
            return self.fixed_size_parser.get_nodes_from_documents(documents)
        
        elif strategy == ChunkingStrategy.TOPIC_BASED:
            return self.topic_based_parser.get_nodes_from_documents(documents)
        
        elif strategy == ChunkingStrategy.HYBRID:
            # For hybrid strategy, we'll use a combination of approaches
            # First, try topic-based chunking
            topic_nodes = self.topic_based_parser.get_nodes_from_documents(documents)
            
            # Check if the chunks are reasonable sizes
            large_chunks = [node for node in topic_nodes if len(node.text) > settings.MAX_CHUNK_SIZE]
            small_chunks = [node for node in topic_nodes if len(node.text) < settings.MIN_CHUNK_SIZE]
            
            # If we have too many large or small chunks, fall back to fixed-size chunking
            if len(large_chunks) > len(topic_nodes) * 0.3 or len(small_chunks) > len(topic_nodes) * 0.5:
                return self.fixed_size_parser.get_nodes_from_documents(documents)
            
            return topic_nodes
        
        else:
            # Default to fixed-size chunking
            return self.fixed_size_parser.get_nodes_from_documents(documents)

# Create a singleton instance
document_processor = DocumentProcessor()
