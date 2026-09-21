"""Educational broadside stripmap SAR: ideal range compression + stationary
range-migration correction + coherent azimuth deramp/FFT image formation.
Paraxial, single point, rectangular spectrum/aperture, no noise or terrain.
Positive radial velocity approaches the radar. Axes are slant range and azimuth.
This is an idealized image former, NOT a complete raw-data Range-Doppler Algorithm.
"""
import numpy as np
C = 3e8
R0, V, WAVELENGTH, PRF = 5000., 150., .03, 1600.


def simulate(bandwidth_mhz=200., radial_velocity=0., antenna_length=2.,
             aperture_fraction=1., azimuth_window="Rectangular"):
    if not 20 <= bandwidth_mhz <= 500 or not .5 <= antenna_length <= 5 or abs(radial_velocity) > 5:
        raise ValueError('Supported domain: B=20–500 MHz, L=0.5–5 m, vr=-5–5 m/s')
    if not .25 <= aperture_fraction <= 1 or azimuth_window not in ("Rectangular", "Hann"):
        raise ValueError('Aperture fraction must be 0.25–1.0 and window Rectangular or Hann')
    dr = C / (2 * bandwidth_mhz * 1e6)
    duration = aperture_fraction * R0 * WAVELENGTH / (V * antenna_length)
    n = int(round(duration * PRF))
    t = (np.arange(n) - (n-1)/2) / PRF
    r = np.linspace(-15, 15, 601)  # range offset from R0; 5 cm display sampling
    rate = 2 * V**2 / (WAVELENGTH * R0)
    fd = 2 * radial_velocity / WAVELENGTH
    # After ideal stationary RCMC, moving-target residual range walk remains.
    envelope = np.sinc((r[None, :] + radial_velocity*t[:, None]) / dr)
    rc = envelope * np.exp(1j*(2*np.pi*fd*t - np.pi*rate*t*t))[:, None]
    rd = np.fft.fftshift(np.fft.fft(rc, axis=0), axes=0)
    doppler = np.fft.fftshift(np.fft.fftfreq(n, 1/PRF))
    # Cancel nominal quadratic phase; Fourier frequency maps to azimuth.
    # exp(+i 2pi fd t) focuses at x=fd*V/rate=vr*R0/V.
    weights = np.hanning(n) if azimuth_window == "Hann" else np.ones(n)
    deramped = rc * (weights * np.exp(1j*np.pi*rate*t*t))[:, None]
    nfft = max(8192, 2**int(np.ceil(np.log2(n))))
    focused = np.fft.fftshift(np.fft.fft(deramped, n=nfft, axis=0), axes=0) / weights.sum()
    x = np.fft.fftshift(np.fft.fftfreq(nfft, 1/PRF)) * V/rate
    keep = abs(x) <= 190
    focused, x = focused[keep], x[keep]
    peak = np.unravel_index(np.abs(focused).argmax(), focused.shape)
    width = half_power_width(x, np.abs(focused[:, peak[1]]))
    return dict(image=focused, rd=rd, r=r, x=x, doppler=doppler, t=t,
                dr=dr, da=V/(rate*(n/PRF)), duration=n/PRF, fd=fd,
                doppler_bw=rate*n/PRF, azimuth_width_3db=width,
                aperture_fraction=aperture_fraction, azimuth_window=azimuth_window, shift=radial_velocity*R0/V,
                walk=abs(radial_velocity)*n/PRF,
                peak_r=float(r[peak[1]]), peak_x=float(x[peak[0]]),
                peak_amplitude=float(np.abs(focused[peak])),
                range_profile=np.abs(focused[peak[0]]),
                azimuth_profile=np.abs(focused[:, peak[1]]))


def half_power_width(axis, amplitude):
    """Interpolated width of the contiguous main peak at half maximum power."""
    peak = int(np.argmax(amplitude))
    threshold = amplitude[peak] / np.sqrt(2)
    left = peak
    right = peak
    while left > 0 and amplitude[left] >= threshold:
        left -= 1
    while right < len(axis)-1 and amplitude[right] >= threshold:
        right += 1
    if left == 0 or right == len(axis)-1:
        return float('nan')
    lo = np.interp(threshold, amplitude[left:left+2], axis[left:left+2])
    hi = np.interp(threshold, amplitude[right-1:right+1][::-1], axis[right-1:right+1][::-1])
    return float(hi-lo)


def db(a, normalize=True):
    a = np.abs(a)
    if normalize:
        a = a / max(float(a.max()), 1e-15)
    return 20*np.log10(np.maximum(a, 1e-4))
