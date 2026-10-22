"""Round 4.1b: a long-running memory instance (docs/ROUND_4_1b.md).

LiveMemory is M (r40_memory.Memory, unchanged) plus ingest(): a batch of new reports is
first checked as a whole - shape, total order after the last stored report and inside
the batch, and report ids that are new to the store and unique inside the batch (the
same rule M's constructor applies, so the running instance and a rebuild from the store
cannot diverge) - and only then appended to the hash-chained ReportStore (written to
disk), added to the per-fact index, and every cached result of the affected facts is
dropped for all knowledge times. A refused batch changes nothing.
"""
from __future__ import annotations

from .r40_memory import Memory, ReportStore
from .r40_schema import check_report, order_key


class LiveMemory(Memory):
    def __init__(self, store: ReportStore):
        super().__init__(store.reports)
        self.store = store
        self._ids = {r["report_id"] for r in store.reports}
        reps = store.reports
        self._last = order_key(reps[-1]) if reps else None

    def ingest(self, reports) -> None:
        batch = [dict(r) for r in reports]
        last, seen = self._last, set()
        for r in batch:
            check_report(r)
            if r["report_id"] in self._ids or r["report_id"] in seen:
                raise ValueError(f"report id {r['report_id']} already exists")
            if last is not None and order_key(r) <= last:
                raise ValueError(f"{r['report_id']} breaks the total order")
            seen.add(r["report_id"])
            last = order_key(r)
        self.store.extend(batch)
        for r in batch:
            fact = (r["subject"], r["attribute"])
            self._by_fact.setdefault(fact, []).append(r)
            self._ids.add(r["report_id"])
            self._cache = {key: v for key, v in self._cache.items() if key[0] != fact}
        if batch:
            self._last = order_key(batch[-1])
