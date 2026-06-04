#!/usr/bin/env python3
"""Haystack RAG Pipeline with Qdrant + Ollama via HAProxy"""

import json
import requests
from datasets import load_dataset
from typing import List

from haystack import Pipeline, component
from haystack.dataclasses import Document
from haystack.components.builders import PromptBuilder
from haystack.components.embedders import (
    SentenceTransformersDocumentEmbedder,
    SentenceTransformersTextEmbedder,
)
from haystack.components.writers import DocumentWriter

# For Qdrant - correct imports
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever

print("=" * 60)
print("Haystack RAG Pipeline with Qdrant + Ollama via HAProxy")
print("=" * 60)


# Function to check/pull Ollama model
def ensure_ollama_model(model_name="tinyllama"):
    """Check if model exists, pull if not."""
    print(f"\nChecking if model '{model_name}' is available...")

    try:
        resp = requests.get("http://127.0.0.1:11434/api/tags", timeout=10)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        existing_models = [m["name"].split(":")[0] for m in models]

        if model_name in existing_models:
            print(f"   ✓ Model '{model_name}' already exists")
            return True

        print(f"   Model not found. Pulling '{model_name}'...")
        resp = requests.post(
            "http://127.0.0.1:11434/api/pull",
            json={"name": model_name},
            stream=True,
            timeout=300,
        )
        resp.raise_for_status()

        for line in resp.iter_lines():
            if line:
                data = json.loads(line)
                if "status" in data:
                    print(f"   {data['status']}")

        print(f"   ✓ Model '{model_name}' pulled successfully")
        return True

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


# 1. Initialize Qdrant Document Store
print("\n1. Connecting to Qdrant Document Store...")
document_store = QdrantDocumentStore(
    host="localhost",
    port=6333,
    index="seven_wonders",
    embedding_dim=384,
    recreate_index=True,
)
print("   ✓ Connected to Qdrant")

# 2. Load Documents
print("\n2. Loading documents from Hugging Face...")
dataset = load_dataset("bilgeyucel/seven-wonders", split="train")
haystack_docs = [Document(content=doc["content"]) for doc in dataset]
print(f"   ✓ Loaded {len(haystack_docs)} documents")

# 3. Index Documents with Embeddings
print("\n3. Indexing documents with embeddings...")
indexing_pipeline = Pipeline()
indexing_pipeline.add_component(
    "embedder",
    SentenceTransformersDocumentEmbedder(
        model="sentence-transformers/all-MiniLM-L6-v2"
    ),
)
indexing_pipeline.add_component("writer", DocumentWriter(document_store=document_store))
indexing_pipeline.connect("embedder.documents", "writer.documents")
indexing_pipeline.run({"embedder": {"documents": haystack_docs}})
print("   ✓ Indexing complete")

# 4. Ensure model is available
if not ensure_ollama_model("tinyllama"):
    print("Failed to ensure model is available. Exiting.")
    exit(1)


# 5. Create a Haystack component for Ollama
@component
class OllamaGenerator:
    """Haystack component for Ollama API through HAProxy."""

    def __init__(self, model: str = "tinyllama", url: str = "http://127.0.0.1:11434"):
        self.model = model
        self.url = url

    @component.output_types(replies=List[str])
    def run(self, prompt: str):
        """Generate response from Ollama."""
        payload = {"model": self.model, "prompt": prompt, "stream": False}

        try:
            response = requests.post(
                f"{self.url}/api/generate", json=payload, timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                answer = result.get("response", "No response")
            else:
                answer = f"Error: {response.status_code}"
        except Exception as e:
            answer = f"Exception: {str(e)}"

        return {"replies": [answer]}


# 6. Build the Prompt Template
prompt_template = """
Given the following context, answer the question truthfully and concisely.

Context:
{% for doc in documents %}
    {{ doc.content }}
{% endfor %}

Question: {{ query }}
Answer:
"""

# 7. Build RAG Pipeline
print("\n4. Building Haystack RAG Pipeline...")
rag_pipeline = Pipeline()

# Add components
rag_pipeline.add_component(
    "text_embedder",
    SentenceTransformersTextEmbedder(model="sentence-transformers/all-MiniLM-L6-v2"),
)
rag_pipeline.add_component(
    "retriever", QdrantEmbeddingRetriever(document_store=document_store, top_k=2)
)
rag_pipeline.add_component("prompt_builder", PromptBuilder(template=prompt_template))
rag_pipeline.add_component(
    "llm", OllamaGenerator(model="tinyllama", url="http://127.0.0.1:11434")
)

# Connect components
rag_pipeline.connect("text_embedder.embedding", "retriever.query_embedding")
rag_pipeline.connect("retriever.documents", "prompt_builder.documents")
rag_pipeline.connect("prompt_builder.prompt", "llm.prompt")

print("   ✓ Pipeline ready")

# 8. Test Queries
print("\n5. Testing Haystack RAG Pipeline...")
print("-" * 60)

test_questions = [
    "What does the Statue of Rhodes look like?",
    "Where were the Hanging Gardens of Babylon located?",
]

for question in test_questions:
    print(f"\nQ: {question}")
    print("   Running pipeline...")

    try:
        results = rag_pipeline.run(
            {
                "text_embedder": {"text": question},
                "prompt_builder": {"query": question},
            }
        )

        # FIXED: Access results correctly
        answer = results["llm"]["replies"][0]
        print(f"A: {answer}")

        # The retriever results are already in the prompt_builder
        # To show retrieval stats, we can print a message
        print("   ✓ Answer generated successfully")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

    print("-" * 40)

print("\n" + "=" * 60)
print("✓ Haystack RAG pipeline demonstration complete!")
print("=" * 60)
