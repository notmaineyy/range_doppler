"""Physics regression checks: .venv/bin/python -m unittest test_sar_model.py"""
import unittest
import numpy as np
import sar_model as sar

class Physics(unittest.TestCase):
    def test_stationary_range_response_and_position(self):
        for b in (20,100,500):
            s=sar.simulate(bandwidth_mhz=b)
            self.assertAlmostEqual(s['peak_r'],0)
            self.assertAlmostEqual(s['peak_x'],0)
            expected=abs(np.sinc(s['r']/s['dr']))
            np.testing.assert_allclose(s['range_profile'],expected,atol=1e-12)

    def test_antenna_resolution_first_null(self):
        for length in (.5,2,5):
            s=sar.simulate(antenna_length=length)
            # Finite sampled rectangular aperture -> Dirichlet response.
            n=len(s['t']); f=s['x'] * (2*sar.V/(sar.WAVELENGTH*sar.R0))
            expected=np.abs(np.sinc(n*f/sar.PRF)/np.sinc(f/sar.PRF))
            np.testing.assert_allclose(s['azimuth_profile'],expected,atol=1e-10)
            self.assertAlmostEqual(s['peak_x'],0)
            self.assertLess(abs(s['da']-sar.WAVELENGTH*sar.R0/(2*sar.V*s['duration'])),.005)

    def test_velocity_sign_shift_and_peak_loss(self):
        for velocity in (-3,3):
            s=sar.simulate(radial_velocity=velocity)
            pixel=s['x'][1]-s['x'][0]
            self.assertLess(abs(s['peak_x']-velocity*sar.R0/sar.V),pixel)
            self.assertLess(s['peak_amplitude'],1)
            self.assertGreater(s['walk'],s['dr'])

    def test_extreme_parameters_and_sampling(self):
        s=sar.simulate(500,5,.5)
        self.assertLess(abs(s['fd'])+s['doppler_bw']/2,sar.PRF/2)
        self.assertTrue(np.isfinite(s['image']).all())
        self.assertEqual(s['image'].shape,(len(s['x']),len(s['r'])))
        self.assertEqual(s['rd'].shape,(len(s['doppler']),len(s['r'])))
        # Range response is sampled at >=6 pixels per finest first-null width.
        self.assertLessEqual(s['r'][1]-s['r'][0],s['dr']/5.9)

if __name__=='__main__':unittest.main()
