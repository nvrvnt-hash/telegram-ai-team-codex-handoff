# Phase 01A

Configuration: set ADMIN_USER_IDS to comma-separated numeric Telegram user IDs
in your local .env. Empty means no administrators. HUMAN_CONTACT is an optional
contact string; no automatic ticket or message is sent. Existing .env is unchanged.

All users need explicit /consent before AI processing. /privacy explains storage
and transfer. /stop revokes consent. /delete removes the user's task metadata and
consent in SQLite across all chats, plus RAM history and rate-limit entries.
Active AI tasks for that user are cancelled; requests already sent to the provider
cannot be recalled. Logical SQLite deletion is not secure erasure of disk pages.
Telegram, provider records, technical logs and backups are outside this command.

Only ADMIN in private chat can invoke internal roles, team/tasks/chatid commands.
Allowed groups use the public consultant even for ADMIN; unrelated messages and
messages without a verified user are ignored. Public consultant receives no
internal role prompts, journal entries, tools or group conversation history.

No quotas, billing, queue capacity changes or external integrations in this phase.
