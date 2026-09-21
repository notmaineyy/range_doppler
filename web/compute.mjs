// Same paraxial, range-compressed signal model as sar_model.py.
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
 if(![B,vr,L,aperture].every(Number.isFinite)||B<20||B>500||Math.abs(vr)>5||L<.5||L>5||aperture<25||aperture>100||!['Rectangular','Hann'].includes(window))throw Error('Control values are outside the supported range.');
 const n=Math.round(1600*(aperture/100)/L),N=8192,NR=301,ND=2**Math.ceil(Math.log2(n)),DROWS=401,DCOLS=151;
 const T=n/1600,dr=150/B,da=.5/T,shift=vr*5000/150,fd=2*vr/.03,dx=800/N;
 const times=new Float64Array(n),wr=new Float64Array(n),wi=new Float64Array(n),rr=new Float64Array(n),ri=new Float64Array(n);
 let sum=0;
 for(let k=0;k<n;k++){
  const t=(k-(n-1)/2)/1600,w=window==='Hann'?.5-.5*Math.cos(2*Math.PI*k/(n-1)):1,phase=2*Math.PI*fd*t;
  times[k]=t;sum+=w;wr[k]=w*Math.cos(phase);wi[k]=w*Math.sin(phase);
  rr[k]=Math.cos(phase-Math.PI*300*t*t);ri[k]=Math.sin(phase-Math.PI*300*t*t);
 }
 const full=!!p.full,half=Math.max(8,4*da),xmin=full?-190:shift-half,xmax=full?190:shift+half;
 // Select exact zero-padded FFT samples. Detailed zoom always resolves the mainlobe.
 const low=Math.ceil(xmin/dx),high=Math.floor(xmax/dx),rows=high-low+1;
 const image=new Float32Array(rows*NR),rd=new Float32Array(DROWS*DCOLS),rp=new Float32Array(NR),ap=new Float32Array(rows),rAxis=new Float32Array(NR),xAxis=new Float32Array(rows);
 const re=new Float64Array(N),im=new Float64Array(N),dre=new Float64Array(ND),dim=new Float64Array(ND);
 let peak=-1,peakCol=0,peakRow=0,rdPeak=0;
 for(let y=0;y<rows;y++)xAxis[y]=(low+y)*dx;
 for(let col=0;col<NR;col++){
  if(cancelled())return null;
  const r=-15+col*.1;rAxis[col]=r;re.fill(0);im.fill(0);
  const withRD=col%2===0;if(withRD){dre.fill(0);dim.fill(0);}
  for(let k=0;k<n;k++){
   const env=sinc((r+vr*times[k])/dr);re[k]=env*wr[k];im[k]=env*wi[k];
   if(withRD){dre[k]=env*rr[k];dim[k]=env*ri[k];}
  }
  fft(re,im);
  for(let row=0;row<rows;row++){
   const bin=((low+row)%N+N)%N,a=Math.hypot(re[bin],im[bin])/sum;
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
 const left=xAxis[l]+(threshold-ap[l])/(ap[l+1]-ap[l])*dx;
 const right=xAxis[h-1]+(threshold-ap[h-1])/(ap[h]-ap[h-1])*dx;
 const width=right-left;
 for(let i=0;i<image.length;i++)image[i]=db(image[i]);
 for(let i=0;i<rd.length;i++)rd[i]=db(rd[i]/rdPeak);
 for(let i=0;i<rp.length;i++)rp[i]=db(rp[i]);for(let i=0;i<ap.length;i++)ap[i]=db(ap[i]);
 return {image,rd,rp,ap,rAxis,xAxis,cols:NR,rows,dcols:DCOLS,drows:DROWS,dr,da,T,shift,fd,walk:Math.abs(vr)*T,width,peak,peakR:rAxis[peakCol],peakX:xAxis[peakRow],Bd:300*T,params:p};
}
