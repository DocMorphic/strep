const clone=x=>structuredClone(x);
const key=x=>JSON.stringify(x,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
const hash=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
const ref=x=>Array.isArray(x)&&x.length===3&&x.every(v=>Number.isInteger(v)&&v>=0);
const schema='strep-studio-native-scene-transfer-v1';
const namespace='native-scene-transfer-jobs';
const names=new Set(['result.json','comparison.json','source-scene.json','correspondence.json','surface-conditions.json','calibration-request.json','candidate.zip','scene.json','stage-draft.json','surface-audit.json','geometry-audit.json','motion-bounds.json']);
export function checkedDownloads(review){
 if(typeof review?.id!=='string'||!/^[A-Za-z0-9_-]{1,100}$/.test(review.id)||!Array.isArray(review.downloads))throw Error('Invalid scene transfer downloads.');
 const seen=new Set();return review.downloads.map(d=>{
  if(typeof d.label!=='string'||(!names.has(d.label)&&!/^actors\/actor-[0-7]\.glb$/.test(d.label))||seen.has(d.label)||!hash(d.sha256)||d.url!==`/files/${namespace}/${review.id}/${d.label}`)throw Error('Source-bound scene transfer download changed.');
  seen.add(d.label);return clone(d);
 });
}
export function stagedScene(review){
 if(review?.status!=='complete'||review.staging_conditions_pass!==true||review.original_selected!==true||review.source_bytes_unchanged!==true||!hash(review.result_sha256)||
    ['engine_playback_verified','human_reviewed','anatomical_reviewed','quality_approved','release_approved','continuous_collision_certified','studio_selection_changed'].some(k=>review[k]!==false)||
    ['candidate_contact_samples_pass','source_rates_pass','joint_displacement_pass','surface_common_clock_pass','surface_contact_samples_pass','geometry_samples_pass'].some(k=>review.checks?.[k]!==true))throw Error('All recorded native transfer conditions must pass before staging a new draft.');
 const files=checkedDownloads(review),request=review.authoring_request;
 if(request?.schema!==schema||!request.draft?.scene||!request.transfers||!review.stage_draft?.scene)throw Error('Completed source-bound scene transfer required.');
 const draft=clone(request.draft);delete draft.contact_revision;const proposed=review.stage_draft;
 if(key(Object.keys(proposed.scene.actors).sort())!==key(Object.keys(draft.scene.actors).sort())||key(Object.keys(review.actors??{}).sort())!==key(Object.keys(draft.scene.actors).sort()))throw Error('Complete scene actor population required.');
 const maps={};for(const [name,row] of Object.entries(request.transfers)){
  if(!draft.scene.actors[name]||!Array.isArray(row.vertex_map)||!row.vertex_map.length)throw Error('Complete explicit correspondence required.');
  const seen=new Set(),targets=new Set();maps[name]=new Map();
  for(const pair of row.vertex_map){if(!ref(pair.source)||!ref(pair.target)||seen.has(key(pair.source))||targets.has(key(pair.target)))throw Error('Distinct explicit vertex correspondence required.');seen.add(key(pair.source));targets.add(key(pair.target));maps[name].set(key(pair.source),pair.target);}
 }
 const used=Object.fromEntries(Object.keys(maps).map(n=>[n,new Set()]));
 const mapped=(name,refs)=>refs.map(r=>{if(!maps[name])return r;used[name].add(key(r));const v=maps[name].get(key(r));if(!v)throw Error('Missing source or incoming partner correspondence.');return clone(v);});
 for(const c of draft.scene.contacts){c.vertices=mapped(c.actor,c.vertices);if(c.target.space==='actor')c.target.vertices=mapped(c.target.actor,c.target.vertices);}
 for(const name of Object.keys(maps))if(used[name].size!==maps[name].size)throw Error('Extra correspondence is not part of scene contacts.');
 for(const [i,[name,a]] of Object.entries(draft.scene.actors).entries()){
  const candidate=proposed.scene.actors[name],binding=review.actors[name],url=`/files/${namespace}/${review.id}/actors/actor-${i}.glb`;
  if(candidate.glb!==(maps[name]?url:a.glb)||!hash(candidate.sha256)||!Number.isInteger(candidate.animation_index)||candidate.animation_index<0||!files.some(d=>d.url===url&&d.sha256===candidate.sha256)||
     binding.original_sha256!==a.sha256||binding.candidate_sha256!==candidate.sha256||binding.candidate_url!==url||binding.animation_index!==candidate.animation_index||
     (!maps[name]&&(candidate.sha256!==a.sha256||candidate.animation_index!==a.animation_index)))throw Error('Complete candidate asset/clip bindings required.');
  Object.assign(a,{glb:candidate.glb,sha256:candidate.sha256,animation_index:candidate.animation_index});
 }
 if(key(draft)!==key(proposed))throw Error('Staged scene changes protected placement, contacts, geometry, targets or timing.');
 return draft;
}
export function createNativeSceneTransferEditor({document=globalThis.document,api,post,getDraft,setDraft,getPatch,download=saveJSON}={}){
 const el=n=>document.getElementById('nativeSceneTransfer'+n);let stamp=null,selections={},loaded=null,rows=[],roles=[],serial=0,busy=false,review=null;
 const status=x=>{el('Status').textContent=x;};const guard=fn=>async()=>{try{await fn();}catch(e){status(e.message);}};
 function options(name,values){const chosen=el(name).value;el(name).replaceChildren(...values.map(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;return o;}));if(values.includes(chosen))el(name).value=chosen;}
 function reset(){loaded=null;rows=[];roles=[];el('Vertices').replaceChildren();el('Roles').replaceChildren();}
 function current(){const draft=clone(getDraft());if(stamp!==key(draft))throw Error('Scene changed; load the current scene and transfers again.');return draft;}
 function selectedList(){el('Selections').replaceChildren(...Object.entries(selections).map(([name,row])=>{const p=document.createElement('p');p.textContent=`${name}: ${row.transfer.job} · ${row.transfer.vertex_map.length} explicit mesh correspondences`;return p;}));}
 async function refresh(){
  const draft=clone(getDraft()),before=key(draft),token=++serial;
  const list=await api('/api/native-transfer-jobs'),jobs=await api('/api/native-scene-transfer-jobs');
  if(token!==serial||before!==key(getDraft()))throw Error('Scene changed while loading transfers.');
  if(stamp!==before){selections={};el('Normals').value=JSON.stringify(Object.fromEntries(draft.scene.contacts.map(c=>[c.id,{target_normal:c.target.space==='actor'?{space:'partner-surface'}:{space:c.target.space,normals:null}}])),null,2);}
  stamp=before;reset();review=null;el('Stage').disabled=true;options('Actor',Object.keys(draft.scene.actors));options('Transfer',list.jobs.filter(j=>j.status==='complete').map(j=>j.id));options('Jobs',jobs.jobs.map(j=>j.id));selectedList();status('Choose the completed transfer for a scene actor, then load its used mesh vertices.');
 }
 async function load(){
  const draft=current(),actor=el('Actor').value,job=el('Transfer').value,before=key(draft),token=++serial;
  if(!job||!draft.scene.actors[actor])throw Error('Choose a scene actor and completed character transfer.');
  const m=await api(`/api/native-transfer-review?id=${encodeURIComponent(job)}`);
  if(m.id!==job||m.status!=='complete'||!hash(m.result_sha256)||m.sampled_runtime_conditions_pass!==true)throw Error('Completed playback-checked transfer required.');
  const response=await post('/api/native-scene-transfer-catalog',{draft,transfers:{[actor]:{job,result_sha256:m.result_sha256}}});
  if(token!==serial||before!==key(getDraft())||el('Actor').value!==actor||el('Transfer').value!==job)throw Error('Actor, scene or transfer changed while loading correspondence.');
  const c=response?.actors?.[actor];if(response.schema!=='strep-studio-native-scene-transfer-catalog-v1'||key(Object.keys(response.actors))!==key([actor])||c.source_sha256!==draft.scene.actors[actor].sha256||c.source_animation_index!==draft.scene.actors[actor].animation_index||c.result_sha256!==m.result_sha256||c.job!==job||!hash(c.target_sha256)||!Array.isArray(c.required_vertices)||!c.required_vertices.length||c.required_vertices.some(r=>!ref(r))||new Set(c.required_vertices.map(key)).size!==c.required_vertices.length||!Array.isArray(c.target_roles)||c.target_roles.some(r=>typeof r!=='string')||response.duration_s!==draft.scene.duration_s)throw Error('Source-bound contact catalog changed.');
  reset();loaded={actor,job,result_sha256:m.result_sha256,catalog:c};const saved=selections[actor]?.transfer.job===job?selections[actor]:null;
  for(const source of c.required_vertices){const row=document.createElement('label');row.className='small';row.style.display='block';const input=document.createElement('input');input.value=JSON.stringify(saved?.transfer.vertex_map.find(p=>key(p.source)===key(source))?.target??null);row.append(document.createTextNode(`${JSON.stringify(source)} → `),input);el('Vertices').append(row);rows.push({source,input});}
  for(const role of c.target_roles){const row=document.createElement('label');row.className='small';row.style.display='block';const box=document.createElement('input');box.type='checkbox';const input=document.createElement('input');input.type='number';input.min='0.000001';input.max='45';input.step='any';input.value=saved?.bounds.role_rotations_degrees[role]??15;box.checked=saved?.bounds.role_rotations_degrees[role]!==undefined;input.disabled=!box.checked;box.onchange=()=>{input.disabled=!box.checked;};row.append(box,document.createTextNode(` ${role} (degrees) `),input);el('Roles').append(row);roles.push({role,box,input});}
  el('Root').value=(saved?.bounds.maximum_root_offset_m??0)*1000;el('Displacement').value=(saved?.bounds.maximum_joint_displacement_m??.02)*1000;status('Enter every target vertex and choose explicit whole-clip bounds.');
 }
 function saveActor(){
  current();if(!loaded||loaded.actor!==el('Actor').value||loaded.job!==el('Transfer').value)throw Error('Load the selected actor/transfer correspondence first.');
  const vertex_map=rows.map(({source,input})=>({source:clone(source),target:JSON.parse(input.value)}));if(vertex_map.some(p=>!ref(p.target))||new Set(vertex_map.map(p=>key(p.target))).size!==vertex_map.length)throw Error('Enter distinct target mesh references for every required source vertex.');
  const role_rotations_degrees=Object.fromEntries(roles.filter(r=>r.box.checked).map(r=>[r.role,Number(r.input.value)])),root=Number(el('Root').value)/1000,displacement=Number(el('Displacement').value)/1000;
  if(!Number.isFinite(root)||root<0||root>.22||!Number.isFinite(displacement)||displacement<1e-6||displacement>.22||Object.values(role_rotations_degrees).some(v=>!Number.isFinite(v)||v<1e-6||v>45)||Object.keys(role_rotations_degrees).length>16||(!Object.keys(role_rotations_degrees).length&&root===0))throw Error('Choose existing rotation roles or a root offset and finite bounds within the displayed limits.');
  selections[loaded.actor]={transfer:{job:loaded.job,result_sha256:loaded.result_sha256,vertex_map},bounds:{role_rotations_degrees,maximum_root_offset_m:root,maximum_joint_displacement_m:displacement}};selectedList();status('Character correspondence and calibration permissions saved.');
 }
 function number(name,min,max,integer=false){const raw=String(el(name).value).trim(),v=Number(raw);if(!raw||!Number.isFinite(v)||v<min||v>max||(integer&&!Number.isInteger(v)))throw Error(`Choose a finite ${name} within its displayed limits.`);return v;}
 function request(){
  const draft=current();if(!Object.keys(selections).length)throw Error('Save correspondence and bounds for at least one character.');
  const actors=Object.fromEntries(Object.entries(selections).map(([n,s])=>[n,clone(s.bounds)]));if(Object.values(actors).reduce((sum,a)=>sum+3*(Object.keys(a.role_rotations_degrees).length+(a.maximum_root_offset_m>0)),0)>96)throw Error('At most 96 calibration controls.');
  const contacts=JSON.parse(el('Normals').value);if(key(Object.keys(contacts).sort())!==key(draft.scene.contacts.map(c=>c.id).sort()))throw Error('Authored normals must cover every scene contact exactly.');
  for(const c of draft.scene.contacts){const d=contacts[c.id]?.target_normal;if(c.target.space==='actor'){if(key(d)!==key({space:'partner-surface'}))throw Error('Use the exact partner-surface declaration.');}else{const count=c.reduction==='centroid'?1:c.vertices.length;if(d?.space!==c.target.space||!Array.isArray(d.normals)||d.normals.length!==count||d.normals.some(v=>!Array.isArray(v)||v.length!==3||v.some(n=>typeof n!=='number'||!Number.isFinite(n))||Math.abs(Math.hypot(...v)-1)>1e-8))throw Error('Author one unit target normal per contact point in world/object coordinates.');}}
  const search={evaluations:number('Evaluations',1,300,true),calls:number('Calls',1,10000,true),seconds:number('Seconds',1,3600),starts:number('Starts',1,7,true)};if(search.starts>search.evaluations)throw Error('Starts must fit the evaluation budget.');
  return {schema,draft,transfers:Object.fromEntries(Object.entries(selections).map(([n,s])=>[n,clone(s.transfer)])),calibration:{actors,surface:{limits:{maximum_opposition_error_degrees:number('Angle',0,90),backface_allowance_m:number('Backface',0,5)/1000,minimum_normal_area_m2:number('Area',1e-16,1e-4),minimum_normal_coherence:number('Coherence',1e-6,1)},maximum_actor_pose_queries:number('Queries',1,20000,true),contacts},search}};
 }
 el('Refresh').onclick=guard(refresh);el('Load').onclick=guard(load);el('Actor').onchange=reset;el('Transfer').onchange=reset;el('SaveActor').onclick=guard(saveActor);
 el('Pick').onclick=guard(()=>{current();if(!loaded)throw Error('Load correspondence first.');const patch=getPatch();if(patch?.glb_sha256!==loaded.catalog.target_sha256||!Array.isArray(patch.vertices)||patch.vertices.length!==rows.length||patch.vertices.some(r=>!ref(r))||new Set(patch.vertices.map(key)).size!==rows.length)throw Error('Pick an exact target-asset patch with the same complete vertex count.');rows.forEach((r,i)=>{r.input.value=JSON.stringify(patch.vertices[i]);});status('Picked references copied in their displayed order. Verify the correspondence before saving.');});
 el('Remove').onclick=guard(()=>{delete selections[el('Actor').value];selectedList();reset();});el('Save').onclick=guard(()=>download(request()));
 el('Build').onclick=guard(async()=>{if(busy)throw Error('Wait for this submission.');const payload=request();busy=true;el('Build').disabled=true;
  try{const job=await post('/api/native-scene-transfer-assets',payload);if(!job?.id||!/^[A-Za-z0-9_-]{1,100}$/.test(job.id))throw Error('Invalid new scene transfer receipt.');const list=await api('/api/native-scene-transfer-jobs');options('Jobs',list.jobs.map(j=>j.id));el('Jobs').value=job.id;status('Separate scene transfer started. Refresh jobs and review all conditions before staging.');}finally{busy=false;el('Build').disabled=false;}
 });
 el('Review').onclick=guard(async()=>{const id=el('Jobs').value;if(!id)throw Error('Choose a scene transfer job.');review=null;el('Stage').disabled=true;el('Results').replaceChildren();const token=++serial;
  const value=await api(`/api/native-scene-transfer-review?id=${encodeURIComponent(id)}`);if(token!==serial||value.id!==id||el('Jobs').value!==id)throw Error('Scene transfer selection changed.');
  const files=checkedDownloads(value),p=document.createElement('p');p.textContent=value.status==='complete'?`${value.calibration_status}. ${Object.entries(value.checks??{}).map(([k,v])=>`${k}: ${v===true?'pass':'fail'}`).join(' · ')}. Engine and quality review still required.`:`${value.status}: ${value.stage||value.error||'waiting'}`;el('Results').append(p);
  for(const d of files){const a=document.createElement('a');a.className='btn';a.href=d.url;a.download='';a.textContent=d.label;el('Results').append(a);}
  review=value;try{stagedScene(value);if(key(getDraft())===key(value.authoring_request.draft))el('Stage').disabled=false;}catch{}status(p.textContent);
 });
 el('Stage').onclick=guard(async()=>{const before=review,sceneBefore=key(getDraft());if(!before||el('Jobs').value!==before.id||sceneBefore!==key(before.authoring_request?.draft))throw Error('Review the selected result against its original scene draft first.');
  const updated=await api(`/api/native-scene-transfer-review?id=${encodeURIComponent(before.id)}`);
  if(review!==before||key(updated)!==key(before)||sceneBefore!==key(getDraft())||el('Jobs').value!==before.id)throw Error('Scene or result changed; review it again.');
  setDraft(stagedScene(updated));stamp=null;reset();selections={};el('Stage').disabled=true;status('All candidate clips staged in a separate new rig/clip epoch. Build Scene contacts assets for engine checks, then review motion and transition endpoints.');
 });
 return {refresh,load,request};
}
function saveJSON(value){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'})),a=globalThis.document.createElement('a');a.href=url;a.download='scene-transfer-request.json';a.click();URL.revokeObjectURL(url);}
