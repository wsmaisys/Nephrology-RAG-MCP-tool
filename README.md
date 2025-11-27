# Production MCP Server Deployment Guide

## HTTP/SSE Transport for Multi-User Access

This guide covers deploying an enterprise-ready MCP server with HTTP/SSE streaming transport for groups of users.

---

## 🎯 Overview

Your MCP server is configured for:

- ✅ **HTTP/SSE Transport** - Streamable responses over HTTP
- ✅ **Multi-User Support** - Session management for concurrent users
- ✅ **Authentication** - API key-based security
- ✅ **CORS Support** - Cross-origin resource sharing
- ✅ **Production Ready** - Load balancing, auto-scaling, monitoring

---

## 🔧 Quick Start

### 1. Generate API Keys

```bash
# Generate secure MCP API key for authentication
python -c "import secrets; print('MCP_API_KEY=' + secrets.token_urlsafe(32))"

# Save output to .env file
```

### 2. Configure Environment

```bash
# Create .env file
cat > .env << EOF
MISTRALAI_API_KEY=your_mistral_api_key
MCP_API_KEY=your_generated_api_key
HOST=0.0.0.0
PORT=8000
ALLOWED_ORIGINS=*
EOF
```

### 3. Install & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python rag_mcp_server.py
```

Server will start at: `http://0.0.0.0:8000`

---

## 🌐 Client Connection

### For Claude Desktop Users

Distribute this configuration to your users:

```json
{
  "mcpServers": {
    "nephrology-rag": {
      "url": "https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_API_KEY_HERE"
      }
    }
  }
}
```

**File Location:**

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

### For Custom MCP Clients

**HTTP POST Request:**

```bash
curl -X POST https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "query_nephrology_docs",
      "arguments": {
        "query": "chronic kidney disease treatment",
        "k": 4
      }
    }
  }'
```

**With Session Tracking:**

```bash
curl -X POST https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "X-Session-ID: user-123" \
  -H "Accept: text/event-stream" \
  -d '...'
```

### JavaScript/TypeScript Client

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

const transport = new SSEClientTransport(
  new URL("https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp"),
  {
    headers: {
      Authorization: "Bearer YOUR_API_KEY",
      "X-Session-ID": "user-session-123",
    },
  }
);

const client = new Client(
  {
    name: "nephrology-client",
    version: "1.0.0",
  },
  {
    capabilities: {},
  }
);

await client.connect(transport);

// Call tool
const result = await client.callTool({
  name: "query_nephrology_docs",
  arguments: {
    query: "acute kidney injury management",
    k: 4,
  },
});

console.log(result);
```

### Python Client

```python
import requests
import json

API_KEY = "your_mcp_api_key"
SERVER_URL = "https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp"

def query_nephrology(query: str, k: int = 4):
    """Query the nephrology RAG server."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "query_nephrology_docs",
            "arguments": {
                "query": query,
                "k": k
            }
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "text/event-stream"
    }

    response = requests.post(SERVER_URL, json=payload, headers=headers)
    return response.json()

# Usage
result = query_nephrology("What are CKD stages?")
print(json.dumps(result, indent=2))
```

---

## 🚀 Production Deployment Options

### Option 1: Docker Deployment (Recommended)

**Single Server:**

```bash
# Build image
docker build -t nephrology-rag-mcp .

# Run container
docker run -d \
  --name mcp-server \
  -p 8000:8080 \
  -e MISTRALAI_API_KEY="your_key" \
  -e MCP_API_KEY="your_api_key" \
  -e ALLOWED_ORIGINS="https://claude.ai,https://your-app.com" \
  --restart unless-stopped \
  nephrology-rag-mcp

# Check logs
docker logs -f mcp-server
```

**With Docker Compose:**

```bash
# Start all services (server + nginx + monitoring)
docker-compose up -d

# View logs
docker-compose logs -f

# Scale servers
docker-compose up -d --scale mcp-server=3

# Stop
docker-compose down
```

### Option 2: Kubernetes Deployment

**Deploy to Kubernetes cluster:**

```bash
# Create namespace and secrets
kubectl create namespace mcp-server

kubectl create secret generic mcp-secrets \
  --from-literal=mistral-api-key="your_mistral_key" \
  --from-literal=mcp-api-key="your_mcp_key" \
  -n mcp-server

# Deploy
kubectl apply -f kubernetes-deployment.yaml

# Check status
kubectl get pods -n mcp-server
kubectl get svc -n mcp-server

# Get external IP
kubectl get svc mcp-service -n mcp-server -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

**Features:**

- Auto-scaling (2-10 replicas based on CPU/memory)
- Load balancing
- Health checks
- Rolling updates

### Option 3: AWS ECS/Fargate (Terraform)

```bash
cd terraform

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Deploy
terraform apply

# Get ALB endpoint
terraform output alb_dns_name
```

**Features:**

- Fully managed container orchestration
- Auto-scaling with CloudWatch
- Secrets management with AWS Secrets Manager
- Application Load Balancer with SSL
- CloudWatch logs and monitoring

### Option 4: Google Cloud Run

```bash
# Build and deploy
gcloud run deploy nephrology-rag-mcp \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "ALLOWED_ORIGINS=*" \
  --set-secrets "MISTRALAI_API_KEY=mistral-key:latest,MCP_API_KEY=mcp-key:latest" \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --min-instances 1 \
  --max-instances 10 \
  --concurrency 80

# Get service URL
gcloud run services describe nephrology-rag-mcp \
  --region us-central1 \
  --format 'value(status.url)'
```

### Option 5: Azure Container Apps

```bash
# Create resource group
az group create --name mcp-rg --location eastus

# Create container app environment
az containerapp env create \
  --name mcp-env \
  --resource-group mcp-rg \
  --location eastus

# Deploy
az containerapp create \
  --name nephrology-rag-mcp \
  --resource-group mcp-rg \
  --environment mcp-env \
  --image your-registry/nephrology-rag-mcp:latest \
  --target-port 8080 \
  --ingress external \
  --min-replicas 2 \
  --max-replicas 10 \
  --cpu 1 \
  --memory 2Gi \
  --secrets mistral-key=your_key mcp-key=your_api_key \
  --env-vars \
    MISTRALAI_API_KEY=secretref:mistral-key \
    MCP_API_KEY=secretref:mcp-key
```

---

## 🔒 Security Configuration

### 1. Enable Authentication

```bash
# Generate strong API key
export MCP_API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Add to environment
echo "MCP_API_KEY=$MCP_API_KEY" >> .env
```

All clients must include: `Authorization: Bearer YOUR_KEY`

### 2. Configure CORS

**Restrict to specific origins:**

```bash
# Production setting
export ALLOWED_ORIGINS="https://claude.ai,https://your-app.com"
```

**Development (allow all):**

```bash
export ALLOWED_ORIGINS="*"
```

### 3. SSL/TLS with Nginx

```bash
# Generate SSL certificate (Let's Encrypt)
certbot certonly --standalone -d your-domain.com

# Copy certificates
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./ssl/key.pem

# Start Nginx proxy
docker-compose up -d nginx
```

### 4. Rate Limiting

Nginx configuration includes:

- **10 requests/second** per IP
- **Burst of 20** requests
- **Max 10 concurrent connections** per IP

Adjust in `nginx.conf`:

```nginx
limit_req_zone $binary_remote_addr zone=mcp_limit:10m rate=10r/s;
```

---

## 📊 Monitoring & Observability

### Health Check Endpoint

```bash
# Simple health check
curl https://your-server.com/health

# Response
{
  "status": "healthy",
  "service": "nephrology-rag-mcp",
  "version": "1.0.0"
}
```

### Server Info

```bash
# Get server status
curl -X POST https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp \
  -H "Authorization: Bearer YOUR_KEY" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_server_info"
    }
  }'
```

### Session Management

```bash
# List active sessions (admin)
curl -X POST https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp \
  -H "Authorization: Bearer YOUR_KEY" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "list_sessions"
    }
  }'
```

### Prometheus Metrics

Access metrics at: `http://your-server:9090`

**Key metrics to monitor:**

- Request rate
- Response time
- Active sessions
- Error rate
- Memory usage

### Logs

**Docker logs:**

```bash
docker logs -f mcp-server
```

**Kubernetes logs:**

```bash
kubectl logs -f deployment/nephrology-rag-mcp -n mcp-server
```

**Filter for errors:**

```bash
kubectl logs -f deployment/nephrology-rag-mcp -n mcp-server | grep ERROR
```

---

## 🎛️ Configuration Options

### Environment Variables

| Variable            | Required    | Default        | Description                            |
| ------------------- | ----------- | -------------- | -------------------------------------- |
| `MISTRALAI_API_KEY` | Yes         | -              | Mistral API key for embeddings         |
| `MCP_API_KEY`       | Recommended | -              | API key for MCP authentication         |
| `HOST`              | No          | `0.0.0.0`      | Server bind address                    |
| `PORT`              | No          | `8000`         | Server port                            |
| `ALLOWED_ORIGINS`   | No          | `*`            | CORS allowed origins (comma-separated) |
| `VECTOR_STORE_PATH` | No          | `vector_store` | Path to FAISS index                    |

### Client Headers

| Header          | Required | Description                           |
| --------------- | -------- | ------------------------------------- |
| `Authorization` | Yes\*    | Bearer token for authentication       |
| `X-Session-ID`  | No       | Session identifier for tracking       |
| `Accept`        | No       | `text/event-stream` for SSE streaming |

\*Required if `MCP_API_KEY` is set

---

## 🧪 Testing & Validation

### 1. Test Health Endpoint

```bash
curl https://your-server.com/health
```

Expected: `{"status": "healthy", ...}`

### 2. Test Authentication

```bash
# Without auth (should fail if enabled)
curl -X POST https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp -d '{...}'

# With auth (should succeed)
curl -X POST https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp \
  -H "Authorization: Bearer YOUR_KEY" \
  -d '{...}'
```

### 3. Test Query

```bash
curl -X POST https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Accept: text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "query_nephrology_docs",
      "arguments": {
        "query": "test query",
        "k": 2
      }
    }
  }'
```

### 4. Load Testing

```bash
# Install Apache Bench
apt-get install apache2-utils

# Test 1000 requests with 10 concurrent
ab -n 1000 -c 10 \
  -H "Authorization: Bearer YOUR_KEY" \
  -p request.json \
  -T "application/json" \
  https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp
```

---

## 🔧 Troubleshooting

### Issue: "Unauthorized" Error

**Cause:** Missing or invalid API key

**Solution:**

```bash
# Verify API key is set
echo $MCP_API_KEY

# Ensure clients use correct header
Authorization: Bearer YOUR_ACTUAL_KEY
```

### Issue: CORS Errors

**Cause:** Origin not allowed

**Solution:**

```bash
# Update ALLOWED_ORIGINS
export ALLOWED_ORIGINS="https://claude.ai,https://your-domain.com"

# Or allow all (development only)
export ALLOWED_ORIGINS="*"
```

### Issue: "Vector store not initialized"

**Cause:** FAISS index not loaded

**Solution:**

```bash
# Check vector store exists
ls -la vector_store/

# Verify MISTRAL_API_KEY is set
echo $MISTRALAI_API_KEY

# Check server logs
docker logs mcp-server | grep "Vector store"
```

### Issue: Slow Responses

**Possible causes & solutions:**

1. **Too many results:** Reduce `k` parameter
2. **Cold start:** First request may be slower
3. **Resource limits:** Increase container memory/CPU
4. **Network latency:** Deploy closer to users

### Issue: Connection Timeouts

**Solution:**

```nginx
# Increase Nginx timeouts
proxy_connect_timeout 300s;
proxy_send_timeout 300s;
proxy_read_timeout 300s;
```

---

## 📈 Scaling Strategies

### Horizontal Scaling

**Docker Compose:**

```bash
docker-compose up -d --scale mcp-server=5
```

**Kubernetes:**

```bash
kubectl scale deployment nephrology-rag-mcp --replicas=5 -n mcp-server
```

### Vertical Scaling

**Increase resources:**

```yaml
resources:
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### Auto-Scaling

**Kubernetes HPA is configured to:**

- Min replicas: 2
- Max replicas: 10
- Scale at 70% CPU or 80% memory

**AWS ECS:**

- Target tracking on CPU (70%)
- Automatic scaling between 2-10 tasks

---

## 🎯 Best Practices

### 1. Security

- ✅ Always use HTTPS in production
- ✅ Set strong `MCP_API_KEY`
- ✅ Restrict CORS to specific origins
- ✅ Enable rate limiting
- ✅ Use secrets management (not env vars in production)

### 2. Reliability

- ✅ Deploy at least 2 replicas
- ✅ Configure health checks
- ✅ Set up monitoring and alerts
- ✅ Use load balancer
- ✅ Implement circuit breakers

### 3. Performance

- ✅ Cache frequent queries
- ✅ Use CDN for static assets
- ✅ Deploy in multiple regions
- ✅ Optimize vector store index
- ✅ Monitor and optimize query patterns

### 4. Operations

- ✅ Centralized logging
- ✅ Automated deployments
- ✅ Infrastructure as Code
- ✅ Disaster recovery plan
- ✅ Regular security updates

---

## 📚 Additional Resources

- **MCP Specification:** https://spec.modelcontextprotocol.io/
- **FastMCP Docs:** https://github.com/jlowin/fastmcp
- **Claude API:** https://docs.anthropic.com/
- **SSE Protocol:** https://html.spec.whatwg.org/multipage/server-sent-events.html

---

## 💡 Support

For production support:

1. Check server logs
2. Verify configuration
3. Test with curl/httpie
4. Review monitoring dashboards
5. Contact your DevOps team

Server is now ready for multi-user production deployment! 🚀
