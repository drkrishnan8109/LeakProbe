import unittest
import numpy as np
from simulator import simulate

class HydraulicTests(unittest.TestCase):
    def test_normal_conservation(self):
        normal = simulate('normal')
        self.assertEqual(len(normal), 10)
        np.testing.assert_allclose(normal.F01_flow_lps, 10, atol=1e-4)
        np.testing.assert_allclose(normal.MA_pressure_m, normal.MB_pressure_m, atol=1e-6)

    def test_leak_onset_and_branch_symmetry(self):
        normal, a, b = [simulate(x) for x in ('normal', 'leak_A', 'leak_B')]
        cols = ['F01_flow_lps','P01_pressure_m','MA_pressure_m','MB_pressure_m']
        np.testing.assert_allclose(a[cols].iloc[:4], normal[cols].iloc[:4], atol=1e-4)
        self.assertGreater(a.F01_flow_lps.iloc[-1], normal.F01_flow_lps.iloc[-1])
        self.assertLess(a.MA_pressure_m.iloc[-1], a.MB_pressure_m.iloc[-1])
        np.testing.assert_allclose(a.F01_flow_lps, b.F01_flow_lps, atol=1e-4)
        np.testing.assert_allclose(a.MA_pressure_m, b.MB_pressure_m, atol=1e-4)

    def test_reject_invalid_scenario_and_hole(self):
        for scenario, size in [('unknown',16), ('leak_A',-1), ('leak_A',float('nan'))]:
            with self.assertRaises(ValueError): simulate(scenario, size)

if __name__ == '__main__': unittest.main()
