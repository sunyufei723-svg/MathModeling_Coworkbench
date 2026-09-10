import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_problem1 import markdown_table
from solver import (
    EnvironmentSeries,
    SolverConfig,
    build_radial_grid_cm,
    moisture_diffusivity,
    solve_problem1,
)


class Problem1SolverTests(unittest.TestCase):
    def test_environment_series_linearly_interpolates_both_boundaries(self):
        environment = EnvironmentSeries(
            time_s=np.array([0.0, 60.0]),
            temperature_c=np.array([28.0, 30.0]),
            moisture=np.array([0.020, 0.026]),
        )
        self.assertEqual(environment.temperature_at(30.0), 29.0)
        self.assertEqual(environment.moisture_at(30.0), 0.023)

    def test_diffusivity_uses_inverse_moisture_formula(self):
        concentration = np.array([2.55, 1.0])
        expected = 7e-9 * np.exp(-0.89 / concentration)
        self.assertTrue(np.allclose(moisture_diffusivity(concentration), expected))
        self.assertAlmostEqual(float(moisture_diffusivity(np.array([2.55]))[0]), 4.937e-9, delta=2e-12)

    def test_internal_and_output_grids_can_have_different_spacing(self):
        internal = build_radial_grid_cm(radius_cm=2.0, dr_cm=0.0025)
        output = build_radial_grid_cm(radius_cm=2.0, dr_cm=0.1)
        self.assertEqual(len(internal), 801)
        self.assertEqual(len(output), 21)
        self.assertEqual(output[-1], 2.0)

    def test_solver_preserves_initial_state_and_surface_responds_first(self):
        environment = EnvironmentSeries(
            time_s=np.array([0.0, 60.0]),
            temperature_c=np.array([28.0, 35.0]),
            moisture=np.array([0.020, 0.025]),
        )
        config = SolverConfig(
            internal_dr_cm=0.05,
            output_dr_cm=0.1,
            duration_s=60,
            output_dt_s=1.0,
            max_time_step_s=2.0,
        )
        result = solve_problem1(environment, config)
        self.assertEqual(result.temperature_c.shape, (61, 21))
        self.assertEqual(result.moisture.shape, (61, 21))
        self.assertTrue(np.allclose(result.temperature_c[0], 28.0))
        self.assertTrue(np.allclose(result.moisture[0], 2.55))
        self.assertGreater(result.temperature_c[-1, -1], result.temperature_c[-1, 0])
        self.assertLess(result.moisture[-1, -1], result.moisture[-1, 0])
        self.assertTrue(np.isfinite(result.temperature_c).all())
        self.assertTrue(np.isfinite(result.moisture).all())

    def test_markdown_table_formats_results_to_four_decimals(self):
        text = markdown_table(["时间/s", "0 cm"], [[100.0, 28.12346]])
        self.assertIn("| 时间/s | 0 cm |", text)
        self.assertIn("| 100 | 28.1235 |", text)


if __name__ == "__main__":
    unittest.main()
