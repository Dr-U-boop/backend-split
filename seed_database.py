import sqlite3
from faker import Faker
from datetime import datetime, timedelta
from app.encryption_utils import encrypt_data
import json
import scipy.io
import numpy as np
import os
import itertools

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

DEFAULT_SCENARIO = {
    "M": 90.0,
    "tm": 60.0,
    "Tm": 20.0,
    "kbol": 1.4,
    "kw": 0.4,
    "t0": 0,
    "t1": 720,
    "ti_1": 30.0,
    "ti_2": 60.0,
    "Ti_1": 10.0,
    "Ti_2": 10.0,
    "OB": 0.05263157894736842,
    "Di": 6.63157894736842,
    "Dbol_1": 2.6526315789473682,
    "Dbol_2": 3.978947368421052,
    "Vbas": 1.2237
}

fake = Faker('ru_RU')


def build_carb_schedule(daily_glucose_profile, interval_minutes=30):
    points_per_day = len(daily_glucose_profile)
    glucose_values = [float(value) for value in daily_glucose_profile]

    meal_windows = [
        ((6, 0), (9, 30)),
        ((11, 0), (14, 30)),
        ((17, 0), (20, 30)),
    ]
    carb_schedule = {}

    def time_to_index(hours, minutes):
        return (hours * 60 + minutes) // interval_minutes

    for start_window, end_window in meal_windows:
        start_idx = max(0, time_to_index(*start_window))
        end_idx = min(points_per_day - 3, time_to_index(*end_window))
        best_idx = start_idx
        best_rise = float('-inf')

        for idx in range(start_idx, end_idx + 1):
            current_level = glucose_values[idx]
            future_slice = glucose_values[idx + 1:idx + 4]
            if not future_slice:
                continue

            future_peak = max(future_slice)
            rise_score = future_peak - current_level

            if rise_score > best_rise:
                best_rise = rise_score
                best_idx = idx

        rise_strength = max(0.0, best_rise)
        carbs = int(round(25 + min(rise_strength * 4, 55)))
        carbs = max(20, min(carbs, 80))
        meal_minutes = best_idx * interval_minutes
        carb_schedule[(meal_minutes // 60, meal_minutes % 60)] = carbs

    return carb_schedule


def simulate_day_data(start_time, glucose_iterator, carb_schedule):
    records = []
    current_time = start_time
    interval_minutes = 30
    points_per_day = (24 * 60) // interval_minutes

    for _ in range(points_per_day):
        current_time += timedelta(minutes=interval_minutes)
        glucose_val = next(glucose_iterator)

        meal_key = (current_time.hour, current_time.minute)
        if meal_key in carb_schedule:
            carbs = carb_schedule[meal_key]
            records.append((current_time, 'carbs', carbs, encrypt_data(f"Meal, {carbs} g carbs")))
            insulin_dose = round(carbs / 10, 1)
            records.append((current_time, 'insulin_bolus', insulin_dose, encrypt_data("Rapid insulin for meal")))

        records.append((current_time, 'glucose', round(float(glucose_val), 1), None))

    return records


def seed_patient_related_data(cur, patient_id, glucose_iterator, carb_schedule):
    params_json = json.dumps(DEFAULT_PARAMETERS)
    sim_json = json.dumps(DEFAULT_SCENARIO)

    encrypted_params = encrypt_data(params_json)
    encrypted_sim = encrypt_data(sim_json)

    # Rerun-safe behavior: recreate generated data for this patient.
    cur.execute("DELETE FROM patients_parameters WHERE patient_id = ?", (patient_id,))
    cur.execute("DELETE FROM simulator_scenarios WHERE patient_id = ?", (patient_id,))
    cur.execute("DELETE FROM timeseries_data WHERE patient_id = ?", (patient_id,))

    cur.execute(
        "INSERT INTO patients_parameters (patient_id, encrypted_parameters) VALUES (?, ?)",
        (patient_id, encrypted_params)
    )
    cur.execute(
        "INSERT INTO simulator_scenarios (patient_id, encrypted_scenario) VALUES (?, ?)",
        (patient_id, encrypted_sim)
    )

    all_timeseries_data = []
    start_date = datetime.now() - timedelta(days=DAYS_OF_DATA)
    for day in range(DAYS_OF_DATA):
        daily_records = simulate_day_data(
            datetime.combine((start_date + timedelta(days=day)).date(), datetime.min.time()),
            glucose_iterator,
            carb_schedule
        )
        for record in daily_records:
            all_timeseries_data.append((patient_id, *record))

    cur.executemany(
        "INSERT INTO timeseries_data (patient_id, timestamp, record_type, value, encrypted_details) VALUES (?, ?, ?, ?, ?)",
        all_timeseries_data
    )

    return len(all_timeseries_data)


def seed_data():
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    print(f"Generating data for {NUM_PATIENTS} random patients...")

    cur.execute("SELECT id FROM doctors WHERE username = 'doctor'")
    doctor_row = cur.fetchone()
    if not doctor_row:
        print("Doctor 'doctor' not found. Run database_setup.py first.")
        con.close()
        return
    doctor_id = doctor_row[0]

    mat_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Multibolus.mat')
    try:
        mat_data = scipy.io.loadmat(mat_file_path)
        x_data = mat_data['x'].flatten()
        print(f"Loaded x data from {mat_file_path}, shape: {x_data.shape}")
    except Exception as e:
        print(f"Error loading {mat_file_path}: {e}")
        con.close()
        return

    points_per_day = (24 * 60) // 30
    sampled_indices = np.linspace(0, len(x_data) - 1, points_per_day, dtype=int)
    daily_glucose_profile = x_data[sampled_indices]
    glucose_iterator = itertools.cycle(daily_glucose_profile)
    carb_schedule = build_carb_schedule(daily_glucose_profile)

    for _ in range(NUM_PATIENTS):
        full_name = fake.name()
        date_of_birth = fake.date_of_birth(minimum_age=20, maximum_age=70)
        contact_info = fake.phone_number()

        cur.execute(
            "INSERT INTO patients (doctor_id, encrypted_full_name, date_of_birth, encrypted_contact_info) VALUES (?, ?, ?, ?)",
            (doctor_id, encrypt_data(full_name), date_of_birth, encrypt_data(contact_info))
        )
        patient_id = cur.lastrowid
        print(f"  Created patient: {full_name} (ID: {patient_id})")

        inserted_count = seed_patient_related_data(cur, patient_id, glucose_iterator, carb_schedule)
        print(f"    -> Inserted {inserted_count} time-series rows.")

    # Add generated data for the fixed test patient created in database_setup.py.
    cur.execute("SELECT id FROM patients WHERE username = 'test_patient'")
    test_patient_row = cur.fetchone()
    if test_patient_row:
        test_patient_id = test_patient_row[0]
        print(f"  Found test_patient (ID: {test_patient_id}), seeding data...")
        inserted_count = seed_patient_related_data(cur, test_patient_id, glucose_iterator, carb_schedule)
        print(f"    -> Inserted {inserted_count} time-series rows for test_patient.")
    else:
        print("  test_patient not found, skipping.")

    con.commit()
    con.close()
    print("\nData generation completed successfully.")


if __name__ == "__main__":
    seed_data()
