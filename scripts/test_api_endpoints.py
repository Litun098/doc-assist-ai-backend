"""
Simple command-line tool to test API endpoints.
"""
import sys
import os
import requests
import json
import uuid

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

def test_standalone_agent_endpoint():
    """Test the standalone agent endpoint."""
    print("Testing standalone agent endpoint...")

    # Create a test document
    file_path, file_id = create_test_document()

    # API endpoint
    url = "http://localhost:8000/api/standalone-agent/process"

    # Test queries
    queries = [
        "What was the total revenue in 2023?",
        "Compare the revenue and expenses for each quarter",
        "What was the profit trend throughout the year?"
    ]

    # Test each query
    for query in queries:
        print(f"\nQuery: {query}")

        # Prepare the request
        data = {
            "content": query,
            "file_ids": [file_id],
            "session_id": str(uuid.uuid4())
        }

        # Add form data
        form_data = {
            "user_id": "test_user"
        }

        try:
            # Send the request
            response = requests.post(url, json=data, data=form_data)

            # Check the response
            if response.status_code == 200:
                result = response.json()
                print(f"Response: {result.get('content', '')}")
            else:
                print(f"Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Error: {str(e)}")

    print("\nStandalone agent endpoint test complete!")

def test_simple_combined_endpoint():
    """Test the simple combined agent endpoint."""
    print("Testing simple combined agent endpoint...")

    # Create a test document
    file_path, file_id = create_test_document()

    # API endpoint
    url = "http://localhost:8000/api/simple-combined/process"

    # Test queries
    queries = [
        "What was the total revenue in 2023?",
        "Compare the revenue and expenses for each quarter",
        "What was the profit trend throughout the year?"
    ]

    # Test each query
    for query in queries:
        print(f"\nQuery: {query}")

        # Prepare the request
        data = {
            "content": query,
            "file_ids": [file_id],
            "session_id": str(uuid.uuid4())
        }

        # Add form data
        form_data = {
            "user_id": "test_user"
        }

        try:
            # Send the request
            response = requests.post(url, json=data, data=form_data)

            # Check the response
            if response.status_code == 200:
                result = response.json()
                print(f"Response: {result.get('content', '')}")
            else:
                print(f"Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Error: {str(e)}")

    print("\nSimple combined agent endpoint test complete!")

def main():
    """Main function."""
    print("Testing API endpoints...")

    # Check if the server is running
    try:
        response = requests.get("http://localhost:8000/")
        if response.status_code != 200:
            print("Error: Server is not running or not accessible.")
            print("Please start the server with: uvicorn main:app --reload")
            return
    except Exception:
        print("Error: Server is not running or not accessible.")
        print("Please start the server with: uvicorn main:app --reload")
        return

    # Test endpoints
    test_standalone_agent_endpoint()
    test_simple_combined_endpoint()

if __name__ == "__main__":
    main()
