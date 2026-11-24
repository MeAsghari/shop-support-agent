FROM python:3.12-slim

# No .pyc files, and logs appear immediately
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install the project and its dependencies
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

# Files for database setup and the knowledge documents
COPY alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts
COPY docs/knowledge ./docs/knowledge

# Run as a normal user, not as root
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "third_agent.api.app:app", "--host", "0.0.0.0", "--port", "8000"]