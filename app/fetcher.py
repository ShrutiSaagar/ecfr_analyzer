import httpx
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from . import models
import json

class ECFRFetcher:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def fetch_agencies(self) -> dict:
        response = await self.client.get(f"{self.base_url}/admin/v1/agencies.json")
        return response.json()
    
    async def fetch_titles(self) -> dict:
        response = await self.client.get(f"{self.base_url}/versioner/v1/titles.json")
        return response.json()
    
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
