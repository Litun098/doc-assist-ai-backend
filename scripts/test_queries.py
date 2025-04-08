import sys
import os
import asyncio
from langchain_openai import ChatOpenAI

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import settings
from app.services.embedder import EmbeddingService
from app.services.query_engine import QueryEngine

async def test_query(query: str, file_ids: list = None):
    """Test a query against the query engine"""
    # Initialize services
    embedding_service = EmbeddingService()
    query_engine = QueryEngine(embedding_service)
    
    # Run query
    result = await query_engine.query(
        query=query,
        file_ids=file_ids or [],
        user_plan="paid",
        session_id=None
    )
    
    # Print results
    print(f"Query: {query}")
    print(f"Response: {result['response']}")
    print(f"Model used: {result['model_used']}")
    print(f"Source documents: {len(result['source_documents'])}")
    for i, doc in enumerate(result['source_documents']):
        print(f"Document {i+1}:")
        print(f"  Content: {doc.page_content[:100]}...")
        print(f"  Metadata: {doc.metadata}")
    
    return result

if __name__ == "__main__":
    # Get query from command line
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "What is the main topic of this document?"
    
    # Get file IDs from command line
    file_ids = sys.argv[2:] if len(sys.argv) > 2 else None
    
    # Run test
    asyncio.run(test_query(query, file_ids))
