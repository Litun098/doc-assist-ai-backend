"""
LlamaIndex service for document processing, indexing, and querying.
"""
import os
import uuid
import time
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from enum import Enum

# LlamaIndex imports
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    Document,
    StorageContext,
    Settings,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core.ingestion import IngestionPipeline
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.weaviate import WeaviateVectorStore
import weaviate
from weaviate.classes.init import Auth, AdditionalConfig, Timeout

# FastAPI imports
from fastapi import UploadFile, HTTPException

# Local imports
from app.models.db_models import FileType, FileStatus, Chunk
from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class ChunkingStrategy(str, Enum):
    """Chunking strategies for document processing."""
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class LlamaIndexService:
    """Service for document processing using LlamaIndex."""

    def __init__(self):
        """Initialize the LlamaIndex service."""
        # Configure LlamaIndex settings
        Settings.llm = OpenAI(
            model=settings.DEFAULT_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.1
        )
        Settings.embed_model = OpenAIEmbedding(
            model_name=settings.EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY,
            embed_batch_size=10,  # Process 10 chunks at a time to avoid rate limits
        )

        # Initialize Weaviate client if configured
        self.weaviate_client = None
        self.vector_store = None
        if settings.WEAVIATE_URL and settings.WEAVIATE_API_KEY:
            try:
                # Connect to Weaviate cloud using the updated client API
                # Skip initialization checks to avoid gRPC issues
                # Make sure we're using the REST endpoint, not gRPC
                weaviate_url = settings.WEAVIATE_URL
                if not weaviate_url.startswith("https://"):
                    weaviate_url = f"https://{weaviate_url}"

                logger.info(f"Connecting to Weaviate at {weaviate_url}")

                # Use a try-except block with multiple connection attempts
                max_retries = 3
                retry_count = 0
                connection_successful = False

                while retry_count < max_retries and not connection_successful:
                    try:
                        self.weaviate_client = weaviate.connect_to_weaviate_cloud(
                            cluster_url=weaviate_url,
                            auth_credentials=Auth.api_key(settings.WEAVIATE_API_KEY),
                            skip_init_checks=True,  # Skip initialization checks
                            additional_config=AdditionalConfig(
                                timeout=Timeout(
                                    init=settings.WEAVIATE_BATCH_TIMEOUT,  # Increase timeout for initialization
                                    query=settings.WEAVIATE_BATCH_TIMEOUT,  # Increase timeout for queries
                                    batch=settings.WEAVIATE_BATCH_TIMEOUT   # Increase timeout for batch operations
                                )
                            )
                        )
                        connection_successful = True
                        logger.info("Successfully connected to Weaviate")
                    except Exception as e:
                        retry_count += 1
                        logger.warning(f"Weaviate connection attempt {retry_count} failed: {str(e)}")
                        if retry_count < max_retries:
                            logger.info(f"Retrying connection to Weaviate ({retry_count}/{max_retries})...")
                            time.sleep(1)  # Wait 1 second before retrying

                # Only proceed with vector store creation if connection was successful
                if connection_successful and self.weaviate_client:
                    try:
                        # Create vector store with the updated API
                        self.vector_store = WeaviateVectorStore(
                            weaviate_client=self.weaviate_client,
                            index_name=settings.LLAMAINDEX_INDEX_NAME,
                            text_key="content",
                            metadata_keys=["file_id", "user_id", "session_id", "page_number", "chunk_index", "heading", "chunking_strategy"]
                        )

                        # Create schema if it doesn't exist
                        self._create_schema_if_not_exists()
                    except Exception as e:
                        logger.error(f"Error creating vector store: {str(e)}")
                        self.vector_store = None
            except Exception as e:
                logger.error(f"Error connecting to Weaviate: {str(e)}")
                self.weaviate_client = None
                self.vector_store = None

        # Set global settings instead of using ServiceContext (which is deprecated)
        Settings.chunk_size = settings.LLAMAINDEX_CHUNK_SIZE
        Settings.chunk_overlap = settings.LLAMAINDEX_CHUNK_OVERLAP

        # Create storage context if vector store is available
        self.storage_context = None
        if self.vector_store:
            self.storage_context = StorageContext.from_defaults(
                vector_store=self.vector_store
            )

    def _create_schema_if_not_exists(self):
        """Create Weaviate schema if it doesn't exist."""
        if not self.weaviate_client:
            return

        try:
            # Check if the collection exists
            try:
                collections = self.weaviate_client.collections.list_all()
                collection_names = []
                for collection in collections:
                    if hasattr(collection, 'name'):
                        collection_names.append(collection.name)
                    elif isinstance(collection, str):
                        collection_names.append(collection)
                    elif isinstance(collection, dict) and 'name' in collection:
                        collection_names.append(collection['name'])
            except Exception as e:
                logger.error(f"Error listing collections: {str(e)}")
                collection_names = []

            # Create collection if it doesn't exist
            if settings.LLAMAINDEX_INDEX_NAME not in collection_names:
                # Create a new collection
                self.weaviate_client.collections.create(
                    name=settings.LLAMAINDEX_INDEX_NAME,
                    description="Document chunks for semantic search",
                    vectorizer_config=None,  # We'll provide our own vectors
                    properties=[
                        {
                            "name": "content",
                            "dataType": ["text"],
                            "description": "The text content of the chunk"
                        },
                        {
                            "name": "file_id",
                            "dataType": ["text"],
                            "description": "The ID of the file this chunk belongs to"
                        },
                        {
                            "name": "user_id",
                            "dataType": ["text"],
                            "description": "The ID of the user who owns this chunk"
                        },
                        {
                            "name": "session_id",
                            "dataType": ["text"],
                            "description": "The ID of the session this chunk is associated with"
                        },
                        {
                            "name": "page_number",
                            "dataType": ["int"],
                            "description": "The page number this chunk is from"
                        },
                        {
                            "name": "chunk_index",
                            "dataType": ["int"],
                            "description": "The index of this chunk within the file"
                        },
                        {
                            "name": "heading",
                            "dataType": ["text"],
                            "description": "The heading or title of the section"
                        },
                        {
                            "name": "chunking_strategy",
                            "dataType": ["text"],
                            "description": "The chunking strategy used (fixed_size, semantic, hybrid)"
                        },
                        {
                            "name": "metadata",
                            "dataType": ["text"],
                            "description": "Additional metadata about the chunk"
                        }
                    ]
                )
                logger.info(f"Created collection {settings.LLAMAINDEX_INDEX_NAME} in Weaviate")
        except Exception as e:
            logger.error(f"Error creating Weaviate schema: {str(e)}")

    async def process_file(self, file_path: str, file_id: str, user_id: str,
                          file_type: FileType, chunking_strategy: ChunkingStrategy = ChunkingStrategy.HYBRID,
                          session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a file using LlamaIndex.

        Args:
            file_path: Path to the file
            file_id: Unique ID for the file
            user_id: ID of the user who uploaded the file
            file_type: Type of the file
            chunking_strategy: Chunking strategy to use
            session_id: ID of the session (optional)

        Returns:
            Dict containing processing results
        """
        try:
            # Load the document
            documents = await self._load_document(file_path, file_type)

            # Check if document has images
            has_images = self._check_for_images(documents, file_type)

            # Get page count
            page_count = len(documents)

            # Create nodes with appropriate chunking strategy
            nodes = await self._create_nodes(documents, file_id, user_id, chunking_strategy, session_id)

            # Create index with batch processing for large documents
            if self.storage_context and self.vector_store:
                # Use vector store with batched processing
                await self._store_nodes_in_batches(nodes)
            else:
                # Use in-memory index if no vector store
                VectorStoreIndex(
                    nodes=nodes,
                )

            # Create chunks for database storage
            chunks = self._create_chunks_from_nodes(nodes, file_id)

            return {
                "file_id": file_id,
                "status": "processed",
                "page_count": page_count,
                "has_images": has_images,
                "chunk_count": len(chunks),
                "chunks": chunks
            }

        except Exception as e:
            logger.error(f"Error processing file {file_id}: {str(e)}")
            raise

    async def _load_document(self, file_path: str, file_type: FileType) -> List[Document]:
        """
        Load a document using LlamaIndex.

        Args:
            file_path: Path to the file
            file_type: Type of the file

        Returns:
            List of Document objects
        """
        try:
            # Use SimpleDirectoryReader to load the document
            # This handles various file types automatically
            documents = SimpleDirectoryReader(
                input_files=[file_path],
                filename_as_id=True
            ).load_data()

            # If the document is loaded as a single document but has multiple pages,
            # split it into multiple documents by page
            if len(documents) == 1 and file_type in [FileType.PDF, FileType.DOCX, FileType.PPTX]:
                # Try to split by pages based on page breaks or slide markers
                text = documents[0].text

                if file_type == FileType.PDF:
                    # Split by form feeds or other page markers
                    pages = text.split("\f")
                elif file_type == FileType.PPTX:
                    # For PowerPoint, try to identify slide breaks (this is approximate)
                    pages = text.split("\n\n\n\n")
                else:
                    # For other documents, split by multiple newlines as a heuristic
                    pages = text.split("\n\n\n")

                # Filter out empty pages
                pages = [page.strip() for page in pages if page.strip()]

                if len(pages) > 1:
                    # Create a document for each page
                    documents = [
                        Document(
                            text=page,
                            metadata={
                                "page_number": i + 1,
                                "file_path": file_path,
                                "file_type": file_type.value
                            }
                        )
                        for i, page in enumerate(pages)
                    ]
                else:
                    # Add page metadata to the single document
                    documents[0].metadata["page_number"] = 1
                    documents[0].metadata["file_path"] = file_path
                    documents[0].metadata["file_type"] = file_type.value

            return documents

        except Exception as e:
            logger.error(f"Error loading document {file_path}: {str(e)}")
            raise

    def _check_for_images(self, _docs: List[Document], file_type: FileType) -> bool:
        """
        Check if a document contains images.

        Args:
            _docs: List of Document objects (unused)
            file_type: Type of the file

        Returns:
            True if the document contains images, False otherwise
        """
        # For now, we'll use a simple heuristic based on file type
        # In a more advanced implementation, we could analyze the document content
        if file_type in [FileType.PDF, FileType.DOCX, FileType.PPTX]:
            # These file types commonly contain images
            # For a more accurate check, we would need to parse the document structure
            return True

        return False

    async def _create_nodes(self, documents: List[Document], file_id: str, user_id: str,
                           chunking_strategy: ChunkingStrategy, session_id: Optional[str] = None) -> List[TextNode]:
        """
        Create nodes from documents using the specified chunking strategy.

        Args:
            documents: List of Document objects
            file_id: Unique ID for the file
            user_id: ID of the user who uploaded the file
            chunking_strategy: Chunking strategy to use
            session_id: ID of the session (optional)

        Returns:
            List of TextNode objects
        """
        nodes = []

        if chunking_strategy == ChunkingStrategy.FIXED_SIZE:
            # Use simple fixed-size chunking
            node_parser = SimpleNodeParser.from_defaults(
                chunk_size=settings.LLAMAINDEX_CHUNK_SIZE,
                chunk_overlap=settings.LLAMAINDEX_CHUNK_OVERLAP
            )
        elif chunking_strategy == ChunkingStrategy.SEMANTIC:
            # Use sentence-based chunking for more semantic coherence
            node_parser = SentenceSplitter(
                chunk_size=settings.LLAMAINDEX_CHUNK_SIZE,
                chunk_overlap=settings.LLAMAINDEX_CHUNK_OVERLAP,
                paragraph_separator="\n\n",
                secondary_chunking_regex="[^,.;。]+[,.;。]?",
            )
        else:  # ChunkingStrategy.HYBRID (default)
            # Use a combination based on document type
            # For now, we'll use the same as SEMANTIC, but this could be enhanced
            node_parser = SentenceSplitter(
                chunk_size=settings.LLAMAINDEX_CHUNK_SIZE,
                chunk_overlap=settings.LLAMAINDEX_CHUNK_OVERLAP,
                paragraph_separator="\n\n",
                secondary_chunking_regex="[^,.;。]+[,.;。]?",
            )

        # Create an ingestion pipeline
        pipeline = IngestionPipeline(
            transformations=[node_parser],
        )

        # Process documents through the pipeline
        for doc_idx, doc in enumerate(documents):
            # Add file and user metadata to the document
            doc.metadata["file_id"] = file_id
            doc.metadata["user_id"] = user_id
            doc.metadata["chunking_strategy"] = chunking_strategy

            # Add session_id if provided
            if session_id:
                doc.metadata["session_id"] = session_id

            # If page_number is not set, use the document index
            if "page_number" not in doc.metadata:
                doc.metadata["page_number"] = doc_idx + 1

        # Run the pipeline
        nodes = pipeline.run(documents)

        # Add additional metadata to nodes
        for i, node in enumerate(nodes):
            node.metadata["chunk_index"] = i

            # Try to extract heading from the text
            lines = node.text.split("\n")
            if lines and len(lines[0]) < 100:  # Simple heuristic for headings
                node.metadata["heading"] = lines[0]
            else:
                node.metadata["heading"] = None

        return nodes

    async def _store_nodes_in_batches(self, nodes: List[TextNode]) -> None:
        """
        Store nodes in Weaviate using batched processing to avoid timeouts.

        Args:
            nodes: List of TextNode objects to store
        """
        if not self.vector_store or not self.weaviate_client:
            logger.warning("Vector store not available, skipping batch storage")
            return

        try:
            # Get the total number of nodes
            total_nodes = len(nodes)
            logger.info(f"Starting batch processing of {total_nodes} nodes")

            # Calculate number of batches
            batch_size = settings.WEAVIATE_BATCH_SIZE
            num_batches = (total_nodes + batch_size - 1) // batch_size  # Ceiling division

            # Process nodes in batches
            for batch_idx in range(num_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, total_nodes)
                batch_nodes = nodes[start_idx:end_idx]

                logger.info(f"Processing batch {batch_idx + 1}/{num_batches} with {len(batch_nodes)} nodes")

                # Create a temporary storage context for this batch
                batch_storage_context = StorageContext.from_defaults(
                    vector_store=self.vector_store
                )

                # Process the batch with retries
                retry_count = 0
                max_retries = settings.WEAVIATE_MAX_RETRIES
                success = False

                while retry_count < max_retries and not success:
                    try:
                        # Create a temporary index for this batch
                        VectorStoreIndex(
                            nodes=batch_nodes,
                            storage_context=batch_storage_context,
                        )
                        success = True
                        logger.info(f"Successfully processed batch {batch_idx + 1}/{num_batches}")
                    except Exception as e:
                        retry_count += 1
                        logger.warning(f"Batch {batch_idx + 1} attempt {retry_count} failed: {str(e)}")
                        if retry_count < max_retries:
                            logger.info(f"Retrying batch {batch_idx + 1} (attempt {retry_count + 1}/{max_retries})...")
                            # Wait before retrying with exponential backoff
                            await asyncio.sleep(2 ** retry_count)
                        else:
                            logger.error(f"Failed to process batch {batch_idx + 1} after {max_retries} attempts")
                            # Continue with next batch instead of failing the entire process

            logger.info(f"Completed batch processing of {total_nodes} nodes")
        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
            # Don't raise the exception to allow the process to continue
            # The document will be marked as processed even if some batches failed

    def _create_chunks_from_nodes(self, nodes: List[TextNode], file_id: str) -> List[Chunk]:
        """
        Create Chunk objects from TextNode objects for database storage.

        Args:
            nodes: List of TextNode objects
            file_id: Unique ID for the file

        Returns:
            List of Chunk objects
        """
        chunks = []

        for node in nodes:
            # Create a Chunk object from the node
            chunk = Chunk(
                id=str(uuid.uuid4()),
                file_id=file_id,
                content=node.text,
                page_number=node.metadata.get("page_number"),
                chunk_index=node.metadata.get("chunk_index", 0),
                embedding_id=node.id_,  # Use the node ID as the embedding ID
                created_at=datetime.now(),
                metadata={
                    "page_number": node.metadata.get("page_number"),
                    "chunk_index": node.metadata.get("chunk_index", 0),
                    "heading": node.metadata.get("heading"),
                    "chunking_strategy": node.metadata.get("chunking_strategy"),
                    "file_id": file_id,
                    "user_id": node.metadata.get("user_id"),
                }
            )
            chunks.append(chunk)

        return chunks

    async def get_document_chunks(self, file_id: str, user_id: str, limit: int = 3) -> Dict[str, Any]:
        """
        Get representative chunks from a document.

        Args:
            file_id: ID of the file to get chunks from
            user_id: ID of the user who owns the file
            limit: Maximum number of chunks to return

        Returns:
            Dict containing document chunks
        """
        try:
            if not self.vector_store:
                raise HTTPException(status_code=500, detail="Vector store not configured")

            # Create a filter for the specified file ID and user ID
            filter_dict = {
                "operator": "And",
                "operands": [
                    {
                        "path": ["file_id"],
                        "operator": "Equal",
                        "valueString": file_id
                    },
                    {
                        "path": ["user_id"],
                        "operator": "Equal",
                        "valueString": user_id
                    }
                ]
            }

            # Get chunks from the vector store
            try:
                # Try using the v4 API first
                collection = self.weaviate_client.collections.get(settings.LLAMAINDEX_INDEX_NAME)

                # Query for chunks
                results = collection.query.fetch_objects(
                    limit=limit,
                    filters=filter_dict,
                    include_vector=False
                )

                # Extract chunks
                chunks = []
                for obj in results.objects:
                    chunks.append({
                        "content": obj.properties.get("content", ""),
                        "file_id": obj.properties.get("file_id", ""),
                        "page_number": obj.properties.get("page_number", 0),
                        "chunk_index": obj.properties.get("chunk_index", 0),
                        "heading": obj.properties.get("heading", ""),
                        "metadata": obj.properties.get("metadata", {})
                    })
            except (AttributeError, Exception) as e:
                logger.error(f"Error using v4 API to get chunks: {str(e)}")
                # Fall back to a simpler approach - get nodes from the retriever
                retriever = self.vector_store.as_retriever(
                    similarity_top_k=limit,
                    filters=filter_dict
                )

                # Use a generic query to get some representative chunks
                nodes = retriever.retrieve("summary of this document")

                # Extract chunks
                chunks = []
                for node in nodes:
                    chunks.append({
                        "content": node.text,
                        "file_id": node.metadata.get("file_id", ""),
                        "page_number": node.metadata.get("page_number", 0),
                        "chunk_index": node.metadata.get("chunk_index", 0),
                        "heading": node.metadata.get("heading", ""),
                        "metadata": node.metadata
                    })

            return {
                "file_id": file_id,
                "user_id": user_id,
                "chunks": chunks
            }

        except Exception as e:
            logger.error(f"Error getting document chunks: {str(e)}")
            return {
                "file_id": file_id,
                "user_id": user_id,
                "chunks": [],
                "error": str(e)
            }

    async def query_documents(self, query: str, file_ids: List[str], user_id: str,
                             top_k: int = 5, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Query documents using LlamaIndex.

        Args:
            query: Query string
            file_ids: List of file IDs to search in
            user_id: ID of the user making the query
            top_k: Number of results to return
            session_id: ID of the session (optional, for prioritizing session-specific chunks)

        Returns:
            Dict containing query results
        """
        try:
            if not self.vector_store:
                raise HTTPException(status_code=500, detail="Vector store not configured")

            # Build the query
            vector_store_query = self.vector_store.as_retriever(
                similarity_top_k=top_k,
            )

            # Add filters for file_ids and user_id
            if file_ids:
                # Base operands for the filter
                filter_operands = [
                    {
                        "operator": "Or",
                        "operands": [
                            {"path": ["file_id"], "operator": "Equal", "valueString": file_id}
                            for file_id in file_ids
                        ]
                    },
                    {
                        "path": ["user_id"],
                        "operator": "Equal",
                        "valueString": user_id
                    }
                ]

                # If session_id is provided, prioritize chunks from this session
                if session_id:
                    # First, try to get chunks specifically from this session
                    session_filter = {
                        "operator": "And",
                        "operands": filter_operands + [
                            {
                                "path": ["session_id"],
                                "operator": "Equal",
                                "valueString": session_id
                            }
                        ]
                    }

                    # Get session-specific chunks
                    session_vector_store_query = self.vector_store.as_retriever(
                        similarity_top_k=top_k,
                        filters=session_filter
                    )

                    session_nodes = session_vector_store_query.retrieve(query)

                    # If we got enough results from the session, use those
                    if len(session_nodes) >= top_k // 2:  # At least half of requested results
                        return self._create_response(query, session_nodes)

                # If no session_id or not enough session-specific results, use regular filter
                filter_dict = {
                    "operator": "And",
                    "operands": filter_operands
                }

                vector_store_query = self.vector_store.as_retriever(
                    similarity_top_k=top_k,
                    filters=filter_dict
                )

            # Get the query embedding (not needed when using retriever directly)
            # query_embedding = Settings.embed_model.get_query_embedding(query)

            # Execute the query
            nodes = vector_store_query.retrieve(query)

            # Create and return the response
            return self._create_response(query, nodes)
        except Exception as e:
            logger.error(f"Error querying documents: {str(e)}")
            raise

    def _create_response(self, query: str, nodes: List) -> Dict[str, Any]:
        """
        Create a response from retrieved nodes.

        Args:
            query: The user's query
            nodes: The retrieved nodes

        Returns:
            Dict containing the response
        """
        # Create a response
        llm = Settings.llm
        response_text = llm.complete(
            f"""You are AnyDocAI, an AI document assistant that helps users understand their documents.

            Use the following context from the user's documents to answer their question. If you don't know the answer, say you don't know.
            Don't try to make up an answer. Always be helpful, concise, and professional.

            Context:
            {' '.join([node.text for node in nodes])}

            Question: {query}

            Answer:"""
        ).text

        # Format the response
        response = {
            "response": response_text,
            "source_documents": [
                {
                    "content": node.text,
                    "metadata": node.metadata,
                    "score": node.score if hasattr(node, "score") else None
                }
                for node in nodes
            ],
            "model_used": Settings.llm.model_name
        }

        return response

    async def process_uploaded_file(self, file: UploadFile, user_id: str,
                                   chunking_strategy: ChunkingStrategy = ChunkingStrategy.HYBRID) -> Dict[str, Any]:
        """
        Process an uploaded file.

        Args:
            file: Uploaded file
            user_id: ID of the user who uploaded the file
            chunking_strategy: Chunking strategy to use

        Returns:
            Dict containing processing results
        """
        try:
            # Check file size
            file.file.seek(0, os.SEEK_END)
            file_size = file.file.tell()
            file.file.seek(0)

            if file_size > settings.MAX_UPLOAD_SIZE:
                raise HTTPException(status_code=400, detail="File too large")

            # Determine file type
            file_type = self._determine_file_type(file.filename)
            if file_type == FileType.UNKNOWN:
                raise HTTPException(status_code=400, detail="Unsupported file type")

            # Generate a unique ID for the file
            file_id = str(uuid.uuid4())

            # Save the file temporarily
            temp_file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}.{file_type.value}")
            os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)

            with open(temp_file_path, "wb") as buffer:
                content = file.file.read()
                buffer.write(content)
                file.file.seek(0)

            # Process the file
            result = await self.process_file(
                file_path=temp_file_path,
                file_id=file_id,
                user_id=user_id,
                file_type=file_type,
                chunking_strategy=chunking_strategy
            )

            # Create file record (for future database integration)
            # {
            #     "id": file_id,
            #     "user_id": user_id,
            #     "filename": file.filename,
            #     "original_filename": file.filename,
            #     "file_type": file_type,
            #     "file_size": file_size,
            #     "status": FileStatus.PROCESSED,
            #     "s3_key": temp_file_path,  # For now, just store the local path
            #     "created_at": datetime.now(),
            #     "updated_at": datetime.now(),
            #     "processed_at": datetime.now(),
            #     "page_count": result.get("page_count", 0),
            #     "has_images": result.get("has_images", False)
            # }

            # TODO: Save file record to database

            # Return the result
            return {
                "id": file_id,
                "filename": file.filename,
                "file_type": file_type,
                "file_size": file_size,
                "status": FileStatus.PROCESSED,
                "created_at": datetime.now(),
                "chunks": result.get("chunks", [])
            }

        except Exception as e:
            logger.error(f"Error processing uploaded file: {str(e)}")
            raise

    def _determine_file_type(self, filename: str) -> FileType:
        """
        Determine the file type from the filename.

        Args:
            filename: Name of the file

        Returns:
            FileType enum value
        """
        extension = filename.split(".")[-1].lower()
        if extension in ["pdf"]:
            return FileType.PDF
        elif extension in ["docx", "doc"]:
            return FileType.DOCX
        elif extension in ["xlsx", "xls"]:
            return FileType.XLSX
        elif extension in ["pptx", "ppt"]:
            return FileType.PPTX
        elif extension in ["txt"]:
            return FileType.TXT
        else:
            return FileType.UNKNOWN

# Create a singleton instance
llama_index_service = LlamaIndexService()
