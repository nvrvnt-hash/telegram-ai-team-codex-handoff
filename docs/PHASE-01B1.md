# Load control (01B.1)

All AI requests, including direct Orchestrator.run calls, pass shared admission.
Limits are keyed by Telegram user ID across private chats and allowed groups.
FIFO waiting uses bounded Futures, without creating a background task per waiter.
At most AI_PARALLEL request pipelines run; the same limit caps model calls,
including specialist fan-out. Waiting and execution have separate timeouts.
Only admitted pipelines create up to three specialist tasks; TaskGroup cancels
siblings on failure. /stop and /delete cancel queued and active user requests.
Commands bypass AI admission and remain available when limits are reached.

Defaults (environment variables; invalid values fail startup):
- AI_PARALLEL=4
- AI_WAITING=16 (zero disables waiting)
- AI_WAIT_TIMEOUT=20 seconds
- AI_RUN_TIMEOUT=90 seconds per pipeline, including model-operation waits
- AI_USER_LIMIT=6 admitted requests per AI_USER_WINDOW=60 seconds
- AI_DUPLICATE_TTL=30 seconds for identical normalized requests and role
- AI_UPDATE_TTL=3600 seconds for Telegram update IDs (message IDs as fallback)
- AI_CACHE_LIMIT=10000 entries per protection cache; full caches reject admission

Repeated update IDs and identical requests are rejected before LLM calls.
Only hashes of request content are retained, not raw messages. Cache entries expire
on admission. Rejected requests do not consume user quota; admitted requests do,
including those later cancelled or timed out. /delete clears user rate/hash records;
transport-only update IDs remain until TTL to prevent replay after deletion.

State is local to one process and resets on restart. Not a distributed or persistent
exactly-once guarantee. Cancellation cannot recall an already-sent provider request
or guarantee that it is free. SDK retry behavior is unchanged. No billing added.
