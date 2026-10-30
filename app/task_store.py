"""Minimal task journal. No raw messages, personal names, or AI outputs are saved."""
import sqlite3
from pathlib import Path

class TaskStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL, roles TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            c.execute("CREATE TABLE IF NOT EXISTS consents (user_id INTEGER PRIMARY KEY, accepted INTEGER NOT NULL)")

    def has_consent(self, user_id):
        with self.conn() as c:
            row = c.execute("SELECT accepted FROM consents WHERE user_id=?", (user_id,)).fetchone()
            return bool(row and row[0])

    def set_consent(self, user_id, accepted):
        with self.conn() as c:
            c.execute("INSERT OR REPLACE INTO consents(user_id,accepted) VALUES(?,?)", (user_id, int(accepted)))

    def delete_user(self, user_id):
        with self.conn() as c:
            c.execute("DELETE FROM tasks WHERE user_id=?", (user_id,))
            c.execute("DELETE FROM consents WHERE user_id=?", (user_id,))

    def conn(self):
        return sqlite3.connect(self.path)

    def add(self, chat_id: int, user_id: int, roles: str, status: str = "done") -> int:
        with self.conn() as c:
            cur = c.execute("INSERT INTO tasks(chat_id,user_id,roles,status) VALUES(?,?,?,?)",(chat_id,user_id,roles,status))
            return cur.lastrowid

    def list_for(self, chat_id: int, user_id: int, limit: int = 10):
        with self.conn() as c:
            return c.execute("SELECT id,roles,status,created_at FROM tasks WHERE chat_id=? AND user_id=? ORDER BY id DESC LIMIT ?",(chat_id,user_id,limit)).fetchall()

    def delete_for(self, chat_id: int, user_id: int) -> int:
        with self.conn() as c:
            return c.execute("DELETE FROM tasks WHERE chat_id=? AND user_id=?",(chat_id,user_id)).rowcount
