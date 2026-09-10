import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from solver import (
    EnvironmentSeries,
    SolverConfig,
    build_output_seconds,
    drying_complete,
    moisture_diffusivity,
    solve_problem3,
)


class Problem3SolverTests(unittest.TestCase):
    def test_environment_holds_last_boundary_after_attachment_range(self):
        env = EnvironmentSeries(
            time_s=np.array([0.0, 60.0]),
            temperature_c=np.array([28.0, 50.0]),
            moisture=np.array([0.02, 0.05]),
        )

        self.assertEqual(env.temperature_at(120.0), 50.0)
        self.assertEqual(env.moisture_at(120.0), 0.05)

    def test_diffusivity_uses_division_by_c_and_kelvin_temperature(self):
        c = np.array([2.55])
        t_c = np.array([50.0])

        expected = 2.4e-3 * np.exp(-0.45 / 2.55) * np.exp(-3850.0 / (50.0 + 273.15))

        self.assertAlmostEqual(float(moisture_diffusivity(c, t_c)[0]), expected)

    def test_drying_complete_requires_every_radius_below_threshold(self):
        self.assertFalse(drying_complete(np.array([0.10, 0.16, 0.08]), threshold=0.15))
        self.assertTrue(drying_complete(np.array([0.10, 0.149, 0.08]), threshold=0.15))

    def test_output_seconds_are_sixty_second_multiples_and_include_end(self):
        seconds = build_output_seconds(end_time_s=3700, interval_s=60)

        self.assertEqual(seconds[0], 60)
        self.assertEqual(seconds[1], 120)
        self.assertEqual(seconds[-2], 3660)
        self.assertEqual(seconds[-1], 3700)

    def test_solver_stops_when_full_profile_is_below_threshold(self):
        env = EnvironmentSeries(
            time_s=np.array([0.0, 60.0]),
            temperature_c=np.array([50.0, 50.0]),
            moisture=np.array([0.05, 0.05]),
        )
        config = SolverConfig(
            duration_limit_s=600,
            dt_s=10.0,
            dr_cm=0.5,
            initial_temperature_c=50.0,
            initial_moisture=0.149,
            completion_threshold=0.15,
            mass_transfer_m_s=1e-4,
        )

        result = solve_problem3(env, config)

        self.assertLessEqual(float(result.moisture[-1].max()), 0.15)
        self.assertGreater(result.drying_end_time_s, 0)
        self.assertTrue(result.coupling_converged.all())


if __name__ == "__main__":
    unittest.main()
