-- =============================================================================
-- TNSE - Telegram News Search Engine
-- Database Initialization Script
-- =============================================================================
-- This script runs automatically when the PostgreSQL container starts for the
-- first time. It sets up extensions and performs initial configuration.
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For trigram-based text search

-- Set Russian as the default text search configuration
ALTER DATABASE tnse SET default_text_search_config = 'pg_catalog.russian';

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'TNSE database initialized successfully';
END $$;
