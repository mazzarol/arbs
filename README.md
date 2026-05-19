# ARBS — Applicant Recruitment Bypass System

Find the real employer behind recruiter-posted IT jobs. ARBS scrapes job boards,
flags recruiter-hidden roles, and uses AI agents to identify the actual hiring company.

## Features

- **Multi-source scraping** — Seek, Indeed, Jora (CareerOne/LinkedIn/recruiter sites are JS-rendered, not scrapable)
- **Recruiter detection** — 130+ Australian IT recruitment agencies flagged automatically
- **Employer identification** — Phrase-search agent finds the real employer by searching unique JD text
- **Employer database** — 63+ Sunshine Coast/QLD companies with careers pages
- **Dashboard** — Jobs scraped, employers revealed, hidden count metrics
- **Connection logging** — IP geolocation, deduplicated per hour
- **Dark theme UI** — Filterable, sortable job listing with age in days
- **MRU search** — Remembers your last 10 keyword searches

## Quick Start

```bash
git clone https://github.com/mazzarol/arbs.git
cd arbs
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

Open http://localhost:8000

## Docker

```bash
cp .env.example .env          # add your DeepSeek key (optional)
docker compose up --build -d  # runs on port 8000
```

Data persists in a Docker volume. Rebuild with `docker compose up --build -d`.

## Architecture

```
app/
├── main.py              FastAPI app, routes
├── database.py          SQLite (Docker: /data/recruiter.db)
├── models.py            Job, Employer, AgentRun, ConnectionLog
├── scraper.py           Seek + Indeed + Jora scrapers
├── logging_mw.py        IP geolocation + dedup middleware
├── seed_employers.py    SC/QLD employer database seeder
└── agents/
    ├── base.py          BaseAgent + AgentOrchestrator
    ├── __init__.py      JD Fingerprint agent (DeepSeek)
    └── phrase_search.py Phrase search agent (Google + DDG)
```

## AI Agents

| Agent | Requires | Method |
|---|---|---|
| Phrase Search | None | Googles unique JD phrases to find employer careers pages |
| JD Fingerprint | DeepSeek API key | LLM matches JD against employer database |

Run from the Agents page. Results show in the Jobs list with confidence scores.

## License

GPL-3.0-or-later — see [LICENSE](LICENSE)
