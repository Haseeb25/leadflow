import asyncio
import logging
from playwright.async_api import async_playwright, BrowserContext, Page
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROXY_LIST = [
    # Add your proxies here: "http://user:pass@host:port"
]

async def create_context(browser, proxy: str = None) -> BrowserContext:
    context_options = {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "viewport": {"width": 1280, "height": 720},
    }
    if proxy:
        context_options["proxy"] = {"server": proxy}
    return await browser.new_context(**context_options)


async def scrape_page(page: Page, url: str) -> List[Dict[str, Any]]:
    results = []
    try:
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)

        # Generic listing extraction — adapt selectors to target site
        listings = await page.query_selector_all(".listing-item, .result-card, article")
        for item in listings:
            title = await item.query_selector("h2, h3, .title")
            link  = await item.query_selector("a")
            desc  = await item.query_selector("p, .description")

            results.append({
                "title": (await title.inner_text()).strip() if title else None,
                "url":   (await link.get_attribute("href"))  if link  else None,
                "description": (await desc.inner_text()).strip() if desc else None,
                "source_url": url,
            })

        logger.info(f"Scraped {len(results)} listings from {url}")
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
    return results


async def paginate_and_scrape(base_url: str, max_pages: int = 10) -> List[Dict[str, Any]]:
    all_results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for page_num in range(1, max_pages + 1):
            proxy = PROXY_LIST[page_num % len(PROXY_LIST)] if PROXY_LIST else None
            context = await create_context(browser, proxy)
            page = await context.new_page()

            url = f"{base_url}?page={page_num}"
            results = await scrape_page(page, url)

            if not results:
                logger.info(f"No results on page {page_num}, stopping.")
                await context.close()
                break

            all_results.extend(results)
            await context.close()
            await asyncio.sleep(1)  # polite delay

        await browser.close()

    logger.info(f"Total listings scraped: {len(all_results)}")
    return all_results


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com/listings"
    results = asyncio.run(paginate_and_scrape(url, max_pages=5))
    print(f"Done. {len(results)} records collected.")
