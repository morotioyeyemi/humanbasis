"""Build generative calibration from real EEGMMIDB data.

Fits per-class (left/right) mean and std of the band-power feature vector for the
calibrated motor encoding, using real recorded epochs, and writes them to
``brain/calibration/<encoding>.json``. The generative model then samples from
these fitted statistics so generated motor signal matches real signal within
tolerance, without any network access at run time.

Run once (data is cached by MNE after first download):

    python brain/build_calibration.py --subjects 1,2,3
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import snp
from brain.features import band_power_vector
from brain.loader import load_mi_epochs
from brain.generative import CALIBRATION_DIR

ENCODING = "mi.c3czc4.mubeta.v1"


def build(subjects: list[int], encoding: str = ENCODING) -> dict:
    rate = snp.get_layout(encoding).rate_hz
    per_class: dict[str, list[list[float]]] = {"left": [], "right": []}
    for s in subjects:
        epochs = load_mi_epochs(s, encoding=encoding)
        for i, label in enumerate(epochs.labels):
            vec = band_power_vector(epochs.data[i], encoding, rate)
            per_class[label].append(vec)

    classes = {}
    for label, rows in per_class.items():
        arr = np.asarray(rows)
        classes[label] = {
            "mean": arr.mean(axis=0).tolist(),
            "std": (arr.std(axis=0) + 1e-6).tolist(),
            "n": int(arr.shape[0]),
        }
    return {"encoding": encoding, "subjects": subjects, "classes": classes}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build generative calibration from real EEG.")
    parser.add_argument("--subjects", type=str, default="1,2,3")
    parser.add_argument("--encoding", type=str, default=ENCODING)
    args = parser.parse_args()
    subjects = [int(s) for s in args.subjects.split(",") if s.strip()]

    data = build(subjects, args.encoding)
    CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)
    out = CALIBRATION_DIR / f"{args.encoding}.json"
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {out} from subjects {subjects}: "
          f"{ {k: v['n'] for k, v in data['classes'].items()} } epochs/class")


if __name__ == "__main__":
    main()
