"""Processed-episode tracking. Single writer for state.json."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Sequence


class State:
    def __init__(self, path):
        self.path = Path(path)
        self._guids = self._load()

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return set()
        return set(data.get("processed", []))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"processed": sorted(self._guids)}
        self.path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")

    def is_processed(self, guid: str) -> bool:
        return guid in self._guids

    def mark(self, guid: str) -> None:
        self._guids.add(guid)
        self.save()

    def seed(self, guids_newest_first: Sequence[str]) -> None:
        """Mark everything except the most recent episode as already done."""
        self._guids = set(guids_newest_first[1:])
        self.save()

    def pending(self, guids_newest_first: Iterable[str]) -> List[str]:
        """Unprocessed guids, oldest first, so a backlog catches up in order."""
        return [g for g in reversed(list(guids_newest_first)) if g not in self._guids]
