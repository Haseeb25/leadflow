import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Lead
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

QUALITY_KEYWORDS = ["urgent", "immediate", "premium", "exclusive", "verified"]
SPAM_KEYWORDS    = ["free", "click here", "limited time", "act now"]


def score_lead(lead: Dict[str, Any]) -> int:
    score = 50  # baseline
    text = f"{lead.get('title', '')} {lead.get('description', '')}".lower()

    for kw in QUALITY_KEYWORDS:
        if kw in text:
            score += 10
    for kw in SPAM_KEYWORDS:
        if kw in text:
            score -= 15

    if lead.get("url"):
        score += 5
    if lead.get("description") and len(lead["description"]) > 100:
        score += 5

    return max(0, min(100, score))


async def ingest_leads(records: List[Dict[str, Any]], db: AsyncSession) -> int:
    inserted = 0

    for record in records:
        if not record.get("url"):
            continue

        # Deduplication check
        existing = await db.execute(select(Lead).where(Lead.url == record["url"]))
        if existing.scalar_one_or_none():
            continue

        lead = Lead(
            title=record.get("title"),
            url=record.get("url"),
            description=record.get("description"),
            source_url=record.get("source_url"),
            score=score_lead(record),
            processed=False,
        )
        db.add(lead)
        inserted += 1

    await db.commit()
    logger.info(f"Ingested {inserted} new leads (skipped {len(records) - inserted} duplicates)")
    return inserted
