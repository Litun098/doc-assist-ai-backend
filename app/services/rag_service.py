"""
RAG (Retrieval-Augmented Generation) service using LlamaIndex.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# LlamaIndex imports - using modular package structure
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.chat_engine import ContextChatEngine
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.vector_stores.weaviate import WeaviateVectorStore
import weaviate

# OpenAI imports
from langchain_openai import ChatOpenAI

# Local imports
from config.config import settings
from app.services.document_processor import document_processor
from app.services.llama_index_service import llama_index_service

# Configure logging
logger = logging.getLogger(__name__)

class RAGService:
    """RAG service using LlamaIndex."""

    def __init__(self):
        """Initialize the RAG service."""
        # Initialize Weaviate client if configured
        self.weaviate_client = None
        self.use_weaviate = False

        # In-memory storage for documents and nodes
        self.document_store = {}
        self.node_store = {}

        # Initialize Weaviate if configured
        if settings.WEAVIATE_URL and settings.WEAVIATE_API_KEY:
            self._connect_to_weaviate_with_retry()

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=settings.DEFAULT_MODEL,
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        )

        # Cache for query engines
        self.query_engine_cache = {}
        self.chat_engine_cache = {}

    def _connect_to_weaviate_with_retry(self, max_retries: int = 3, retry_delay: float = 2.0):
        """
        Connect to Weaviate with retry logic.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        import time

        for attempt in range(max_retries + 1):
            try:
                from weaviate.classes.init import Auth, AdditionalConfig, Timeout
                import weaviate

                # Make sure we're using the REST endpoint, not gRPC
                weaviate_url = settings.WEAVIATE_URL
                if not weaviate_url.startswith("https://"):
                    weaviate_url = f"https://{weaviate_url}"

                logger.info(f"Connecting to Weaviate at {weaviate_url} (attempt {attempt + 1}/{max_retries + 1})")
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

                # Test the connection
                try:
                    # Try a simple operation to verify connection
                    self.weaviate_client.collections.list_all()
                    self.use_weaviate = True
                    logger.info("Successfully connected to Weaviate for vector storage")
                    return
                except Exception as test_error:
                    logger.warning(f"Weaviate connection test failed: {str(test_error)}")
                    if self.weaviate_client:
                        try:
                            self.weaviate_client.close()
                        except:
                            pass
                        self.weaviate_client = None
                    raise test_error

            except Exception as e:
                logger.error(f"Error connecting to Weaviate (attempt {attempt + 1}): {str(e)}")

                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
                else:
                    logger.error("Failed to connect to Weaviate after all retry attempts")
                    logger.info("Falling back to in-memory storage")
                    self.use_weaviate = False
                    self.weaviate_client = None

    def _check_weaviate_connection(self) -> bool:
        """
        Check if Weaviate connection is healthy and reconnect if needed.

        Returns:
            True if connection is healthy, False otherwise
        """
        if not self.use_weaviate or not self.weaviate_client:
            return False

        try:
            # Test the connection with a simple operation
            self.weaviate_client.collections.list_all()
            return True
        except Exception as e:
            logger.warning(f"Weaviate connection check failed: {str(e)}")
            logger.info("Attempting to reconnect to Weaviate...")

            # Close the current connection
            try:
                if self.weaviate_client:
                    self.weaviate_client.close()
            except:
                pass

            # Try to reconnect
            self._connect_to_weaviate_with_retry(max_retries=2, retry_delay=1.0)
            return self.use_weaviate and self.weaviate_client is not None

    def get_vector_store(self, user_id: str) -> Any:
        """
        Get a vector store for the user.

        Args:
            user_id: ID of the user

        Returns:
            Vector store instance (Weaviate or in-memory)
        """
        from llama_index.core.vector_stores import SimpleVectorStore

        # Check Weaviate connection health before using it
        if self._check_weaviate_connection():
            # Use Weaviate vector store
            try:
                # Create a user-specific collection name
                # Weaviate doesn't allow underscores in class names, so we'll replace them with hyphens
                # Also, we'll use a shorter version of the user_id to avoid exceeding length limits
                short_user_id = user_id.replace("-", "")[:8]
                index_name = f"{settings.LLAMAINDEX_INDEX_NAME}{short_user_id}"

                return WeaviateVectorStore(
                    weaviate_client=self.weaviate_client,
                    index_name=index_name,
                    text_key="text",
                    metadata_keys=["file_id", "file_type", "file_name", "user_id"]
                )
            except Exception as e:
                logger.error(f"Error creating Weaviate vector store: {str(e)}")
                logger.info("Falling back to in-memory vector store")

        # Use in-memory vector store
        # In a real implementation, you would use a persistent vector store
        return SimpleVectorStore()

    def get_query_engine(self, user_id: str, file_ids: Optional[List[str]] = None) -> Optional[RetrieverQueryEngine]:
        """
        Get a query engine for the user and specified files.

        Args:
            user_id: ID of the user
            file_ids: List of file IDs to include in the query (optional)

        Returns:
            RetrieverQueryEngine instance or None if no documents are available
        """
        # Create a cache key
        cache_key = f"{user_id}_{','.join(file_ids) if file_ids else 'all'}"

        # Check if we have a cached query engine
        if cache_key in self.query_engine_cache:
            return self.query_engine_cache[cache_key]

        try:
            # Get the vector store
            vector_store = self.get_vector_store(user_id)

            # Create a storage context
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            # Create an index
            index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                storage_context=storage_context
            )

            # Create a retriever with metadata filtering if file_ids are specified
            if file_ids:
                # Create metadata filters for the specified file IDs
                filters = {"file_id": {"$in": file_ids}}
                retriever = VectorIndexRetriever(
                    index=index,
                    similarity_top_k=settings.LLAMAINDEX_SIMILARITY_TOP_K,
                    filters=filters
                )
            else:
                # No filtering, retrieve from all files
                retriever = VectorIndexRetriever(
                    index=index,
                    similarity_top_k=settings.LLAMAINDEX_SIMILARITY_TOP_K
                )

            # Create a query engine with similarity score threshold
            query_engine = RetrieverQueryEngine.from_args(
                retriever=retriever,
                node_postprocessors=[
                    SimilarityPostprocessor(similarity_cutoff=0.7)
                ]
            )

            # Cache the query engine
            self.query_engine_cache[cache_key] = query_engine

            return query_engine
        except Exception as e:
            logger.error(f"Error creating query engine: {str(e)}")
            return None

    def get_chat_engine(self, user_id: str, file_ids: Optional[List[str]] = None) -> Optional[ContextChatEngine]:
        """
        Get a chat engine for the user and specified files.

        Args:
            user_id: ID of the user
            file_ids: List of file IDs to include in the chat (optional)

        Returns:
            ContextChatEngine instance or None if no documents are available
        """
        # Create a cache key
        cache_key = f"{user_id}_{','.join(file_ids) if file_ids else 'all'}"

        # Check if we have a cached chat engine
        if cache_key in self.chat_engine_cache:
            return self.chat_engine_cache[cache_key]

        try:
            # Get the query engine
            query_engine = self.get_query_engine(user_id, file_ids)
            if not query_engine:
                return None

            # Create a chat engine
            chat_engine = ContextChatEngine.from_defaults(
                retriever=query_engine.retriever,
                llm=self.llm,
                system_prompt="""You are an AI assistant that helps users with their documents.
                You have access to a set of documents that you can search to answer questions.
                Always provide helpful, accurate, and concise responses based on the document context.
                If you don't know the answer or can't find relevant information in the documents, say so.
                """
            )

            # Cache the chat engine
            self.chat_engine_cache[cache_key] = chat_engine

            return chat_engine
        except Exception as e:
            logger.error(f"Error creating chat engine: {str(e)}")
            return None

    async def query_documents(self, query: str, user_id: str, file_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Query documents using the RAG system.

        Args:
            query: User's query
            user_id: ID of the user
            file_ids: List of file IDs to include in the query (optional)

        Returns:
            Dictionary with query results
        """
        try:
            # Get the query engine
            query_engine = self.get_query_engine(user_id, file_ids)
            if not query_engine:
                return {
                    "response": "No documents found. Please upload some documents first.",
                    "query": query,
                    "file_ids": file_ids or [],
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                    "sources": []
                }

            # Query the documents
            response = query_engine.query(query)

            # Extract source nodes
            source_nodes = response.source_nodes if hasattr(response, 'source_nodes') else []
            sources = []

            for node in source_nodes:
                source = {
                    "text": node.node.text,
                    "metadata": node.node.metadata,
                    "score": node.score if hasattr(node, 'score') else None
                }
                sources.append(source)

            # Format the result
            result = {
                "response": str(response),
                "query": query,
                "file_ids": file_ids or [],
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "sources": sources
            }

            return result

        except Exception as e:
            logger.error(f"Error querying documents: {str(e)}")
            return {
                "response": f"Error querying documents: {str(e)}",
                "query": query,
                "file_ids": file_ids or [],
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "sources": []
            }

    async def chat_with_documents(self,
                                 message: str,
                                 user_id: str,
                                 file_ids: Optional[List[str]] = None,
                                 chat_history: Optional[List[Dict[str, str]]] = None,
                                 session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Chat with documents using the RAG system.

        Args:
            message: User's message
            user_id: ID of the user
            file_ids: List of file IDs to include in the chat (optional)
            chat_history: List of previous chat messages (optional)
            session_id: ID of the session (optional, for prioritizing session-specific chunks)

        Returns:
            Dictionary with chat response
        """
        try:
            # If session_id is provided, use direct LlamaIndex query for better session-specific results
            if session_id and file_ids:
                # Convert chat history to a prompt context
                context = ""
                if chat_history:
                    for msg in chat_history[-3:]:  # Use last 3 messages for context
                        role = msg["role"].capitalize()
                        context += f"{role}: {msg['content']}\n"

                # Create a more specific query with chat context
                enhanced_query = f"{context}\nUser: {message}"

                # Use LlamaIndex service directly with session_id
                llama_response = await llama_index_service.query_documents(
                    query=enhanced_query,
                    file_ids=file_ids,
                    user_id=user_id,
                    top_k=5,
                    session_id=session_id
                )

                # Extract source nodes
                source_nodes = llama_response.get("source_documents", [])
                sources = []

                for node in source_nodes:
                    sources.append({
                        "text": node.get("content", ""),
                        "metadata": node.get("metadata", {}),
                        "score": node.get("score")
                    })

                # Format the result
                return {
                    "response": llama_response.get("response", ""),
                    "message": message,
                    "file_ids": file_ids,
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                    "sources": sources
                }

            # Fall back to chat engine if no session_id
            chat_engine = self.get_chat_engine(user_id, file_ids)
            if not chat_engine:
                return {
                    "response": "No documents found. Please upload some documents first.",
                    "message": message,
                    "file_ids": file_ids or [],
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                    "sources": []
                }

            # Convert chat history to LlamaIndex format
            llama_chat_history = []
            if chat_history:
                for msg in chat_history:
                    if msg["role"] == "user":
                        llama_chat_history.append(ChatMessage(role=MessageRole.USER, content=msg["content"]))
                    elif msg["role"] == "assistant":
                        llama_chat_history.append(ChatMessage(role=MessageRole.ASSISTANT, content=msg["content"]))
                    elif msg["role"] == "system":
                        llama_chat_history.append(ChatMessage(role=MessageRole.SYSTEM, content=msg["content"]))

            # Chat with the documents
            response = chat_engine.chat(message, chat_history=llama_chat_history)

            # Extract source nodes if available
            source_nodes = getattr(response, 'source_nodes', [])
            sources = []

            for node in source_nodes:
                source = {
                    "text": node.node.text,
                    "metadata": node.node.metadata,
                    "score": node.score if hasattr(node, 'score') else None
                }
                sources.append(source)

            # Format the result
            result = {
                "response": str(response),
                "message": message,
                "file_ids": file_ids or [],
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "sources": sources
            }

            return result

        except Exception as e:
            logger.error(f"Error chatting with documents: {str(e)}")

            # Provide a more helpful error message based on the error type
            error_message = self._get_helpful_error_message(str(e), message)

            return {
                "response": error_message,
                "message": message,
                "file_ids": file_ids or [],
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "sources": []
            }

    def _get_helpful_error_message(self, error_str: str, user_message: str) -> str:
        """
        Generate a helpful error message based on the error type.

        Args:
            error_str: The original error string
            user_message: The user's original message

        Returns:
            A helpful error message for the user
        """
        error_lower = error_str.lower()

        if "connection" in error_lower and ("reset" in error_lower or "unavailable" in error_lower):
            return (
                "I'm currently experiencing connectivity issues with the document database. "
                "This might be temporary - please try your question again in a moment. "
                "If the issue persists, you can still ask general questions and I'll do my best to help!"
            )
        elif "weaviate" in error_lower or "vector" in error_lower:
            return (
                "I'm having trouble accessing your documents right now due to a database issue. "
                "Please try again in a few moments. In the meantime, feel free to ask me general questions!"
            )
        elif "timeout" in error_lower:
            return (
                "The request took longer than expected to process. This might be due to high server load. "
                "Please try asking your question again, or try rephrasing it to be more specific."
            )
        elif "no documents" in error_lower or "no chunks" in error_lower:
            return (
                "I couldn't find any relevant information in your uploaded documents for this question. "
                "Try rephrasing your question or asking about different aspects of your documents. "
                "You can also ask me to summarize the entire document to see what information is available."
            )
        else:
            # Generic fallback with helpful suggestions
            return (
                f"I encountered an issue while processing your question: '{user_message}'. "
                "This might be a temporary problem. Please try:\n"
                "• Rephrasing your question\n"
                "• Asking about a specific part of your document\n"
                "• Trying again in a moment\n\n"
                "I'm still here to help with general questions if needed!"
            )

    def close_connections(self):
        """Close all connections and clean up resources."""
        try:
            if self.weaviate_client:
                logger.info("Closing Weaviate client connection...")
                self.weaviate_client.close()
                self.weaviate_client = None
                logger.info("Weaviate client connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing Weaviate client: {str(e)}")

        # Reset use_weaviate flag and clear caches
        self.use_weaviate = False
        self.query_engine_cache.clear()
        self.chat_engine_cache.clear()

# Create a singleton instance
rag_service = RAGService()
