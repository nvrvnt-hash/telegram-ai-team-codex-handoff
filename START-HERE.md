# Telegram AI Team — передача в Codex (Windows 11)

**Назначение:** комплект исходников и точных заданий для локального Codex в VS Code.
**Версия передачи:** 1.1 Token-Efficient, 30.10.2026. Это не запущенный и не настроенный на вашем ПК бот.

## Как начать
1. Скачайте архив `telegram-ai-team-codex-handoff.zip`, распакуйте папку `telegram-ai-team-codex-handoff` в, например, `C:\Projects\telegram-ai-team-codex-handoff` (или другую доступную вам папку).
2. Откройте **именно эту распакованную папку** через `File → Open Folder` в VS Code, а не отдельный `.py`.
3. Откройте расширение Codex в VS Code (ваша авторизация уже может работать). Выберите локальную рабочую папку проекта.
4. Сначала учтите `CAVEMAN-SETUP-WINDOWS.md`: установка официального Caveman **не обязательна** — проект уже содержит правила экономии. Затем отправьте фразу из `CODEX-FIRST-MESSAGE.md`; Codex должен **только провести аудит Этапа 00** и остановиться.
5. После согласования последовательно отправляйте: `Выполни этап 01 по phases/01-local-foundation.md`, затем этап 02 и т. д. Не просите сразу все этапы.
6. В терминале Windows 11 для базовой проверки используйте инструкции ниже. Секреты вводятся только вручную в локальный `.env` после проверки безопасности.

## Быстрая локальная проверка (без токенов и сети)
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt pytest
python -m pytest tests -q
```
Если `py -3.12` недоступен, попросите Codex проверить установленный Python и выбрать совместимую версию; не предлагайте переустановку без причины.

## Основные файлы
- `AGENTS.md` — короткие обязательные правила разработки для Codex.
- `TOKEN-ECONOMY.md` — сокращение входного контекста и ответов, лимиты LLM и правила проверки экономии.
- `CAVEMAN-SETUP-WINDOWS.md` — установка официального Caveman без прокси и облачной маршрутизации.
- `docs/runtime-cost-design.md` — бюджетное ТЗ для Telegram runtime (ещё не реализовано).
- `CODEX-FIRST-MESSAGE.md` — точное стартовое задание.
- `GOALS.md` — продуктовые требования, кто и зачем пользуется ботом.
- `ROADMAP.md` — план релизов и критерии завершения.
- `phases/` — ограниченные пошаговые задания и проверки.
- `CURRENT-STATE.md` — фактическое состояние полученного MVP.
- `docs/original/` — оригинальные README и архитектура v0.1.0.
- `app/`, `tests/` — существующий код и тесты, **не изменённые при сборке**.
- `.agents/skills/` — исходные OSINT и Telegram AI Team навыки.
- `OPERATIONAL-BOUNDARIES.md` — Telegram, конфиденциальность, доступы, запрет спама.

## Что точно ещё не сделано
Бот не подключён к Telegram, внешнему LLM, n8n, реальным товарам или CRM. Текущие 5 юнит-тестов не доказывают работу Telegram/API. Менеджер и роли в MVP — логическая оркестрация одного приложения, а не самостоятельные процессы на отдельных серверах.

## Справочные источники
- Telegram Bot API: https://core.telegram.org/bots/api
- Telegram Bot Features: https://core.telegram.org/bots/features
- OpenAI Codex/AGENTS: https://developers.openai.com/cookbook/examples/codex/iterating-development-workflows-with-codex
- OpenAI Skills: https://developers.openai.com/blog/skills-agents-sdk
- OSINT Library: https://tools.osintnewsletter.com/
