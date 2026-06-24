DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    institution_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    department TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
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
    expiration_date TEXT,
    notes TEXT
);

CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    transaction_type TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
    transaction_time TIME(0) NOT NULL DEFAULT LOCALTIME(0),
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT,
    FOREIGN KEY (item_id) REFERENCES items (id) ON DELETE RESTRICT
);

INSERT INTO users (institution_id, name, role, department)
VALUES
    ('S1001', 'Demo Student', 'student', 'Nursing'),
    ('F1001', 'Demo Faculty', 'faculty', 'Nursing'),
    ('A1001', 'Demo Administrator', 'administrator', 'Simulation Lab');
