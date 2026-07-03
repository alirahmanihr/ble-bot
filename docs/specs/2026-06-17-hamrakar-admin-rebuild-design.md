# Hamrakar Admin Panel — Design Spec

**Date:** 2026-06-17
**Status:** Approved
**Version:** 2.0 (Complete Rebuild)

---

## 1. Overview

Complete rebuild of the Hamrakar admin panel as a clean, modern web application. Replaces the bloated `hamrakar-bot-simulator` with a focused admin tool that connects directly to the production Bale bot running on Railway.

### Goals
- Admin panel auto-connects to Railway backend on startup
- All admin actions (approve/reject jobs, applications) affect the real bot
- Phone Simulator sends and receives real messages from the Bale bot
- No simulated data — everything is live
- Runs on desktop via browser (potential PWA install later)

### Non-Goals
- Public-facing features (this is internal admin tool)
- Multi-user auth (single admin)
- Mobile support (desktop-first)
- Electron/Tauri wrapper (browser is sufficient)

---

## 2. Architecture

### 2.1 Project Structure (pnpm Monorepo)

```
untitled1/
├── apps/
│   ├── web/              # React 19 + Vite 6 + TailwindCSS 4
│   │   ├── src/
│   │   │   ├── App.tsx           # Main app with tab switching
│   │   │   ├── api.ts            # API client (calls proxy)
│   │   │   ├── components/
│   │   │   │   ├── AdminPanel/   # Job/application/user management
│   │   │   │   ├── PhoneSimulator/ # Bale chat simulator
│   │   │   │   └── ui/          # Shared UI components
│   │   │   └── hooks/           # SWR hooks for data fetching
│   │   ├── index.html
│   │   ├── vite.config.ts
│   │   └── package.json
│   │
│   └── proxy/            # Express.js proxy server
│       ├── src/
│       │   ├── index.ts         # Express server entry
│       │   ├── routes/
│       │   │   ├── admin.ts     # /api/admin/* → Railway
│       │   │   └── bale.ts      # /api/bale/* → Bale API
│       │   └── middleware/
│       │       └── auth.ts      # Admin token validation
│       ├── package.json
│       └── tsconfig.json
│
├── packages/
│   └── shared/           # Shared TypeScript types
│       ├── src/
│       │   └── types.ts         # User, Job, Application, etc.
│       └── package.json
│
├── pnpm-workspace.yaml
├── .env                    # ADMIN_TOKEN, BALE_BOT_TOKEN, RAILWAY_API_URL
├── .env.example
└── .gitignore
```

### 2.2 Data Flow

```
Browser (React App)
    │
    │  GET/POST /api/admin/*  (with X-Admin-Token header)
    ▼
Express Proxy (localhost:3001)
    │
    ├── /api/admin/*  ──►  Railway FastAPI (astonishing-respect-production-2505.up.railway.app)
    │                        Authenticated with X-Admin-Token
    │
    └── /api/bale/*   ──►  Bale API (tapi.bale.ai/bot<TOKEN>/)
                             Uses BOT_TOKEN from .env
```

- **Browser never sees BOT_TOKEN or ADMIN_TOKEN** — they stay in proxy's `.env`
- **Proxy validates every request** with `X-Admin-Token` header
- **Railway API also validates** the same token (added to `api_server.py`)

### 2.3 Phone Simulator Architecture

**Problem:** Bale uses long-polling — if the simulator polls directly, the production bot misses updates.

**Solution:** Log-based message relay.

1. **Modify `bale-bot` on Railway:** Add a `messages` table to SQLite. Log every incoming and outgoing message with `chat_id`, `direction`, `text`, `timestamp`.

2. **Add Railway endpoint:** `GET /admin/messages?chat_id=X&after_id=Y` returns recent messages for a chat.

3. **To send a message from simulator:**
   - Browser → `POST /api/bale/sendMessage` → Proxy → Bale API `sendMessage` endpoint
   - Bot receives the message normally via its own long-polling
   - Bot processes it and responds
   - Bot logs both the incoming (from admin) and outgoing (bot reply) messages to the `messages` table

4. **To receive messages in simulator:**
   - Simulator polls `GET /api/admin/messages?chat_id=<ADMIN_CHAT_ID>&after_id=<last_seen_id>` every 2 seconds
   - New messages appear in the chat UI

```
Admin sends "سلام" in Phone Simulator
    │
    ▼
POST /api/bale/sendMessage  (proxy → Bale API)
    │
    ▼
Bale delivers to bot's long-polling
    │
    ▼
Bot processes "سلام", responds "سلام! چطور میتونم کمک کنم؟"
    │
    ▼
Bot logs to messages table: [dir=in, text=سلام], [dir=out, text=سلام!...]
    │
    ▼
Simulator's 2s polling picks up both messages
    │
    ▼
UI shows the conversation
```

### 2.4 Database Changes on Railway

**New table in `database.py`:**

```sql
CREATE TABLE IF NOT EXISTS messages (
    msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('in', 'out')),
    text TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
```

**Changes to `bot.py`:**
- After receiving a message: `await db.log_message(cid, 'in', text)`
- After sending a message: `await db.log_message(cid, 'out', text)`

**New API endpoint in `api_server.py`:**
- `GET /admin/messages?chat_id=X&after_id=Y&limit=20`
- Requires `X-Admin-Token` validation

**Auth middleware for `api_server.py`:**
- Check `X-Admin-Token` header on all `/admin/*` and mutation endpoints
- Reject with 401 if missing or invalid

---

## 3. Frontend Design

### 3.1 Tech Stack
- **React 19** with hooks, no class components
- **Vite 6** for dev server and build
- **TailwindCSS 4** for styling (dark theme)
- **SWR** for data fetching and auto-refresh
- **Lucide React** for icons
- **motion** (Framer Motion) for subtle animations
- **Recharts** for statistics charts

### 3.2 Views (Tab-Based, No Router)

**Tab 1: Admin Console** — The main work area
- **Stats Cards:** Total users, employers, job-seekers, active jobs, pending items — with trend indicators
- **Pending Jobs:** List of jobs awaiting approval with title, company, category, salary. Approve/Reject buttons with optional reason for rejection.
- **Pending Applications:** List of resumes awaiting approval with seeker name, job title. Approve/Reject.
- **Users Table:** Searchable, filterable table of all users with role, name, phone, province.
- **Broadcast Panel:** Send message to all users, filtered by role and/or category.
- **Settings:** Edit welcome text, bot menus.

**Tab 2: Phone Simulator** — Real Bale chat simulation
- **Phone frame UI** resembling Bale messenger (RTL, Persian)
- **User selector:** Choose which chat_id to simulate (admin's own ID is default)
- **Chat view:** Scrollable message list with incoming (left) and outgoing (right) bubbles
- **Message input:** Text input with send button — sends through proxy to Bale
- **Auto-scroll** to latest message
- **Loading indicator** while waiting for bot response

### 3.3 Component Tree

```
App
├── Header (logo, tab switcher, connection status indicator)
├── [Tab 1] AdminPanel
│   ├── StatsGrid (4 stats cards)
│   ├── PendingSection
│   │   ├── PendingJobsTable (with approve/reject)
│   │   └── PendingApplicationsTable (with approve/reject)
│   ├── UsersTable (search, filter, delete)
│   ├── BroadcastPanel
│   └── SettingsPanel (welcome text, menus)
│
└── [Tab 2] PhoneSimulator
    ├── ChatSelector (choose active chat_id)
    ├── ChatMessages (message list)
    └── ChatInput (text field + send button)
```

### 3.4 Data Fetching Pattern

```typescript
// Example: Pending jobs with SWR auto-refresh
const { data: jobs, error, mutate } = useSWR(
  '/api/admin/jobs/pending',
  fetcher,
  { refreshInterval: 3000 }
);

// Example: Phone simulator messages polling
const { data: messages } = useSWR(
  `/api/admin/messages?chat_id=${chatId}&after_id=${lastId}`,
  fetcher,
  { refreshInterval: 2000 }
);
```

### 3.5 States

Every data-dependent component handles:
- **Loading:** Skeleton/spinner shown during initial fetch
- **Empty:** Friendly "nothing to show" message with icon
- **Error:** Error message with retry button
- **Success:** Data rendered normally

---

## 4. API Endpoints (Proxy)

### 4.1 Proxy → Railway

| Method | Proxy Path | Railway Target | Description |
|--------|-----------|----------------|-------------|
| GET | `/api/admin/stats` | `/stats` | Dashboard stats |
| GET | `/api/admin/users` | `/users` | All users |
| GET | `/api/admin/jobs` | `/jobs` | All jobs |
| GET | `/api/admin/applications` | `/applications` | All applications |
| POST | `/api/admin/approve-job/:id` | `/approve-job/:id` | Approve job |
| POST | `/api/admin/reject-job/:id` | `/reject-job/:id?reason=...` | Reject job |
| POST | `/api/admin/approve-application/:id` | `/approve-application/:id` | Approve app |
| POST | `/api/admin/reject-application/:id` | `/reject-application/:id?reason=...` | Reject app |
| GET | `/api/admin/settings/welcome-text` | `/settings/welcome-text` | Get welcome |
| POST | `/api/admin/settings/welcome-text` | `/settings/welcome-text` | Set welcome |
| GET | `/api/admin/messages` | `/admin/messages?chat_id=...&after_id=...` | Chat messages |

### 4.2 Proxy → Bale

| Method | Proxy Path | Bale Target | Description |
|--------|-----------|-------------|-------------|
| POST | `/api/bale/sendMessage` | `/sendMessage` | Send message as bot |
| POST | `/api/bale/getMe` | `/getMe` | Bot info/test |

### 4.3 Auth Header

All proxy API calls include:
```
X-Admin-Token: <ADMIN_TOKEN from .env>
```

---

## 5. Security

| Concern | Mitigation |
|---------|-----------|
| BOT_TOKEN leak | Stored in proxy `.env` only, never sent to browser |
| Unauthorized API access | `X-Admin-Token` validated by both proxy and Railway |
| `.env` committed to git | `.gitignore` covers `.env`; `.env.example` provided |
| SQLite injection | Parameterized queries already in place (aiosqlite) |
| Message log growth | Cap at 1000 rows per chat_id; cron cleanup if needed |

---

## 6. Railway Changes Required

The following changes must be made to the `bale-bot` repository on GitHub/Railway:

1. **`database.py`:** Add `messages` table to `init_db()`, add `log_message()` and `get_messages()` functions
2. **`bot.py`:** Call `log_message()` after receiving and after sending each message
3. **`api_server.py`:** 
   - Add `GET /admin/messages` endpoint
   - Add `X-Admin-Token` validation middleware
   - Add `ADMIN_TOKEN` to config
4. **`config.py`:** Load `ADMIN_TOKEN` from env

---

## 7. Edge Cases & Error Handling

| Scenario | Behavior |
|----------|----------|
| Railway offline / cold start | Show "connecting..." spinner, auto-retry every 5s |
| Bale API rate limited | Show error toast, suggest waiting |
| No pending jobs | Show empty state: "✅ همه آگهی‌ها بررسی شدن" |
| No messages for chat_id | Show "هنوز پیامی نیست" with instruction to send first message |
| Token mismatch | Show "⚠️ خطای احراز هویت" and check .env |
| Large message list | Virtual scrolling for performance |
| Browser tab hidden | SWR pauses polling (saves bandwidth) |

---

## 8. Non-Functional Requirements

- **Performance:** Initial load < 2s, subsequent page switches instant
- **Real-time lag:** Max 3s for data, 2s for messages
- **Accessibility:** RTL support, Persian typography, keyboard navigable
- **Code quality:** TypeScript strict mode, no `any` types except where necessary

---

## 9. Implementation Order

1. Scaffold monorepo (pnpm workspace, shared types, proxy skeleton, web skeleton)
2. Build Express proxy with full route table
3. Build Admin Console (stats, jobs, applications, users)
4. Build Phone Simulator (chat UI, message polling)
5. Modify Railway bot (messages table, auth, endpoints)
6. End-to-end testing with live Railway
7. Polish UI, add animations, final review
