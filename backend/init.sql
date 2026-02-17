-- PortAct Database Initialization SQL Script
-- This script creates the database, user, and sets up initial configuration
-- Run this script as PostgreSQL superuser (postgres)

-- Create database user if not exists
DO
$$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'portact_user') THEN
        CREATE USER portact_user WITH PASSWORD 'CHANGE_THIS_PASSWORD';
    END IF;
END
$$;

-- Create database if not exists
SELECT 'CREATE DATABASE portact_db OWNER portact_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'portact_db')\gexec

-- Connect to the database
\c portact_db

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE portact_db TO portact_user;
GRANT ALL ON SCHEMA public TO portact_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO portact_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO portact_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO portact_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO portact_user;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create audit trigger function for tracking changes
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully!';
    RAISE NOTICE 'Database: portact_db';
    RAISE NOTICE 'User: portact_user';
    RAISE NOTICE 'Next step: Run Alembic migrations to create tables';
END $$;

-- Made with Bob
