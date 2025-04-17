# Agent Capabilities for AnyDocAI

This document explains how to use the agent capabilities in AnyDocAI for multi-step reasoning and tool-using workflows.

## Overview

AnyDocAI's agent capabilities allow for:

1. **Multi-step Reasoning**: Breaking down complex tasks into steps
2. **Tool Usage**: Using specialized tools for different tasks
3. **Data Analysis**: Analyzing data from documents
4. **Visualization**: Creating charts and visualizations
5. **Summarization**: Generating insights and summaries

## Architecture

The agent capabilities consist of the following components:

1. **AgentService**: Core service for processing multi-step requests
2. **Tools**: Specialized tools for different tasks
   - DocumentRetrievalTool: Retrieves information from documents
   - ExcelAnalysisTool: Analyzes Excel files
   - ChartGenerationTool: Creates charts and visualizations
   - SummaryGenerationTool: Generates summaries and insights
3. **FastAPI Endpoints**: API endpoints for agent requests

## Setup

### Installation

Install the required dependencies:

```bash
pip install -r requirements-llamaindex.txt
```

### Configuration

Configure the following settings in `.env`:

```
# OpenAI API Key (required for LLM)
OPENAI_API_KEY=your_openai_api_key
```

## Usage

### Processing Multi-step Requests

```python
from app.services.agent_service import agent_service

# Process a request
result = await agent_service.process_request(
    query="Find the total revenue from Q1_Sales.xlsx, then create a bar chart and summarize the key trends",
    user_id="user_id",
    file_ids=["file_id_1", "file_id_2"]
)

# Access the response
response_text = result["response"]
```

### API Endpoint

```
POST /api/agent/process
```

Parameters:
- `content`: The query text
- `file_ids`: List of file IDs to use
- `session_id`: Optional session ID for conversation context
- `user_id`: ID of the user making the query

## Example Use Cases

### Data Analysis

```
Find the total revenue from the Excel file and compare it to last year's data
```

This will:
1. Retrieve the Excel file
2. Calculate the total revenue
3. Compare it to historical data
4. Generate a summary

### Document Comparison

```
Compare the financial projections in Q1_Report.pdf with the actual results in Q1_Results.xlsx
```

This will:
1. Extract projections from the PDF
2. Extract actual results from the Excel file
3. Compare the two datasets
4. Generate a summary of the comparison

### Research and Summarization

```
Find all mentions of market trends in the annual reports and create a summary with visualizations
```

This will:
1. Search for market trends in the documents
2. Extract relevant information
3. Create visualizations
4. Generate a comprehensive summary

## Advanced Features

### Custom Tools

You can create custom tools for specific tasks:

```python
from langchain.tools import BaseTool

class CustomTool(BaseTool):
    name = "custom_tool"
    description = "Description of what the tool does"
    
    def _run(self, input_data: str) -> str:
        # Implement the tool logic
        return "Result"
```

### Multi-agent Collaboration

For complex workflows, you can create multiple agents that collaborate:

```python
# Create specialized agents
data_analysis_agent = create_agent([excel_analysis_tool, chart_generation_tool])
document_retrieval_agent = create_agent([document_retrieval_tool])

# Orchestrate collaboration
def orchestrate(query):
    # Determine which agent to use
    if "excel" in query.lower() or "data" in query.lower():
        return data_analysis_agent.run(query)
    else:
        return document_retrieval_agent.run(query)
```

## Best Practices

1. **Clear Instructions**: Provide clear, specific instructions to the agent
2. **File Selection**: Specify the relevant files for the task
3. **Step-by-Step Queries**: For complex tasks, break them down into steps
4. **Error Handling**: Handle errors gracefully and provide feedback
5. **Performance Optimization**: For large files, use background processing

## Troubleshooting

Common issues and solutions:

1. **Tool Errors**: Check that the required dependencies are installed
2. **File Access**: Ensure the agent has access to the specified files
3. **Complex Queries**: Break down complex queries into simpler steps
4. **Memory Issues**: For large files, use streaming or chunking
5. **Timeout Issues**: Increase timeout settings for complex tasks
