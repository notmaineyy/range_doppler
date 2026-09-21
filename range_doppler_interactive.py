"""
Interactive range-Doppler explorer.

Run (from the project root)::

    .venv/bin/python range_doppler_interactive.py

Use the sliders / checkbox and watch the range-Doppler map (left) and the
fully-compressed SAR image (right) update live.

Toggles
-------
* Bandwidth B          : range resolution dR = c/(2B)  (clarity, not position)
* Radial velocity vr   : Doppler centroid f_dc = 2*vr/lam and range walk
                         (position error along Doppler / azimuth)
* Antenna length La    : azimuth resolution rho_az = La/2 and Doppler
                         bandwidth Bd = 2*vp/La  (clarity, not position)
* Along-track velocity : azimuth filter mismatch -> defocus (clarity)
* SNR / speckle        : image-domain noise floor and multiplicative Rayleigh
                         speckle (detectability / clarity)

The azimuth matched filter is applied in the Doppler (frequency) domain, which
is exactly the Range-Doppler Algorithm and keeps updates fast enough for
real-time toggling.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, CheckButtons, Button

import range_doppler_demo as rd

C = rd.C


# --------------------------------------------------------------------------- #
# Fast range-Doppler algorithm (azimuth matched filter in Doppler domain)
# --------------------------------------------------------------------------- #
def rda_compress(cfg, d, rc):
    f_a, _, _, _, Na, _ = rd.axes(cfg, d)
    H = np.exp(-1j * np.pi * f_a ** 2 / d["fR"])      # azimuth reference
    rd_map = np.fft.fftshift(np.fft.fft(rc, axis=0), axes=0)
    ac = np.fft.ifft(np.fft.ifftshift(rd_map * H[:, None], axes=0), axis=0)
    return rd_map, ac


def to_dB(x, floor=1e-6):
    m = np.abs(x)
    m = m / (m.max() + 1e-15)
    return 20.0 * np.log10(m + floor)


# --------------------------------------------------------------------------- #
# Full simulation -> two display images + readout metadata
# --------------------------------------------------------------------------- #
def simulate(base_cfg, t_f, B, vr, La, vt, snr, speckle, rng):
    cfg = dict(base_cfg)
    cfg["B"] = B
    cfg["La"] = La
    d = rd.derive(cfg)
    t_m = rd.slow_time(cfg, d)
    R = rd.slant_range(cfg, t_m, vr=vr, vt=vt)
    data = rd.raw_echo(cfg, d, t_m, t_f, R)
    rc = rd.range_compress(cfg, d, data)
    rd_map, ac = rda_compress(cfg, d, rc)

    # image-domain noise + speckle (kept off the range-Doppler map)
    ac = ac / (np.abs(ac).max() + 1e-15)
    if speckle:
        ac = ac * (rng.standard_normal(ac.shape)
                   + 1j * rng.standard_normal(ac.shape)) / np.sqrt(2)
    if snr < 40.0:
        sigma = 10.0 ** (-snr / 20.0)
        ac = ac + sigma * (rng.standard_normal(ac.shape)
                           + 1j * rng.standard_normal(ac.shape)) / np.sqrt(2)

    rd_disp = to_dB(rd_map)
    im_disp = to_dB(ac)

    f_a, R_axis, x_axis, _, Na, Nr = rd.axes(cfg, d)
    fd = 2.0 * vr / d["lam"]
    meta = dict(dR=d["dR"], rho_az=d["rho_az"], Bd=d["Bd"], fd=fd, Na=Na,
                R_axis=R_axis, x_axis=x_axis, f_a=f_a)
    return rd_disp, im_disp, meta


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #
class Explorer:
    def __init__(self):
        self.base_cfg = rd.make_cfg()
        self.t_f, _ = rd.fast_time(self.base_cfg)

        self.fig = plt.figure(figsize=(13, 9))
        self.ax_rd = self.fig.add_axes([0.06, 0.42, 0.40, 0.50])
        self.ax_im = self.fig.add_axes([0.54, 0.42, 0.40, 0.50])

        self.im_rd = None
        self.im_im = None
        self.txt = None

        # sliders: (label, vmin, vmax, init) -> fraction of figure height
        specs = [
            ("Bandwidth B [MHz]", 20.0, 500.0, 200.0),
            ("Radial vel. $v_r$ [m/s]", -5.0, 5.0, 0.0),
            ("Antenna length $L_a$ [m]", 0.5, 5.0, 2.0),
            ("Along-track vel. $v_t$ [m/s]", 0.0, 80.0, 0.0),
            ("SNR [dB]", -10.0, 40.0, 30.0),
        ]
        y = 0.26
        self.sliders = {}
        for label, lo, hi, init in specs:
            ax = self.fig.add_axes([0.08, y, 0.72, 0.02])
            sl = Slider(ax, label, lo, hi, valinit=init)
            sl.on_changed(self.update)
            self.sliders[label] = sl
            y -= 0.045

        ax_chk = self.fig.add_axes([0.08, 0.31, 0.12, 0.06])
        self.chk = CheckButtons(ax_chk, ["speckle"], [False])
        self.chk.on_clicked(self.update)

        ax_btn = self.fig.add_axes([0.86, 0.32, 0.08, 0.045])
        self.btn = Button(ax_btn, "Reset")
        self.btn.on_clicked(self.reset)

        self.fig.canvas.mpl_connect("key_press_event", self.on_key)
        self.update()

    def _vals(self):
        s = self.sliders
        B = s["Bandwidth B [MHz]"].val * 1e6
        vr = s["Radial vel. $v_r$ [m/s]"].val
        La = s["Antenna length $L_a$ [m]"].val
        vt = s["Along-track vel. $v_t$ [m/s]"].val
        snr = s["SNR [dB]"].val
        speckle = bool(self.chk.get_status()[0])
        return B, vr, La, vt, snr, speckle

    def update(self, val=None):
        B, vr, La, vt, snr, speckle = self._vals()
        rng = np.random.default_rng(0)      # fixed seed -> no flicker
        rd_disp, im_disp, meta = simulate(self.base_cfg, self.t_f, B, vr, La,
                                          vt, snr, speckle, rng)

        Ra = meta["R_axis"]; xa = meta["x_axis"]; fa = meta["f_a"]

        if self.im_rd is None:
            self.im_rd = self.ax_rd.imshow(
                rd_disp, aspect="auto", origin="lower", cmap="inferno",
                extent=[Ra[0], Ra[-1], fa[0], fa[-1]], vmin=-60, vmax=0)
            self.ax_rd.set_xlabel("Range [m]")
            self.ax_rd.set_ylabel("Doppler [Hz]")
            self.ax_rd.set_title("Range-Doppler map")
            self.im_im = self.ax_im.imshow(
                im_disp, aspect="auto", origin="lower", cmap="inferno",
                extent=[Ra[0], Ra[-1], xa[0], xa[-1]], vmin=-60, vmax=0)
            self.ax_im.set_xlabel("Range [m]")
            self.ax_im.set_ylabel("Azimuth [m]")
            self.ax_im.set_title("Compressed image (range x azimuth)")
            self.fig.colorbar(self.im_rd, ax=self.ax_rd, fraction=0.046, pad=0.04)
            self.fig.colorbar(self.im_im, ax=self.ax_im, fraction=0.046, pad=0.04)
        else:
            self.im_rd.set_data(rd_disp)
            self.im_rd.set_extent([Ra[0], Ra[-1], fa[0], fa[-1]])
            self.im_im.set_data(im_disp)
            self.im_im.set_extent([Ra[0], Ra[-1], xa[0], xa[-1]])

        self.ax_rd.axhline(meta["fd"], color="c", ls="--", lw=0.7)
        self.ax_rd.axhline(0, color="w", ls=":", lw=0.5)

        if self.txt is None:
            self.txt = self.fig.text(0.5, 0.355, "", ha="center", fontsize=11)
        self.txt.set_text(
            f"dR = c/2B = {meta['dR']:.2f} m    "
            f"rho_az = La/2 = {meta['rho_az']:.2f} m    "
            f"f_dc = 2vr/lam = {meta['fd']:+6.0f} Hz    "
            f"Bd = 2vp/La = {meta['Bd']:.0f} Hz    "
            f"Na = {meta['Na']}")

        self.fig.canvas.draw_idle()

    def reset(self, event):
        for label, init in [("Bandwidth B [MHz]", 200.0),
                            ("Radial vel. $v_r$ [m/s]", 0.0),
                            ("Antenna length $L_a$ [m]", 2.0),
                            ("Along-track vel. $v_t$ [m/s]", 0.0),
                            ("SNR [dB]", 30.0)]:
            self.sliders[label].set_val(init)
        if self.chk.get_status()[0]:
            self.chk.set_active(0)
        self.update()

    def on_key(self, event):
        if event.key == "r":
            self.reset(None)


def main():
    Explorer()
    plt.show()


if __name__ == "__main__":
    main()
