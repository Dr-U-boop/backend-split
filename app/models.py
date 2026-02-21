from pydantic import BaseModel
from datetime import date, datetime
from typing import Any, List, Optional

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

class PatientFullData(PatientDisplay):
        records: List[MedicalRecordDisplay] = []

class TimeSeriesDataPoint(BaseModel):
     timestamp: datetime
     record_type: str
     value: float
     details: Optional[str] = None

class TimeSeriesDataIngest(BaseModel):
     patient_id: int
     data_points: List[TimeSeriesDataPoint]

class PatientTimeSeriesDataPoint(BaseModel):
     timestamp: datetime
     record_type: str
     value: Optional[float] = None
     details: Optional[str] = None

class PatientTimeSeriesDataIngest(BaseModel):
     data_points: List[PatientTimeSeriesDataPoint]

class DiaryEntryDisplay(BaseModel):
    timestamp: datetime
    text: str

class PatientParameters(BaseModel):
    patient_id: int
    encrypted_parameters: str

class SimulatorScenario(BaseModel):
    scenario_id: int
    patient_id: int
    scenario_data: dict


class SimulatorParametersUpdate(BaseModel):
    parameters: dict[str, Any]


class SimulatorScenarioUpdate(BaseModel):
    scenario_data: dict[str, Any]


class SimulatorRunRequest(BaseModel):
    parameters: Optional[dict[str, Any]] = None
    scenario_data: Optional[dict[str, Any]] = None
    scenario_id: Optional[int] = None
    model_type: Optional[str] = "sibr"
    cgm_noise_seed: Optional[int] = None
