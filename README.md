# RAG Pipeline with k8s, HAProxy, and Haystack

## TLDR

```bash
# Deploy everything
kind create cluster --config kind-config.yaml --name rag-cluster
kubectl apply -f qdrant.yaml
kubectl apply -f ollama.yaml
kubectl port-forward -n rag-system svc/qdrant 6333:6333 &
cd haproxy && docker-compose up -d && cd ..
kubectl exec -it -n rag-system deployment/ollama -- ollama pull tinyllama

# Verify deployment and run pipeline
./verify_task1.sh && python rag_demo.py
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
      │             └─────────────┘     │   └─────────────┘   │
      │                                 │                     │
      │ (port-forward)                  │   ┌─────────────┐   │
      ▼                                 │   │  Qdrant     │   │
┌─────────────┐                         │   │  :6333      │   │
│ localhost:  │                         │   └─────────────┘   │
│ 6333        │                         └─────────────────────┘
└─────────────┘
```

## Prerequisites

| Tool | Version | Check Command | Notes |
|------|---------|---------------|-------|
| Docker Desktop | 28.3.2+ | `docker --version` | Required to run containers |
| Kind CLI | 0.31.0+ | `kind version` | Manages Kind clusters |
| kubectl | 1.32.2+ | `kubectl version --client` | Kubernetes CLI |
| Python | 3.12.9+ | `python --version` | Runs the RAG pipeline |

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
| Run verification | `./verify_task1.sh` |

## Security Features

| Component | Binding | External Access | Localhost Access |
|-----------|---------|-----------------|------------------|
| HAProxy | `127.0.0.1:11434` | Blocked | Allowed |
| Ollama | NodePort:32000 | (kind only) | Allowed |
| Qdrant | ClusterIP | Not Allowed | via port-forward |

HAProxy is bound to localhost only in `haproxy/docker-compose.yml`:

```yaml
ports:
  - "127.0.0.1:11434:11434"  # localhost only!
```

## Verification

Run the verification script to ensure all components are working correctly:

```bash
# Make the script executable
chmod +x verify_task1.sh

# Run verification
./verify_task1.sh
```

### Expected Verification Output

```
==========================================
Task 1 Bonus Requirements Verification
==========================================

1. Kubernetes (Kind) Cluster:
✓ Kind cluster running

2. Qdrant in cluster:
✓ Qdrant pod running
✓ Qdrant ClusterIP service

3. Ollama in cluster with NodePort:
✓ Ollama pod running
✓ Ollama NodePort service

4. HAProxy on host:
✓ HAProxy container running

5. HAProxy localhost-only binding:
✓ HAProxy bound to 127.0.0.1 only

6. Ollama reachable via HAProxy:
✓ Ollama accessible via HAProxy

7. Qdrant collection exists:
✓ Qdrant collection 'seven_wonders' exists

8. Documents indexed in Qdrant:
✓ 151 documents indexed in Qdrant

9. Haystack pipeline test:
✓ Haystack Qdrant integration works

10. End-to-end RAG test:
✓ End-to-end RAG works (retrieval + generation)

==========================================
Verification Complete
==========================================
```

The script checks all 10 bonus task requirements and provides a clear pass/fail status for each.

## File Structure

```
task-1/
├── kind-config.yaml       # Kind cluster with port mappings
├── qdrant.yaml            # Qdrant deployment + PVC + ClusterIP
├── ollama.yaml            # Ollama deployment + PVC + NodePort
├── rag_demo.py            # Haystack RAG pipeline
├── verify_task1.sh        # 10-point verification script
├── requirements.txt       # Python dependencies
├── haproxy/
│   ├── docker-compose.yml # HAProxy container config
│   └── haproxy.cfg        # HAProxy routing rules
└── README.md              # This file
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
