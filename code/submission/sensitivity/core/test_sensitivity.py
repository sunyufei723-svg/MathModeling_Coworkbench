import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from morris import analyse_morris, generate_morris_design
from parameters import PARAMETER_SPECS, default_unit_point, point_from_unit, unit_from_point
from pce import fit_pce, latin_hypercube, validation_metrics
from radau_crosscheck import compare_integrators
from sobol import analytical_sobol, bootstrap_sobol


class GlobalSensitivityTests(unittest.TestCase):
    def test_default_parameter_mapping(self):
        point = point_from_unit(default_unit_point())
        self.assertEqual(point["ambient_temperature_delta_c"], 0.0)
        for name, value in point.items():
            if name != "ambient_temperature_delta_c":
                self.assertEqual(value, 1.0)
        np.testing.assert_allclose(unit_from_point(point), default_unit_point())

    def test_morris_design_changes_one_parameter_per_step(self):
        design = generate_morris_design(3, trajectories_per_seed=2, seeds=(7, 8))
        self.assertEqual(len(design.points), 4 * (3 + 1))
        for trajectory in design.trajectories:
            for step in trajectory["steps"]:
                left = design.points[step["from_point_index"]]
                right = design.points[step["to_point_index"]]
                changed = np.flatnonzero(np.abs(left - right) > 1.0e-12)
                self.assertEqual(changed.tolist(), [step["parameter_index"]])

    def test_morris_recovers_linear_ranking(self):
        design = generate_morris_design(3, trajectories_per_seed=4, seeds=(17, 18))
        outputs = design.points @ np.array([3.0, -2.0, 0.5])
        result = analyse_morris(design, outputs, ("a", "b", "c"))
        self.assertEqual([row["parameter"] for row in result["rows"]], ["a", "b", "c"])
        self.assertAlmostEqual(result["rows"][0]["mu_h"], 3.0)
        self.assertAlmostEqual(result["rows"][1]["mu_h"], -2.0)

    def test_pce_exact_polynomial_and_sobol(self):
        points = latin_hypercube(100, 2, seed=123)
        x = 2.0 * points[:, 0] - 1.0
        y = 2.0 * points[:, 1] - 1.0
        outputs = 5.0 + 2.0 * x + y + 0.5 * x * y
        model = fit_pce(points, outputs, ("x", "y"), degree=2)
        validation = latin_hypercube(50, 2, seed=456)
        xv = 2.0 * validation[:, 0] - 1.0
        yv = 2.0 * validation[:, 1] - 1.0
        exact = 5.0 + 2.0 * xv + yv + 0.5 * xv * yv
        metrics = validation_metrics(exact, model.predict(validation))
        self.assertLess(metrics["maximum_absolute_error_h"], 1.0e-11)
        sobol = analytical_sobol(model)
        self.assertAlmostEqual(sum(row["first_order"] for row in sobol["rows"]) + sobol["interactions"][0]["second_order"], 1.0, places=12)
        intervals = bootstrap_sobol(points, outputs, ("x", "y"), degree=2, repetitions=10, seed=9)
        self.assertEqual(set(intervals), {"x", "y"})

    def test_declared_parameter_count_and_ranges(self):
        self.assertEqual(len(PARAMETER_SPECS), 9)
        self.assertTrue(all(spec.lower < spec.upper for spec in PARAMETER_SPECS))

    def test_integrator_comparison_includes_profiles(self):
        common = {
            "node_count": 5,
            "continuous_event_time_h": 1.0,
            "continuous_event_time_s": 3600.0,
            "event_surface_moisture": 0.1,
            "event_argmax_index": 0,
            "runtime_s": 1.0,
            "sample_time_s": [60.0, 120.0],
            "sample_moisture": [[0.2, 0.1, None], [0.15, 0.1, None]],
        }
        perturbed = dict(common)
        perturbed["continuous_event_time_s"] = 3600.01
        perturbed["sample_moisture"] = [[0.200001, 0.1, None], [0.15, 0.1, None]]
        result = compare_integrators(["test"], [common], [perturbed])
        self.assertTrue(result["passed"])
        self.assertAlmostEqual(
            result["rows"][0]["representative_profile_maximum_moisture_difference"],
            1.0e-6,
        )


if __name__ == "__main__":
    unittest.main()
