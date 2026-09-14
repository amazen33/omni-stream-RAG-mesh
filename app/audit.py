"""Append-only, tamper-evident audit records stored in object-lock storage."""
from __future__ import annotations
import json, os, uuid
from datetime import datetime, timezone
from typing import Any, Dict
import boto3

class AuditSink:
    def __init__(self) -> None:
        self.bucket = os.getenv("AUDIT_BUCKET", "rag-audit")
        self.prefix = os.getenv("AUDIT_PREFIX", "requests")
        self.s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("S3_ENDPOINT_URL") or None,
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

    def write(self, request_id: str, payload: Dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        key = f"{self.prefix}/{now:%Y/%m/%d}/{now:%H%M%S.%fZ}-{request_id}-{uuid.uuid4().hex}.json"
        body = json.dumps({"request_id": request_id, "timestamp": now.isoformat(), **payload},
                          sort_keys=True, separators=(",", ":")).encode()
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=body,
                           ContentType="application/json",
                           ObjectLockMode="COMPLIANCE",
                           ObjectLockRetainUntilDate=now.replace(year=now.year + 7))
        return key
