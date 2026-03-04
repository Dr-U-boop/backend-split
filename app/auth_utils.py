from datetime import datetime, timedelta, timezone
import json
import os
import sqlite3

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.analysis_utils import analyze_patient_data
from app.encryption_utils import decrypt_data
from app.models import PatientDisplay, SimulatorScenario

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
DB_NAME = "medical_app.db"

if SECRET_KEY is None:
    raise ValueError("Необходимо установить переменную окружения SECRET_KEY в .env файле")


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"[auth] token decoded: sub={payload.get('sub')} role={payload.get('role')}")
        return payload
    except JWTError as exc:
        print(f"[auth] token decode failed: {exc}")
        raise _credentials_exception()


def get_current_doctor(token: str = Depends(oauth2_scheme)):
    print(f"[auth] raw token present={bool(token)} prefix={token[:20] if token else None}")
    payload = _decode_token(token)
    if payload.get("role") != "doctor":
        print(f"[auth] invalid role for doctor route: {payload.get('role')}")
        raise _credentials_exception()

    username = payload.get("sub")
    if username is None:
        print("[auth] missing sub in doctor token payload")
        raise _credentials_exception()

    print(f"[auth] doctor lookup DB_NAME={DB_NAME} cwd={os.getcwd()}")
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM doctors WHERE username = ?", (username,))
    user = cur.fetchone()
    con.close()

    print(f"[auth] doctor lookup: username={username} found={user is not None}")
    if user is None:
        raise _credentials_exception()

    return user


def get_current_patient(token: str = Depends(oauth2_scheme)):
    print(f"[auth] raw patient token present={bool(token)} prefix={token[:20] if token else None}")
    payload = _decode_token(token)
    if payload.get("role") != "patient":
        print(f"[auth] invalid role for patient route: {payload.get('role')}")
        raise _credentials_exception()

    patient_id = payload.get("patient_id")
    if patient_id is None:
        print("[auth] missing patient_id in patient token payload")
        raise _credentials_exception()

    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    patient = cur.fetchone()
    con.close()

    print(f"[auth] patient lookup: patient_id={patient_id} found={patient is not None}")
    if patient is None:
        raise _credentials_exception()

    return patient


def ensure_doctor_access_to_patient(cur: sqlite3.Cursor, doctor_id: int, patient_id: int) -> None:
    cur.execute("SELECT id FROM patients WHERE id = ? AND doctor_id = ?", (patient_id, doctor_id))
    if cur.fetchone() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пациент не найден")


def row_to_patient_display(patient_row: sqlite3.Row) -> PatientDisplay:
    return PatientDisplay(
        id=patient_row["id"],
        doctor_id=patient_row["doctor_id"],
        full_name=decrypt_data(patient_row["encrypted_full_name"]),
        contact_info=decrypt_data(patient_row["encrypted_contact_info"]) if patient_row["encrypted_contact_info"] else None,
        date_of_birth=patient_row["date_of_birth"],
        created_at=patient_row["created_at"],
    )


def fetch_patient_glucose_data(
    cur: sqlite3.Cursor,
    patient_id: int,
    start_datetime: datetime | None,
    end_datetime: datetime | None,
):
    if start_datetime and end_datetime:
        query = """
            SELECT timestamp, value FROM timeseries_data
            WHERE patient_id = ? AND record_type = 'glucose' AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
        """
        params = (patient_id, start_datetime, end_datetime)
    else:
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        query = """
            SELECT timestamp, value FROM timeseries_data
            WHERE patient_id = ? AND record_type = 'glucose' AND timestamp >= ?
            ORDER BY timestamp ASC
        """
        params = (patient_id, seven_days_ago)

    cur.execute(query, params)
    glucose_records = cur.fetchall()
    labels = [datetime.fromisoformat(rec["timestamp"]).strftime("%d.%m %H:%M") for rec in glucose_records]
    data = [rec["value"] for rec in glucose_records]
    return {"labels": labels, "data": data}


def fetch_patient_comprehensive_data(
    cur: sqlite3.Cursor,
    patient_id: int,
    start_datetime: datetime | None,
    end_datetime: datetime | None,
):
    if not (start_datetime and end_datetime):
        end_datetime = datetime.utcnow()
        start_datetime = end_datetime - timedelta(days=7)

    cur.execute(
        """
        SELECT timestamp, record_type, value FROM timeseries_data
        WHERE patient_id = ? AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
        """,
        (patient_id, start_datetime, end_datetime),
    )
    records = cur.fetchall()

    response_data = {"glucose": [], "insulin": [], "carbs": []}
    for rec in records:
        point = {"x": rec["timestamp"], "y": rec["value"]}
        if rec["record_type"] == "glucose":
            response_data["glucose"].append(point)
        elif "insulin" in rec["record_type"]:
            response_data["insulin"].append(point)
        elif rec["record_type"] == "carbs":
            response_data["carbs"].append(point)

    return response_data


def fetch_patient_recommendations(cur: sqlite3.Cursor, patient_id: int):
    month_ago = datetime.utcnow() - timedelta(days=30)
    cur.execute(
        "SELECT timestamp, record_type, value FROM timeseries_data WHERE patient_id = ? AND timestamp >= ?",
        (patient_id, month_ago),
    )
    records = [
        {
            "timestamp": datetime.fromisoformat(rec["timestamp"]),
            "record_type": rec["record_type"],
            "value": rec["value"],
        }
        for rec in cur.fetchall()
    ]
    return {"recommendations": analyze_patient_data(records)}


def fetch_patient_parameters(cur: sqlite3.Cursor, patient_id: int):
    cur.execute("SELECT encrypted_parameters FROM patients_parameters WHERE patient_id = ?", (patient_id,))
    record = cur.fetchone()
    if not record:
        return {}
    decrypted_json_str = decrypt_data(record["encrypted_parameters"])
    return json.loads(decrypted_json_str)


def fetch_patient_scenarios(cur: sqlite3.Cursor, patient_id: int):
    cur.execute("SELECT id, patient_id, encrypted_scenario FROM simulator_scenarios WHERE patient_id = ?", (patient_id,))
    records = cur.fetchall()

    scenarios = []
    for rec in records:
        try:
            decrypted_str = decrypt_data(rec["encrypted_scenario"])
            scenario_json = json.loads(decrypted_str)
            scenarios.append(
                SimulatorScenario(
                    scenario_id=rec["id"],
                    patient_id=rec["patient_id"],
                    scenario_data=scenario_json,
                )
            )
        except Exception:
            continue

    return scenarios


def fetch_patient_diary_entries(
    cur: sqlite3.Cursor,
    patient_id: int,
    start_datetime: datetime | None = None,
    end_datetime: datetime | None = None,
):
    if start_datetime and end_datetime:
        cur.execute(
            """
            SELECT timestamp, encrypted_details FROM timeseries_data
            WHERE patient_id = ? AND record_type = 'self_monitoring_diary' AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp DESC
            """,
            (patient_id, start_datetime, end_datetime),
        )
    else:
        cur.execute(
            """
            SELECT timestamp, encrypted_details FROM timeseries_data
            WHERE patient_id = ? AND record_type = 'self_monitoring_diary'
            ORDER BY timestamp DESC
            """,
            (patient_id,),
        )

    entries = []
    for rec in cur.fetchall():
        if not rec["encrypted_details"]:
            continue
        try:
            entries.append(
                {
                    "timestamp": rec["timestamp"],
                    "text": decrypt_data(rec["encrypted_details"]),
                }
            )
        except Exception:
            continue

    return entries
