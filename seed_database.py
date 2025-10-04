# backend/seed_database.py
import sqlite3
import random
from faker import Faker
from datetime import datetime, timedelta
from app.encryption_utils import encrypt_data

DB_NAME = "medical_app.db"
NUM_PATIENTS = 5  # Сколько пациентов создать
DAYS_OF_DATA = 62 # За сколько последних дней сгенерировать данные

# Инициализируем Faker для генерации русскоязычных данных
fake = Faker('ru_RU')

def simulate_glucose_and_insulin(start_time):
    """
    Симулирует данные о глюкозе и инсулине за 24 часа для одного пациента.
    Возвращает список кортежей для вставки в БД.
    """
    records = []
    current_time = start_time
    # Начальный уровень глюкозы (в ммоль/л)
    glucose_level = random.uniform(5.0, 8.0)

    # Симулируем показания каждые 5 минут в течение суток
    for _ in range(24 * 12): # 288 точек в день
        # Имитация приемов пищи (пики глюкозы)
        if current_time.hour in [8, 13, 19]: # Завтрак, обед, ужин
            glucose_level += random.uniform(1.5, 3.0)
        
        # Имитация введения болюсного инсулина (после еды)
        if current_time.hour in [8, 13, 19] and current_time.minute == 5:
            insulin_dose = random.uniform(4.0, 8.0)
            records.append((current_time, 'insulin_bolus', insulin_dose, None))
            glucose_level -= random.uniform(1.0, 2.5) # Эффект инсулина
            
        # Естественное снижение и колебания глюкозы
        glucose_level -= random.uniform(0.1, 0.3)
        glucose_level = max(3.0, glucose_level) # Глюкоза не падает слишком низко

        records.append((current_time, 'glucose', round(glucose_level, 1), None))
        current_time += timedelta(minutes=5)

    return records


def seed_data():
    """
    Главная функция для заполнения базы данных.
    """
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()

    print(f"Генерация данных для {NUM_PATIENTS} пациентов...")
    
    # Получаем ID первого врача для привязки пациентов
    cur.execute("SELECT id FROM doctors WHERE username = 'doctor'")
    doctor_id_row = cur.fetchone()
    if not doctor_id_row:
        print("Ошибка: Врач с именем 'doctor' не найден. Запустите сначала database_setup.py")
        return
    doctor_id = doctor_id_row[0]

    for i in range(NUM_PATIENTS):
        # --- Создаем пациента ---
        full_name = fake.name()
        date_of_birth = fake.date_of_birth(minimum_age=20, maximum_age=70)
        contact_info = fake.phone_number()
        
        encrypted_name = encrypt_data(full_name)
        encrypted_contact = encrypt_data(contact_info)

        cur.execute(
            "INSERT INTO patients (doctor_id, encrypted_full_name, date_of_birth, encrypted_contact_info) VALUES (?, ?, ?, ?)",
            (doctor_id, encrypted_name, date_of_birth, encrypted_contact)
        )
        patient_id = cur.lastrowid
        print(f"  Создан пациент: {full_name} (ID: {patient_id})")

        # --- Генерируем для него временные данные ---
        all_timeseries_data = []
        start_date = datetime.now() - timedelta(days=DAYS_OF_DATA)
        
        for day in range(DAYS_OF_DATA):
            day_start_time = start_date + timedelta(days=day)
            daily_records = simulate_glucose_and_insulin(day_start_time)
            for record in daily_records:
                # Добавляем patient_id к каждой записи
                all_timeseries_data.append((patient_id, *record))

        # Вставляем все сгенерированные данные в БД одной командой
        cur.executemany(
            "INSERT INTO timeseries_data (patient_id, timestamp, record_type, value, encrypted_details) VALUES (?, ?, ?, ?, ?)",
            all_timeseries_data
        )
        print(f"    -> Добавлено {len(all_timeseries_data)} записей о глюкозе/инсулине.")

    con.commit()
    con.close()
    print("\nГенерация данных успешно завершена!")

if __name__ == "__main__":
    seed_data()