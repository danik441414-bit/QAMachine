# QAmachine — AI-Powered QA SaaS Platform

![Next.js](https://img.shields.io/badge/Next.js-14-black?style=flat-square&logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

A full-stack SaaS platform that wraps a senior-level AI QA agent into a chat-based web interface. Users describe what to test — QAmachine autonomously browses the site, finds bugs, and delivers structured reports.

---

## Features

- **AI QA Agent** — autonomous browser testing powered by Claude + Playwright
- **Chat Interface** — send a URL and task, get a full QA report in real time
- **Streaming Results** — live run status via Server-Sent Events
- **Auth System** — JWT-based registration, login, protected routes
- **Dashboard** — run history, issue counts, report downloads
- **Billing Ready** — Stripe integration structure in place
- **Multiple Test Modes** — UI/UX audit, functional, regression, API, mobile emulation, performance

---

## Tech Stack

| Layer     | Technology                                          |
|-----------|-----------------------------------------------------|
| Frontend  | Next.js 14 (App Router), TypeScript, Tailwind CSS   |
| Backend   | FastAPI, SQLAlchemy 2.0 (async), Aiosqlite          |
| AI Engine | Claude (Anthropic), LangChain, Playwright           |
| Auth      | JWT + bcrypt                                        |
| Realtime  | Server-Sent Events                                  |
| Billing   | Stripe                                              |
| DB        | SQLite (dev) / PostgreSQL (prod)                    |

---

## Project Structure

```
├── QAmachine/               # AI QA engine (CLI + agent core)
│   ├── agents/              # intent_parser, planner, explorer, judge, reporter...
│   ├── orchestrator.py      # main agent loop
│   └── main.py              # CLI entry point
│
└── qamachine-saas/          # SaaS web platform
    ├── frontend/
    │   └── src/
    │       ├── app/
    │       │   ├── (landing)/       # Landing page
    │       │   ├── (auth)/          # Login / Signup
    │       │   └── (app)/           # Protected: dashboard, chats, billing, settings
    │       ├── components/
    │       │   ├── ui/              # Button, Input, Card, Badge
    │       │   ├── layout/          # Sidebar, Topbar
    │       │   └── chat/            # ChatInput, MessageBubble, RunResult
    │       └── lib/api.ts           # Typed API client
    │
    └── backend/
        └── app/
            ├── api/v1/              # auth, users, chats, runs, billing, dashboard
            ├── models/              # User, Chat, Message, Run, Subscription
            ├── services/            # MachineRunner (background task)
            └── machine/engine.py   # QAmachine integration point
```

---

## How It Works

1. User submits a URL + task description in the chat
2. Backend creates a `Run` and starts `MachineRunner` as a background task
3. The AI agent (Claude + Playwright) autonomously navigates the site
4. Steps and findings stream back to the UI via SSE
5. On completion, a structured report is saved and displayed

---

## Quick Start

### Backend

```bash
cd qamachine-saas/backend
python -m venv .venv
source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`

### Frontend

```bash
cd qamachine-saas/frontend
npm install
npm run dev
```

Open `http://localhost:3000`

---

## Author

Built by **Danil** — [GitHub](https://github.com/danik441414-bit)
