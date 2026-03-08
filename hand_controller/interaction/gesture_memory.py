from __future__ import annotations
from collections import deque


class GestureMemory:
    def __init__(self, maxlen: int = 4):
        self.history = deque(maxlen=maxlen)

    def push(self, label: str) -> None:
        self.history.append(label)

    def majority(self) -> str | None:
        if not self.history:
            return None
        counts = {}
        for label in self.history:
            counts[label] = counts.get(label, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]
