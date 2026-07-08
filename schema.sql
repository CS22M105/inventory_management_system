-- NOTE: As of Phase 2 (Alembic), this file is a readable reference and a
-- convenience for local dev bootstrap only. The SOURCE OF TRUTH for schema
-- changes is the migrations/ directory. For any new/production database, run
-- `alembic upgrade head` instead of applying this file. The baseline revision
-- (migrations/versions/0001_baseline.py) mirrors the CREATE statements below.

DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS users;
DROP SEQUENCE IF EXISTS item_barcode_number_seq;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    institution_id TEXT UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    department TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    barcode TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    bin_location TEXT NOT NULL,
    room TEXT NOT NULL,
    company TEXT,
    quantity INTEGER NOT NULL DEFAULT 0,
    minimum_quantity INTEGER NOT NULL DEFAULT 0,
    location TEXT,
    expiration_date DATE,
    notes TEXT
);

CREATE SEQUENCE item_barcode_number_seq START WITH 1;

CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    transaction_type TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
    transaction_time TIME(0) NOT NULL DEFAULT LOCALTIME(0),
    lab_instructor TEXT,
    topic_of_day TEXT,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT,
    FOREIGN KEY (item_id) REFERENCES items (id) ON DELETE RESTRICT
);

-- Seed users have no password_hash yet (invited state). Set one with:
--   flask --app app set-password <email> <password>
INSERT INTO users (institution_id, email, name, role, department)
VALUES
    ('S1001', 'student@example.edu', 'Demo Student', 'student', 'Nursing'),
    ('F1001', 'faculty@example.edu', 'Demo Faculty', 'faculty', 'Nursing'),
    ('A1001', 'admin@example.edu', 'Demo Administrator', 'administrator', 'Simulation Lab');
