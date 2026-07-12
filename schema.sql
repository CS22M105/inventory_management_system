-- NOTE: As of Phase 2 (Alembic), this file is a readable reference and a
-- convenience for local dev bootstrap only. The SOURCE OF TRUTH for schema
-- changes is the migrations/ directory. For any new/production database, run
-- `alembic upgrade head` instead of applying this file. The baseline revision
-- (migrations/versions/0001_baseline.py) mirrors the CREATE statements below.

DROP TABLE IF EXISTS audit_events;
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

CREATE TABLE audit_events (
    id SERIAL PRIMARY KEY,
    actor_user_id INTEGER,
    event_type TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    details TEXT,
    ip_address TEXT,
    request_id TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- Performance indexes (mirror migration 0004_transaction_indexes). Support the
-- /transactions list ORDER BY and its item/user/date filters, plus items sort.
CREATE INDEX ix_transactions_item_id ON transactions (item_id);
CREATE INDEX ix_transactions_user_id ON transactions (user_id);
CREATE INDEX ix_transactions_transaction_date ON transactions (transaction_date);
CREATE INDEX ix_transactions_date_time_id
    ON transactions (transaction_date DESC, transaction_time DESC, id DESC);
CREATE INDEX ix_items_name ON items (name);
CREATE INDEX ix_audit_events_created_at
    ON audit_events (created_at DESC, id DESC);
CREATE INDEX ix_audit_events_actor_user_id ON audit_events (actor_user_id);
CREATE INDEX ix_audit_events_event_type ON audit_events (event_type);

-- Seed users have no password_hash yet (invited state). Set one with:
--   flask --app app set-password <email> <password>
INSERT INTO users (institution_id, email, name, role, department)
VALUES
    ('S1001', 'student@example.edu', 'Demo Student', 'student', 'Nursing'),
    ('F1001', 'faculty@example.edu', 'Demo Faculty', 'faculty', 'Nursing'),
    ('A1001', 'admin@example.edu', 'Demo Administrator', 'administrator', 'Simulation Lab');
