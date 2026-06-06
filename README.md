# LeadFlow — Automated Lead Scraping & Processing Pipeline

A production-grade web automation pipeline built with **Playwright**, **FastAPI**, and **PostgreSQL**. Scrapes listings from target websites, scores lead quality, deduplicates records, and exposes everything through a REST API.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        LeadFlow                             │
│                                                             │
│  POST /scrape                                               │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐     ┌──────────────┐     ┌─────────────┐  │
│  │  Playwright │────▶│    Ingest    │────▶│  PostgreSQL │  │
│  │  Scraper    │     │   Worker     │     │     DB      │  │
│  │             │     │ (score+dedup)│     │             │  │
│  └─────────────┘     └──────────────┘     └─────────────┘  │
│                                                  │          │
│                           GET /leads ◀───────────┘          │
│                           GET /stats                        │
│                           GET /runs                         │
└─────────────────────────────────────────────────────────────┘
```

**Key components:**
- `scraper/` — Playwright-based async scraper with proxy support, pagination, and polite delays
- `workers/ingest.py` — URL deduplication + keyword-based quality scoring (0–100)
- `api/main.py` — FastAPI REST layer, background job queue, run tracking
- `db/models.py` — SQLAlchemy async models for leads and scraper runs

---

## Features

- Headless Chromium via Playwright (handles JS-rendered pages)
- Per-context proxy rotation (plug in your proxy list)
- Automatic pagination with empty-page stop condition
- Lead quality scoring engine (keyword signals, URL presence, description length)
- URL-based deduplication — no duplicate records inserted
- Background job execution — `/scrape` returns immediately, runs async
- Scraper run history tracked in DB (status, records found, errors)
- Full REST API: trigger scrapes, browse leads, view stats

---

## Quick Start

### Local with Docker

```bash
git clone https://github.com/yourusername/leadflow.git
cd leadflow

docker-compose up --build
```

API will be live at `http://localhost:8000`  
Docs at `http://localhost:8000/docs`

### Local without Docker

```bash
pip install -r requirements.txt
playwright install chromium

# Set your DB connection
export DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/leadflow

uvicorn api.main:app --reload
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/scrape` | Trigger scrape job (async) |
| GET | `/leads` | List all leads (paginated) |
| GET | `/leads/{id}` | Single lead detail |
| GET | `/stats` | Total, processed, avg score |
| GET | `/runs` | Scraper run history |

### Trigger a scrape

```bash
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{"target_url": "https://example.com/listings", "max_pages": 5}'
```

### Get leads

```bash
curl http://localhost:8000/leads?skip=0&limit=20
```

---

## Adapting the Scraper

The scraper in `scraper/scraper.py` uses generic CSS selectors by default. To target a specific site:

1. Open the site in Chrome DevTools
2. Identify selectors for listing container, title, link, description
3. Update `scrape_page()` in `scraper/scraper.py`

For login-protected sites, add session setup before `page.goto()`:

```python
await page.goto("https://site.com/login")
await page.fill("#email", "your@email.com")
await page.fill("#password", "yourpassword")
await page.click("button[type=submit]")
await context.storage_state(path="session.json")
```

Then reuse the session:

```python
context = await browser.new_context(storage_state="session.json")
```

---

## Deployment (Railway)

1. Push to GitHub
2. Create new Railway project → Deploy from GitHub
3. Add PostgreSQL plugin
4. Set `DATABASE_URL` environment variable
5. Deploy

---

## Tech Stack

- **Playwright** — Browser automation and scraping
- **FastAPI** — Async REST API
- **PostgreSQL + SQLAlchemy** — Async ORM and storage
- **Docker** — Containerized deployment
- **asyncio** — Concurrent scraping workers

---

## Project Structure

```
leadflow/
├── api/
│   └── main.py          # FastAPI app, routes, background jobs
├── scraper/
│   └── scraper.py       # Playwright scraper, pagination, proxy rotation
├── workers/
│   └── ingest.py        # Deduplication, quality scoring, DB insert
├── db/
│   └── models.py        # SQLAlchemy models, async engine
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```
