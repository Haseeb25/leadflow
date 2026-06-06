from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional
from db.models import Lead, ScraperRun, get_db, init_db
from scraper.scraper import paginate_and_scrape
from workers.ingest import ingest_leads
import asyncio

app = FastAPI(title="LeadFlow API", version="1.0.0")


@app.on_event("startup")
async def startup():
    await init_db()


# ── Schemas ───────────────────────────────────────────────────────────────────

class LeadOut(BaseModel):
    id: int
    title: Optional[str]
    url: Optional[str]
    description: Optional[str]
    score: int
    processed: bool

    class Config:
        from_attributes = True


class ScrapeRequest(BaseModel):
    target_url: str
    max_pages: int = 10


class StatsOut(BaseModel):
    total_leads: int
    processed: int
    avg_score: float


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "LeadFlow running", "version": "1.0.0"}


@app.post("/scrape", status_code=202)
async def trigger_scrape(req: ScrapeRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    background_tasks.add_task(run_scrape_job, req.target_url, req.max_pages)
    return {"message": "Scrape job started", "target": req.target_url, "max_pages": req.max_pages}


@app.get("/leads", response_model=List[LeadOut])
async def get_leads(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).offset(skip).limit(limit))
    return result.scalars().all()


@app.get("/leads/{lead_id}", response_model=LeadOut)
async def get_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@app.get("/stats", response_model=StatsOut)
async def get_stats(db: AsyncSession = Depends(get_db)):
    total = await db.execute(select(func.count(Lead.id)))
    processed = await db.execute(select(func.count(Lead.id)).where(Lead.processed == True))
    avg_score = await db.execute(select(func.avg(Lead.score)))
    return {
        "total_leads": total.scalar() or 0,
        "processed": processed.scalar() or 0,
        "avg_score": round(float(avg_score.scalar() or 0), 2),
    }


@app.get("/runs")
async def get_runs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScraperRun).order_by(ScraperRun.started_at.desc()).limit(20))
    runs = result.scalars().all()
    return [{"id": r.id, "status": r.status, "records_found": r.records_found, "errors": r.errors} for r in runs]


# ── Background job ────────────────────────────────────────────────────────────

async def run_scrape_job(target_url: str, max_pages: int):
    from db.models import AsyncSessionLocal
    from datetime import datetime

    async with AsyncSessionLocal() as db:
        run = ScraperRun(status="running")
        db.add(run)
        await db.commit()
        await db.refresh(run)

        try:
            records = await paginate_and_scrape(target_url, max_pages)
            inserted = await ingest_leads(records, db)

            run.status = "done"
            run.records_found = inserted
            run.finished_at = datetime.utcnow()
        except Exception as e:
            run.status = "failed"
            run.errors = 1
            run.finished_at = datetime.utcnow()

        await db.commit()
