import pytest
import boto3
from moto import mock_aws
from google.cloud import storage

from app.audit import AuditSink


def test_s3_custom_endpoint_uses_required_only_checksums_and_writes_locked_object(monkeypatch):
    endpoint = "https://synthetic-s3.example.test"
    monkeypatch.setenv("MOTO_S3_CUSTOM_ENDPOINTS", endpoint)
    monkeypatch.setenv("ENABLE_AUDIT_STORE", "true")
    monkeypatch.setenv("AUDIT_BACKEND", "s3")
    monkeypatch.setenv("S3_ENDPOINT_URL", endpoint)
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AUDIT_BUCKET", "synthetic-locked-audit")
    with mock_aws():
        client = boto3.client("s3", endpoint_url=endpoint, region_name="us-east-1")
        client.create_bucket(Bucket="synthetic-locked-audit", ObjectLockEnabledForBucket=True)
        sink = AuditSink()
        assert sink.s3.meta.config.request_checksum_calculation == "when_required"
        key = sink.write("synthetic-request", {"event": "synthetic-audit"}, correlation_id="synthetic-correlation")
        record = client.get_object(Bucket="synthetic-locked-audit", Key=key)
        assert record["ObjectLockMode"] == "COMPLIANCE"
        assert b'"event":"synthetic-audit"' in record["Body"].read()


def test_azure_audit_backend_requires_explicit_connection_configuration(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_AUDIT_STORE", "true")
    monkeypatch.setenv("AUDIT_BACKEND", "azure_blob")
    monkeypatch.delenv("AZURE_STORAGE_CONNECTION_STRING", raising=False)

    with pytest.raises(ValueError, match="AZURE_STORAGE_CONNECTION_STRING"):
        AuditSink()


def test_unknown_audit_backend_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_AUDIT_STORE", "true")
    monkeypatch.setenv("AUDIT_BACKEND", "filesystem")

    with pytest.raises(ValueError, match="AUDIT_BACKEND"):
        AuditSink()


def test_gcs_audit_backend_requires_bucket_lock_and_uses_create_only_writes(monkeypatch) -> None:
    class FakeBlob:
        def __init__(self) -> None:
            self.call = None

        def upload_from_string(self, *args, **kwargs) -> None:
            self.call = (args, kwargs)

    class FakeBucket:
        retention_period = 86_400
        retention_policy_locked = True

        def __init__(self) -> None:
            self.blob_instance = FakeBlob()
            self.healthcheck_timeout = None

        def blob(self, _key: str) -> FakeBlob:
            return self.blob_instance

        def reload(self, timeout: float) -> None:
            self.healthcheck_timeout = timeout

    class FakeClient:
        def __init__(self, bucket: FakeBucket) -> None:
            self.bucket = bucket

        def get_bucket(self, _name: str, timeout: int) -> FakeBucket:
            assert timeout == 3
            return self.bucket

    bucket = FakeBucket()
    monkeypatch.setenv("ENABLE_AUDIT_STORE", "true")
    monkeypatch.setenv("AUDIT_BACKEND", "gcs")
    monkeypatch.setenv("AUDIT_BUCKET", "locked-audit")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "locked-audit-project")
    monkeypatch.setattr(storage, "Client", lambda project=None: FakeClient(bucket))

    sink = AuditSink()
    sink.healthcheck(timeout=1.5)
    assert bucket.healthcheck_timeout == 1.5
    key = sink.write("request-1", {"event": "safe"}, correlation_id="correlation-1")
    assert key
    args, kwargs = bucket.blob_instance.call
    assert args[0]
    assert kwargs["content_type"] == "application/json"
    assert kwargs["if_generation_match"] == 0


def test_gcs_audit_backend_rejects_an_unlocked_bucket(monkeypatch) -> None:
    class FakeBucket:
        retention_period = 86_400
        retention_policy_locked = False

    class FakeClient:
        def get_bucket(self, _name: str, timeout: int) -> FakeBucket:
            return FakeBucket()

    monkeypatch.setenv("ENABLE_AUDIT_STORE", "true")
    monkeypatch.setenv("AUDIT_BACKEND", "gcs")
    monkeypatch.setenv("AUDIT_BUCKET", "locked-audit")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "locked-audit-project")
    monkeypatch.setattr(storage, "Client", lambda project=None: FakeClient())

    with pytest.raises(RuntimeError, match="locked retention"):
        AuditSink()


def test_gcs_audit_backend_requires_explicit_project_and_bucket(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_AUDIT_STORE", "true")
    monkeypatch.setenv("AUDIT_BACKEND", "gcs")
    monkeypatch.delenv("AUDIT_BUCKET", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    with pytest.raises(ValueError, match="AUDIT_BUCKET and GOOGLE_CLOUD_PROJECT"):
        AuditSink()
