"""Check the installed adapter set without connecting to any integration."""
import argparse
import importlib
import importlib.metadata

MAIN = ('kafka', 'langchain_ollama', 'opensearchpy', 'azure.storage.blob', 'google.cloud.storage')
CHROMA_ONLY = frozenset({'chromadb', 'numpy', 'onnxruntime', 'chroma-hnswlib', 'posthog',
                       'tokenizers', 'huggingface-hub', 'kubernetes', 'hf-xet'})


def verify(profile):
    for name in MAIN + (('chromadb',) if profile == 'lab' else ()):
        importlib.import_module(name)
    installed = {dist.metadata['Name'].lower().replace('_', '-') for dist in importlib.metadata.distributions()}
    if profile == 'main':
        unexpected = CHROMA_ONLY & installed
        if unexpected:
            raise SystemExit('Chroma-only dependencies in main: ' + ', '.join(sorted(unexpected)))
    print(f'{profile} adapter imports passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('main', 'lab'), required=True)
    verify(parser.parse_args().profile)
