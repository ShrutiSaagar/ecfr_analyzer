
DROP TABLE IF EXISTS agencies CASCADE;
DROP TABLE IF EXISTS titles CASCADE;
DROP TABLE IF EXISTS title_version_statistics CASCADE;
DROP TABLE IF EXISTS processing_jobs CASCADE;
DROP TABLE IF EXISTS title_versions CASCADE;

-- Agencies table to store basic agency information
CREATE TABLE agencies (
    id SERIAL PRIMARY KEY,
    agency_id VARCHAR(100) UNIQUE,
    name TEXT NOT NULL,
    short_name VARCHAR(100),
    display_name TEXT,
    sortable_name TEXT,
    slug VARCHAR(255) UNIQUE,
    docs JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Store basic title information
CREATE TABLE titles (
    id SERIAL PRIMARY KEY,
    number INTEGER UNIQUE,
    name TEXT NOT NULL,
    latest_amended_on DATE,
    latest_issue_date DATE,
    up_to_date_as_of DATE,
    reserved BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Store version information and statistics for each title version
CREATE TABLE title_version_statistics (
    id SERIAL PRIMARY KEY,
    title_number INTEGER REFERENCES titles(number),
    version_date DATE NOT NULL,
    amendment_date DATE,
    issue_date DATE,
    s3_path TEXT,  -- Path to XML content in S3
    word_statistics JSONB, -- Hierarchical structure with word counts
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(title_number, version_date)
);

-- Track processing status and coordination
CREATE TABLE processing_jobs (
    id SERIAL PRIMARY KEY,
    job_type VARCHAR(20) NOT NULL, -- 'FETCH_CONTENT', 'PROCESS_WORDS'
    title_number INTEGER,
    version_date DATE,
    status VARCHAR(20) NOT NULL, -- 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'
    lock_id UUID,
    lock_acquired_at TIMESTAMP,
    attempts INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX idx_title_version_stats_date ON title_version_statistics(version_date);
CREATE INDEX idx_title_version_stats_title ON title_version_statistics(title_number);
-- CREATE INDEX idx_agency_mappings_agency ON agency_document_mappings(agency_id);
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX idx_word_statistics ON title_version_statistics USING gin (word_statistics);

-- Create function to update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updating timestamp
CREATE TRIGGER update_processing_jobs_updated_at
    BEFORE UPDATE ON processing_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


DROP TABLE IF EXISTS title_versions CASCADE;
-- Store title versions
CREATE TABLE title_versions (
    id SERIAL PRIMARY KEY,
    title_number INTEGER REFERENCES titles(number),
    version_date DATE NOT NULL,
    amendment_date DATE,
    issue_date DATE,
    identifier VARCHAR(100),
    name TEXT,
    part VARCHAR(100),
    substantive BOOLEAN,
    removed BOOLEAN,
    subpart VARCHAR(100),
    type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- UNIQUE(title_number, version_date, identifier)
);

-- Create indexes for common queries
CREATE INDEX idx_title_versions_title_date 
    ON title_versions(title_number, version_date);
CREATE INDEX idx_title_versions_identifier 
    ON title_versions(identifier);


DROP TABLE IF EXISTS version_processing_jobs CASCADE;

-- Table to track processing jobs
CREATE TABLE version_processing_jobs (
    id SERIAL PRIMARY KEY,
    title_number INTEGER REFERENCES titles(number),
    version_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'
    attempt_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP,
    error_message TEXT,
    lock_id UUID,
    lock_acquired_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_processing_task
        UNIQUE(title_number, version_date)
);

DROP TABLE IF EXISTS version_word_counts CASCADE;

-- Table to store word count results
CREATE TABLE version_word_counts (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES version_processing_jobs(id),
    title_number INTEGER NOT NULL REFERENCES titles(number),
    type VARCHAR(20) NOT NULL,
    code VARCHAR(20) NOT NULL,
    word_statistics JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_date DATE NOT NULL DEFAULT CURRENT_DATE,
    CONSTRAINT unique_version_word_counts UNIQUE (title_number, type, code, version_date)
);



I want to rename the content processing tasks table and the processing results table to something more appropriate and I want to use locks on records in the job table to avoid race condition between the workers.