"""Trusted identity and live consent checks; never derived from message text."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Access:
    user_id: int
    private: bool


class AccessPolicy:
    def __init__(self, store, admin_ids=()):
        self.store = store
        self.admin_ids = frozenset(admin_ids)

    def internal(self, access):
        return access.private and access.user_id in self.admin_ids

    def require(self, access, internal=False):
        if access is None or not self.store.has_consent(access.user_id):
            raise PermissionError("Consent required")
        if internal and not self.internal(access):
            raise PermissionError("Internal access denied")
