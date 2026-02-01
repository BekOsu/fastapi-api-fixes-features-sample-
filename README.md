# Task Tracker API

A production-style FastAPI backend for task management with user authentication, demonstrating API fixes, performance improvements, and feature additions.

## Table of Contents

- [Introduction](#introduction)
- [What I Fixed](#what-i-fixed)
- [What I Improved](#what-i-improved)
- [What I Added](#what-i-added)
- [API Endpoints](#api-endpoints)
- [Quick Start](#quick-start)
- [Local Development Setup](#local-development-setup)
- [Docker Usage](#docker-usage)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)

## Introduction

Task Tracker API is a RESTful backend service built with FastAPI that provides comprehensive task management capabilities. The API supports:

- User registration and JWT-based authentication
- Full CRUD operations for tasks
- Task assignment and status transitions with workflow validation
- Filtering, search, and pagination
- Bulk operations for efficient task management

The project follows best practices for production APIs including structured logging, error handling, and metrics collection.

## What I Fixed

### Missing Authentication on Force Delete Endpoint

The `/tasks/{task_id}/force` endpoint was missing authentication, allowing unauthenticated users to delete any task.

**Before (Broken):**
```python
@router.delete(
    "/{task_id}/force",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Force delete a task",
)
def force_delete_task(
    task_id: int,
    db: DBSession,
) -> None:
    """Force delete a task without permission checks."""
    task = task_service.get_task_by_id(db, task_id)
    db.delete(task)
    db.commit()
```

**After (Fixed):**
```python
@router.delete(
    "/{task_id}/force",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Force delete a task",
)
def force_delete_task(
    task_id: int,
    db: DBSession,
    current_user: CurrentUser,  # Added authentication
) -> None:
    """Force delete a task.

    Only the owner or assignee can delete the task.
    """
    task = task_service.get_task_by_id(db, task_id)
    task_service._check_task_permission(task, current_user)  # Added permission check
    db.delete(task)
    db.commit()
```

The fix adds the `CurrentUser` dependency to require authentication and includes a permission check to ensure only the task owner or assignee can perform the deletion.

## What I Improved

### N+1 Query Fix with Eager Loading

The task listing endpoint was suffering from N+1 query problems when loading related user data. For each task returned, separate queries were being executed to fetch the owner and assignee.

**Solution:** Implemented `joinedload` from SQLAlchemy to eagerly load relationships in a single query.

```python
# app/services/task_query_service.py

from sqlalchemy.orm import joinedload

def list_tasks(
    db: Session,
    filters: TaskFilter,
    pagination: PaginationParams,
) -> PaginatedResponse[TaskResponse]:
    """List tasks with filtering, search, and pagination.

    Uses joinedload to eagerly load owner and assignee relationships,
    avoiding N+1 query problems.
    """
    # ... filtering logic ...

    # Apply pagination and ordering with eager loading to avoid N+1
    tasks = (
        query.options(
            joinedload(Task.owner),
            joinedload(Task.assignee),
        )
        .order_by(Task.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.per_page)
        .all()
    )
```

This optimization reduces database queries from `1 + (2 * N)` to just `1` query for listing N tasks with their related users.

### Structured JSON Logging

Implemented production-ready structured logging with JSON output format for better log aggregation and analysis.

```python
# app/core/logging.py

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add contextual fields
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        return json.dumps(log_data)
```

Features:
- JSON-formatted log output for production environments
- Request ID tracking for distributed tracing
- Duration tracking for performance monitoring
- Configurable log format (JSON or standard text for development)

## What I Added

### Bulk Status Update Endpoint

Added a new endpoint for updating the status of multiple tasks in a single request.

**Endpoint:** `POST /api/v1/tasks/bulk-status`

```python
@router.post(
    "/bulk-status",
    response_model=TaskBulkStatusUpdateResponse,
    summary="Bulk update task statuses",
)
def bulk_update_status(
    request: TaskBulkStatusUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> TaskBulkStatusUpdateResponse:
    """Update status of multiple tasks at once.

    Validates:
    - All task IDs exist
    - User has permission for each task
    - All transitions are valid

    Returns detailed results for each task.
    """
    return task_service.bulk_update_status(db, request, current_user)
```

**Request Schema:**
```json
{
  "task_ids": [1, 2, 3],
  "target_status": "in_progress"
}
```

**Response Schema:**
```json
{
  "total": 3,
  "successful": 2,
  "failed": 1,
  "results": [
    {
      "task_id": 1,
      "success": true,
      "previous_status": "todo",
      "new_status": "in_progress"
    },
    {
      "task_id": 2,
      "success": true,
      "previous_status": "todo",
      "new_status": "in_progress"
    },
    {
      "task_id": 3,
      "success": false,
      "error": "Invalid transition from 'done' to 'in_progress'",
      "previous_status": "done"
    }
  ]
}
```

### Metrics Endpoint

Added a simple in-memory metrics collector with an endpoint to retrieve application metrics.

**Endpoint:** `GET /ops/metrics`

```python
# app/core/metrics.py

class MetricsCollector:
    def __init__(self):
        self._lock = Lock()
        self._request_count = 0
        self._status_codes = defaultdict(int)

    def increment_request(self):
        with self._lock:
            self._request_count += 1

    def record_status_code(self, code: int):
        with self._lock:
            self._status_codes[code] += 1

    def get_metrics(self) -> dict:
        with self._lock:
            return {
                "total_requests": self._request_count,
                "status_codes": dict(self._status_codes),
            }
```

**Response Example:**
```json
{
  "total_requests": 1542,
  "status_codes": {
    "200": 1200,
    "201": 150,
    "400": 42,
    "401": 100,
    "404": 50
  }
}
```

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/auth/register` | Register a new user | No |
| POST | `/api/v1/auth/login` | Login with email/password | No |
| POST | `/api/v1/auth/refresh` | Refresh access token | No |
| GET | `/api/v1/auth/me` | Get current user info | Yes |

### Tasks

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/tasks` | List tasks with filtering/pagination | Yes |
| POST | `/api/v1/tasks` | Create a new task | Yes |
| GET | `/api/v1/tasks/{task_id}` | Get task by ID | Yes |
| PATCH | `/api/v1/tasks/{task_id}` | Update a task | Yes |
| DELETE | `/api/v1/tasks/{task_id}` | Delete a task | Yes |
| POST | `/api/v1/tasks/{task_id}/assign` | Assign/unassign a task | Yes |
| POST | `/api/v1/tasks/{task_id}/transition` | Transition task status | Yes |
| POST | `/api/v1/tasks/bulk-status` | Bulk update task statuses | Yes |
| DELETE | `/api/v1/tasks/{task_id}/force` | Force delete a task | Yes |

### Operations

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/ops/health` | Health check | No |
| GET | `/ops/metrics` | Application metrics | No |

## Quick Start

### Register a New User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "full_name": "John Doe"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

### Create a Task

```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "title": "Implement user authentication",
    "description": "Add JWT-based auth with login and register endpoints",
    "priority": "high"
  }'
```

### List Tasks with Filtering

```bash
curl -X GET "http://localhost:8000/api/v1/tasks?status=todo&priority=high&page=1&per_page=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Transition Task Status

```bash
curl -X POST http://localhost:8000/api/v1/tasks/1/transition \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "target_status": "in_progress"
  }'
```

### Bulk Update Task Statuses

```bash
curl -X POST http://localhost:8000/api/v1/tasks/bulk-status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "task_ids": [1, 2, 3],
    "target_status": "in_progress"
  }'
```

## Local Development Setup

### Prerequisites

- Python 3.11 or higher
- pip

### Installation

1. **Clone the repository and navigate to the project directory**

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Seed the database with sample data (optional):**
   ```bash
   python scripts/seed.py
   ```

6. **Start the development server:**
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`. Access the interactive documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./task_tracker.db` |
| `SECRET_KEY` | JWT signing secret | `change-me-in-production` |
| `DEBUG` | Enable debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FORMAT` | Log format (`json` or `standard`) | `json` |

## Docker Usage

### Using Docker Compose

Start the application with Docker Compose:

```bash
docker-compose up -d
```

This will:
- Build the Docker image
- Start the API on port 8000
- Mount a data volume for SQLite persistence
- Configure health checks

### View Logs

```bash
docker-compose logs -f api
```

### Stop the Application

```bash
docker-compose down
```

### Build Image Only

```bash
docker build -t task-tracker-api .
```

### Run Container Directly

```bash
docker run -p 8000:8000 -v ./data:/app/data task-tracker-api
```

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run with Coverage

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

### Run Specific Test Files

```bash
# Run auth tests
pytest tests/test_auth.py -v

# Run task tests
pytest tests/test_tasks.py -v

# Run bulk operation tests
pytest tests/test_bulk.py -v

# Run fix verification tests
pytest tests/test_fixes.py -v
```

## Project Structure

```
fastapi-api-fixes-features-sample/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py             # Dependency injection (auth, db session)
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth.py         # Authentication endpoints
│   │       ├── ops.py          # Health check and metrics endpoints
│   │       └── tasks.py        # Task CRUD endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Application settings
│   │   ├── error_handlers.py   # Exception handlers
│   │   ├── exceptions.py       # Custom exception classes
│   │   ├── jwt.py              # JWT token utilities
│   │   ├── logging.py          # Structured logging configuration
│   │   ├── metrics.py          # Metrics collector
│   │   ├── middleware.py       # Request logging middleware
│   │   └── security.py         # Password hashing utilities
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py             # SQLAlchemy base and mixins
│   │   ├── session.py          # Database session factory
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── task.py         # Task model and enums
│   │       └── user.py         # User model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py           # Shared schemas (pagination, health)
│   │   ├── task.py             # Task request/response schemas
│   │   └── user.py             # User request/response schemas
│   └── services/
│       ├── __init__.py
│       ├── auth_service.py     # Authentication business logic
│       ├── task_query_service.py # Task listing with eager loading
│       ├── task_service.py     # Task CRUD business logic
│       └── user_service.py     # User business logic
├── alembic/
│   ├── env.py                  # Alembic environment configuration
│   ├── script.py.mako          # Migration script template
│   └── versions/               # Database migration files
├── scripts/
│   └── seed.py                 # Database seeding script
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Test fixtures and configuration
│   ├── test_auth.py            # Authentication tests
│   ├── test_bulk.py            # Bulk operations tests
│   ├── test_fixes.py           # Fix verification tests
│   └── test_tasks.py           # Task endpoint tests
├── alembic.ini                 # Alembic configuration
├── docker-compose.yml          # Docker Compose configuration
├── Dockerfile                  # Docker build instructions
├── Makefile                    # Development shortcuts
├── pyproject.toml              # Project dependencies and tools config
└── README.md                   # This file
```

### Key Components

- **`app/api/routes/`**: HTTP endpoint definitions organized by domain
- **`app/core/`**: Cross-cutting concerns (config, auth, logging, middleware)
- **`app/db/`**: Database models and session management
- **`app/schemas/`**: Pydantic models for request/response validation
- **`app/services/`**: Business logic layer separating concerns from routes

## License

This project is provided as a sample implementation for educational purposes.
