export function createBakedSceneEditor({document=globalThis.document,api,post}={}){
 const el=name=>document.getElementById('bakedScene'+name),selected=()=>document.getElementById('scenePropBakeJobs').value;
 const status=text=>{el('Status').textContent=text;},guard=fn=>async()=>{try{await fn();}catch(error){status(error.message);}};
 const option=(value,text)=>{const node=document.createElement('option');node.value=value;node.textContent=text;return node;};
 const state=v=>v===null?'not measured':v===true?'pass':v===false?'fail':'unknown';
 let binding=null,epoch=0,reviewEpoch=0,busy=false;
 function snapshot(){if(!binding||selected()!==binding.bake_job)throw Error('Bind the selected completed animation bake again.');return {bake_job:binding.bake_job,source_result_sha256:binding.source_result_sha256};}
 el('Bind').onclick=guard(async()=>{const id=selected();if(!id)throw Error('Choose a completed animation bake first.');const token=++epoch;binding=null;
  const m=await api(`/api/baked-scene-source?id=${encodeURIComponent(id)}`);
  if(token!==epoch||selected()!==id||m.bake_job!==id)throw Error('Animation bake selection changed; bind again.');
  if(![m.source_result_sha256,m.source_baked_zip_sha256].every(v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v))||m.quality_approved!==false||m.release_approved!==false)throw Error('Invalid saved-scene source metadata.');
  binding=m;status(`Bake bound. Original scene: ${state(m.source_scene_conditions_pass)}; physical timing: ${state(m.exact_physical_event_timing_pass)}. Export preserves those results and the original clips.`);
 });
 async function refresh(){const data=await api('/api/baked-scene-jobs'),chosen=el('Jobs').value;el('Jobs').replaceChildren(...data.jobs.map(j=>option(j.id,`${j.id} · ${j.status}`)));if(data.jobs.some(j=>j.id===chosen))el('Jobs').value=chosen;return data;}
 el('Refresh').onclick=guard(refresh);
 el('Build').onclick=guard(async()=>{if(busy)throw Error('Wait for this saved-scene request.');const payload=snapshot(),token=epoch;busy=true;el('Build').disabled=true;
  try{const result=await post('/api/baked-scene-assets',payload);await refresh();if(token===epoch&&selected()===payload.bake_job)el('Jobs').value=result.id;
   status(`Saved-scene export ${result.id} started. Original clips stay selected; review its playback verification when complete.`);
  }finally{busy=false;el('Build').disabled=false;}
 });
 el('Review').onclick=guard(async()=>{const id=el('Jobs').value;if(!id)throw Error('Choose a saved-scene export.');const token=++reviewEpoch,result=await api(`/api/baked-scene-review?id=${encodeURIComponent(id)}`);
  if(token!==reviewEpoch||el('Jobs').value!==id||result.id!==id)throw Error('Saved-scene review selection changed; request it again.');
  el('Results').replaceChildren();const text=document.createElement('p');
  if(result.status==='complete'){
   if(result.scene_playback_verified!==true||result.exported_main_scene_verified!==true||result.live_prop_physics!==false||result.quality_approved!==false||result.release_approved!==false||!Number.isFinite(result.source_end_hold_duration_s)||result.source_end_hold_duration_s<0||!Number.isFinite(result.maximum_application_delay_s)||result.maximum_application_delay_s<0)throw Error('Invalid saved-scene verification.');
   const allowed=['runtime/baked-runtime.zip','runtime/result.json','audit/result.json','request.json','result.json'];
   if(!Array.isArray(result.downloads)||result.downloads.length!==allowed.length||new Set(result.downloads.map(d=>d.label)).size!==allowed.length||result.downloads.some(d=>!allowed.includes(d.label)||d.url!==`/files/baked-scene-jobs/${encodeURIComponent(id)}/${d.label}`))throw Error('Invalid saved-scene downloads.');
   text.textContent=`Saved scene ready. Shared actor/prop playback and startup: pass. Original actor end hold: ${(result.source_end_hold_duration_s*1000).toFixed(3)} ms. Original scene: ${state(result.source_scene_conditions_pass)}; root samples: ${state(result.root_samples_pass)}; physical timing: ${state(result.exact_physical_event_timing_pass)} (${(result.maximum_application_delay_s*1000).toFixed(3)} ms delay); grip agreement: ${state(result.held_grip_sampled_conditions_pass)}; ground screen: ${state(result.floor_sampled_screen_pass)}; default 30 FPS import: ${state(result.default_30fps_import_pass)}. No live prop physics. Animation quality remains unapproved.`;
   el('Results').append(text);for(const d of result.downloads){const a=document.createElement('a');a.href=d.url;a.download='';a.className='btn';a.textContent=d.label;el('Results').append(a);}
  }else{text.textContent=`${result.status}: ${result.error||result.stage||'waiting'}`;el('Results').append(text);}
  status(text.textContent);
 });
 return {snapshot,refresh};
}
