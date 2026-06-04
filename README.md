```markdown
# Task 1: RAG Pipeline with Kubernetes, HAProxy, and Haystack

## TL;DR

```bash
# Deploy everything
kind create cluster --config kind-config.yaml --name rag-cluster
kubectl apply -f qdrant.yaml
kubectl apply -f ollama.yaml
kubectl port-forward -n rag-system svc/qdrant 6333:6333 &
cd haproxy && docker-compose up -d && cd ..
kubectl exec -it -n rag-system deployment/ollama -- ollama pull tinyllama

# Run the pipeline
python rag_demo.py
```

## What It Does

Deploys Qdrant (vector database) and Ollama (LLM) in Kubernetes, exposes Ollama via HAProxy (localhost-only for security), and runs a Haystack RAG pipeline that retrieves documents from Qdrant and generates answers using Ollama.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐
│   Python    │────►│   HAProxy   │────►│   Kind Cluster      │
│   RAG Demo  │     │  :11434     │     │   ┌─────────────┐   │
│  (Haystack) │     │ (localhost  │     │   │  Ollama     │   │
└─────────────┘     │  only)      │     │   │  :32000     │   │
      │            └─────────────┘     │   └─────────────┘   │
      │                                │                     │
      │ (port-forward)                 │   ┌─────────────┐   │
      ▼                                │   │  Qdrant     │   │
┌─────────────┐                         │   │  :6333      │   │
│ localhost:  │                         │   └─────────────┘   │
│ 6333        │                         └─────────────────────┘
└─────────────┘
```

## Prerequisites

| Tool | Version | Installation |
|------|---------|--------------|
| Docker Desktop | 4.25+ | docker.com |
| Kind | 0.20+ | choco install kind |
| kubectl | 1.27+ | choco install kubernetes-cli |
| Python | 3.10+ | python.org |
| uv | Latest | pip install uv |

## Quick Start

### 1. Create Kind Cluster

```bash
kind create cluster --config kind-config.yaml --name rag-cluster
kubectl cluster-info --context kind-rag-cluster
```

### 2. Deploy Qdrant and Ollama

```bash
kubectl apply -f qdrant.yaml
kubectl apply -f ollama.yaml

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=qdrant -n rag-system --timeout=60s
kubectl wait --for=condition=ready pod -l app=ollama -n rag-system --timeout=120s
```

### 3. Port-Forward Qdrant

```bash
# Run this in a separate terminal and keep it open
kubectl port-forward -n rag-system svc/qdrant 6333:6333
```

### 4. Start HAProxy

```bash
cd haproxy
docker-compose up -d
cd ..
```

### 5. Pull the Model

```bash
kubectl exec -it -n rag-system deployment/ollama -- ollama pull tinyllama
```

### 6. Run the Pipeline

```bash
python rag_demo.py
```

## Expected Output

```
============================================================
Haystack RAG Pipeline with Qdrant + Ollama via HAProxy
============================================================

1. Connecting to Qdrant Document Store...
   ✓ Connected to Qdrant

2. Loading documents from Hugging Face...
   ✓ Loaded 151 documents

3. Indexing documents with embeddings...
   ✓ Indexing complete

4. Building Haystack RAG Pipeline...
   ✓ Pipeline ready

5. Testing Haystack RAG Pipeline...
------------------------------------------------------------

Q: What does the Statue of Rhodes look like?
   Running pipeline...
A: The Statue of Rhodes was a giant bronze statue of the sun god Helios,
   standing approximately 33 meters tall at the entrance of Rhodes harbor.

   ✓ Answer generated successfully
----------------------------------------

Q: Where were the Hanging Gardens of Babylon located?
   Running pipeline...
A: The Hanging Gardens of Babylon were located in the ancient city of
   Babylon, near present-day Hillah in Babil Province, Iraq.

   ✓ Answer generated successfully
----------------------------------------

============================================================
✓ Haystack RAG pipeline demonstration complete!
============================================================
```

## Commands Reference

| Operation | Command |
|-----------|---------|
| Create cluster | `kind create cluster --config kind-config.yaml --name rag-cluster` |
| Delete cluster | `kind delete cluster --name rag-cluster` |
| Deploy Qdrant | `kubectl apply -f qdrant.yaml` |
| Deploy Ollama | `kubectl apply -f ollama.yaml` |
| Check pods | `kubectl get pods -n rag-system` |
| Check logs | `kubectl logs -n rag-system deployment/ollama` |
| Port-forward Qdrant | `kubectl port-forward -n rag-system svc/qdrant 6333:6333` |
| Start HAProxy | `cd haproxy && docker-compose up -d` |
| Stop HAProxy | `cd haproxy && docker-compose down` |
| Pull model | `kubectl exec -it -n rag-system deployment/ollama -- ollama pull tinyllama` |
| Test HAProxy | `curl http://127.0.0.1:11434/api/tags` |
| Test Qdrant | `curl http://localhost:6333/collections` |
| Run pipeline | `python rag_demo.py` |

## Security Features

| Component | Binding | External Access | Localhost Access |
|-----------|---------|-----------------|------------------|
| HAProxy | `127.0.0.1:11434` | ❌ Blocked | ✅ Allowed |
| Ollama | NodePort:32000 | ❌ (kind only) | ✅ |
| Qdrant | ClusterIP | ❌ | ✅ (via port-forward) |

HAProxy is bound to localhost only in `haproxy/docker-compose.yml`:

```yaml
ports:
  - "127.0.0.1:11434:11434"  # localhost only!
```

## Troubleshooting

### HAProxy won't start

```bash
cd haproxy
docker-compose down
docker-compose up -d
docker logs haproxy-ollama-proxy
```

### Ollama pod stuck in ContainerCreating

```bash
kubectl describe pod -n rag-system -l app=ollama
# Image pull takes 3-5 minutes (1.5GB)
```

### Qdrant connection refused

```bash
# Ensure port-forward is running in a separate terminal
kubectl port-forward -n rag-system svc/qdrant 6333:6333
```

### Model not found

```bash
kubectl exec -it -n rag-system deployment/ollama -- ollama pull tinyllama
curl http://127.0.0.1:11434/api/tags  # Should show tinyllama
```

### Timeout errors

Increase timeouts in `haproxy/haproxy.cfg`:

```cfg
timeout client 300s
timeout server 300s
```

### Kind not found

```bash
# Download kind.exe
curl -L -o kind.exe https://kind.sigs.k8s.io/dl/v0.31.0/kind-windows-amd64
export PATH="$HOME:$PATH"
```

## File Structure

```
task-1/
├── kind-config.yaml       # Kind cluster with port mappings
├── qdrant.yaml            # Qdrant deployment + PVC + ClusterIP
├── ollama.yaml            # Ollama deployment + PVC + NodePort
├── rag_demo.py            # Haystack RAG pipeline
├── requirements.txt       # Python dependencies
├── haproxy/
│   ├── docker-compose.yml # HAProxy container config
│   └── haproxy.cfg        # HAProxy routing rules
└── README.md              # This file
```

## Cleaning Up

```bash
# Stop HAProxy
cd haproxy && docker-compose down && cd ..

# Delete Kubernetes resources
kubectl delete namespace rag-system

# Delete kind cluster
kind delete cluster --name rag-cluster

# Stop port-forward (press Ctrl+C in that terminal)
```

## Requirements Met (Bonus Task)

- [x] Single-node Kubernetes cluster using kind
- [x] Qdrant deployed inside cluster with PVC
- [x] Ollama deployed inside cluster with NodePort (32000)
- [x] HAProxy on host machine listening on 127.0.0.1:11434 only
- [x] HAProxy forwards to Ollama NodePort
- [x] Haystack uses Qdrant as vector store
- [x] Haystack uses HAProxy endpoint for Ollama
- [x] Documents embedded and stored in Qdrant (151 documents)
- [x] Document retrieval works from Qdrant
- [x] Answer generation works via Ollama through HAProxy

## License

MIT

## Author

MLOps Intern - Task 1 Completion
```