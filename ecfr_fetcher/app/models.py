from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from .db import Base
from sqlalchemy.dialects.postgresql import JSONB

class Agency(Base):
    __tablename__ = "agencies"
    
    id = Column(Integer, primary_key=True)
    agency_id = Column(String(100), unique=True)
    name = Column(String, nullable=False)
    short_name = Column(String(100))
    display_name = Column(String)
    sortable_name = Column(String)
    docs = Column(JSONB)
    slug = Column(String(255), unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AgencyDocumentMapping(Base):
    __tablename__ = "agency_document_mappings"
    
    id = Column(Integer, primary_key=True)
    agency_id = Column(String(50), ForeignKey("agencies.agency_id"))
    title_number = Column(Integer)
    chapter = Column(String(50))
    subchapter = Column(String(50))
    part = Column(String(50))
    subtitle = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Title(Base):
    __tablename__ = "titles"
    
    id = Column(Integer, primary_key=True)
    number = Column(Integer, unique=True)
    name = Column(String, nullable=False)
    latest_amended_on = Column(Date)
    latest_issue_date = Column(Date)
    up_to_date_as_of = Column(Date)
    reserved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
