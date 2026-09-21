"""Run: .venv/bin/streamlit run app.py"""
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import sar_model as sar
st.set_page_config(page_title='SAR image laboratory', layout='wide')
st.title('SAR image laboratory')
st.write('Range locates echoes across the flight track. Doppler history is coherently focused into azimuth position along the flight track. The output is a spatial image.')
B = st.sidebar.number_input('Bandwidth [MHz]', min_value=20., max_value=500., value=200., step=5., format='%.1f')
vr = st.sidebar.number_input('Target radial velocity [m/s]', min_value=-5., max_value=5., value=0., step=.1, format='%.2f')
L = st.sidebar.number_input('Along-track antenna length [m]', min_value=.5, max_value=5., value=2., step=.1, format='%.2f')
fraction = st.sidebar.number_input('Processed aperture [%]', min_value=25., max_value=100., value=100., step=5., format='%.1f')
window = st.sidebar.selectbox('Azimuth weighting', ['Rectangular', 'Hann'])
st.sidebar.caption('Type any value within the bounds, or use the −/+ step buttons. Aperture percentage selects the central part of the available illumination time.')
st.sidebar.caption('Positive velocity = approaching. Platform: 150 m/s. Centre slant range: 5 km. Wavelength: 3 cm. Broadside stripmap SAR.')
@st.cache_data(max_entries=8)
def run(b,v,l,f,w):
    return sar.simulate(b,v,l,f/100,w)
s = run(B,vr,L,fraction,window)
cols=st.columns(4)
for col,label,value in zip(cols,['Range resolution','Rectangular azimuth reference','Predicted azimuth displacement','Range walk during aperture'],[f"{s['dr']:.2f} m",f"{s['da']:.2f} m",f"{s['shift']:+.2f} m",f"{s['walk']:.2f} m"]):
    col.metric(label,value)
st.caption(f"Resolution references are ideal first-null separations for rectangular weighting. Measured azimuth −3 dB width: {s['azimuth_width_3db']:.2f} m. Hann weighting broadens the mainlobe while reducing sidelobes.")
a,b=st.columns([1,1.3])
with a:
    z=sar.db(s['rd']).T  # transpose -> (range, Doppler)
    # Decimate data AND coordinate arrays together for the intermediate view.
    stride=max(1,int(np.ceil(len(s['doppler'])/600)))
    fig=go.Figure(go.Heatmap(z=z[:,::stride],x=s['doppler'][::stride],y=s['range'],zmin=-40,zmax=0,colorscale='Inferno',colorbar=dict(title='dB')))
    fig.add_vline(x=s['fd'],line_color='cyan',line_dash='dash')
    fig.update_layout(title='Intermediate range–Doppler domain',xaxis_title='Relative Doppler frequency of scene [Hz]',yaxis_title='Slant range [m]',height=510)
    st.plotly_chart(fig,use_container_width=True, theme=None)
with b:
    zoom=st.checkbox('Zoom to target response',value=True)
    selection=(abs(s['x']-s['shift']) < max(8,4*L)) if zoom else np.ones(len(s['x']),dtype=bool)
    z=sar.db(s['image'],False).T  # transpose -> (range, azimuth)
    fig=go.Figure(go.Heatmap(z=z[:,selection],x=s['x'][selection],y=s['range'],zmin=-40,zmax=0,colorscale='Inferno',colorbar=dict(title='dB')))
    fig.add_trace(go.Scatter(x=[0],y=[5000],mode='markers',marker=dict(symbol='cross',color='cyan',size=12),name='True position at aperture centre'))
    fig.add_trace(go.Scatter(x=[s['shift']],y=[5000],mode='markers',marker=dict(symbol='circle-open',color='lime',size=14),name='Predicted apparent position'))
    fig.update_layout(title='Focused SAR image',xaxis_title='Azimuth along flight track [m]',yaxis_title='Slant range [m]',height=510,legend=dict(orientation='h',y=1.12))
    st.plotly_chart(fig,use_container_width=True, theme=None)
    st.caption(f"Measured brightest pixel: range {sar.R0+s['peak_r']:.2f} m, azimuth {s['peak_x']:+.2f} m. True centre-time location: (5000 m, 0 m). Disable zoom to see both positions when moving.")
c,d=st.columns(2)
for col,axis,key,label in [(c,s['range'],'range_profile','Slant range [m]'),(d,s['x'],'azimuth_profile','Azimuth [m]')]:
    with col:
        f=go.Figure(go.Scatter(x=axis,y=sar.db(s[key],False)))
        f.update_layout(xaxis_title=label,yaxis_title='Response relative to stationary peak [dB]',height=280,yaxis_range=[-40,1])
        if key=='azimuth_profile': f.update_xaxes(range=[s['shift']-10,s['shift']+10])
        st.plotly_chart(f,use_container_width=True, theme=None)
st.markdown(r'''
**What to demonstrate**
- **Bandwidth:** compare 20 and 500 MHz with velocity zero. $\delta R=c/(2B)$ improves from 7.5 m to 0.30 m. The true position stays fixed.
- **Radial velocity:** compare −3, 0 and +3 m/s. $f_c=2v_r/\lambda$ shifts the response to $\Delta x=v_rR_0/V$: −100, 0 and +100 m. Range walk can spread the energy and reduce the peak.
- **Antenna length:** at 100% aperture with rectangular weighting, compare 0.5 and 5 m with velocity zero. In full-aperture stripmap SAR, $\delta x\approx L_a/2$: 0.25 versus 2.5 m. A shorter antenna sees the target longer and supplies a wider Doppler history.

- **Processed aperture:** compare 100%, 50% and 25%. Less coherent observation broadens the azimuth response. With $L_a=2$ m the rectangular reference changes from 1 to 2 to 4 m. Shorter observation also reduces moving-target range walk.
- **Azimuth weighting:** compare Rectangular and Hann at zero velocity. Hann suppresses sidelobes, with a wider mainlobe. The model normalizes the weights so a stationary peak remains at 0 dB. Noise penalties are outside this model.

Changing bandwidth or antenna length changes resolution, not the target's true position. Velocity physically changes range over time; its azimuth displacement is a positioning error from processing the moving target as stationary.
''')
with st.expander('Signal model, assumptions and limits'):
    st.latex(r'R(t)\simeq R_0-v_rt+V^2t^2/(2R_0),\quad K_a=2V^2/(\lambda R_0)')
    st.latex(r's(r,t)=\mathrm{sinc}((r+v_rt)/\delta R)\exp(j2\pi f_ct-j\pi K_at^2)')
    st.write('Ideal range compression and stationary range-migration correction are assumed. A deramp and slow-time FFT form the image. This is a paraxial point-target model, not a raw-data RDA processor. Rectangular processing gives sinc sidelobes. Hann applies a taper to the azimuth processing weights. Processed aperture selects the central fraction of the beam-limited dwell. All images share the stationary unit-amplitude reference; the intermediate map is separately normalized. No terrain, antenna-gain/SNR tradeoff, or speckle is simulated. Slant range is not ground range; at incidence angle θ, ground-range resolution is δR/sin θ. The La/2 result assumes broadside stripmap with the full beam-limited aperture, not fixed-aperture spotlight SAR.')
    st.write(f"Measured azimuth −3 dB width {s['azimuth_width_3db']:.3f} m. Aperture {s['duration']:.3f} s; Doppler centroid {s['fd']:+.1f} Hz; bandwidth {s['doppler_bw']:.1f} Hz; PRF {sar.PRF:.0f} Hz. Zero-padding interpolates the image; it does not improve resolution.")
    st.markdown('[ESA: SAR image formation](https://www.esa.int/Enabling_Support/Space_Engineering_Technology/Onboard_Data_Processing/Introduction_to_a_SAR_System)')
