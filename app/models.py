from pydantic import BaseModel
from datetime import date, datetime
from typing import List, Optional

class PatientBase(BaseModel):
    full_name: str
    date_of_birth: date
    contact_info: Optional[str] = None

class PatientCreate(PatientBase):
    pass

class PatientDisplay(PatientBase):
    id: int
    doctor_id: int
    created_at: datetime

class MedicalRecordCreate(BaseModel):
    record_date: datetime
    record_data: str # Любой текст для записи в JSON

class MedicalRecordDisplay(MedicalRecordCreate):
    id: int
    patient_id: int

class UserCredentials(BaseModel):
    username: str
    password: str