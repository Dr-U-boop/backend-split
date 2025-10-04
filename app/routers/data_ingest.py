from fastapi import APIRouter, HTTPException, status
import sqlite3
from app.models import TimeSeriesDataIngest
from app.encryption_utils import encrypt_data

router = APIRouter()
DB_NAME = "medical_app.db"

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
def ingest_timeseries_data(payload: TimeSeriesDataIngest):
    """
    Принимает пачку временных данных (глюкоза, инсулин) от устройства/приложения.
    """
    records_to_insert = []
    for point in payload.data_points:
        details = encrypt_data(point.details) if point.details else None
        records_to_insert.append(
            (payload.patient_id, point.timestamp, point.record_type, point.value, details)
        )

    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.executemany(
        "INSERT INTO timeseries_data (patient_id, timestamp, record_type, value, encrypted_details) VALUES (?, ?, ?, ?, ?)",
        records_to_insert
    )
    con.commit()
    con.close()

    return {"message": f"len(records_to_insert) записей успешно принято."}