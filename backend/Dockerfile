# backend/Dockerfile
FROM python:3.11-slim

# Create and set work directory
WORKDIR /app

# Copy only poetry files to install dependencies first (cache layer)
COPY pyproject.toml poetry.lock /app/

# Install poetry, then install all dependencies (no venv creation inside container)
RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy backend source code into the container
COPY backend/ /app/

# Expose FastAPI port
EXPOSE 8000

# Launch the API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
