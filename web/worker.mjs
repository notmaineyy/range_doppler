import {compute} from './compute.mjs';
let latest=0;
const channel=new MessageChannel();let resume;channel.port1.onmessage=()=>{if(resume){const r=resume;resume=null;r();}};
const yieldWork=()=>new Promise(resolve=>{resume=resolve;channel.port2.postMessage(0);});
onmessage=async({data})=>{
 latest=data.id;const start=performance.now();
 try{
  const result=await compute(data.params,()=>latest!==data.id,yieldWork);
  if(result&&latest===data.id)postMessage({id:data.id,result,ms:performance.now()-start},[result.image.buffer,result.rd.buffer,result.rp.buffer,result.ap.buffer,result.rAxis.buffer,result.xAxis.buffer]);
 }catch(e){postMessage({id:data.id,error:e.message});}
};
