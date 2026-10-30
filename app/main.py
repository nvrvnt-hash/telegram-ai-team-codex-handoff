"""Telegram polling composition; importing does not load secrets."""
import asyncio
import os
from aiogram import Bot, Dispatcher, F
from dotenv import load_dotenv
from openai import AsyncOpenAI
from .access import AccessPolicy
from .handlers import MessageHandler
from .orchestrator import OpenAIModel, Orchestrator
from .task_store import TaskStore
from .conversation import ConversationMemory
from .load_control import LoadConfig, LoadControl


async def start():
    load_dotenv()
    token, api_key = os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("OPENAI_API_KEY", "")
    if not token or not api_key:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN and OPENAI_API_KEY in .env")
    admins = {int(v.strip()) for v in os.getenv("ADMIN_USER_IDS", "").split(",") if v.strip()}
    groups = {int(v.strip()) for v in os.getenv("ALLOWED_GROUP_IDS", "").split(",") if v.strip()}
    bot = Bot(token=token)
    llm = AsyncOpenAI(api_key=api_key, timeout=35, max_retries=1)
    try:
        store = TaskStore(os.getenv("TASK_DB", "./data/tasks.sqlite3"))
        policy = AccessPolicy(store, admins)
        defaults = LoadConfig()
        config = LoadConfig(**{name: type(getattr(defaults, name))(os.getenv("AI_" + name.upper(), getattr(defaults, name)))
                               for name in defaults.__dataclass_fields__})
        team = Orchestrator(OpenAIModel(llm, os.getenv("OPENAI_MODEL", "gpt-5.5")), policy, LoadControl(config))
        me = await bot.get_me()
        handler = MessageHandler(team, store, ConversationMemory(), policy, groups,
                                 me.username or "", me.id, os.getenv("HUMAN_CONTACT", ""))
        dp = Dispatcher()
        dp.message.register(handler.__call__, F.text)
        await dp.start_polling(bot, allowed_updates=["message"])
    finally:
        await llm.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(start())
