import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.auth_utils import ensure_doctor_access_to_patient, get_current_doctor
from app.models import SimulatorParametersUpdate, SimulatorRunRequest, SimulatorScenarioUpdate
from app.simulator.service import (
    get_patient_parameters,
    get_patient_scenarios,
    run_simulation,
    save_patient_parameters,
    save_patient_scenario,
)

router = APIRouter()
DB_NAME = "medical_app.db"


@router.get("/patients/{patient_id}/config")
def get_simulator_config(patient_id: int, current_doctor: dict = Depends(get_current_doctor)):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    ensure_doctor_access_to_patient(cur, current_doctor["id"], patient_id)

    parameters = get_patient_parameters(cur, patient_id)
    scenarios = get_patient_scenarios(cur, patient_id)
    con.close()

    return {"patient_id": patient_id, "parameters": parameters, "scenarios": scenarios}


@router.put("/patients/{patient_id}/parameters")
def update_simulator_parameters(
    patient_id: int,
    payload: SimulatorParametersUpdate,
    current_doctor: dict = Depends(get_current_doctor),
):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    ensure_doctor_access_to_patient(cur, current_doctor["id"], patient_id)
    save_patient_parameters(cur, patient_id, payload.parameters)
    con.commit()
    con.close()

    return {"message": "Параметры симулятора сохранены"}


@router.post("/patients/{patient_id}/scenarios")
def create_simulator_scenario(
    patient_id: int,
    payload: SimulatorScenarioUpdate,
    current_doctor: dict = Depends(get_current_doctor),
):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    ensure_doctor_access_to_patient(cur, current_doctor["id"], patient_id)
    scenario_id = save_patient_scenario(cur, patient_id, payload.scenario_data, scenario_id=None)
    con.commit()
    con.close()

    return {"message": "Сценарий сохранен", "scenario_id": scenario_id}


@router.put("/patients/{patient_id}/scenarios/{scenario_id}")
def update_simulator_scenario(
    patient_id: int,
    scenario_id: int,
    payload: SimulatorScenarioUpdate,
    current_doctor: dict = Depends(get_current_doctor),
):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    ensure_doctor_access_to_patient(cur, current_doctor["id"], patient_id)
    save_patient_scenario(cur, patient_id, payload.scenario_data, scenario_id=scenario_id)
    con.commit()
    con.close()

    return {"message": "Сценарий обновлен", "scenario_id": scenario_id}


@router.post("/patients/{patient_id}/run")
def run_patient_simulation(
    patient_id: int,
    payload: SimulatorRunRequest,
    current_doctor: dict = Depends(get_current_doctor),
):
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    ensure_doctor_access_to_patient(cur, current_doctor["id"], patient_id)

    parameters = payload.parameters if payload.parameters is not None else get_patient_parameters(cur, patient_id)

    if payload.scenario_data is not None:
        scenario_data = payload.scenario_data
    else:
        scenarios = get_patient_scenarios(cur, patient_id)
        if not scenarios:
            con.close()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сценарии не найдены")

        if payload.scenario_id is None:
            scenario_data = scenarios[0]["scenario_data"]
        else:
            found = [s for s in scenarios if s["scenario_id"] == payload.scenario_id]
            if not found:
                con.close()
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сценарий не найден")
            scenario_data = found[0]["scenario_data"]

    con.close()
    result = run_simulation(
        parameters=parameters,
        scenario=scenario_data,
        model_type=payload.model_type or "sibr",
        cgm_noise_seed=payload.cgm_noise_seed,
    )
    return result
