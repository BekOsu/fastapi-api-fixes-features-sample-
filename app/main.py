from fastapi import FastAPI

from app.api.routes import auth
from app.core.config import settings
from app.core.error_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import LoggingMiddleware, RequestIDMiddleware

# Configure logging
setup_logging()

app = FastAPI(
    title=settings.app_name,
    description="Task management API with user authentication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Register middleware (order matters - first added is outermost)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIDMiddleware)

# Register exception handlers
register_exception_handlers(app)

# Register routers
app.include_router(auth.router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["ops"])
def health_check():
    return {"status": "healthy"}
