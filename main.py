import asyncio
from app.config import settings
from app.db import AsyncSessionLocal
from app.fetcher import ECFRFetcher, DataProcessor

async def main():
    async with AsyncSessionLocal() as session:
        fetcher = ECFRFetcher(settings.ECFR_BASE_URL)
        processor = DataProcessor(session)
        
        try:
            # Fetch and process agencies
            agencies_data = await fetcher.fetch_agencies()
            await processor.process_agencies(agencies_data)
            
            # Fetch and process titles
            titles_data = await fetcher.fetch_titles()
            await processor.process_titles(titles_data)
            
        finally:
            await fetcher.close()

if __name__ == "__main__":
    asyncio.run(main())
