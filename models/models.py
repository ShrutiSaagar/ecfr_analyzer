from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from db.db import Base
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid

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

class TitleVersion(Base):
    __tablename__ = "title_versions"
    
    id = Column(Integer, primary_key=True)
    title_number = Column(Integer, ForeignKey("titles.number"))
    version_date = Column(Date, nullable=False)
    amendment_date = Column(Date)
    issue_date = Column(Date)
    identifier = Column(String(100))
    name = Column(String)
    part = Column(String(100))
    substantive = Column(Boolean)
    removed = Column(Boolean)
    subpart = Column(String(100))
    type = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AgencyTitleMapping(Base):
    __tablename__ = 'agency_title_mappings'
    
    id = Column(Integer, primary_key=True)
    agency_id = Column(String(100), ForeignKey('agencies.agency_id'))
    title_number = Column(Integer, ForeignKey('titles.number'))
    xpath_expressions = Column(JSONB)
    created_at = Column(DateTime, default=func.now())

class VersionProcessingJobs(Base):
    __tablename__ = 'version_processing_jobs'
    
    id = Column(Integer, primary_key=True)
    title_number = Column(Integer, ForeignKey('titles.number'))
    version_date = Column(Date, nullable=False)
    status = Column(String(20), default='PENDING')
    attempt_count = Column(Integer, default=0)
    last_attempt_at = Column(DateTime)
    error_message = Column(String(500))
    lock_id = Column(UUID(as_uuid=True), default=uuid.uuid4)
    lock_acquired_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # __table_args__ = (
    #     UniqueConstraint('title_number', 'version_date', name='unique_processing_task'),
    # )

class VersionWordCounts(Base):
    __tablename__ = 'version_word_counts'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('version_processing_jobs.id'))
    title_number = Column(Integer, nullable=False)
    type = Column(String(100))  # Indicates whether it is a chapter, subtitle, etc.
    code = Column(String(100))  # The chapter or subtitle number
    word_statistics = Column(JSONB)
    created_at = Column(DateTime, default=func.now())
    version_date = Column(Date, nullable=False)
