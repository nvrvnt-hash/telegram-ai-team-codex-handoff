"""Offline-testable access-controlled Telegram handler."""
import asyncio
import re
from .load_control import LoadRejected
from .access import Access
from .roles import ROLES
from .security import is_mentioned, parse_direct_role

PRIVACY = (
    "Я AI-помощник. После явного /consent запросы передаются OpenAI. В личном чате "
    "передаются также до 3 предыдущих пар вопросов и ответов. История хранится в RAM "
    "и используется до 30 минут; SQLite хранит Telegram ID, метаданные задач и согласие. "
    "/stop отзывает согласие без удаления истории; /delete удаляет записи пользователя "
    "из активной базы, память и согласие во всех чатах. Данные Telegram, AI-провайдера, "
    "технические журналы, резервные копии и физические остатки SQLite этим не очищаются. "
    "Не присылайте секреты. Для согласия отправьте /consent. /human — связь с человеком."
)


class MessageHandler:
    def __init__(self, team, store, memory, policy, groups=(), username="", bot_id=0, human=""):
        self.team, self.store, self.memory, self.policy = team, store, memory, policy
        self.groups, self.username, self.bot_id, self.human = set(groups), username, bot_id, human

    async def __call__(self, m, event_update=None):
        user = m.from_user
        if user is None or user.is_bot or getattr(m, "sender_chat", None) or not m.text:
            return
        private, text = m.chat.type == "private", m.text.strip()
        match = re.match(r"^/([a-zA-Z_]+)(?:@([\w]+))?(?=\s|$)", text)
        if match and match[2] and match[2].casefold() != self.username.casefold():
            return
        if not private:
            reply = m.reply_to_message
            addressed = bool(match) or is_mentioned(text, self.username) or (
                reply and reply.from_user and reply.from_user.id == self.bot_id)
            if m.chat.id not in self.groups or not addressed:
                return
        uid, access = user.id, Access(user.id, private)
        cmd = match[1].lower() if match else None
        if cmd in {"start", "help", "privacy"}:
            await m.answer(PRIVACY)
            return
        if cmd == "consent":
            self.store.set_consent(uid, True)
            await m.answer("Согласие на передачу сообщений OpenAI сохранено. Отзыв: /stop.")
            return
        if cmd in {"stop", "delete"}:
            self.team.load.cancel_user(uid)
            try:
                if cmd == "stop":
                    self.store.set_consent(uid, False)
                    response = "Согласие отозвано. AI отключён. История не удалена."
                else:
                    self.store.delete_user(uid)
                    self.memory.delete_user(uid)
                    self.team.load.delete_user(uid)
                    response = ("Записи пользователя в активной базе, память и согласие удалены. "
                                "Для AI требуется /consent. Telegram, AI-провайдер, журналы, "
                                "резервные копии и физические остатки SQLite не очищены.")
            except Exception:
                await m.answer("Операция не завершена. Успех удаления или отзыва не подтверждён. /human")
                return
            await m.answer(response)
            return
        if cmd == "human":
            await m.answer(f"Связь с человеком: {self.human}" if self.human else "Маршрут связи не настроен. Обращение не передано.")
            return
        if cmd in {"tasks", "team", "roles", "chatid"}:
            if not self.policy.internal(access):
                await m.answer("Служебные команды доступны ADMIN только в личном чате.")
                return
            if cmd == "tasks":
                rows = self.store.list_for(m.chat.id, uid)
                await m.answer("\n".join(f"#{i} | {roles} | {status} | {date}" for i, roles, status, date in rows) or "Задач пока нет.")
            elif cmd == "chatid":
                await m.answer(f"ID личного чата: {m.chat.id}")
            else:
                await m.answer("\n".join(f"{k}: {r.title}" for k, r in ROLES.items()))
            return
        if text.startswith("/") and cmd != "ask":
            await m.answer("Неизвестная команда. /help")
            return
        force, query = parse_direct_role(text) if cmd == "ask" else (None, text)
        if force and not self.policy.internal(access):
            await m.answer("Доступ к внутренним ролям запрещён.")
            return
        if self.username:
            query = re.sub(r"@" + re.escape(self.username) + r"\b", "", query, flags=re.I).strip()
        try:
            self.policy.require(access)
        except PermissionError:
            await m.answer(PRIVACY)
            return
        if not query or len(query) > 2500:
            await m.answer("Введите запрос длиной от 1 до 2500 символов.")
            return
        key = (m.chat.id, uid)
        update_id = getattr(event_update, "update_id", None)
        message_id = getattr(m, "message_id", None)
        update_key = ("update", update_id) if update_id is not None else (
            ("message", m.chat.id, message_id) if message_id is not None else None)
        try:
            full = self.memory.context(key, query) if private else query
            result = await self.team.run(full, force, access=access, update_key=update_key, request_text=query)
            self.policy.require(access)
            self.store.add(m.chat.id, uid, ",".join(a.role for a in result.assignments) or "public")
            if private:
                self.memory.add(key, query, result.answer)
            for start in range(0, len(result.answer), 3800):
                self.policy.require(access)
                await m.answer(result.answer[start:start + 3800])
        except asyncio.CancelledError:
            if self.store.has_consent(uid):
                raise
        except LoadRejected as error:
            await m.answer(str(error))
        except TimeoutError:
            await m.answer("Время ожидания или выполнения истекло. Повторите позднее.")
        except Exception:
            await m.answer("Не удалось обработать запрос. /human")
