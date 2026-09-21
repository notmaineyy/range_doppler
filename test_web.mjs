// Run: node test_web.mjs. Values below come from the NumPy reference model.
import assert from 'node:assert/strict';
import {compute} from './web/compute.mjs';
const baseline={B:200,vr:0,L:2,aperture:100,window:'Rectangular'};
const cases=[
 [{},.882687612,1,0],
 [{vr:3},1.249819885,.58949013265,100],
 [{aperture:25},3.543234471,1,0],
 [{window:'Hann'},1.441070935,1,0],
];
for(const [changes,width,peak,x] of cases){
 const s=await compute({...baseline,...changes});
 assert.ok(Math.abs(s.width-width)<1e-5);
 assert.ok(Math.abs(s.peak-peak)<1e-8);
 assert.ok(Math.abs(s.peakX-x)<.1);
 assert.equal(s.image.length,s.cols*s.rows);
 assert.equal(s.rd.length,s.dcols*s.drows);
}
await assert.rejects(()=>compute({...baseline,B:0}));
assert.equal(await compute(baseline,()=>true),null);
const extreme=await compute({...baseline,B:500,vr:5,L:.5});
assert.ok(Number.isFinite(extreme.width));
assert.ok(extreme.fd+extreme.Bd/2<800);
console.log('Browser model: reference values, array dimensions, invalid input, cancellation and extreme sampling passed.');
