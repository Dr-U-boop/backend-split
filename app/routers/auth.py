from fastapi import APIRouter, Depends, HTTPException
import bcrypt
import sqlite3

from app.auth_utils import create_access_token, get_current_doctor, get_current_patient, row_to_patient_display
from app.models import UserCredentials

router = APIRouter()
DB_NAME = "medical_app.db"


@router.post("/login")
async def login_doctor(credentials: UserCredentials):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM doctors WHERE username = ?", (credentials.username,))
    user_record = cur.fetchone()
    con.close()

    if not user_record:
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")

    stored_hashed_password = user_record["hashed_password"]
    password_bytes = credentials.password.encode("utf-8")
    if not bcrypt.checkpw(password_bytes, stored_hashed_password):
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")

    access_token = create_access_token(
        data={
            "sub": user_record["username"],
            "role": "doctor",
            "doctor_id": user_record["id"],
        }
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/patient/login")
async def login_patient(credentials: UserCredentials):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM patients WHERE username = ?", (credentials.username,))
    patient_record = cur.fetchone()
    con.close()

    if not patient_record or not patient_record["hashed_password"]:
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")

    stored_hashed_password = patient_record["hashed_password"]
    password_bytes = credentials.password.encode("utf-8")
    if not bcrypt.checkpw(password_bytes, stored_hashed_password):
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")

    access_token = create_access_token(
        data={
            "sub": patient_record["username"],
            "role": "patient",
            "patient_id": patient_record["id"],
        }
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
def read_doctor_me(current_doctor: dict = Depends(get_current_doctor)):
    return {
        "username": current_doctor["username"],
        "full_name": current_doctor["full_name"],
        "specialization": current_doctor["specialization"],
        "role": "doctor",
    }


@router.get("/patient/me")
def read_patient_me(current_patient: dict = Depends(get_current_patient)):
    patient = row_to_patient_display(current_patient)
    return {
        "id": patient.id,
        "username": current_patient["username"],
        "full_name": patient.full_name,
        "date_of_birth": patient.date_of_birth,
        "contact_info": patient.contact_info,
        "doctor_id": patient.doctor_id,
        "role": "patient",
    }
