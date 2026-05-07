-- Postgres extensions required by the platform. Loaded automatically by
-- docker-entrypoint-initdb.d on first container start.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
