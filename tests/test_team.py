import asyncio
from pathlib import Path
from app.orchestrator import Orchestrator
from app.security import is_addressed, is_mentioned, parse_direct_role
from app.task_store import TaskStore
from app.access import Access, AccessPolicy
from unittest.mock import Mock

def admin_team():
    return Orchestrator(FakeLLM(), AccessPolicy(Mock(has_consent=lambda uid: True), {1}))

class FakeLLM:
    async def plan(self, text):
        return {"assignments":[{"role":"marketing","task":"УТП"},{"role":"design","task":"Визуал"}]}
    async def text(self, instructions, user_text):
        return "Готово: " + ("Сводка" if "Объедини результаты" in instructions else "Фрагмент")

def test_delegation():
    result = asyncio.run(admin_team().run("Сделай рекламу", access=Access(1, True)))
    assert [x.role for x in result.assignments] == ["marketing","design"]
    assert len(result.parts) == 2 and "Сводка" in result.answer

def test_forced_specialist():
    result = asyncio.run(admin_team().run("SEO текст", "seo", access=Access(1, True)))
    assert [x.role for x in result.assignments] == ["seo"]

def test_private_group_triggers():
    assert is_mentioned("Привет @TeamTestBot!", "TeamTestBot")
    assert is_addressed("ответ", "TeamTestBot", 42, 42)
    assert is_addressed("/ask@TeamTestBot что сделать", "TeamTestBot", None, 42)
    assert not is_addressed("просто обсуждение", "TeamTestBot", None, 42)
    assert parse_direct_role("/ask marketing: оффер") == ("marketing", "оффер")

def test_journal(tmp_path: Path):
    db = TaskStore(tmp_path / "test.db")
    db.add(1, 2, "marketing,design")
    assert len(db.list_for(1,2)) == 1
    assert db.list_for(1,3) == []
    assert db.delete_for(1,2) == 1
    assert db.list_for(1,2) == []

from app.conversation import ConversationMemory

def test_private_short_context():
    mem = ConversationMemory()
    key = (15, 30)
    assert mem.context(key, "А как насчёт второго?") == "А как насчёт второго?"
    mem.add(key, "Сравни рюкзак и сумку", "Рюкзак для ноутбука, сумка для мелочей")
    followup = mem.context(key, "А для метро?")
    assert "Сравни рюкзак и сумку" in followup and "А для метро?" in followup
    mem.delete(key)
    assert mem.context(key, "А для метро?") == "А для метро?"
