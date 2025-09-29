from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import sqlite3
from app.models import PatientCreate, PatientDisplay, MedicalRecordCreate
from app.auth_utils import get_current_doctor
from app.encryption_utils import encrypt_data, decrypt_data
from datetime import datetime

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
        created_at = datetime.utcnow(),
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
