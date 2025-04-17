"""
Simple test script for agent capabilities.
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

def test_agent_simple():
    """Test basic agent functionality."""
    print("Testing basic agent functionality...")
    
    # Check if OpenAI API key is set
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_openai_api_key":
        print("Error: OpenAI API key is not set. Please set it in your .env file.")
        print("OPENAI_API_KEY=your_actual_api_key")
        return
    
    try:
        # Import LangChain (do this inside the function to catch import errors)
        from langchain.agents import initialize_agent, Tool
        from langchain.agents import AgentType
        from langchain_openai import ChatOpenAI
        
        # Create a test document
        file_path, file_id = create_test_document()
        
        # Read the file content
        with open(file_path, "r") as f:
            content = f.read()
        
        # Create a simple tool for document search
        def search_document(query):
            """Search the document for information."""
            # In a real implementation, this would use LlamaIndex
            # For now, we'll just do a simple text search
            lines = content.split("\n")
            results = []
            for line in lines:
                if query.lower() in line.lower():
                    results.append(line)
            
            if results:
                return "\n".join(results)
            else:
                return "No relevant information found."
        
        # Create tools
        tools = [
            Tool(
                name="DocumentSearch",
                func=search_document,
                description="Search for information in the document"
            )
        ]
        
        # Create LLM
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        )
        
        # Create agent
        agent = initialize_agent(
            tools,
            llm,
            agent=AgentType.OPENAI_FUNCTIONS,
            verbose=True
        )
        
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
                response = agent.run(f"Use the DocumentSearch tool to find information about: {query}")
                print(f"Response: {response}")
            except Exception as e:
                print(f"Error: {str(e)}")
        
        print("\nAgent basic test complete!")
    
    except ImportError as e:
        print(f"Import error: {str(e)}")
        print("Please make sure you have installed all the required packages:")
        print("pip install langchain langchain-openai")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_agent_simple()
