"""Vector and search integrations with explicit, environment-driven opt-in."""
from __future__ import annotations
import os
from typing import Any

class RetrievalStore:
    def __init__(self) -> None:
        self.collection = None
        self.search = None
        self.embedder = None
        if os.getenv("ENABLE_VECTOR_STORE", "false").lower() == "true":
            import chromadb
            self.collection = chromadb.HttpClient(
                host=os.getenv("CHROMA_HOST", "chroma"), port=int(os.getenv("CHROMA_PORT", "8000"))
            ).get_or_create_collection(os.getenv("CHROMA_COLLECTION", "documents"))
            from langchain_ollama import OllamaEmbeddings
            self.embedder = OllamaEmbeddings(
                model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
            )
        if os.getenv("ENABLE_SEARCH_STORE", "false").lower() == "true":
            from opensearchpy import OpenSearch
            self.search = OpenSearch(
                hosts=[os.getenv("SEARCH_URL", "http://opensearch:9200")],
                verify_certs=os.getenv("SEARCH_VERIFY_CERTS", "true").lower() == "true",
            )
            index = os.getenv("SEARCH_INDEX", "rag-documents")
            if not self.search.indices.exists(index=index):
                self.search.indices.create(index=index, body={"mappings": {"properties": {
                    "text": {"type": "text"}, "source": {"type": "keyword"}
                }}})

    def add(self, ids: list[str], documents: list[str], embeddings: list[list[float]] | None = None) -> None:
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

    def query(self, text: str, top_k: int) -> list[dict[str, Any]]:
        if self.collection:
            query_embedding = self.embedder.embed_query(text) if self.embedder else None
            args: dict[str, Any] = {"n_results": top_k}
            if query_embedding:
                args["query_embeddings"] = [query_embedding]
            else:
                args["query_texts"] = [text]
            result = self.collection.query(**args)
            docs = result.get("documents", [[]])[0]
            return [{"text": doc, "index": i, "backend": "chroma"} for i, doc in enumerate(docs)]
        if self.search:
            result = self.search.search(index=os.getenv("SEARCH_INDEX", "rag-documents"),
                                        body={"size": top_k, "query": {"match": {"text": text}}})
            return [{"text": hit["_source"]["text"], "index": i, "backend": "opensearch"}
                    for i, hit in enumerate(result["hits"]["hits"])]
        return []
