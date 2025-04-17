# AnyDocAI Agent Capabilities

This README provides instructions for testing the agent capabilities in AnyDocAI.

## Prerequisites

1. **OpenAI API Key**: You need a valid OpenAI API key to use the agent capabilities.
   - Get one from [https://platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys)
   - Add it to your `.env` file:
     ```
     OPENAI_API_KEY=your_actual_api_key
     ```

2. **Required Packages**: Make sure you have installed all the required packages:
   ```bash
   pip install langchain langchain-openai llama-index llama-index-embeddings-openai llama-index-llms-openai
   ```

## Testing Options

### Option 1: Test LlamaIndex Directly

This tests the basic LlamaIndex functionality without the agent framework:

```bash
python scripts/test_llama_index_simple.py
```

### Option 2: Test Agent Directly

This tests the basic agent functionality with a simple document search tool:

```bash
python scripts/test_agent_simple.py
```

### Option 3: Test API Endpoints

This tests the API endpoints for the agent capabilities:

1. Start the server:
   ```bash
   uvicorn main:app --reload
   ```

2. Run the test script:
   ```bash
   python scripts/test_api_endpoints.py
   ```

## Agent Types

AnyDocAI supports three types of agents:

1. **Standalone Agent**: A simple agent that doesn't depend on LlamaIndex
   - API Endpoint: `/api/standalone-agent/process`
   - Test Script: `scripts/test_standalone_agent.py`

2. **Simple Combined Agent**: A simplified agent that uses both LangChain and basic file operations
   - API Endpoint: `/api/simple-combined/process`
   - Test Script: `scripts/test_simple_combined.py`

3. **Simple Agent**: A simplified agent for testing
   - Test Script: `scripts/test_agent_simple.py`

## Troubleshooting

If you encounter any issues:

1. **OpenAI API Key**: Make sure your OpenAI API key is valid and has sufficient quota.
2. **Import Errors**: Make sure you have installed all the required packages.
3. **Server Not Running**: Make sure the server is running before testing the API endpoints.
4. **Version Conflicts**: If you encounter version conflicts, try creating a new virtual environment.

## Next Steps

Once you have tested the agent capabilities, you can:

1. **Integrate with Frontend**: Connect the API endpoints to your frontend.
2. **Add More Tools**: Create additional tools for specific tasks.
3. **Enhance Document Processing**: Improve the document processing capabilities.
4. **Add Visualization**: Add visualization capabilities to the agent.
