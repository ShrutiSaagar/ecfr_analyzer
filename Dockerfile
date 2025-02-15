# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# RUN apt-get update && apt-get install -y inetutils-ping telnet iputils-arping dnsutils

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# FROM python:3.12-slim
# Copy application code
COPY . .
# COPY ./config /app/config
# COPY ./data_parser /app/data_parser
# COPY ./db /app/db
# COPY ./ecfr_fetcher /app/ecfr_fetcher
# COPY ./models /app/models
# COPY ./__init__.py /app/__init__.py

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Command to run the job processor
CMD ["python", "/app/data_parser/job_processor.py"]
