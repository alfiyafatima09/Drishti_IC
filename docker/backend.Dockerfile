# Backend Dockerfile for Drishti IC Verification System
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY models/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend /app/backend
COPY models /app/models

# Create necessary directories
RUN mkdir -p /app/logs /app/cache /app/data

# Expose port
EXPOSE 8000

# Set working directory to backend
WORKDIR /app/backend

# Run migrations and start server
CMD python -c "from models.database import init_database; init_database()" && \
    uvicorn core.app:app --host 0.0.0.0 --port 8000
