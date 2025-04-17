"""
Simple combined agent service that uses both LangChain and LlamaIndex.
"""
import os
import logging
from typing import List, Dict, Any
from datetime import datetime

# LangChain imports
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain_openai import ChatOpenAI
import json

# Local imports
from config.config import settings
from app.utils.chart_generator import generate_trend_chart, generate_comparison_chart

# Configure logging
logger = logging.getLogger(__name__)


class SimpleCombinedAgent:
    """Simple combined agent service that uses both LangChain and LlamaIndex."""

    def __init__(self):
        """Initialize the simple combined agent service."""
        # Initialize LLM with cost-effective model
        self.llm = ChatOpenAI(
            model=settings.FREE_MODEL,  # Using the most cost-effective model
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        )

        # Create tools
        self.tools = [
            Tool(
                name="DocumentSearch",
                func=self._search_documents,
                description="Search for information in documents",
                coroutine=None
            ),
            Tool(
                name="DocumentAnalysis",
                func=self._analyze_documents,
                description="Analyze documents to extract insights",
                coroutine=None
            ),
            Tool(
                name="ChartGeneration",
                func=self._generate_chart,
                description="Generate chart data for visualizing document information",
                coroutine=None
            )
        ]

        # Initialize agent with better instructions
        self.agent = initialize_agent(
            self.tools,
            self.llm,
            agent=AgentType.OPENAI_FUNCTIONS,
            verbose=True,
            handle_parsing_errors=True,
            early_stopping_method="generate",
            max_iterations=3,
            agent_kwargs={
                "prefix": """
                You are a helpful AI assistant that answers questions about documents.
                You have access to tools that can search and analyze documents, and generate charts.

                For questions about specific information like numbers, dates, or facts, use the DocumentSearch tool.
                For questions that require analysis, comparison, or identifying trends, use the DocumentAnalysis tool.
                For requests to visualize data, create charts, or show trends graphically, use the ChartGeneration tool.

                Always try to be helpful and provide the most relevant information from the documents.
                If you can't find the information, explain what you tried and suggest alternatives.

                When generating charts, return the chart data to the user so they can visualize it.
                """
            }
        )

    def _search_documents(self, query: str) -> str:
        """
        Search for information in documents.

        Args:
            query: Query string
            file_paths: List of file paths

        Returns:
            Search results as a string
        """
        try:
            # Get file_paths from the agent's memory
            file_paths = getattr(self, '_current_file_paths', [])

            if not file_paths:
                return "No documents provided for search."

            # Read documents
            document_contents = []
            for file_path in file_paths:
                try:
                    if os.path.exists(file_path):
                        with open(file_path, "r") as f:
                            content = f.read()
                            document_contents.append(content)
                except Exception as e:
                    logger.error(f"Error reading document {file_path}: {str(e)}")

            if not document_contents:
                return "Could not read any documents."

            # Improved search that looks for keywords and context
            # In a real implementation, this would use LlamaIndex or a vector database

            # Extract keywords from the query
            keywords = query.lower().split()
            keywords = [k for k in keywords if len(k) > 3]  # Filter out short words

            # Add common financial terms that might be relevant
            if 'revenue' in query.lower():
                keywords.extend(['revenue', 'income', 'sales', 'total'])
            if 'expense' in query.lower() or 'expenses' in query.lower():
                keywords.extend(['expense', 'expenses', 'cost', 'costs'])
            if 'profit' in query.lower():
                keywords.extend(['profit', 'earnings', 'income', 'margin'])
            if 'quarter' in query.lower() or 'quarterly' in query.lower():
                keywords.extend(['q1', 'q2', 'q3', 'q4', 'quarter'])

            # Search for relevant sections
            results = []
            for content in document_contents:
                lines = content.split("\n")

                # Process the document line by line
                i = 0
                while i < len(lines):
                    line = lines[i]

                    # Check if line contains any keywords
                    if any(keyword in line.lower() for keyword in keywords):
                        # Extract a context window (the line plus surrounding lines)
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)
                        context = "\n".join(lines[start:end])
                        results.append(context)
                    i += 1

            # Remove duplicates while preserving order
            unique_results = []
            for result in results:
                if result not in unique_results:
                    unique_results.append(result)

            if unique_results:
                return "\n\n".join(unique_results)
            else:
                return "No relevant information found in the documents."

        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return f"Error searching documents: {str(e)}"

    def _generate_chart(self, query: str) -> str:
        """
        Generate chart data based on document content.

        Args:
            query: Query string describing the chart to generate

        Returns:
            Chart data as a JSON string
        """
        try:
            # Get file_paths from the agent's memory
            file_paths = getattr(self, '_current_file_paths', [])

            if not file_paths:
                return "No documents provided for chart generation."

            # Read documents
            document_contents = []
            for file_path in file_paths:
                try:
                    if os.path.exists(file_path):
                        with open(file_path, "r") as f:
                            content = f.read()
                            document_contents.append(content)
                except Exception as e:
                    logger.error(f"Error reading document {file_path}: {str(e)}")

            if not document_contents:
                return "Could not read any documents for chart generation."

            # Join all document contents
            full_content = "\n".join(document_contents)

            # Generate appropriate chart data based on query
            chart_data = None

            # Extract financial data
            quarters = ["Q1", "Q2", "Q3", "Q4"]
            revenue_data = []
            expense_data = []
            profit_data = []

            lines = full_content.split('\n')
            for line in lines:
                # Extract revenue data
                if any(f"{q} Revenue: $" in line for q in quarters):
                    try:
                        value = int(line.split('$')[1].replace(',', ''))
                        for i, q in enumerate(quarters):
                            if f"{q} Revenue: $" in line:
                                # Ensure the list is long enough
                                while len(revenue_data) <= i:
                                    revenue_data.append(0)
                                revenue_data[i] = value
                    except (IndexError, ValueError):
                        pass

                # Extract expense data
                if any(f"{q} Expenses: $" in line for q in quarters):
                    try:
                        value = int(line.split('$')[1].replace(',', ''))
                        for i, q in enumerate(quarters):
                            if f"{q} Expenses: $" in line:
                                # Ensure the list is long enough
                                while len(expense_data) <= i:
                                    expense_data.append(0)
                                expense_data[i] = value
                    except (IndexError, ValueError):
                        pass

                # Extract profit data
                if any(f"{q} Profit: $" in line for q in quarters):
                    try:
                        value = int(line.split('$')[1].replace(',', ''))
                        for i, q in enumerate(quarters):
                            if f"{q} Profit: $" in line:
                                # Ensure the list is long enough
                                while len(profit_data) <= i:
                                    profit_data.append(0)
                                profit_data[i] = value
                    except (IndexError, ValueError):
                        pass

            # Determine chart type based on query
            if "trend" in query.lower() or "over time" in query.lower():
                # Create a trend chart
                if "revenue" in query.lower() and len(revenue_data) > 0:
                    chart_data = generate_trend_chart(
                        title="Revenue Trend",
                        labels=quarters[:len(revenue_data)],
                        data=revenue_data,
                        color="rgba(54, 162, 235, 0.5)"
                    )
                elif "expense" in query.lower() and len(expense_data) > 0:
                    chart_data = generate_trend_chart(
                        title="Expense Trend",
                        labels=quarters[:len(expense_data)],
                        data=expense_data,
                        color="rgba(255, 99, 132, 0.5)"
                    )
                elif "profit" in query.lower() and len(profit_data) > 0:
                    chart_data = generate_trend_chart(
                        title="Profit Trend",
                        labels=quarters[:len(profit_data)],
                        data=profit_data,
                        color="rgba(75, 192, 192, 0.5)"
                    )
            else:
                # Default to comparison chart
                datasets = []
                if len(revenue_data) > 0:
                    datasets.append({
                        "label": "Revenue",
                        "data": revenue_data,
                        "backgroundColor": "rgba(54, 162, 235, 0.5)",
                        "borderColor": "rgba(54, 162, 235, 1)",
                        "borderWidth": 1
                    })
                if len(expense_data) > 0:
                    datasets.append({
                        "label": "Expenses",
                        "data": expense_data,
                        "backgroundColor": "rgba(255, 99, 132, 0.5)",
                        "borderColor": "rgba(255, 99, 132, 1)",
                        "borderWidth": 1
                    })
                if len(profit_data) > 0:
                    datasets.append({
                        "label": "Profit",
                        "data": profit_data,
                        "backgroundColor": "rgba(75, 192, 192, 0.5)",
                        "borderColor": "rgba(75, 192, 192, 1)",
                        "borderWidth": 1
                    })

                if datasets:
                    chart_data = generate_comparison_chart(
                        title="Quarterly Financial Performance",
                        labels=quarters[:max(len(revenue_data), len(expense_data), len(profit_data))],
                        datasets=datasets
                    )

            # If we still don't have chart data, return an error
            if not chart_data:
                return "Could not generate chart data from the document content."

            # Return chart data as JSON string
            return json.dumps(chart_data, indent=2)

        except Exception as e:
            logger.error(f"Error generating chart: {str(e)}")
            return f"Error generating chart: {str(e)}"

    def _analyze_documents(self, query: str) -> str:
        """
        Analyze documents to extract insights.

        Args:
            query: Query string
            file_paths: List of file paths

        Returns:
            Analysis results as a string
        """
        try:
            # Get file_paths from the agent's memory
            file_paths = getattr(self, '_current_file_paths', [])

            if not file_paths:
                return "No documents provided for analysis."

            # Read documents
            document_contents = []
            for file_path in file_paths:
                try:
                    if os.path.exists(file_path):
                        with open(file_path, "r") as f:
                            content = f.read()
                            document_contents.append(content)
                except Exception as e:
                    logger.error(f"Error reading document {file_path}: {str(e)}")

            if not document_contents:
                return "Could not read any documents."

            # Use the LLM to analyze the documents
            prompt = f"""
            You are an AI assistant that analyzes financial documents to extract insights.

            Query: {query}

            Document content:
            {' '.join(document_contents)}

            Please analyze the document content and provide insights related to the query.
            Focus on extracting key information, identifying patterns, and providing actionable insights.

            If the query is about revenue, expenses, or profits, make sure to include specific numbers and trends.
            If the query is about comparing quarters, create a clear comparison with the relevant metrics.
            If the query is about trends, identify the pattern and explain what it means.

            Be specific and concise in your analysis.
            """

            # Generate analysis
            analysis = self.llm.invoke(prompt).content

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing documents: {str(e)}")
            return f"Error analyzing documents: {str(e)}"

    async def process_request(self, query: str, user_id: str, file_ids: List[str] = None) -> Dict[str, Any]:
        """
        Process a request using the simple combined agent.

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

            # Store file_paths in the instance for tool access
            self._current_file_paths = file_paths

            # Prepare the input with more context
            input_text = f"""I need information from a document.

            Here's my question: {query}

            Please use the most appropriate tool to find the answer in the document.
            If you need to search for specific information, use DocumentSearch.
            If you need to analyze or compare information, use DocumentAnalysis.
            If you need to create a chart or visualization, use ChartGeneration.
            """

            # Run the agent
            try:
                response = self.agent.run(input_text)
            except Exception as e:
                logger.error(f"Agent execution error: {str(e)}")
                response = f"I encountered an error while processing your request. Please try a more specific question or provide more context."

            # Check if the agent used the ChartGeneration tool
            chart_data = None
            try:
                # Look for the ChartGeneration tool invocation in the agent's steps
                if hasattr(self.agent, 'intermediate_steps') and self.agent.intermediate_steps:
                    for action, tool_output in self.agent.intermediate_steps:
                        if action.tool == 'ChartGeneration' and tool_output:
                            try:
                                # Try to parse the tool output as JSON
                                if tool_output.strip().startswith('{') and tool_output.strip().endswith('}'):
                                    chart_data = json.loads(tool_output)
                                    if 'type' in chart_data and 'data' in chart_data:
                                        logger.info("Chart data detected from ChartGeneration tool")
                                        break
                            except json.JSONDecodeError:
                                pass

                # If we didn't find chart data in the tool outputs, try to extract it from the response
                if not chart_data:
                    # Try to extract JSON from the response text
                    import re
                    # Look for JSON objects in the response
                    json_matches = re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response)
                    for json_match in json_matches:
                        try:
                            potential_chart = json.loads(json_match.group(0))
                            if 'type' in potential_chart and 'data' in potential_chart:
                                chart_data = potential_chart
                                # Clean up the response to remove the JSON
                                response = response.replace(json_match.group(0), "")
                                response = response.strip()
                                logger.info("Extracted chart data from response")
                                break
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.error(f"Error processing chart data: {str(e)}")

            # Format the result
            result = {
                "response": response,
                "query": query,
                "file_ids": file_ids or [],
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }

            # Add chart data if available
            if chart_data:
                result["chart_data"] = chart_data

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
simple_combined_agent = SimpleCombinedAgent()
