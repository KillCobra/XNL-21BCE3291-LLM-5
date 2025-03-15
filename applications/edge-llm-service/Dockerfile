FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV MODEL_PATH=/models/tflite_model
ENV USE_TFLITE=true
ENV LOG_LEVEL=info

# Expose the application port
EXPOSE 8080

# Run the application
CMD ["python", "app.py"] 