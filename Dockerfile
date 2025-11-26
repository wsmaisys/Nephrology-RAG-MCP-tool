# Use a stable Python version compatible with FAISS + LangChain
FROM python:3.10-slim

# Prevent Python from writing .pyc files and buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Cloud Run expects the app to listen on port 8080
ENV PORT=8080

# Create working directory
WORKDIR /app

# Install system dependencies for FAISS + scientific packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker layer caching)
COPY requirements.txt /app/

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project (including vector store)
COPY . /app/

# Expose expected port
EXPOSE 8080

# Start your MCP server
# Make sure rag_mcp_server.py calls server.run(host="0.0.0.0", port=8080)
CMD ["python", "rag_mcp_server.py"]