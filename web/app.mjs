const specs=[['B','Bandwidth [MHz]',20,500,200,5,1],['vr','Target radial velocity [m/s]',-5,5,0,.1,2],['L','Along-track antenna length [m]',.5,5,2,.1,2],['aperture','Processed aperture [%]',25,100,100,5,1]];
const state={B:200,vr:0,L:2,aperture:100,window:'Rectangular',full:false};
const controls=document.querySelector('#controls');let result=null,requested=0,timer,busy=false,queued=false,paintPending=false;
for(const [key,label,min,max,value,step,digits] of specs){
 const div=document.createElement('div');div.className='control';
 div.innerHTML=`<label for="${key}-number">${label}</label><div class="entry"><input id="${key}-number" type="number" min="${min}" max="${max}" step="any" value="${value.toFixed(digits)}"><div class="steps"><button type="button" aria-label="Increase ${label}">▲</button><button type="button" aria-label="Decrease ${label}">▼</button></div></div><input id="${key}-slider" aria-label="${label} slider" type="range" min="${min}" max="${max}" step="any" value="${value}"><div class="limits"><span>${min}</span><span>${max}</span></div>`;
 controls.append(div);const number=div.querySelector('input[type=number]'),slider=div.querySelector('input[type=range]'),buttons=div.querySelectorAll('button');
 function sync(v,format=false){v=+v.toFixed(digits);state[key]=v;slider.value=v;if(format)number.value=v.toFixed(digits);buttons[0].disabled=v>=max;buttons[1].disabled=v<=min;schedule();}
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
worker.onmessage=({data})=>{if(data.id!==requested)return;busy=false;if(data.error){document.querySelector('#error').textContent=data.error;return;}result=data.result;document.querySelector('#error').textContent='';document.querySelector('#status').textContent=`Updated in ${Math.round(data.ms)} ms`;updateMetrics();paint();if(queued){document.querySelector('#status').textContent='Updating…';dispatch();}};
worker.onerror=()=>{document.querySelector('#error').textContent='The background calculation could not start. Serve this page using python server.py.';};
document.querySelector('#window').onchange=e=>{state.window=e.target.value;schedule();};
document.querySelector('#full').onchange=e=>{state.full=e.target.checked;schedule();};
document.querySelector('#reset').onclick=()=>{for(const [key,,min,max,value,,digits] of specs){state[key]=value;document.querySelector(`#${key}-number`).value=value.toFixed(digits);document.querySelector(`#${key}-slider`).value=value;const btns=document.querySelector(`#${key}-number`).parentElement.querySelectorAll('button');btns[0].disabled=value>=max;btns[1].disabled=value<=min;}state.window='Rectangular';state.full=false;document.querySelector('#window').value=state.window;document.querySelector('#full').checked=false;schedule();};
function updateMetrics(){const s=result;for(const key of ['dr','da','shift','walk'])document.querySelector('#'+key).textContent=(key==='shift'&&s[key]>=0?'+':'')+s[key].toFixed(2)+' m';document.querySelector('#width').textContent=`Measured azimuth −3 dB width: ${s.width.toFixed(2)} m · ${s.params.window} weighting`;
 document.querySelector('#peak').textContent=`Brightest pixel: range ${s.peakR.toFixed(2)} m, azimuth ${s.peakX.toFixed(2)} m. True centre-time position: (5000 m, 0 m).`+(Math.abs(s.shift)>Math.max(8,4*s.da)&&!s.params.full?' Enable full position range to see the true marker.':'');
 document.querySelector('#sampling').textContent=`Processed dwell: ${s.T.toFixed(3)} s · Doppler centroid: ${s.fd.toFixed(1)} Hz · Nominal Doppler span: ${s.Bd.toFixed(1)} Hz · Image/profiles: dB relative to stationary peak. Display interpolation does not add resolution.`;
}
function setup(id){const canvas=document.querySelector('#'+id),w=canvas.clientWidth,h=canvas.clientHeight,ratio=window.devicePixelRatio||1;canvas.width=Math.round(w*ratio);canvas.height=Math.round(h*ratio);const c=canvas.getContext('2d');c.scale(ratio,ratio);c.fillStyle='#10151b';c.fillRect(0,0,w,h);c.font='12px system-ui';return {c,w,h,left:62,top:18,pw:w-111,ph:h-72};}
const palette=[[0,0,4],[40,11,84],[101,21,110],[159,42,99],[212,72,66],[245,125,21],[250,193,39],[252,255,164]];
const lut=Array.from({length:256},(_,k)=>{const t=k/255*(palette.length-1),i=Math.min(palette.length-2,Math.floor(t)),f=t-i;return palette[i].map((v,j)=>Math.round(v*(1-f)+palette[i+1][j]*f));});
function axes(o,xmin,xmax,ymin,ymax,xlabel,ylabel){const {c,left,top,pw,ph}=o;c.strokeStyle='#607281';c.lineWidth=1;c.strokeRect(left,top,pw,ph);c.fillStyle='#b2c4d0';c.textAlign='center';
 for(let i=0;i<=4;i++){const x=xmin+(xmax-xmin)*i/4,y=ymin+(ymax-ymin)*i/4;c.fillText(Math.abs(x)<.001?'0':x.toFixed(Math.abs(xmax-xmin)<20?1:0),left+pw*i/4,top+ph+20);c.textAlign='right';c.fillText(Math.abs(y)<.001?'0':y.toFixed(Math.abs(ymax-ymin)<20?1:0),left-8,top+ph-ph*i/4+4);c.textAlign='center';}
 c.fillText(xlabel,left+pw/2,top+ph+46);c.save();c.translate(16,top+ph/2);c.rotate(-Math.PI/2);c.fillText(ylabel,0,0);c.restore();}
function transpose(z,cols,rows){const t=new Float32Array(cols*rows);for(let y=0;y<rows;y++)for(let x=0;x<cols;x++)t[x*rows+y]=z[y*cols+x];return t;}
function heat(id,z,cols,rows,xmin,xmax,xlabel,ymin,ymax,ylabel){const o=setup(id),{c,left,top,pw,ph}=o;
 const buffer=document.createElement('canvas');buffer.width=cols;buffer.height=rows;const bc=buffer.getContext('2d'),pixels=bc.createImageData(cols,rows);
 for(let y=0;y<rows;y++)for(let x=0;x<cols;x++){const color=lut[Math.max(0,Math.min(255,Math.round((z[y*cols+x]+40)/40*255)))],j=((rows-1-y)*cols+x)*4;pixels.data[j]=color[0];pixels.data[j+1]=color[1];pixels.data[j+2]=color[2];pixels.data[j+3]=255;}
 bc.putImageData(pixels,0,0);c.imageSmoothingEnabled=true;c.drawImage(buffer,left,top,pw,ph);axes(o,xmin,xmax,ymin,ymax,xlabel,ylabel);
 for(let j=0;j<256;j++){const [r,g,b]=lut[255-j];c.fillStyle=`rgb(${r},${g},${b})`;c.fillRect(left+pw+12,top+ph*j/256,10,ph/256+1);}c.fillStyle='#b2c4d0';c.textAlign='left';c.fillText('0',left+pw+25,top+5);c.fillText('−40',left+pw+23,top+ph);c.fillText('dB',left+pw+10,top-6);
 const xPos=v=>left+pw*(v-xmin)/(xmax-xmin),yPos=v=>top+ph*(ymax-v)/(ymax-ymin);
 c.save();c.beginPath();c.rect(left,top,pw,ph);c.clip();c.strokeStyle='#52ebed';c.lineWidth=1.5;
 if(id==='rd'){c.setLineDash([5,4]);c.beginPath();c.moveTo(xPos(result.fd),top);c.lineTo(xPos(result.fd),top+ph);c.stroke();}
 else{const x=xPos(0),y=yPos(5000),xp=xPos(result.shift);c.beginPath();c.moveTo(x-7,y);c.lineTo(x+7,y);c.moveTo(x,y-7);c.lineTo(x,y+7);c.stroke();c.strokeStyle='#a9f76a';c.beginPath();c.arc(xp,y,8,0,2*Math.PI);c.stroke();}
 c.restore();}
function line(id,xx,yy,xmin,xmax,label){const o=setup(id),{c,left,top,pw,ph}=o;axes(o,xmin,xmax,-40,0,label,'Response [dB]');c.save();c.beginPath();c.rect(left,top,pw,ph);c.clip();c.strokeStyle='#293c4a';
 for(let k=1;k<4;k++){c.beginPath();c.moveTo(left,top+ph*k/4);c.lineTo(left+pw,top+ph*k/4);c.stroke();}c.strokeStyle='#78d9da';c.lineWidth=1.8;c.beginPath();for(let i=0;i<xx.length;i++){const x=left+(xx[i]-xmin)/(xmax-xmin)*pw,y=top-yy[i]/40*ph;i?c.lineTo(x,y):c.moveTo(x,y);}c.stroke();c.restore();}
function paint(){if(paintPending)return;paintPending=true;requestAnimationFrame(()=>{paintPending=false;if(!result)return;const s=result;const r0=s.rAxis[0],r1=s.rAxis[s.cols-1];heat('rd',transpose(s.rd,s.dcols,s.drows),s.drows,s.dcols,-800,800,'Relative Doppler frequency of scene [Hz]',r0,r1,'Slant range [m]');heat('image',transpose(s.image,s.cols,s.rows),s.rows,s.cols,s.xAxis[0],s.xAxis[s.rows-1],'Azimuth along flight track [m]',r0,r1,'Slant range [m]');line('rangeProfile',s.rAxis,s.rp,r0,r1,'Slant range [m]');line('azimuthProfile',s.xAxis,s.ap,s.shift-10,s.shift+10,'Azimuth [m]');});}
new ResizeObserver(()=>paint()).observe(document.querySelector('main'));
schedule();
