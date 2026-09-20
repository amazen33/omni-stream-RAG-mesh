"""Append-only audit records with bounded storage and immutable backends."""
from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from typing import Any, Dict
import uuid

import boto3
from botocore.config import Config
from .redaction import sanitize_for_boundary


log = logging.getLogger(__name__)


def _positive_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except ValueError:
        return default


class AuditSink:
    """Write canonical sanitized audit records without unbounded local copies."""

    def __init__(self) -> None:
        self.bucket = os.getenv("AUDIT_BUCKET", "rag-audit")
        self.prefix = os.getenv("AUDIT_PREFIX", "requests")
        self.enabled = os.getenv("ENABLE_AUDIT_STORE", "false").lower() == "true"
        self.backend = os.getenv("AUDIT_BACKEND", "s3").lower()
        self.retention = timedelta(days=_positive_int("AUDIT_RETENTION_DAYS", 365 * 7))
        self.lock_mode = os.getenv("AUDIT_LOCK_MODE", "COMPLIANCE").upper()
        self.pii_token_key = os.getenv("PII_TOKEN_SALT", "change-me")
        if self.lock_mode not in {"COMPLIANCE", "GOVERNANCE"}:
            raise ValueError("AUDIT_LOCK_MODE must be COMPLIANCE or GOVERNANCE")
        if self.lock_mode == "COMPLIANCE" and self.retention.days < 1:
            raise ValueError("COMPLIANCE audit retention must be at least one day")

        # Local records are a bounded test/development diagnostic only. Once a
        # durable backend is selected, keeping a second in-process copy creates
        # unnecessary growth and an additional sensitive-data residence.
        self.records: deque[dict[str, Any]] = deque(
            maxlen=_positive_int("AUDIT_IN_MEMORY_MAX_RECORDS", 1_000)
        )
        self.s3 = None
        self.azure_container = None
        self.gcs_bucket = None
        self.azure_timeout = _positive_int("AUDIT_AZURE_TIMEOUT_SECONDS", 3)
        self.gcs_timeout = _positive_int("AUDIT_GCS_TIMEOUT_SECONDS", 3)
        if self.enabled:
            if self.backend == "s3":
                timeout = _positive_int("AUDIT_S3_TIMEOUT_SECONDS", 3)
                retries = _positive_int("AUDIT_S3_MAX_ATTEMPTS", 3)
                self.s3 = boto3.client(
                    "s3",
                    endpoint_url=os.getenv("S3_ENDPOINT_URL") or None,
                    region_name=os.getenv("AWS_REGION", "us-east-1"),
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                    config=Config(
                        connect_timeout=timeout,
                        read_timeout=timeout,
                        retries={"max_attempts": retries, "mode": "standard"},
                    ),
                )
            elif self.backend == "azure_blob":
                connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
                container_name = os.getenv("AZURE_AUDIT_CONTAINER", self.bucket)
                if not connection_string:
                    raise ValueError("AZURE_STORAGE_CONNECTION_STRING is required for the Azure Blob audit backend")
                from azure.storage.blob import BlobServiceClient

                retries = _positive_int("AUDIT_AZURE_MAX_ATTEMPTS", 3)
                service = BlobServiceClient.from_connection_string(
                    connection_string,
                    retry_total=retries,
                    retry_connect=retries,
                    retry_read=retries,
                    retry_status=retries,
                )
                self.azure_container = service.get_container_client(container_name)
                properties = self.azure_container.get_container_properties(timeout=self.azure_timeout)
                if not getattr(properties, "has_immutability_policy", False):
                    raise RuntimeError("Azure audit container must have a locked immutability policy")
            elif self.backend == "gcs":
                from google.cloud import storage

                if not os.getenv("AUDIT_BUCKET") or not os.getenv("GOOGLE_CLOUD_PROJECT"):
                    raise ValueError("AUDIT_BUCKET and GOOGLE_CLOUD_PROJECT are required for the GCS audit backend")
                client = storage.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT") or None)
                self.gcs_bucket = client.get_bucket(self.bucket, timeout=self.gcs_timeout)
                if not (
                    getattr(self.gcs_bucket, "retention_period", None)
                    and getattr(self.gcs_bucket, "retention_policy_locked", False)
                ):
                    raise RuntimeError("GCS audit bucket must have a locked retention policy")
            else:
                raise ValueError("AUDIT_BACKEND must be s3, azure_blob, or gcs")

    def _key(self, category: str, correlation_id: str) -> tuple[datetime, str]:
        now = datetime.now(timezone.utc)
        key = (
            f"{self.prefix}/{category}/{now:%Y/%m/%d}/"
            f"{now:%H%M%S.%fZ}-{correlation_id}-{uuid.uuid4().hex}.json"
        )
        return now, key

    def _persist(self, key: str, record: Dict[str, Any], now: datetime) -> str:
        # A caller cannot accidentally bypass the privacy boundary by sending
        # an unreviewed payload to the sink.  Correlation and request IDs stay
        # intact; caller-supplied identifiers and free-form fields are HMAC
        # tokenized, and recognised PII in every other string is redacted.
        safe_record = sanitize_for_boundary(record, self.pii_token_key)
        body = json.dumps(safe_record, sort_keys=True, separators=(",", ":")).encode()
        if self.azure_container is not None:
            from azure.storage.blob import ContentSettings, ImmutabilityPolicy

            self.azure_container.upload_blob(
                name=key,
                data=body,
                overwrite=False,
                content_settings=ContentSettings(content_type="application/json"),
                immutability_policy=ImmutabilityPolicy(
                    expiry_time=now + self.retention,
                    policy_mode="Locked",
                ),
                timeout=self.azure_timeout,
            )
            return key
        if self.gcs_bucket is not None:
            blob = self.gcs_bucket.blob(key)
            # Generation zero makes the write create-only even before the
            # bucket's locked retention policy prevents replacement/deletion.
            blob.upload_from_string(
                body,
                content_type="application/json",
                if_generation_match=0,
                timeout=self.gcs_timeout,
            )
            return key
        if self.s3 is None:
            self.records.append({"key": key, **safe_record})
            log.info("audit store disabled; record retained in bounded local diagnostics")
            return key
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
            ObjectLockMode=self.lock_mode,
            ObjectLockRetainUntilDate=now + self.retention,
        )
        return key

    def write(self, request_id: str, payload: Dict[str, Any], correlation_id: str | None = None) -> str:
        now, key = self._key("requests", request_id)
        # Add invariant identity fields last so callers cannot overwrite them.
        record = {
            **payload,
            "request_id": request_id,
            "correlation_id": correlation_id or request_id,
            "timestamp": now.isoformat(),
        }
        return self._persist(key, record, now)

    def write_state_transition(
        self,
        correlation_id: str,
        state_from: str,
        state_to: str,
        reason: str,
        payload: Dict[str, Any] | None = None,
    ) -> str:
        now, key = self._key("transitions", correlation_id)
        record = {
            "record_type": "state_transition",
            "correlation_id": correlation_id,
            "timestamp": now.isoformat(),
            "state_from": state_from,
            "state_to": state_to,
            "reason": reason,
            "payload": payload or {},
        }
        return self._persist(key, record, now)

    def write_compensation(self, correlation_id: str, compensating_record: Dict[str, Any]) -> str:
        now, key = self._key("compensations", correlation_id)
        record = {
            **compensating_record,
            "record_type": "compensation",
            "correlation_id": correlation_id,
            "timestamp": now.isoformat(),
        }
        try:
            from app.metrics import observe_compensating_event

            observe_compensating_event(
                compensating_record.get("boundary", "audit"),
                compensating_record.get("reason", "downstream_failure"),
            )
        except Exception:
            pass
        return self._persist(key, record, now)
