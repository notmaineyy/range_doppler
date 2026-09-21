"""Generate the three controlled experiments: .venv/bin/python sar_assignment.py"""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import sar_model as sar
OUT=Path(__file__).parent/'outputs'/'sar_assignment'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    measurements=[]
    cases=[('bandwidth',[20,100,500]),('radial_velocity',[-3,0,3]),('antenna_length',[.5,2,5])]
    for variable,values in cases:
        fig,axes=plt.subplots(2,3,figsize=(14,8),layout='constrained')
        for col,value in enumerate(values):
            params=dict(bandwidth_mhz=200.,radial_velocity=0.,antenna_length=2.)
            params['bandwidth_mhz' if variable=='bandwidth' else variable]=value
            s=sar.simulate(**params)
            measurements.append(dict(variable=variable,value=value,**{k:s[k] for k in ['dr','da','shift','walk','peak_r','peak_x','peak_amplitude']}))
            ax=axes[0,col]
            ylim=115 if variable=='radial_velocity' else 6
            keep=abs(s['x'])<=ylim
            im=ax.pcolormesh(s['r'],s['x'][keep],sar.db(s['image'],False)[keep],cmap='inferno',vmin=-40,vmax=0,shading='auto',rasterized=True)
            ax.plot(0,0,'+',color='cyan',ms=11,label='True at t=0')
            ax.plot(0,s['shift'],'o',mfc='none',mec='lime',ms=9,label='Predicted apparent')
            unit={'bandwidth':'MHz','radial_velocity':'m/s','antenna_length':'m'}[variable]
            ax.set(title=f'{value:g} {unit} | range {s["dr"]:.2f} m, azimuth {s["da"]:.2f} m',xlabel='Slant-range offset from 5000 m [m]',ylabel='Azimuth [m]')
            ax.legend(fontsize=8,loc='upper right')
            ax=axes[1,col]
            if variable=='bandwidth':
                ax.plot(s['r'],sar.db(s['range_profile'],False)); ax.set_xlabel('Slant-range offset [m]')
            else:
                ax.plot(s['x'],sar.db(s['azimuth_profile'],False))
                ax.set_xlim(s['shift']-7,s['shift']+7); ax.set_xlabel('Azimuth [m]')
            ax.set_ylim(-40,1); ax.grid(alpha=.25); ax.set_ylabel('Response [dB]')
            ax.set_title(f'Measured peak: r offset {s["peak_r"]:+.2f} m, x {s["peak_x"]:+.2f} m',fontsize=10)
        fig.colorbar(im,ax=list(axes[0]),label='dB relative to stationary peak',shrink=.8)
        titles={'bandwidth':'Bandwidth sharpens the range response; target position stays fixed', 'radial_velocity':'Radial motion creates azimuth position error and residual range walk', 'antenna_length':'Full-aperture stripmap SAR: shorter antenna gives finer azimuth resolution'}
        fig.suptitle(titles[variable],fontsize=15)
        fig.savefig(OUT/f'{variable}.png',dpi=150)
        plt.close(fig)
    (OUT/'measurements.json').write_text(json.dumps(measurements,indent=2))
    print(json.dumps(measurements,indent=2))

if __name__=='__main__':main()
