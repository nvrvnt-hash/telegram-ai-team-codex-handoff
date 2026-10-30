"""Least-privilege Telegram group entrypoints."""
import re

def is_mentioned(text: str, username: str) -> bool:
    if not username:
        return False
    return re.search(r"(?<![\w@])@" + re.escape(username) + r"\b", text, re.I) is not None

def is_addressed(text: str, username: str, reply_user_id: int | None, bot_id: int) -> bool:
    if reply_user_id is not None and reply_user_id == bot_id:
        return True
    if is_mentioned(text, username):
        return True
    return re.match(r"^/(?:start|help|team|roles|ask|tasks|task)(?:@" + re.escape(username) + r")?(?:\s|$)", text, re.I) is not None

def parse_direct_role(text: str) -> tuple[str | None, str]:
    # Example: /ask marketing: Составь оффер
    # Or: /ask seo ключевые слова
    s = re.sub(r"^/ask(?:@\w+)?\s*", "", text, flags=re.I).strip()
    parts = s.split(maxsplit=1)
    if parts:
        role = parts[0].rstrip(":").casefold()
        if role in {"marketing","design","analytics","seo","content","support","research"}:
            return role, parts[1].strip() if len(parts) > 1 else ""
    return None, s
