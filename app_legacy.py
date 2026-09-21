"""
Range-Doppler web app.

Run::

    .venv/bin/streamlit run app.py

Use the sidebar controls to toggle the radar variables and watch the
range-Doppler map and the compressed SAR image update live.
"""

import numpy as np
import streamlit as st
import plotly.graph_objects as go

import radar

st.set_page_config(page_title="Range-Doppler Explorer", layout="wide")

BASE = radar.make_cfg()
T_F, _ = radar.fast_time(BASE)
RNG = np.random.default_rng(0)

DB_MIN, DB_MAX = -60.0, 0.0


@st.cache_data
def get_base():
    cfg = radar.make_cfg()
    t_f, _ = radar.fast_time(cfg)
    return cfg, t_f


# --------------------------------------------------------------------------- #
# Sidebar controls
# --------------------------------------------------------------------------- #
st.sidebar.title("Radar variables")

B_mhz = st.sidebar.slider("Bandwidth B [MHz]", 20.0, 500.0, 200.0, 5.0)
vr = st.sidebar.slider("Radial velocity $v_r$ [m/s]", -5.0, 5.0, 0.0, 0.1)
La = st.sidebar.slider("Antenna length $L_a$ [m]", 0.5, 5.0, 2.0, 0.1)
vt = st.sidebar.slider("Target along-track velocity $v_t$ [m/s]", 0.0, 80.0, 0.0, 1.0)
snr = st.sidebar.slider("SNR [dB]", -10.0, 40.0, 30.0, 1.0)
speckle = st.sidebar.checkbox("Multiplicative speckle (Rayleigh)", value=False)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Range resolution $dR = c/2B$  \n"
    "Azimuth resolution $\\rho_{az} = L_a/2$  \n"
    "Doppler centroid $f_{dc} = 2v_r/\\lambda$"
)

# --------------------------------------------------------------------------- #
# Simulation
# --------------------------------------------------------------------------- #
cfg, t_f = get_base()
rd_disp, im_disp, meta = radar.simulate(
    cfg, t_f, B_mhz * 1e6, vr, La, vt, snr, speckle, RNG
)

# downsample for a responsive browser (max-pooling preserves the peak)
rd_ds, _, _ = radar.downsample2d(rd_disp, 512, 700)
im_ds, _, _ = radar.downsample2d(im_disp, 512, 700)

Ra = meta["R_axis"]; xa = meta["x_axis"]; fa = meta["f_a"]

# --------------------------------------------------------------------------- #
# Header + metrics
# --------------------------------------------------------------------------- #
st.title("Range–Doppler / azimuth explorer")
st.caption(
    "Point-target SAR simulation through the Range-Doppler Algorithm. "
    "Left: range-Doppler map (after range compression + azimuth FFT). "
    "Right: fully compressed image (range x azimuth)."
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Range res. $dR$", f"{meta['dR']:.2f} m")
c2.metric("Azimuth res. $\\rho_{az}$", f"{meta['rho_az']:.2f} m")
c3.metric("Doppler centroid $f_{dc}$", f"{meta['fd']:+.0f} Hz")
c4.metric("Doppler bw $B_d$", f"{meta['Bd']:.0f} Hz")

# --------------------------------------------------------------------------- #
# Plots
# --------------------------------------------------------------------------- #
def heatmap(z, x, y, title, xlabel, ylabel, hline=None):
    fig = go.Figure(go.Heatmap(
        z=z, x=x, y=y, zmin=DB_MIN, zmax=DB_MAX,
        colorscale="Inferno", colorbar=dict(title="dB"),
    ))
    fig.update_layout(
        title=title, xaxis_title=xlabel, yaxis_title=ylabel,
        height=520, margin=dict(l=60, r=20, t=60, b=50),
    )
    if hline is not None:
        fig.add_hline(y=hline, line=dict(color="cyan", dash="dash", width=1))
    fig.add_hline(y=0, line=dict(color="white", dash="dot", width=1))
    return fig


colL, colR = st.columns(2)
with colL:
    st.plotly_chart(
        heatmap(rd_ds, Ra, fa, "Range-Doppler map", "Range [m]",
                "Doppler frequency [Hz]", hline=meta["fd"]),
        use_container_width=True,
    )
with colR:
    st.plotly_chart(
        heatmap(im_ds, Ra, xa, "Compressed image (range x azimuth)",
                "Range [m]", "Azimuth [m]"),
        use_container_width=True,
    )

st.caption(
    f"Aperture time $T_a$ = {meta['Ta']:.2f} s, slow-time samples $N_a$ = "
    f"{meta['Na']}, range samples $N_r$ = {meta['Nr']}, "
    f"$\\lambda$ = {meta['lam']*100:.2f} cm."
)
