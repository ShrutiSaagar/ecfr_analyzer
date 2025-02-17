# data_parser/job_queue.py
import asyncio
import logging
from typing import List, Dict
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# from data_parser import models
from db.db import get_db  # Correct import path
from config.base import settings
from models.models import *

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')


class DataProcessor:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def fetch_agencies(self) -> List[Agency]:
        """Fetches all agencies from the database."""
        try:
            result = await self.session.execute(select(Agency))
            agencies = result.scalars().all()
            logging.info(f"Fetched {len(agencies)} agencies from the database.")
            return agencies
        except Exception as e:
            logging.error(f"Error fetching agencies: {e}")
            raise

    async def create_processing_jobs_for_title_versions(self):
        """Creates VersionProcessingJobs entries for each TitleVersion that doesn't already have one."""
        try:
            # 1. Fetch all TitleVersions
            agencies = await self.fetch_agencies()
            # print('agencies')
            # print(agencies)
            titles_set = set()
            for agency in agencies:
                docs = agency.docs
                logging.info(f"Agency: {agency.name}, Docs: {docs}")
                try:
                    docs_list = docs
                    for doc in docs_list:
                        # print('doc')
                        # print(doc)
                        title = doc.get("title")
                        if title in { 7, 50 } : #12, 47, 49, 21, 48}: #7, 50 - lastly
                            titles_set.add(title)
                        chapter = doc.get("chapter")
                        logging.info(f"Title: {title}, Chapter: {chapter}")
                except json.JSONDecodeError as e:
                    logging.error(f"Error decoding JSON for agency {agency.name}: {e}")

            title_versions = []
            for title in titles_set:
                title_versions_query = await self.session.execute(
                    select(TitleVersion).filter(TitleVersion.title_number == title).order_by(TitleVersion.version_date.desc())
                )
                title_versions_for_title = title_versions_query.scalars().all()
                title_versions.extend(title_versions_for_title)
                # title_version = await self.session.execute(
                #     select(TitleVersion).filter(TitleVersion.title_number == title).order_by(TitleVersion.version_date.desc()).limit(1)
                # )
                # title_version = title_version.scalar_one_or_none()
                # if title_version:
                #     title_versions.append(title_version)
            
            jobs_created = 0
            
            for i, tv in enumerate(title_versions):
                # 2. Check if a VersionProcessingJobs record already exists
                existing_job = await self.session.execute(
                    select(VersionProcessingJobs).filter_by(
                        title_number=tv.title_number,
                        version_date=tv.version_date
                    )
                )
                existing_job = existing_job.scalar_one_or_none()

                if not existing_job:
                    # 3. Create a new VersionProcessingJobs if it doesn't exist
                    new_job = VersionProcessingJobs(
                        title_number=tv.title_number,
                        version_date=tv.version_date
                    )
                    self.session.add(new_job)
                    jobs_created += 1

                # Commit every 100 records
                if jobs_created % 100 == 0:
                    await self.session.commit()

            # Final commit for any remaining records
            await self.session.commit()
            logging.info(f"Created {jobs_created} VersionProcessingJobs entries.")

        except Exception as e:
            logging.error(f"Error creating VersionProcessingJobs entries: {e}")
            await self.session.rollback()
            raise

class JobQueueManager:
    
    async def enqueue_title_version_jobs(self):
        """Enqueues title version jobs for processing."""
        async for session in get_db():
            processor = DataProcessor(session)
            await processor.create_processing_jobs_for_title_versions()


# Example Usage (inside an asyncio event loop):
async def main():

    queue_manager = JobQueueManager()
    await queue_manager.enqueue_title_version_jobs()

if __name__ == "__main__":
    asyncio.run(main())


