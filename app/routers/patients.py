from datetime import datetime, timedelta
from typing import List, Optional
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth_utils import (
    ensure_doctor_access_to_patient,
    fetch_patient_comprehensive_data,
    fetch_patient_diary_entries,
    fetch_patient_glucose_data,
    fetch_patient_parameters,
    fetch_patient_recommendations,
    fetch_patient_scenarios,
    get_current_doctor,
    get_current_patient,
    row_to_patient_display,
)
from app.encryption_utils import encrypt_data
from app.models import (
    DiaryEntryDisplay,
    MedicalRecordCreate,
    PatientCreate,
    PatientDisplay,
    PatientTimeSeriesDataIngest,
    SimulatorScenario,
)

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
        (current_doctor["id"], encrypted_name, patient.date_of_birth, encrypted_contact),
    )

    new_patient_id = cur.lastrowid
    con.commit()
    con.close()

    return PatientDisplay(
        id=new_patient_id,
        doctor_id=current_doctor["id"],
        created_at=datetime.now(),
        **patient.dict(),
    )


@router.get("/", response_model=List[PatientDisplay])
def get_my_patients(current_doctor: dict = Depends(get_current_doctor)):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("SELECT * FROM patients WHERE doctor_id = ?", (current_doctor["id"],))
    patients_records = cur.fetchall()
    con.close()

    return [row_to_patient_display(record) for record in patients_records]


@router.get("/me", response_model=PatientDisplay)
def get_current_patient_profile(current_patient: dict = Depends(get_current_patient)):
    return row_to_patient_display(current_patient)


@router.get("/me/glucose_data")
def get_current_patient_glucose_data(
    current_patient: dict = Depends(get_current_patient),
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None,
):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    result = fetch_patient_glucose_data(cur, current_patient["id"], start_datetime, end_datetime)
    con.close()
    return result


@router.get("/me/comprehensive_data")
def get_current_patient_comprehensive_data(
    current_patient: dict = Depends(get_current_patient),
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None,
):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    result = fetch_patient_comprehensive_data(cur, current_patient["id"], start_datetime, end_datetime)
    con.close()
    return result


@router.get("/me/recommendations")
def get_current_patient_recommendations(current_patient: dict = Depends(get_current_patient)):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    result = fetch_patient_recommendations(cur, current_patient["id"])
    con.close()
    return result


@router.get("/me/parameters")
def get_current_patient_parameters(current_patient: dict = Depends(get_current_patient)):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    try:
        result = fetch_patient_parameters(cur, current_patient["id"])
    except Exception as e:
        con.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"РћС€РёР±РєР° РґРµС€РёС„СЂРѕРІРєРё РїР°СЂР°РјРµС‚СЂРѕРІ: {str(e)}",
        )
    con.close()
    return result


@router.get("/me/scenarios", response_model=List[SimulatorScenario])
def get_current_patient_scenarios(current_patient: dict = Depends(get_current_patient)):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    result = fetch_patient_scenarios(cur, current_patient["id"])
    con.close()
    return result


@router.get("/me/diary", response_model=List[DiaryEntryDisplay])
def get_current_patient_diary_entries(
    current_patient: dict = Depends(get_current_patient),
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None,
):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    result = fetch_patient_diary_entries(cur, current_patient["id"], start_datetime, end_datetime)
    con.close()
    return result


@router.post("/me/timeseries_data", status_code=status.HTTP_201_CREATED)
def add_current_patient_timeseries_data(
    payload: PatientTimeSeriesDataIngest,
    current_patient: dict = Depends(get_current_patient),
):
    if not payload.data_points:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Список data_points не должен быть пустым",
        )

    records_to_insert = []
    for point in payload.data_points:
        record_type = point.record_type.strip().lower()

        if record_type in {"glucose", "carbs"} or "insulin" in record_type:
            if point.value is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Для glucose/carbs/insulin поле value обязательно",
                )
            stored_value = point.value
            stored_type = record_type
        elif record_type in {"self_monitoring_diary", "diary", "patient_diary", "self_monitoring"}:
            if not point.details or not point.details.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Для записи дневника требуется непустое поле details",
                )
            stored_value = 0.0
            stored_type = "self_monitoring_diary"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="record_type должен быть glucose, carbs, содержать insulin или быть self_monitoring_diary",
            )

        details = encrypt_data(point.details) if point.details else None
        records_to_insert.append(
            (current_patient["id"], point.timestamp, stored_type, stored_value, details)
        )

    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.executemany(
        "INSERT INTO timeseries_data (patient_id, timestamp, record_type, value, encrypted_details) VALUES (?, ?, ?, ?, ?)",
        records_to_insert,
    )
    con.commit()
    con.close()

    return {"message": f"Добавлено {len(records_to_insert)} записей"}

@router.post("/{patient_id}/records", status_code=status.HTTP_201_CREATED)
def add_medical_record(patient_id: int, record: MedicalRecordCreate, current_doctor: dict = Depends(get_current_doctor)):
    encrypted_data = encrypt_data(record.record_data)
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    ensure_doctor_access_to_patient(cur, current_doctor["id"], patient_id)

    cur.execute(
        "INSERT INTO medical_records (patient_id, record_date, encrypted_record_data) VALUES (?, ?, ?)",
        (patient_id, record.record_date, encrypted_data),
    )
    con.commit()
    con.close()
    return {"message": "Р—Р°РїРёСЃСЊ СѓСЃРїРµС€РЅРѕ РґРѕР±Р°РІР»РµРЅР°"}


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(patient_id: int, current_doctor: dict = Depends(get_current_doctor)):
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("DELETE FROM patients WHERE id = ? AND doctor_id = ?", (patient_id, current_doctor["id"]))
    con.commit()
    if cur.rowcount == 0:
        con.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="РџР°С†РёРµРЅС‚ РЅРµ РЅР°Р№РґРµРЅ РёР»Рё Сѓ РІР°СЃ РЅРµС‚ РїСЂР°РІ РЅР° РµРіРѕ СѓРґР°Р»РµРЅРёРµ")
    con.close()
    return


@router.get("/{patient_id}", response_model=PatientDisplay)
def get_patient_details(patient_id: int, current_doctor: dict = Depends(get_current_doctor)):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("SELECT * FROM patients WHERE id = ? AND doctor_id = ?", (patient_id, current_doctor["id"]))
    patient_record = cur.fetchone()
    con.close()

    if not patient_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="РџР°С†РёРµРЅС‚ РЅРµ РЅР°Р№РґРµРЅ")

    return row_to_patient_display(patient_record)


@router.get("/{patient_id}/glucose_data")
def get_patient_glucose_data(
    patient_id: int,
    current_doctor: dict = Depends(get_current_doctor),
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None,
):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    ensure_doctor_access_to_patient(cur, current_doctor["id"], patient_id)
    result = fetch_patient_glucose_data(cur, patient_id, start_datetime, end_datetime)
    con.close()
    return result


@router.get("/{patient_id}/comprehensive_data")
def get_patient_comprehensive_data(
    patient_id: int,
    current_doctor: dict = Depends(get_current_doctor),
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None,
):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    ensure_doctor_access_to_patient(cur, current_doctor["id"], patient_id)
    result = fetch_patient_comprehensive_data(cur, patient_id, start_datetime, end_datetime)
    con.close()
    return result


@router.get("/{patient_id}/recommendations")
def get_patient_recommendations(patient_id: int, current_doctor: dict = Depends(get_current_doctor)):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    ensure_doctor_access_to_patient(cur, current_doctor["id"], patient_id)
    result = fetch_patient_recommendations(cur, patient_id)
    con.close()
    return result


@router.get("/{patient_id}/parameters")
def get_patient_parameters(patient_id: int, current_doctor: dict = Depends(get_current_doctor)):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    ensure_doctor_access_to_patient(cur, current_doctor["id"], patient_id)

    try:
        result = fetch_patient_parameters(cur, patient_id)
    except Exception as e:
        con.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"РћС€РёР±РєР° РґРµС€РёС„СЂРѕРІРєРё РїР°СЂР°РјРµС‚СЂРѕРІ: {str(e)}",
        )

    con.close()
    return result


@router.get("/{patient_id}/scenarios", response_model=List[SimulatorScenario])
def get_simulator_scenarios(patient_id: int, current_doctor: dict = Depends(get_current_doctor)):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    ensure_doctor_access_to_patient(cur, current_doctor["id"], patient_id)
    result = fetch_patient_scenarios(cur, patient_id)
    con.close()
    return result


@router.get("/{patient_id}/diary", response_model=List[DiaryEntryDisplay])
def get_patient_diary_entries(
    patient_id: int,
    current_doctor: dict = Depends(get_current_doctor),
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None,
):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    ensure_doctor_access_to_patient(cur, current_doctor["id"], patient_id)
    result = fetch_patient_diary_entries(cur, patient_id, start_datetime, end_datetime)
    con.close()
    return result

