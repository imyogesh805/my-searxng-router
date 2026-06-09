FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and static assets
COPY . .

# Expose port (Render sets this dynamically using the $PORT env variable)
EXPOSE 80

# Run FastAPI app with dynamic port fallback
CMD ["sh", "-c", "uvicorn gateway_api:app --host 0.0.0.0 --port ${PORT:-80}"]
