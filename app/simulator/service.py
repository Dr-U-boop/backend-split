import json
import sqlite3
from typing import Any

import numpy as np
from fastapi import HTTPException, status

from app.encryption_utils import decrypt_data, encrypt_data
from app.simulator.c_loader import run_simulation_model_c
from app.simulator.defaults import DEFAULT_PARAMETERS, DEFAULT_SCENARIO


MODEL_TO_CODE = {
    "sibr": 1,
    "dm": 2,
}


def _decode_json_field(value: str, field_name: str) -> dict[str, Any]:
    try:
        return json.loads(decrypt_data(value))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось декодировать {field_name}: {exc}",
        ) from exc


def get_patient_parameters(cur: sqlite3.Cursor, patient_id: int) -> dict[str, Any]:
    cur.execute("SELECT encrypted_parameters FROM patients_parameters WHERE patient_id = ?", (patient_id,))
    row = cur.fetchone()
    if not row:
        return dict(DEFAULT_PARAMETERS)
    return _decode_json_field(row["encrypted_parameters"], "parameters")


def get_patient_scenarios(cur: sqlite3.Cursor, patient_id: int) -> list[dict[str, Any]]:
    cur.execute(
        "SELECT id, encrypted_scenario FROM simulator_scenarios WHERE patient_id = ? ORDER BY id ASC",
        (patient_id,),
    )
    rows = cur.fetchall()
    if not rows:
        return [{"scenario_id": None, "scenario_data": dict(DEFAULT_SCENARIO)}]

    result: list[dict[str, Any]] = []
    for row in rows:
        result.append(
            {
                "scenario_id": row["id"],
                "scenario_data": _decode_json_field(row["encrypted_scenario"], "scenario"),
            }
        )
    return result


def save_patient_parameters(cur: sqlite3.Cursor, patient_id: int, payload: dict[str, Any]) -> None:
    enc = encrypt_data(json.dumps(payload))
    cur.execute("SELECT id FROM patients_parameters WHERE patient_id = ?", (patient_id,))
    row = cur.fetchone()
    if row:
        cur.execute(
            "UPDATE patients_parameters SET encrypted_parameters = ? WHERE patient_id = ?",
            (enc, patient_id),
        )
    else:
        cur.execute(
            "INSERT INTO patients_parameters (patient_id, encrypted_parameters) VALUES (?, ?)",
            (patient_id, enc),
        )


def save_patient_scenario(
    cur: sqlite3.Cursor,
    patient_id: int,
    scenario_data: dict[str, Any],
    scenario_id: int | None = None,
) -> int:
    enc = encrypt_data(json.dumps(scenario_data))
    if scenario_id is None:
        cur.execute(
            "INSERT INTO simulator_scenarios (patient_id, encrypted_scenario) VALUES (?, ?)",
            (patient_id, enc),
        )
        return int(cur.lastrowid)

    cur.execute(
        "UPDATE simulator_scenarios SET encrypted_scenario = ? WHERE id = ? AND patient_id = ?",
        (enc, scenario_id, patient_id),
    )
    if cur.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сценарий не найден")
    return scenario_id


def _to_float(d: dict[str, Any], key: str, fallback: float) -> float:
    raw = d.get(key, fallback)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return float(fallback)


def _normalize_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    s = {**DEFAULT_SCENARIO, **scenario}

    # Recompute dependent insulin fields to match original simulator creators.
    OB = _to_float(s, "OB", 1 / 19)
    if OB == 0:
        OB = 1 / 19
    M = _to_float(s, "M", DEFAULT_SCENARIO["M"])
    kbol = _to_float(s, "kbol", DEFAULT_SCENARIO["kbol"])
    kw = _to_float(s, "kw", DEFAULT_SCENARIO["kw"])
    Di = kbol * M * OB

    s["OB"] = OB
    s["Di"] = Di
    s["Dbol_1"] = _to_float(s, "Dbol_1", kw * Di)
    s["Dbol_2"] = _to_float(s, "Dbol_2", (1 - kw) * Di)

    return s


def _build_patient_vec(parameters: dict[str, Any]) -> np.ndarray:
    p = {**DEFAULT_PARAMETERS, **parameters}
    keys = [
        "mt", "Vi", "ki1", "ki2", "ki3", "kgabs", "kgri", "kmin", "kmax", "k1gg", "k2gg", "ucns",
        "vidb", "kres", "k1e", "k2e", "k1abs", "k2abs", "ks", "kd", "ksen", "lbh", "gth", "kh1",
        "kh2", "kh3", "kh4", "k1gl", "k2gl", "kh5", "kh6", "k1gng", "k2gng", "kKc", "ib", "gb",
        "kret", "kdec", "delth_g", "vid", "Kidb", "vgg", "vgl", "Kgl", "Kgn", "Ki", "vgng", "Kgng",
        "k1i", "k2i", "k3i", "di", "dh",
    ]
    return np.array([_to_float(p, k, DEFAULT_PARAMETERS[k]) for k in keys], dtype=np.float64)


def _build_init_vec(parameters: dict[str, Any], model_type: str) -> np.ndarray:
    p = {**DEFAULT_PARAMETERS, **parameters}
    if model_type == "sibr":
        keys = [
            "g0", "Il0", "Ip0", "fgut0", "fliq0", "fsol0", "gt0", "Xt0", "Ii0", "It0", "Hp0", "SRsh0",
            "gl0", "Phn10", "Pha10", "Phn20", "Pha20", "yg0", "PCa0", "PCn0", "pyr0", "Er0", "Er10",
        ]
        return np.array([_to_float(p, k, DEFAULT_PARAMETERS[k]) for k in keys], dtype=np.float64)

    # DM model initialization as in simulator2.py
    return np.array(
        [
            _to_float(p, "g0", DEFAULT_PARAMETERS["g0"]),
            _to_float(p, "Il0", DEFAULT_PARAMETERS["Il0"]),
            _to_float(p, "Ip0", DEFAULT_PARAMETERS["Ip0"]),
            _to_float(p, "fgut0", DEFAULT_PARAMETERS["fgut0"]),
            _to_float(p, "fliq0", DEFAULT_PARAMETERS["fliq0"]),
            _to_float(p, "fsol0", DEFAULT_PARAMETERS["fsol0"]),
            _to_float(p, "gt0", DEFAULT_PARAMETERS["gt0"]),
            104.08,
            104.08,
            _to_float(p, "Xt0", DEFAULT_PARAMETERS["Xt0"]),
            3.08,
            0.0,
            _to_float(p, "Ii0", DEFAULT_PARAMETERS["Ii0"]),
            _to_float(p, "It0", DEFAULT_PARAMETERS["It0"]),
        ],
        dtype=np.float64,
    )


def _build_scenario_vec(s: dict[str, Any]) -> np.ndarray:
    keys = [
        "M", "tm", "Tm", "kbol", "kw", "t0", "t1", "ti_1", "ti_2", "Ti_1", "Ti_2", "OB", "Di", "Dbol_1", "Dbol_2", "Vbas"
    ]
    return np.array([_to_float(s, k, DEFAULT_SCENARIO.get(k, 0.0)) for k in keys], dtype=np.float64)


def _johnson_su_noise(glucose_mgdl: np.ndarray, seed: int) -> np.ndarray:
    # Matches generator shape from simulator2.py
    params = [-5.47, 15.9574, -0.5444, 1.6898]
    x_rand = np.random.RandomState(int(seed))
    x0 = 0.0
    err = []
    for i in range(len(glucose_mgdl)):
        if i == 0:
            x0 = x_rand.randn()
        else:
            x0 = 0.7 * (x0 + x_rand.randn())

        eps = params[0] + params[1] * np.sinh((x0 - params[2]) / params[3])
        err.append(glucose_mgdl[i] / 1.8 + eps)
    return np.array(err, dtype=np.float64)


def _compute_metrics(g: np.ndarray, tm: int, Tm: int, g_delay: np.ndarray) -> dict[str, Any]:
    tm = max(0, min(tm, len(g)))
    after_start = min(len(g), tm + max(Tm, 0))

    metrics = {
        "average": float(np.average(g)),
        "average_before_meals": float(np.average(g[:tm])) if tm > 0 else float(np.average(g)),
        "average_after_meals": float(np.average(g[after_start:])) if after_start < len(g) else float(np.average(g)),
        "min": float(np.min(g)),
        "max": float(np.max(g)),
        "min_with_30min_meal_delay": float(np.min(g_delay)),
        "fraction_below_target": float(np.mean(g < 3.9)),
        "fraction_above_target": float(np.mean(g > 10.0)),
        "fraction_within_target": float(np.mean((g >= 3.9) & (g <= 10.0))),
        "fraction_below_critical": float(np.mean(g < 3.9)),
        "fraction_above_critical": float(np.mean(g > (230.0 / 18.0))),
        "integral_above_180": float(np.sum((g - 10.0) * (g > 10.0))),
    }
    return metrics


def run_simulation(
    parameters: dict[str, Any],
    scenario: dict[str, Any],
    model_type: str = "sibr",
    cgm_noise_seed: int | None = None,
) -> dict[str, Any]:
    model_type = (model_type or "sibr").lower()
    if model_type not in MODEL_TO_CODE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model_type должен быть 'sibr' или 'dm'")

    p = {**DEFAULT_PARAMETERS, **parameters}
    s = _normalize_scenario(scenario)

    patient_vec = _build_patient_vec(p)
    init_vec = _build_init_vec(p, model_type)
    scenario_vec = _build_scenario_vec(s)

    t0 = int(round(_to_float(s, "t0", DEFAULT_SCENARIO["t0"])))
    t1 = int(round(_to_float(s, "t1", DEFAULT_SCENARIO["t1"])))
    if t1 <= t0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="scenario.t1 должен быть больше t0")

    dt = 1.0
    steps = (t1 - t0) + 1

    time_arr, glucose_raw = run_simulation_model_c(
        model_type=MODEL_TO_CODE[model_type],
        patient_vec=patient_vec,
        init_vec=init_vec,
        scenario_vec=scenario_vec,
        t0=float(t0),
        dt=dt,
        steps=steps,
        tms=0.0,
    )

    _, glucose_raw_delay = run_simulation_model_c(
        model_type=MODEL_TO_CODE[model_type],
        patient_vec=patient_vec,
        init_vec=init_vec,
        scenario_vec=scenario_vec,
        t0=float(t0),
        dt=dt,
        steps=steps,
        tms=30.0,
    )

    tm = int(round(_to_float(s, "tm", DEFAULT_SCENARIO["tm"])))
    Tm = int(round(_to_float(s, "Tm", DEFAULT_SCENARIO["Tm"])))

    noise_profile = None
    if cgm_noise_seed is not None:
        noise_profile = _johnson_su_noise(glucose_raw, cgm_noise_seed)

    glucose_mmol = glucose_raw / 18.0
    glucose_mmol_delay = glucose_raw_delay / 18.0

    return {
        "model_type": model_type,
        "time": time_arr.tolist(),
        "glucose": glucose_raw.tolist(),
        "glucose_delay_30m": glucose_raw_delay.tolist(),
        "glucose_mmol": glucose_mmol.tolist(),
        "metrics": _compute_metrics(glucose_mmol, tm=tm, Tm=Tm, g_delay=glucose_mmol_delay),
        "cgm_noisy_trace": noise_profile.tolist() if noise_profile is not None else None,
    }
