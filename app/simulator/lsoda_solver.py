from __future__ import annotations

import numpy as np

from app.simulator.c_loader import run_simulation_model_c


def run_simulation_model_lsoda(
    model_type: int,
    patient_vec: np.ndarray,
    init_vec: np.ndarray,
    scenario_vec: np.ndarray,
    t0: float,
    dt: float,
    steps: int,
    tms: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compatibility wrapper with the LSODA entrypoint name.
    Backend execution is delegated to the native C simulator for speed.
    """
    return run_simulation_model_c(
        model_type=model_type,
        patient_vec=patient_vec,
        init_vec=init_vec,
        scenario_vec=scenario_vec,
        t0=t0,
        dt=dt,
        steps=steps,
        tms=tms,
    )

