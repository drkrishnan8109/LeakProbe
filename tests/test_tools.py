import unittest
from tools import Investigation, dispatch

class ToolTests(unittest.TestCase):
    def test_upstream_ambiguity_and_measurement_update(self):
        session = Investigation()
        before = dispatch(session, 'compare_hypotheses', {})['ranking']
        scores = {r['scenario']: r['normalized_rmse'] for r in before}
        self.assertAlmostEqual(scores['leak_A'], scores['leak_B'], places=5)
        observations = dispatch(session, 'get_observations', {})
        self.assertNotIn('MA_pressure_m', observations['readings'][0])
        self.assertEqual(dispatch(session, 'recommend_measurement', {})['recommended'], 'MA')
        self.assertIn('error', dispatch(session, 'collect_demo_measurement', {'point':'MB'}))
        dispatch(session, 'collect_demo_measurement', {'point':'MA'})
        after = dispatch(session, 'compare_hypotheses', {})['ranking']
        self.assertEqual(after[0]['scenario'], 'leak_A')
        self.assertLess(after[0]['normalized_rmse'], after[1]['normalized_rmse'])

    def test_schema_and_allowlist(self):
        session = Investigation()
        for name, args in [('shell', {}), ('get_observations', {'path':'/etc/passwd'}),
                           ('collect_demo_measurement', {'point':'INVALID'})]:
            self.assertIn('error', dispatch(session, name, args))

    def test_same_measurement_not_charged_twice(self):
        session = Investigation()
        dispatch(session, 'collect_demo_measurement', {'point':'MA'})
        dispatch(session, 'collect_demo_measurement', {'point':'MA'})
        self.assertEqual(session.remaining_minutes, 5)
