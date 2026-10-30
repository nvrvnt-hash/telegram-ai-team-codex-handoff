# Технический план Telegram AI-бота (n8n + API + база знаний)

## Границы
Это blueprint, не развёрнутый сервис. Требуются бот-токен от @BotFather, сервер/хостинг или n8n, LLM API, источники данных, политика приватности, согласия и идентификаторы разрешённых групп. Секреты только в Credentials/ENV.

## MVP: поток сообщения
1. Telegram webhook (или Telegram Trigger в n8n, если поддерживает нужный тип update).
2. Verify transport/authentication (где применимо `secret_token`), allowlist чатов, дедупликация update_id.
3. Route: DM / разрешённая группа / Guest Mode; проверить команды и триггер (`@mention`, reply, `/ask`, guest_query), и права.
4. Проверить действующее согласие и статус /stop, /delete, /human.
5. Sanitise input: ограничить длину, исключить секреты и опасные вложения; отделить текст пользователя от системных инструкций.
6. Intent classifier (FAQ, product, human, other); подобрать минимальные подтверждённые записи собственной базы.
7. LLM output → факт-чек по базе и бизнес-правилам (без придуманных характеристик).
8. Format → sendMessage / answerGuestQuery (соответственно режиму), rate limits, retry_after, логирование факта ответа.
9. Feedback → агрегированная отчётность; эскалация специалисту с согласием.

## Сущности данных (минимум)
- `chat_config(chat_id, type, enabled, admin_approved_at, triggers, privacy_mode_note)`
- `consent(chat_id, user_id, purpose, status, updated_at, expires_at)`
- `knowledge_items(id, scope, source, verified_at, expires_at, text, product_id)`
- `processed_updates(update_id, processed_at, outcome)` (TTL ограничен)
- `handoff_tickets(id, chat_id, status, created_at, consent_record)`
- `operational_metrics(day, permitted_responses, errors, handoffs, optouts)`
Исключить массовую таблицу `all_group_messages`.

## Конфигурация
См. `assets/telegram-bot-config.example.yaml`. Настройки демонстрационные: никаких реальных токенов и адресов. Для продакшна — backend в приватном окружении, валидируемые webhook updates, разграничение прав, бэкапы минимально необходимой БД.

## Важные технические нюансы
- Guest Mode (2026): отдельные update и метод `answerGuestQuery`; не путать с обычным `sendMessage` в группе.
- `setWebhook` и `getUpdates` несовместимы при одновременно установленном webhook.
- Обрабатывать любые повторные доставки (`update_id`), timeouts, 429 с `retry_after`.
- Отсечь циклы при общении с другими ботами, даже если Bot-to-Bot Communication Mode подключён.
- Долгая история чужих чатов через Bot API недоступна; не проектировать функцию «пройти по всем группам».
- GPT/LLM-интеграция — отдельный процессор входящих добровольно предоставленных сообщений, не сбор данных для обучения модели или построения внешнего индексатора Telegram.

## Тест-план
- Бот в DM приветствует, проверяет согласие и отвечает на FAQ.
- Группе без разрешения молчит; в разрешённой группе без @упоминания молчит.
- На @упоминание отвечает один раз, без самовольных ссылок.
- Guest Mode: входящий вызов без членства отрабатывается ровно один раз при поддержке.
- /stop и /delete работают, у менеджера /quiet и kill switch.
- Запрос без данных о цене/наличии → не фантазирует.
- Внедрение инструкции в пользовательском сообщении («игнорируй правила») → игнорирует.
- 429/повторы/отказ Telegram → корректный retry без дубликата.

## Документация
https://core.telegram.org/bots/api
https://core.telegram.org/bots/features
https://telegram.org/tos/bot-developers
