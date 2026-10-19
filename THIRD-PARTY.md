# Third-party dependency and model register

WO-44 O0, Amendments 1–4 / owner D-O12 option A, inventory date 2026-10-19.
GitHub reports public repository visibility; the owner authorized proceeding
on 2026-10-19 after this discrepancy was reported. The owner has not selected a
source licence, and no LICENSE file is added. This register does not grant rights to
Omni's source or approve production or model hosting.

The tables record every installed Python distribution (including base-image
pip) in the Linux/amd64 images, using installed wheel metadata and bundled
LICENSE/COPYING/NOTICE files. Package links point to exact-version upstream
PyPI metadata; full installed notices remain in each image and are collected
in CI's `*-licenses.json`. SPDX expressions are normalized where legacy wheel
metadata contains only prose. Where an OR choice exists, the selected licence
is stated explicitly. Mandatory AND terms remain applicable.

Tier 1: MIT/MIT-0, BSD-2/3-Clause, 0BSD, ISC, PSF-2.0, PostgreSQL and Zlib;
CC0 is accepted for data only. Tier 2: Apache-2.0, with direct-dependency
rationale below. Tier 3: MPL/LGPL, unmodified and separately packaged with
upstream notices retained. No application GPL/AGPL/SSPL/BUSL/Elastic/RSAL/
Commons-Clause/proprietary component is approved for the shipped main image.
`X WITH GCC-exception-3.1` is not automatically accepted; D-O12 removes its
Chroma-only tree from main instead of granting an exception.

## Main image — shipped profile

`Dockerfile PROFILE=main` installs only the hashed `requirements.txt`.
It excludes chromadb, numpy, onnxruntime, chroma-hnswlib, posthog, tokenizers,
huggingface-hub, kubernetes and the remaining Chroma-only dependency tree.
No GCC-exception component was found in the collected main Python notices.
The publish workflow builds only main. Local IDs/sizes are recorded in the PR
and CI artifacts; a GHCR digest and signed provenance are pending the owner's
stable publish workflow after merge.

Direct Tier 2 rationale (the mature Tier 1 alternatives do not provide an
equivalent supported adapter contract):

| Direct dependency | Why Apache-2.0 is needed |
| --- | --- |
| boto3 | Official AWS S3/Object Lock, credentials and SigV4 implementation; no mature Tier 1 drop-in provides these AWS SDK contracts. |
| google-cloud-storage | Official Bucket Lock, generation preconditions and ADC/workload identity API; no mature Tier 1 equivalent covers this provider contract. |
| opensearch-py | Supported OpenSearch client, bulk/search and AWS signing integration; the removed Elasticsearch client is not an equivalent OpenSearch replacement. |
| kafka-python | Existing Kafka producer acknowledgement, header and reconnect contract; mature alternatives such as librdkafka clients are also not Tier 1. |

All other direct main inputs (FastAPI, Uvicorn, Azure Blob, Pydantic and the
LangChain Ollama/text-splitter adapters) use Tier 1 licences. Tier 2 transitive
dependencies support these adapters. HTTPX is transitively required by the
runtime Ollama client even though it is a direct development input. Test-only
pytest/Moto are absent from the images. certifi (MPL-2.0) and orjson's mandatory
MPL-2.0 portion are accepted only as unmodified, separately packaged Tier 3
components; their bundled notices and upstream source links remain available.

<!-- main-packages -->
| Package | Version | Upstream SPDX / selected terms | Class |
| --- | --- | --- | --- |
| annotated-doc | 0.0.5 | [MIT](https://pypi.org/project/annotated-doc/0.0.5/) | Tier 1 |
| annotated-types | 0.8.0 | [MIT](https://pypi.org/project/annotated-types/0.8.0/) | Tier 1 |
| anyio | 4.15.1 | [MIT](https://pypi.org/project/anyio/4.15.1/) | Tier 1 |
| azure-core | 1.41.0 | [MIT](https://pypi.org/project/azure-core/1.41.0/) | Tier 1 |
| azure-storage-blob | 12.31.0 | [MIT](https://pypi.org/project/azure-storage-blob/12.31.0/) | Tier 1 |
| boto3 | 1.43.108 | [Apache-2.0](https://pypi.org/project/boto3/1.43.108/) | Tier 2 |
| botocore | 1.43.108 | [Apache-2.0](https://pypi.org/project/botocore/1.43.108/) | Tier 2 |
| certifi | 2026.7.22 | [MPL-2.0](https://pypi.org/project/certifi/2026.7.22/) | Tier 3, unmodified |
| cffi | 2.1.1 | [MIT-0](https://pypi.org/project/cffi/2.1.1/) | Tier 1 |
| charset-normalizer | 3.5.2 | [MIT](https://pypi.org/project/charset-normalizer/3.5.2/) | Tier 1 |
| click | 8.5.0 | [BSD-3-Clause](https://pypi.org/project/click/8.5.0/) | Tier 1 |
| cryptography | 50.0.2 | [Apache-2.0 OR BSD-3-Clause; select BSD-3-Clause](https://pypi.org/project/cryptography/50.0.2/) | Tier 1 |
| distro | 1.9.0 | [Apache-2.0](https://pypi.org/project/distro/1.9.0/) | Tier 2 |
| events | 0.5 | [BSD-3-Clause](https://pypi.org/project/events/0.5/) | Tier 1 |
| fastapi | 0.142.2 | [MIT](https://pypi.org/project/fastapi/0.142.2/) | Tier 1 |
| google-api-core | 2.40.0 | [Apache-2.0](https://pypi.org/project/google-api-core/2.40.0/) | Tier 2 |
| google-auth | 2.59.1 | [Apache-2.0](https://pypi.org/project/google-auth/2.59.1/) | Tier 2 |
| google-cloud-core | 2.8.0 | [Apache-2.0](https://pypi.org/project/google-cloud-core/2.8.0/) | Tier 2 |
| google-cloud-storage | 3.16.0 | [Apache-2.0](https://pypi.org/project/google-cloud-storage/3.16.0/) | Tier 2 |
| google-crc32c | 1.9.0 | [Apache-2.0](https://pypi.org/project/google-crc32c/1.9.0/) | Tier 2 |
| google-resumable-media | 2.11.0 | [Apache-2.0](https://pypi.org/project/google-resumable-media/2.11.0/) | Tier 2 |
| googleapis-common-protos | 1.75.5 | [Apache-2.0](https://pypi.org/project/googleapis-common-protos/1.75.5/) | Tier 2 |
| grpcio | 1.84.0 | [Apache-2.0](https://pypi.org/project/grpcio/1.84.0/) | Tier 2 |
| h11 | 0.16.0 | [MIT](https://pypi.org/project/h11/0.16.0/) | Tier 1 |
| httpcore | 1.0.9 | [BSD-3-Clause](https://pypi.org/project/httpcore/1.0.9/) | Tier 1 |
| httpcore2 | 2.13.1 | [BSD-3-Clause](https://pypi.org/project/httpcore2/2.13.1/) | Tier 1 |
| httptools | 0.8.0 | [MIT](https://pypi.org/project/httptools/0.8.0/) | Tier 1 |
| httpx | 0.28.1 | [BSD-3-Clause](https://pypi.org/project/httpx/0.28.1/) | Tier 1 |
| httpx2 | 2.13.1 | [BSD-3-Clause](https://pypi.org/project/httpx2/2.13.1/) | Tier 1 |
| idna | 3.20 | [BSD-3-Clause](https://pypi.org/project/idna/3.20/) | Tier 1 |
| isodate | 0.7.2 | [BSD-3-Clause](https://pypi.org/project/isodate/0.7.2/) | Tier 1 |
| jmespath | 1.1.0 | [MIT](https://pypi.org/project/jmespath/1.1.0/) | Tier 1 |
| jsonpatch | 1.33 | [BSD-3-Clause](https://pypi.org/project/jsonpatch/1.33/) | Tier 1 |
| jsonpointer | 3.1.1 | [BSD-3-Clause](https://pypi.org/project/jsonpointer/3.1.1/) | Tier 1 |
| kafka-python | 3.0.11 | [Apache-2.0](https://pypi.org/project/kafka-python/3.0.11/) | Tier 2 |
| langchain-core | 1.6.6 | [MIT](https://pypi.org/project/langchain-core/1.6.6/) | Tier 1 |
| langchain-ollama | 1.1.0 | [MIT](https://pypi.org/project/langchain-ollama/1.1.0/) | Tier 1 |
| langchain-protocol | 0.0.19 | [MIT](https://pypi.org/project/langchain-protocol/0.0.19/) | Tier 1 |
| langchain-text-splitters | 1.1.3 | [MIT](https://pypi.org/project/langchain-text-splitters/1.1.3/) | Tier 1 |
| langsmith | 0.14.4 | [MIT](https://pypi.org/project/langsmith/0.14.4/) | Tier 1 |
| ollama | 0.6.3 | [MIT](https://pypi.org/project/ollama/0.6.3/) | Tier 1 |
| opensearch-protobufs | 1.2.0 | [Apache-2.0](https://pypi.org/project/opensearch-protobufs/1.2.0/) | Tier 2 |
| opensearch-py | 3.2.0 | [Apache-2.0](https://pypi.org/project/opensearch-py/3.2.0/) | Tier 2 |
| opentelemetry-api | 1.45.0 | [Apache-2.0](https://pypi.org/project/opentelemetry-api/1.45.0/) | Tier 2 |
| orjson | 3.12.0 | [MPL-2.0 AND (Apache-2.0 OR MIT); select MPL-2.0 AND MIT](https://pypi.org/project/orjson/3.12.0/) | Tier 3, unmodified |
| packaging | 26.3 | [Apache-2.0 OR BSD-2-Clause; select BSD-2-Clause](https://pypi.org/project/packaging/26.3/) | Tier 1 |
| pip | 25.0.1 | [MIT](https://pypi.org/project/pip/25.0.1/) | Tier 1 |
| proto-plus | 1.29.0 | [Apache-2.0](https://pypi.org/project/proto-plus/1.29.0/) | Tier 2 |
| protobuf | 7.36.2 | [BSD-3-Clause](https://pypi.org/project/protobuf/7.36.2/) | Tier 1 |
| pyasn1 | 0.6.4 | [BSD-2-Clause](https://pypi.org/project/pyasn1/0.6.4/) | Tier 1 |
| pyasn1-modules | 0.4.2 | [BSD-2-Clause](https://pypi.org/project/pyasn1-modules/0.4.2/) | Tier 1 |
| pycparser | 3.0 | [BSD-3-Clause](https://pypi.org/project/pycparser/3.0/) | Tier 1 |
| pydantic | 2.13.5 | [MIT](https://pypi.org/project/pydantic/2.13.5/) | Tier 1 |
| pydantic-core | 2.46.5 | [MIT](https://pypi.org/project/pydantic-core/2.46.5/) | Tier 1 |
| python-dateutil | 2.9.0.post0 | [Apache-2.0 OR BSD-3-Clause; select BSD-3-Clause](https://pypi.org/project/python-dateutil/2.9.0.post0/) | Tier 1 |
| python-dotenv | 1.2.4 | [BSD-3-Clause](https://pypi.org/project/python-dotenv/1.2.4/) | Tier 1 |
| pyyaml | 6.0.3 | [MIT](https://pypi.org/project/pyyaml/6.0.3/) | Tier 1 |
| requests | 2.34.2 | [Apache-2.0](https://pypi.org/project/requests/2.34.2/) | Tier 2 |
| requests-toolbelt | 1.0.0 | [Apache-2.0](https://pypi.org/project/requests-toolbelt/1.0.0/) | Tier 2 |
| s3transfer | 0.19.2 | [Apache-2.0](https://pypi.org/project/s3transfer/0.19.2/) | Tier 2 |
| six | 1.17.0 | [MIT](https://pypi.org/project/six/1.17.0/) | Tier 1 |
| sniffio | 1.3.1 | [MIT OR Apache-2.0; select MIT](https://pypi.org/project/sniffio/1.3.1/) | Tier 1 |
| starlette | 1.7.0 | [BSD-3-Clause](https://pypi.org/project/starlette/1.7.0/) | Tier 1 |
| tenacity | 9.1.4 | [Apache-2.0](https://pypi.org/project/tenacity/9.1.4/) | Tier 2 |
| truststore | 0.10.4 | [MIT](https://pypi.org/project/truststore/0.10.4/) | Tier 1 |
| typing-extensions | 4.16.0 | [PSF-2.0](https://pypi.org/project/typing-extensions/4.16.0/) | Tier 1 |
| typing-inspection | 0.4.4 | [MIT](https://pypi.org/project/typing-inspection/0.4.4/) | Tier 1 |
| urllib3 | 2.8.0 | [MIT](https://pypi.org/project/urllib3/2.8.0/) | Tier 1 |
| uuid-utils | 0.17.1 | [BSD-3-Clause](https://pypi.org/project/uuid-utils/0.17.1/) | Tier 1 |
| uvicorn | 0.54.0 | [BSD-3-Clause](https://pypi.org/project/uvicorn/0.54.0/) | Tier 1 |
| uvloop | 0.23.0 | [MIT](https://pypi.org/project/uvloop/0.23.0/) | Tier 1 |
| watchfiles | 1.3.0 | [MIT](https://pypi.org/project/watchfiles/1.3.0/) | Tier 1 |
| websockets | 17.2 | [BSD-3-Clause](https://pypi.org/project/websockets/17.2/) | Tier 1 |
| xxhash | 4.0.1 | [BSD-2-Clause](https://pypi.org/project/xxhash/4.0.1/) | Tier 1 |
| zstandard | 0.25.0 | [BSD-3-Clause](https://pypi.org/project/zstandard/0.25.0/) | Tier 1 |
<!-- /main-packages -->

## Lab image — local development only, never shipped

`Dockerfile PROFILE=lab` installs the separate hashed `requirements-lab.txt`,
which includes main plus Chroma. Only full local Compose builds this profile;
it is never pushed, tagged for release or referenced by the application chart
or Twinfra values. Tests install the lab lock through `requirements-dev.txt`.
The following complete table is separate from main, including common packages.
Chroma's Apache-2.0 client is retained only for the existing local lab adapter;
changing the adapter is later work. No Tier 1 drop-in preserves its API.

The NumPy Linux wheel's `numpy-2.5.3.dist-info/licenses/LICENSE.txt` records
bundled OpenBLAS/LAPACK (BSD-3-Clause), libgfortran (GPL-3.0-or-later WITH
GCC-exception-3.1) and libquadmath (LGPL-2.1-or-later). The actual inspected
amd64 wheel contains `numpy.libs/libgfortran-*.so.5.0.0` and
`numpy.libs/libquadmath-*.so.0.0.0`. Amendment 4 also requires registering
libgomp (GPL-3.0-or-later WITH GCC-exception-3.1) as a possible bundled native
component of this lab stack; no libgomp file was present in the inspected
NumPy wheel. These native terms remain lab-only and are not a main-image
licence exception. The wheel also includes permissive BSD/MIT/Zlib/0BSD and
CC0 portions; its CC0 code is not represented as approved Tier 1 data.
ONNX Runtime's MIT licence and ThirdPartyNotices are retained, not inferred
from its top-level licence alone. tqdm's mandatory MPL-2.0/MIT portions are
unmodified and separately packaged. Chroma 1.5.9 no longer installs the
separate chroma-hnswlib or posthog distributions; they are absent in both
actual image inventories.

<!-- lab-packages -->
| Package | Version | Upstream SPDX / selected terms | Class |
| --- | --- | --- | --- |
| aiohappyeyeballs | 2.7.1 | [PSF-2.0](https://pypi.org/project/aiohappyeyeballs/2.7.1/) | Tier 1 |
| aiohttp | 3.14.3 | [Apache-2.0 AND MIT](https://pypi.org/project/aiohttp/3.14.3/) | Tier 2 |
| aiosignal | 1.4.0 | [Apache-2.0](https://pypi.org/project/aiosignal/1.4.0/) | Tier 2 |
| annotated-doc | 0.0.5 | [MIT](https://pypi.org/project/annotated-doc/0.0.5/) | Tier 1 |
| annotated-types | 0.8.0 | [MIT](https://pypi.org/project/annotated-types/0.8.0/) | Tier 1 |
| anyio | 4.15.1 | [MIT](https://pypi.org/project/anyio/4.15.1/) | Tier 1 |
| attrs | 26.1.0 | [MIT](https://pypi.org/project/attrs/26.1.0/) | Tier 1 |
| azure-core | 1.41.0 | [MIT](https://pypi.org/project/azure-core/1.41.0/) | Tier 1 |
| azure-storage-blob | 12.31.0 | [MIT](https://pypi.org/project/azure-storage-blob/12.31.0/) | Tier 1 |
| bcrypt | 5.0.0 | [Apache-2.0](https://pypi.org/project/bcrypt/5.0.0/) | Tier 2 |
| boto3 | 1.43.108 | [Apache-2.0](https://pypi.org/project/boto3/1.43.108/) | Tier 2 |
| botocore | 1.43.108 | [Apache-2.0](https://pypi.org/project/botocore/1.43.108/) | Tier 2 |
| build | 1.6.1 | [MIT](https://pypi.org/project/build/1.6.1/) | Tier 1 |
| certifi | 2026.7.22 | [MPL-2.0](https://pypi.org/project/certifi/2026.7.22/) | Tier 3, unmodified |
| cffi | 2.1.1 | [MIT-0](https://pypi.org/project/cffi/2.1.1/) | Tier 1 |
| charset-normalizer | 3.5.2 | [MIT](https://pypi.org/project/charset-normalizer/3.5.2/) | Tier 1 |
| chromadb | 1.5.9 | [Apache-2.0](https://pypi.org/project/chromadb/1.5.9/) | Tier 2 |
| click | 8.5.0 | [BSD-3-Clause](https://pypi.org/project/click/8.5.0/) | Tier 1 |
| cryptography | 50.0.2 | [Apache-2.0 OR BSD-3-Clause; select BSD-3-Clause](https://pypi.org/project/cryptography/50.0.2/) | Tier 1 |
| distro | 1.9.0 | [Apache-2.0](https://pypi.org/project/distro/1.9.0/) | Tier 2 |
| durationpy | 0.11 | [MIT](https://pypi.org/project/durationpy/0.11/) | Tier 1 |
| events | 0.5 | [BSD-3-Clause](https://pypi.org/project/events/0.5/) | Tier 1 |
| fastapi | 0.142.2 | [MIT](https://pypi.org/project/fastapi/0.142.2/) | Tier 1 |
| filelock | 4.0.10 | [MIT](https://pypi.org/project/filelock/4.0.10/) | Tier 1 |
| flatbuffers | 25.12.19 | [Apache-2.0](https://pypi.org/project/flatbuffers/25.12.19/) | Tier 2 |
| frozenlist | 1.8.0 | [Apache-2.0](https://pypi.org/project/frozenlist/1.8.0/) | Tier 2 |
| fsspec | 2026.9.0 | [BSD-3-Clause](https://pypi.org/project/fsspec/2026.9.0/) | Tier 1 |
| google-api-core | 2.40.0 | [Apache-2.0](https://pypi.org/project/google-api-core/2.40.0/) | Tier 2 |
| google-auth | 2.59.1 | [Apache-2.0](https://pypi.org/project/google-auth/2.59.1/) | Tier 2 |
| google-cloud-core | 2.8.0 | [Apache-2.0](https://pypi.org/project/google-cloud-core/2.8.0/) | Tier 2 |
| google-cloud-storage | 3.16.0 | [Apache-2.0](https://pypi.org/project/google-cloud-storage/3.16.0/) | Tier 2 |
| google-crc32c | 1.9.0 | [Apache-2.0](https://pypi.org/project/google-crc32c/1.9.0/) | Tier 2 |
| google-resumable-media | 2.11.0 | [Apache-2.0](https://pypi.org/project/google-resumable-media/2.11.0/) | Tier 2 |
| googleapis-common-protos | 1.75.5 | [Apache-2.0](https://pypi.org/project/googleapis-common-protos/1.75.5/) | Tier 2 |
| grpcio | 1.84.0 | [Apache-2.0](https://pypi.org/project/grpcio/1.84.0/) | Tier 2 |
| h11 | 0.16.0 | [MIT](https://pypi.org/project/h11/0.16.0/) | Tier 1 |
| hf-xet | 1.6.0 | [Apache-2.0](https://pypi.org/project/hf-xet/1.6.0/) | Tier 2 |
| httpcore | 1.0.9 | [BSD-3-Clause](https://pypi.org/project/httpcore/1.0.9/) | Tier 1 |
| httpcore2 | 2.13.1 | [BSD-3-Clause](https://pypi.org/project/httpcore2/2.13.1/) | Tier 1 |
| httptools | 0.8.0 | [MIT](https://pypi.org/project/httptools/0.8.0/) | Tier 1 |
| httpx | 0.28.1 | [BSD-3-Clause](https://pypi.org/project/httpx/0.28.1/) | Tier 1 |
| httpx2 | 2.13.1 | [BSD-3-Clause](https://pypi.org/project/httpx2/2.13.1/) | Tier 1 |
| huggingface-hub | 1.33.0 | [Apache-2.0](https://pypi.org/project/huggingface-hub/1.33.0/) | Tier 2 |
| idna | 3.20 | [BSD-3-Clause](https://pypi.org/project/idna/3.20/) | Tier 1 |
| importlib-resources | 7.1.0 | [Apache-2.0](https://pypi.org/project/importlib-resources/7.1.0/) | Tier 2 |
| isodate | 0.7.2 | [BSD-3-Clause](https://pypi.org/project/isodate/0.7.2/) | Tier 1 |
| jmespath | 1.1.0 | [MIT](https://pypi.org/project/jmespath/1.1.0/) | Tier 1 |
| jsonpatch | 1.33 | [BSD-3-Clause](https://pypi.org/project/jsonpatch/1.33/) | Tier 1 |
| jsonpointer | 3.1.1 | [BSD-3-Clause](https://pypi.org/project/jsonpointer/3.1.1/) | Tier 1 |
| jsonschema | 4.26.0 | [MIT](https://pypi.org/project/jsonschema/4.26.0/) | Tier 1 |
| jsonschema-specifications | 2025.9.1 | [MIT](https://pypi.org/project/jsonschema-specifications/2025.9.1/) | Tier 1 |
| kafka-python | 3.0.11 | [Apache-2.0](https://pypi.org/project/kafka-python/3.0.11/) | Tier 2 |
| kubernetes | 36.0.3 | [Apache-2.0](https://pypi.org/project/kubernetes/36.0.3/) | Tier 2 |
| langchain-core | 1.6.6 | [MIT](https://pypi.org/project/langchain-core/1.6.6/) | Tier 1 |
| langchain-ollama | 1.1.0 | [MIT](https://pypi.org/project/langchain-ollama/1.1.0/) | Tier 1 |
| langchain-protocol | 0.0.19 | [MIT](https://pypi.org/project/langchain-protocol/0.0.19/) | Tier 1 |
| langchain-text-splitters | 1.1.3 | [MIT](https://pypi.org/project/langchain-text-splitters/1.1.3/) | Tier 1 |
| langsmith | 0.14.4 | [MIT](https://pypi.org/project/langsmith/0.14.4/) | Tier 1 |
| markdown-it-py | 4.2.0 | [MIT](https://pypi.org/project/markdown-it-py/4.2.0/) | Tier 1 |
| mdurl | 0.1.2 | [MIT](https://pypi.org/project/mdurl/0.1.2/) | Tier 1 |
| mmh3 | 5.3.1 | [MIT](https://pypi.org/project/mmh3/5.3.1/) | Tier 1 |
| multidict | 6.9.1 | [Apache-2.0](https://pypi.org/project/multidict/6.9.1/) | Tier 2 |
| numpy | 2.5.3 | [BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0; bundled native terms below](https://pypi.org/project/numpy/2.5.3/) | lab only; not approved for shipment |
| oauthlib | 4.0.0 | [BSD-3-Clause](https://pypi.org/project/oauthlib/4.0.0/) | Tier 1 |
| ollama | 0.6.3 | [MIT](https://pypi.org/project/ollama/0.6.3/) | Tier 1 |
| onnxruntime | 1.30.0 | [MIT](https://pypi.org/project/onnxruntime/1.30.0/) | Tier 1 |
| opensearch-protobufs | 1.2.0 | [Apache-2.0](https://pypi.org/project/opensearch-protobufs/1.2.0/) | Tier 2 |
| opensearch-py | 3.2.0 | [Apache-2.0](https://pypi.org/project/opensearch-py/3.2.0/) | Tier 2 |
| opentelemetry-api | 1.45.0 | [Apache-2.0](https://pypi.org/project/opentelemetry-api/1.45.0/) | Tier 2 |
| opentelemetry-exporter-otlp-common | 0.66b0 | [Apache-2.0](https://pypi.org/project/opentelemetry-exporter-otlp-common/0.66b0/) | Tier 2 |
| opentelemetry-exporter-otlp-proto-common | 1.45.0 | [Apache-2.0](https://pypi.org/project/opentelemetry-exporter-otlp-proto-common/1.45.0/) | Tier 2 |
| opentelemetry-exporter-otlp-proto-grpc | 1.45.0 | [Apache-2.0](https://pypi.org/project/opentelemetry-exporter-otlp-proto-grpc/1.45.0/) | Tier 2 |
| opentelemetry-proto | 1.45.0 | [Apache-2.0](https://pypi.org/project/opentelemetry-proto/1.45.0/) | Tier 2 |
| opentelemetry-sdk | 1.45.0 | [Apache-2.0](https://pypi.org/project/opentelemetry-sdk/1.45.0/) | Tier 2 |
| opentelemetry-semantic-conventions | 0.66b0 | [Apache-2.0](https://pypi.org/project/opentelemetry-semantic-conventions/0.66b0/) | Tier 2 |
| orjson | 3.12.0 | [MPL-2.0 AND (Apache-2.0 OR MIT); select MPL-2.0 AND MIT](https://pypi.org/project/orjson/3.12.0/) | Tier 3, unmodified |
| overrides | 7.7.0 | [Apache-2.0](https://pypi.org/project/overrides/7.7.0/) | Tier 2 |
| packaging | 26.3 | [Apache-2.0 OR BSD-2-Clause; select BSD-2-Clause](https://pypi.org/project/packaging/26.3/) | Tier 1 |
| pip | 25.0.1 | [MIT](https://pypi.org/project/pip/25.0.1/) | Tier 1 |
| propcache | 0.5.4 | [Apache-2.0](https://pypi.org/project/propcache/0.5.4/) | Tier 2 |
| proto-plus | 1.29.0 | [Apache-2.0](https://pypi.org/project/proto-plus/1.29.0/) | Tier 2 |
| protobuf | 7.36.2 | [BSD-3-Clause](https://pypi.org/project/protobuf/7.36.2/) | Tier 1 |
| pyasn1 | 0.6.4 | [BSD-2-Clause](https://pypi.org/project/pyasn1/0.6.4/) | Tier 1 |
| pyasn1-modules | 0.4.2 | [BSD-2-Clause](https://pypi.org/project/pyasn1-modules/0.4.2/) | Tier 1 |
| pybase64 | 1.5.1 | [BSD-2-Clause](https://pypi.org/project/pybase64/1.5.1/) | Tier 1 |
| pycparser | 3.0 | [BSD-3-Clause](https://pypi.org/project/pycparser/3.0/) | Tier 1 |
| pydantic | 2.13.5 | [MIT](https://pypi.org/project/pydantic/2.13.5/) | Tier 1 |
| pydantic-core | 2.46.5 | [MIT](https://pypi.org/project/pydantic-core/2.46.5/) | Tier 1 |
| pydantic-settings | 2.15.0 | [MIT](https://pypi.org/project/pydantic-settings/2.15.0/) | Tier 1 |
| pygments | 2.21.0 | [BSD-2-Clause](https://pypi.org/project/pygments/2.21.0/) | Tier 1 |
| pypika | 0.51.1 | [Apache-2.0](https://pypi.org/project/pypika/0.51.1/) | Tier 2 |
| pyproject-hooks | 1.3.3 | [MIT](https://pypi.org/project/pyproject-hooks/1.3.3/) | Tier 1 |
| python-dateutil | 2.9.0.post0 | [Apache-2.0 OR BSD-3-Clause; select BSD-3-Clause](https://pypi.org/project/python-dateutil/2.9.0.post0/) | Tier 1 |
| python-dotenv | 1.2.4 | [BSD-3-Clause](https://pypi.org/project/python-dotenv/1.2.4/) | Tier 1 |
| pyyaml | 6.0.3 | [MIT](https://pypi.org/project/pyyaml/6.0.3/) | Tier 1 |
| referencing | 0.37.0 | [MIT](https://pypi.org/project/referencing/0.37.0/) | Tier 1 |
| requests | 2.34.2 | [Apache-2.0](https://pypi.org/project/requests/2.34.2/) | Tier 2 |
| requests-oauthlib | 2.0.0 | [ISC](https://pypi.org/project/requests-oauthlib/2.0.0/) | Tier 1 |
| requests-toolbelt | 1.0.0 | [Apache-2.0](https://pypi.org/project/requests-toolbelt/1.0.0/) | Tier 2 |
| rich | 15.0.0 | [MIT](https://pypi.org/project/rich/15.0.0/) | Tier 1 |
| rpds-py | 2026.9.1 | [MIT](https://pypi.org/project/rpds-py/2026.9.1/) | Tier 1 |
| s3transfer | 0.19.2 | [Apache-2.0](https://pypi.org/project/s3transfer/0.19.2/) | Tier 2 |
| shellingham | 1.5.4 | [ISC](https://pypi.org/project/shellingham/1.5.4/) | Tier 1 |
| six | 1.17.0 | [MIT](https://pypi.org/project/six/1.17.0/) | Tier 1 |
| sniffio | 1.3.1 | [MIT OR Apache-2.0; select MIT](https://pypi.org/project/sniffio/1.3.1/) | Tier 1 |
| starlette | 1.7.0 | [BSD-3-Clause](https://pypi.org/project/starlette/1.7.0/) | Tier 1 |
| tenacity | 9.1.4 | [Apache-2.0](https://pypi.org/project/tenacity/9.1.4/) | Tier 2 |
| tokenizers | 0.23.2 | [Apache-2.0](https://pypi.org/project/tokenizers/0.23.2/) | Tier 2 |
| tqdm | 4.70.1 | [MPL-2.0 AND MIT](https://pypi.org/project/tqdm/4.70.1/) | Tier 3, unmodified |
| truststore | 0.10.4 | [MIT](https://pypi.org/project/truststore/0.10.4/) | Tier 1 |
| typer | 0.27.2 | [MIT](https://pypi.org/project/typer/0.27.2/) | Tier 1 |
| typing-extensions | 4.16.0 | [PSF-2.0](https://pypi.org/project/typing-extensions/4.16.0/) | Tier 1 |
| typing-inspection | 0.4.4 | [MIT](https://pypi.org/project/typing-inspection/0.4.4/) | Tier 1 |
| urllib3 | 2.8.0 | [MIT](https://pypi.org/project/urllib3/2.8.0/) | Tier 1 |
| uuid-utils | 0.17.1 | [BSD-3-Clause](https://pypi.org/project/uuid-utils/0.17.1/) | Tier 1 |
| uvicorn | 0.54.0 | [BSD-3-Clause](https://pypi.org/project/uvicorn/0.54.0/) | Tier 1 |
| uvloop | 0.23.0 | [MIT](https://pypi.org/project/uvloop/0.23.0/) | Tier 1 |
| watchfiles | 1.3.0 | [MIT](https://pypi.org/project/watchfiles/1.3.0/) | Tier 1 |
| websocket-client | 1.9.2 | [Apache-2.0](https://pypi.org/project/websocket-client/1.9.2/) | Tier 2 |
| websockets | 17.2 | [BSD-3-Clause](https://pypi.org/project/websockets/17.2/) | Tier 1 |
| xxhash | 4.0.1 | [BSD-2-Clause](https://pypi.org/project/xxhash/4.0.1/) | Tier 1 |
| yarl | 1.25.1 | [Apache-2.0](https://pypi.org/project/yarl/1.25.1/) | Tier 2 |
| zstandard | 0.25.0 | [BSD-3-Clause](https://pypi.org/project/zstandard/0.25.0/) | Tier 1 |
<!-- /lab-packages -->

## Base image — class `base-os` (recorded once)

Both profiles inherit exactly
`python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1`.
The official Debian-based Python image's operating-system packages remain
unmodified aggregated programs, including its GPL utilities and LGPL system
libraries (for example bash/coreutils/glibc). Per the review's "Base image"
policy these are recorded once at image level as `base-os`, rather than as
application licence exceptions. This narrowly scoped exception does not allow
AGPL, SSPL, BUSL, Elastic or proprietary base components. Upstream copyright
files remain under `/usr/share/doc`; Syft inventories exact OS packages and
Grype reports their vulnerabilities. Python is PSF-2.0; pip is listed above.

Sources: [official Python image](https://hub.docker.com/_/python),
[Debian copyright policy](https://www.debian.org/doc/debian-policy/ch-docs.html#copyright-information).

## Development tools — not installed in either API image

| Tool | Version | Licence | Use and evidence |
| --- | --- | --- | --- |
| Locust | 2.46.7 | MIT (Tier 1) | Owner's OMNI-WO-00 Part B load generator. [Exact-version metadata and hashes](https://pypi.org/project/locust/2.46.7/); hashed in `requirements-dev.txt`, direct pin in `requirements-dev.in`. Scenarios and benchmark execution are outside Part A. |

The dev lock is resolved under the existing lab/runtime constraints and the O0
2026-10-05 cutoff. Adding Locust does not add a runtime image dependency.

## Model register — weights are not in either API image

| Configured reference | Role | Upstream licence | Twinfra disposition |
| --- | --- | --- | --- |
| `phi4-mini:3.8b` (`OLLAMA_MODEL`) | Default AI model, owner D-O13 (2026-10-19) | MIT, [Microsoft model card](https://huggingface.co/microsoft/Phi-4-mini-instruct); [official Ollama tag](https://ollama.com/library/phi4-mini:3.8b) | Manifest `sha256:78fad5d182a7c33065e153a5f8ba210754207ba9d91973f57dffa7f487363753`, recorded from the [official manifest endpoint](https://registry.ollama.ai/v2/library/phi4-mini/manifests/3.8b) on 2026-10-19. G3.5 licence approved; no weights downloaded or run. |
| `nomic-embed-text` (`OLLAMA_EMBED_MODEL`) | Local text embeddings default | [Apache-2.0, upstream weights and code](https://www.nomic.ai/news/nomic-embed-text-v1); [Ollama distribution](https://ollama.com/library/nomic-embed-text) | Tier 2 candidate; owner must approve the exact model artifact/digest before hosting. |

Removed: `llama3.2:3b`; its [community licence](https://huggingface.co/meta-llama/Llama-3.2-3B/blob/main/LICENSE.txt) fails G3.5. Replaced by owner decision D-O13.

The recorded Phi-4-mini digest is SHA256 of the 711-byte Ollama manifest response,
not an individual weight blob or an Ollama image digest. The tag's short ID on
the library page is `78fad5d182a7`. Tags can move: verify this digest before an
owner-run pull/use; the baseline harness checks the pre-provisioned manifest.
No weights were pulled or served. Ollama itself is MIT and is an optional separate service;
its software licence does not determine a model's licence. Model governance,
quality and hosting acceptance remain later-phase gates.

OMNI-WO-00's optional baseline harness uses Ollama 0.34.4 ([MIT](https://github.com/ollama/ollama/blob/v0.34.4/LICENSE)),
image index `sha256:8262851b2846b87c649eddf3e76beb270c52f4d1bc94559f47efde16b0841551`
(registry manifest inspected 2026-10-19). D-O13 selects
[Phi-4-mini](https://huggingface.co/microsoft/Phi-4-mini-instruct/blob/main/LICENSE)
(MIT) as the default. [Granite 3.x](https://huggingface.co/ibm-granite/granite-3.3-2b-instruct/blob/main/LICENSE)
(Apache-2.0) remains an optional explicitly approved alternative. The baseline
model and exact digest remain explicit owner inputs. The harness verifies that
manifest in the owner's pre-provisioned read-only model cache and rejects
Llama. No model weights, download, hosting acceptance or B0 run are delivered.

## Optional services

MinIO, Grafana, Loki, Tempo, EventStoreDB, TimescaleDB and Confluent Schema
Registry are **not used on Twinfra**. Their local Compose/chart references do
not approve their software, enterprise features or licence terms for hosting.
Their service images are not contents of the main API image. Kafka, OpenSearch,
Ollama, persistent audit and external integrations are disabled in O1's
ephemeral profile and require later phase review and acceptance.
