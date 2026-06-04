print("Testing imports...")

try:
    from haystack import Pipeline
    print("✓ Haystack core")
except ImportError as e:
    print(f"✗ Haystack core: {e}")

try:
    from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
    print("✓ qdrant-haystack")
except ImportError as e:
    print(f"✗ qdrant-haystack: {e}")

try:
    from haystack_integrations.components.generators.ollama import OllamaChatGenerator
    print("✓ ollama-haystack")
except ImportError as e:
    print(f"✗ ollama-haystack: {e}")

try:
    from sentence_transformers import SentenceTransformer
    print("✓ sentence-transformers")
except ImportError as e:
    print(f"✗ sentence-transformers: {e}")

print("\nIf any imports failed, run:")
print("pip install qdrant-haystack ollama-haystack sentence-transformers datasets")