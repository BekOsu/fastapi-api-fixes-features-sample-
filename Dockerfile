FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir "fastapi>=0.109.0" "uvicorn[standard]>=0.27.0" "sqlalchemy>=2.0.25" "alembic>=1.13.1" "pydantic>=2.5.0" "pydantic-settings>=2.1.0" "python-jose[cryptography]>=3.3.0" "passlib[bcrypt]>=1.7.4" "python-multipart>=0.0.6" "email-validator>=2.1.0"

# Copy application
COPY alembic.ini .
COPY alembic/ alembic/
COPY app/ app/
COPY scripts/ scripts/

# Create data directory and set permissions
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:8000/ops/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
