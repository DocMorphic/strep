import {offsetMatrix} from './scene-prop-runtime-editor.mjs';

export function createScenePropBakeEditor({document=globalThis.document,api,post,download=saveJSON}={}){
 const el=name=>document.getElementById('scenePropBake'+name),selected=()=>document.getElementById('scenePropRuntimeJobs').value;
 const status=text=>{el('Status').textContent=text;},guard=fn=>async()=>{try{await fn();}catch(error){status(error.message);}};
 const option=(value,text)=>{const node=document.createElement('option');node.value=value;node.textContent=text;return node;};
 const numeric=(name,label,low=-Infinity,high=Infinity)=>{const node=el(name),v=Number(node.value);if(node.value.trim()===''||!Number.isFinite(v)||v<low||v>high)throw Error('Choose a valid '+label+'.');return v;};
 let binding=null,epoch=0,reviewEpoch=0,busy=false;
 function snapshot(){
  if(!binding||selected()!==binding.runtime_job)throw Error('Bind the selected completed prop runtime again.');
  if(!['plane','none'].includes(el('Floor').value))throw Error('Choose the ground collision mode.');
  return {runtime_job:binding.runtime_job,source_result_sha256:binding.source_result_sha256,request:{schema:'strep-scene-prop-bake-request-v1',source_runtime_zip_sha256:binding.source_runtime_zip_sha256,
   parent_world_transform:offsetMatrix(['X','Y','Z'].map(n=>numeric(n,'scene position')),['RX','RY','RZ'].map(n=>numeric(n,'scene rotation'))),
   floor:{enabled:el('Floor').value==='plane',height_m:numeric('Height','ground height',-10000,10000),friction:numeric('Friction','ground friction',0,1),restitution:numeric('Restitution','ground restitution',0,1)}}};
 }
 el('Bind').onclick=guard(async()=>{const id=selected();if(!id)throw Error('Select a completed prop runtime first.');const token=++epoch;binding=null;
  const m=await api(`/api/scene-prop-bake-source?id=${encodeURIComponent(id)}`);
  if(token!==epoch||selected()!==id||m.runtime_job!==id)throw Error('Prop runtime selection changed; bind again.');
  if(![m.source_result_sha256,m.source_runtime_zip_sha256].every(v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v))||![60,120,240].includes(m.physics_fps)||m.quality_approved!==false||m.release_approved!==false)throw Error('Invalid bound prop runtime metadata.');
  binding=m;status(`Runtime bound at ${m.physics_fps} Hz. Original scene conditions: ${m.source_scene_conditions_pass?'pass':'fail'}; root samples: ${m.root_samples_pass?'pass':'fail'}. Choose the scene placement and ground.`);
 });
 el('Save').onclick=guard(()=>download(snapshot()));
 async function refresh(){const data=await api('/api/scene-prop-bake-jobs'),chosen=el('Jobs').value;el('Jobs').replaceChildren(...data.jobs.map(j=>option(j.id,`${j.id} · ${j.status}`)));if(data.jobs.some(j=>j.id===chosen))el('Jobs').value=chosen;return data;}
 el('Refresh').onclick=guard(refresh);
 el('Build').onclick=guard(async()=>{if(busy)throw Error('Wait for this bake request.');const payload=snapshot(),token=epoch;busy=true;el('Build').disabled=true;
  try{const result=await post('/api/scene-prop-bake-assets',payload);await refresh();if(token===epoch&&selected()===payload.runtime_job)el('Jobs').value=result.id;
   status(`Bake ${result.id} started from ${payload.runtime_job}. Original clips stay selected; inspect its contact and timing results when complete.`);
  }finally{busy=false;el('Build').disabled=false;}
 });
 el('Review').onclick=guard(async()=>{const id=el('Jobs').value;if(!id)throw Error('Choose a prop animation bake.');const token=++reviewEpoch,result=await api(`/api/scene-prop-bake-review?id=${encodeURIComponent(id)}`);
  if(token!==reviewEpoch||el('Jobs').value!==id||result.id!==id)throw Error('Bake review selection changed; request it again.');
  el('Results').replaceChildren();const text=document.createElement('p');
  if(result.status==='complete'){
   if(result.quality_approved!==false||result.release_approved!==false||result.engine_import_verified!==true||typeof result.maximum_application_delay_s!=='number'||!Number.isFinite(result.maximum_application_delay_s)||result.maximum_application_delay_s<0)throw Error('Invalid completed bake conditions.');
   const state=v=>v===null?'not measured':v===true?'pass':v===false?'fail':'unknown';
   text.textContent=`Editable assets ready. Original scene: ${state(result.source_scene_conditions_pass)}; root samples: ${state(result.root_samples_pass)}. Configured engine import: pass. Physical timing: ${state(result.exact_physical_event_timing_pass)} (${(result.maximum_application_delay_s*1000).toFixed(3)} ms maximum delay). Baked grip agreement: ${state(result.held_grip_sampled_conditions_pass)}; ground screen: ${state(result.floor_sampled_screen_pass)}. Default 30 FPS import: ${state(result.default_30fps_import_pass)}. Anatomical contact, continuous collision and animation quality are not approved.`;
   const allowed=['bake/baked-assets.zip','bake-request.json','bake/result.json','result.json'];
   if(!Array.isArray(result.downloads)||result.downloads.length!==allowed.length||new Set(result.downloads.map(d=>d.label)).size!==allowed.length||result.downloads.some(d=>!allowed.includes(d.label)||d.url!==`/files/scene-prop-bake-jobs/${encodeURIComponent(id)}/${d.label}`))throw Error('Invalid bake downloads.');
   el('Results').append(text);for(const d of result.downloads){const a=document.createElement('a');a.href=d.url;a.download='';a.className='btn';a.textContent=d.label;el('Results').append(a);}
  }else{text.textContent=`${result.status}: ${result.error||result.stage||'waiting'}`;el('Results').append(text);}
  status(text.textContent);
 });
 return {snapshot,refresh};
}
function saveJSON(value){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'})),a=globalThis.document.createElement('a');a.href=url;a.download='prop-bake-studio-request.json';a.click();URL.revokeObjectURL(url);}
