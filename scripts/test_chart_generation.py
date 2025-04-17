"""
Test script for chart generation capabilities.
"""
import sys
import os
import asyncio
import uuid
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.simple_combined_agent import simple_combined_agent
from config.config import settings


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


async def test_chart_generation():
    """Test chart generation capabilities."""
    # Check if OpenAI API key is set
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_openai_api_key":
        print("Error: OpenAI API key is not set. Please set it in your .env file.")
        print("OPENAI_API_KEY=your_actual_api_key")
        return None
    
    # Create a test text file
    file_id = await create_test_text_file()
    
    # Test queries
    queries = [
        "Generate a chart showing the revenue trend throughout the year",
        "Create a chart comparing revenue and expenses for each quarter",
        "Show me a visualization of the profit growth over the quarters"
    ]
    
    print("\nTesting chart generation capabilities...")
    for query in queries:
        print(f"\nQuery: {query}")
        try:
            result = await simple_combined_agent.process_request(
                query=query,
                user_id="test_user",
                file_ids=[file_id]
            )
            
            print(f"Response: {result.get('response', '')}")
            
            # Check if chart data is available
            if 'chart_data' in result:
                print("\nChart data generated:")
                chart_data = result['chart_data']
                print(f"Chart type: {chart_data.get('type', 'unknown')}")
                print(f"Chart title: {chart_data.get('title', 'untitled')}")
                
                # Print dataset labels
                if 'data' in chart_data and 'datasets' in chart_data['data']:
                    print("Datasets:")
                    for dataset in chart_data['data']['datasets']:
                        print(f"  - {dataset.get('label', 'unlabeled')}: {dataset.get('data', [])}")
            else:
                print("No chart data was generated.")
                
        except Exception as e:
            print(f"Error: {str(e)}")
    
    return file_id


async def main():
    """Main test function."""
    print("Testing chart generation capabilities...")
    
    # Test chart generation
    file_id = await test_chart_generation()
    
    if file_id:
        print("\nChart generation test complete!")


if __name__ == "__main__":
    asyncio.run(main())
