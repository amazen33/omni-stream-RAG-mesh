from domain.events import AuditRecordLogged, TelemetryIngested, TransactionProcessed


def test_events_are_stable_kafka_contracts():
    assert TelemetryIngested(request_id="r").topic == "telemetry.ingested"
    assert TransactionProcessed(request_id="r").topic == "transaction.processed"
    assert AuditRecordLogged(request_id="r").to_dict()["event_type"] == "AuditRecordLogged"


def test_event_json_is_serializable():
    assert '"topic":"audit.record.logged"' in AuditRecordLogged(request_id="r").to_json()
