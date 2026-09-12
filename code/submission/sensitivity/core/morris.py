from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MorrisDesign:
    points: np.ndarray
    trajectories: list[dict[str, object]]
    levels: int
    delta: float


def generate_morris_design(
    dimension: int,
    trajectories_per_seed: int = 10,
    levels: int = 6,
    seeds: tuple[int, ...] = (20260912, 20260913),
) -> MorrisDesign:
    if dimension < 1 or trajectories_per_seed < 1:
        raise ValueError("dimension and trajectories_per_seed must be positive")
    if levels < 4 or levels % 2:
        raise ValueError("Morris levels must be an even integer >= 4")
    delta = levels / (2.0 * (levels - 1.0))
    grid = np.linspace(0.0, 1.0, levels)
    points: list[np.ndarray] = []
    metadata: list[dict[str, object]] = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        for local_index in range(trajectories_per_seed):
            directions = rng.choice(np.array([-1.0, 1.0]), size=dimension)
            base = np.empty(dimension, dtype=float)
            for index, direction in enumerate(directions):
                candidates = grid[grid <= 1.0 - delta + 1.0e-12]
                low = float(rng.choice(candidates))
                base[index] = low if direction > 0.0 else low + delta
            order = rng.permutation(dimension)
            trajectory_indices = [len(points)]
            points.append(base.copy())
            current = base.copy()
            steps = []
            for parameter_index in order:
                following = current.copy()
                signed_delta = directions[parameter_index] * delta
                following[parameter_index] += signed_delta
                if following[parameter_index] < -1.0e-12 or following[parameter_index] > 1.0 + 1.0e-12:
                    raise RuntimeError("generated Morris point outside [0, 1]")
                points.append(following)
                next_index = len(points) - 1
                steps.append(
                    {
                        "parameter_index": int(parameter_index),
                        "from_point_index": int(trajectory_indices[-1]),
                        "to_point_index": int(next_index),
                        "signed_delta": float(signed_delta),
                    }
                )
                trajectory_indices.append(next_index)
                current = following
            metadata.append(
                {
                    "seed": int(seed),
                    "trajectory_within_seed": int(local_index),
                    "point_indices": trajectory_indices,
                    "steps": steps,
                }
            )
    return MorrisDesign(np.vstack(points), metadata, levels, float(delta))


def analyse_morris(
    design: MorrisDesign,
    outputs: np.ndarray,
    parameter_names: tuple[str, ...],
) -> dict[str, object]:
    outputs = np.asarray(outputs, dtype=float)
    if outputs.shape != (len(design.points),):
        raise ValueError("Morris output length does not match design")
    effects: dict[str, list[float]] = {name: [] for name in parameter_names}
    seed_effects: dict[int, dict[str, list[float]]] = {}
    for trajectory in design.trajectories:
        seed = int(trajectory["seed"])
        seed_effects.setdefault(seed, {name: [] for name in parameter_names})
        for step in trajectory["steps"]:
            parameter_index = int(step["parameter_index"])
            effect = (
                outputs[int(step["to_point_index"])] - outputs[int(step["from_point_index"])]
            ) / float(step["signed_delta"])
            name = parameter_names[parameter_index]
            effects[name].append(float(effect))
            seed_effects[seed][name].append(float(effect))

    rows = []
    for name in parameter_names:
        values = np.asarray(effects[name], dtype=float)
        rows.append(
            {
                "parameter": name,
                "mu_h": float(np.mean(values)),
                "mu_star_h": float(np.mean(np.abs(values))),
                "sigma_h": float(np.std(values, ddof=1)),
                "elementary_effect_count": int(values.size),
                "effects_h": values.tolist(),
                "seed_mu_star_h": {
                    str(seed): float(np.mean(np.abs(per_parameter[name])))
                    for seed, per_parameter in seed_effects.items()
                },
            }
        )
    rows.sort(key=lambda item: float(item["mu_star_h"]), reverse=True)
    maximum = float(rows[0]["mu_star_h"])
    selected = [str(row["parameter"]) for row in rows[: min(5, len(rows))]]
    return {
        "levels": design.levels,
        "delta": design.delta,
        "trajectory_count": len(design.trajectories),
        "model_evaluation_count": len(design.points),
        "rows": rows,
        "selected_parameters": selected,
        "selection_rule": (
            "retain the top 5 by mu_star; the 10% of maximum threshold is reported as a diagnostic, "
            "not used to discard shrinkage or mass-transfer effects before PCE"
        ),
        "ten_percent_of_maximum_mu_star_h": 0.1 * maximum,
        "interpretation": "screening elementary effects, not variance contributions",
    }
