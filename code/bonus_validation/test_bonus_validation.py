import unittest

import run_bonus_validation as bv


class LayeredUQTests(unittest.TestCase):
    def test_q4_layered_uq_names_model_form_as_dominant(self):
        layered = bv.layered_uq_statement()
        q4 = layered["problem4"]

        self.assertEqual(q4["dominant_layer"], "shrinkage_density_closure")
        self.assertGreater(q4["shrinkage_density_closure"]["upper_shift_h"], q4["boundary_surrogate"]["half_width_h"])
        self.assertAlmostEqual(q4["main_answer_h"], 50.824506989, places=6)
        self.assertAlmostEqual(q4["shrinkage_density_closure"]["upper_bound_h"], 60.7312, places=4)


if __name__ == "__main__":
    unittest.main()
