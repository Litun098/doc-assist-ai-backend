# LlamaIndex Integration for AnyDocAI

This document explains how to use LlamaIndex for document processing, indexing, and querying in AnyDocAI.

## Overview

AnyDocAI uses LlamaIndex for:

1. **Document Loading**: Loading and parsing various document types (PDF, DOCX, XLSX, PPTX, TXT)
2. **Document Chunking**: Splitting documents into semantic chunks for better retrieval
3. **Vector Indexing**: Creating and managing vector indexes in Weaviate
4. **Document Querying**: Retrieving relevant document chunks and generating answers

## Architecture

The LlamaIndex integration consists of the following components:

1. **LlamaIndexService**: Core service for document processing and querying
2. **Celery Tasks**: Background tasks for processing large documents
3. **FastAPI Endpoints**: API endpoints for file upload and querying

## Setup

### Installation

Install the required dependencies:

```bash
pip install -r requirements-llamaindex.txt
```

### Configuration

Configure the following settings in `.env`:

```
# OpenAI API Key (required for embeddings and LLM)
OPENAI_API_KEY=your_openai_api_key

# Weaviate (for vector storage)
WEAVIATE_URL=your_weaviate_url
WEAVIATE_API_KEY=your_weaviate_api_key
```

## Usage

### Processing Documents

There are two ways to process documents:

1. **Synchronous Processing** (for small files):

```python
from app.services.llama_index_service import llama_index_service, ChunkingStrategy

# Process a file
result = await llama_index_service.process_file(
    file_path="path/to/file.pdf",
    file_id="unique_file_id",
    user_id="user_id",
    file_type=FileType.PDF,
    chunking_strategy=ChunkingStrategy.HYBRID
)
```

2. **Asynchronous Processing** (for large files):

```python
from app.workers.llama_index_tasks import process_file_with_llama_index

# Start a background task
process_file_with_llama_index.delay(
    file_id="unique_file_id",
    user_id="user_id",
    file_path="path/to/file.pdf",
    file_type="pdf"
)
```

### Querying Documents

```python
from app.services.llama_index_service import llama_index_service

# Query documents
result = await llama_index_service.query_documents(
    query="What is the main topic of the document?",
    file_ids=["file_id_1", "file_id_2"],
    user_id="user_id",
    top_k=5
)

# Access the response
response_text = result["response"]
source_documents = result["source_documents"]
model_used = result["model_used"]
```

## API Endpoints

### Upload a File

```
POST /api/llama-index/upload
```

Parameters:
- `file`: The file to upload (multipart/form-data)
- `user_id`: ID of the user uploading the file
- `process_immediately`: Whether to process the file immediately (default: false)
- `chunking_strategy`: Chunking strategy to use (default: hybrid)

### Query Documents

```
POST /api/llama-index/query
```

Parameters:
- `content`: The query text
- `file_ids`: List of file IDs to search in
- `session_id`: Optional session ID for conversation context
- `user_id`: ID of the user making the query

## Chunking Strategies

AnyDocAI supports three chunking strategies:

1. **Fixed Size**: Splits documents into chunks of fixed size with overlap
2. **Semantic**: Splits documents based on semantic boundaries (sentences, paragraphs)
3. **Hybrid**: Combines fixed size and semantic chunking based on document type

## User-Level Isolation

Documents are isolated at the user level through:

1. **User ID in Metadata**: Each document chunk includes the user ID in its metadata
2. **Query Filtering**: Queries are filtered to only return results from the user's documents
3. **Access Control**: API endpoints verify user access to files

## Versioning

Document indexes are versioned through:

1. **File ID**: Each file has a unique ID that is included in the chunk metadata
2. **Chunk Metadata**: Each chunk includes metadata about its source file, page, and position
3. **Embedding ID**: Each chunk has a unique embedding ID for tracking and updating

## Scaling

The LlamaIndex integration is designed to scale through:

1. **Celery Background Tasks**: Large documents are processed in the background
2. **Weaviate Vector Store**: Scales to millions of document chunks
3. **Stateless Services**: Services can be scaled horizontally

## Troubleshooting

Common issues and solutions:

1. **OpenAI API Key**: Ensure your OpenAI API key is valid and has sufficient quota
2. **Weaviate Connection**: Check that Weaviate is running and accessible
3. **File Types**: Ensure you're using supported file types
4. **Memory Issues**: For large documents, use the background processing option
