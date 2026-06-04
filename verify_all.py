#!/usr/bin/env python3
"""Verify all RAG pipeline components are ready."""

import requests
import subprocess
import sys

def check_kind_cluster():
    print("\n1. Checking Kind Cluster...")
    try:
        result = subprocess.run(["kind", "get", "clusters"], capture_output=True, text=True)
        if "rag-cluster" in result.stdout or result.stdout.strip():
            print(f"   ✓ Kind cluster exists: {result.stdout.strip()}")
            return True
        else:
            print("   ✗ No kind cluster found. Run: kind create cluster --config kind-config.yaml")
            return False
    except FileNotFoundError:
        print("   ✗ Kind not installed")
        return False

def check_kubernetes_pods():
    print("\n2. Checking Kubernetes Pods...")
    try:
        # Check qdrant
        result = subprocess.run(["kubectl", "get", "pods", "-n", "rag-system", "-l", "app=qdrant"],
                                capture_output=True, text=True)
        if "Running" in result.stdout:
            print("   ✓ Qdrant pod is running")
        else:
            print("   ✗ Qdrant not running. Run: kubectl apply -f qdrant.yaml")
            return False

        # Check ollama
        result = subprocess.run(["kubectl", "get", "pods", "-n", "rag-system", "-l", "app=ollama"],
                                capture_output=True, text=True)
        if "Running" in result.stdout:
            print("   ✓ Ollama pod is running")
        else:
            print("   ✗ Ollama not running. Run: kubectl apply -f ollama.yaml")
            return False

        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

def check_qdrant_access():
    print("\n3. Checking Qdrant Access...")
    try:
        response = requests.get("http://localhost:6333/collections", timeout=5)
        if response.status_code == 200:
            print("   ✓ Qdrant is accessible on localhost:6333")
            return True
    except:
        print("   ✗ Qdrant not accessible on localhost:6333")
        print("   → Run: kubectl port-forward -n rag-system svc/qdrant 6333:6333")
        return False

def check_haproxy():
    print("\n4. Checking HAProxy...")
    try:
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("   ✓ HAProxy is accessible on 127.0.0.1:11434")
            return True
    except:
        print("   ✗ HAProxy not accessible")
        print("   → Run: cd haproxy && docker-compose up -d")
        return False

def check_ollama_model():
    print("\n5. Checking Ollama Model...")
    try:
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        models = response.json().get("models", [])
        model_names = [m["name"] for m in models]

        if "tinyllama" in model_names:
            print("   ✓ tinyllama model is available")
            return True
        else:
            print("   ⚠ tinyllama model not found - will be auto-pulled by rag_demo.py")
            return True  # Not a failure, will be auto-pulled
    except:
        return False

def check_python_packages():
    print("\n6. Checking Python Packages...")
    required = ["haystack_ai", "qdrant_haystack", "sentence_transformers", "datasets"]
    missing = []

    for package in required:
        try:
            __import__(package.replace("-", "_"))
            print(f"   ✓ {package}")
        except ImportError:
            missing.append(package)
            print(f"   ✗ {package} - NOT INSTALLED")

    if missing:
        print(f"\n   Install missing packages: pip install {' '.join(missing)}")
        return False
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("RAG Pipeline Verification")
    print("=" * 60)

    checks = [
        check_kind_cluster(),
        check_kubernetes_pods(),
        check_qdrant_access(),
        check_haproxy(),
        check_ollama_model(),
        check_python_packages()
    ]

    print("\n" + "=" * 60)
    if all(checks):
        print("✓ All checks passed! Ready to run: python rag_demo.py")
    else:
        print("✗ Some checks failed. Please fix the issues above.")
    print("=" * 60)