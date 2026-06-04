import requests
import json
from datasets import load_dataset
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

print("=" * 60)
print("RAG Pipeline with Qdrant + Ollama via HAProxy")
print("=" * 60)

# 1. Connect to Qdrant
print("\n1. Connecting to Qdrant...")
qdrant = QdrantClient(host="localhost", port=6333)
print("   Connected to Qdrant")

# 2. Create collection
collection_name = "seven_wonders"

if qdrant.collection_exists(collection_name):
    qdrant.delete_collection(collection_name)
    print(f"   Deleted existing collection: {collection_name}")

qdrant.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)
print(f"   Created collection: {collection_name}")

# 3. Load documents
print("\n2. Loading documents...")
dataset = load_dataset("bilgeyucel/seven-wonders", split="train")
docs = [doc["content"] for doc in dataset]
print(f"   Loaded {len(docs)} documents")

# 4. Create embeddings and store in Qdrant
print("\n3. Creating embeddings and storing in Qdrant...")
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

points = []
for i, doc in enumerate(docs):
    embedding = model.encode(doc)
    points.append(PointStruct(id=i, vector=embedding.tolist(), payload={"text": doc}))

    if (i + 1) % 50 == 0:
        print(f"   Processed {i + 1}/{len(docs)} documents")

qdrant.upsert(collection_name=collection_name, points=points)
print(f"   Stored {len(points)} vectors in Qdrant")

# 5. Test queries
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

    print(f"   Retrieved {len(search_result)} documents")

    # Build context from retrieved documents
    if search_result:
        context_parts = []
        for hit in search_result:
            if hasattr(hit, 'payload') and hit.payload:
                text = hit.payload.get("text", "")
                # Take first 800 characters from each document
                context_parts.append(text[:800])
        context = "\n---\n".join(context_parts)
    else:
        context = "No relevant documents found."

    # Simple prompt
    prompt = f"""Context: {context[:2000]}

Question: {question}

Answer based only on the context above. If you don't know, say "I don't know".

Answer:"""

    print(f"   Calling Ollama via HAProxy...")

    # Call Ollama with the same format that worked in curl
    payload = {
        "model": "tinyllama",
        "prompt": prompt,
        "stream": False
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps(payload),
            headers=headers,
            timeout=120
        )

        print(f"   Response status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            answer = result.get("response", "No response")
        else:
            answer = f"HTTP Error: {response.status_code} - {response.text[:100]}"

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
print("✅ RAG pipeline demonstration complete!")
print("=" * 60)