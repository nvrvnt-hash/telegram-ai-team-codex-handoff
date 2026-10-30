import asyncio
from dataclasses import replace
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import pytest
from app.load_control import LoadControl, LoadConfig, LoadRejected
from app.access import Access, AccessPolicy
from app.orchestrator import Orchestrator
from app.handlers import MessageHandler
from app.conversation import ConversationMemory
from app.task_store import TaskStore


def test_bounded_fifo_and_overflow():
    async def scenario():
        load = LoadControl(LoadConfig(parallel=1, waiting=1))
        entered, release = asyncio.Event(), asyncio.Event()
        order = []
        async def work(uid):
            async with load.slot(uid, str(uid)):
                order.append(uid)
                entered.set()
                await release.wait()
        first = asyncio.create_task(work(1))
        await entered.wait()
        second = asyncio.create_task(work(2))
        await asyncio.sleep(0)
        with pytest.raises(LoadRejected, match="заполнена"):
            await work(3)
        assert load.running == 1 and len(load.waiters) == 1
        release.set()
        await asyncio.gather(first, second)
        assert order == [1, 2] and load.running == 0 and not load.waiters
    asyncio.run(scenario())


def test_wait_timeout_and_cancel_free_capacity():
    async def scenario():
        load = LoadControl(LoadConfig(parallel=1, waiting=1, wait_timeout=.02))
        async with load.slot(1, "one"):
            with pytest.raises(TimeoutError):
                async with load.slot(2, "two"):
                    pytest.fail("waiting request ran")
            assert not load.waiters
            async def pending():
                async with load.slot(3, "three"):
                    pytest.fail("cancelled request ran")
            job = asyncio.create_task(pending())
            await asyncio.sleep(0)
            load.cancel_user(3)
            with pytest.raises(asyncio.CancelledError):
                await job
            assert not load.waiters and load.running == 1
        assert load.running == 0 and not load.tasks
    asyncio.run(scenario())


def test_execution_timeout_releases_slot():
    async def scenario():
        load = LoadControl(LoadConfig(parallel=1, run_timeout=.02))
        with pytest.raises(TimeoutError):
            async with load.slot(1, "test"):
                await asyncio.Event().wait()
        async with load.slot(2, "next"):
            assert load.running == 1
        assert not load.tasks and load.running == 0
    asyncio.run(scenario())


def test_user_limit_duplicates_and_expiry():
    now = [0.0]
    load = LoadControl(LoadConfig(user_limit=2), clock=lambda: now[0])
    load.check(1, "hello", None, ("update", 10))
    with pytest.raises(LoadRejected, match="update"):
        load.check(2, "different", None, ("update", 10))
    with pytest.raises(LoadRejected, match="одинаковый"):
        load.check(1, "hello", None, None)
    load.check(1, "second", None, None)
    with pytest.raises(LoadRejected, match="Лимит"):
        load.check(1, "third", None, None)
    now[0] = 3601
    load.check(1, "hello", None, ("update", 10))


@pytest.mark.parametrize("changes", [{"parallel": 0}, {"waiting": -1}, {"run_timeout": float("nan")}, {"user_limit": 0}])
def test_invalid_config(changes):
    with pytest.raises(ValueError):
        replace(LoadConfig(), **changes)


def build(tmp_path, config):
    store = TaskStore(tmp_path / "load.db")
    for uid in (1, 2, 3):
        store.set_consent(uid, True)
    model = NS(text=AsyncMock(return_value="ok"), plan=AsyncMock())
    policy = AccessPolicy(store)
    team = Orchestrator(model, policy, LoadControl(config))
    handler = MessageHandler(team, store, ConversationMemory(), policy, {-10}, "TestBot", 99)
    return store, model, team, handler


def message(text, uid=1, private=True):
    return NS(text=text, from_user=NS(id=uid, is_bot=False), sender_chat=None,
              chat=NS(id=uid if private else -10, type="private" if private else "group"),
              reply_to_message=None, answer=AsyncMock())


def test_repeated_update_and_cross_chat_limit(tmp_path):
    async def scenario():
        store, model, team, handler = build(tmp_path, LoadConfig(user_limit=1))
        await handler(message("first"), NS(update_id=100))
        await handler(message("different", uid=2), NS(update_id=100))
        await handler(message("/ask other", private=False), NS(update_id=101))
        with pytest.raises(LoadRejected):
            await team.run("direct bypass", access=Access(1, True))
        assert model.text.await_count == 1
        for cmd in ("/privacy", "/stop", "/delete"):
            m = message(cmd)
            await handler(m)
            m.answer.assert_awaited_once()
        assert not store.has_consent(1)
    asyncio.run(scenario())


def test_stop_queued_and_overflow_zero_llm(tmp_path):
    async def scenario():
        store, model, team, handler = build(tmp_path, LoadConfig(parallel=1, waiting=1))
        entered, release = asyncio.Event(), asyncio.Event()
        async def slow(*args):
            entered.set()
            await release.wait()
            return "ok"
        model.text.side_effect = slow
        first = asyncio.create_task(handler(message("first", uid=1)))
        await entered.wait()
        second = asyncio.create_task(handler(message("second", uid=2)))
        await asyncio.sleep(0)
        rejected = message("third", uid=3)
        await handler(rejected)
        assert "заполнена" in rejected.answer.call_args.args[0]
        await handler(message("/stop", uid=2))
        await second
        assert not team.load.waiters
        release.set()
        await first
        assert model.text.await_count == 1
        assert not team.load.tasks and team.load.running == 0
        assert store.list_for(2, 2) == []
    asyncio.run(scenario())


def test_parallel_call_limit(tmp_path):
    async def scenario():
        _, model, team, _ = build(tmp_path, LoadConfig(parallel=2))
        active, peak = 0, 0
        release = asyncio.Event()
        async def slow(*args):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            try:
                await release.wait()
                return "ok"
            finally:
                active -= 1
        model.text.side_effect = slow
        jobs = [asyncio.create_task(team.run(str(uid), access=Access(uid, True))) for uid in (1, 2, 3)]
        for _ in range(5):
            await asyncio.sleep(0)
        assert peak == 2 and len(team.load.waiters) == 1
        release.set()
        await asyncio.gather(*jobs)
        assert peak == 2 and not team.load.tasks
    asyncio.run(scenario())
