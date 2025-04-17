# Standalone Agent for AnyDocAI

This document explains how to use the standalone agent capabilities in AnyDocAI.

## Overview

The standalone agent provides multi-step reasoning capabilities without any external dependencies beyond LangChain. It can:

1. **Analyze Queries**: Break down complex queries into steps
2. **Read Documents**: Read text files directly
3. **Generate Responses**: Create comprehensive responses based on document contents

## Setup

### Installation

Install the standalone dependencies:

```bash
python scripts/install_standalone_deps.py
```

This will install:
- langchain
- langchain-openai

### Configuration

Configure the following settings in `.env`:

```
# OpenAI API Key (required for LLM)
OPENAI_API_KEY=your_openai_api_key
```

## Usage

### Processing Multi-step Requests

```python
from app.services.standalone_agent_service import standalone_agent_service

# Process a request
result = await standalone_agent_service.process_request(
    query="What was the total revenue in 2023?",
    user_id="user_id",
    file_ids=["file_id_1", "file_id_2"]
)

# Access the response
response_text = result["response"]
analysis = result["steps"]["analysis"]
document_contents = result["steps"]["document_contents"]
```

### API Endpoint

```
POST /api/standalone-agent/process
```

Parameters:
- `content`: The query text
- `file_ids`: List of file IDs to use
- `session_id`: Optional session ID for conversation context
- `user_id`: ID of the user making the query

## Example Use Cases

### Document Analysis

```
What was the total revenue in 2023?
```

This will:
1. Analyze the query to determine it's about revenue in 2023
2. Read the document contents
3. Generate a response with the total revenue

### Comparative Analysis

```
Compare the revenue and expenses for each quarter
```

This will:
1. Analyze the query to determine it's about comparing revenue and expenses
2. Read the document contents
3. Generate a response that compares the values

### Trend Analysis

```
What was the profit trend throughout the year?
```

This will:
1. Analyze the query to determine it's about profit trends
2. Read the document contents
3. Generate a response that describes the trend

## Testing

Run the test script to verify the standalone agent works:

```bash
python scripts/test_standalone_agent.py
```

This will:
1. Create a test text file with financial data
2. Run several test queries
3. Display the responses and analysis

## Extending the Agent

You can extend the standalone agent by:

1. **Adding More Steps**: Add additional steps to the `process_request` method
2. **Supporting More File Types**: Extend the `DocumentReader` class to support more file types
3. **Enhancing Analysis**: Improve the query analysis capabilities

## Future Enhancements

Once you have the full dependencies installed, you can:

1. **Add LlamaIndex Integration**: Use LlamaIndex for more advanced document processing
2. **Add Data Analysis**: Analyze Excel files and other data sources
3. **Create Visualizations**: Generate charts and graphs
