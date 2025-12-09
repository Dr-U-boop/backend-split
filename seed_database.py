import sqlite3
import random
from faker import Faker
from datetime import datetime, timedelta
from app.encryption_utils import encrypt_data
import json

DB_NAME = "medical_app.db"
NUM_PATIENTS = 5
DAYS_OF_DATA = 30

DEFAULT_PARAMETERS = {
    "mt": 79.7963,
    "Vi": 0.05,
    "ki1": 0.19,
    "ki2": 0.27,
    "ki3": 0.3484,
    "kgabs": 0.057,
    "kgri": 0.056,
    "kmin": 0.008,
    "kmax": 0.056,
    "k1gg": 0.065,
    "k2gg": 0.079,
    "ucns": 0.35,
    "vidb": 1.0,
    "kres": 0.0731,
    "k1e": 0.05,
    "k2e": 188.333,
    "k1abs": 0.0297,
    "k2abs": 0.0113,
    "ks": 0.2,
    "kd": 1.0,
    "ksen": 1.0,
    "lbh": 5.0,
    "gth": 199.08,
    "kh1": 0.001,
    "kh2": 0.001,
    "kh3": 0.001,
    "kh4": 0.001,
    "k1gl": 0.02,
    "k2gl": 0.1,
    "kh5": 0.001,
    "kh6": 0.001,
    "k1gng": 0.0084,
    "k2gng": 0.0048,
    "kKc": 0.0035,
    "ib": 104.08,
    "gb": 199.08,
    "g0": 210.24,
    "Il0": 2.61,
    "Ip0": 5.2045,
    "fgut0": 0.0,
    "fliq0": 0.0,
    "fsol0": 0.0,
    "gt0": 210.0,
    "Xt0": 0.0,
    "Ii0": 4120.5,
    "It0": 10830.0,
    "Hp0": 50.2757,
    "SRsh0": 5.0276,
    "gl0": 210.0,
    "Phn10": 0.4932,
    "Pha10": 9.5018,
    "Phn20": 5.7039,
    "Pha20": 0.2961,
    "yg0": 20000.0,
    "PCa0": 0.9887,
    "PCn0": 0.0513,
    "pyr0": 0.0,
    "Er0": 10.0,
    "Er10": 10.0,
    "kret": 0.13,
    "kdec": 0.68,
    "delth_g": 0.9,
    "vid": 0.087,
    "Kidb": 205.59,
    "vgg": 0.5,
    "vgl": 0.25,
    "Kgl": 75,
    "Kgn": 432,
    "Ki": 2.5,
    "vgng": 2,
    "Kgng": 0.5,
    "k1i": 0.19,
    "k2i": 0.27,
    "k3i": 0.3484,
    "di": 0.12,
    "dh": 0.1
}

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

        # Добавляем параметры для симуляции
        params_json = json.dumps(DEFAULT_PARAMETERS)
        encrypted_params = encrypt_data(params_json)
        cur.execute(
            "INSERT INTO patients_parameters (patient_id, encrypted_parameters) VALUES (?, ?)",
            (patient_id, encrypted_params)
        )

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