"""Round 4.1b: a long-running memory instance (docs/ROUND_4_1b.md).

LiveMemory is M (r40_memory.Memory, unchanged) plus ingest(): new reports are appended
to the hash-chained ReportStore (written to disk), added to the per-fact index, and every
cached result of the affected fact is dropped - for all knowledge times, because a late
report can change the answer for a knowledge time that was already asked.
"""
from __future__ import annotations

from .r40_memory import Memory, ReportStore


class LiveMemory(Memory):
    def __init__(self, store: ReportStore):
        super().__init__(store.reports)
        self.store = store

    def ingest(self, reports) -> None:
        for r in reports:
            self.store.extend([r])                  # checks shape and total order, writes
            fact = (r["subject"], r["attribute"])
            self._by_fact.setdefault(fact, []).append(dict(r))
            self._cache = {key: v for key, v in self._cache.items() if key[0] != fact}
