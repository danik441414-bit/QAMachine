# QAmachine SaaS

**Stack:** Next.js 14 + FastAPI + SQLAlchemy async + PostgreSQL (Supabase prod) / SQLite (dev)
**Paths:** frontend `C:\...\qamachine-saas\frontend` | backend `C:\...\qamachine-saas\backend`
**QA engine:** `C:\Users\Даниил\Desktop\QAmachine` (subprocess via run_session.py)

## Запуск (локально)
```bash
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev   # http://localhost:3000
```

---

## VPS (qamachine.site)
- **IP:** 46.225.28.29, Ubuntu, root пользователь
- **Репозиторий:** `/root/repo` (содержит и QAmachine и qamachine-saas как подпапки)
- **Database:** PostgreSQL на Supabase (DATABASE_URL в .env)
- **Python venv:** `/root/repo/qamachine-saas/backend/.venv`

### Два systemd сервиса:

**`qamachine-api.service`** — FastAPI бэкенд
- WorkingDirectory: `/root/repo/qamachine-saas/backend`
- ExecStart: `.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2`
- EnvironmentFile: `/root/repo/qamachine-saas/backend/.env`

**`qamachine-frontend.service`** — Next.js фронтенд
- WorkingDirectory: `/root/repo/qamachine-saas/frontend`
- ExecStart: `npm start -- -p 3000`
- Фронт работает на порту 3000

### Nginx (`/etc/nginx/sites-enabled/qamachine`)
```
/api/v1/  →  proxy_pass http://127.0.0.1:8000   (FastAPI)
/         →  proxy_pass http://127.0.0.1:3000   (Next.js)
```
Next.js сам проксирует `/api/v1/*` на бэкенд через `next.config.mjs` rewrites (для dev).
На проде — nginx делает это напрямую.

### .env бэкенда на VPS (`/root/repo/qamachine-saas/backend/.env`):
Хранится ТОЛЬКО на сервере, никогда не коммитится в git.
```
DEBUG=false
SECRET_KEY=<generate: openssl rand -hex 32>
DATABASE_URL=postgresql+asyncpg://postgres:<password>@db.<project>.supabase.co:5432/postgres
CORS_ORIGINS=["https://qamachine.site","https://www.qamachine.site","http://46.225.28.29"]
FRONTEND_URL=https://qamachine.site
ANTHROPIC_API_KEY=sk-ant-<your-key>
QAMACHINE_DIR=/root/repo/QAmachine
QAMACHINE_PYTHON=/root/repo/QAmachine/.venv/bin/python
QAMACHINE_RUNNER=/root/repo/QAmachine/run_session.py
RESEND_API_KEY=re_<your-key>
NOWPAYMENTS_API_KEY=<your-key>
NOWPAYMENTS_IPN_SECRET=<your-secret>
DODO_API_KEY=<your-key>
DODO_WEBHOOK_SECRET=whsec_<your-secret>
DODO_PRODUCT_PRO=pdt_<product-id>
DODO_PRODUCT_TEAM=pdt_<product-id>
DODO_ENV=test
ADMIN_EMAILS=["your@email.com"]
GOOGLE_CLIENT_ID=<your-google-client-id>
```

---

## Деплой на VPS

```bash
# Только бэкенд (быстро):
cd /root/repo/qamachine-saas && git pull && systemctl restart qamachine-api

# Бэкенд + фронтенд (если менялись файлы в frontend/):
cd /root/repo/qamachine-saas && git pull
cd frontend && npm run build
systemctl restart qamachine-frontend qamachine-api

# Проверка статуса:
systemctl status qamachine-api qamachine-frontend --no-pager

# Логи:
journalctl -u qamachine-api -f --no-pager
journalctl -u qamachine-frontend -f --no-pager
```

**ВАЖНО:** Сначала `git push` локально на Windows, потом `git pull` на VPS.

---

## Платёжные сервисы

### 1. Dodo Payments (карта) — ОСНОВНОЙ
- **Сайт:** app.dodopayments.com
- **API test:** `https://test.dodopayments.com`
- **API live:** `https://live.dodopayments.com`
- **Эндпоинт:** `POST /billing/checkout/card`
- **Webhook:** `POST /billing/webhook/dodo`
- **Webhook URL:** `https://qamachine.site/api/v1/billing/webhook/dodo`
- **Комиссия:** ~3.9% + $0.39
- **Статус:** Test mode (DODO_ENV=test)

### 2. NOWPayments (крипто USDT)
- **Сайт:** nowpayments.io
- **Эндпоинт:** `POST /billing/checkout/crypto`
- **Webhook:** `POST /billing/webhook/crypto` (HMAC-SHA512)
- **Выплата:** USDT TRC20 → Binance кошелёк
- **Комиссия:** ~1%

### 3. Stripe — НЕ ИСПОЛЬЗУЕТСЯ
- Украина не поддерживается как страна продавца

---

## UX флоу оплаты
1. `/billing` → одна кнопка "Улучшить Pro/Team" на каждый план
2. → редирект на `/billing/checkout/[plan]`
3. → выбор: **Bank Card** (Dodo Payments) или **Crypto USDT** (NOWPayments)
4. → "Continue to payment" → внешний чекаут
5. → после оплаты: редирект на `/billing?success=1`
6. → вебхук активирует план в БД

---

## Auth методы
1. **Email + пароль** — стандартная регистрация с верификацией письма (Resend)
2. **Google OAuth** — `POST /auth/google`, id_token верификация, `GOOGLE_CLIENT_ID` в .env
3. **Magic link** — `POST /auth/magic-link`, письмо со ссылкой (15 мин), авторегистрация

---

## Интернационализация (i18n)

**4 языка:** EN | RU | UK (Українська) | ES (Español)

- **Переводы:** `frontend/src/lib/i18n.ts`
- **Контекст:** `frontend/src/context/language-context.tsx`
- **Переключатель:** Настройки → 4 кнопки EN / RU / UA / ES
- **Автодетект:** backend `/locale/detect` по IP → fallback browser lang

---

## Тарифы и лимиты
| Plan | Price | Runs | Chats | Tutor | Modes |
|------|-------|------|-------|-------|-------|
| Free | $0 | 3 | 1 | 20 msg | Functional + UI/UX only |
| Pro | $29 | 50 | ∞ | ∞ | All 9 |
| Team | $79 | 200 | ∞ | ∞ | All 9 |

---

## Ключевые файлы
| Файл | Что делает |
|------|-----------|
| `backend/app/core/config.py` | Все настройки: лимиты, ключи оплаты, DODO_ENV, ADMIN_EMAILS |
| `backend/app/api/v1/billing.py` | NOWPayments + Dodo + вебхуки |
| `backend/app/api/v1/auth.py` | Email/pass + Google OAuth + Magic link |
| `backend/app/api/v1/chats.py` | CRUD чатов + лимиты + запуск Machine |
| `backend/app/models/user.py` | User: plan, credits, google_id, magic_token |
| `frontend/src/lib/i18n.ts` | Переводы EN/RU/UK/ES |
| `frontend/src/lib/api.ts` | Axios client + все API методы |

---

## Модели БД
`users`, `chats`, `messages`, `runs`, `subscriptions`, `page_views`, `payments`

---

## TODO
- [ ] **Dodo:** перейти test → live (верификация в дашборде)
- [ ] **NOWPayments:** перегенерировать ключи
- [ ] Monthly reset credits (нет cron)
- [ ] Email уведомления о завершении Run
