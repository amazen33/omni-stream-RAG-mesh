"""Catch installed adapters that cannot import on the supported Python runtime."""
import importlib

import pytest


@pytest.mark.parametrize("module", ["kafka", "chromadb", "langchain_ollama", "opensearchpy", "elasticsearch", "azure.storage.blob", "google.cloud.storage"])
def test_optional_adapter_import(module):
    importlib.import_module(module)
