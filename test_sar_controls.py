import unittest
import sar_model as sar
from streamlit.testing.v1 import AppTest

class Controls(unittest.TestCase):
    def test_aperture(self):
        full=sar.simulate()
        short=sar.simulate(aperture_fraction=.25)
        self.assertAlmostEqual(short['da']/full['da'],4)
        self.assertAlmostEqual(short['peak_x'],0)
        self.assertAlmostEqual(short['azimuth_width_3db']/full['azimuth_width_3db'],4,delta=.05)
        moving=sar.simulate(radial_velocity=3,aperture_fraction=.25)
        self.assertAlmostEqual(moving['walk'],.375)
        self.assertAlmostEqual(moving['peak_x'],100)

    def test_window(self):
        rectangular=sar.simulate()
        hann=sar.simulate(azimuth_window='Hann')
        self.assertGreater(hann['azimuth_width_3db'],rectangular['azimuth_width_3db'])
        self.assertAlmostEqual(hann['peak_amplitude'],1)
        import numpy as np
        mask=abs(hann['x'])>2.1
        self.assertLess(hann['azimuth_profile'][mask].max(),rectangular['azimuth_profile'][mask].max())

    def test_numeric_controls(self):
        app=AppTest.from_file('/Users/shermi/range_doppler/app.py').run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.sidebar.number_input),4)
        self.assertEqual(len(app.sidebar.slider),0)
        app.sidebar.number_input[0].set_value(105.)
        app.sidebar.number_input[1].set_value(3.1)
        app.sidebar.number_input[2].set_value(1.9)
        app.sidebar.number_input[3].set_value(50.)
        app.sidebar.selectbox[0].set_value('Hann').run(timeout=30)
        self.assertFalse(app.exception)
        self.assertIn('1.43 m',[m.value for m in app.metric])
        self.assertIn('+103.33 m',[m.value for m in app.metric])

if __name__=='__main__':unittest.main()
