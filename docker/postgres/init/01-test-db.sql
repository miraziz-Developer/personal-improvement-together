-- Separate database for integration tests, so tests never touch development data.
CREATE DATABASE pit_test OWNER pit;
