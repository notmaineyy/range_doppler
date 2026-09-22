// Independent analytic checks for the browser image former. Run: node test_web.mjs
import assert from 'node:assert/strict';
import {compute,windowFactors} from './web/compute.mjs';
const p={B:200,vr:0,L:2,aperture:100,window:'Rectangular',squint:0,compensation:'Stationary scene'};
const close=(a,b,tol=1e-5)=>assert.ok(Math.abs(a-b)<tol,`${a} != ${b}`);
const base=await compute(p);
close(base.peak,1);close(base.peakX,0);close(base.peakR,5000);
// Stationary image is separable: the range cut must be the matched sinc response.
for(let i=0;i<base.cols;i++){
 const u=(base.rAxis[i]-5000)/base.dr;
 const amplitude=Math.abs(u)<1e-8?1:Math.abs(Math.sin(Math.PI*u)/(Math.PI*u));
 close(base.rp[i],20*Math.log10(Math.max(amplitude,1e-4)),.25); // Float32 range-axis quantization
}
for(const vr of [-38.82,-3,3,38.82]){
 const squint=Math.asin(vr/150)*180/Math.PI;
 const a=await compute({...p,vr,squint});
 close(a.peakX,0);close(a.peakR,5000);close(a.peak,1);
 close(a.platformCentroid,2*vr/.03);close(a.fd,0);close(a.shift,0);
 assert.deepEqual(a.xAxis,base.xAxis);assert.deepEqual(a.rAxis,base.rAxis);
 close(a.rate,300*(1-(vr/150)**2));
 // Centroid-corrected data must match for symmetric forward/backward squint.
 const b=await compute({...p,vr:-vr,squint:-squint});
 assert.deepEqual(a.image,b.image);assert.deepEqual(a.rd,b.rd);
}
const long=await compute({...p,L:5}),short=await compute({...p,L:.5});
assert.ok(long.width>short.width*9); // physical antenna, full-aperture stripmap
const quarter=await compute({...p,aperture:25});
close(quarter.da/base.da,4);assert.ok(quarter.syntheticLength<base.syntheticLength);
for(const squint of [-15,15]){
 const s=await compute({...p,squint,vr:150*Math.sin(squint*Math.PI/180)});const cs=Math.cos(squint*Math.PI/180);
 close(s.rate,300*cs*cs);close(s.platformCentroid,10000*Math.sin(squint*Math.PI/180));
 close(s.peakX,0);close(s.peak,1);assert.deepEqual(s.xAxis,base.xAxis);

}
const f=windowFactors(10000,'Hann');close(f.rect,.88589294,1e-6);close(f.bins,1.440727,2e-5);close(f.beta,1.6263,.001);
const hann=await compute({...p,window:'Hann'});assert.ok(hann.width>base.width*1.6);close(hann.peak,1);
assert.ok(hann.broadening>1.62&&hann.broadening<1.64);
await assert.rejects(()=>compute({...p,squint:90}));await assert.rejects(()=>compute({...p,B:0}));
assert.equal(await compute(p,()=>true),null);
const extreme=await compute({...p,B:500,vr:150*Math.sin(Math.PI/12),L:.5,squint:15});
assert.ok(extreme.fd+extreme.Bd/2<800);assert.ok(Number.isFinite(extreme.width));
await assert.rejects(()=>compute({...p,vr:3,squint:0}));
console.log('Passed: sinc PSF, stationary target, aircraft radial geometry/compensation, fixed axes, antenna/aperture scaling, squint centroid/rate, Hann broadening, bounds and cancellation.');

const hamming=await compute({...p,window:'Hamming'});
close(hamming.peak,1);close(hamming.peakX,0);
assert.ok(hamming.width>base.width*1.45&&hamming.width<hann.width);
assert.ok(hamming.broadening>1.46&&hamming.broadening<1.48);
// Independent finite Hamming DTFT half-power check at the reported width.
const hn=Math.round(hamming.T*1600),hf=windowFactors(hn,'Hamming').bins/(2*hn);
let hs=0,hr=0;
for(let k=0;k<hn;k++){const w=.54-.46*Math.cos(2*Math.PI*k/(hn-1));hs+=w;hr+=w*Math.cos(2*Math.PI*hf*(k-(hn-1)/2));}
close(hr/hs,Math.SQRT1_2,1e-9);
const sidelobes=Array.from(hamming.ap).filter((_,i)=>Math.abs(hamming.xAxis[i])>2.1*hamming.da);
assert.ok(Math.max(...sidelobes)<-40);
console.log('Passed: Hamming normalization, focus, half-power DTFT width and sidelobe suppression.');
