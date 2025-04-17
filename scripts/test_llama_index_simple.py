"""
Simple test script for LlamaIndex.
"""
import sys
import os
import uuid

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import config
from config.config import settings

def create_test_document():
    """Create a test document for indexing."""
    # Create a test directory
    test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
    os.makedirs(test_dir, exist_ok=True)
    
    # Generate a unique ID for the file
    file_id = str(uuid.uuid4())
    file_path = os.path.join(test_dir, f"{file_id}.txt")
    
    # Create a sample text file
    with open(file_path, "w") as f:
        f.write("# Financial Report 2023\n\n")
        f.write("## Revenue\n\n")
        f.write("Total revenue for 2023: $1,500,000\n")
        f.write("Q1 Revenue: $300,000\n")
        f.write("Q2 Revenue: $350,000\n")
        f.write("Q3 Revenue: $400,000\n")
        f.write("Q4 Revenue: $450,000\n\n")
        f.write("## Expenses\n\n")
        f.write("Total expenses for 2023: $1,000,000\n")
        f.write("Q1 Expenses: $220,000\n")
        f.write("Q2 Expenses: $240,000\n")
        f.write("Q3 Expenses: $260,000\n")
        f.write("Q4 Expenses: $280,000\n\n")
        f.write("## Profit\n\n")
        f.write("Total profit for 2023: $500,000\n")
        f.write("Q1 Profit: $80,000\n")
        f.write("Q2 Profit: $110,000\n")
        f.write("Q3 Profit: $140,000\n")
        f.write("Q4 Profit: $170,000\n")
    
    print(f"Created test document: {file_path}")
    print(f"File ID: {file_id}")
    
    return file_path, file_id

def test_llama_index_simple():
    """Test basic LlamaIndex functionality."""
    print("Testing basic LlamaIndex functionality...")
    
    # Check if OpenAI API key is set
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_openai_api_key":
        print("Error: OpenAI API key is not set. Please set it in your .env file.")
        print("OPENAI_API_KEY=your_actual_api_key")
        return
    
    try:
        # Import LlamaIndex (do this inside the function to catch import errors)
        from llama_index.core import Document, VectorStoreIndex
        from llama_index.llms.openai import OpenAI
        
        # Create a test document
        file_path, file_id = create_test_document()
        
        # Read the file content
        with open(file_path, "r") as f:
            content = f.read()
        
        # Create a Document object
        document = Document(text=content)
        
        # Create an LLM
        llm = OpenAI(model="gpt-3.5-turbo", api_key=settings.OPENAI_API_KEY)
        
        # Create an index from the document
        index = VectorStoreIndex.from_documents([document], llm=llm)
        
        # Create a query engine
        query_engine = index.as_query_engine()
        
        # Test queries
        queries = [
            "What was the total revenue in 2023?",
            "Compare the revenue and expenses for each quarter",
            "What was the profit trend throughout the year?"
        ]
        
        print("\nTesting queries...")
        for query in queries:
            print(f"\nQuery: {query}")
            try:
                response = query_engine.query(query)
                print(f"Response: {response}")
            except Exception as e:
                print(f"Error: {str(e)}")
        
        print("\nLlamaIndex basic test complete!")
    
    except ImportError as e:
        print(f"Import error: {str(e)}")
        print("Please make sure you have installed all the required packages:")
        print("pip install llama-index llama-index-embeddings-openai llama-index-llms-openai")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_llama_index_simple()
