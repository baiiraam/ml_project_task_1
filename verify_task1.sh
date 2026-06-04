#!/bin/bash

echo "=========================================="
echo "Task 1 Bonus Requirements Verification"
echo "=========================================="

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
    else
        echo -e "${RED}✗ $1${NC}"
    fi
}

echo -e "\n1. Kubernetes (Kind) Cluster:"
kubectl get nodes &>/dev/null && check "Kind cluster running" || check "Kind cluster NOT running"

echo -e "\n2. Qdrant in cluster:"
kubectl get pods -n rag-system -l app=qdrant | grep -q Running && check "Qdrant pod running" || check "Qdrant pod NOT running"
kubectl get svc -n rag-system qdrant | grep -q ClusterIP && check "Qdrant ClusterIP service" || check "Qdrant service issue"

echo -e "\n3. Ollama in cluster with NodePort:"
kubectl get pods -n rag-system -l app=ollama | grep -q Running && check "Ollama pod running" || check "Ollama pod NOT running"
kubectl get svc -n rag-system ollama | grep -q NodePort && check "Ollama NodePort service" || check "Ollama service issue"

echo -e "\n4. HAProxy on host:"
docker ps | grep -q haproxy && check "HAProxy container running" || check "HAProxy NOT running"

echo -e "\n5. HAProxy localhost-only binding:"
docker port haproxy-ollama-proxy 2>/dev/null | grep -q "127.0.0.1" && check "HAProxy bound to 127.0.0.1 only" || check "HAProxy binding issue"

echo -e "\n6. Ollama reachable via HAProxy:"
curl -s http://127.0.0.1:11434/api/tags | grep -q tinyllama && check "Ollama accessible via HAProxy" || check "Ollama NOT accessible via HAProxy"

echo -e "\n7. Qdrant collection exists:"
curl -s http://localhost:6333/collections | grep -q seven_wonders && check "Qdrant collection 'seven_wonders' exists" || check "Qdrant collection missing"

echo -e "\n8. Documents indexed in Qdrant:"
POINTS=$(curl -s http://localhost:6333/collections/seven_wonders | grep -o '"points_count":[0-9]*' | cut -d: -f2)
if [ "$POINTS" -eq 151 ]; then
    check "151 documents indexed in Qdrant"
else
    echo -e "${RED}✗ Documents indexed: $POINTS (expected 151)${NC}"
fi

echo -e "\n9. Haystack pipeline test:"
cd ~/Desktop/task_1
uv run -q python -c "
import requests
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
doc_store = QdrantDocumentStore(host='localhost', port=6333, index='seven_wonders', embedding_dim=384)
" 2>/dev/null && check "Haystack Qdrant integration works" || check "Haystack Qdrant integration failed"

echo -e "\n10. End-to-end RAG test:"
ANSWER=$(uv run -q python -c "
import requests
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

qdrant = QdrantClient(host='localhost', port=6333)
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
question = 'What is the Statue of Rhodes?'
embedding = model.encode(question)
results = qdrant.query_points(collection_name='seven_wonders', query=embedding.tolist(), limit=1)
if results.points:
    context = results.points[0].payload.get('text', '')[:200]
    resp = requests.post('http://127.0.0.1:11434/api/generate', 
                        json={'model': 'tinyllama', 'prompt': f'Context: {context}\nQuestion: {question}\nAnswer:', 'stream': False},
                        timeout=60)
    print('success' if resp.status_code == 200 else 'fail')
" 2>/dev/null | grep -q success)
if [ $? -eq 0 ]; then
    check "End-to-end RAG works (retrieval + generation)"
else
    check "End-to-end RAG test failed"
fi

echo -e "\n=========================================="
echo "Verification Complete"
echo "=========================================="
