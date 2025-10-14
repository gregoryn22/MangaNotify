# MangaNotify → Stable Product Roadmap (with a more *modifiable* UI)

> This plan is tailored from your current stack brief and repo state. It keeps your single-container, Unraid-friendly philosophy, while making the UI easier to evolve without blowing up complexity.

---

## North Star

- **Stable, single-container app** that polls MangaBaka, sends Pushover/Discord alerts, and serves a **clean, easily-editable UI**.
- **Keep ops simple** (no DB/Redis), but **reduce code risk** (duplicated entrypoints, ad-hoc rate limit store, empty routers).
- **Adopt a light, incremental UI architecture** you can extend as features land, without forcing a big frontend rewrite.

---

## Scope & Non-Goals

- **In scope:** backend consolidation, test/lint CI hardening, JSON data versioning, rate-limit hygiene, UI componentization, minimal build tooling.
- **Out of scope (for now):** migrating to a database, adding workers/queues, full design system refactor, k8s.

---

## Phase 0 — “Green & Clean” (Week 0–1)

**Objective:** Eliminate obvious foot-guns and make CI a reliable safety net.

**Tasks**
1. **Consolidate entrypoints**
   - Delete `server.py`, ensure imports/tests use `main.py`.  
   - Add a tiny `routers/health.py` (or keep as inlined route, but not both).
2. **Rate-limit hygiene**
   - Add periodic TTL pruning (e.g., every 5 minutes) to in-memory rate-limits to prevent unbounded growth.
3. **Version & secrets housekeeping**
   - Sync `requirements.in` → regenerate `requirements.txt` and `requirements-dev.txt` (remove prod/dev skew).
   - Add `MASTER_KEY`, `PORT` to `env.example`. Clarify `CORS_ALLOW_ORIGINS` guidance.
4. **Quality gates**
   - Add `ruff` (lint+format) via `pyproject.toml`; wire into CI and `scripts/run_tests.py`.
   - Keep `pytest` with coverage threshold ≥85%.

**Acceptance**
- CI: green on lint, type (optional), unit/integration tests.
- No references to `server.py` remain.
- `GET /api/health` responds; rate-limit map does not grow unbounded during soak.

---

## Phase 1 — Data Safety & Observability (Week 2–3)

**Objective:** Make upgrades safe and behavior visible.

**Tasks**
1. **JSON data versioning**
   - Wrap files as `{ "_version": 1, "items": [...] }`.
   - On startup: detect legacy shape and auto-migrate; write back v1.
2. **Readiness endpoint**
   - `GET /api/ready` checks: can write to `/data`, can reach MangaBaka within timeout (HEAD/ping), poller status OK.
3. **Light metrics (optional but tiny)**
   - Expose `/metrics` (Prometheus format) with request counts, poll successes/errors, notification attempts.

**Acceptance**
- Restart-safe upgrades with no manual steps.
- `/ready` flips to green only when app is actually able to serve.

---

## Phase 2 — UI Modifiability (Week 4–6)

**Objective:** Introduce **small, composable UI building blocks** without adopting a heavy framework (unless you choose to).

### Pick a baseline path (recommended → **A**)

**A) HTMX + Alpine (no build step, HTML-first) — *Recommended now***  
- Pros: zero/low tooling, progressive enhancement, tiny surface area, very easy to edit.  
- Plan:
  - Keep FastAPI templates/static hosting.
  - Incrementally convert existing views to **partial endpoints** (returning fragments) and **HTMX swaps**.
  - Use **Alpine** for local state (modals, toggles), and **HTMX** for server actions (search, watchlist CRUD, refresh).
  - Extract **HTML components** (partials) per feature: series card, watchlist row, notification item.

**B) Web Components (Lit) — *Slightly more tooling, still light***  
- Pros: framework-agnostic, encapsulated components; Cons: small build step (Vite).  
- Plan: add `/frontend` with Vite + Lit; output to `src/manganotify/static/` at build.

**C) React + TanStack (Vite) — *Heavier, most flexibility later***  
- Pros: long-term scale; Cons: adds Node toolchain and state choices now.  
- Plan: isolate in `/frontend`, build to static, mount behind FastAPI.

> Default path: **A (HTMX + Alpine)** keeps your current “no npm” ethos and makes the UI *immediately* more editable.

### UI Architecture Goals (for all paths)

- **File structure**
  ```
  src/manganotify/static/
    css/               # tokens.css, base.css, components.css
    js/                # minimal helpers; if A: htmx.min.js, alpine.min.js vendored
    components/        # *_partial.html or *.tmpl.html (A), or *.ts (B/C)
    pages/
      index.html
      setup.html
  ```
- **Design tokens**: `css/tokens.css` for spacing, colors, sizes; components consume tokens so restyling is easy.
- **Server-rendered first**: pages render on server; actions mutate via HTMX (or client router if B/C).
- **Component contracts**: each component gets a data contract (JSON/HTML); test with fixtures.

**Incremental Conversion Order**
1. **Setup wizard** → partials/forms (lowest risk)
2. **Search** → results list partial, debounce, “Add to watchlist” action
3. **Watchlist** → table with per-row actions (mark read, refresh)
4. **Notifications** → list with resend / clear
5. **Series detail** → chapter list, quick actions

**Acceptance**
- You can add a new action (e.g., “mute series for 24h”) by composing:
  - a small FastAPI route returning HTML partial
  - a tiny HTMX trigger attribute
  - optional Alpine state for button/confirm  
  **No central JS rewrite needed.**

---

## Phase 3 — DevX & Delivery (Week 6–7)

**Objective:** Faster builds and clearer delivery.

**Tasks**
1. **Dockerfile speedups**
   - Pre-generate `requirements.txt` (remove `pip-compile` from Dockerfile) or use a builder stage.
2. **Static asset pipeline**
   - Path A: vendor `htmx`, `alpine` into `static/js/` and pin versions; add an integrity check note in docs.
   - Path B/C: Vite build step (`npm ci && npm run build`) that outputs to `static/`.
3. **Docs**
   - `CONTRIBUTING.md`: how to run tests; how to add a UI component/partial; how to add a router.
   - “Playbook” to add a new feature: backend route + partial + HTMX swap (template provided below).

**Acceptance**
- Cold Docker build < 2–3 minutes on your machine.
- Adding a feature follows a 5–8 step, copy-pasta-friendly playbook.

---

## Phase 4 — Nice-to-Haves (Week 8+)

- Dark mode & theme switcher via CSS variables only.
- `/metrics` dashboard (Grafana, optional).
- Split liveness vs readiness checks in Docker healthcheck.
- Feature flags (env-driven) for new UI components.

---

## Cursor.ai “Task Queue” (pasteable, bite-sized prompts)

> Use these one at a time. Each has clear acceptance criteria.

1. **Remove legacy entrypoint**
   - *Prompt:* “Refactor the app to use only `main.py` as the entrypoint. Delete `server.py`, update imports/tests, ensure `/api/health` remains available. Keep behavior identical.”
   - *Done when:* repo has no `server.py` references; tests & CI pass.

2. **Implement rate-limit pruning**
   - *Prompt:* “In the rate-limit middleware, add a periodic TTL cleanup (every 5 minutes) to prune stale IP buckets, with O(1) per request overhead.”
   - *Done when:* soak test shows stable memory; new unit test asserts pruning.

3. **Add JSON data versioning + auto-migration**
   - *Prompt:* “Wrap `watchlist.json` and `notifications.json` with `{ "_version": 1, "items": [...] }`. On startup, detect legacy shape and migrate in-place. Add tests.”
   - *Done when:* legacy files load & are rewritten to v1; tests pass.

4. **Introduce HTMX + Alpine & componentize Setup page**
   - *Prompt:* “Add HTMX + Alpine (vendored minified files). Convert Setup page to use HTMX partials for each form section. Provide unit tests for returned HTML fragments (BeautifulSoup).”
   - *Done when:* Setup flows work with partial swaps; tests cover fragments.

5. **Componentize Search → Watchlist flow**
   - *Prompt:* “Create `components/search_results.partial.html` and an `/api/search/partial` route returning it. Add `hx-get` + `hx-trigger` to search input. Add ‘Add to Watchlist’ action that swaps row state.”
   - *Done when:* Search is live without page reload, watchlist updates inline.

6. **Componentize Watchlist table**
   - *Prompt:* “Create `components/watchlist_row.partial.html` and row actions (mark read, refresh series). Ensure idempotent server actions; HTMX swaps only the row.”
   - *Done when:* Row actions don’t reload page; partial tests exist.

7. **Readiness endpoint**
   - *Prompt:* “Add `/api/ready` that checks: `/data` writable, MangaBaka reachable within 1s, poller running. Return JSON with booleans and last poll timestamps.”
   - *Done when:* Docker healthcheck can be updated to `/api/ready` if desired.

8. **Ruff + CI gate**
   - *Prompt:* “Add `ruff` to `pyproject.toml` with sensible rules. Update CI to run `ruff check` and `ruff format --check`. Fix current violations.”
   - *Done when:* CI fails on lint; now passes.

---

## UI “Modifiability Ladder” (choose where to stop)

- **Step 1 (now):** Server-rendered pages + **HTMX partials** + **Alpine** micro-state.
- **Step 2:** Add **Web Components (Lit)** for card-level reuse; keep HTMX for data.
- **Step 3:** If/when features demand, introduce **React + TanStack** behind a stable API and keep the server HTMX path for low-power devices/admin pages.

> Each step retains the previous one, so you don’t rewrite—just augment.

---

## Definition of Done (per PR)

- All tests & linting pass (CI).
- If UI changed: partial/component has a fixture + HTML snapshot test.
- Docs updated: a one-liner in `CHANGELOG.md` and, if new component, a short “how to reuse” note.

---

## Tiny “Add a Feature” Playbook (HTMX path)

1. Add FastAPI route that returns a rendered partial.
2. Create `components/<name>.partial.html` (no layout, just the piece).
3. In page HTML, add `hx-get="/api/<name>/partial" hx-trigger="…" hx-target="#<target>" hx-swap="outerHTML"`.
4. Optional: Alpine state for local UX (confirmations, temporary spinners).
5. Unit test: feed known data → assert fragment HTML structure.
6. Wire to nav; document in `docs/feature_<name>.md`.

---

## Deliverables Checklist

- [ ] CI green, `server.py` removed, health router consistent.  
- [ ] Rate-limit TTL pruning.  
- [ ] JSON v1 with auto-migration.  
- [ ] `/ready` endpoint (+ optional `/metrics`).  
- [ ] HTMX/Alpine vendored; Setup/Search/Watchlist componentized.  
- [ ] `ruff` in CI; Dockerfile speedups; docs for “add a feature”.
