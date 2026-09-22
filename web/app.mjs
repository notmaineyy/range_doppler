const specs=[['B','Bandwidth [MHz]',20,500,150,5,1],['vr','Aircraft radial velocity [m/s]',-38.82,38.82,0,.1,2],['L','Physical antenna length [m]',.5,5,2,.1,2],['aperture','Processed aperture [%]',25,100,100,5,1],['squint','Squint from broadside [°]',-15,15,0,1,1]];
const state={B:150,vr:0,L:2,aperture:100,window:'Rectangular',squint:0};
const controls=document.querySelector('#controls');let result=null,requested=0,timer,busy=false,queued=false,paintPending=false;
for(const [key,label,min,max,value,step,digits] of specs){
 const div=document.createElement('div');div.className='control';
 div.innerHTML=`<label for="${key}-number">${label}</label><div class="entry"><input id="${key}-number" type="number" min="${min}" max="${max}" step="any" value="${value.toFixed(digits)}"><div class="steps"><button type="button" aria-label="Increase ${label}">▲</button><button type="button" aria-label="Decrease ${label}">▼</button></div></div><input id="${key}-slider" aria-label="${label} slider" type="range" min="${min}" max="${max}" step="any" value="${value}"><div class="limits"><span>${min}</span><span>${max}</span></div>`;
 controls.append(div);const number=div.querySelector('input[type=number]'),slider=div.querySelector('input[type=range]'),buttons=div.querySelectorAll('button');
 function sync(v,format=false){v=+v.toFixed(digits);state[key]=v;slider.value=v;if(key==='vr'||key==='squint'){const other=key==='vr'?'squint':'vr',linked=key==='vr'?Math.asin(v/150)*180/Math.PI:150*Math.sin(v*Math.PI/180);state[other]=linked;const field=document.querySelector(`#${other}-number`),range=document.querySelector(`#${other}-slider`);if(field){field.value=linked.toFixed(other==='vr'?2:1);range.value=linked;const bs=field.parentElement.querySelectorAll('button');bs[0].disabled=linked>=Number(field.max);bs[1].disabled=linked<=Number(field.min);}}if(format)number.value=v.toFixed(digits);buttons[0].disabled=v>=max;buttons[1].disabled=v<=min;schedule();}
 slider.addEventListener('input',()=>{number.value=Number(slider.value).toFixed(digits);sync(Number(slider.value));});
 number.addEventListener('input',()=>{const v=number.valueAsNumber;if(Number.isFinite(v)&&v>=min&&v<=max){number.setCustomValidity('');sync(v);}else number.setCustomValidity(`Enter a value from ${min} to ${max}.`);});
 number.addEventListener('change',()=>{if(!number.validity.valid){number.value=state[key].toFixed(digits);number.setCustomValidity('');}else sync(number.valueAsNumber,true);});
 number.addEventListener('keydown',e=>{if(e.key==='ArrowUp'||e.key==='ArrowDown'){e.preventDefault();sync(Math.max(min,Math.min(max,+(state[key]+(e.key==='ArrowUp'?step:-step)).toFixed(digits))),true);}if(e.key==='Enter')number.blur();});
 buttons[0].onclick=()=>sync(Math.min(max,+(state[key]+step).toFixed(digits)),true);
 buttons[1].onclick=()=>sync(Math.max(min,+(state[key]-step).toFixed(digits)),true);
 buttons[0].disabled=value>=max;buttons[1].disabled=value<=min;
}
const worker=new Worker('./worker.mjs',{type:'module'});
function dispatch(){timer=null;if(busy){queued=true;return;}busy=true;queued=false;worker.postMessage({id:++requested,params:{...state}});}
function schedule(){document.querySelector('#status').textContent=result?'Updating…':'Computing…';if(!timer)timer=setTimeout(dispatch,25);}
worker.onmessage=({data})=>{if(data.id!==requested)return;busy=false;if(data.error){document.querySelector('#error').textContent=data.error;document.querySelector('#status').textContent='Invalid parameters';if(queued)dispatch();return;}result=data.result;document.querySelector('#error').textContent='';document.querySelector('#status').textContent=`Updated in ${Math.round(data.ms)} ms`;updateMetrics();paint();if(queued){document.querySelector('#status').textContent='Updating…';dispatch();}};
worker.onerror=()=>{document.querySelector('#error').textContent='The background calculation could not start. Serve this page using python server.py.';};
document.querySelector('#window').onchange=e=>{state.window=e.target.value;schedule();};

document.querySelector('#display').onchange=()=>paint();
document.querySelector('#reset').onclick=()=>{for(const [key,,min,max,value,,digits] of specs){state[key]=value;document.querySelector(`#${key}-number`).value=value.toFixed(digits);document.querySelector(`#${key}-slider`).value=value;const btns=document.querySelector(`#${key}-number`).parentElement.querySelectorAll('button');btns[0].disabled=value>=max;btns[1].disabled=value<=min;}state.window='Rectangular';document.querySelector('#window').value=state.window;document.querySelector('#display').value='Log power (dB)';schedule();};
function updateMetrics(){const s=result;
 document.querySelector('#window-comparison').textContent=s.params.window!=='Rectangular'?'Cyan: '+s.params.window+'-weighted image response. Dashed grey: no-windowing reference at the same geometry and aperture. Both have unit peak, so compare sidelobe heights and mainlobe widths directly.':'Cyan: no windowing (uniform pulse weights / rectangular aperture). Select Hann or Hamming to overlay its response on a dashed no-windowing reference. A finite aperture still produces sidelobes without a taper.';

 document.querySelector('#azimuth-values').textContent=`Slice at slant range ${s.peakR.toFixed(2)} m · Measured full half-power width: ${s.width===null?'unavailable':s.width.toFixed(2)+' m'} · Physical antenna: ${s.params.L.toFixed(2)} m · Processed synthetic aperture: ${s.syntheticLength.toFixed(1)} m. First-null reference: ${s.da.toFixed(2)} m (Rectangular); this is a different width definition.`;
for(const key of ['dr','da','shift','walk'])document.querySelector('#'+key).textContent=(key==='shift'&&s[key]>=0?'+':'')+s[key].toFixed(2)+' m';document.querySelector('#width').textContent=`Measured azimuth −3 dB width: ${s.width===null?'not measurable':s.width.toFixed(2)+' m'} · Weighting broadening β = ${s.broadening.toFixed(3)}× · Stationary prediction: ${s.nominalWidth.toFixed(2)} m`;
 document.querySelector('#peak').textContent=`Brightest pixel: range ${s.peakR.toFixed(2)} m, azimuth ${s.peakX.toFixed(2)} m. True centre-time position: (5000 m, 0 m). Fixed close-up: azimuth −5…+5 m, range 4995…5005 m; 1 m × 1 m grid. Stationary target; aircraft trajectory compensated.`;
 document.querySelector('#sampling').textContent=`Dwell: ${s.T.toFixed(3)} s · Synthetic aperture: ${s.syntheticLength.toFixed(1)} m · Physical antenna: ${s.params.L.toFixed(2)} m · Aircraft Doppler centroid removed: ${s.platformCentroid.toFixed(1)} Hz · Residual centroid: ${s.fd.toFixed(1)} Hz · Nominal Doppler span: ${s.Bd.toFixed(1)} Hz.`;
 document.querySelector('#diagnostic').textContent=`The target is stationary. Aircraft radial velocity is ${s.aircraftRadialVelocity.toFixed(2)} m/s at aperture centre. Ideal trajectory compensation removes aircraft-induced range migration and centroid phase; changing it does not create a target-motion shift. β compares this window’s stationary full −3 dB width with Rectangular at the same dwell. It does not include motion defocus.`;

}
function setup(id){const canvas=document.querySelector('#'+id),w=canvas.clientWidth,h=canvas.clientHeight,ratio=window.devicePixelRatio||1;canvas.width=Math.round(w*ratio);canvas.height=Math.round(h*ratio);const c=canvas.getContext('2d');c.scale(ratio,ratio);c.fillStyle='#10151b';c.fillRect(0,0,w,h);c.font='12px system-ui';const square=id==='image',side=Math.min(w-111,h-72);return {c,w,h,left:62,top:18,pw:square?side:w-111,ph:square?side:h-72};}
const palette=[[0,0,4],[40,11,84],[101,21,110],[159,42,99],[212,72,66],[245,125,21],[250,193,39],[252,255,164]];
const lut=Array.from({length:256},(_,k)=>{const t=k/255*(palette.length-1),i=Math.min(palette.length-2,Math.floor(t)),f=t-i;return palette[i].map((v,j)=>Math.round(v*(1-f)+palette[i+1][j]*f));});
function axes(o,xmin,xmax,ymin,ymax,xlabel,ylabel){const {c,left,top,pw,ph}=o;c.strokeStyle='#607281';c.lineWidth=1;c.strokeRect(left,top,pw,ph);c.fillStyle='#b2c4d0';c.textAlign='center';
 const ticks=xmax-xmin===10&&ymax-ymin===10?[.1,.3,.5,.7,.9]:[0,.25,.5,.75,1];
 for(const t of ticks){const x=xmin+(xmax-xmin)*t,y=ymin+(ymax-ymin)*t;c.fillText(Math.abs(x)<.001?'0':x.toFixed(Math.abs(xmax-xmin)<20?1:0),left+pw*t,top+ph+20);c.textAlign='right';c.fillText(Math.abs(y)<.001?'0':y.toFixed(Math.abs(ymax-ymin)<20?1:0),left-8,top+ph-ph*t+4);c.textAlign='center';}
 c.fillText(xlabel,left+pw/2,top+ph+46);c.save();c.translate(16,top+ph/2);c.rotate(-Math.PI/2);c.fillText(ylabel,0,0);c.restore();}
function transpose(z,cols,rows){const t=new Float32Array(cols*rows);for(let y=0;y<rows;y++)for(let x=0;x<cols;x++)t[x*rows+y]=z[y*cols+x];return t;}
function heat(id,z,cols,rows,xmin,xmax,xlabel,ymin,ymax,ylabel){const o=setup(id),{c,left,top,pw,ph}=o;
 const linear=id!=='rd'&&document.querySelector('#display').value==='Linear power';
 const cw=Math.min(cols,Math.max(1,Math.round(pw))),ch=Math.min(rows,Math.max(1,Math.round(ph)));
 const buffer=document.createElement('canvas');buffer.width=cw;buffer.height=ch;const bc=buffer.getContext('2d'),pixels=bc.createImageData(cw,ch);
 for(let y=0;y<ch;y++)for(let x=0;x<cw;x++){
  let value=-80;
  for(let yy=Math.floor(y*rows/ch);yy<Math.ceil((y+1)*rows/ch);yy++)for(let xx=Math.floor(x*cols/cw);xx<Math.ceil((x+1)*cols/cw);xx++)value=Math.max(value,z[yy*cols+xx]);
  const level=linear?Math.pow(10,value/10):(value+40)/40;
  const color=lut[Math.max(0,Math.min(255,Math.round(level*255)))],j=((ch-1-y)*cw+x)*4;
  pixels.data[j]=color[0];pixels.data[j+1]=color[1];pixels.data[j+2]=color[2];pixels.data[j+3]=255;
 }
 bc.putImageData(pixels,0,0);c.imageSmoothingEnabled=true;c.drawImage(buffer,left,top,pw,ph);axes(o,xmin,xmax,ymin,ymax,xlabel,ylabel);
 for(let j=0;j<256;j++){const [r,g,b]=lut[255-j];c.fillStyle=`rgb(${r},${g},${b})`;c.fillRect(left+pw+12,top+ph*j/256,10,ph/256+1);}c.fillStyle='#b2c4d0';c.textAlign='left';c.fillText(linear?'1':'0',left+pw+25,top+5);c.fillText(linear?'0':'−40',left+pw+23,top+ph);c.fillText(linear?'Power':'dB',left+pw+8,top-6);
 const xPos=v=>left+pw*(v-xmin)/(xmax-xmin),yPos=v=>top+ph*(ymax-v)/(ymax-ymin);
 c.save();c.beginPath();c.rect(left,top,pw,ph);c.clip();
 if(id==='image'){
  c.strokeStyle='rgba(210,230,245,.32)';c.lineWidth=.7;c.beginPath();
  for(let x=Math.ceil(xmin);x<=xmax;x++){c.moveTo(xPos(x),top);c.lineTo(xPos(x),top+ph);}
  for(let y=Math.ceil(ymin);y<=ymax;y++){c.moveTo(left,yPos(y));c.lineTo(left+pw,yPos(y));}c.stroke();
 }
 c.strokeStyle='#52ebed';c.lineWidth=1.5;
 if(id==='rd'){c.setLineDash([5,4]);c.beginPath();c.moveTo(xPos(result.fd),top);c.lineTo(xPos(result.fd),top+ph);c.stroke();}
 else{const centre=id==='detail'?result.shift:0;const x=xPos(-centre),y=yPos(5000),xp=xPos(result.shift-centre);c.beginPath();c.moveTo(x-7,y);c.lineTo(x+7,y);c.moveTo(x,y-7);c.lineTo(x,y+7);c.stroke();c.strokeStyle='#a9f76a';c.beginPath();c.arc(xp,y,id==='image'?3:8,0,2*Math.PI);c.stroke();}
 c.restore();}
function line(id,xx,yy,xmin,xmax,label){const o=setup(id),{c,left,top,pw,ph}=o;axes(o,xmin,xmax,-60,0,label,'Response [dB]');c.save();c.beginPath();c.rect(left,top,pw,ph);c.clip();c.strokeStyle='#293c4a';
 for(let k=1;k<4;k++){c.beginPath();c.moveTo(left,top+ph*k/4);c.lineTo(left+pw,top+ph*k/4);c.stroke();}if(id==='azimuthProfile'&&result.params.window!=='Rectangular'){
 // Exact finite uniform-aperture response at the same dwell, before display interpolation.
 const n=Math.round(result.T*1600),sinc=v=>Math.abs(v)<1e-12?1:Math.sin(Math.PI*v)/(Math.PI*v);
 c.strokeStyle='#a9b6c3';c.lineWidth=1.3;c.setLineDash([5,4]);c.beginPath();
 for(let i=0;i<xx.length;i++){
  const f=xx[i]*result.rate/150,amplitude=Math.abs(sinc(n*f/1600)/sinc(f/1600));
  const db=20*Math.log10(Math.max(amplitude,1e-4)),x=left+(xx[i]-xmin)/(xmax-xmin)*pw,y=top-db/60*ph;
  i?c.lineTo(x,y):c.moveTo(x,y);
 }c.stroke();c.setLineDash([]);
 }
 if(id==='azimuthProfile'&&result.width!==null){
 const cx=left+(result.peakX-result.shift-xmin)/(xmax-xmin)*pw,half=result.width/2/(xmax-xmin)*pw;
 const level=20*Math.log10(result.peak)-10*Math.log10(2),y=top-level/60*ph;
 c.fillStyle='rgba(120,217,218,.13)';c.fillRect(cx-half,top,2*half,ph);
 c.strokeStyle='#edca75';c.setLineDash([4,4]);c.beginPath();c.moveTo(left,y);c.lineTo(left+pw,y);c.stroke();c.setLineDash([]);
 c.beginPath();c.moveTo(cx-half,y+5);c.lineTo(cx-half,y-5);c.moveTo(cx-half,y);c.lineTo(cx+half,y);c.moveTo(cx+half,y-5);c.lineTo(cx+half,y+5);c.stroke();
 c.fillStyle='#edca75';c.textAlign='left';c.fillText(`Half power · width ${result.width.toFixed(2)} m`,left+5,top+ph-9);
 }c.strokeStyle='#78d9da';c.lineWidth=1.8;c.beginPath();for(let i=0;i<xx.length;i++){const x=left+(xx[i]-xmin)/(xmax-xmin)*pw,y=top-yy[i]/60*ph;i?c.lineTo(x,y):c.moveTo(x,y);}c.stroke();c.restore();}
function paint(){if(paintPending)return;paintPending=true;requestAnimationFrame(()=>{
 paintPending=false;if(!result)return;const s=result,r0=s.rAxis[0],r1=s.rAxis[s.cols-1];
 heat('rd',transpose(s.rd,s.dcols,s.drows),s.drows,s.dcols,-800,800,'Doppler relative to squint centroid [Hz]',r0,r1,'Slant range [m]');
 // Fixed 10 m square close-up, sampled at the existing 0.1 m display interval.
 const zoom=new Float32Array(101*101);
 for(let a=0;a<=100;a++)for(let r=0;r<=100;r++)zoom[r*101+a]=s.image[(2150+a)*s.cols+100+r];
 heat('image',zoom,101,101,-5,5,'Azimuth [m] · 1 m grid',4995,5005,'Slant range [m]');
 line('rangeProfile',s.rAxis,s.rp,r0,r1,'Slant range [m]');
 const relative=Float32Array.from(s.xAxis,x=>x-s.shift);
 line('azimuthProfile',relative,s.ap,-10,10,'Azimuth offset from predicted peak [m]');
 heat('detail',transpose(s.image,s.cols,s.rows),s.rows,s.cols,-220,220,'Azimuth along flight track [m]',r0,r1,'Slant range [m]');
 });}

new ResizeObserver(()=>paint()).observe(document.querySelector('main'));
schedule();
