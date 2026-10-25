import {validateNativePreview} from './native-preview-policy.mjs';
export function createSurfaceClipComparison({document,job,attempt,api,createPlayer}){
 const el=id=>document.getElementById(id);let player=null,serial=0,time=0,loaded=false;
 const disable=()=>{for(const id of ['play','time','fit'])el(id).disabled=true;};
 const fail=e=>{player?.pause();disable();el('status').textContent=e.message;};
 async function init(){try{
  if(!/^[a-f0-9]{32}$/.test(job)||!/^[a-f0-9]{32}$/.test(attempt))throw Error('Open a saved comparison from Studio.');
  const data=await api(`/api/surface-clip-jobs/${job}/attempt/${attempt}`);
  if(data.id!==job||data.attempt!==attempt||data.quality_approved!==false||data.release_approved!==false||!Array.isArray(data.versions)||!data.versions.length||data.versions.length>3)throw Error('Comparison identity changed.');
  const r=data.result;
  if(!r||!['checkpointed','unresolved','complete_numerical_candidate'].includes(r.status)||r.quality_approved!==false||r.release_approved!==false||r.transition_review_required!==true||!Number.isInteger(r.total_keys)||r.total_keys<2||r.validated_through!==undefined&&(!Number.isInteger(r.validated_through)||r.validated_through<0||r.validated_through>=r.total_keys))throw Error('Invalid correction measurements.');
  const urls=new Set();
  for(const v of data.versions){validateNativePreview(v);if(v.kind!=='native_surface_correction'||!v.preview_url.startsWith(`/files/surface-clip-jobs/${job}/${attempt}/`)||v.animation_index!==0||v.animation_count!==1||v.preview_start_s!==0||v.preview_end_s!==data.versions[0].preview_end_s||urls.has(v.preview_url))throw Error('Unexpected comparison asset.');urls.add(v.preview_url);}
  if(!data.versions[0].preview_url.endsWith('/original.glb'))throw Error('Original must be the initial comparison.');
  player=await createPlayer({canvas:el('view'),onTime:t=>{time=t;el('time').value=String(t);el('clock').textContent=t.toFixed(3)+' s';}});
  el('version').replaceChildren();data.versions.forEach((v,i)=>{const option=document.createElement('option');option.value=String(i);option.textContent=v.label;el('version').append(option);});
  async function load(){const token=++serial,previous=time;player.pause();disable();const v=data.versions[Number(el('version').value)];
   try{await player.load(v,{fitView:!loaded});if(token!==serial)return;player.seek(loaded?previous:0);loaded=true;el('time').max=String(v.preview_end_s);for(const id of ['play','time','fit'])el(id).disabled=false;el('status').textContent=`${v.label}. ${r.status}; ${r.validated_through===undefined?'no accepted prefix':`checked ${r.validated_through+1}/${r.total_keys} keys`}. Scene, engine, transition and motion-quality review remain required.`;}
   catch(e){if(token===serial)fail(e);}
  }
  el('version').disabled=false;el('version').value='0';el('version').onchange=load;el('play').onclick=()=>player.toggle();el('fit').onclick=()=>player.fit();el('time').oninput=()=>{player.pause();player.seek(Number(el('time').value));};await load();
 }catch(e){fail(e);}}
 return {init};
}
if(typeof document!=='undefined'){
 const query=new URLSearchParams(location.search);
 const comparison=createSurfaceClipComparison({document,job:query.get('job'),attempt:query.get('attempt'),
  api:async url=>{const response=await fetch(url,{cache:'no-store'}),data=await response.json();if(!response.ok)throw Error(data.error||'Comparison unavailable');return data;},
  createPlayer:async options=>(await import('./native-reference-player.mjs')).createNativeReferencePlayer(options)});
 await comparison.init();
}
