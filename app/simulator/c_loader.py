import ctypes
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parent
C_FILE = BASE_DIR / "c" / "sim_core.c"
LIB_NAME = "libsim_core"


def _lib_path() -> Path:
    if sys.platform == "darwin":
        return BASE_DIR / f"{LIB_NAME}.dylib"
    if os.name == "nt":
        return BASE_DIR / f"{LIB_NAME}.dll"
    return BASE_DIR / f"{LIB_NAME}.so"


def _compile_library() -> Path:
    lib_path = _lib_path()
    if os.name == "nt":
        raise RuntimeError("Windows build is not implemented for simulator C library")

    if sys.platform == "darwin":
        cmd = ["cc", "-O3", "-dynamiclib", str(C_FILE), "-o", str(lib_path), "-lm"]
    else:
        cmd = ["cc", "-O3", "-shared", "-fPIC", str(C_FILE), "-o", str(lib_path), "-lm"]

    subprocess.check_call(cmd)
    return lib_path


def _ensure_library() -> ctypes.CDLL:
    lib_path = _lib_path()
    if (not lib_path.exists()) or C_FILE.stat().st_mtime > lib_path.stat().st_mtime:
        _compile_library()

    lib = ctypes.CDLL(str(lib_path))
    lib.run_simulation_model.argtypes = [
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
    ]
    lib.run_simulation_model.restype = ctypes.c_int
    return lib


def run_simulation_model_c(
    model_type: int,
    patient_vec: np.ndarray,
    init_vec: np.ndarray,
    scenario_vec: np.ndarray,
    t0: float,
    dt: float,
    steps: int,
    tms: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    lib = _ensure_library()

    patient_vec = np.ascontiguousarray(patient_vec, dtype=np.float64)
    init_vec = np.ascontiguousarray(init_vec, dtype=np.float64)
    scenario_vec = np.ascontiguousarray(scenario_vec, dtype=np.float64)

    out_time = np.zeros(steps, dtype=np.float64)
    out_glucose = np.zeros(steps, dtype=np.float64)

    code = lib.run_simulation_model(
        int(model_type),
        patient_vec.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        int(patient_vec.size),
        init_vec.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        int(init_vec.size),
        scenario_vec.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        int(scenario_vec.size),
        float(t0),
        float(dt),
        int(steps),
        float(tms),
        out_time.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        out_glucose.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )

    if code != 0:
        raise RuntimeError(f"C simulator failed with code {code}")

    return out_time, out_glucose
