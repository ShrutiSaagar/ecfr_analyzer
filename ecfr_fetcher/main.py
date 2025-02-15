import asyncio
from config.base import settings
from db.db import AsyncSessionLocal
from app.fetcher import ECFRFetcher, DataProcessor

from models import models
from sqlalchemy import select

async def fetch_all_title_versions(session, fetcher, processor):
    """Fetch versions for all titles"""
    # Get all title numbers from the database
    result = await session.execute(select(models.Title.number))
    title_numbers = [row[0] for row in result]
    
    for title_number in title_numbers:
        try:
            print(f"Fetching versions for title {title_number}")
            versions_data = await fetcher.fetch_title_versions(title_number)
            await processor.process_title_versions(title_number, versions_data)
        except Exception as e:
            print(f"Error processing title {title_number}: {str(e)}")
            continue
        
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
            
            # Fetch and process title versions
            await fetch_all_title_versions(session, fetcher, processor)
        finally:
            await fetcher.close()

if __name__ == "__main__":
    asyncio.run(main())
