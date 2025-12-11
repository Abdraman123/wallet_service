FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy all project files (needed because pyproject.toml references README.md)
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

EXPOSE 8000

# Run migrations and start uvicorn
CMD sh -c 'alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT'
