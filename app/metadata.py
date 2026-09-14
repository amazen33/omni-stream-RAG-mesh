"""Optional Elasticsearch/OpenSearch metadata and audit index adapter."""
from __future__ import annotations
import os
from typing import Any


class MetadataIndex:
    def __init__(self) -> None:
        self.client = None
        if os.getenv("ENABLE_METADATA_INDEX", "false").lower() == "true":
            from elasticsearch import Elasticsearch
            self.client = Elasticsearch(os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200"))
            self.index = os.getenv("ELASTICSEARCH_INDEX", "rag-audit-metadata")

    def put(self, request_id: str, metadata: dict[str, Any]) -> None:
        if self.client:
            self.client.index(index=self.index, id=request_id, document=metadata, op_type="create")
