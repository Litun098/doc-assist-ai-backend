"""
Test script for agent capabilities.
"""
import sys
import os
import asyncio
import json
import uuid
import pandas as pd
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.agent_service import agent_service


async def create_test_excel_file():
    """Create a test Excel file for analysis."""
    # Create a test directory
    test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
    os.makedirs(test_dir, exist_ok=True)
    
    # Generate a unique ID for the file
    file_id = str(uuid.uuid4())
    file_path = os.path.join(test_dir, f"{file_id}.xlsx")
    
    # Create a sample DataFrame
    data = {
        'Month': ['January', 'February', 'March', 'April', 'May', 'June'],
        'Revenue': [10000, 12000, 15000, 14000, 16000, 18000],
        'Expenses': [8000, 9000, 10000, 11000, 10500, 12000],
        'Profit': [2000, 3000, 5000, 3000, 5500, 6000]
    }
    df = pd.DataFrame(data)
    
    # Save to Excel
    df.to_excel(file_path, index=False)
    
    print(f"Created test Excel file: {file_path}")
    
    return file_id


async def test_agent_capabilities():
    """Test agent capabilities."""
    # Create a test Excel file
    file_id = await create_test_excel_file()
    
    # Test queries
    queries = [
        "What is the total revenue in the Excel file?",
        "Create a bar chart of revenue by month and summarize the trends",
        "Compare revenue and expenses, then create a line chart showing both"
    ]
    
    print("\nTesting agent capabilities...")
    for query in queries:
        print(f"\nQuery: {query}")
        result = await agent_service.process_request(
            query=query,
            user_id="test_user",
            file_ids=[file_id]
        )
        
        print(f"Response: {result.get('response', '')}")
        
        # Print other details
        if 'error' in result:
            print(f"Error: {result['error']}")
    
    return file_id


async def main():
    """Main test function."""
    print("Testing agent capabilities...")
    
    # Test agent capabilities
    file_id = await test_agent_capabilities()
    
    print("\nAgent capabilities test complete!")


if __name__ == "__main__":
    asyncio.run(main())
