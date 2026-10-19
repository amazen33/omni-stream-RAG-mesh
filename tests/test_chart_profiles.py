"""Render real manifests: selectors, restricted runtime and Secret references."""
import json

import pytest
import yaml

from ops.helm_contract import PROFILES, render, verify_version


@pytest.fixture(scope='module', autouse=True)
def required_helm():
    verify_version()


def manifests(profile, **kwargs):
    return [doc for doc in yaml.safe_load_all(render(profile, **kwargs).stdout) if doc]


def test_twinfra_is_one_ephemeral_restricted_gateway_fronted_pod():
    resources = manifests('twinfra', namespace='omni-dev')
    deployment = next(r for r in resources if r['kind'] == 'Deployment')
    assert deployment['spec']['replicas'] == 1
    assert not any(r['kind'] == 'PodDisruptionBudget' for r in resources)
    pod = deployment['spec']['template']['spec']
    assert pod['automountServiceAccountToken'] is False
    assert pod['securityContext']['runAsNonRoot'] is True
    container = pod['containers'][0]
    assert container['securityContext']['readOnlyRootFilesystem'] is True
    assert container['securityContext']['allowPrivilegeEscalation'] is False
    assert 'spiffe-workload-api' not in str(pod)
    assert 'sidecar.istio.io/inject' not in deployment['spec']['template']['metadata']['labels']
    config = next(r for r in resources if r['kind'] == 'ConfigMap')['data']
    for name in ('VECTOR_STORE', 'SEARCH_STORE', 'AUDIT_STORE', 'KAFKA', 'OLLAMA_INFERENCE'):
        assert config[f'ENABLE_{name}'] == 'false'
    policy = next(r for r in resources if r['metadata']['name'] == 'rag-api-allow-required-paths')
    gateway = policy['spec']['ingress'][0]['from']
    assert gateway == [{'namespaceSelector': {'matchLabels': {'kubernetes.io/metadata.name': 'platform-services'}},
                        'podSelector': {'matchLabels': {'app.kubernetes.io/instance': 'apisix',
                                                       'app.kubernetes.io/name': 'apisix'}}}]
    assert policy['spec']['ingress'][1]['ports'] == [{'protocol': 'TCP', 'port': 8000}]
    assert policy['spec']['egress'] == [{'to': [{'namespaceSelector': {'matchLabels': {
        'kubernetes.io/metadata.name': 'kube-system'}}}], 'ports': [
            {'protocol': 'UDP', 'port': 53}, {'protocol': 'TCP', 'port': 53}]}]


def test_debezium_requires_an_existing_secret():
    result = render('generic', extra=('--set', 'integrations.debezium=true'), check=False)
    assert result.returncode != 0
    assert b'db.existingSecret is required' in result.stderr


def test_twinfra_can_use_the_published_digest_without_a_mutable_tag():
    digest = 'sha256:' + 'a' * 64
    resources = manifests('twinfra', extra=('--set', 'ragApi.image.repository=ghcr.io/amazen33/omni-stream-rag-mesh',
                                            '--set', 'ragApi.image.digest=' + digest))
    deployment = next(r for r in resources if r['kind'] == 'Deployment')
    assert deployment['spec']['template']['spec']['containers'][0]['image'] == 'ghcr.io/amazen33/omni-stream-rag-mesh@' + digest


@pytest.mark.parametrize('profile', (*PROFILES, 'twinfra'))
def test_configmaps_have_only_password_references_and_provider_is_wired(profile):
    resources = manifests(profile, extra=('--set', 'integrations.debezium=true',
        '--set', 'db.existingSecret=synthetic-database-secret', '--set', 'db.passwordKey=database-key',
        '--set', 'db.password=synthetic-password-value',
        '--set', 'db.connectImage=example.invalid/reviewed-connect@sha256:' + '0' * 64))
    configs = [r for r in resources if r['kind'] == 'ConfigMap']
    connector = next(r for r in configs if r['metadata']['name'] == 'debezium-connector')
    password = json.loads(connector['data']['connector.json'])['config']['database.password']
    assert password == '${secrets:rag/synthetic-database-secret:database-key}'
    for config in configs:
        text = json.dumps(config['data'])
        assert 'changeme' not in text and 'synthetic-password-value' not in text
    worker = next(r for r in resources if r['kind'] == 'KafkaConnect')
    assert worker['spec']['config']['config.providers'] == 'secrets'
    assert worker['spec']['config']['config.providers.secrets.class'] == 'io.strimzi.kafka.KubernetesSecretConfigProvider'
    role = next(r for r in resources if r['kind'] == 'Role')
    assert role['rules'] == [{'apiGroups': [''], 'resources': ['secrets'],
        'resourceNames': ['synthetic-database-secret'], 'verbs': ['get']}]
