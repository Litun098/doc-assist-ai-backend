from typing import List, Dict, Any
import weaviate
from langchain_openai import OpenAIEmbeddings
import uuid

from app.models.db_models import Chunk
from config.config import settings


class EmbeddingService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY
        )

        # Initialize Weaviate client
        if settings.WEAVIATE_URL and settings.WEAVIATE_API_KEY:
            self.weaviate_client = weaviate.Client(
                url=settings.WEAVIATE_URL,
                auth_client_secret=weaviate.AuthApiKey(api_key=settings.WEAVIATE_API_KEY)
            )
            self._ensure_schema()
        else:
            self.weaviate_client = None
            print("Warning: Weaviate not configured. Using local embeddings only.")

    def _ensure_schema(self):
        """Ensure the Weaviate schema exists"""
        if not self.weaviate_client:
            return

        # Check if schema exists
        schema = self.weaviate_client.schema.get()
        classes = [c["class"] for c in schema["classes"]] if "classes" in schema else []

        # Create schema if it doesn't exist
        if "DocumentChunk" not in classes:
            class_obj = {
                "class": "DocumentChunk",
                "description": "A chunk of text from a document",
                "vectorizer": "none",  # We'll provide our own vectors
                "properties": [
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "The text content of the chunk"
                    },
                    {
                        "name": "file_id",
                        "dataType": ["string"],
                        "description": "The ID of the file this chunk belongs to"
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
                        "name": "metadata",
                        "dataType": ["text"],
                        "description": "Additional metadata about the chunk"
                    }
                ]
            }
            self.weaviate_client.schema.create_class(class_obj)

    def embed_chunks(self, chunks: List[Chunk]) -> Dict[str, str]:
        """Embed chunks and store them in Weaviate"""
        if not chunks:
            return {}

        # Extract text from chunks
        texts = [chunk.content for chunk in chunks]

        # Generate embeddings
        embeddings = self.embeddings.embed_documents(texts)

        # Store in Weaviate if available
        chunk_embedding_ids = {}

        if self.weaviate_client:
            for i, chunk in enumerate(chunks):
                # Create a unique ID for the embedding
                embedding_id = str(uuid.uuid4())

                # Store in Weaviate
                self.weaviate_client.data_object.create(
                    class_name="DocumentChunk",
                    data_object={
                        "content": chunk.content,
                        "file_id": chunk.file_id,
                        "page_number": chunk.page_number,
                        "chunk_index": chunk.chunk_index,
                        "metadata": str(chunk.metadata)
                    },
                    uuid=embedding_id,
                    vector=embeddings[i]
                )

                chunk_embedding_ids[chunk.id] = embedding_id

        return chunk_embedding_ids

    def search_similar_chunks(self, query: str, file_ids: List[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for chunks similar to the query"""
        if not self.weaviate_client:
            return []

        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)

        # Build Weaviate query
        query_builder = (
            self.weaviate_client.query
            .get("DocumentChunk", ["content", "file_id", "page_number", "chunk_index", "metadata"])
            .with_near_vector({"vector": query_embedding})
            .with_limit(limit)
        )

        # Add file filter if specified
        if file_ids:
            query_builder = query_builder.with_where({
                "operator": "Or",
                "operands": [{"path": ["file_id"], "operator": "Equal", "valueString": file_id} for file_id in file_ids]
            })

        # Execute query
        result = query_builder.do()

        # Extract results
        chunks = []
        if "data" in result and "Get" in result["data"] and "DocumentChunk" in result["data"]["Get"]:
            chunks = result["data"]["Get"]["DocumentChunk"]

        return chunks
