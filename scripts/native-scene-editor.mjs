import {createMaterialRegionAuthor} from './material-region-author.mjs';
import {createMaterialPatchLoader} from './material-patch-loader.mjs';
const clone=value=>structuredClone(value);
const identity=()=>[0,0,0,1];
const key=value=>JSON.stringify(value,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
function endpointInspection(value,contact){
 const times=[...new Set(contact.interval_s)],count=contact.reduction==='centroid'?1:contact.vertices.length;
 const positions=a=>Array.isArray(a)&&a.length===times.length&&a.every(row=>Array.isArray(row)&&row.length===count&&row.every(v=>Array.isArray(v)&&v.length===3&&v.every(n=>typeof n==='number'&&Number.isFinite(n))));
 return key(value?.times_s)===key(times)&&positions(value?.source_world_m)&&positions(value?.target_world_m)&&Array.isArray(value?.separation_m)&&value.separation_m.length===times.length&&value.separation_m.every(row=>Array.isArray(row)&&row.length===count&&row.every(n=>typeof n==='number'&&Number.isFinite(n)&&n>=0));
}
function explicitPatch(patch,actor,reduction){
 if(!actor||patch?.glb_sha256!==actor.sha256)throw Error('Pick a patch on the contact’s selected character clip.');
 const refs=patch.vertices;
 if(!Array.isArray(refs)||!refs.length||refs.length>256||refs.some(r=>!Array.isArray(r)||r.length!==3||r.some(i=>!Number.isInteger(i)||i<0))||new Set(refs.map(key)).size!==refs.length)throw Error('Choose 1–256 distinct mesh references; larger regions are not sampled down.');
 if(!['individual','centroid'].includes(reduction))throw Error('Choose individual points or an average patch position.');
 return {glb_sha256:patch.glb_sha256,vertices:clone(refs),reduction};
}
export function revisionDraft(value,edit){
 const baseline=clone(value.contact_revision?.baseline??value);delete baseline.contact_revision;
 const edits=clone(value.contact_revision?.edits??[]),existing=edits.find(e=>e.id===edit.id);
 if(existing){if(edit.source!==null)existing.source=clone(edit.source);if(edit.partner!==null)existing.partner=clone(edit.partner);}
 else edits.push(clone(edit));
 const result=clone(baseline);
 for(const e of edits){const row=result.scene.contacts.find(c=>c.id===e.id);if(!row)throw Error('Choose an existing contact.');
  if(e.source!==null){const p=explicitPatch(e.source,result.scene.actors[row.actor],e.source.reduction);row.vertices=p.vertices;row.reduction=p.reduction;}
  if(e.partner!==null){if(row.target.space!=='actor')throw Error('This contact has no partner patch.');const p=explicitPatch(e.partner,result.scene.actors[row.target.actor],e.partner.reduction);row.target.vertices=p.vertices;row.target.reduction=p.reduction;}
  const count=row.reduction==='centroid'?1:row.vertices.length,target=row.target;
  const other=target.space==='actor'?(target.reduction==='centroid'?1:target.vertices.length):target.points_m.length;
  if(count!==other)throw Error('Keep one-to-one point correspondence; revise both partner sides together when needed.');
  if(key(row)===key(baseline.scene.contacts.find(c=>c.id===e.id)))throw Error('The contact patch has not changed.');
 }
 result.contact_revision={schema:'strep-native-contact-revision-v1',baseline,edits};return result;
}
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
 const el=name=>document.getElementById('nativeScene'+name);let draft=emptyDraft(),partner=null,busy=false,revisionBusy=false,revisionSource=null,revisionPartner=null,pendingRevision=null,regionLoader=null,regionAuthor=null;
 const status=text=>{el('Status').textContent=text;};
 const number=name=>{const text=el(name).value;if(String(text).trim()==='')throw Error('Fill in '+name);const value=Number(text);if(!Number.isFinite(value))throw Error('Enter a finite '+name);return value;};
 const metres=(name,original)=>{const value=number(name);return original!==undefined&&value===original*1000?original:value/1000;};
 const guard=fn=>async()=>{try{await fn();}catch(error){status(error.message);}};
 function options(name,values){const chosen=el(name).value;el(name).replaceChildren(...values.map(value=>{const option=document.createElement('option');option.value=value;option.textContent=value;return option;}));if(values.includes(chosen))el(name).value=chosen;}
 function targetOptions(){options('Target',el('TargetType').value==='actor'?Object.keys(draft.scene.actors):Object.keys(draft.scene.objects));}
 function ordinary(){if(draft.contact_revision)throw Error('Restore the original draft before changing other authoring fields.');}
 function rows(name,values,remove){el(name).replaceChildren(...values.map(([id,label])=>{const row=document.createElement('p');row.textContent=label+' ';const button=document.createElement('button');button.className='btn';button.textContent='Remove';button.disabled=!!draft.contact_revision;button.onclick=()=>{if(draft.contact_revision){status('Restore the original draft before removing authoring conditions.');return;}remove(id);partner=null;draw();};row.append(button);return row;}));}
 function resetRevision(){regionAuthor?.clear();regionLoader?.clear();revisionSource=null;revisionPartner=null;pendingRevision=null;el('RevisionApply').disabled=true;el('RevisionResults').replaceChildren();
  const row=draft.scene.contacts.find(c=>c.id===el('RevisionContact').value);el('RevisionSourceReduction').value=row?.reduction??'centroid';el('RevisionPartnerReduction').value=row?.target.reduction??'centroid';el('RevisionPartner').disabled=!row||row.target.space!=='actor';el('RevisionPartnerReduction').disabled=!row||row.target.space!=='actor';}
 function draw(){
  rows('Actors',Object.entries(draft.scene.actors).map(([name,a])=>[name,`${name} · ${a.placement.translation_m.join(', ')} m`]),name=>{if(draft.scene.contacts.some(c=>c.actor===name||c.target.actor===name)){status('Remove this character’s contacts first.');return;}delete draft.scene.actors[name];});
  rows('Objects',Object.entries(draft.scene.objects).map(([name,o])=>[name,`${name} · ${o.geometry.shape} · ${o.keyframes.length} pose key(s)`]),name=>{if(draft.scene.contacts.some(c=>c.target.object===name)){status('Remove this object’s contacts first.');return;}delete draft.scene.objects[name];});
  rows('Contacts',draft.scene.contacts.map(c=>[c.id,`${c.id} · ${c.actor} → ${c.target.object||c.target.actor||'world'} · ${c.mode} ${c.interval_s.join('–')} s`]),id=>{draft.scene.contacts=draft.scene.contacts.filter(c=>c.id!==id);});
  options('ContactActor',Object.keys(draft.scene.actors));options('FitObject',Object.keys(draft.scene.objects));targetOptions();
  options('RevisionContact',draft.scene.contacts.map(c=>c.id));resetRevision();
  for(const name of ['AddActor','AddObject','AddContact','DepthLimit','FloorHeight','Fit','FitObject','FirstGrip','SecondGrip','EditWindow','Translation','Rotation','Keys'])el(name).disabled=!!draft.contact_revision;
  el('Floor').disabled=!!draft.contact_revision||!!draft.geometry.planes.floor&&key(draft.geometry.planes.floor.normal_world)!=='[0,1,0]';el('RevisionRestore').disabled=!draft.contact_revision;
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
 el('AddActor').onclick=guard(async()=>{ordinary();const context=getContext();if(!context.job)throw Error('Select a completed character clip.');const job=context.job.id,variant=context.variant,draftBefore=key(editable());
  const m=await api(`/api/native-scene-actor?job=${encodeURIComponent(job)}&variant=${encodeURIComponent(variant)}`);
  const current=getContext();if(current.job?.id!==job||current.variant!==variant)throw Error('Character selection changed; add the intended clip again.');
  if(key(editable())!==draftBefore)throw Error('Scene draft changed; add the intended character again.');ordinary();
  const name=el('ActorName').value.trim();if(!/^[A-Za-z0-9_-]{1,64}$/.test(name)||draft.scene.actors[name])throw Error('Choose a new character name.');
  if(draft.scene.duration_s!==null&&draft.scene.duration_s!==m.duration_s)throw Error('Clips have different durations. Retime them explicitly first.');
  const p=triplet(el('ActorPosition').value);if(draft.scene.duration_s===null){draft.scene.duration_s=m.duration_s;draft.geometry.clock.times_s=[0,m.duration_s];el('End').value=m.duration_s;el('EditWindow').value=`0, ${m.duration_s}`;}
  draft.scene.actors[name]={glb:m.source_url,sha256:m.glb_sha256,animation_index:m.animation_index,placement:{translation_m:p,rotation_xyzw:identity()}};draw();status(`Added ${name}: ${m.label}.`);
 });
 el('AddObject').onclick=guard(()=>{ordinary();const name=el('ObjectName').value.trim(),shape=el('Shape').value;if(!/^[A-Za-z0-9_-]{1,64}$/.test(name)||draft.scene.objects[name])throw Error('Choose a new object name.');
  const values=triplet(el('Dimensions').value,shape==='box'?3:shape==='sphere'?1:2);if(values.some(v=>v<=0))throw Error('Object dimensions must be positive.');
  const geometry={schema:'strep-object-geometry-v1',shape,...(shape==='box'?{size_m:values}:shape==='sphere'?{radius_m:values[0]}:{radius_m:values[0],height_m:values[1]})};
  draft.scene.objects[name]={geometry,keyframes:[{time_s:0,translation_m:triplet(el('ObjectPosition').value),rotation_xyzw:identity()}]};draw();status('Added an explicitly placed static object.');
 });
 el('PartnerPatch').onclick=guard(()=>{const actor=el('Target').value,source=draft.scene.actors[actor],patch=getPatch();if(el('TargetType').value!=='actor'||!source||source.sha256!==patch.glb_sha256)throw Error('Select the target partner and pick its mesh patch.');partner={actor,...clone(patch)};status('Partner target patch saved for this draft.');});
 el('AddContact').onclick=guard(()=>{ordinary();const type=el('TargetType').value;let target;
  if(type==='actor'){if(!partner||partner.actor!==el('Target').value||draft.scene.actors[partner.actor]?.sha256!==partner.glb_sha256)throw Error('Choose and save the partner target patch first.');target={space:'actor',actor:partner.actor,vertices:clone(partner.vertices),reduction:'centroid'};}
  else target=type==='world'?{space:'world',points_m:[triplet(el('Point').value)]}:{space:'object',object:el('Target').value,points_m:[triplet(el('Point').value)]};
  const id=el('ContactName').value.trim();if(draft.scene.contacts.some(c=>c.id===id))throw Error('Choose a new contact name.');
  const mode=el('Mode').value,start=number('Start');
  draft.scene.contacts.push(contactFromPatch(draft,el('ContactActor').value,getPatch(),{id,target,mode,start,end:mode==='touch'?start:number('End'),position:number('ContactLimit')/1000,speed:mode==='touch'?null:number('SpeedLimit')/1000}));draw();status('Explicit contact added. All selected vertices are preserved.');
 });
 const revisionChoice=()=>({id:el('RevisionContact').value,
  source:revisionSource?{...clone(revisionSource),reduction:el('RevisionSourceReduction').value}:null,
  partner:revisionPartner?{...clone(revisionPartner),reduction:el('RevisionPartnerReduction').value}:null});
 function invalidateRevision(){pendingRevision=null;el('RevisionApply').disabled=true;}
 el('RevisionContact').onchange=resetRevision;
 el('RevisionSourceReduction').onchange=invalidateRevision;el('RevisionPartnerReduction').onchange=invalidateRevision;
 function stageRevisionPatch(side,patch){
  if(revisionBusy||busy)throw Error('Wait for the current request.');const row=draft.scene.contacts.find(c=>c.id===el('RevisionContact').value);if(!row)throw Error('Choose an existing contact.');
  if(side==='partner'&&row.target.space!=='actor')throw Error('This contact has no partner patch.');
  const actor=side==='source'?row.actor:row.target.actor,reduction=side==='source'?'RevisionSourceReduction':'RevisionPartnerReduction';
  const p=explicitPatch(patch,draft.scene.actors[actor],patch.reduction);
  if(side==='source')revisionSource=p;else revisionPartner=p;el(reduction).value=p.reduction;invalidateRevision();
 }
 for(const [side,button] of [['source','RevisionSource'],['partner','RevisionPartner']])el(button).onclick=guard(()=>{
  if(revisionBusy)throw Error('Wait for the contact review.');const row=draft.scene.contacts.find(c=>c.id===el('RevisionContact').value);if(!row)throw Error('Choose an existing contact.');
  if(side==='partner'&&row.target.space!=='actor')throw Error('This contact has no partner patch.');const actor=side==='source'?row.actor:row.target.actor;
  const p=explicitPatch(getPatch(),draft.scene.actors[actor],el(side==='source'?'RevisionSourceReduction':'RevisionPartnerReduction').value);
  stageRevisionPatch(side,p);regionLoader.clear();status(`Staged ${p.vertices.length} ${side} vertices for ${row.id}. Preview before applying.`);
 });
 function checkedPreview(r,payload){
  const record=r?.record,expectedActors=Object.fromEntries(Object.entries(payload.scene.actors).map(([n,a])=>[n,a.sha256]));
  if(r?.schema!=='strep-native-contact-revision-preview-v1'||r.original_selected!==true||r.animation_edited!==false||r.anatomical_review_pending!==true||[r.quality_approved,r.training_admitted,r.release_approved].some(v=>v!==false)
   ||!/^[a-f0-9]{64}$/.test(r.draft_sha256)||!/^[a-f0-9]{64}$/.test(r.baseline_sha256)||!r.implementation_sha256||!['studio_native_scene.py','native_contact_revision.py'].every(n=>/^[a-f0-9]{64}$/.test(r.implementation_sha256[n]))||Object.values(r.implementation_sha256).some(h=>!/^[a-f0-9]{64}$/.test(h))
   ||key(r.actor_sha256)!==key(expectedActors)||key(record?.actor_sha256)!==key(expectedActors)
   ||key(record?.original_contacts)!==key(payload.contact_revision.baseline.scene.contacts)||key(record?.authored_contacts)!==key(payload.scene.contacts)||key(record?.explicit_edits)!==key(payload.contact_revision.edits)
   ||record?.schema!=='strep-native-contact-revision-v1'||record?.contact_timing_and_limits_unchanged!==true||record?.other_authoring_fields_unchanged!==true||record?.original_intent_retained!==true||record?.contact_intent_revised!==true||record?.animation_edited!==false||record?.anatomical_review_pending!==true
   ||[record?.quality_approved,record?.training_admitted,record?.release_approved].some(v=>v!==false)
   ||!Array.isArray(r.changes)||key(r.changes.map(c=>c.id))!==key(payload.contact_revision.edits.map(e=>e.id))||r.changes.some(c=>key(c.original_contact)!==key(payload.contact_revision.baseline.scene.contacts.find(b=>b.id===c.id))||key(c.authored_contact)!==key(payload.scene.contacts.find(b=>b.id===c.id))||!endpointInspection(c.original_endpoint_inspection,c.original_contact)||!endpointInspection(c.authored_endpoint_inspection,c.authored_contact)))throw Error('Contact review does not match the unapproved draft.');
  return r;
 }
 el('RevisionPreview').onclick=guard(async()=>{if(revisionBusy||busy)throw Error('Wait for the current request.');const choice=revisionChoice();if(!choice.source&&!choice.partner)throw Error('Stage a source or partner patch first.');
  const before=editable(),payload=revisionDraft(before,choice);revisionBusy=true;invalidateRevision();el('RevisionPreview').disabled=true;
  try{const r=checkedPreview(await post('/api/native-scene-contact-revision',payload),payload);
   if(key(before)!==key(editable())||key(choice)!==key(revisionChoice()))throw Error('The scene or staged patches changed; preview again.');
   pendingRevision={before,payload,choice,result:r};el('RevisionApply').disabled=false;el('RevisionResults').replaceChildren();
   for(const change of r.changes){const text=document.createElement('p'),a=change.original_contact,b=change.authored_contact;
    text.textContent=`${change.id}: source ${a.vertices.length} ${a.reduction} → ${b.vertices.length} ${b.reduction}`+(b.target.space==='actor'?`; partner ${a.target.vertices.length} ${a.target.reduction} → ${b.target.vertices.length} ${b.target.reduction}`:'')+'. Timing, limits and animation bytes stay preserved. Endpoint inspection only; anatomy and motion quality need review.';el('RevisionResults').append(text);
    const old=change.original_endpoint_inspection,newer=change.authored_endpoint_inspection;
    for(let i=0;i<old.times_s.length;i++){const sample=document.createElement('p');sample.className='small';sample.textContent=`At ${old.times_s[i]} s: original separation ${Math.max(...old.separation_m[i])*1000} mm; authored separation ${Math.max(...newer.separation_m[i])*1000} mm.`;el('RevisionResults').append(sample);}
    const details=document.createElement('details'),summary=document.createElement('summary'),coordinates=document.createElement('pre');summary.textContent='Exact original and authored vertices and endpoint positions';
    coordinates.textContent=JSON.stringify({original_contact:a,authored_contact:b,original_endpoint_positions:old,authored_endpoint_positions:newer},null,2);details.append(summary,coordinates);el('RevisionResults').append(details);}
   status('Review the explicit patch changes, then Apply. The original contact conditions will be retained.');
  }finally{revisionBusy=false;el('RevisionPreview').disabled=false;}
 });
 el('RevisionApply').onclick=guard(async()=>{if(revisionBusy||busy)throw Error('Wait for the current request.');const pending=pendingRevision;
  if(!pending||key(pending.before)!==key(editable())||key(pending.choice)!==key(revisionChoice())){invalidateRevision();throw Error('Preview the current scene and patches before applying.');}
  revisionBusy=true;el('RevisionApply').disabled=true;
  try{const r=checkedPreview(await post('/api/native-scene-contact-revision',pending.payload),pending.payload);
   if(pending!==pendingRevision||key(pending.before)!==key(editable())||key(pending.choice)!==key(revisionChoice())||key(r)!==key(pending.result))throw Error('The preview or source changed; preview again.');
   bind(pending.payload);status('Explicit revised contact intent applied to the draft. Original conditions are retained; timing and bounds are preserved. Save or build separately.');
  }finally{revisionBusy=false;pendingRevision=null;el('RevisionApply').disabled=true;}
 });
 el('RevisionRestore').onclick=guard(()=>{if(revisionBusy||busy)throw Error('Wait for the current request.');if(!draft.contact_revision)throw Error('No contact revision to restore.');bind(draft.contact_revision.baseline);status('Original authoring draft restored. Animation bytes remain unchanged.');});
 el('TargetType').onchange=targetOptions;el('Shape').onchange=()=>{el('Dimensions').value=el('Shape').value==='box'?'0.4, 0.4, 0.4':el('Shape').value==='sphere'?'0.2':'0.2, 0.4';};
 el('Mode').onchange=()=>{el('End').disabled=el('Mode').value==='touch';el('SpeedLimit').disabled=el('Mode').value==='touch';};
 el('Save').onclick=guard(()=>download(editable()));
 el('Import').onchange=guard(async()=>{const file=el('Import').files?.[0];if(!file)return;if(file.size>1048576)throw Error('Scene draft exceeds 1 MiB.');bind(JSON.parse(await file.text()));status('Draft loaded. Source hashes will be checked before building.');});
 async function refresh(){const data=await api('/api/native-scene-jobs');const chosen=el('Jobs').value;options('Jobs',data.jobs.map(j=>j.id));if(data.jobs.some(j=>j.id===chosen))el('Jobs').value=chosen;return data;}
 el('Refresh').onclick=guard(refresh);
 el('Build').onclick=guard(async()=>{if(busy||revisionBusy)throw Error('Wait for this request.');busy=true;el('Build').disabled=true;try{const job=await post('/api/native-scene-assets',editable());await refresh();el('Jobs').value=job.id;status('Scene job started. Refresh its results to follow the saved stages.');}finally{busy=false;el('Build').disabled=false;}});
 el('Review').onclick=guard(async()=>{const id=el('Jobs').value;if(!id)throw Error('Select a scene asset job.');const r=await api(`/api/native-scene-review?id=${encodeURIComponent(id)}`);el('Results').replaceChildren();
  const text=document.createElement('p');text.textContent=r.status==='complete'?`Recorded sampled conditions: ${r.sampled_conditions_pass?'pass':'fail'} at ${r.samples} times. Original contacts: ${r.source_contacts_pass?'pass':'fail'}. Motion-quality, physics and runtime approval remain open.`:`${r.status}: ${r.stage||r.error||'waiting'} · ${r.completed_stages?.length??0} completed stage(s).`;el('Results').append(text);
  for(const entry of r.downloads||[]){const a=document.createElement('a');a.className='btn';a.href=entry.url;a.download='';a.textContent=entry.label;el('Results').append(a);}status(r.status==='complete'?'Recorded results and source-bound assets loaded.':text.textContent);
 });
 regionLoader=createMaterialPatchLoader({document,post,getDraft:editable,getContact:()=>el('RevisionContact').value,stage:stageRevisionPatch,status,download});
 regionAuthor=createMaterialRegionAuthor({document,post,getDraft:editable,getContact:()=>el('RevisionContact').value,getSide:()=>el('RegionSide').value,getPatch,status,
  saved:value=>{regionLoader.clear();el('RegionBundle').value=value.bundle;el('RegionResult').value=value.result_sha256;el('RegionPatch').value=value.patch_id;el('RegionIndices').value='';}});
 draw();return {bind,snapshot:editable,refresh};
}
function defaultDownload(value,filename='native-scene-draft.json'){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'})),a=globalThis.document.createElement('a');a.href=url;a.download=filename;a.click();URL.revokeObjectURL(url);}
