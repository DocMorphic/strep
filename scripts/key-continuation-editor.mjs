const digest=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const job=v=>typeof v==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(v);
export function checkedReview(value,id){
 if(!job(id)||value?.schema!=='strep-studio-key-continuation-review-v1'||value.id!==id||value.original_selected!==true||value.quality_approved!==false||value.release_approved!==false)throw Error('Invalid continuation review.');
 if(value.status!=='complete'){if(!Array.isArray(value.downloads)||value.downloads.length)throw Error('Incomplete jobs cannot provide clips.');return value;}
 if(value.full_replay_pass!==true||typeof value.sampled_conditions_pass!=='boolean'||!Number.isInteger(value.rate_failures)||value.rate_failures<0||!Number.isInteger(value.floor_failures)||value.floor_failures<0)throw Error('Complete replay and failure counts required.');
 if(value.sampled_conditions_pass&&(value.rate_failures||value.floor_failures))throw Error('Passing checks contradict the recorded failures.');
 const expected=['input/saved-start.glb','study/probes/final/character.glb','study/result.json','replay/result.json'];
 if(!Array.isArray(value.downloads)||value.downloads.length!==expected.length||value.downloads.some((d,i)=>d.url!==`/files/key-continuation-jobs/${id}/${expected[i]}`||!digest(d.sha256)||typeof d.label!=='string'))throw Error('Returned files changed.');
 return value;
}
export function createKeyContinuationEditor({document=globalThis.document,api,post}){
 const el=n=>document.getElementById('keyContinuation'+n);let sources=[],busy=false,serial=0;
 const status=text=>{el('Status').textContent=text;};
 const guard=fn=>async()=>{try{await fn();}catch(e){status(e.message);}};
 const options=(name,items)=>{const old=el(name).value;el(name).replaceChildren(...items.map(({id,label})=>{const o=document.createElement('option');o.value=id;o.textContent=label??id;return o;}));if(items.some(i=>i.id===old))el(name).value=old;};
 function selection(){const source=sources.find(s=>s.id===el('Source').value);el('Build').disabled=busy||!source;
  el('SourceInfo').textContent=source?`${source.rate_failures} motion-rate failures · ${source.floor_failures} floor failures in the saved clip. Original limits stay fixed.`:'No verified saved corrections available.';return source;}
 async function load(){const token=++serial;el('Build').disabled=true;const value=await api('/api/key-continuation-sources');
  if(token!==serial)return;
  if(value?.schema!=='strep-studio-key-continuation-catalog-v1'||value.original_selected!==true||value.quality_approved!==false||value.release_approved!==false||!Array.isArray(value.sources)||new Set(value.sources.map(s=>s.id)).size!==value.sources.length||value.sources.some(s=>!digest(s.id)||typeof s.label!=='string'||!Number.isInteger(s.controls)||s.controls<1||![s.rate_failures,s.floor_failures].every(n=>Number.isInteger(n)&&n>=0)))throw Error('Invalid verified-job catalog.');
  sources=value.sources;options('Source',sources);selection();status(sources.length?'Choose a verified saved correction.':'No verified corrections are registered yet.');
 }
 async function refresh(){const value=await api('/api/key-continuation-jobs');if(!Array.isArray(value.jobs)||value.jobs.some(j=>!job(j.id)))throw Error('Invalid continuation jobs.');options('Jobs',value.jobs.map(j=>({id:j.id,label:`${j.id} · ${j.status}`})));}
 function request(){const source=selection();if(!source)throw Error('Choose a verified saved correction first.');const iterations=Number(el('Iterations').value);if(!Number.isInteger(iterations)||iterations<1||iterations>4)throw Error('Choose 1–4 further steps.');return {schema:'strep-studio-key-continuation-v1',source_id:source.id,iterations};}
 el('Source').onchange=selection;el('Sources').onclick=guard(load);el('Refresh').onclick=guard(refresh);
 el('Build').onclick=guard(async()=>{if(busy)throw Error('Wait for the current submission.');const payload=request();busy=true;selection();
  try{const value=await post('/api/key-continuations',payload);if(!job(value.id))throw Error('Invalid submitted continuation.');await refresh();el('Jobs').value=value.id;status('Continuation queued. Preparation, correction and full replay wait for the required RAM. Refresh results to review progress.');}
  finally{busy=false;selection();}
 });
 el('Jobs').onchange=()=>{el('Results').replaceChildren();};
 el('Review').onclick=guard(async()=>{const id=el('Jobs').value;if(!job(id))throw Error('Choose a continuation job.');const value=checkedReview(await api(`/api/key-continuation-review?id=${encodeURIComponent(id)}`),id);
  if(el('Jobs').value!==id)throw Error('Continuation selection changed; review it again.');el('Results').replaceChildren();
  const text=value.status==='complete'?`Full replay passed. Motion-rate failures: ${value.rate_failures}; floor failures: ${value.floor_failures}. ${value.sampled_conditions_pass?'Sampled checks pass; import and animation review remain required.':'The proposal still fails acceptance.'} Your current scene remains selected.`:`${value.status}: ${value.stage??value.error??'waiting'}`;
  const p=document.createElement('p');p.textContent=text;el('Results').append(p);
  for(const d of value.downloads){const a=document.createElement('a');a.className='btn';a.href=d.url;a.download='';a.textContent=d.label;el('Results').append(a);}status(text);
 });
 return {load,refresh,request};
}
