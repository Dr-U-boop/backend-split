import sqlite3
import random
from faker import Faker
from datetime import datetime, timedelta
from app.encryption_utils import encrypt_data

DB_NAME = "medical_app.db"
NUM_PATIENTS = 5
DAYS_OF_DATA = 30

fake = Faker('ru_RU')

def simulate_day_data(start_time):
    records = []
    current_time = start_time
    glucose_level = random.uniform(5.0, 8.0)

    for minute_interval in range(24 * 12): # 288 points per day (every 5 mins)
        current_time += timedelta(minutes=5)
        
        # Meal simulation
        if current_time.hour in [8, 13, 19] and current_time.minute == 0:
            carbs = random.randint(30, 80)
            records.append((current_time, 'carbs', carbs, encrypt_data(f"Прием пищи, {carbs} г угл.")))
            glucose_level += (carbs / 15) # Simplified glucose rise
            
            insulin_dose = round(carbs / 10, 1) # Simplified insulin dose
            records.append((current_time, 'insulin_bolus', insulin_dose, encrypt_data("Быстрый инсулин на еду")))
            glucose_level -= (insulin_dose * 1.5) # Simplified insulin effect
        
        # Natural fluctuations
        glucose_level += random.uniform(-0.2, 0.1)
        glucose_level = max(3.0, min(18.0, glucose_level)) # Keep within a realistic range

        records.append((current_time, 'glucose', round(glucose_level, 1), None))
        #records.append((current_time, 'carbs', carbs, encrypt_data(f"Прием пищи, {carbs} г угл.")))
        #records.append((current_time, 'insulin_bolus', insulin_dose, encrypt_data("Быстрый инсулин на еду")))
        
    return records

def seed_data():
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    print(f"Генерация данных для {NUM_PATIENTS} пациентов...")
    
    cur.execute("SELECT id FROM doctors WHERE username = 'doctor'")
    doctor_id = cur.fetchone()[0]

    for i in range(NUM_PATIENTS):
        full_name = fake.name()
        date_of_birth = fake.date_of_birth(minimum_age=20, maximum_age=70)
        contact_info = fake.phone_number()
        
        cur.execute(
            "INSERT INTO patients (doctor_id, encrypted_full_name, date_of_birth, encrypted_contact_info) VALUES (?, ?, ?, ?)",
            (doctor_id, encrypt_data(full_name), date_of_birth, encrypt_data(contact_info))
        )
        patient_id = cur.lastrowid
        print(f"  Создан пациент: {full_name} (ID: {patient_id})")

        all_timeseries_data = []
        start_date = datetime.now() - timedelta(days=DAYS_OF_DATA)
        for day in range(DAYS_OF_DATA):
            daily_records = simulate_day_data(
            datetime.combine((start_date + timedelta(days=day)).date(), datetime.min.time()))
            for record in daily_records:
                all_timeseries_data.append((patient_id, *record))

        cur.executemany(
            "INSERT INTO timeseries_data (patient_id, timestamp, record_type, value, encrypted_details) VALUES (?, ?, ?, ?, ?)",
            all_timeseries_data
        )
        print(f"    -> Добавлено {len(all_timeseries_data)} записей.")

    con.commit()
    con.close()
    print("\nГенерация данных успешно завершена!")

if __name__ == "__main__":
    seed_data()