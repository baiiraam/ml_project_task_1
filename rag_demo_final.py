#!/usr/bin/env python3
"""Final RAG Pipeline with Qdrant + Ollama via HAProxy"""

import requests
import json
import time
from datasets import load_dataset
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

print("=" * 60)
print("RAG Pipeline with Qdrant + Ollama via HAProxy")
print("=" * 60)

def ensure_ollama_model(model_name="tinyllama"):
    """Check if model exists, pull if not."""
    print(f"\nChecking if model '{model_name}' is available...")

    try:
        # Check existing models
        resp = requests.get("http://127.0.0.1:11434/api/tags", timeout=10)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        existing_models = [m["name"].split(":")[0] for m in models]

        if model_name in existing_models or f"{model_name}:latest" in [m["name"] for m in models]:
            print(f"   ✓ Model '{model_name}' already exists")
            return True

        print(f"   Model not found. Pulling '{model_name}'...")
        resp = requests.post(
            "http://127.0.0.1:11434/api/pull",
            json={"name": model_name},
            stream=True,
            timeout=300
        )
        resp.raise_for_status()

        for line in resp.iter_lines():
            if line:
                data = json.loads(line)
                if "status" in data:
                    print(f"   {data['status']}")
                if "error" in data:
                    print(f"   ✗ Error: {data['error']}")
                    return False

        print(f"   ✓ Model '{model_name}' pulled successfully")
        return True

    except Exception as e:
        print(f"   ✗ Error checking model: {e}")
        return False

# 1. Connect to Qdrant
print("\n1. Connecting to Qdrant...")
qdrant = QdrantClient(host="localhost", port=6333)
print("   ✓ Connected to Qdrant")

# 2. Create collection
collection_name = "seven_wonders"

if qdrant.collection_exists(collection_name):
    qdrant.delete_collection(collection_name)
    print(f"   Deleted existing collection: {collection_name}")

qdrant.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)
print(f"   ✓ Created collection: {collection_name}")

# 3. Load documents
print("\n2. Loading documents...")
dataset = load_dataset("bilgeyucel/seven-wonders", split="train")
docs = [doc["content"] for doc in dataset]
print(f"   ✓ Loaded {len(docs)} documents")

# 4. Create embeddings and store in Qdrant
print("\n3. Creating embeddings and storing in Qdrant...")
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

points = []
for i, doc in enumerate(docs):
    embedding = model.encode(doc)
    points.append(PointStruct(id=i, vector=embedding.tolist(), payload={"text": doc}))

qdrant.upsert(collection_name=collection_name, points=points)
print(f"   ✓ Stored {len(points)} vectors in Qdrant")

# 5. Ensure model is available
if not ensure_ollama_model("tinyllama"):
    print("Failed to ensure model is available. Exiting.")
    exit(1)

# 6. Test queries
print("\n4. Testing RAG queries...")
print("-" * 60)

def query_rag(question):
    print(f"\nQ: {question}")

    # Embed question
    q_embedding = model.encode(question)

    # Search in Qdrant
    search_result = qdrant.query_points(
        collection_name=collection_name,
        query=q_embedding.tolist(),
        limit=2
    ).points

    print(f"   ✓ Retrieved {len(search_result)} documents")

    # Build context from retrieved documents
    if search_result:
        context_parts = []
        for hit in search_result:
            if hit.payload:
                text = hit.payload.get("text", "")
                context_parts.append(text[:1000])
        context = "\n---\n".join(context_parts)
    else:
        context = "No relevant documents found."

    # Prompt
    prompt = f"""Based on the following context, answer the question concisely in 1-2 sentences.

Context:
{context[:1500]}

Question: {question}

Answer:"""

    print(f"   Calling Ollama via HAProxy (this may take 10-20 seconds)...")

    payload = {"model": "tinyllama", "prompt": prompt, "stream": False}

    try:
        response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json=payload,
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            answer = result.get("response", "No response").strip()
        else:
            answer = f"HTTP Error: {response.status_code}"

    except requests.Timeout:
        answer = "Timeout: Ollama took too long to respond"
    except Exception as e:
        answer = f"Exception: {str(e)}"

    print(f"A: {answer[:400]}")
    print("-" * 40)

# Run tests
test_questions = [
    "What does the Statue of Rhodes look like?",
    "Where were the Hanging Gardens of Babylon located?",
]

for q in test_questions:
    query_rag(q)

print("\n" + "=" * 60)
print("✓ RAG pipeline demonstration complete!")
print("=" * 60)