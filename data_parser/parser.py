
# text_processor.py
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from collections import Counter
import string

class TextProcessor:
    def __init__(self):
        # Download required NLTK data
        nltk.download('punkt')
        nltk.download('stopwords')
        nltk.download('wordnet')
        nltk.download('averaged_perceptron_tagger')
        
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))

    def process_text(self, text):
        # Tokenize
        tokens = word_tokenize(text.lower())
        
        # Remove punctuation and numbers
        tokens = [token for token in tokens 
                 if token not in string.punctuation and not token.isnumeric()]
        
        # Remove stop words and lemmatize
        tokens = [self.lemmatizer.lemmatize(token) 
                 for token in tokens if token not in self.stop_words]
        
        # Count tokens
        return dict(Counter(tokens))

# processor.py
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
import uuid
import xml.etree.ElementTree as ET
from sqlalchemy import and_, or_
from sqlalchemy.future import select
from .models import ContentProcessingTask, AgencyTitleMapping, ProcessingResult
from .text_processor import TextProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ECFRProcessor:
    def __init__(self, session, api_base_url):
        self.session = session
        self.api_base_url = api_base_url
        self.text_processor = TextProcessor()

    async def fetch_pending_tasks(self):
        query = select(ContentProcessingTask).where(
            and_(
                ContentProcessingTask.status == 'PENDING',
                or_(
                    ContentProcessingTask.lock_id.is_(None),
                    ContentProcessingTask.lock_acquired_at < datetime.now() - timedelta(hours=1)
                )
            )
        ).limit(10)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def acquire_task_lock(self, task):
        task.lock_id = uuid.uuid4()
        task.lock_acquired_at = datetime.now()
        task.status = 'PROCESSING'
        task.attempt_count += 1
        await self.session.commit()
        return True

    async def fetch_agency_mappings(self, title_number):
        query = select(AgencyTitleMapping).where(
            AgencyTitleMapping.title_number == title_number
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def fetch_xml_content(self, title_number, version_date):
        url = f"{self.api_base_url}/api/versioner/v1/full/{version_date}/title-{title_number}.xml"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.text()

    def process_xml_content(self, xml_content, xpath):
        root = ET.fromstring(xml_content)
        elements = root.findall(xpath)
        text = ' '.join(''.join(element.itertext()) for element in elements)
        return self.text_processor.process_text(text)

    async def process_task(self, task):
        try:
            await self.acquire_task_lock(task)

            xml_content = await self.fetch_xml_content(
                task.title_number,
                task.version_date.strftime('%Y-%m-%d')
            )

            agency_mappings = await self.fetch_agency_mappings(task.title_number)

            for mapping in agency_mappings:
                for xpath in mapping.xpath_expressions:
                    word_counts = self.process_xml_content(xml_content, xpath)
                    
                    result = ProcessingResult(
                        task_id=task.id,
                        agency_id=mapping.agency_id,
                        title_number=task.title_number,
                        xpath=xpath,
                        word_statistics=word_counts
                    )
                    self.session.add(result)

            task.status = 'COMPLETED'
            task.lock_id = None
            task.lock_acquired_at = None
            await self.session.commit()

            logger.info(f"Successfully processed task {task.id}")

        except Exception as e:
            logger.error(f"Error processing task {task.id}: {str(e)}")
            task.status = 'FAILED'
            task.error_message = str(e)
            task.lock_id = None
            task.lock_acquired_at = None
            await self.session.commit()

import asyncio
from .database import get_db
from .config import settings
from .processor import ECFRProcessor

async def main():
    async for session in get_db():
        processor = ECFRProcessor(
            session=session,
            api_base_url=settings.API_BASE_URL
        )
        
        while True:
            try:
                pending_tasks = await processor.fetch_pending_tasks()
                if not pending_tasks:
                    logger.info("No pending tasks found")
                    break

                await asyncio.gather(
                    *[processor.process_task(task) for task in pending_tasks]
                )

            except Exception as e:
                logger.error(f"Error in main processing loop: {str(e)}")
                break

if __name__ == "__main__":
    asyncio.run(main())
