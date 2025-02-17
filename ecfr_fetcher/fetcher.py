import httpx
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import models
import json

class ECFRFetcher:
    def __init__(self, base_url: str):
        self.base_url = base_url
        # self.client = httpx.AsyncClient()
        self.client = httpx.AsyncClient(timeout=900)
    
    async def fetch_agencies(self) -> dict:
        response = await self.client.get(f"{self.base_url}/admin/v1/agencies.json")
        return response.json()
    
    async def fetch_titles(self) -> dict:
        response = await self.client.get(f"{self.base_url}/versioner/v1/titles.json")
        return response.json()
    
    async def fetch_title_versions(self, title_number: int) -> dict:
        """Fetch versions for a specific title"""
        response = await self.client.get( f"{self.base_url}/versioner/v1/versions/title-{title_number}.json")
        if response.status_code == 404:
            return {"content_versions": []}
        return response.json()
    
    async def fetch_full_title(self, title_number: int, version_date: str) -> dict:
        """Fetch the full title given the title number and version date"""
        response = await self.client.get(f"{self.base_url}/versioner/v1/full/{version_date}/title-{title_number}.xml")
        if response.status_code == 404:
            return {"title": {}}
        return response.text
    
    async def close(self):
        await self.client.aclose()

class DataProcessor:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def process_agencies(self, agencies_data: dict):
        for agency_data in agencies_data["agencies"]:
            agency = models.Agency(
                agency_id=agency_data["slug"],
                name=agency_data["name"],
                short_name=agency_data["short_name"],
                display_name=agency_data["display_name"],
                sortable_name=agency_data["sortable_name"],
                docs=agency_data["cfr_references"],
                slug=agency_data["slug"]
            )
            self.session.add(agency)
        
        await self.session.commit()
    
    async def process_titles(self, titles_data: dict):
        for title_data in titles_data["titles"]:
            title = models.Title(
                number=title_data["number"],
                name=title_data["name"],
                latest_amended_on=datetime.strptime(title_data["latest_amended_on"], "%Y-%m-%d").date() if title_data["latest_amended_on"] else None,
                latest_issue_date=datetime.strptime(title_data["latest_issue_date"], "%Y-%m-%d").date() if title_data["latest_issue_date"] else None,
                up_to_date_as_of=datetime.strptime(title_data["up_to_date_as_of"], "%Y-%m-%d").date() if title_data["up_to_date_as_of"] else None,
                reserved=title_data["reserved"]
            )
            self.session.add(title)
        
        await self.session.commit()

    async def process_title_versions(self, title_number: int, versions_data: dict):
        """Process and store title versions"""
        for version in versions_data.get("content_versions", []):
            title_version = models.TitleVersion(
                title_number=title_number,
                version_date=datetime.strptime(version["date"], "%Y-%m-%d").date(),
                amendment_date=datetime.strptime(version["amendment_date"], "%Y-%m-%d").date(),
                issue_date=datetime.strptime(version["issue_date"], "%Y-%m-%d").date(),
                identifier=version["identifier"],
                name=version["name"],
                part=version["part"],
                substantive=version["substantive"],
                removed=version["removed"],
                subpart=version.get("subpart"),  # Some might not have subpart
                type=version["type"]
            )
            self.session.add(title_version)
        
        try:
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e