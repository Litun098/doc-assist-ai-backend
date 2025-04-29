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
            try:
                # Try the new Weaviate client format first
                from weaviate.classes.init import Auth, AdditionalConfig, Timeout
                # Make sure we're using the REST endpoint, not gRPC
                weaviate_url = settings.WEAVIATE_URL
                if not weaviate_url.startswith("https://"):
                    weaviate_url = f"https://{weaviate_url}"

                print(f"Connecting to Weaviate at {weaviate_url}")
                self.weaviate_client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=weaviate_url,
                    auth_credentials=Auth.api_key(settings.WEAVIATE_API_KEY),
                    skip_init_checks=True,  # Skip initialization checks
                    additional_config=AdditionalConfig(
                        timeout=Timeout(init=60)  # Increase timeout to 60 seconds
                    )
                )
            except (ImportError, AttributeError):
                # Fall back to the older client format
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

        try:
            # Try v4 API first
            try:
                # Check if collection exists
                collections = self.weaviate_client.collections.list_all()
                collection_names = []

                # Handle different return types
                for collection in collections:
                    if hasattr(collection, 'name'):
                        collection_names.append(collection.name)
                    elif isinstance(collection, str):
                        collection_names.append(collection)
                    elif isinstance(collection, dict) and 'name' in collection:
                        collection_names.append(collection['name'])

                print(f"Found collections: {collection_names}")

                # Create collection if it doesn't exist
                if "DocumentChunk" not in collection_names:
                    print("Creating DocumentChunk collection...")
                    try:
                        # Try v4 API
                        self.weaviate_client.collections.create(
                            name="DocumentChunk",
                            description="A chunk of text from a document",
                            vectorizer_config=None,  # We'll provide our own vectors
                            properties=[
                                {
                                    "name": "content",
                                    "data_type": ["text"],
                                    "description": "The text content of the chunk"
                                },
                                {
                                    "name": "file_id",
                                    "data_type": ["string"],
                                    "description": "The ID of the file this chunk belongs to"
                                },
                                {
                                    "name": "page_number",
                                    "data_type": ["int"],
                                    "description": "The page number this chunk is from"
                                },
                                {
                                    "name": "chunk_index",
                                    "data_type": ["int"],
                                    "description": "The index of this chunk within the file"
                                },
                                {
                                    "name": "chunking_strategy",
                                    "data_type": ["string"],
                                    "description": "The chunking strategy used (fixed_size or topic_based)"
                                },
                                {
                                    "name": "heading",
                                    "data_type": ["text"],
                                    "description": "The heading or title of the section (for topic-based chunks)"
                                },
                                {
                                    "name": "is_first_in_section",
                                    "data_type": ["boolean"],
                                    "description": "Whether this chunk is the first in its section"
                                },
                                {
                                    "name": "metadata",
                                    "data_type": ["text"],
                                    "description": "Additional metadata about the chunk"
                                }
                            ]
                        )
                        print("DocumentChunk collection created successfully")
                    except Exception as e:
                        print(f"Error creating collection with v4 API: {str(e)}")
                        raise
            except AttributeError:
                # Fall back to v3 API
                print("Falling back to v3 API...")

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
                                "name": "chunking_strategy",
                                "dataType": ["string"],
                                "description": "The chunking strategy used (fixed_size or topic_based)"
                            },
                            {
                                "name": "heading",
                                "dataType": ["text"],
                                "description": "The heading or title of the section (for topic-based chunks)"
                            },
                            {
                                "name": "is_first_in_section",
                                "dataType": ["boolean"],
                                "description": "Whether this chunk is the first in its section"
                            },
                            {
                                "name": "metadata",
                                "dataType": ["text"],
                                "description": "Additional metadata about the chunk"
                            }
                        ]
                    }
                    self.weaviate_client.schema.create_class(class_obj)
                    print("DocumentChunk class created successfully")
        except Exception as e:
            print(f"Error ensuring schema: {str(e)}")

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

                try:
                    # Try v4 API first
                    try:
                        # Get the collection
                        collection = self.weaviate_client.collections.get("DocumentChunk")

                        # Store in Weaviate
                        collection.data.insert(
                            properties={
                                "content": chunk.content,
                                "file_id": chunk.file_id,
                                "page_number": chunk.page_number,
                                "chunk_index": chunk.chunk_index,
                                "metadata": str(chunk.metadata)
                            },
                            uuid=embedding_id,
                            vector=embeddings[i]
                        )
                    except AttributeError:
                        # Fall back to v3 API
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
                except Exception as e:
                    print(f"Error storing chunk in Weaviate: {str(e)}")
                    # Continue with the next chunk

        return chunk_embedding_ids

    def search_similar_chunks(self, query: str, file_ids: List[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for chunks similar to the query"""
        if not self.weaviate_client:
            return []

        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)

        try:
            # Try v4 API first
            try:
                # Get the collection
                collection = self.weaviate_client.collections.get("DocumentChunk")

                # Build query
                query_obj = collection.query.near_vector(
                    vector=query_embedding,
                    limit=limit
                )

                # Add file filter if specified
                if file_ids:
                    # Create filter for file_ids
                    file_filter = collection.query.filter.by_property("file_id").contains_any(file_ids)
                    query_obj = query_obj.with_where(file_filter)

                # Execute query
                result = query_obj.objects

                # Convert to the expected format
                chunks = []
                for obj in result:
                    chunks.append({
                        "content": obj.properties.get("content", ""),
                        "file_id": obj.properties.get("file_id", ""),
                        "page_number": obj.properties.get("page_number", 0),
                        "chunk_index": obj.properties.get("chunk_index", 0),
                        "metadata": obj.properties.get("metadata", "")
                    })

                return chunks
            except AttributeError:
                # Fall back to v3 API
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
        except Exception as e:
            print(f"Error searching similar chunks: {str(e)}")
            return []
