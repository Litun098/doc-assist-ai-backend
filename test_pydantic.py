from langchain.tools import BaseTool
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class TestModel:
    """A test model for llama_index_service."""
    
    def query_documents(self, query: str, file_ids: List[str], user_id: str, top_k: int = 5) -> Dict[str, Any]:
        """Query documents."""
        return {"response": f"Test response for query: {query}"}

class DocumentRetrievalToolSimple(BaseTool):
    """Tool for retrieving information from documents."""
    
    name = "document_retrieval"
    description = "Retrieve information from documents based on a query"
    
    def __init__(self, service):
        super().__init__()
        self._service = service
        
    @property
    def service(self):
        return self._service
    
    def _run(self, query: str, file_ids: List[str], user_id: str) -> str:
        """Run the tool."""
        try:
            result = self.service.query_documents(
                query=query,
                file_ids=file_ids,
                user_id=user_id,
                top_k=5
            )
            return result["response"]
        except Exception as e:
            return f"Error retrieving documents: {str(e)}"

# Create a test instance
test_model = TestModel()
tool = DocumentRetrievalToolSimple(test_model)

# Test the tool
result = tool._run("test query", ["file1", "file2"], "user1")
print(f"Result: {result}")
