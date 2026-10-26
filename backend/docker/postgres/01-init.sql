-- Runs once, when the PostgreSQL volume is created.

-- Trigram search for the airport autocomplete.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Database for the integration tests, isolated from development data.
CREATE DATABASE booking_test OWNER booking;
\connect booking_test
CREATE EXTENSION IF NOT EXISTS pg_trgm;
