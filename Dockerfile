# Use a stable Python version compatible with FAISS + LangChain
FROM python:3.10-slim

# Prevent Python from writing .pyc files and buffering immediately
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create working directory
WORKDIR /app

# Install system dependencies for FAISS + scientific packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker layer caching)
COPY requirements.txt /app/

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project (including vector store)
COPY . /app/

# Expose expected port (8000 hardcoded in server)
EXPOSE 8000

# Health check - ensure container stays healthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start your MCP server
# Server is hardcoded to listen on 0.0.0.0:8000
CMD ["python", "rag_mcp_server.py"]