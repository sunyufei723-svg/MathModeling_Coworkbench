import sys
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from solver import (  # noqa: E402
    EnvironmentSeries,
    SolverConfig,
    build_radial_grid_cm,
    interface_average,
    moisture_diffusivity,
    solve_problem1,
)


class Problem1ImprovedTests(unittest.TestCase):
    def test_harmonic_interface_average(self):
        left = np.array([2.0, 4.0])
        right = np.array([4.0, 0.0])
        # 谐波平均 2*l*r/(l+r)；任一侧为 0 时界面 D→0（比算术平均更物理）
        self.assertTrue(np.allclose(interface_average(left, right, "harmonic"), [8.0 / 3.0, 0.0]))

    def test_arithmetic_interface_average_matches_original(self):
        left = np.array([2.0, 4.0])
        right = np.array([4.0, 0.0])
        # 算术平均 0.5*(l+r) ＝ 原版 code/problem1/solver.py 的行为
        self.assertTrue(np.allclose(interface_average(left, right, "arithmetic"), [3.0, 2.0]))

    def test_unknown_interface_mean_raises(self):
        with self.assertRaises(ValueError):
            interface_average(np.array([1.0]), np.array([1.0]), "geometric")

    def test_harmonic_never_exceeds_arithmetic(self):
        rng = np.random.default_rng(0)
        left = rng.uniform(1e-9, 5e-9, 64)
        right = rng.uniform(1e-9, 5e-9, 64)
        harmonic = interface_average(left, right, "harmonic")
        arithmetic = interface_average(left, right, "arithmetic")
        self.assertTrue(np.all(harmonic <= arithmetic + 1e-20))

    def test_diffusivity_uses_inverse_moisture_formula(self):
        concentration = np.array([2.55, 1.0])
        self.assertTrue(np.allclose(moisture_diffusivity(concentration), 7e-9 * np.exp(-0.89 / concentration)))

    def test_internal_and_output_grids_can_have_different_spacing(self):
        self.assertEqual(len(build_radial_grid_cm(2.0, 0.0025)), 801)
        self.assertEqual(len(build_radial_grid_cm(2.0, 0.1)), 21)

    def test_default_config_is_the_improved_behaviour(self):
        config = SolverConfig()
        self.assertEqual(config.interface_mean, "harmonic")
        self.assertTrue(config.clip_negative_moisture)

    def test_temperature_is_decoupled_from_interface_mean(self):
        """温度场用常物性 k、界面 transport 为常数，与 interface_mean 无关 → 两种平均温度逐点相等。"""
        environment = EnvironmentSeries(
            time_s=np.array([0.0, 120.0]),
            temperature_c=np.array([28.0, 40.0]),
            moisture=np.array([0.01963, 0.021]),
        )
        config = SolverConfig(internal_dr_cm=0.1, output_dr_cm=0.1, duration_s=120, output_dt_s=1.0, max_time_step_s=5.0)
        harmonic_result = solve_problem1(environment, config)
        arithmetic_result = solve_problem1(environment, replace(config, interface_mean="arithmetic"))
        self.assertTrue(np.array_equal(harmonic_result.temperature_c, arithmetic_result.temperature_c))
        # 水分场依赖 D(C) 的界面平均，开关必须真正接进计算路径（非 no-op）→ 两者不逐位相等。
        # 注意：温和短算例下 D(C) 近均匀、谐波≈算术，差异很小（allclose 为真），其量级由
        # run_and_verify.py 在真实 30 min 工况下量化并写入 verification.json，此处只验证「确有差异」。
        self.assertFalse(np.array_equal(harmonic_result.moisture, arithmetic_result.moisture))

    def test_short_improved_run_is_finite_and_physical(self):
        environment = EnvironmentSeries(
            time_s=np.array([0.0, 60.0]),
            temperature_c=np.array([28.0, 35.0]),
            moisture=np.array([0.020, 0.025]),
        )
        config = SolverConfig(internal_dr_cm=0.05, output_dr_cm=0.1, duration_s=60, output_dt_s=1.0, max_time_step_s=2.0)
        result = solve_problem1(environment, config)
        self.assertEqual(result.temperature_c.shape, (61, 21))
        self.assertEqual(result.moisture.shape, (61, 21))
        self.assertTrue(np.isfinite(result.temperature_c).all())
        self.assertTrue(np.isfinite(result.moisture).all())
        self.assertGreaterEqual(result.moisture.min(), 0.0)  # C≥0 裁剪保证非负
        self.assertGreater(result.temperature_c[-1, -1], result.temperature_c[-1, 0])  # 表面先升温
        self.assertLess(result.moisture[-1, -1], result.moisture[-1, 0])  # 表面先脱水


if __name__ == "__main__":
    unittest.main()
