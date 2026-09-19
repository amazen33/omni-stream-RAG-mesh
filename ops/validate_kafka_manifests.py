"""Validate rendered Kafka resources against the selected operator's CRDs."""
import sys

import jsonschema
import yaml


def main(manifest_path, crd_path):
    with open(crd_path, encoding="utf-8") as source:
        crds = [item for item in yaml.safe_load_all(source)
                if item and item.get('kind') == 'CustomResourceDefinition']
    schemas = {
        (crd['spec']['names']['kind'], crd['spec']['group'] + '/' + version['name']):
        version['schema']['openAPIV3Schema']
        for crd in crds for version in crd['spec']['versions']
    }
    with open(manifest_path, encoding="utf-8") as source:
        resources = [item for item in yaml.safe_load_all(source) if item]
    count = 0
    for resource in resources:
        if resource['apiVersion'].startswith('kafka.strimzi.io/'):
            key = (resource['kind'], resource['apiVersion'])
            if key not in schemas:
                raise ValueError(f"Unsupported operator resource: {key}")
            jsonschema.Draft7Validator(schemas[key]).validate(resource)
            count += 1
    if count != 2:
        raise ValueError(f"Expected Kafka and KafkaNodePool, validated {count}")
    print(f"Validated {count} Kafka resources against pinned Strimzi CRDs")


if __name__ == '__main__':
    main(*sys.argv[1:])
