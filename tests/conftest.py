"""Explicit, dependency-free test profile before application imports."""
import os

os.environ["RUNTIME_PROFILE"] = "test"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
for name in ("AUDIT_STORE", "KAFKA", "VECTOR_STORE", "SEARCH_STORE", "OLLAMA_INFERENCE"):
    os.environ[f"ENABLE_{name}"] = "false"
