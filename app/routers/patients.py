from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
import sqlite3
from app.models import PatientCreate, PatientDisplay, MedicalRecordCreate
from app.auth_utils import get_current_doctor
from app.encryption_utils import encrypt_data, decrypt_data
from app.analysis_utils import analyze_patient_data
from datetime import datetime, timedelta, time

router = APIRouter()
DB_NAME = "medical_app.db"

@router.post("/", response_model=PatientDisplay, status_code=status.HTTP_201_CREATED)
def create_patient(patient: PatientCreate, current_doctor: dict = Depends(get_current_doctor)):
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()

    encrypted_name = encrypt_data(patient.full_name)
    encrypted_contact = encrypt_data(patient.contact_info) if patient.contact_info else None

    cur.execute(
        """
        INSERT INTO patients (doctor_id, encrypted_full_name, date_of_birth, encrypted_contact_info)
        VALUES (?, ?, ?, ?)
        """,
        (current_doctor["id"], encrypted_name, patient.date_of_birth, encrypted_contact)
    )

    new_patient_id = cur.lastrowid
    con.commit()
    con.close()

    return PatientDisplay(
        id = new_patient_id,
        doctor_id = current_doctor["id"],
        created_at = datetime.now(),
        **patient.dict()
    )

@router.get("/", response_model=List[PatientDisplay])
def get_my_patients(current_doctor: dict = Depends(get_current_doctor)):
    """Возвращает список всех пациентов для текущего врача."""
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    
    cur.execute("SELECT * FROM patients WHERE doctor_id = ?", (current_doctor["id"],))
    patients_records = cur.fetchall()
    con.close()
    
    patients_list = []
    for record in patients_records:
        patients_list.append(PatientDisplay(
            id=record["id"],
            doctor_id=record["doctor_id"],
            full_name=decrypt_data(record["encrypted_full_name"]),
            contact_info=decrypt_data(record["encrypted_contact_info"]) if record["encrypted_contact_info"] else None,
            date_of_birth=record["date_of_birth"],
            created_at=record["created_at"]
        ))
    return patients_list

@router.post("/{patient_id}/records", status_code=status.HTTP_201_CREATED)
def add_medical_record(patient_id: int, record: MedicalRecordCreate, current_doctor: dict = Depends(get_current_doctor)):
    """Добавляет новую медицинскую запись для указанного пациента."""
    # Здесь нужна проверка, что врач имеет право добавлять запись для этого пациента
    encrypted_data = encrypt_data(record.record_data)
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO medical_records (patient_id, record_date, encrypted_record_data) VALUES (?, ?, ?)",
        (patient_id, record.record_date, encrypted_data)
    )
    con.commit()
    con.close()
    return {"message": "Запись успешно добавлена"}

@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(patient_id: int, current_doctor: dict = Depends(get_current_doctor)):
    """Удаляет пациента и все его медицинские записи."""
    # Важно: проверить, что врач-владелец удаляет своего пациента
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("DELETE FROM patients WHERE id = ? AND doctor_id = ?", (patient_id, current_doctor["id"]))
    con.commit()
    if cur.rowcount == 0:
        con.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пациент не найден или у вас нет прав на его удаление")
    con.close()
    return

@router.get("/{patient_id}", response_model=PatientDisplay) # Для простоты пока оставим PatientDisplay
def get_patient_details(patient_id: int, current_doctor: dict = Depends(get_current_doctor)):
    """Возвращает детальную информацию о конкретном пациенте и его мед. записи."""
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Проверяем, существует ли пациент и принадлежит ли он этому врачу
    cur.execute("SELECT * FROM patients WHERE id = ? AND doctor_id = ?", (patient_id, current_doctor["id"]))
    patient_record = cur.fetchone()

    if not patient_record:
        con.close()
        raise HTTPException(status_code=status.HTTP_4_NOT_FOUND, detail="Пациент не найден")

    # Получаем медицинские записи для этого пациента
    cur.execute("SELECT * FROM medical_records WHERE patient_id = ? ORDER BY record_date DESC", (patient_id,))
    medical_records = cur.fetchall()
    con.close()

    # Дешифруем данные пациента
    patient_details = PatientDisplay(
        id=patient_record["id"],
        doctor_id=patient_record["doctor_id"],
        full_name=decrypt_data(patient_record["encrypted_full_name"]),
        contact_info=decrypt_data(patient_record["encrypted_contact_info"]) if patient_record["encrypted_contact_info"] else None,
        date_of_birth=patient_record["date_of_birth"],
        created_at=patient_record["created_at"]
    )
    
    # В будущем мы добавим записи в модель ответа
    # patient_details.records = [ ...дешифрованные записи... ]

    return patient_details

@router.get("/{patient_id}/glucose_data")
def get_patient_glucose_data(
    patient_id: int, 
    current_doctor: dict = Depends(get_current_doctor),
    start_datetime: Optional[datetime] = None, # <--- Принимаем полную дату и время
    end_datetime: Optional[datetime] = None
):
    """
    Возвращает данные о глюкозе. По умолчанию за последние 7 дней.
    Если даты и время указаны, фильтрует по ним.
    """
    # ... (проверка доступа врача остается без изменений) ...
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT id FROM patients WHERE id = ? AND doctor_id = ?", (patient_id, current_doctor["id"]))
    if cur.fetchone() is None:
        con.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пациент не найден")

    if start_datetime and end_datetime:
        query = """
            SELECT timestamp, value FROM timeseries_data 
            WHERE patient_id = ? AND record_type = 'glucose' AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
        """
        params = (patient_id, start_datetime, end_datetime)
    else:
        # --- ЛОГИКА ПО УМОЛЧАНИЮ (ПОСЛЕДНИЕ 7 ДНЕЙ) ---
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        query = """
            SELECT timestamp, value FROM timeseries_data 
            WHERE patient_id = ? AND record_type = 'glucose' AND timestamp >= ?
            ORDER BY timestamp ASC
        """
        params = (patient_id, seven_days_ago)
        
    cur.execute(query, params)
    glucose_records = cur.fetchall()
    con.close()

    labels = [datetime.fromisoformat(rec["timestamp"]).strftime('%d.%m %H:%M') for rec in glucose_records]
    data = [rec["value"] for rec in glucose_records]

    return {"labels": labels, "data": data}

 # backend/app/routers/patients.py
# ...

@router.get("/{patient_id}/comprehensive_data")
def get_patient_comprehensive_data(
    patient_id: int, 
    current_doctor: dict = Depends(get_current_doctor),
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None
):
    """
    Возвращает полный набор данных (глюкоза, инсулин, углеводы) за период.
    """
    # ... (проверка доступа врача остается без изменений) ...
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    # Проверяем, существует ли пациент и принадлежит ли он этому врачу
    cur.execute("SELECT * FROM patients WHERE id = ? AND doctor_id = ?", (patient_id, current_doctor["id"]))
    patient_record = cur.fetchone()

    if not patient_record:
        con.close()
        raise HTTPException(status_code=status.HTTP_4_NOT_FOUND, detail="Пациент не найден")
    
    if not (start_datetime and end_datetime):
        end_datetime = datetime.utcnow()
        start_datetime = end_datetime - timedelta(days=7)

    cur.execute(
        """
        SELECT timestamp, record_type, value FROM timeseries_data 
        WHERE patient_id = ? AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
        """,
        (patient_id, start_datetime, end_datetime)
    )
    records = cur.fetchall()
    con.close()

    # Форматируем данные в удобную для Chart.js структуру
    response_data = {
        "glucose": [],
        "insulin": [],
        "carbs": []
    }
    for rec in records:
        point = {"x": rec["timestamp"], "y": rec["value"]}
        if rec["record_type"] == 'glucose':
            response_data["glucose"].append(point)
        elif 'insulin' in rec["record_type"]:
            response_data["insulin"].append(point)
        elif rec["record_type"] == 'carbs':
            response_data["carbs"].append(point)

    return response_data

@router.get("/{patient_id}/recommendations")
def get_patient_recommendations(patient_id: int, current_doctor: dict = Depends(get_current_doctor)):
    """
    Анализирует данные пациента за последние 30 дней и возвращает рекомендации.
    """
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Проверяем, принадлежит ли пациент врачу
    cur.execute("SELECT id FROM patients WHERE id = ? AND doctor_id = ?", (patient_id, current_doctor["id"]))
    if cur.fetchone() is None:
        con.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пациент не найден")

    # Загружаем ВСЕ данные за месяц
    month_ago = datetime.utcnow() - timedelta(days=30)
    cur.execute(
        "SELECT timestamp, record_type, value FROM timeseries_data WHERE patient_id = ? AND timestamp >= ?",
        (patient_id, month_ago)
    )

    # Преобразуем строки в словари
    records = [
        {
            "timestamp": datetime.fromisoformat(rec["timestamp"]),
            "record_type": rec["record_type"],
            "value": rec["value"]
        }
        for rec in cur.fetchall()
    ]

    con.close()
    recommendations = analyze_patient_data(records)
    return {"recommendations": recommendations}
    con.close()
    recommendations = analyze_patient_data(records)
    return {"recommendations": recommendations}

@router.get("/{patient_id}/parameters")
def get_patient_parameters(patient_id: int, current_doctor: dict = Depends(get_current_doctor)):
    """
    Возвращает расшифрованные параметры симуляции пациента.
    """
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Проверка доступа
    cur.execute("SELECT id FROM patients WHERE id = ? AND doctor_id = ?", (patient_id, current_doctor["id"]))
    if cur.fetchone() is None:
        con.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пациент не найден")

    cur.execute("SELECT encrypted_parameters FROM patients_parameters WHERE patient_id = ?", (patient_id,))
    record = cur.fetchone()
    con.close()

    if not record:
        return {} # Или ошибка, если параметры обязательны

    try:
        decrypted_json_str = decrypt_data(record["encrypted_parameters"])
        import json
        return json.loads(decrypted_json_str)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ошибка дешифровки параметров: {str(e)}")
