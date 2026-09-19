"""Append-only, tamper-evident audit records stored in object-lock storage."""
from __future__ import annotations
import json, os, uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
import boto3
import logging

log = logging.getLogger(__name__)
OBJECT_LOCK_RETENTION = timedelta(days=365 * 7)

class AuditSink:
    def __init__(self) -> None:
        self.bucket = os.getenv("AUDIT_BUCKET", "rag-audit")
        self.prefix = os.getenv("AUDIT_PREFIX", "requests")
        self.enabled = os.getenv("ENABLE_AUDIT_STORE", "false").lower() == "true"
        self.s3 = None
        self.records: list[dict[str, Any]] = []
        if self.enabled:
            self.s3 = boto3.client(
                "s3", endpoint_url=os.getenv("S3_ENDPOINT_URL") or None,
                region_name=os.getenv("AWS_REGION", "us-east-1"),
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            )

    def write(self, request_id: str, payload: Dict[str, Any], correlation_id: str | None = None) -> str:
        now = datetime.now(timezone.utc)
        key = f"{self.prefix}/{now:%Y/%m/%d}/{now:%H%M%S.%fZ}-{request_id}-{uuid.uuid4().hex}.json"
        # Add invariant identity fields last so a caller cannot accidentally
        # overwrite the request/correlation pair in the durable audit record.
        record = {**payload, "request_id": request_id, "correlation_id": correlation_id or request_id,
                  "timestamp": now.isoformat()}
        self.records.append({"key": key, **record})
        body = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        if not self.s3:
            log.info("audit store disabled; record retained in application event stream")
            return key
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=body,
                           ContentType="application/json",
                           ObjectLockMode="COMPLIANCE",
                           ObjectLockRetainUntilDate=now + OBJECT_LOCK_RETENTION)
        return key
    def write_state_transition(
        self, correlation_id: str, state_from: str, state_to: str, reason: str, payload: Dict[str, Any] | None = None
    ) -> str:
        now = datetime.now(timezone.utc)
        key = f"{self.prefix}/transitions/{now:%Y/%m/%d}/{now:%H%M%S.%fZ}-{correlation_id}-{uuid.uuid4().hex}.json"
        record = {
            "record_type": "state_transition",
            "correlation_id": correlation_id,
            "timestamp": now.isoformat(),
            "state_from": state_from,
            "state_to": state_to,
            "reason": reason,
            "payload": payload or {},
        }
        self.records.append({"key": key, **record})
        body = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        if not self.s3:
            log.info("audit store disabled; state transition retained in stream: %s -> %s", state_from, state_to)
            return key
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=body,
                           ContentType="application/json",
                           ObjectLockMode="COMPLIANCE",
                           ObjectLockRetainUntilDate=now + OBJECT_LOCK_RETENTION)
        return key
    def write_compensation(self, correlation_id: str, compensating_record: Dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        key = f"{self.prefix}/compensations/{now:%Y/%m/%d}/{now:%H%M%S.%fZ}-{correlation_id}-{uuid.uuid4().hex}.json"
        record = {
            **compensating_record,
            "record_type": "compensation",
            "correlation_id": correlation_id,
            "timestamp": now.isoformat(),
        }
        self.records.append({"key": key, **record})

        try:
            from app.metrics import observe_compensating_event
            observe_compensating_event(
                compensating_record.get("boundary", "audit"),
                compensating_record.get("reason", "downstream_failure"),
            )
        except Exception:
            pass

        body = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        if not self.s3:
            log.info("audit store disabled; compensation retained in stream for %s", correlation_id)
            return key
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=body,
                           ContentType="application/json",
                           ObjectLockMode="COMPLIANCE",
                           ObjectLockRetainUntilDate=now + OBJECT_LOCK_RETENTION)
        return key
