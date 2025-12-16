# backend/database_setup.py
import sqlite3
import bcrypt
from datetime import datetime

DB_NAME = "medical_app.db"
TEST_PASSWORD = "supersecretpassword123"

password_bytes = TEST_PASSWORD.encode('utf-8')
salt = bcrypt.gensalt()
hashed_password = bcrypt.hashpw(password_bytes, salt)

con = sqlite3.connect(DB_NAME)
cur = con.cursor()

# --- Включаем поддержку внешних ключей (foreign keys) ---
cur.execute("PRAGMA foreign_keys = ON;")

# --- Обновляем/Создаем таблицу doctors ---
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

# --- Создаем таблицу patients ---
cur.execute("""
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id INTEGER,
    encrypted_full_name TEXT NOT NULL,
    encrypted_contact_info TEXT,
    date_of_birth DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctors (id)
)
""")

# --- Создаем таблицу medical_records ---
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

# --- Добавляем/Обновляем тестового врача ---
cur.execute("SELECT id FROM doctors WHERE username = 'doctor'")
if cur.fetchone() is None:
    cur.execute("""
    INSERT INTO doctors (username, hashed_password, full_name, specialization)
    VALUES (?, ?, ?, ?)
    """, ("doctor", hashed_password, "Иван Петрович Сидоров", "Терапевт"))
else:
    cur.execute("""
    UPDATE doctors 
    SET full_name = ?, specialization = ? 
    WHERE username = ?
    """, ("Иван Петрович Сидоров", "Терапевт", "doctor"))

# ... (внутри файла database_setup.py)

# --- Создаем таблицу для временных рядов ---
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

# --- Создаем таблицу для сценариев симулятора ---
cur.execute("""
CREATE TABLE IF NOT EXISTS simulator_scenarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    encrypted_scenario TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE
)
""")

# --- Создаем таблицу для параметров пациентов ---
cur.execute("""
CREATE TABLE IF NOT EXISTS patients_parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    encrypted_parameters TEXT NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE
)
""")

# ... (в конце файла)
print(f"Таблица 'timeseries_data' успешно создана/проверена.")


con.commit()
con.close()

print(f"База данных '{DB_NAME}' успешно обновлена по новой схеме.")