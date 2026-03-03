# ALINE AI Document Processing System (OpenAI-Only Version)

This is a robust document processing system that uses OpenAI-compatible APIs for document classification, extraction, and routing. This version has been optimized to use only OpenAI-compatible APIs and removes all Ollama dependencies.

## Features

- **Document Classification**: Automatically categorizes documents into predefined types
- **Information Extraction**: Extracts structured data from documents
- **File Watching**: Monitors specified directories for new documents
- **Background Processing**: Asynchronous task processing with Celery
- **Web Interface**: Frontend for managing documents and viewing results

## Architecture

The system consists of multiple services:

- **Backend**: FastAPI application for API endpoints
- **Worker**: Celery workers for background tasks
- **Watcher**: File system watcher for new documents
- **PostgreSQL**: Database for storing metadata
- **Redis**: Message broker for Celery
- **Frontend**: Web interface

## Prerequisites

- Docker and Docker Compose
- OpenAI API key (or compatible API key)
- Windows or Linux system with sufficient storage for documents

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd aline_ai_mvp_windows_lan
```

2. Copy the example environment file:
```bash
cp .env.example .env
```

3. Edit the `.env` file to include your OpenAI API key:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

4. Customize other environment variables as needed:
   - `WATCH_PATH`: Directory to watch for new documents (default: `C:\AlineInbox`)
   - `FILE_STORAGE_ROOT`: Directory to store processed documents (default: `C:\AlineStorage`)
   - `WEB_PORT`: Port for the web interface (default: 9876)

## Running the Application

Start all services with Docker Compose:

```bash
docker-compose up --build
```

The application will be available at `http://localhost:9876`

## Configuration Options

### OpenAI Compatible API Settings (DashScope)
- `OPENAI_API_KEY`: Your DashScope API key (example: `sk-sp-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
- `OPENAI_BASE_URL`: API endpoint (default: `https://coding.dashscope.aliyuncs.com/v1`)
- `MODEL_NAME`: Model to use (default: `qwen3-coder-plus`)

### Application Settings
- `REQUEST_TIMEOUT`: API request timeout in seconds (default: 60)
- `MAX_FILE_SIZE`: Maximum file size in MB (default: 50)
- `LOG_LEVEL`: Logging level (default: INFO)

### Security Settings
- `SECURE_COOKIES`: Enable secure cookies (default: true)
- `MAX_LOGIN_ATTEMPTS`: Max login attempts before lockout (default: 5)
- `LOGIN_LOCKOUT_TIME`: Lockout duration in seconds (default: 300)

## Services

### Backend
- Runs on port 8000 internally
- Provides REST API for document processing
- Handles authentication and database operations

### Worker
- Processes background tasks using Celery
- Performs document classification and extraction
- Communicates with OpenAI API

### Watcher
- Monitors the `WATCH_PATH` directory for new files
- Creates database records for new documents
- Triggers processing workflows

### Frontend
- Web interface for managing documents
- Runs on port specified by `WEB_PORT` (default: 9876)

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure your `OPENAI_API_KEY` is correctly set in the `.env` file
2. **Database Connection**: Check that PostgreSQL is running and accessible
3. **File Permissions**: Ensure the application has read/write access to the watch and storage directories

### Logs
Check service logs with:
```bash
docker-compose logs -f <service-name>
```

## Development

To run individual services during development:

```bash
# Start only the database and Redis
docker-compose up postgres redis

# Run backend in development mode
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Security

- All API keys are stored in environment variables
- JWT tokens are used for authentication
- Rate limiting and login attempt tracking are implemented
- Secure cookie settings are configurable

## Performance

- Document processing is handled asynchronously
- API calls include retry logic with exponential backoff
- Database connections are pooled
- File watching is optimized for performance

## Updating

To update to the latest version:

```bash
git pull
docker-compose down
docker-compose up --build
```

## Support

For issues or questions, please check the logs and ensure your OpenAI API key is valid and has sufficient quota.