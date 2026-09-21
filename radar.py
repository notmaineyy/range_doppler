"""
Pure-numpy SAR range-Doppler simulation core.

Shared by the CLI demo (range_doppler_demo.py), the desktop interactive
explorer (range_doppler_interactive.py) and the web app (app.py).

No matplotlib / plotting imports live here, so the module is safe to import
inside headless web servers.

Image axes
----------
* Range axis  : fast-time (echo delay), R = c*tau/2.  Clarity set by the
                range resolution  dR = c/(2*B)  (the BANDWIDTH B).
* Doppler axis: slow-time (platform motion).  The ANTENNA LENGTH La sets the
                beamwidth  theta = lam/La  -> Doppler bandwidth Bd = 2*vp/La
                and azimuth resolution  rho_az = La/2.
"""

import numpy as np

C = 3.0e8


# --------------------------------------------------------------------------- #
# Geometry / derived quantities
# --------------------------------------------------------------------------- #
def make_cfg():
    cfg = dict(
        fc=10.0e9,      # carrier (X-band)
        B=200.0e6,      # chirp bandwidth
        Tp=5.0e-6,      # pulse duration
        Fs=400.0e6,     # range sampling frequency (>= 2B)
        vp=150.0,       # platform along-track velocity [m/s]
        La=2.0,         # antenna length [m]
        PRF=800.0,      # pulse repetition frequency [Hz]
        R0=5.0e3,       # slant range to scene center [m]
        swath=300.0,    # half-width of the range window [m]
    )
    return cfg


def derive(cfg):
    lam = C / cfg["fc"]
    Kr = cfg["B"] / cfg["Tp"]                  # chirp rate
    theta = lam / cfg["La"]                    # azimuth beamwidth
    Ta = cfg["R0"] * theta / cfg["vp"]         # synthetic aperture time
    fR = 2.0 * cfg["vp"] ** 2 / (lam * cfg["R0"])  # Doppler rate
    Bd = 2.0 * cfg["vp"] / cfg["La"]           # Doppler bandwidth
    dR = C / (2.0 * cfg["B"])                  # range resolution
    rho_az = cfg["La"] / 2.0                   # azimuth resolution (SAR)
    return dict(lam=lam, Kr=Kr, theta=theta, Ta=Ta, fR=fR, Bd=Bd, dR=dR,
                rho_az=rho_az)


def slow_time(cfg, d):
    Na = int(np.round(cfg["PRF"] * d["Ta"]))
    Na += Na % 2                                   # keep even
    t = (np.arange(Na) - Na / 2) / cfg["PRF"]      # centred on t = 0
    return t


def fast_time(cfg):
    t0 = 2.0 * (cfg["R0"] - cfg["swath"]) / C
    dur = 2.0 * cfg["swath"] / C + cfg["Tp"]
    Nr = int(np.ceil(cfg["Fs"] * dur))
    t = t0 + np.arange(Nr) / cfg["Fs"]
    return t, t0


# --------------------------------------------------------------------------- #
# Signal model
# --------------------------------------------------------------------------- #
def slant_range(cfg, t_m, x0=0.0, vr=0.0, vt=0.0):
    """Instantaneous two-way path / 2 for a point target.

    x0 : along-track position of closest approach [m]
    vr : radial (line-of-sight) velocity, positive = approaching [m/s]
    vt : target along-track velocity [m/s]
    """
    across = cfg["R0"] - vr * t_m
    along = (cfg["vp"] - vt) * t_m - x0
    return np.sqrt(across ** 2 + along ** 2)


def raw_echo(cfg, d, t_m, t_fast, R, A=1.0):
    """Baseband received echo for a single point scatterer (no noise)."""
    Na, Nr = len(t_m), len(t_fast)
    data = np.zeros((Na, Nr), dtype=complex)
    tau = 2.0 * R / C                              # two-way delay
    t = t_fast[None, :] - tau[:, None]             # (Na, Nr) fast-time offset
    mask = np.abs(t) <= cfg["Tp"] / 2.0
    phase = -4.0 * np.pi * R[:, None] / d["lam"]   # Doppler / azimuth phase
    val = A * np.exp(1j * phase) * np.exp(1j * np.pi * d["Kr"] * t ** 2)
    data[mask] = val[mask]
    return data


def range_compress(cfg, d, data):
    """Matched-filter each slow-time row with the transmit chirp (FFT based)."""
    Na, Nr = data.shape
    Np = int(round(cfg["Tp"] * cfg["Fs"]))
    t_ref = np.arange(Np) / cfg["Fs"]
    ref = np.exp(1j * np.pi * d["Kr"] * t_ref ** 2)
    nfft = int(2 ** np.ceil(np.log2(Nr + Np - 1)))
    H = np.conj(np.fft.fft(ref, nfft))
    rc = np.fft.ifft(np.fft.fft(data, nfft, axis=1) * H, axis=1)[:, :Nr]
    return rc


def range_doppler_map(rc):
    """FFT along slow-time (azimuth) -> range-Doppler domain."""
    return np.fft.fftshift(np.fft.fft(rc, axis=0), axes=0)


def azimuth_compress(cfg, d, rc, fR=None):
    """Azimuth matched filter along slow-time, per range bin (time domain)."""
    t_m = slow_time(cfg, d)
    if fR is None:
        fR = d["fR"]
    h = np.exp(1j * np.pi * fR * t_m ** 2)          # conj. of received quadratic
    out = np.empty_like(rc)
    for n in range(rc.shape[1]):
        out[:, n] = np.convolve(rc[:, n], h, mode="same")
    return out


def rda_compress(cfg, d, rc):
    """Azimuth matched filter in the Doppler domain (the Range-Doppler
    Algorithm) -- fast enough for real-time toggling."""
    f_a = doppler_axis(cfg, d)
    H = np.exp(-1j * np.pi * f_a ** 2 / d["fR"])    # azimuth reference
    rd_map = np.fft.fftshift(np.fft.fft(rc, axis=0), axes=0)
    ac = np.fft.ifft(np.fft.ifftshift(rd_map * H[:, None], axes=0), axis=0)
    return rd_map, ac


def axes(cfg, d):
    t_m = slow_time(cfg, d)
    t_f, t0 = fast_time(cfg)
    Na, Nr = len(t_m), len(t_f)
    f_a = np.fft.fftshift(np.fft.fftfreq(Na, d=1.0 / cfg["PRF"]))
    R_axis = (t0 + np.arange(Nr) / cfg["Fs"]) * C / 2.0
    x_axis = cfg["vp"] * t_m                        # azimuth spatial axis
    return f_a, R_axis, x_axis, t_m, Na, Nr


def doppler_axis(cfg, d):
    t_m = slow_time(cfg, d)
    Na = len(t_m)
    return np.fft.fftshift(np.fft.fftfreq(Na, d=1.0 / cfg["PRF"]))


# --------------------------------------------------------------------------- #
# Display helpers
# --------------------------------------------------------------------------- #
def to_dB(x, floor=1e-6):
    m = np.abs(x)
    m = m / (m.max() + 1e-15)
    return 20.0 * np.log10(m + floor)


def downsample2d(z, max_rows=512, max_cols=512):
    """Max-pool `z` down to at most max_rows x max_cols (preserves peaks)."""
    R, Cc = z.shape
    rr = int(np.ceil(R / max_rows))
    cc = int(np.ceil(Cc / max_cols))
    if rr <= 1 and cc <= 1:
        return z, 1, 1
    Rc = (R // rr) * rr
    Cc2 = (Cc // cc) * cc
    z = z[:Rc, :Cc2]
    return z.reshape(Rc // rr, rr, Cc2 // cc, cc).max(axis=(1, 3)), rr, cc


# --------------------------------------------------------------------------- #
# Full simulation -> two display images + readout metadata
# --------------------------------------------------------------------------- #
def simulate(base_cfg, t_f, B, vr, La, vt, snr, speckle, rng):
    cfg = dict(base_cfg)
    cfg["B"] = B
    cfg["La"] = La
    d = derive(cfg)
    t_m = slow_time(cfg, d)
    R = slant_range(cfg, t_m, vr=vr, vt=vt)
    data = raw_echo(cfg, d, t_m, t_f, R)
    rc = range_compress(cfg, d, data)
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

    f_a, R_axis, x_axis, _, Na, Nr = axes(cfg, d)
    fd = 2.0 * vr / d["lam"]
    meta = dict(dR=d["dR"], rho_az=d["rho_az"], Bd=d["Bd"], fd=fd, Na=Na,
                Nr=Nr, Ta=d["Ta"], lam=d["lam"],
                R_axis=R_axis, x_axis=x_axis, f_a=f_a)
    return rd_disp, im_disp, meta
