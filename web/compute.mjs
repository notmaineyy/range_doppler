// Stationary target, moving aircraft: local quadratic stripmap model.
// Ideal trajectory-based range migration and platform Doppler centroid removal.
// The image coordinate is the along-track slow-time coordinate V*t. Squint is measured from broadside.
// Float64 arithmetic, radix-2 FFT, normalized coherent azimuth weighting.
const plans=new Map();
function plan(n){
 if(plans.has(n)) return plans.get(n);
 const rev=new Uint32Array(n),co=new Float64Array(n/2),si=new Float64Array(n/2);
 let bits=Math.log2(n);
 for(let i=0;i<n;i++){let a=i,b=0;for(let k=0;k<bits;k++){b=(b<<1)|(a&1);a>>=1;}rev[i]=b;}
 for(let k=0;k<n/2;k++){co[k]=Math.cos(-2*Math.PI*k/n);si[k]=Math.sin(-2*Math.PI*k/n);}
 const p={rev,co,si};plans.set(n,p);return p;
}
function fft(re,im){const n=re.length,{rev,co,si}=plan(n);
 for(let i=0;i<n;i++){const j=rev[i];if(j>i){[re[i],re[j]]=[re[j],re[i]];[im[i],im[j]]=[im[j],im[i]];}}
 for(let len=2;len<=n;len*=2){const h=len/2,stride=n/len;
  for(let i=0;i<n;i+=len)for(let j=0;j<h;j++){
   const a=i+j,b=a+h,k=j*stride,rr=re[b]*co[k]-im[b]*si[k],ii=re[b]*si[k]+im[b]*co[k];
   re[b]=re[a]-rr;im[b]=im[a]-ii;re[a]+=rr;im[a]+=ii;
  }
 }
}
const sinc=x=>Math.abs(x)<1e-12?1:Math.sin(Math.PI*x)/(Math.PI*x);
const db=x=>20*Math.log10(Math.max(x,1e-4));
export async function compute(p, cancelled=()=>false, yieldWork=async()=>{}){
 const {B,vr,L,aperture,window}=p;
 // Constant-speed straight flight past a stationary target. Radial velocity is
 // the centre-time LOS projection, not an independent moving-target velocity.
 const squint=p.squint??Math.asin(vr/150)*180/Math.PI;
 if(![B,vr,L,aperture,squint].every(Number.isFinite)||B<20||B>500||Math.abs(squint)>15.000001||L<.5||L>5||aperture<25||aperture>100||!['Rectangular','Hann','Hamming'].includes(window))throw Error('Control values are outside the supported range.');
 const cs=Math.cos(squint*Math.PI/180),sn=Math.sin(squint*Math.PI/180),rate=300*cs*cs;
 const aircraftRadialVelocity=150*sn;
 if(Math.abs(vr-aircraftRadialVelocity)>.02)throw Error('Aircraft radial velocity and squint must satisfy vr = 150 sin(squint).');
 const compensation='Aircraft trajectory',compensated=true,residualVr=0;
 const n=Math.round(1600*(aperture/100)/(L*cs)),N=8192,NR=301,ND=2**Math.ceil(Math.log2(n)),DROWS=401,DCOLS=151;
 const T=n/1600,dr=150/B,da=150/(rate*T),shift=0;
 const fd=0,fdResidual=0,platformCentroid=2*aircraftRadialVelocity/.03,dx=1600/N*150/rate;
 const factors=windowFactors(n,window);
 const times=new Float64Array(n),wr=new Float64Array(n),wi=new Float64Array(n),rr=new Float64Array(n),ri=new Float64Array(n);
 let sum=0;
 for(let k=0;k<n;k++){
  const t=(k-(n-1)/2)/1600,w=windowWeight(k,n,window),phase=2*Math.PI*fdResidual*t;
  times[k]=t;sum+=w;wr[k]=w*Math.cos(phase);wi[k]=w*Math.sin(phase);
  rr[k]=Math.cos(2*Math.PI*fd*t-Math.PI*rate*t*t);ri[k]=Math.sin(2*Math.PI*fd*t-Math.PI*rate*t*t);
 }
 // Fixed absolute azimuth grid: the plot no longer follows or rescales to the target.
 const xmin=-220,xmax=220,rows=4401,gridDx=.1;
 const image=new Float32Array(rows*NR),rd=new Float32Array(DROWS*DCOLS),rp=new Float32Array(NR),ap=new Float32Array(rows),rAxis=new Float32Array(NR),xAxis=new Float32Array(rows);
 const re=new Float64Array(N),im=new Float64Array(N),dre=new Float64Array(ND),dim=new Float64Array(ND);
 let peak=-1,peakCol=0,peakRow=0,rdPeak=0;
 for(let y=0;y<rows;y++)xAxis[y]=xmin+y*gridDx;
 for(let col=0;col<NR;col++){
  if(cancelled())return null;
   const r=-15+col*.1;rAxis[col]=5000+r;re.fill(0);im.fill(0);
  const withRD=col%2===0;if(withRD){dre.fill(0);dim.fill(0);}
  for(let k=0;k<n;k++){
   const env=sinc((r+residualVr*times[k])/dr);re[k]=env*wr[k];im[k]=env*wi[k];
   if(withRD){const observed=sinc(r/dr);dre[k]=observed*rr[k];dim[k]=observed*ri[k];}
  }
  fft(re,im);
  for(let row=0;row<rows;row++){
   const u=xAxis[row]/dx,k=Math.floor(u),fraction=u-k,a0=((k%N)+N)%N,a1=(a0+1)%N;
   // Interpolate magnitude for a fixed display grid, without inventing a Doppler shift.
   const a=((1-fraction)*Math.hypot(re[a0],im[a0])+fraction*Math.hypot(re[a1],im[a1]))/sum;
   image[row*NR+col]=a;
   if(a>peak){peak=a;peakCol=col;peakRow=row;}
  }
  if(withRD){fft(dre,dim);for(let y=0;y<DROWS;y++){
    const f=-800+y*1600/(DROWS-1),bin=((Math.round(f*ND/1600)%ND)+ND)%ND,a=Math.hypot(dre[bin],dim[bin]);
    rd[y*DCOLS+col/2]=a;rdPeak=Math.max(rdPeak,a);
  }}
  if(col%12===11){await yieldWork();}
 }
 for(let c=0;c<NR;c++)rp[c]=image[peakRow*NR+c];
 for(let r=0;r<rows;r++)ap[r]=image[r*NR+peakCol];
 let l=peakRow,h=peakRow,threshold=peak/Math.sqrt(2);
 while(l>0&&ap[l]>=threshold)l--;while(h<rows-1&&ap[h]>=threshold)h++;
 const left=xAxis[l]+(threshold-ap[l])/(ap[l+1]-ap[l])*gridDx;
 const right=xAxis[h-1]+(threshold-ap[h-1])/(ap[h]-ap[h-1])*gridDx;
 const width=l>0&&h<rows-1?right-left:null;
 for(let i=0;i<image.length;i++)image[i]=db(image[i]);
 for(let i=0;i<rd.length;i++)rd[i]=db(rd[i]/rdPeak);
 for(let i=0;i<rp.length;i++)rp[i]=db(rp[i]);for(let i=0;i<ap.length;i++)ap[i]=db(ap[i]);
 return {image,rd,rp,ap,rAxis,xAxis,cols:NR,rows,dcols:DCOLS,drows:DROWS,dr,da,T,shift,fd,walk:Math.abs(aircraftRadialVelocity)*T,width,peak,peakR:rAxis[peakCol],peakX:xAxis[peakRow],Bd:rate*T,rate,platformCentroid,aircraftRadialVelocity,syntheticLength:150*T,
   broadening:factors.beta,windowWidthBins:factors.bins,nominalWidth:factors.bins*da,rectWidth:factors.rect*da,compensated,squint,params:{...p,squint,compensation}};
}

// Full half-power width in units of 1/T. Evaluate the actual discrete window,
// rather than confusing ENBW (Hann ~1.50) with mainlobe broadening (~1.63).
const factorCache=new Map();
export function windowFactors(n,window){
 const key=n+window;if(factorCache.has(key))return factorCache.get(key);
 function width(kind){
  const w=Float64Array.from({length:n},(_,k)=>windowWeight(k,n,kind)),sum=w.reduce((a,b)=>a+b,0);
  let lo=0,hi=2;
  for(let it=0;it<40;it++){
   const f=(lo+hi)/2;let amplitude=0;
   for(let k=0;k<n;k++)amplitude+=w[k]*Math.cos(2*Math.PI*f*(k-(n-1)/2)/n);
   if(amplitude/sum>Math.SQRT1_2)lo=f;else hi=f;
  }
  return lo+hi;
 }
 const rect=width('Rectangular'),bins=window==='Rectangular'?rect:width(window);
 const value={rect,bins,beta:bins/rect};factorCache.set(key,value);return value;
}

function windowWeight(k,n,kind){
 const cosine=Math.cos(2*Math.PI*k/(n-1));
 return kind==='Hann'?.5-.5*cosine:kind==='Hamming'?.54-.46*cosine:1;
}
