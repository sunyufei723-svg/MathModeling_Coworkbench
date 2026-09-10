import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from solver import EnvironmentSeries, SolverConfig, build_radial_grid_cm, solve_problem1
from run_problem1 import dataframe_to_markdown


class Problem1SolverTests(unittest.TestCase):
    def test_environment_series_linearly_interpolates_temperature_and_moisture(self):
        env = EnvironmentSeries(
            time_s=np.array([0.0, 60.0]),
            temperature_c=np.array([28.0, 30.0]),
            moisture=np.array([0.020, 0.026]),
        )

        self.assertEqual(env.temperature_at(30.0), 29.0)
        self.assertEqual(env.moisture_at(30.0), 0.023)

    def test_build_radial_grid_uses_required_spacing_and_surface_radius(self):
        grid = build_radial_grid_cm(radius_cm=2.0, dr_cm=0.1)

        self.assertEqual(len(grid), 21)
        self.assertEqual(grid[0], 0.0)
        self.assertEqual(grid[-1], 2.0)
        self.assertTrue(np.allclose(np.diff(grid), 0.1))

    def test_problem1_solver_preserves_initial_state_and_surface_responds_first(self):
        env = EnvironmentSeries(
            time_s=np.array([0.0, 1800.0]),
            temperature_c=np.array([28.0, 50.0]),
            moisture=np.array([0.01963, 0.05000]),
        )
        config = SolverConfig(duration_s=120, dt_s=1.0, dr_cm=0.1)

        result = solve_problem1(env, config)

        self.assertEqual(result.temperature_c.shape, (121, 21))
        self.assertEqual(result.moisture.shape, (121, 21))
        self.assertTrue(np.allclose(result.temperature_c[0], 28.0))
        self.assertTrue(np.allclose(result.moisture[0], 2.55))
        self.assertGreater(result.temperature_c[-1, -1], result.temperature_c[-1, 0])
        self.assertLess(result.moisture[-1, -1], result.moisture[-1, 0])
        self.assertTrue(np.isfinite(result.temperature_c).all())
        self.assertTrue(np.isfinite(result.moisture).all())

    def test_dataframe_to_markdown_does_not_need_optional_tabulate_package(self):
        import pandas as pd

        frame = pd.DataFrame({"时间/s": [100], "0 cm": [28.12345], "2 cm": [29.0]})

        markdown = dataframe_to_markdown(frame)

        self.assertIn("| 时间/s | 0 cm | 2 cm |", markdown)
        self.assertIn("| 100 | 28.12345 | 29 |", markdown)


if __name__ == "__main__":
    unittest.main()
