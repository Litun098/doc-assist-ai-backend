"""
Combined agent service that uses both LangChain and LlamaIndex.
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

# LlamaIndex imports
from llama_index.core import Document, VectorStoreIndex
from llama_index.llms.openai import OpenAI as LlamaOpenAI

# In newer versions of LlamaIndex, SimpleDirectoryReader is in a different location
try:
    from llama_index.readers.file import SimpleDirectoryReader
except ImportError:
    try:
        from llama_index.core.readers import SimpleDirectoryReader
    except ImportError:
        from llama_index.readers import SimpleDirectoryReader

# Local imports
from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Document processor using LlamaIndex."""

    def __init__(self):
        """Initialize the document processor."""
        # Initialize LLM
        self.llm = LlamaOpenAI(model=settings.DEFAULT_MODEL, api_key=settings.OPENAI_API_KEY)

    def read_document(self, file_path: str) -> Document:
        """
        Read a document from a file path.

        Args:
            file_path: Path to the document

        Returns:
            A Document object
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            # Read file using SimpleDirectoryReader
            reader = SimpleDirectoryReader(input_files=[file_path])
            documents = reader.load_data()

            return documents[0]

        except Exception as e:
            logger.error(f"Error reading document: {str(e)}")
            raise

    def create_index(self, documents: List[Document]) -> VectorStoreIndex:
        """
        Create an index from documents.

        Args:
            documents: List of Document objects

        Returns:
            A VectorStoreIndex
        """
        try:
            # Create an index
            index = VectorStoreIndex.from_documents(documents, llm=self.llm)

            return index

        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            raise

    def query_index(self, index: VectorStoreIndex, query: str) -> str:
        """
        Query an index.

        Args:
            index: A VectorStoreIndex
            query: Query string

        Returns:
            A Response object
        """
        try:
            # Create a query engine
            query_engine = index.as_query_engine()

            # Query the index
            response = query_engine.query(query)

            return response

        except Exception as e:
            logger.error(f"Error querying index: {str(e)}")
            raise


class CombinedAgentService:
    """Combined agent service that uses both LangChain and LlamaIndex."""

    def __init__(self):
        """Initialize the combined agent service."""
        # Initialize document processor
        self.document_processor = DocumentProcessor()

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=settings.DEFAULT_MODEL,
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        )

        # Create tools
        self.tools = [
            Tool(
                name="DocumentSearch",
                func=self._search_documents,
                description="Search for information in documents"
            ),
            Tool(
                name="DocumentAnalysis",
                func=self._analyze_documents,
                description="Analyze documents to extract insights"
            ),
            Tool(
                name="SummaryGeneration",
                func=self._generate_summary,
                description="Generate a summary from document content"
            )
        ]

        # Initialize agent
        self.agent = initialize_agent(
            self.tools,
            self.llm,
            agent=AgentType.OPENAI_FUNCTIONS,
            verbose=True
        )

    def _search_documents(self, query: str, file_paths: List[str] = None) -> str:
        """
        Search for information in documents.

        Args:
            query: Query string
            file_paths: List of file paths

        Returns:
            Search results as a string
        """
        try:
            if not file_paths:
                return "No documents provided for search."

            # Read documents
            documents = []
            for file_path in file_paths:
                try:
                    document = self.document_processor.read_document(file_path)
                    documents.append(document)
                except Exception as e:
                    logger.error(f"Error reading document {file_path}: {str(e)}")

            if not documents:
                return "Could not read any documents."

            # Create index
            index = self.document_processor.create_index(documents)

            # Query index
            response = self.document_processor.query_index(index, query)

            return str(response)

        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return f"Error searching documents: {str(e)}"

    def _analyze_documents(self, query: str, file_paths: List[str] = None) -> str:
        """
        Analyze documents to extract insights.

        Args:
            query: Query string
            file_paths: List of file paths

        Returns:
            Analysis results as a string
        """
        try:
            if not file_paths:
                return "No documents provided for analysis."

            # Read documents
            documents = []
            for file_path in file_paths:
                try:
                    document = self.document_processor.read_document(file_path)
                    documents.append(document)
                except Exception as e:
                    logger.error(f"Error reading document {file_path}: {str(e)}")

            if not documents:
                return "Could not read any documents."

            # Create a prompt for analysis
            prompt = PromptTemplate(
                input_variables=["query", "documents"],
                template="""
                You are an AI assistant that analyzes documents to extract insights.

                Query: {query}

                Document content:
                {documents}

                Please analyze the document content and provide insights related to the query.
                Focus on extracting key information, identifying patterns, and providing actionable insights.
                """
            )

            # Create a chain
            chain = LLMChain(llm=self.llm, prompt=prompt)

            # Run the chain
            analysis = chain.run(
                query=query,
                documents="\n\n".join([doc.text for doc in documents])
            )

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing documents: {str(e)}")
            return f"Error analyzing documents: {str(e)}"

    def _generate_summary(self, query: str, file_paths: List[str] = None) -> str:
        """
        Generate a summary from document content.

        Args:
            query: Query string
            file_paths: List of file paths

        Returns:
            Summary as a string
        """
        try:
            if not file_paths:
                return "No documents provided for summarization."

            # Read documents
            documents = []
            for file_path in file_paths:
                try:
                    document = self.document_processor.read_document(file_path)
                    documents.append(document)
                except Exception as e:
                    logger.error(f"Error reading document {file_path}: {str(e)}")

            if not documents:
                return "Could not read any documents."

            # Create a prompt for summarization
            prompt = PromptTemplate(
                input_variables=["query", "documents"],
                template="""
                You are an AI assistant that generates summaries from document content.

                Query: {query}

                Document content:
                {documents}

                Please generate a concise summary that addresses the query based on the document content.
                Focus on key points, main ideas, and important details.
                """
            )

            # Create a chain
            chain = LLMChain(llm=self.llm, prompt=prompt)

            # Run the chain
            summary = chain.run(
                query=query,
                documents="\n\n".join([doc.text for doc in documents])
            )

            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return f"Error generating summary: {str(e)}"

    async def process_request(self, query: str, user_id: str, file_ids: List[str] = None) -> Dict[str, Any]:
        """
        Process a request using the combined agent.

        Args:
            query: The user's query
            user_id: The user's ID
            file_ids: List of file IDs to use

        Returns:
            Dict containing the agent's response
        """
        try:
            # Convert file IDs to file paths
            file_paths = []
            if file_ids:
                for file_id in file_ids:
                    # In a real implementation, you would get the file path from the database
                    # For now, we'll assume the files are in the uploads directory
                    file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}.txt")
                    if os.path.exists(file_path):
                        file_paths.append(file_path)

            # Prepare the input
            input_dict = {
                "input": query,
                "file_paths": file_paths
            }

            # Run the agent
            response = self.agent.run(input_dict)

            # Format the result
            result = {
                "response": response,
                "query": query,
                "file_ids": file_ids or [],
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
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
combined_agent_service = CombinedAgentService()
