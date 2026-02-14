# backend/database_setup.py
import sqlite3
import bcrypt
from app.encryption_utils import encrypt_data

DB_NAME = "medical_app.db"
TEST_PASSWORD = "supersecretpassword123"

password_bytes = TEST_PASSWORD.encode('utf-8')
salt = bcrypt.gensalt()
hashed_password = bcrypt.hashpw(password_bytes, salt)

con = sqlite3.connect(DB_NAME)
cur = con.cursor()

# Enable foreign keys
cur.execute("PRAGMA foreign_keys = ON;")

# doctors table
cur.execute("""
CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    full_name TEXT,
    specialization TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# patients table (with auth fields)
cur.execute("""
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id INTEGER,
    username TEXT UNIQUE,
    hashed_password TEXT,
    encrypted_full_name TEXT NOT NULL,
    encrypted_contact_info TEXT,
    date_of_birth DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctors (id)
)
""")

# migration for existing databases
cur.execute("PRAGMA table_info(patients)")
patients_columns = {row[1] for row in cur.fetchall()}
if "username" not in patients_columns:
    cur.execute("ALTER TABLE patients ADD COLUMN username TEXT UNIQUE")
if "hashed_password" not in patients_columns:
    cur.execute("ALTER TABLE patients ADD COLUMN hashed_password TEXT")

# medical_records table
cur.execute("""
CREATE TABLE IF NOT EXISTS medical_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    record_date TIMESTAMP NOT NULL,
    encrypted_record_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE
)
""")

# upsert test doctor
cur.execute("SELECT id FROM doctors WHERE username = 'doctor'")
if cur.fetchone() is None:
    cur.execute("""
    INSERT INTO doctors (username, hashed_password, full_name, specialization)
    VALUES (?, ?, ?, ?)
    """, ("doctor", hashed_password, "Ivan Petrovich Sidorov", "Therapist"))
else:
    cur.execute("""
    UPDATE doctors
    SET full_name = ?, specialization = ?
    WHERE username = ?
    """, ("Ivan Petrovich Sidorov", "Therapist", "doctor"))

# upsert test patient with login/password
cur.execute("SELECT id FROM doctors WHERE username = 'doctor'")
doctor_row = cur.fetchone()
doctor_id = doctor_row[0] if doctor_row else None

if doctor_id is not None:
    encrypted_test_name = encrypt_data("Test Patient")
    encrypted_test_contact = encrypt_data("test_patient@example.com")

    cur.execute("SELECT id FROM patients WHERE username = 'test_patient'")
    if cur.fetchone() is None:
        cur.execute("""
        INSERT INTO patients (
            doctor_id,
            username,
            hashed_password,
            encrypted_full_name,
            encrypted_contact_info,
            date_of_birth
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            doctor_id,
            "test_patient",
            hashed_password,
            encrypted_test_name,
            encrypted_test_contact,
            "1990-01-01"
        ))
    else:
        cur.execute("""
        UPDATE patients
        SET doctor_id = ?,
            hashed_password = ?,
            encrypted_full_name = ?,
            encrypted_contact_info = ?,
            date_of_birth = ?
        WHERE username = ?
        """, (
            doctor_id,
            hashed_password,
            encrypted_test_name,
            encrypted_test_contact,
            "1990-01-01",
            "test_patient"
        ))

# timeseries_data table
cur.execute("""
CREATE TABLE IF NOT EXISTS timeseries_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    timestamp TIMESTAMP NOT NULL,
    record_type TEXT NOT NULL,
    value REAL NOT NULL,
    encrypted_details TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE
)
""")

# simulator_scenarios table
cur.execute("""
CREATE TABLE IF NOT EXISTS simulator_scenarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    encrypted_scenario TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE
)
""")

# patients_parameters table
cur.execute("""
CREATE TABLE IF NOT EXISTS patients_parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    encrypted_parameters TEXT NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE
)
""")

con.commit()
con.close()

print(f"Database '{DB_NAME}' updated successfully.")