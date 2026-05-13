"""Smoke-test the A2B and SMPL-Anthropometry adapters.

A2B can run end-to-end on our target measurements (pretrained weights ship
with the repo). SMPL-Anthropometry requires SMPL-X .pkl weights which are
behind academic registration — that adapter is exercised only as far as
the import + measurement-name mapping; the actual `from_verts` call is
deferred unless `SMPLX_MODEL_DIR` is set.

Writes outputs/adapter_smoke_test.json with whatever results came back.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.a2b_adapter import predict_betas
from src.measurements import load_measurements


MEASUREMENTS_PATH = REPO_ROOT / "target_measurements.json"
REPORT_PATH = REPO_ROOT / "outputs" / "adapter_smoke_test.json"


def smoke_a2b(measurements: dict) -> dict:
    print("=== A2B adapter ===")
    out = {}
    for model_type in ("nn", "svr"):
        try:
            betas = predict_betas(measurements, model_type=model_type)
            print(f"  {model_type}: shape={betas.shape}, "
                  f"mean={float(betas.mean()):+.4f}, "
                  f"std={float(betas.std()):.4f}, "
                  f"min={float(betas.min()):+.4f}, "
                  f"max={float(betas.max()):+.4f}")
            out[model_type] = {
                "ok": True,
                "shape": list(betas.shape),
                "betas": [float(b) for b in betas.tolist()],
                "magnitude_ok": bool(float(np.abs(betas).max()) < 8.0),
            }
        except Exception as e:
            print(f"  {model_type}: FAILED ({type(e).__name__}: {e})")
            out[model_type] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return out


def smoke_anthropometry() -> dict:
    print("=== SMPL-Anthropometry adapter ===")
    from src.anthropometry_adapter import (
        ANTHROPOMETRY_ROOT,
        UPSTREAM_NAME_MAP,
        _ensure_on_path,
    )

    out = {
        "repo_present": ANTHROPOMETRY_ROOT.exists(),
        "name_map_keys": list(UPSTREAM_NAME_MAP.keys()),
    }
    if not ANTHROPOMETRY_ROOT.exists():
        print("  repo not cloned; skipping")
        return out

    _ensure_on_path()
    try:
        import measure as upstream_measure  # noqa: F401
        out["import_ok"] = True
        print("  upstream `measure` module imports OK")
    except Exception as e:
        out["import_ok"] = False
        out["import_error"] = f"{type(e).__name__}: {e}"
        print(f"  upstream import failed: {e}")
        return out

    smplx_dir = os.environ.get("SMPLX_MODEL_DIR")
    if not smplx_dir:
        out["from_verts_ok"] = None
        out["from_verts_note"] = (
            "SMPLX_MODEL_DIR not set; cannot instantiate MeasureSMPLX "
            "without SMPL-X .pkl weights. Adapter API verified at import "
            "level only."
        )
        print("  SMPLX_MODEL_DIR not set; skipping full from_verts test")
        return out

    from src.anthropometry_adapter import measure_mesh

    try:
        verts = np.random.RandomState(0).randn(10475, 3).astype(np.float32) * 0.05
        result = measure_mesh(verts, gender="female")
        out["from_verts_ok"] = True
        out["sample_measurements_cm"] = {k: float(v) for k, v in result.items()}
        print(f"  measure_mesh ran on random verts, {len(result)} measurements returned")
    except Exception as e:
        out["from_verts_ok"] = False
        out["from_verts_error"] = f"{type(e).__name__}: {e}"
        print(f"  measure_mesh failed: {e}")
    return out


def main() -> None:
    measurements = load_measurements(MEASUREMENTS_PATH)

    report = {
        "input_summary": {
            "stature_cm": measurements["stature_cm"],
            "gender": measurements["gender"],
            "wh_ratio": round(measurements["waist_cm"] / measurements["hip_cm"], 3),
        },
        "a2b": smoke_a2b(measurements),
        "anthropometry": smoke_anthropometry(),
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w") as f:
        json.dump(report, f, indent=2)
    print(f"\nwrote {REPORT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
