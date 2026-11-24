import unittest

from virtual_flow import fit, predict


def rows():
    return [dict(model='amber95', installation_id=g, mode='heating', defrost=0,
                 buh=0, steady=1, power_source='metered', frequency_hz=30+i,
                 outside_c=5, supply_c=35, return_c=32, power_w=600+i*20,
                 measured_flow_lh=1000+i*10, water_factor=1.163)
            for g in ('a','b') for i in range(40)]


class TestVirtualFlow(unittest.TestCase):
    def test_fit_and_holdout(self):
        data = rows()
        artifact = fit(data, 'amber95')
        self.assertEqual(artifact['installation_count'], 2)
        self.assertEqual(len(artifact['validation']), 2)
        self.assertTrue(all(v['predicted_rows'] == 40 for v in artifact['validation']))
        result = predict(data[15], artifact)
        self.assertEqual(result['source'], 'virtual_experimental')
        self.assertAlmostEqual(result['flow_lh'], 1150, delta=57.5)
        self.assertAlmostEqual(result['thermal_w'], result['flow_lh']*3*1.163)


    def test_abstention(self):
        data = rows(); artifact = fit(data, 'amber95')
        for change in [dict(defrost=1),dict(buh=1),dict(steady=0),
                       dict(return_c=34),dict(mode='cooling'),dict(model='amber65'),
                       dict(frequency_hz=100),dict(power_source='estimated'),dict(power_w='nan')]:
            with self.subTest(change=change):
                self.assertIsNone(predict(dict(data[0], **change), artifact)['flow_lh'])


    def test_single_installation_is_unvalidated(self):
        data = rows()[:40]
        artifact = fit(data, 'amber95')
        self.assertEqual(artifact['validation'], [])
        self.assertIsNone(artifact['error_fraction_p90_worst_installation'])
