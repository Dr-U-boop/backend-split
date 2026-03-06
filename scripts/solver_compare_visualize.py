#!/usr/bin/env python3
from __future__ import annotations

import ctypes
import json
import math
import subprocess
import time
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT_PROD = Path('/Users/nillkiggers/Documents/Glukoze-Prod/backend-split')
ROOT_TEST = Path('/Users/nillkiggers/Documents/Glukoze-Test')

OLD_SRC = ROOT_PROD / 'app/simulator/c/sim_core.c'
NEW_SRC = ROOT_PROD / 'app/simulator/c/sim_core.cpp'
OLD_LIB = Path('/tmp/libsim_core_old_compare.dylib')
NEW_LIB = Path('/tmp/libsim_core_new_compare.dylib')


def compile_libs() -> None:
    subprocess.check_call(['cc', '-O3', '-dynamiclib', str(OLD_SRC), '-o', str(OLD_LIB), '-lm'])
    subprocess.check_call(['c++', '-O3', '-std=c++17', '-dynamiclib', str(NEW_SRC), '-o', str(NEW_LIB), '-lm'])


def load_lib(path: Path):
    lib = ctypes.CDLL(str(path))
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


def import_sim_helpers():
    import sys

    sys.path.insert(0, str(ROOT_PROD))
    from app.simulator.defaults import DEFAULT_PARAMETERS, DEFAULT_SCENARIO
    from app.simulator.service import (
        _build_init_vec,
        _build_patient_vec,
        _build_scenario_vec,
        _normalize_scenario,
        _to_float,
    )

    return DEFAULT_PARAMETERS, DEFAULT_SCENARIO, _build_patient_vec, _build_init_vec, _build_scenario_vec, _normalize_scenario, _to_float


def run_once(lib, model_type: str, tms: float, patient_vec: np.ndarray, init_vec: np.ndarray, scenario_vec: np.ndarray, t0: int, steps: int):
    out_time = np.zeros(steps, dtype=np.float64)
    out_gl = np.zeros(steps, dtype=np.float64)
    code = lib.run_simulation_model(
        1 if model_type == 'sibr' else 2,
        patient_vec.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        int(patient_vec.size),
        init_vec.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        int(init_vec.size),
        scenario_vec.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        int(scenario_vec.size),
        float(t0),
        1.0,
        int(steps),
        float(tms),
        out_time.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        out_gl.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )
    if code != 0:
        raise RuntimeError(f'run_simulation_model failed with code {code}')
    return out_time, out_gl


def benchmark_ms(lib, model_type: str, reps: int, patient_vec: np.ndarray, init_vec: np.ndarray, scenario_vec: np.ndarray, t0: int, steps: int) -> float:
    start = time.perf_counter()
    for _ in range(reps):
        run_once(lib, model_type, 0.0, patient_vec, init_vec, scenario_vec, t0, steps)
    return (time.perf_counter() - start) * 1000.0 / reps


def polyline(points, color, width=1.5):
    pts = ' '.join(f'{x:.2f},{y:.2f}' for x, y in points)
    return f'<polyline fill="none" stroke="{color}" stroke-width="{width}" points="{pts}" />'


def draw_panel(svg_parts, x, y, w, h, title, xvals, series, colors, labels, y_label):
    if len(xvals) == 0:
        return
    margin_l = 56
    margin_r = 18
    margin_t = 28
    margin_b = 32
    px0 = x + margin_l
    py0 = y + margin_t
    pw = w - margin_l - margin_r
    ph = h - margin_t - margin_b

    y_min = min(float(np.min(s)) for s in series)
    y_max = max(float(np.max(s)) for s in series)
    if math.isclose(y_min, y_max):
        y_max = y_min + 1.0
    pad = (y_max - y_min) * 0.08
    y_min -= pad
    y_max += pad

    x_min = float(xvals[0])
    x_max = float(xvals[-1])

    def sx(v):
        return px0 + (float(v) - x_min) * pw / (x_max - x_min if x_max != x_min else 1.0)

    def sy(v):
        return py0 + ph - (float(v) - y_min) * ph / (y_max - y_min)

    svg_parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="white" stroke="#d0d7de"/>')
    svg_parts.append(f'<text x="{x + 8}" y="{y + 18}" font-size="14" font-family="Arial">{title}</text>')

    # axes
    svg_parts.append(f'<line x1="{px0}" y1="{py0 + ph}" x2="{px0 + pw}" y2="{py0 + ph}" stroke="#555"/>')
    svg_parts.append(f'<line x1="{px0}" y1="{py0}" x2="{px0}" y2="{py0 + ph}" stroke="#555"/>')

    # y ticks
    for i in range(5):
        yy = py0 + ph * i / 4.0
        val = y_max - (y_max - y_min) * i / 4.0
        svg_parts.append(f'<line x1="{px0}" y1="{yy:.2f}" x2="{px0 + pw}" y2="{yy:.2f}" stroke="#f0f0f0"/>')
        svg_parts.append(f'<text x="{px0 - 52}" y="{yy + 4:.2f}" font-size="10" font-family="Arial">{val:.2f}</text>')

    # x ticks
    for i in range(6):
        xx = px0 + pw * i / 5.0
        val = x_min + (x_max - x_min) * i / 5.0
        svg_parts.append(f'<line x1="{xx:.2f}" y1="{py0}" x2="{xx:.2f}" y2="{py0 + ph}" stroke="#f5f5f5"/>')
        svg_parts.append(f'<text x="{xx - 10:.2f}" y="{py0 + ph + 16}" font-size="10" font-family="Arial">{val:.0f}</text>')

    # lines
    for s, c in zip(series, colors):
        pts = [(sx(xx), sy(yy)) for xx, yy in zip(xvals, s)]
        svg_parts.append(polyline(pts, c, 1.6))

    # labels
    svg_parts.append(f'<text x="{x + w - 80}" y="{y + h - 10}" font-size="10" font-family="Arial">time, min</text>')
    svg_parts.append(f'<text x="{x + 8}" y="{y + h - 10}" font-size="10" font-family="Arial">{y_label}</text>')

    ly = y + 20
    lx = x + w - 180
    for lbl, c in zip(labels, colors):
        svg_parts.append(f'<line x1="{lx}" y1="{ly - 4}" x2="{lx + 18}" y2="{ly - 4}" stroke="{c}" stroke-width="2"/>')
        svg_parts.append(f'<text x="{lx + 24}" y="{ly}" font-size="11" font-family="Arial">{lbl}</text>')
        ly += 14


def write_model_svg(path: Path, model: str, time_arr: np.ndarray, old_0: np.ndarray, new_0: np.ndarray, old_30: np.ndarray, new_30: np.ndarray):
    old_0_m = old_0 / 18.0
    new_0_m = new_0 / 18.0
    old_30_m = old_30 / 18.0
    new_30_m = new_30 / 18.0
    d0 = new_0_m - old_0_m
    d30 = new_30_m - old_30_m

    W, H = 1280, 980
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">',
        '<rect width="100%" height="100%" fill="#fbfdff"/>',
        f'<text x="20" y="28" font-size="20" font-family="Arial">Solver comparison: old RK4(C) vs new LSODA(C++) - {model.upper()}</text>',
    ]

    draw_panel(parts, 20, 50, 1240, 280, 'Trajectory (tms=0)', time_arr, [old_0_m, new_0_m], ['#1f77b4', '#d62728'], ['old RK4', 'new LSODA'], 'glucose mmol/L')
    draw_panel(parts, 20, 350, 1240, 280, 'Trajectory (tms=30)', time_arr, [old_30_m, new_30_m], ['#1f77b4', '#d62728'], ['old RK4', 'new LSODA'], 'glucose mmol/L')
    draw_panel(parts, 20, 650, 1240, 280, 'Difference (new-old) in mmol/L', time_arr, [d0, d30], ['#2ca02c', '#9467bd'], ['delta tms=0', 'delta tms=30'], 'delta mmol/L')

    parts.append('</svg>')
    path.write_text('\n'.join(parts), encoding='utf-8')


def write_speed_svg(path: Path, old_sibr, new_sibr, old_dm, new_dm):
    W, H = 900, 420
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">',
        '<rect width="100%" height="100%" fill="#fbfdff"/>',
        '<text x="20" y="30" font-size="20" font-family="Arial">Performance comparison (lower is better)</text>',
    ]
    vals = [('SIBR old', old_sibr, '#1f77b4'), ('SIBR new', new_sibr, '#d62728'), ('DM old', old_dm, '#1f77b4'), ('DM new', new_dm, '#d62728')]
    vmax = max(v for _, v, _ in vals) * 1.15
    x0, y0, w, h = 70, 70, 780, 300
    parts.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="white" stroke="#d0d7de"/>')
    for i in range(6):
        yy = y0 + h * i / 5.0
        val = vmax - vmax * i / 5.0
        parts.append(f'<line x1="{x0}" y1="{yy:.2f}" x2="{x0 + w}" y2="{yy:.2f}" stroke="#f0f0f0"/>')
        parts.append(f'<text x="20" y="{yy + 4:.2f}" font-size="10" font-family="Arial">{val:.2f} ms</text>')

    bar_w = 120
    gap = 60
    for i, (name, val, color) in enumerate(vals):
        bx = x0 + 40 + i * (bar_w + gap)
        bh = h * (val / vmax)
        by = y0 + h - bh
        parts.append(f'<rect x="{bx}" y="{by:.2f}" width="{bar_w}" height="{bh:.2f}" fill="{color}"/>')
        parts.append(f'<text x="{bx + 5}" y="{y0 + h + 16}" font-size="11" font-family="Arial">{name}</text>')
        parts.append(f'<text x="{bx + 10}" y="{by - 6:.2f}" font-size="11" font-family="Arial">{val:.2f} ms</text>')

    parts.append('</svg>')
    path.write_text('\n'.join(parts), encoding='utf-8')


def main() -> None:
    compile_libs()
    old = load_lib(OLD_LIB)
    new = load_lib(NEW_LIB)

    (
        DEFAULT_PARAMETERS,
        DEFAULT_SCENARIO,
        _build_patient_vec,
        _build_init_vec,
        _build_scenario_vec,
        _normalize_scenario,
        _to_float,
    ) = import_sim_helpers()

    s = _normalize_scenario(dict(DEFAULT_SCENARIO))
    t0 = int(round(_to_float(s, 't0', DEFAULT_SCENARIO['t0'])))
    t1 = int(round(_to_float(s, 't1', DEFAULT_SCENARIO['t1'])))
    steps = (t1 - t0) + 1

    patient_vec = np.ascontiguousarray(_build_patient_vec(dict(DEFAULT_PARAMETERS)), dtype=np.float64)
    scenario_vec = np.ascontiguousarray(_build_scenario_vec(s), dtype=np.float64)

    results = {}
    speeds = {}

    for model in ('sibr', 'dm'):
        init_vec = np.ascontiguousarray(_build_init_vec(dict(DEFAULT_PARAMETERS), model), dtype=np.float64)
        t_old0, g_old0 = run_once(old, model, 0.0, patient_vec, init_vec, scenario_vec, t0, steps)
        _, g_new0 = run_once(new, model, 0.0, patient_vec, init_vec, scenario_vec, t0, steps)
        _, g_old30 = run_once(old, model, 30.0, patient_vec, init_vec, scenario_vec, t0, steps)
        _, g_new30 = run_once(new, model, 30.0, patient_vec, init_vec, scenario_vec, t0, steps)

        d0 = g_new0 - g_old0
        d30 = g_new30 - g_old30

        results[model] = {
            'tms0': {
                'rmse_mgdl': float(np.sqrt(np.mean(d0 * d0))),
                'mae_mgdl': float(np.mean(np.abs(d0))),
                'max_abs_mgdl': float(np.max(np.abs(d0))),
            },
            'tms30': {
                'rmse_mgdl': float(np.sqrt(np.mean(d30 * d30))),
                'mae_mgdl': float(np.mean(np.abs(d30))),
                'max_abs_mgdl': float(np.max(np.abs(d30))),
            },
        }

        old_ms = benchmark_ms(old, model, 25, patient_vec, init_vec, scenario_vec, t0, steps)
        new_ms = benchmark_ms(new, model, 25, patient_vec, init_vec, scenario_vec, t0, steps)
        speeds[model] = {
            'old_avg_ms': float(old_ms),
            'new_avg_ms': float(new_ms),
            'new_vs_old_ratio': float(new_ms / old_ms if old_ms > 0 else math.nan),
        }

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_svg = ROOT_PROD / 'reports' / f'solver_compare_{ts}_{model}.svg'
        write_model_svg(out_svg, model, t_old0, g_old0, g_new0, g_old30, g_new30)
        results[model]['plot'] = str(out_svg)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    speed_svg = ROOT_PROD / 'reports' / f'solver_compare_{ts}_speed.svg'
    write_speed_svg(speed_svg, speeds['sibr']['old_avg_ms'], speeds['sibr']['new_avg_ms'], speeds['dm']['old_avg_ms'], speeds['dm']['new_avg_ms'])

    summary = {
        'generated_at': datetime.now().isoformat(),
        'results': results,
        'speed': speeds,
        'speed_plot': str(speed_svg),
        'old_lib': str(OLD_LIB),
        'new_lib': str(NEW_LIB),
    }
    out_json = ROOT_PROD / 'reports' / f'solver_compare_{ts}_summary.json'
    out_json.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(str(out_json))
    print(str(speed_svg))
    for model in ('sibr', 'dm'):
        print(results[model]['plot'])


if __name__ == '__main__':
    main()
