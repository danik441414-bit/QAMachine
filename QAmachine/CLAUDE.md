# QAmachine

Автономный QA-агент: Playwright браузер + Claude AI (Haiku) → находит баги, генерирует отчёты/тесты.

**Связанный проект:** `C:\Users\Даниил\Desktop\qamachine-saas` (SaaS-оболочка, вызывает как subprocess)

## Запуск
```bash
.venv\Scripts\activate
python main.py                                          # CLI
python run_session.py <run_id> <url> <task>            # subprocess из SaaS
.venv\Scripts\pytest generated_tests\ -v              # запуск автотестов
```

**.env:** `ANTHROPIC_API_KEY=sk-ant-...`

## Структура
```
main.py              # CLI: ввод URL+задачи, роутинг по intent
run_session.py       # Subprocess: печатает QAMACHINE_RESULT:{...} в stdout
orchestrator.py      # Главный цикл сессии
schemas.py           # Все Pydantic-модели
memory.py            # CoverageTracker + SemanticLog
context_builder.py   # DOM-инъекция qa-id + screenshot + aria
agents/
  intent_parser.py   # → Intent (BROWSER_TEST|MOBILE_TEST|GENERATE_DOCS|GENERATE_AUTOMATION)
  planner.py         # → TestMission (mode, strategy, max_steps)
  explorer.py        # LLM → NavigationDecision (action + target_id)
  judge.py           # 2-шаговая верификация багов (Evidence → Verdict)
  reporter.py        # markdown + docx отчёт
  api_tester.py      # тестирует XHR/fetch эндпоинты (макс 25, порог 2000ms)
  playwright_generator.py  # генерирует pytest-playwright .py
  doc_generator.py   # test cases / checklist / test plan
  mobile_engine.py   # device presets (iPhone/Pixel/iPad)
```

## Pipeline
`intent_parser` → `planner` → `Orchestrator.run()`:  
каждый шаг: scope check → SPA wait → `build_page_context()` → `explorer.decide()` → `judge` (параллельно) → `_execute()`  
post: reporter → docx_writer

## 9 режимов
`ui_ux`, `functional`, `specific_flow`, `all_flows`, `regression`, `network`, `api`, `load_performance`, `mobile`

## Outputs
- `reports/qa_reports/` — MD + DOCX отчёты
- `reports/qa_docs/` — тест-кейсы, чеклисты, тест-планы  
- `generated_tests/` — pytest-playwright файлы
- `ux_traces/` — скриншоты шагов (очищаются при старте)

## Нюансы
- `PRESS_KEY` использует `target_id` как название клавиши ("Escape", "Enter") — костыль
- Judge в ThreadPoolExecutor (3 параллельных LLM на шаг) — при rate limit могут быть ошибки
- `api_tester` запросы без куки → 401 для защищённых эндпоинтов — это ожидаемо
- `qa_experience.json` и `auth_state.json` — gitignored, не удалять

## Изменения (апрель 2026)
- **explorer.py**: 4-шаговый протокол, `stuck_note` (`🔴 LOOP DETECTED`), `creds_hint`, правило не Enter после TYPE
- **orchestrator.py**: `_go_to_main_streak` circuit breaker (≥5 → break), `_detect_hard_blocker()` (CAPTCHA/cloudflare/auth wall), TYPE exempt from stuck override, auth URL keywords detection
- **planner.py**: credentials_text → всегда `allow_typing=True`, любой формат логина/пароля
- **memory.py**: input/textarea не фильтруются из `clicked_element_ids`
- **run_session.py**: `QAMACHINE_ALLOWED_MODES` env var → проверка mode после planner, если запрещён → возвращает `blocked_by_plan: true` без запуска
