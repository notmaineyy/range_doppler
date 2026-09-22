"""
Range-Doppler / azimuth dimensions of a SAR image.

This script simulates a single point target through the Range-Doppler
Algorithm (RDA) and shows how physical variables trade off between the
target's *clarity* (how tightly its energy is focused) and its *apparent
position* in the image.

Image axes
----------
* Range axis  : fast-time (echo delay).  R = c*tau/2.   Clarity limited by
                the slant-range resolution  dR = c*b_r / (2*B),  so it is set
                by the transmitted BANDWIDTH B (b_r = range IPR windowing
                broadening factor).  B does NOT move the target.
* Doppler axis: slow-time (platform motion).  The target traces a quadratic
                Doppler history  f_a(t) = -2*vp^2*t/(lam*R0).  The antenna
                LENGTH La sets the beamwidth  theta = lam/La, hence the
                observed Doppler bandwidth  Bd = 2*vp/La  and the azimuth
                (cross-range) resolution
                    rho_az = lam * R0 * b_a / (2 * L_syn),
                where L_syn = vp * T_a,proc is the processed synthetic aperture
                length and b_a is the azimuth IPR broadening factor.  At full
                aperture with rectangular weighting this reduces to La/2.
                Neither La nor vp changes a stationary target's azimuth position.

Variables exercised (each produces one figure in ./outputs)
-----------------------------------------------------------
1. Bandwidth B          -> range clarity (dR = c*b_r/2B), position unchanged.
2. Radial velocity vr   -> Doppler-centroid shift fd = 2*vr/lam, which
                           displaces the target in azimuth by dx = vr*R0/vp
                           and causes range walk  vr*T_a,proc  (position error).
3. Antenna length La    -> azimuth clarity (rho_az = lam*R0*b_a/2L_syn,
                           Bd = 2*vp/La), position unchanged.
4. Target along-track vt-> relative-velocity mismatch defocuses the azimuth
                           response (clarity loss), position ~ unchanged.
5. SNR / speckle        -> thermal noise floor and multiplicative Rayleigh
                           speckle both degrade detectability / clarity.

All processing is done in numpy; matplotlib (Agg backend) writes PNGs.
"""

import os

import numpy as np
import matplotlib

if __name__ == "__main__":
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

C = 3.0e8
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")


# --------------------------------------------------------------------------- #
# Radar geometry / derived quantities
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
        aperture_fraction=1.0,        # fraction of full aperture processed
        range_window="Rectangular",  # range IPR weighting
        azimuth_window="Rectangular",  # azimuth IPR weighting
    )
    return cfg


def derive(cfg):
    """Derived geometry and the two spatial resolutions.

    Slant-range resolution:
        dR = c * b_r / (2 * B)              b_r = range IPR window broadening
    Azimuth resolution:
        rho_az = lam * R0 * b_a / (2 * L_syn)
    where L_syn = R0 * theta is the synthetic aperture length (the along-track
    distance over which the target is illuminated) and b_a is the azimuth IPR
    window broadening.  At full aperture with rectangular weighting L_syn = R0 *
    theta and b_a = 1, giving the familiar rho_az = lam*R0/(2*R0*theta) = La/2.
    """
    lam = C / cfg["fc"]
    Kr = cfg["B"] / cfg["Tp"]                  # chirp rate
    theta = lam / cfg["La"]                    # azimuth beamwidth
    Ta = cfg["R0"] * theta / cfg["vp"]         # full synthetic aperture time
    fR = 2.0 * cfg["vp"] ** 2 / (lam * cfg["R0"])  # Doppler rate
    Bd = 2.0 * cfg["vp"] / cfg["La"]           # Doppler bandwidth

    # Window broadening factors for the impulse response (IPR).  Rectangular
    # gives the narrowest mainlobe (factor 1); Hann trades mainlobe width for
    # much lower sidelobes (~1.30).
    B_ROAD = {"Rectangular": 1.0, "Hann": 1.30}
    b_r = B_ROAD[cfg.get("range_window", "Rectangular")]
    b_a = B_ROAD[cfg.get("azimuth_window", "Rectangular")]

    # Processed aperture: fraction of the full beam-limited illumination time.
    ap = cfg.get("aperture_fraction", 1.0)
    Ta_proc = ap * Ta                          # processed synthetic aperture time
    L_syn = cfg["vp"] * Ta_proc                # processed synthetic aperture length

    dR = C * b_r / (2.0 * cfg["B"])                        # slant-range resolution
    rho_az = lam * cfg["R0"] * b_a / (2.0 * L_syn)         # azimuth resolution
    return dict(lam=lam, Kr=Kr, theta=theta, Ta=Ta, Ta_proc=Ta_proc,
                L_syn=L_syn, fR=fR, Bd=Bd, dR=dR, rho_az=rho_az,
                b_r=b_r, b_a=b_a, ap=ap,
                range_window=cfg.get("range_window", "Rectangular"),
                azimuth_window=cfg.get("azimuth_window", "Rectangular"))


def slow_time(cfg, d):
    Na = int(np.round(cfg["PRF"] * d["Ta_proc"]))
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


def _window(name, n):
    """IPR weighting: Rectangular (factor 1.0) or Hann (mainlobe x~1.30)."""
    if name == "Hann":
        return np.hanning(n)
    return np.ones(n)


def range_compress(cfg, d, data):
    """Matched-filter each slow-time row with the transmit chirp (FFT based)."""
    Na, Nr = data.shape
    Np = int(round(cfg["Tp"] * cfg["Fs"]))
    t_ref = np.arange(Np) / cfg["Fs"]
    ref = np.exp(1j * np.pi * d["Kr"] * t_ref ** 2)
    ref = ref * _window(d.get("range_window", "Rectangular"), Np)
    nfft = int(2 ** np.ceil(np.log2(Nr + Np - 1)))
    H = np.conj(np.fft.fft(ref, nfft))
    rc = np.fft.ifft(np.fft.fft(data, nfft, axis=1) * H, axis=1)[:, :Nr]
    return rc


def range_doppler_map(rc):
    """FFT along slow-time (azimuth) -> range-Doppler domain."""
    rd = np.fft.fftshift(np.fft.fft(rc, axis=0), axes=0)
    return rd


def azimuth_compress(cfg, d, rc, fR=None):
    """Azimuth matched filter along slow-time, per range bin."""
    t_m = slow_time(cfg, d)
    if fR is None:
        fR = d["fR"]
    h = np.exp(1j * np.pi * fR * t_m ** 2)          # conj. of received quadratic
    h = h * _window(d.get("azimuth_window", "Rectangular"), len(t_m))
    out = np.empty_like(rc)
    for n in range(rc.shape[1]):
        out[:, n] = np.convolve(rc[:, n], h, mode="same")
    return out


def axes(cfg, d):
    t_m = slow_time(cfg, d)
    t_f, t0 = fast_time(cfg)
    Na, Nr = len(t_m), len(t_f)
    f_a = np.fft.fftshift(np.fft.fftfreq(Na, d=1.0 / cfg["PRF"]))
    R_axis = (t0 + np.arange(Nr) / cfg["Fs"]) * C / 2.0
    x_axis = cfg["vp"] * t_m                        # azimuth spatial axis
    return f_a, R_axis, x_axis, t_m, Na, Nr


def peak_range(R_axis, img, t_m, R0, vr=0.0):
    """Range bin of the maximum-energy slow-time sample."""
    i = np.argmax(np.abs(img).sum(axis=0))
    return R_axis[i]


# --------------------------------------------------------------------------- #
# Figure 1 : baseline range-Doppler / azimuth image
# --------------------------------------------------------------------------- #
def fig_baseline(cfg, d):
    t_m = slow_time(cfg, d)
    t_f, t0 = fast_time(cfg)
    R = slant_range(cfg, t_m)
    data = raw_echo(cfg, d, t_m, t_f, R)
    rc = range_compress(cfg, d, data)
    rd = range_doppler_map(rc)
    ac = azimuth_compress(cfg, d, rc)
    f_a, R_axis, x_axis, _, Na, Nr = axes(cfg, d)

    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6))
    im0 = axs[0].imshow(20 * np.log10(np.abs(rd) + 1e-6), aspect="auto",
                        extent=[R_axis[0], R_axis[-1], f_a[0], f_a[-1]],
                        origin="lower", cmap="inferno")
    axs[0].axhline(0, color="w", lw=0.7, ls="--")
    axs[0].set_title("Range-Doppler map (after range compression + azimuth FFT)")
    axs[0].set_xlabel("Range [m]")
    axs[0].set_ylabel("Doppler frequency $f_a$ [Hz]")
    fig.colorbar(im0, ax=axs[0], label="dB")

    im1 = axs[1].imshow(20 * np.log10(np.abs(ac) + 1e-6), aspect="auto",
                        extent=[R_axis[0], R_axis[-1], x_axis[0], x_axis[-1]],
                        origin="lower", cmap="inferno")
    axs[1].set_title("Fully compressed image (range x azimuth)")
    axs[1].set_xlabel("Range [m]")
    axs[1].set_ylabel("Azimuth $x = v_p t$ [m]")
    fig.colorbar(im1, ax=axs[1], label="dB")

    fig.suptitle(
        f"Baseline: B={cfg['B']/1e6:.0f} MHz -> dR={d['dR']:.2f} m | "
        f"La={cfg['La']} m -> rho_az={d['rho_az']:.1f} m | "
        f"Bd={d['Bd']:.0f} Hz, PRF={cfg['PRF']:.0f} Hz", y=1.02)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------- #
# Figure 2 : bandwidth -> range clarity
# --------------------------------------------------------------------------- #
def fig_bandwidth(cfg, d):
    t_m = slow_time(cfg, d)
    t_f, t0 = fast_time(cfg)
    R = slant_range(cfg, t_m)

    Bs = [50e6, 200e6, 500e6]
    fig, axs = plt.subplots(1, 3, figsize=(13, 4))
    for ax, B in zip(axs, Bs):
        c2 = dict(cfg); c2["B"] = B
        d2 = derive(c2)
        data = raw_echo(c2, d2, t_m, t_f, R)
        rc = range_compress(c2, d2, data)
        ac = azimuth_compress(c2, d2, rc)
        _, R_axis, _, _, _, _ = axes(c2, d2)
        j, i = np.unravel_index(np.argmax(np.abs(ac)), ac.shape)
        slc = np.abs(ac[j, :])                      # range slice through peak
        slc = slc / slc.max()
        ax.plot(R_axis, 20 * np.log10(slc + 1e-9), lw=1.2)
        ax.set_title(f"B = {B/1e6:.0f} MHz  (dR = {d2['dR']:.2f} m)")
        ax.set_xlabel("Range [m]")
        ax.set_ylabel("Normalized power [dB]")
        ax.axvline(cfg["R0"], color="r", ls="--", lw=0.8, label="true R0")
        ax.set_ylim(-40, 2)
        ax.legend(fontsize=7)
        ax.grid(alpha=0.3)
    fig.suptitle("Bandwidth sets range clarity (mainlobe narrows), position fixed at R0")
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------- #
# Figure 3 : radial velocity -> position error + range walk
# --------------------------------------------------------------------------- #
def fig_radial_velocity(cfg, d):
    t_m = slow_time(cfg, d)
    t_f, t0 = fast_time(cfg)
    vrs = [0.0, 1.0, 2.0]
    f_a, R_axis, x_axis, _, _, _ = axes(cfg, d)

    fig, axs = plt.subplots(1, 3, figsize=(14, 4.4))
    for ax, vr in zip(axs, vrs):
        R = slant_range(cfg, t_m, vr=vr)
        data = raw_echo(cfg, d, t_m, t_f, R)
        rc = range_compress(cfg, d, data)
        rd = range_doppler_map(rc)
        fd = 2.0 * vr / d["lam"]
        dx = vr * cfg["R0"] / cfg["vp"]
        im = ax.imshow(20 * np.log10(np.abs(rd) + 1e-6), aspect="auto",
                       extent=[R_axis[0], R_axis[-1], f_a[0], f_a[-1]],
                       origin="lower", cmap="inferno")
        ax.axhline(fd, color="c", ls="--", lw=0.8, label=f"$f_{{dc}}$=+{fd:.0f} Hz")
        ax.axhline(0, color="w", ls=":", lw=0.6)
        ax.set_title(f"$v_r$ = {vr:.0f} m/s  ($\\Delta x$ = {dx:.0f} m)")
        ax.set_xlabel("Range [m]")
        ax.set_ylabel("Doppler [Hz]")
        ax.legend(fontsize=7, loc="upper right")

    fig.suptitle(
        "Radial velocity shifts the Doppler centroid (position along Doppler) "
        "$f_{dc} = 2v_r/\\lambda$ and causes range walk $v_r T_a$; uncompensated "
        "it also displaces the target in azimuth by $\\Delta x = v_r R_0/v_p$")
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------- #
# Figure 4 : antenna length -> azimuth clarity
# --------------------------------------------------------------------------- #
def fig_antenna_length(cfg, d):
    t_f, t0 = fast_time(cfg)

    Las = [1.0, 2.0, 4.0]
    fig, axs = plt.subplots(1, 3, figsize=(13, 4))
    for ax, La in zip(axs, Las):
        c2 = dict(cfg); c2["La"] = La
        d2 = derive(c2)
        t_m = slow_time(c2, d2)
        R = slant_range(c2, t_m)
        data = raw_echo(c2, d2, t_m, t_f, R)
        rc = range_compress(c2, d2, data)
        ac = azimuth_compress(c2, d2, rc)
        _, _, x_axis, _, _, _ = axes(c2, d2)
        i = np.argmax(np.abs(ac).sum(axis=0))
        slc = np.abs(ac[:, i])
        slc = slc / slc.max()
        ax.plot(x_axis, 20 * np.log10(slc + 1e-9), lw=1.2)
        ax.set_title(f"$L_a$ = {La:.0f} m  ($\\rho_{{az}}$ = {d2['rho_az']:.1f} m, "
                     f"$B_d$ = {d2['Bd']:.0f} Hz)")
        ax.set_xlabel("Azimuth $x$ [m]")
        ax.set_ylabel("Normalized power [dB]")
        ax.axvline(0, color="r", ls="--", lw=0.8, label="true x0")
        ax.set_ylim(-40, 2)
        ax.legend(fontsize=7)
        ax.grid(alpha=0.3)
    fig.suptitle("Antenna length sets azimuth clarity ($\\rho_{az} = L_a/2$), position fixed")
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------- #
# Figure 5 : target along-track velocity -> azimuth defocus
# --------------------------------------------------------------------------- #
def fig_along_track(cfg, d):
    t_m = slow_time(cfg, d)
    t_f, t0 = fast_time(cfg)
    vts = [0.0, 40.0, 80.0]
    fig, axs = plt.subplots(1, 3, figsize=(13, 4))
    for ax, vt in zip(axs, vts):
        R = slant_range(cfg, t_m, vt=vt)
        data = raw_echo(cfg, d, t_m, t_f, R)
        rc = range_compress(cfg, d, data)
        ac = azimuth_compress(cfg, d, rc)          # nominal fR (mismatched for vt)
        _, _, x_axis, _, _, _ = axes(cfg, d)
        i = np.argmax(np.abs(ac).sum(axis=0))
        slc = np.abs(ac[:, i])
        slc = slc / slc.max()
        ax.plot(x_axis, 20 * np.log10(slc + 1e-9), lw=1.2)
        ax.set_title(f"target $v_t$ = {vt:.0f} m/s  (mismatch {vt:.0f} m/s)")
        ax.set_xlabel("Azimuth $x$ [m]")
        ax.set_ylabel("Normalized power [dB]")
        ax.axvline(0, color="r", ls="--", lw=0.8, label="true x0")
        ax.set_ylim(-40, 2)
        ax.legend(fontsize=7)
        ax.grid(alpha=0.3)
    fig.suptitle(
        "Target along-track velocity mismatches the azimuth filter -> defocus "
        "(clarity loss; position roughly fixed)")
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------- #
# Figure 6 : SNR and speckle
# --------------------------------------------------------------------------- #
def fig_snr_speckle(cfg, d):
    t_m = slow_time(cfg, d)
    t_f, t0 = fast_time(cfg)
    R = slant_range(cfg, t_m)
    rng = np.random.default_rng(0)

    snrs = [30.0, 10.0, 0.0]
    fig, axs = plt.subplots(2, 3, figsize=(14, 8))

    # --- thermal noise (AWGN) ---
    for ax, snr in zip(axs[0], snrs):
        data = raw_echo(cfg, d, t_m, t_f, R)
        A = 1.0
        sigma = A * 10 ** (-snr / 20.0)
        data = data + sigma * (rng.standard_normal(data.shape)
                               + 1j * rng.standard_normal(data.shape)) / np.sqrt(2)
        rc = range_compress(cfg, d, data)
        ac = azimuth_compress(cfg, d, rc)
        _, R_axis, x_axis, _, _, _ = axes(cfg, d)
        im = ax.imshow(20 * np.log10(np.abs(ac) + 1e-6), aspect="auto",
                       extent=[R_axis[0], R_axis[-1], x_axis[0], x_axis[-1]],
                       origin="lower", cmap="inferno")
        ax.set_title(f"thermal noise, SNR = {snr:.0f} dB")
        ax.set_xlabel("Range [m]")
        ax.set_ylabel("Azimuth [m]")

    # --- multiplicative speckle (Rayleigh amplitude) ---
    for ax, snr in zip(axs[1], snrs):
        data = raw_echo(cfg, d, t_m, t_f, R)
        rc = range_compress(cfg, d, data)
        ac = azimuth_compress(cfg, d, rc)
        # unit-mean complex Gaussian per pixel -> Rayleigh magnitude speckle
        speckle = (rng.standard_normal(ac.shape)
                   + 1j * rng.standard_normal(ac.shape)) / np.sqrt(2)
        ac = ac * speckle
        A = 1.0
        sigma = A * 10 ** (-snr / 20.0)
        ac = ac + sigma * (rng.standard_normal(ac.shape)
                           + 1j * rng.standard_normal(ac.shape)) / np.sqrt(2)
        _, R_axis, x_axis, _, _, _ = axes(cfg, d)
        im = ax.imshow(20 * np.log10(np.abs(ac) + 1e-6), aspect="auto",
                       extent=[R_axis[0], R_axis[-1], x_axis[0], x_axis[-1]],
                       origin="lower", cmap="inferno")
        ax.set_title(f"speckle + noise, SNR = {snr:.0f} dB")
        ax.set_xlabel("Range [m]")
        ax.set_ylabel("Azimuth [m]")

    fig.suptitle(
        "Noise raises the detection floor; speckle (Rayleigh) smears the point "
        "into grainy texture -> clarity/detectability loss")
    fig.tight_layout()
    return fig


def main():
    os.makedirs(OUT, exist_ok=True)
    cfg = make_cfg()
    d = derive(cfg)

    figs = {
        "01_baseline.png": fig_baseline(cfg, d),
        "02_bandwidth.png": fig_bandwidth(cfg, d),
        "03_radial_velocity.png": fig_radial_velocity(cfg, d),
        "04_antenna_length.png": fig_antenna_length(cfg, d),
        "05_along_track_velocity.png": fig_along_track(cfg, d),
        "06_snr_speckle.png": fig_snr_speckle(cfg, d),
    }
    for name, fig in figs.items():
        path = os.path.join(OUT, name)
        fig.savefig(path, dpi=130, bbox_inches="tight")
        plt.close(fig)
        print(f"wrote {path}")

    print("\nDerived radar parameters:")
    print(f"  lambda      = {d['lam']*100:.2f} cm")
    print(f"  dR          = {d['dR']:.2f} m  (range resolution = c*b_r/2B)")
    print(f"  rho_az      = {d['rho_az']:.2f} m  "
          f"(azimuth resolution = lam*R0*b_a/2L_syn)")
    print(f"  Bd          = {d['Bd']:.0f} Hz (Doppler bandwidth)")
    print(f"  Ta          = {d['Ta']:.2f} s  (synthetic aperture time)")


if __name__ == "__main__":
    main()
