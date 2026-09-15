"""
Chaos & Verification Test: Surviving & Verifying Downstream Failure across the RAG Mesh Lifecycle
Validates:
1. Structured Correlation IDs across HTTP headers, payload, and log context.
2. Boundary Metrics & LGTM Monitoring (Bulkhead, Circuit Breaker trips, Latency metrics).
3. Audit & Rollback Verification (MinIO WORM state transitions and SHA-256 integrity).
"""

import sys
import os
import json
import hashlib
import unittest

# Ensure app directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../app")))

try:
    from fastapi.testclient import TestClient
    from main import app, ollama_breaker, audit_logger, CircuitBreakerState, LifecycleState
except ImportError as exc:
    print(f"Skipping test execution due to missing dependency: {exc}")
    TestClient = None


class TestDownstreamFailureSurvival(unittest.TestCase):
    def setUp(self):
        if TestClient is None:
            self.skipTest("TestClient not installed in current environment")
        self.client = TestClient(app)
        # Reset breaker state
        ollama_breaker.state = CircuitBreakerState.CLOSED
        ollama_breaker.consecutive_failures = 0
        audit_logger.in_memory_audit_store.clear()

    def test_01_structured_correlation_ids(self):
        """Verify immutable correlation IDs are preserved across request-response cycle."""
        custom_corr_id = "txn-corr-test-uuid-4444"
        custom_cause_id = "cause-test-parent-1111"

        response = self.client.post(
            "/api/v1/query",
            headers={
                "X-Correlation-ID": custom_corr_id,
                "X-Causation-ID": custom_cause_id,
            },
            json={
                "prompt": "Test query for correlation validation",
                "simulate_downstream_failure": True,
            }
        )

        # Assert Correlation ID propagation in HTTP headers
        self.assertEqual(response.headers.get("X-Correlation-ID"), custom_corr_id)
        self.assertEqual(response.headers.get("X-Causation-ID"), custom_cause_id)

        data = response.json()
        self.assertEqual(data["correlation_id"], custom_corr_id)
        print(f"[TEST 1 PASS] Correlation ID '{custom_corr_id}' successfully propagated.")

    def test_02_boundary_metrics_and_circuit_breaker(self):
        """Verify boundary metrics increment on failure and circuit breaker trips."""
        # Send 2 failing requests to trip the circuit breaker (failure_threshold=2)
        for i in range(2):
            res = self.client.post(
                "/api/v1/query",
                json={
                    "prompt": f"Failing prompt {i}",
                    "simulate_downstream_failure": True,
                }
            )
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.json()["compensating_event_triggered"])

        # Circuit breaker should now be OPEN
        self.assertEqual(ollama_breaker.state, CircuitBreakerState.OPEN)

        # Next request must be rejected with 503 by Circuit Breaker
        rejected_res = self.client.post(
            "/api/v1/query",
            json={"prompt": "Should be blocked by circuit breaker"}
        )
        self.assertEqual(rejected_res.status_code, 503)

        # Verify Prometheus metrics scrape endpoint
        metrics_res = self.client.get("/metrics")
        self.assertEqual(metrics_res.status_code, 200)
        metrics_text = metrics_res.text

        self.assertIn("rag_circuit_breaker_tripped_total", metrics_text)
        self.assertIn("rag_downstream_boundary_latency_seconds", metrics_text)
        print("[TEST 2 PASS] Boundary metrics and Circuit Breaker trip verified on /metrics.")

    def test_03_audit_and_rollback_verification(self):
        """Verify immutable MinIO state transitions with SHA-256 integrity and compensating rollback."""
        corr_id = "txn-audit-verify-7777"
        self.client.post(
            "/api/v1/query",
            headers={"X-Correlation-ID": corr_id},
            json={
                "prompt": "Trigger compensating rollback",
                "simulate_downstream_failure": True,
            }
        )

        audit_res = self.client.get("/api/v1/audit/trail")
        self.assertEqual(audit_res.status_code, 200)
        trail = audit_res.json()["records"]

        # Filter records for this correlation ID
        matching_records = [r for r in trail if r["correlation_id"] == corr_id]
        states = [r["state"] for r in matching_records]

        # Assert expected lifecycle state machine transitions
        self.assertIn(LifecycleState.INITIATED.value, states)
        self.assertIn(LifecycleState.INFERENCE_FAILED.value, states)
        self.assertIn(LifecycleState.COMPENSATING_ROLLBACK.value, states)

        # Verify SHA-256 cryptographic checksum integrity on each record
        for rec in matching_records:
            expected_hash = rec["sha256_checksum"]
            rec_copy = dict(rec)
            del rec_copy["sha256_checksum"]
            calculated_hash = hashlib.sha256(json.dumps(rec_copy, sort_keys=True).encode("utf-8")).hexdigest()
            self.assertEqual(expected_hash, calculated_hash, "Cryptographic audit checksum mismatch!")

        # Verify compensating flag on rollback record
        rollback_record = next(r for r in matching_records if r["state"] == LifecycleState.COMPENSATING_ROLLBACK.value)
        self.assertTrue(rollback_record["is_compensating"])

        print("[TEST 3 PASS] MinIO WORM audit trail and compensating rollback SHA-256 verified.")


if __name__ == "__main__":
    unittest.main()
