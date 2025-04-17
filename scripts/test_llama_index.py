"""
Test script for LlamaIndex integration.
"""
import sys
import os
import asyncio
from datetime import datetime
import uuid

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llama_index_service import llama_index_service, ChunkingStrategy
from app.models.db_models import FileType


async def test_process_file():
    """Test processing a file with LlamaIndex."""
    # Create a test file
    test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
    os.makedirs(test_dir, exist_ok=True)
    
    test_file_id = str(uuid.uuid4())
    test_file_path = os.path.join(test_dir, f"{test_file_id}.txt")
    
    # Create a simple text file for testing
    with open(test_file_path, "w") as f:
        f.write("# Test Document\n\n")
        f.write("This is a test document for LlamaIndex integration.\n\n")
        f.write("## Section 1\n\n")
        f.write("This is the first section of the document. It contains some text that will be processed.\n")
        f.write("LlamaIndex should split this into chunks and index it for retrieval.\n\n")
        f.write("## Section 2\n\n")
        f.write("This is the second section of the document. It contains different information.\n")
        f.write("We'll use this to test the retrieval capabilities of LlamaIndex.\n\n")
        f.write("## Section 3\n\n")
        f.write("This is the third section with some technical information.\n")
        f.write("LlamaIndex is a data framework for LLM applications to ingest, structure, and access private or domain-specific data.\n")
        f.write("It's designed to help developers build RAG (Retrieval Augmented Generation) systems.\n")
    
    print(f"Created test file: {test_file_path}")
    
    # Process the file
    print("Processing file with LlamaIndex...")
    result = await llama_index_service.process_file(
        file_path=test_file_path,
        file_id=test_file_id,
        user_id="test_user",
        file_type=FileType.TXT,
        chunking_strategy=ChunkingStrategy.HYBRID
    )
    
    print(f"File processed successfully!")
    print(f"Page count: {result.get('page_count', 0)}")
    print(f"Has images: {result.get('has_images', False)}")
    print(f"Chunk count: {result.get('chunk_count', 0)}")
    
    # Print some chunks
    chunks = result.get("chunks", [])
    if chunks:
        print("\nSample chunks:")
        for i, chunk in enumerate(chunks[:3]):  # Print first 3 chunks
            print(f"Chunk {i+1}:")
            print(f"  Content: {chunk.content[:100]}...")
            print(f"  Metadata: {chunk.metadata}")
            print()
    
    return test_file_id, chunks


async def test_query(test_file_id: str):
    """Test querying with LlamaIndex."""
    # Test queries
    queries = [
        "What is LlamaIndex?",
        "What are the sections in the document?",
        "What is RAG?"
    ]
    
    print("\nTesting queries...")
    for query in queries:
        print(f"\nQuery: {query}")
        result = await llama_index_service.query_documents(
            query=query,
            file_ids=[test_file_id],
            user_id="test_user",
            top_k=2
        )
        
        print(f"Response: {result['response']}")
        print(f"Model used: {result['model_used']}")
        print(f"Source documents: {len(result['source_documents'])}")
        for i, doc in enumerate(result['source_documents']):
            print(f"Document {i+1}:")
            print(f"  Content: {doc['content'][:100]}...")
            print(f"  Metadata: {doc['metadata']}")


async def main():
    """Main test function."""
    print("Testing LlamaIndex integration...")
    
    # Test processing a file
    test_file_id, chunks = await test_process_file()
    
    # Test querying
    await test_query(test_file_id)
    
    print("\nLlamaIndex integration test complete!")


if __name__ == "__main__":
    asyncio.run(main())
