# Recruiter Bypass — MVP Plan

## Architecture

```
┌─────────────────────────────────────────┐
│  Docker Container (desktop → NAS)        │
│                                          │
│  ┌──────────┐  ┌──────────────────┐     │
│  │ FastAPI   │  │  AI Agent Swarm   │     │
│  │ Backend   │◄─┤  (Ollama local)   │     │
│  │ Port 8000 │  │  - Job Scraper    │     │
│  │           │  │  - Employer Match  │     │
│  │  ┌──────┐ │  │  - Logo Search    │     │
│  │  │SQLite│ │  │  - JD Fingerprint │     │
│  │  │(dev) │ │  └──────────────────┘     │
│  │  └──────┘ │                           │
│  └──────────┘                           │
│                                          │
│  Dashboard (HTMX + Jinja2)               │
│  - Job feed                              │
│  - Employer matches                      │
│  - Agent status / control                │
└─────────────────────────────────────────┘
         │
         ▼
    Ollama (localhost:11434)
    - qwen3.5-hermes / deepseek
    - For JD analysis & matching
```

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI + Python | Already using in whisper |
| Frontend | Jinja2 + HTMX | Simple, no SPA overhead |
| Database | SQLite → Postgres | Dev: SQLite, Prod: Postgres |
| AI Agents | Ollama (local) | No API costs, private |
| Scraping | httpx + BeautifulSoup | Lightweight, Pythonic |
| Container | Docker + docker-compose | Desktop → Portainer NAS |

## Phase 1 — Scraper + DB (Week 1)

- [ ] Scrape Seek IT jobs (single page, hardcoded search)
- [ ] Parse: title, company (if visible), location, description
- [ ] Store in SQLite
- [ ] Simple web UI: table of scraped jobs

## Phase 2 — Employer Identification (Week 2)

- [ ] AI Agent 1: JD text fingerprinting
  - Extract unique phrases ("leading provider of X in Y")
  - Match against known employer descriptions
- [ ] AI Agent 2: Company name inference
  - Parse "our client" → search for clues in JD
  - Cross-reference with LinkedIn company search
- [ ] AI Agent 3: Logo/pattern matching (future)
- [ ] Manual employer database: add known direct-hire companies

## Phase 3 — Dashboard (Week 3)

- [ ] Job feed with employer match status
- [ ] Agent control: run/pause/configure agents
- [ ] Stats: matched vs unmatched, new employers found
- [ ] Employer directory page

## Phase 4 — Polish + Containerize (Week 4)

- [ ] Dockerfile + docker-compose
- [ ] Migrate SQLite → Postgres (target: hoarder:5433)
- [ ] Move to Portainer on Terramaster
- [ ] Basic auth / API key for dashboard

## Route Map (FastAPI)

```
GET  /                    Dashboard home
GET  /jobs                 Job feed (paginated)
GET  /jobs/{id}            Job detail + employer match
GET  /employers            Employer directory
POST /agents/run           Trigger agent swarm
GET  /agents/status        Agent activity log
POST /employers/add        Manual employer entry
GET  /api/jobs             JSON API for plugin (future)
```
