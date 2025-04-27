"""
Agent service for multi-step reasoning and tool-using capabilities.
"""
import os
import uuid
import json
import logging
import asyncio
from typing import List, Dict, Any
from datetime import datetime
import base64
from io import BytesIO

# LangChain imports
from langchain.agents import Tool
from langchain.agents import create_openai_functions_agent
from langchain.agents import AgentExecutor
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# Custom tool base class to avoid Pydantic issues
class CustomTool:
    """Base class for custom tools."""

    def __init__(self, name, description):
        self.name = name
        self.description = description

    def _run(self, *_args, **_kwargs):
        """
        Run the tool.

        Args:
            _args: Positional arguments (unused)
            _kwargs: Keyword arguments (unused)

        Returns:
            Tool output
        """
        raise NotImplementedError("Subclasses must implement this method")

    def run(self, *args, **kwargs):
        """
        Run the tool.

        Args:
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Tool output
        """
        return self._run(*args, **kwargs)

# Data processing imports
import pandas as pd
import matplotlib.pyplot as plt

# Local imports
from app.services.llama_index_service import llama_index_service
# from app.models.db_models import FileType
from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class DocumentRetrievalTool(CustomTool):
    """Tool for retrieving information from documents."""

    def __init__(self):
        super().__init__(
            name="document_retrieval",
            description="Retrieve information from documents based on a query"
        )
        self.llama_index_service = None

    async def _arun(self, query: str, file_ids: List[str], user_id: str) -> str:
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

    def _run(self, query: str, file_ids: List[str], user_id: str) -> str:
        """Run the tool synchronously."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self._arun(query, file_ids, user_id))


class ExcelAnalysisTool(CustomTool):
    """Tool for analyzing Excel files."""

    def __init__(self):
        super().__init__(
            name="excel_analysis",
            description="Analyze Excel files to extract data, calculate metrics, and generate insights"
        )
        self.llama_index_service = None

    async def _arun(self, query: str, file_ids: List[str], _user_id: str = None) -> str:
        """
        Run the tool asynchronously.

        Args:
            query: The query to analyze
            file_ids: List of file IDs to analyze
            _user_id: User ID (unused, default: None)

        Returns:
            Analysis results as a string
        """
        try:
            # Get file paths for the Excel files
            file_paths = []
            for file_id in file_ids:
                # In a real implementation, you would get the file path from the database
                # For now, we'll assume the files are in the uploads directory
                file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}.xlsx")
                if os.path.exists(file_path):
                    file_paths.append(file_path)

            if not file_paths:
                return "No Excel files found"

            # Load and analyze the Excel files
            results = []
            for file_path in file_paths:
                # Load the Excel file
                excel_data = pd.read_excel(file_path)

                # Basic analysis
                analysis = {
                    "file_name": os.path.basename(file_path),
                    "shape": excel_data.shape,
                    "columns": excel_data.columns.tolist(),
                    "summary": excel_data.describe().to_dict(),
                    "head": excel_data.head(5).to_dict(orient="records")
                }

                # Add more specific analysis based on the query
                if "total" in query.lower() and "revenue" in query.lower():
                    # Look for revenue column
                    revenue_cols = [col for col in excel_data.columns if "revenue" in col.lower()]
                    if revenue_cols:
                        total_revenue = excel_data[revenue_cols[0]].sum()
                        analysis["total_revenue"] = total_revenue

                results.append(analysis)

            return json.dumps(results, indent=2)

        except Exception as e:
            logger.error(f"Error analyzing Excel files: {str(e)}")
            return f"Error analyzing Excel files: {str(e)}"

    def _run(self, query: str, file_ids: List[str], user_id: str) -> str:
        """Run the tool synchronously."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self._arun(query, file_ids, user_id))


class ChartGenerationTool(CustomTool):
    """Tool for generating charts and visualizations."""

    def __init__(self):
        super().__init__(
            name="chart_generation",
            description="Generate charts and visualizations from data"
        )

    def _run(self, data: str, chart_type: str = "bar") -> str:
        """Run the tool."""
        try:
            # Parse the data
            data_dict = json.loads(data)

            # Create a DataFrame
            if isinstance(data_dict, list) and "head" in data_dict[0]:
                # Use the head data from the Excel analysis
                df = pd.DataFrame(data_dict[0]["head"])
            elif isinstance(data_dict, dict) and "data" in data_dict:
                # Use the data field
                df = pd.DataFrame(data_dict["data"])
            else:
                # Try to convert the dict to a DataFrame
                df = pd.DataFrame(data_dict)

            # Generate the chart
            plt.figure(figsize=(10, 6))

            if chart_type.lower() == "bar":
                df.plot(kind="bar")
            elif chart_type.lower() == "line":
                df.plot(kind="line")
            elif chart_type.lower() == "pie":
                df.plot(kind="pie", y=df.columns[1], autopct="%1.1f%%")
            else:
                df.plot()

            plt.title(f"{chart_type.capitalize()} Chart")
            plt.tight_layout()

            # Save the chart to a BytesIO object
            buffer = BytesIO()
            plt.savefig(buffer, format="png")
            buffer.seek(0)

            # Convert to base64
            image_base64 = base64.b64encode(buffer.read()).decode("utf-8")

            # Save the chart to a file
            chart_id = str(uuid.uuid4())
            chart_path = os.path.join(settings.UPLOAD_DIR, f"chart_{chart_id}.png")
            plt.savefig(chart_path)

            return f"Chart generated and saved to {chart_path}. Base64 image: {image_base64[:50]}..."

        except Exception as e:
            logger.error(f"Error generating chart: {str(e)}")
            return f"Error generating chart: {str(e)}"


class SummaryGenerationTool(CustomTool):
    """Tool for generating summaries."""

    def __init__(self):
        super().__init__(
            name="summary_generation",
            description="Generate summaries from data and analysis results"
        )
        self.llm = ChatOpenAI(model=settings.DEFAULT_MODEL, temperature=0.7)

    def _run(self, data: str, query: str) -> str:
        """Run the tool."""
        try:
            # Create a prompt for summarization
            prompt = PromptTemplate(
                input_variables=["data", "query"],
                template="""
                You are an AI assistant that generates summaries from data and analysis results.

                Data:
                {data}

                Query:
                {query}

                Please generate a concise summary that addresses the query based on the data.
                Focus on key insights, trends, and actionable information.
                """
            )

            # Create a chain
            chain = LLMChain(llm=self.llm, prompt=prompt)

            # Run the chain
            summary = chain.run(data=data, query=query)

            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return f"Error generating summary: {str(e)}"


class AgentService:
    """Service for multi-step reasoning and tool-using capabilities."""

    def __init__(self):
        """Initialize the agent service."""
        # Initialize tools
        self.document_retrieval_tool = DocumentRetrievalTool()
        self.document_retrieval_tool.llama_index_service = llama_index_service

        self.excel_analysis_tool = ExcelAnalysisTool()
        self.excel_analysis_tool.llama_index_service = llama_index_service

        self.chart_generation_tool = ChartGenerationTool()
        self.summary_generation_tool = SummaryGenerationTool()

        # Create tools list
        self.tools = [
            Tool(
                name="document_retrieval",
                func=self.document_retrieval_tool._run,
                description=self.document_retrieval_tool.description
            ),
            Tool(
                name="excel_analysis",
                func=self.excel_analysis_tool._run,
                description=self.excel_analysis_tool.description
            ),
            Tool(
                name="chart_generation",
                func=self.chart_generation_tool._run,
                description=self.chart_generation_tool.description
            ),
            Tool(
                name="summary_generation",
                func=self.summary_generation_tool._run,
                description=self.summary_generation_tool.description
            )
        ]

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=settings.DEFAULT_MODEL,
            temperature=0.7
        )

        # Initialize agent using the new method
        from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

        # Create a prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are AnyDocAI, an AI document assistant that helps users understand their documents.
            You have access to several tools to help you answer questions about documents.
            Use the tools to provide accurate and helpful responses.
            If you don't know the answer, say you don't know. Don't try to make up an answer.
            Always be helpful, concise, and professional."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # Create the agent with the prompt
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )

        # Create agent executor
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=self.tools,
            verbose=True
        )

    async def process_request(self, query: str, user_id: str, file_ids: List[str] = None) -> Dict[str, Any]:
        """
        Process a request using the agent.

        Args:
            query: The user's query
            user_id: The user's ID
            file_ids: List of file IDs to use

        Returns:
            Dict containing the agent's response
        """
        try:
            # Prepare the input
            input_dict = {
                "input": query,
                "user_id": user_id,
                "file_ids": file_ids or []
            }

            # Add empty chat history if not provided
            input_dict["chat_history"] = input_dict.get("chat_history", [])

            # Run the agent executor
            result = self.agent_executor.invoke(input_dict)
            response = result.get("output", "")

            # Format the response
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
agent_service = AgentService()
