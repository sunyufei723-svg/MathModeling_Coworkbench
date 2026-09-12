from __future__ import annotations

import numpy as np


def _common_profile_difference(
    left: dict[str, object],
    right: dict[str, object],
) -> float:
    left_times = np.asarray(left["sample_time_s"], dtype=float)
    right_times = np.asarray(right["sample_time_s"], dtype=float)
    common = np.intersect1d(left_times, right_times)
    if common.size == 0:
        raise ValueError("integrator records have no common profile times")
    left_profile = np.asarray(
        [[np.nan if value is None else float(value) for value in row] for row in left["sample_moisture"]],
        dtype=float,
    )
    right_profile = np.asarray(
        [[np.nan if value is None else float(value) for value in row] for row in right["sample_moisture"]],
        dtype=float,
    )
    differences = []
    for time_s in common:
        left_index = int(np.where(np.isclose(left_times, time_s))[0][0])
        right_index = int(np.where(np.isclose(right_times, time_s))[0][0])
        finite = np.isfinite(left_profile[left_index]) & np.isfinite(right_profile[right_index])
        if np.any(finite):
            differences.append(
                float(
                    np.max(
                        np.abs(
                            left_profile[left_index, finite]
                            - right_profile[right_index, finite]
                        )
                    )
                )
            )
    if not differences:
        raise ValueError("integrator records have no common finite profile values")
    return max(differences)


def compare_integrators(
    scenario_names: list[str],
    bdf_records: list[dict[str, object]],
    radau_records: list[dict[str, object]],
) -> dict[str, object]:
    if not (len(scenario_names) == len(bdf_records) == len(radau_records)):
        raise ValueError("Radau comparison inputs differ in length")
    rows = []
    for name, bdf, radau in zip(scenario_names, bdf_records, radau_records, strict=True):
        difference = abs(
            float(bdf["continuous_event_time_s"]) - float(radau["continuous_event_time_s"])
        )
        rows.append(
            {
                "scenario": name,
                "bdf_event_time_h": float(bdf["continuous_event_time_h"]),
                "radau_event_time_h": float(radau["continuous_event_time_h"]),
                "absolute_difference_s": float(difference),
                "event_surface_moisture_difference": abs(
                    float(bdf["event_surface_moisture"])
                    - float(radau["event_surface_moisture"])
                ),
                "representative_profile_maximum_moisture_difference": _common_profile_difference(
                    bdf,
                    radau,
                ),
                "event_argmax_same": int(bdf["event_argmax_index"])
                == int(radau["event_argmax_index"]),
                "bdf_runtime_s": float(bdf["runtime_s"]),
                "radau_runtime_s": float(radau["runtime_s"]),
            }
        )
    return {
        "node_count": int(bdf_records[0]["node_count"]),
        "rows": rows,
        "acceptance": {
            "event_time_difference_limit_s": 30.0,
            "surface_moisture_difference_limit": 1.0e-4,
            "representative_profile_maximum_moisture_difference_limit": 1.0e-4,
        },
        "passed": bool(
            all(
                float(row["absolute_difference_s"]) < 30.0
                and float(row["event_surface_moisture_difference"]) < 1.0e-4
                and float(row["representative_profile_maximum_moisture_difference"]) < 1.0e-4
                and bool(row["event_argmax_same"])
                for row in rows
            )
        ),
    }
