"""Seeded, wholly synthetic API fixtures for the owner's QoS scenarios.

KB means 1024 UTF-8 bytes. No global random state, clock, UUIDs or real records
are used. Payment fields match the existing API and contain no card data.
"""
from __future__ import annotations

import argparse
import json
import random

DOCUMENT_SIZES_KB = (1, 10, 100)
_WORDS = ("synthetic", "sample", "parcel", "inventory", "orbit", "harbor", "ledger", "violet")


def generate_corpus(seed: int, count: int = 1) -> dict[str, list[dict[str, object]]]:
    """Return count documents per size, plus matching questions and payments.

    All text is ASCII (and therefore has identical character/UTF-8 byte sizes).
    PII-looking numeric identifiers are avoided entirely.
    """
    if count < 1:
        raise ValueError("count must be positive")
    rng = random.Random(seed)
    documents: list[dict[str, object]] = []
    questions: list[dict[str, object]] = []
    payments: list[dict[str, object]] = []
    for size_kb in DOCUMENT_SIZES_KB:
        for index in range(count):
            marker = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(16))
            source = f"synthetic-{size_kb}kb-{index}-{marker}"
            prefix = f"Synthetic document {marker}. The sample parcel is violet. "
            target = size_kb * 1024
            words = " ".join(rng.choice(_WORDS) for _ in range(target // 4 + 1))
            documents.append({"source": source, "text": (prefix + words)[:target]})
            questions.append({"question": f"In synthetic document {marker}, what color is the sample parcel?", "top_k": 4})
            payments.append({
                "transaction_id": f"synthetic-txn-{marker}",
                "merchant_id": f"synthetic-merchant-{marker}",
                "amount_minor": rng.randrange(1, 100_001),
                "currency": "USD",
                "payment_network": "synthetic",
            })
    return {"documents": documents, "questions": questions, "payments": payments}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--count", type=int, default=1, help="Documents per size (default: 1)")
    args = parser.parse_args()
    print(json.dumps(generate_corpus(args.seed, args.count), sort_keys=True))


if __name__ == "__main__":
    main()
