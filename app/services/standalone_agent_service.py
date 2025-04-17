"""
Standalone agent service that doesn't depend on LlamaIndex.
"""
import os
import uuid
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

# LangChain imports
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# Local imports
from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class DocumentReader:
    """Simple document reader that doesn't depend on LlamaIndex."""
    
    def read_document(self, file_path: str) -> str:
        """
        Read a document from a file path.
        
        Args:
            file_path: Path to the document
            
        Returns:
            The document content as a string
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return f"File not found: {file_path}"
            
            # Read file based on extension
            extension = file_path.split(".")[-1].lower()
            
            if extension == "txt":
                # Read text file
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            
            elif extension == "json":
                # Read JSON file
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return json.dumps(data, indent=2)
            
            else:
                return f"Unsupported file type: {extension}"
        
        except Exception as e:
            logger.error(f"Error reading document: {str(e)}")
            return f"Error reading document: {str(e)}"


class StandaloneAgentService:
    """Standalone agent service that doesn't depend on LlamaIndex."""
    
    def __init__(self):
        """Initialize the standalone agent service."""
        # Initialize document reader
        self.document_reader = DocumentReader()
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=settings.DEFAULT_MODEL,
            temperature=0.7
        )
    
    async def process_request(self, query: str, user_id: str, file_ids: List[str] = None) -> Dict[str, Any]:
        """
        Process a request using a simple multi-step approach.
        
        Args:
            query: The user's query
            user_id: The user's ID
            file_ids: List of file IDs to use
            
        Returns:
            Dict containing the response
        """
        try:
            # Step 1: Analyze the query to determine what needs to be done
            analysis_prompt = PromptTemplate(
                input_variables=["query"],
                template="""
                You are an AI assistant that analyzes user queries to determine what needs to be done.
                
                Query: {query}
                
                Please analyze this query and break it down into steps that need to be performed.
                Return your analysis in a clear, structured format.
                """
            )
            analysis_chain = LLMChain(llm=self.llm, prompt=analysis_prompt)
            analysis = analysis_chain.run(query=query)
            
            # Step 2: Read documents
            document_contents = []
            if file_ids:
                for file_id in file_ids:
                    # In a real implementation, you would get the file path from the database
                    # For now, we'll assume the files are in the uploads directory
                    file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}.txt")
                    content = self.document_reader.read_document(file_path)
                    document_contents.append({
                        "file_id": file_id,
                        "content": content
                    })
            
            # Step 3: Generate a response based on the document contents
            response_prompt = PromptTemplate(
                input_variables=["query", "analysis", "document_contents"],
                template="""
                You are an AI assistant that helps users with document-related queries.
                
                Query: {query}
                
                Analysis of the query:
                {analysis}
                
                Document contents:
                {document_contents}
                
                Please provide a comprehensive response to the user's query based on the information above.
                If the document contents don't contain relevant information, say so.
                """
            )
            response_chain = LLMChain(llm=self.llm, prompt=response_prompt)
            response = response_chain.run(
                query=query,
                analysis=analysis,
                document_contents=str(document_contents)
            )
            
            # Format the result
            result = {
                "response": response,
                "query": query,
                "file_ids": file_ids or [],
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "steps": {
                    "analysis": analysis,
                    "document_contents": document_contents
                }
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return {
                "error": str(e),
                "query": query,
                "file_ids": file_ids or [],
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }


# Create a singleton instance
standalone_agent_service = StandaloneAgentService()
