"""
Simplified agent service for multi-step reasoning.
"""
import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# LangChain imports
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# Local imports
from app.services.llama_index_service import llama_index_service
from app.models.db_models import FileType
from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class SimpleDocumentRetrievalTool:
    """Simple tool for retrieving information from documents."""
    
    def __init__(self, llama_index_service):
        self.llama_index_service = llama_index_service
    
    async def run(self, query: str, file_ids: List[str], user_id: str) -> str:
        """Run the tool asynchronously."""
        try:
            result = await self.llama_index_service.query_documents(
                query=query,
                file_ids=file_ids,
                user_id=user_id,
                top_k=5
            )
            return result["response"]
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            return f"Error retrieving documents: {str(e)}"


class SimpleAgentService:
    """Simplified service for multi-step reasoning."""
    
    def __init__(self):
        """Initialize the agent service."""
        # Initialize document retrieval tool
        self.document_retrieval_tool = SimpleDocumentRetrievalTool(llama_index_service)
        
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
            
            # Step 2: Retrieve relevant information from documents
            document_info = await self.document_retrieval_tool.run(
                query=query,
                file_ids=file_ids or [],
                user_id=user_id
            )
            
            # Step 3: Generate a response based on the retrieved information
            response_prompt = PromptTemplate(
                input_variables=["query", "analysis", "document_info"],
                template="""
                You are an AI assistant that helps users with document-related queries.
                
                Query: {query}
                
                Analysis of the query:
                {analysis}
                
                Information retrieved from documents:
                {document_info}
                
                Please provide a comprehensive response to the user's query based on the information above.
                """
            )
            response_chain = LLMChain(llm=self.llm, prompt=response_prompt)
            response = response_chain.run(
                query=query,
                analysis=analysis,
                document_info=document_info
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
                    "document_retrieval": document_info
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
simple_agent_service = SimpleAgentService()
