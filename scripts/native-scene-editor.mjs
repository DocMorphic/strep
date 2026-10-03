const clone=value=>structuredClone(value);
const identity=()=>[0,0,0,1];
export function triplet(text,count=3){const raw=String(text).trim(),tokens=raw.split(/[\s,]+/);const values=tokens.map(Number);if(!raw||tokens.some(t=>!t)||values.length!==count||!values.every(Number.isFinite))throw Error(`Enter ${count} finite numbers.`);return values;}
export function contactFromPatch(draft,actor,patch,{id,target,mode,start,end,position,speed}){
 const source=draft.scene.actors[actor];if(!source||patch.glb_sha256!==source.sha256)throw Error('Pick a patch on this character clip.');
 if(!Array.isArray(patch.vertices)||!patch.vertices.length)throw Error('Pick a mesh patch first.');
 return {id,actor,vertices:clone(patch.vertices),reduction:'centroid',target:clone(target),mode,
  interval_s:mode==='touch'?[start,start]:[start,end],limits:mode==='touch'?{position_m:position}:{position_m:position,relative_speed_m_s:speed}};
}
export function emptyDraft(){return {schema:'strep-studio-native-scene-v1',scene:{schema:'strep-native-scene-contacts-v1',duration_s:null,actors:{},objects:{},contacts:[]},
 geometry:{clock:{mode:'native-and-frame-populations',times_s:[]},limits:{penetration_m:.005,depth_resolution_m:1e-6,surface_tolerance_m:1e-8},planes:{}},object_edit:null};}
export function createNativeSceneEditor({document=globalThis.document,api,post,getContext,getPatch,download=defaultDownload}={}){
 const el=name=>document.getElementById('nativeScene'+name);let draft=emptyDraft(),partner=null,busy=false;
 const status=text=>{el('Status').textContent=text;};
 const number=name=>{const text=el(name).value;if(String(text).trim()==='')throw Error('Fill in '+name);const value=Number(text);if(!Number.isFinite(value))throw Error('Enter a finite '+name);return value;};
 const metres=(name,original)=>{const value=number(name);return original!==undefined&&value===original*1000?original:value/1000;};
 const guard=fn=>async()=>{try{await fn();}catch(error){status(error.message);}};
 function options(name,values){const chosen=el(name).value;el(name).replaceChildren(...values.map(value=>{const option=document.createElement('option');option.value=value;option.textContent=value;return option;}));if(values.includes(chosen))el(name).value=chosen;}
 function targetOptions(){options('Target',el('TargetType').value==='actor'?Object.keys(draft.scene.actors):Object.keys(draft.scene.objects));}
 function rows(name,values,remove){el(name).replaceChildren(...values.map(([id,label])=>{const row=document.createElement('p');row.textContent=label+' ';const button=document.createElement('button');button.className='btn';button.textContent='Remove';button.onclick=()=>{remove(id);partner=null;draw();};row.append(button);return row;}));}
 function draw(){
  rows('Actors',Object.entries(draft.scene.actors).map(([name,a])=>[name,`${name} · ${a.placement.translation_m.join(', ')} m`]),name=>{if(draft.scene.contacts.some(c=>c.actor===name||c.target.actor===name)){status('Remove this character’s contacts first.');return;}delete draft.scene.actors[name];});
  rows('Objects',Object.entries(draft.scene.objects).map(([name,o])=>[name,`${name} · ${o.geometry.shape} · ${o.keyframes.length} pose key(s)`]),name=>{if(draft.scene.contacts.some(c=>c.target.object===name)){status('Remove this object’s contacts first.');return;}delete draft.scene.objects[name];});
  rows('Contacts',draft.scene.contacts.map(c=>[c.id,`${c.id} · ${c.actor} → ${c.target.object||c.target.actor||'world'} · ${c.mode} ${c.interval_s.join('–')} s`]),id=>{draft.scene.contacts=draft.scene.contacts.filter(c=>c.id!==id);});
  options('ContactActor',Object.keys(draft.scene.actors));options('FitObject',Object.keys(draft.scene.objects));targetOptions();
  const holds=draft.scene.contacts.filter(c=>c.mode==='hold'&&c.target.space==='object').map(c=>c.id);options('FirstGrip',holds);options('SecondGrip',holds);
  el('Duration').textContent=draft.scene.duration_s===null?'No character clips added.':`Shared duration: ${draft.scene.duration_s} seconds. Existing animation timing is preserved.`;
 }
 function editable(){const value=clone(draft);value.geometry.limits.penetration_m=metres('DepthLimit',draft.geometry.limits.penetration_m);
  if(!el('Floor').disabled){if(el('Floor').checked)value.geometry.planes.floor={normal_world:[0,1,0],offset_m:number('FloorHeight')};else delete value.geometry.planes.floor;}
  value.object_edit=el('Fit').checked?{schema:'strep-native-object-hold-fit-v1',object:el('FitObject').value,
   contact_ids:[el('FirstGrip').value,el('SecondGrip').value],edit_window_s:triplet(el('EditWindow').value,2),maximum_translation_m:metres('Translation',draft.object_edit?.maximum_translation_m),
   maximum_rotation_degrees:number('Rotation'),maximum_keys:number('Keys')}:null;return value;}
 function bind(value){if(value?.schema!=='strep-studio-native-scene-v1'||!value.scene?.actors||!value.scene?.objects||!Array.isArray(value.scene.contacts)||!value.geometry?.planes)throw Error('Open a saved native scene draft.');
  draft=clone(value);partner=null;el('DepthLimit').value=draft.geometry.limits.penetration_m*1000;
  const floor=draft.geometry.planes.floor;el('Floor').disabled=!!floor&&JSON.stringify(floor.normal_world)!=='[0,1,0]';el('Floor').checked=!!floor;el('FloorHeight').value=floor?.offset_m??0;
  el('Fit').checked=!!draft.object_edit;draw();
  if(draft.object_edit){const e=draft.object_edit;el('FitObject').value=e.object;el('FirstGrip').value=e.contact_ids[0];el('SecondGrip').value=e.contact_ids[1];el('EditWindow').value=e.edit_window_s.join(', ');el('Translation').value=e.maximum_translation_m*1000;el('Rotation').value=e.maximum_rotation_degrees;el('Keys').value=e.maximum_keys;}
 }
 el('AddActor').onclick=guard(async()=>{const context=getContext();if(!context.job)throw Error('Select a completed character clip.');const job=context.job.id,variant=context.variant;
  const m=await api(`/api/native-scene-actor?job=${encodeURIComponent(job)}&variant=${encodeURIComponent(variant)}`);
  const current=getContext();if(current.job?.id!==job||current.variant!==variant)throw Error('Character selection changed; add the intended clip again.');
  const name=el('ActorName').value.trim();if(!/^[A-Za-z0-9_-]{1,64}$/.test(name)||draft.scene.actors[name])throw Error('Choose a new character name.');
  if(draft.scene.duration_s!==null&&draft.scene.duration_s!==m.duration_s)throw Error('Clips have different durations. Retime them explicitly first.');
  const p=triplet(el('ActorPosition').value);if(draft.scene.duration_s===null){draft.scene.duration_s=m.duration_s;draft.geometry.clock.times_s=[0,m.duration_s];el('End').value=m.duration_s;el('EditWindow').value=`0, ${m.duration_s}`;}
  draft.scene.actors[name]={glb:m.source_url,sha256:m.glb_sha256,animation_index:m.animation_index,placement:{translation_m:p,rotation_xyzw:identity()}};draw();status(`Added ${name}: ${m.label}.`);
 });
 el('AddObject').onclick=guard(()=>{const name=el('ObjectName').value.trim(),shape=el('Shape').value;if(!/^[A-Za-z0-9_-]{1,64}$/.test(name)||draft.scene.objects[name])throw Error('Choose a new object name.');
  const values=triplet(el('Dimensions').value,shape==='box'?3:shape==='sphere'?1:2);if(values.some(v=>v<=0))throw Error('Object dimensions must be positive.');
  const geometry={schema:'strep-object-geometry-v1',shape,...(shape==='box'?{size_m:values}:shape==='sphere'?{radius_m:values[0]}:{radius_m:values[0],height_m:values[1]})};
  draft.scene.objects[name]={geometry,keyframes:[{time_s:0,translation_m:triplet(el('ObjectPosition').value),rotation_xyzw:identity()}]};draw();status('Added an explicitly placed static object.');
 });
 el('PartnerPatch').onclick=guard(()=>{const actor=el('Target').value,source=draft.scene.actors[actor],patch=getPatch();if(el('TargetType').value!=='actor'||!source||source.sha256!==patch.glb_sha256)throw Error('Select the target partner and pick its mesh patch.');partner={actor,...clone(patch)};status('Partner target patch saved for this draft.');});
 el('AddContact').onclick=guard(()=>{const type=el('TargetType').value;let target;
  if(type==='actor'){if(!partner||partner.actor!==el('Target').value||draft.scene.actors[partner.actor]?.sha256!==partner.glb_sha256)throw Error('Choose and save the partner target patch first.');target={space:'actor',actor:partner.actor,vertices:clone(partner.vertices),reduction:'centroid'};}
  else target=type==='world'?{space:'world',points_m:[triplet(el('Point').value)]}:{space:'object',object:el('Target').value,points_m:[triplet(el('Point').value)]};
  const id=el('ContactName').value.trim();if(draft.scene.contacts.some(c=>c.id===id))throw Error('Choose a new contact name.');
  const mode=el('Mode').value,start=number('Start');
  draft.scene.contacts.push(contactFromPatch(draft,el('ContactActor').value,getPatch(),{id,target,mode,start,end:mode==='touch'?start:number('End'),position:number('ContactLimit')/1000,speed:mode==='touch'?null:number('SpeedLimit')/1000}));draw();status('Explicit contact added. All selected vertices are preserved.');
 });
 el('TargetType').onchange=targetOptions;el('Shape').onchange=()=>{el('Dimensions').value=el('Shape').value==='box'?'0.4, 0.4, 0.4':el('Shape').value==='sphere'?'0.2':'0.2, 0.4';};
 el('Mode').onchange=()=>{el('End').disabled=el('Mode').value==='touch';el('SpeedLimit').disabled=el('Mode').value==='touch';};
 el('Save').onclick=guard(()=>download(editable()));
 el('Import').onchange=guard(async()=>{const file=el('Import').files?.[0];if(!file)return;if(file.size>1048576)throw Error('Scene draft exceeds 1 MiB.');bind(JSON.parse(await file.text()));status('Draft loaded. Source hashes will be checked before building.');});
 async function refresh(){const data=await api('/api/native-scene-jobs');const chosen=el('Jobs').value;options('Jobs',data.jobs.map(j=>j.id));if(data.jobs.some(j=>j.id===chosen))el('Jobs').value=chosen;return data;}
 el('Refresh').onclick=guard(refresh);
 el('Build').onclick=guard(async()=>{if(busy)throw Error('Wait for this request.');busy=true;el('Build').disabled=true;try{const job=await post('/api/native-scene-assets',editable());await refresh();el('Jobs').value=job.id;status('Scene job started. Refresh its results to follow the saved stages.');}finally{busy=false;el('Build').disabled=false;}});
 el('Review').onclick=guard(async()=>{const id=el('Jobs').value;if(!id)throw Error('Select a scene asset job.');const r=await api(`/api/native-scene-review?id=${encodeURIComponent(id)}`);el('Results').replaceChildren();
  const text=document.createElement('p');text.textContent=r.status==='complete'?`Recorded sampled conditions: ${r.sampled_conditions_pass?'pass':'fail'} at ${r.samples} times. Original contacts: ${r.source_contacts_pass?'pass':'fail'}. Motion-quality, physics and runtime approval remain open.`:`${r.status}: ${r.stage||r.error||'waiting'} · ${r.completed_stages?.length??0} completed stage(s).`;el('Results').append(text);
  for(const entry of r.downloads||[]){const a=document.createElement('a');a.className='btn';a.href=entry.url;a.download='';a.textContent=entry.label;el('Results').append(a);}status(r.status==='complete'?'Recorded results and source-bound assets loaded.':text.textContent);
 });
 draw();return {bind,snapshot:editable,refresh};
}
function defaultDownload(value){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'})),a=globalThis.document.createElement('a');a.href=url;a.download='native-scene-draft.json';a.click();URL.revokeObjectURL(url);}
