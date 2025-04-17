"""
Test script for combined agent capabilities.
"""
import sys
import os
import asyncio
import uuid

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.combined_agent_service import combined_agent_service


async def create_test_text_file():
    """Create a test text file for analysis."""
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
    
    print(f"Created test text file: {file_path}")
    print(f"File ID: {file_id}")
    
    return file_id


async def test_combined_agent():
    """Test combined agent capabilities."""
    # Check if OpenAI API key is set
    from config.config import settings
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_openai_api_key":
        print("Error: OpenAI API key is not set. Please set it in your .env file.")
        print("OPENAI_API_KEY=your_actual_api_key")
        return None
    
    # Create a test text file
    file_id = await create_test_text_file()
    
    # Test queries
    queries = [
        "What was the total revenue in 2023?",
        "Compare the revenue and expenses for each quarter",
        "What was the profit trend throughout the year?"
    ]
    
    print("\nTesting combined agent capabilities...")
    for query in queries:
        print(f"\nQuery: {query}")
        try:
            result = await combined_agent_service.process_request(
                query=query,
                user_id="test_user",
                file_ids=[file_id]
            )
            
            print(f"Response: {result.get('response', '')}")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    return file_id


async def main():
    """Main test function."""
    print("Testing combined agent capabilities...")
    
    # Test agent capabilities
    file_id = await test_combined_agent()
    
    if file_id:
        print("\nCombined agent capabilities test complete!")


if __name__ == "__main__":
    asyncio.run(main())
