"""Vector/search integrations with explicit failure and authentication contracts."""
from __future__ import annotations

from collections import OrderedDict
import logging
import os
from typing import Any


log = logging.getLogger(__name__)


def _enabled(name: str) -> bool:
    return os.getenv(name, "false").lower() == "true"


def _positive_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


class RetrievalStore:
    """Use memory only when no persistent retrieval backend was requested."""

    def __init__(self) -> None:
        self.collection = None
        self.search = None
        self.embedder = None
        self.vector_enabled = _enabled("ENABLE_VECTOR_STORE")
        self.search_enabled = _enabled("ENABLE_SEARCH_STORE")
        self.vector_error: str | None = None
        self._documents: OrderedDict[str, str] = OrderedDict()
        self._memory_limit = _positive_int("MEMORY_STORE_MAX_DOCUMENTS", 10_000)

        if self.vector_enabled:
            try:
                import chromadb
                from langchain_ollama import OllamaEmbeddings

                self.collection = chromadb.HttpClient(
                    host=os.getenv("CHROMA_HOST", "chroma"),
                    port=int(os.getenv("CHROMA_PORT", "8000")),
                ).get_or_create_collection(os.getenv("CHROMA_COLLECTION", "documents"))
                self.embedder = OllamaEmbeddings(
                    model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
                    base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
                )
            except Exception as exc:
                self.vector_error = type(exc).__name__
                log.exception("vector_store_initialization_failed error=%s", self.vector_error)
                self._record_failure("vector_store", self.vector_error)

        if self.search_enabled:
            try:
                self.search = self._create_search_client()
                index = os.getenv("SEARCH_INDEX", "rag-documents")
                if not self.search.indices.exists(index=index):
                    self.search.indices.create(index=index, body={"mappings": {"properties": {
                        "text": {"type": "text"}, "source": {"type": "keyword"}
                    }}})
            except Exception as exc:
                log.exception("search_store_initialization_failed error=%s", type(exc).__name__)
                raise RuntimeError("configured search store is unavailable") from exc

    @staticmethod
    def _record_failure(boundary: str, reason: str) -> None:
        try:
            from .metrics import observe_downstream_failure

            observe_downstream_failure(boundary, reason)
        except Exception:
            pass

    def _create_search_client(self):
        from opensearchpy import OpenSearch

        mode = os.getenv("SEARCH_AUTH_MODE", "none").lower()
        url = os.getenv("SEARCH_URL", "http://opensearch:9200")
        options: dict[str, Any] = {
            "hosts": [url],
            "verify_certs": os.getenv("SEARCH_VERIFY_CERTS", "true").lower() == "true",
            "timeout": _positive_int("SEARCH_TIMEOUT_SECONDS", 3),
            "max_retries": _positive_int("SEARCH_MAX_RETRIES", 3),
            "retry_on_timeout": True,
        }
        if mode == "basic":
            username = os.getenv("SEARCH_USERNAME")
            password = os.getenv("SEARCH_PASSWORD")
            if not username or not password:
                raise ValueError("SEARCH_USERNAME and SEARCH_PASSWORD are required for basic auth")
            options["http_auth"] = (username, password)
        elif mode == "aws_sigv4":
            import boto3
            from opensearchpy import AWSV4SignerAuth

            region = os.getenv("AWS_REGION")
            credentials = boto3.Session().get_credentials()
            if not region or credentials is None:
                raise ValueError("AWS_REGION and workload credentials are required for AWS SigV4 search auth")
            options["http_auth"] = AWSV4SignerAuth(credentials, region, "es")
            options["use_ssl"] = True
        elif mode != "none":
            raise ValueError("SEARCH_AUTH_MODE must be none, basic, or aws_sigv4")
        return OpenSearch(**options)

    def _ensure_vector_ready(self) -> None:
        if self.vector_enabled and (self.collection is None or self.embedder is None):
            raise RuntimeError(f"configured vector store is unavailable ({self.vector_error or 'unknown'})")

    def _remember(self, ids: list[str], documents: list[str]) -> None:
        if self.vector_enabled or self.search_enabled:
            return
        for doc_id, document in zip(ids, documents):
            self._documents[doc_id] = document
            self._documents.move_to_end(doc_id)
            while len(self._documents) > self._memory_limit:
                self._documents.popitem(last=False)

    def add(self, ids: list[str], documents: list[str], embeddings: list[list[float]] | None = None) -> None:
        self._ensure_vector_ready()
        self._remember(ids, documents)
        if self.embedder and embeddings is None:
            embeddings = self.embedder.embed_documents(documents)
        if self.collection:
            args: dict[str, Any] = {"ids": ids, "documents": documents}
            if embeddings:
                args["embeddings"] = embeddings
            self.collection.add(**args)
        if self.search:
            index = os.getenv("SEARCH_INDEX", "rag-documents")
            for doc_id, text in zip(ids, documents):
                self.search.index(index=index, id=doc_id, body={"text": text, "source": "ingest"}, refresh=False)

    def remove(self, ids: list[str]) -> None:
        """Compensate a partially completed ingestion after an audit failure."""
        if self.collection:
            self.collection.delete(ids=ids)
        if self.search:
            index = os.getenv("SEARCH_INDEX", "rag-documents")
            for doc_id in ids:
                try:
                    self.search.delete(index=index, id=doc_id, ignore=[404], refresh=False)
                except TypeError:
                    self.search.delete(index=index, id=doc_id, ignore=404, refresh=False)
        for doc_id in ids:
            self._documents.pop(doc_id, None)

    def query(self, text: str, top_k: int) -> list[dict[str, Any]]:
        self._ensure_vector_ready()
        if self.collection:
            query_embedding = self.embedder.embed_query(text) if self.embedder else None
            args: dict[str, Any] = {"n_results": top_k, "include": ["documents", "distances"]}
            if query_embedding:
                args["query_embeddings"] = [query_embedding]
            else:
                args["query_texts"] = [text]
            result = self.collection.query(**args)
            docs = result.get("documents", [[]])[0]
            distances = result.get("distances", [[]])[0]
            return [
                {"text": doc, "index": index, "backend": "chroma", "score": 1.0 - float(distances[index])}
                for index, doc in enumerate(docs)
                if index >= len(distances) or float(distances[index]) < 1.0
            ]
        if self.search:
            result = self.search.search(
                index=os.getenv("SEARCH_INDEX", "rag-documents"),
                body={"size": top_k, "query": {"match": {"text": text}}},
            )
            return [
                {"text": hit["_source"]["text"], "index": index, "backend": "opensearch", "score": hit.get("_score", 0)}
                for index, hit in enumerate(result["hits"]["hits"])
                if float(hit.get("_score") or 0) > 0
            ]
        words = set(text.lower().split())
        scored = [
            (document, len(words.intersection(document.lower().split())))
            for document in self._documents.values()
        ]
        return [
            {"text": document, "index": index, "backend": "memory", "score": score}
            for index, (document, score) in enumerate(sorted(scored, key=lambda entry: entry[1], reverse=True))
            if score > 0
        ][:top_k]
