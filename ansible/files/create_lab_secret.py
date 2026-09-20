#!/usr/bin/env python3
"""Create credentials once without printing them or overwriting existing data."""
import base64
import json
import os
import secrets
import shlex
import subprocess
import sys

namespace = sys.argv[1]
kube_cli = shlex.split(os.environ.get("KUBE_CLI", "kubectl"))
if not kube_cli:
    raise SystemExit("KUBE_CLI must contain a Kubernetes client command")
existing = json.loads(subprocess.check_output(
    kube_cli + ["-n", namespace, "get", "secret", "rag-secrets", "--ignore-not-found", "-o", "json"]
) or b"{}")
required = {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "PII_TOKEN_SALT", "POSTGRES_PASSWORD", "GRAFANA_ADMIN_PASSWORD"}
if not existing:
    values = {key: secrets.token_urlsafe(32) for key in required}
    values["AWS_ACCESS_KEY_ID"] = "rag-lab"
    resource = {"apiVersion": "v1", "kind": "Secret", "metadata": {
        "name": "rag-secrets", "namespace": namespace,
    }, "type": "Opaque", "data": {
        key: base64.b64encode(value.encode()).decode() for key, value in values.items()
    }}
    subprocess.run(kube_cli + ["create", "-f", "-"],
                   input=json.dumps(resource).encode(), check=True, stdout=subprocess.DEVNULL)
elif not required.issubset(existing.get("data", {})):
    raise SystemExit("Existing rag-secrets lacks required keys; credentials were not overwritten")
