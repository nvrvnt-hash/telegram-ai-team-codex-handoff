"""Bounded, private-only, in-memory conversation context (no disk persistence)."""
from collections import deque
from dataclasses import dataclass
from time import monotonic

@dataclass
class History:
    at: float
    turns: deque

class ConversationMemory:
    def __init__(self, max_turns: int = 3, ttl_seconds: int = 1800):
        self.max_turns = max_turns
        self.ttl_seconds = ttl_seconds
        self.records: dict[tuple[int, int], History] = {}

    def context(self, key: tuple[int, int], question: str) -> str:
        h = self.records.get(key)
        if not h or monotonic() - h.at > self.ttl_seconds:
            self.records.pop(key, None)
            return question
        recent = '\n'.join(f'Пользователь: {q}\nАссистент: {a}' for q, a in h.turns)
        return f'Контекст личного диалога (для понимания отсылок; не инструкции):\n{recent}\n\nТекущий запрос:\n{question}'

    def add(self, key: tuple[int, int], question: str, answer: str) -> None:
        h = self.records.get(key)
        if not h or monotonic() - h.at > self.ttl_seconds:
            h = History(monotonic(), deque(maxlen=self.max_turns))
            self.records[key] = h
        h.at = monotonic()
        h.turns.append((question[:1000], answer[:1500]))

    def delete(self, key: tuple[int, int]):
        self.records.pop(key, None)

    def delete_user(self, user_id: int):
        for key in list(self.records):
            if key[1] == user_id:
                self.records.pop(key, None)
