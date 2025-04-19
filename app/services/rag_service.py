"""
RAG (Retrieval-Augmented Generation) service using LlamaIndex.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# LlamaIndex imports
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

        # Disable Weaviate for now to get the server running
        self.use_weaviate = False
        logger.info("Using in-memory storage (Weaviate disabled)")

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=settings.DEFAULT_MODEL,
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        )

        # Cache for query engines
        self.query_engine_cache = {}
        self.chat_engine_cache = {}

    def get_vector_store(self, user_id: str) -> Any:
        """
        Get a vector store for the user.

        Args:
            user_id: ID of the user

        Returns:
            Vector store instance (Weaviate or in-memory)
        """
        from llama_index.core.vector_stores import SimpleVectorStore

        if self.use_weaviate and self.weaviate_client:
            # Use Weaviate vector store
            try:
                index_name = f"{settings.LLAMAINDEX_INDEX_NAME}_{user_id}"

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
                                 chat_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Chat with documents using the RAG system.

        Args:
            message: User's message
            user_id: ID of the user
            file_ids: List of file IDs to include in the chat (optional)
            chat_history: List of previous chat messages (optional)

        Returns:
            Dictionary with chat response
        """
        try:
            # Get the chat engine
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
            return {
                "response": f"Error chatting with documents: {str(e)}",
                "message": message,
                "file_ids": file_ids or [],
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "sources": []
            }

# Create a singleton instance
rag_service = RAGService()
