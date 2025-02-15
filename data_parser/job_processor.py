import asyncio
import logging
from typing import List
import os
import json
import cProfile
import pstats # For analyzing profile output
import io # For capturing profile output to string

from sqlalchemy import select, update, func, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from uuid import uuid4

from ecfr_fetcher.app.fetcher import ECFRFetcher
from models.models import VersionProcessingJobs, VersionWordCounts
from content_parser import TextProcessor
from config.base import settings 
from db.db import get_db

from dotenv import load_dotenv
load_dotenv()  

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')

class JobProcessor:
    # def __init__(self, session: AsyncSession):
    #     self.session = session
    def __init__(self):
        """
        Initializes the JobProcessor with a database connection URL.
        """
        db_url = f"postgresql+asyncpg://{os.environ.get('DB_USER')}:{os.environ.get('DB_PASSWORD')}@{os.environ.get('DB_HOST')}:{os.environ.get('DB_PORT')}/{os.environ.get('DB_NAME')}"

        self.db_url = db_url
        self._engine = create_async_engine(db_url) # Create engine once per processor instance
        self.async_session_factory = async_sessionmaker(self._engine, expire_on_commit=False) # Session factory
        title_path_map_file = os.path.join(os.path.dirname(__file__), 'title_path_map.json')
        with open(title_path_map_file, 'r') as file:
            self.title_path_map = json.load(file)
        self.processor = TextProcessor()


    async def fetch_jobs(self, batch_size: int = 10) -> List[VersionProcessingJobs]:
        """
        Fetches a batch of 'PENDING' jobs from the version_processing_jobs table using SELECT FOR UPDATE SKIP LOCKED.
        This ensures that jobs are locked for processing by a single processor and skipped if already locked.

        Returns:
            A list of VersionProcessingJobs objects that are fetched and locked for processing.
            Returns an empty list if no jobs are available.
        """
        async with self.async_session_factory() as session:
            try:
                # Using a raw SQL text query for 'FOR UPDATE SKIP LOCKED' for clarity and specific feature
                stmt = text("""
                    SELECT *
                    FROM version_processing_jobs
                    WHERE status = 'PENDING'
                    ORDER BY created_at
                    LIMIT :batch_size
                    FOR UPDATE SKIP LOCKED
                """).bindparams(batch_size=batch_size)

                result = await session.execute(stmt)

                jobs = [VersionProcessingJobs(**dict(row)) for row in result.mappings()]

                if jobs:
                    job_ids = [job.id for job in jobs]
                    logging.info(f"Fetched and locked {len(jobs)} jobs with IDs: {job_ids}")
                    # Update status to PROCESSING immediately after fetching and locking
                    await self._mark_jobs_processing(session, job_ids)
                    await session.commit() # Commit transaction to hold locks and update statuses
                    return jobs
                else:
                    logging.debug("No pending jobs found.")
                    return [] # No jobs found

            except SQLAlchemyError as e:
                logging.error(f"Database error fetching jobs: {e}")
                await session.rollback() # Rollback in case of any error during fetch or lock
                return [] # Indicate no jobs fetched due to error
            except Exception as e:
                logging.exception(f"Unexpected error fetching jobs: {e}") # Log full exception
                await session.rollback()
                return []


    async def _mark_jobs_processing(self, session: AsyncSession, job_ids: List[int]):
        """
        Marks the fetched jobs as 'PROCESSING' in the database.
        This is an internal method called immediately after fetching and locking jobs.
        """
        try:
            stmt = update(VersionProcessingJobs).where(VersionProcessingJobs.id.in_(job_ids)).values(
                status='PROCESSING',
                attempt_count=VersionProcessingJobs.attempt_count + 1,
                lock_id=uuid4(), # Assign a lock_id to track which processor is working on it
                lock_acquired_at=func.now()
            )
            await session.execute(stmt)
            logging.debug(f"Marked jobs {job_ids} as PROCESSING.")
        except SQLAlchemyError as e:
            logging.error(f"Error marking jobs as PROCESSING in database: {e}")
            raise # Re-raise to be handled in fetch_jobs or process_job


    async def process_job(self, job: VersionProcessingJobs):
        """
        Processes a single job. This is where your main job logic should reside.
        This example simulates job processing and updates job status to 'COMPLETED' or 'FAILED'.

        Args:
            job: The VersionProcessingJobs object to be processed.
        """
        job_id = job.id
        print(f"Starting processing job ID: {job_id}, Title: {job.title_number}, Version Date: {job.version_date}")
        logging.info(f"Starting processing job ID: {job_id}, Title: {job.title_number}, Version Date: {job.version_date}")
        async with self.async_session_factory() as session:
            # async with session.begin(): # Use begin() for transaction management
            try:
                logging.info(f"Job ID: {job_id} COMPLETED successfully.")
                fetcher = ECFRFetcher(settings.ECFR_BASE_URL)
                xml_resp = await fetcher.fetch_full_title(job.title_number, job.version_date)
                self.processor.set_xml_content(xml_resp)
                title_number = str(job.title_number)
                word_count_paragraphs = {key: {} for key in self.title_path_map[title_number]}
                if title_number in self.title_path_map:
                    extracted_text_paragraphs = await self.processor.extract_content_from_xml(self.title_path_map[title_number])
                    for type, value in extracted_text_paragraphs.items():
                        for code, text in value.items():
                            word_counts = await self.processor.aggregate_word_counts_stemming_numeric_filter(text)
                            word_count_paragraphs[type][code] = word_counts
                            
                    logging.info(f"Title: {title_number}, Word Counts complete!")#: {word_count_paragraphs}")
                else:
                    logging.warning(f"Title number {title_number} not found in title_path_map.")

                # Save the word count results to the database or any other storage
                await self._save_word_counts(session, job.title_number, job_id, job.version_date, word_count_paragraphs)
                await self._update_job_status(session, job_id, 'COMPLETED')
                await session.commit()
                logging.info(f"Job ID: {job_id} processed and marked COMPLETED successfully.") # Log AFTER successful completion

            except Exception as e:
                logging.error(f"Error processing job ID: {job_id}: {e}")
                await self._update_job_status(session, job_id, 'FAILED', str(e)) # Update status to FAILED in DB
                await session.rollback() # Rollback transaction on error during processing! 
                logging.warning(f"Transaction rolled back for job ID {job_id} due to error.")

    async def _save_word_counts(self, session: AsyncSession, title: int, job_id: int, version_date: str, word_counts: dict):
        """
        Saves the word count results to the database or any other storage.

        Args:
            session: The database session.
            title: The title number of the job being processed.
            job_id: The ID of the job being processed.
            version_date: The version date of the job being processed.
            word_counts: The word count results to be saved.
        """
        try:
            for type, counts in word_counts.items():
                for code, count in counts.items():
                    word_count_entry = VersionWordCounts(
                        title_number=title,
                        task_id=job_id,
                        version_date=version_date,
                        type=type,
                        code=code,
                        word_statistics=count
                    )
                    session.add(word_count_entry)

            await session.flush()  # Flush to ensure all records are staged
            await session.commit()
            # print(f"Saved word counts for title: {title}, version_date: {version_date}, type: {type}, code: {code}.")
            logging.debug(f"Saved word counts for title: {title}, version_date: {version_date}, type: {type}, code: {code}.")
        except SQLAlchemyError as e:
            logging.error(f"Database error saving word counts for title: {title}, version_date: {version_date}, type: {type}, code: {code} : {e}")
            await session.rollback()
            raise
    
    async def _update_job_status(self, session: AsyncSession, job_id: int, status: str, error_message: str = None):
        async with self.async_session_factory() as new_session: #trying new session for status update
            try:
                stmt = update(VersionProcessingJobs).where(VersionProcessingJobs.id == job_id).values(
                    status=status,
                    error_message=error_message,
                    last_attempt_at=func.now(),
                    updated_at=func.now(),
                    lock_id=None,
                    lock_acquired_at=None
                )
                await new_session.execute(stmt)
                await new_session.commit()
                logging.debug(f"Updated job ID: {job_id} status to {status}.")
            except SQLAlchemyError as e:
                logging.error(f"Database error updating job status for ID {job_id}: {e}")
                await new_session.rollback()
                raise
        

    async def run_processor_loop(self):
        """
        Main loop for the job processor. Fetches jobs and processes them continuously.
        """
        logging.info(f"Job processor started.")
        while True:
            jobs = await self.fetch_jobs() # Fetch a batch of jobs
            if jobs:
                for job in jobs:
                    await self.process_job(job)
                    await asyncio.sleep(0.25)
            else:
                await asyncio.sleep(2) # Wait for 2 seconds if no jobs are found


async def run_multiple_processors(num_processors: int):
    """
    Runs multiple job processors concurrently using asyncio.gather.
    """
    # db_url = settings.DATABASE_URL # Use your database URL from settings
    # session = get_db()
    processors = [JobProcessor() for _ in range(num_processors)]
    tasks = [processor.run_processor_loop() for processor in processors]
    logging.info(f"Running {num_processors} job processors.")
    await asyncio.gather(*tasks) # Run all processors concurrently


async def main():
    """
    Main function to start the job processors.
    """
    num_processors = 3 # Define number of parallel processors
    await run_multiple_processors(num_processors)
    # processor = JobProcessor()
    # jobs = await processor.fetch_jobs() # Fetch a batch of jobs
    # if jobs:
    #     for job in jobs:
    #         await processor.process_job(job)

if __name__ == "__main__":
    
    # --- Profiling with cProfile ---
    # pr = cProfile.Profile() # Create a profiler object
    # pr.enable() # Start profiling

    asyncio.run(main())
    

    # pr.disable() # Stop profiling

    # # --- Analyze and Print Profile Results ---
    # s = io.StringIO() # Capture profile output to string
    # sortby = 'cumulative' # Sort by cumulative time
    # ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    # ps.print_stats(50) # Print top 20 functions by cumulative time
    # print(s.getvalue()) # Print the formatted stats to console
