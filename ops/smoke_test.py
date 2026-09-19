"""Run a real HTTP smoke test against an isolated, dependency-free API process."""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request


def main():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = dict(os.environ)
    for name in ("AUDIT_STORE", "KAFKA", "VECTOR_STORE", "SEARCH_STORE", "OLLAMA_INFERENCE"):
        env[f"ENABLE_{name}"] = "false"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    def request(path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.load(response)

    try:
        deadline = time.monotonic() + 20
        while True:
            try:
                assert request("/health/live")["status"] == "ok"
                break
            except OSError:
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("API did not start")
                time.sleep(0.1)
        assert request("/ingest-sample", {"text": "synthetic evidence"})["chunks"] > 0
        assert request("/ask", {"question": "synthetic evidence"})["retrieved"]
        assert request("/payments/transactions", {
            "transaction_id": "smoke", "merchant_id": "synthetic", "amount_minor": 1, "currency": "USD"
        })["decision"] == "allow"
        print("HTTP smoke passed: liveness, ingestion, retrieval, payments")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
