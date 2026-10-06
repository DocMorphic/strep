const clone=x=>structuredClone(x);
const key=x=>JSON.stringify(x,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
const hash=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
const job=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x);
const falseFlags=['quality_approved','release_approved','training_admitted','human_reviewed','anatomical_reviewed','physics_verified','continuous_collision_certified','real_time_playback_verified','gpu_render_checked','studio_selection_changed'];
const baseFiles=['result.json','audit/result.json','replay.json','source.json','surface-policy.json'],packageFiles=['checked-assets.zip','surface-gate.json','portable-surface-policy.json'];
export function checkedDownloads(value){
 if(!job(value?.id)||!Array.isArray(value.downloads))throw Error('Invalid surface export selection.');
 if(value.status!=='complete'){if(value.downloads.length)throw Error('Partial surface exports cannot expose completed files.');return [];}
 if(!hash(value.result_sha256)||value.original_selected!==true||falseFlags.some(k=>value[k]!==false)||typeof value.checked_package_available!=='boolean'||value.all_declared_scene_and_surface_samples_pass!==value.checked_package_available)throw Error('Typed unapproved surface export required.');
 if(!['scene','game'].includes(value.source?.kind)||!job(value.source?.job)||!hash(value.source?.result_sha256)||value.new_engine_executed!==false||value.engine_queries_reused!==true||typeof value.normal_intent_revised!=='boolean'||value.root_event_tracks_included!==(value.source.kind==='game'))throw Error('Exact source and reused engine evidence required.');
 const checks=['scene_conditions_pass','point_conditions_pass','surface_conditions_pass','root_event_conditions_pass'];
 if(checks.some(k=>typeof value[k]!=='boolean')||value.checked_package_available!==checks.every(k=>value[k]))throw Error('All declared surface/scene/root/event checks must pass.');
 const expected=new Set([...baseFiles,...(value.checked_package_available?packageFiles:[])]),seen=new Set();
 for(const d of value.downloads){if(!expected.has(d.label)||seen.has(d.label)||!hash(d.sha256)||d.url!==`/files/surface-export-jobs/${value.id}/${d.label}`)throw Error('Complete fixed surface export downloads required.');seen.add(d.label);}
 if(seen.size!==expected.size)throw Error('Complete fixed surface export downloads required.');return clone(value.downloads);
}
function policyFor(m){return m.inherited_surface??{limits:{maximum_opposition_error_degrees:1,backface_allowance_m:.00005,minimum_normal_area_m2:1e-12,minimum_normal_coherence:.1},maximum_actor_pose_queries:20000,contacts:Object.fromEntries(m.scene.contacts.map(c=>[c.id,{target_normal:c.target.space==='actor'?{space:'partner-surface'}:{space:c.target.space,normals:null}}]))};}
export function validatePolicy(value,scene){
 if(!value||key(Object.keys(value).sort())!==key(['contacts','limits','maximum_actor_pose_queries'])||!value.limits||!value.contacts)throw Error('Exact authored surface fields required.');
 const ranges={maximum_opposition_error_degrees:[0,90],backface_allowance_m:[0,.005],minimum_normal_area_m2:[1e-16,1e-4],minimum_normal_coherence:[1e-6,1]};
 if(key(Object.keys(value.limits).sort())!==key(Object.keys(ranges).sort())||Object.entries(ranges).some(([k,[lo,hi]])=>typeof value.limits[k]!=='number'||!Number.isFinite(value.limits[k])||value.limits[k]<lo||value.limits[k]>hi)||!Number.isInteger(value.maximum_actor_pose_queries)||value.maximum_actor_pose_queries<1||value.maximum_actor_pose_queries>20000)throw Error('Finite surface limits and a 1–20000 complete query budget required.');
 if(key(Object.keys(value.contacts).sort())!==key(scene.contacts.map(c=>c.id).sort()))throw Error('Surface conditions must cover every active contact exactly.');
 for(const c of scene.contacts){const row=value.contacts[c.id],d=row?.target_normal;if(key(Object.keys(row??{}))!==key(['target_normal']))throw Error('Exact target-normal declaration required.');
  if(c.target.space==='actor'){if(key(d)!==key({space:'partner-surface'}))throw Error('Use the exact partner-surface declaration.');}
  else{const n=c.reduction==='centroid'?1:c.vertices.length;if(key(Object.keys(d??{}).sort())!==key(['normals','space'])||d.space!==c.target.space||!Array.isArray(d.normals)||d.normals.length!==n||d.normals.some(v=>!Array.isArray(v)||v.length!==3||v.some(x=>typeof x!=='number'||!Number.isFinite(x))||Math.abs(Math.hypot(...v)-1)>1e-8))throw Error('Author one unit world/object target normal per contact point.');}
 }return clone(value);
}
export function createSurfaceExportEditor({document=globalThis.document,api,post,download=saveJSON}={}){
 const el=n=>document.getElementById('surfaceExport'+n);let bound=null,serial=0,busy=false;
 const status=x=>{el('Status').textContent=x;};const guard=fn=>async()=>{try{await fn();}catch(e){status(e.message);}};
 function options(name,values){const chosen=el(name).value;el(name).replaceChildren(...values.map(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;return o;}));if(values.includes(chosen))el(name).value=chosen;}
 function clear(){bound=null;serial++;el('SourceInfo').replaceChildren();}
 async function refresh(){const kind=el('Kind').value,token=++serial;const sources=await api(kind==='game'?'/api/native-scene-game-jobs':'/api/native-scene-jobs'),results=await api('/api/surface-export-jobs');if(token!==serial||kind!==el('Kind').value)throw Error('Source kind changed; refresh again.');options('Source',sources.jobs.filter(j=>j.status==='complete').map(j=>j.id));options('Jobs',results.jobs.map(j=>j.id));clear();status('Bind a completed engine package to its exact scene and inherited normal intent.');}
 async function bind(){const kind=el('Kind').value,id=el('Source').value,token=++serial;if(!job(id))throw Error('Choose a completed engine package.');bound=null;
  const m=await api(`/api/surface-export-source?kind=${encodeURIComponent(kind)}&id=${encodeURIComponent(id)}`);
  if(token!==serial||kind!==el('Kind').value||id!==el('Source').value)throw Error('Source selection changed while binding.');
  if(m.schema!=='strep-studio-surface-export-source-v1'||m.source?.kind!==kind||m.source?.job!==id||!hash(m.source.result_sha256)||!hash(m.normal_origins_sha256)||!hash(m.package_sha256)||!hash(m.contacts_sha256)||!hash(m.portable_scene_sha256)||!m.scene?.actors||!Array.isArray(m.scene.contacts)||!Array.isArray(m.normal_origins)||typeof m.scene_conditions_pass!=='boolean'||m.root_event_tracks_included!==(kind==='game')||m.quality_approved!==false||m.release_approved!==false)throw Error('Exact source scene/package metadata required.');
  for(const a of Object.values(m.scene.actors))if(!hash(a.sha256)||!Number.isInteger(a.animation_index)||a.animation_index<0)throw Error('Complete selected actor/clip metadata required.');
  bound=clone(m);el('Policy').value=JSON.stringify(policyFor(m),null,2);el('Revise').checked=false;el('Revise').disabled=!m.normal_origins.length;el('Notes').value='';
  const p=document.createElement('p');p.textContent=`${kind} ${id} · ${m.scene.duration_s}s · ${Object.keys(m.scene.actors).length} characters · ${m.scene.contacts.length} contacts · scene checks ${m.scene_conditions_pass?'pass':'fail'} · ${m.normal_origins.length} transfer origins. ${m.inherited_surface?'Inherited normals loaded.':m.normal_origins.length?'Changed contact scope requires explicit separate normal intent.':'Author target normals before checking.'}`;el('SourceInfo').replaceChildren(p);status(p.textContent);
 }
 function request(){if(!bound||bound.source.kind!==el('Kind').value||bound.source.job!==el('Source').value)throw Error('Bind the selected engine package first.');
  const surface=validatePolicy(JSON.parse(el('Policy').value),bound.scene),changed=bound.normal_origins.length&&key(surface)!==key(bound.inherited_surface);
  let revision=null;if(changed){const notes=el('Notes').value.trim();if(!el('Revise').checked||!notes||notes.length>1500)throw Error('Record explicit separate normal intent and its reason; inherited constraints cannot silently change.');revision={notes};}else if(el('Revise').checked)throw Error('Unchanged/fresh normals do not need an inherited-intent revision.');
  return {schema:'strep-studio-surface-export-v1',source:clone(bound.source),surface,normal_origins_sha256:bound.normal_origins_sha256,normal_revision:revision};
 }
 el('Kind').onchange=clear;el('Source').onchange=clear;el('Refresh').onclick=guard(refresh);el('Bind').onclick=guard(bind);el('Save').onclick=guard(()=>download(request()));
 el('Build').onclick=guard(async()=>{if(busy)throw Error('Wait for this submission.');const payload=request(),before=bound;busy=true;el('Build').disabled=true;
  try{const m=await api(`/api/surface-export-source?kind=${payload.source.kind}&id=${encodeURIComponent(payload.source.job)}`);if(bound!==before||key(m)!==key(before)||key(request())!==key(payload))throw Error('Source package, normals or revision changed; bind again.');const result=await post('/api/surface-export-assets',payload);if(!job(result.id))throw Error('Invalid surface export receipt.');const jobs=await api('/api/surface-export-jobs');options('Jobs',jobs.jobs.map(j=>j.id));el('Jobs').value=result.id;status('Complete imported surface replay started. Review failures or the separate checked package; originals remain selected.');}finally{busy=false;el('Build').disabled=false;}
 });
 el('Review').onclick=guard(async()=>{const id=el('Jobs').value,token=++serial;if(!job(id))throw Error('Choose a surface export result.');el('Results').replaceChildren();
  const value=await api(`/api/surface-export-review?id=${encodeURIComponent(id)}`);if(token!==serial||value.id!==id||id!==el('Jobs').value)throw Error('Surface export selection changed.');const files=checkedDownloads(value),p=document.createElement('p');
  p.textContent=value.status==='complete'?`Scene ${value.scene_conditions_pass?'pass':'fail'} · points ${value.point_conditions_pass?'pass':'fail'} · surfaces ${value.surface_conditions_pass?'pass':'fail'} · root/events ${value.root_event_conditions_pass?'pass':'fail'}. ${value.checked_package_available?'Separate checked ZIP available.':'No checked package: failed conditions retained.'} Human motion/transition review remains required.`:`${value.status}: ${value.stage||value.error||'waiting'}`;el('Results').append(p);
  for(const d of files){const a=document.createElement('a');a.className='btn';a.href=d.url;a.download='';a.textContent=d.label;el('Results').append(a);}status(p.textContent);
 });
 return {refresh,bind,request};
}
function saveJSON(value){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'})),a=globalThis.document.createElement('a');a.href=url;a.download='surface-export-request.json';a.click();URL.revokeObjectURL(url);}
