"""Deterministic, version-independent random choices (SHA-256 counter mode).

Python's `random` module is not guaranteed to give the same sequence across
versions for every method; worlds must be byte-identical everywhere, so the lab
uses its own generator.
"""
from __future__ import annotations

import hashlib


class HashRng:
    def __init__(self, seed: str):
        self._seed = seed.encode("utf-8")
        self._counter = 0

    def _next_u64(self) -> int:
        block = hashlib.sha256(self._seed + b"\0" + str(self._counter).encode()).digest()
        self._counter += 1
        return int.from_bytes(block[:8], "big")

    def below(self, n: int) -> int:
        """Uniform integer in [0, n) without modulo bias."""
        if n <= 0:
            raise ValueError("n must be positive")
        limit = (1 << 64) - ((1 << 64) % n)
        while True:
            value = self._next_u64()
            if value < limit:
                return value % n

    def choice(self, items):
        return items[self.below(len(items))]

    def shuffled(self, items):
        result = list(items)
        for i in range(len(result) - 1, 0, -1):
            j = self.below(i + 1)
            result[i], result[j] = result[j], result[i]
        return result

    def sample(self, items, k: int):
        if k > len(items):
            raise ValueError("sample larger than population")
        return self.shuffled(items)[:k]
