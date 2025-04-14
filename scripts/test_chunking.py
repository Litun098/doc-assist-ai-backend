import sys
import os
import json
from pprint import pprint

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.db_models import FileType
from app.services.chunker import HybridChunker, FixedSizeChunker, TopicBasedChunker

# Sample texts for testing
SAMPLE_TEXT_WITH_HEADINGS = """# Introduction to Document Chunking

Document chunking is a critical part of any document processing system. It involves breaking down large documents into smaller, more manageable pieces called "chunks".

## Why Chunking Matters

Chunking is important for several reasons:
1. It allows for more efficient processing of large documents
2. It enables more precise retrieval of relevant information
3. It helps maintain context when working with language models

### Types of Chunking Strategies

There are several approaches to chunking:

#### Fixed-Size Chunking
This approach divides text into chunks of approximately equal size, with some overlap between chunks to maintain context across chunk boundaries.

#### Topic-Based Chunking
This approach tries to keep semantically related content together by identifying natural boundaries in the text, such as headings, paragraphs, or topic shifts.

## Implementation Considerations

When implementing a chunking system, consider:
- The nature of your documents
- The requirements of your downstream tasks
- The trade-off between chunk size and context preservation

# Conclusion

Choosing the right chunking strategy can significantly impact the performance of your document processing system. A hybrid approach that adapts to different document types often yields the best results.
"""

SAMPLE_SPREADSHEET_TEXT = """Sheet: Sales Data
Product ID  Product Name  Category  Price  Units Sold  Revenue
P001  Widget A  Hardware  19.99  150  2998.50
P002  Widget B  Hardware  24.99  120  2998.80
P003  Software X  Software  99.99  75  7499.25
P004  Software Y  Software  149.99  50  7499.50
P005  Service Z  Services  299.99  25  7499.75

Sheet: Customer Data
Customer ID  Name  Email  Purchase Count  Total Spent
C001  John Doe  john@example.com  5  599.95
C002  Jane Smith  jane@example.com  3  449.97
C003  Bob Johnson  bob@example.com  8  1199.92
C004  Alice Brown  alice@example.com  2  199.98
C005  Charlie Davis  charlie@example.com  6  899.94
"""

def test_fixed_size_chunking():
    """Test fixed-size chunking"""
    print("\n=== Testing Fixed-Size Chunking ===\n")
    
    chunker = FixedSizeChunker(chunk_size=500, chunk_overlap=100)
    chunks = chunker.chunk_text(SAMPLE_TEXT_WITH_HEADINGS)
    
    print(f"Created {len(chunks)} chunks")
    for i, (chunk_text, metadata) in enumerate(chunks):
        print(f"\nChunk {i+1}:")
        print(f"Length: {len(chunk_text)} characters")
        print(f"Metadata: {json.dumps(metadata, indent=2)}")
        print(f"Preview: {chunk_text[:100]}...")

def test_topic_based_chunking():
    """Test topic-based chunking"""
    print("\n=== Testing Topic-Based Chunking ===\n")
    
    chunker = TopicBasedChunker(max_chunk_size=1000, min_chunk_size=100)
    chunks = chunker.chunk_text(SAMPLE_TEXT_WITH_HEADINGS)
    
    print(f"Created {len(chunks)} chunks")
    for i, (chunk_text, metadata) in enumerate(chunks):
        print(f"\nChunk {i+1}:")
        print(f"Length: {len(chunk_text)} characters")
        print(f"Heading: {metadata.get('heading', 'None')}")
        print(f"Metadata: {json.dumps(metadata, indent=2)}")
        print(f"Preview: {chunk_text[:100]}...")

def test_hybrid_chunking():
    """Test hybrid chunking system"""
    print("\n=== Testing Hybrid Chunking System ===\n")
    
    hybrid_chunker = HybridChunker()
    
    # Test with text document (should use topic-based chunking)
    print("\n--- Testing with text document (PDF) ---\n")
    text_chunks = hybrid_chunker.chunk_text(
        SAMPLE_TEXT_WITH_HEADINGS,
        file_type=FileType.PDF
    )
    
    print(f"Created {len(text_chunks)} chunks")
    for i, (chunk_text, metadata) in enumerate(text_chunks):
        print(f"\nChunk {i+1}:")
        print(f"Strategy: {metadata.get('chunking_strategy')}")
        print(f"Heading: {metadata.get('heading', 'None')}")
        print(f"Length: {len(chunk_text)} characters")
        print(f"Preview: {chunk_text[:100]}...")
    
    # Test with spreadsheet (should use fixed-size chunking)
    print("\n--- Testing with spreadsheet (XLSX) ---\n")
    spreadsheet_chunks = hybrid_chunker.chunk_text(
        SAMPLE_SPREADSHEET_TEXT,
        file_type=FileType.XLSX
    )
    
    print(f"Created {len(spreadsheet_chunks)} chunks")
    for i, (chunk_text, metadata) in enumerate(spreadsheet_chunks):
        print(f"\nChunk {i+1}:")
        print(f"Strategy: {metadata.get('chunking_strategy')}")
        print(f"Length: {len(chunk_text)} characters")
        print(f"Preview: {chunk_text[:100]}...")

if __name__ == "__main__":
    # Run all tests
    test_fixed_size_chunking()
    test_topic_based_chunking()
    test_hybrid_chunking()
