# frontend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy Poetry files at build time to install dependencies
COPY pyproject.toml poetry.lock /app/

RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy Streamlit app code
COPY frontend/ /app/

# Expose Streamlit port
EXPOSE 8501

# Launch Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
