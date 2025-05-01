# AnyDocAI Backend

AnyDocAI is an AI document assistant that lets you chat with all your files — PDFs, Word docs, Excel sheets, PowerPoint presentations, Charts, Graphs and text files — all in one place.

## Features

- Upload and process various document types (PDF, DOCX, XLSX, PPTX, TXT)
- Chat with AI about your documents
- Ask questions across multiple files
- Get instant summaries
- Extract key data

## Tech Stack

- **Backend**: Python + FastAPI, Celery
- **AI Models**: OpenAI GPT-4-Turbo, GPT-3.5-Turbo, GPT-4-Vision
- **File Parsing**: PyMuPDF, python-docx, pandas, python-pptx
- **Vector Store**: Weaviate
- **Embeddings**: OpenAI text-embedding-3-small
- **Background Jobs**: Celery + Redis
- **Storage**: Local storage (S3 compatible storage in production)

## Getting Started

### Prerequisites

- Python 3.9+
- Redis (for Celery)
- OpenAI API key
- Weaviate instance (optional for development)

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   ```
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
5. Copy `.env.example` to `.env` and fill in your API keys and configuration

### Running the Application

1. Start Redis (for Celery)
2. Start the Celery worker:
   ```
   celery -A config.celery_worker worker --loglevel=info
   ```
3. Start the FastAPI server:
   ```
   uvicorn main:app --reload
   ```

## API Endpoints

- **POST /api/auth/register**: Register a new user
- **POST /api/auth/login**: Login a user
- **GET /api/auth/me**: Get current user information
- **POST /api/auth/logout**: Logout a user
- **POST /api/files/upload**: Upload a file
- **GET /api/files**: List files for a user
- **GET /api/files/{file_id}**: Get file details
- **POST /api/chat/message**: Send a message to the AI
- **GET /api/chat/sessions**: List chat sessions
- **GET /api/chat/sessions/{session_id}**: Get chat session details
- **GET /api/chat/sessions/{session_id}/messages**: Get messages for a chat session

## Development

### Project Structure

```
/app
  /api
    routes.py         # FastAPI endpoints
    schemas.py        # Pydantic request/response models
  /services
    file_parser.py    # PDF/DOCX/Excel parser logic
    chunker.py        # Splitting files into chunks
    embedder.py       # Embedding logic
    query_engine.py   # Search + prompt builder
  /workers
    tasks.py          # Celery background jobs
    utils.py          # Progress updater, logs
  /models
    db_models.py      # Pydantic models

/config
  config.py           # All keys and settings
  celery_worker.py    # Worker launcher

/scripts
  init_weaviate.py    # Sets up schema, indexes
  test_queries.py     # Quick GPT test script

main.py               # FastAPI entrypoint
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
