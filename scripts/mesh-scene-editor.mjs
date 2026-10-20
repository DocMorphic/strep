const clone=value=>structuredClone(value),key=value=>JSON.stringify(value),hash=/^[a-f0-9]{64}$/;
const name=value=>{if(!/^[A-Za-z0-9_-]{1,64}$/.test(value))throw Error('Use a distinct name with letters, numbers, hyphens or underscores.');return value;};
export function triple(text){const values=String(text).trim().split(/[\s,]+/).map(Number);if(!String(text).trim()||values.length!==3||values.some(x=>!Number.isFinite(x)||Math.abs(x)>1e6))throw Error('Enter three finite coordinates.');return values;}
export function xyzQuaternion(degrees){
 const [x,y,z]=degrees.map(v=>v*Math.PI/360),a=Math.cos(x),b=Math.sin(x),c=Math.cos(y),d=Math.sin(y),e=Math.cos(z),f=Math.sin(z);
 return [b*c*e-a*d*f,a*d*e+b*c*f,a*c*f-b*d*e,a*c*e+b*d*f];
}
export function meshContact(draft,props,patch,grip,settings){
 const {id,actor,prop,mode,start,end,gap,speed}=settings;name(id);
 if(!draft.scene.actors[actor]||patch?.glb_sha256!==draft.scene.actors[actor].sha256)throw Error('Pick a contact patch on this exact character clip.');
 if(!Array.isArray(patch.vertices)||!patch.vertices.length||patch.vertices.length>256||patch.vertices.some(v=>!Array.isArray(v)||v.length!==3||v.some(i=>!Number.isInteger(i)||i<0))||new Set(patch.vertices.map(key)).size!==patch.vertices.length)throw Error('Choose a distinct skin surface patch.');
 if(!props[prop]||grip.asset_id!==props[prop].asset_id||!hash.test(grip.grip_id))throw Error('Select a saved grip on this object in Object grip points.');
 if(!['touch','hold'].includes(mode)||![start,end,gap,speed].every(v=>typeof v==='number'&&Number.isFinite(v))||start<0||start>draft.scene.duration_s||gap<0||speed<0||mode==='hold'&&!(start<end&&end<=draft.scene.duration_s))throw Error('Use in-clip contact times and nonnegative limits.');
 return {id,actor,vertices:clone(patch.vertices),reduction:'centroid',prop,grip_id:grip.grip_id,mode,interval_s:[start,mode==='touch'?start:end],limits:mode==='touch'?{position_m:gap}:{position_m:gap,relative_speed_m_s:speed}};
}
export function createMeshSceneEditor({document=globalThis.document,api,post,getDraft,getPatch,getGrip}){
 const el=s=>document.getElementById('meshScene'+s);let draft=null,props={},contacts=[],busy=false,revision=0;
 const status=s=>{el('Status').textContent=s;};
 const checked=()=>{if(!draft)throw Error('Use the current native scene first.');if(key(getDraft())!==key(draft))throw Error('The native scene changed. Bind it again before adding contacts or saving.');};
 const numeric=s=>{const raw=String(el(s).value).trim(),v=Number(raw);if(!raw||!Number.isFinite(v))throw Error('Fill in '+s);return v;};
 const action=fn=>async()=>{if(busy)return;busy=true;try{await fn();}catch(e){status(e.message);}finally{busy=false;}};
 const options=(s,values)=>{const previous=el(s).value;el(s).replaceChildren(...values.map(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;return o;}));if(values.includes(previous))el(s).value=previous;};
 function draw(){options('Actor',Object.keys(draft?.scene.actors||{}));options('Target',Object.keys(props));
  el('Objects').textContent=Object.keys(props).length?`Objects: ${Object.keys(props).join(', ')}`:'No imported objects placed.';
  el('Contacts').replaceChildren(...contacts.map(c=>{const p=document.createElement('p');p.textContent=`${c.id}: ${c.actor} → ${c.prop}, ${c.mode} ${c.interval_s.join('–')} seconds `;const remove=document.createElement('button');remove.className='btn';remove.textContent='Remove';remove.onclick=()=>{if(busy)return;contacts=contacts.filter(x=>x.id!==c.id);revision++;draw();};p.append(remove);return p;}));
 }
 el('Bind').onclick=action(()=>{const value=clone(getDraft());if(!value.scene?.actors||!Object.keys(value.scene.actors).length||value.object_edit!==null||value.contact_revision)throw Error('Add characters and resolve pending object edits or contact revisions first.');draft=value;props={};contacts=[];revision++;el('Summary').textContent=`${Object.keys(draft.scene.actors).join(', ')} · ${draft.scene.duration_s} seconds. Scene bound; rebinding clears this object/contact draft.`;el('End').value=draft.scene.duration_s;draw();status('Choose a saved object grip and place its object.');});
 el('AddObject').onclick=action(async()=>{
  checked();const selected=clone(getGrip()),id=name(el('Object').value.trim()),before=revision;
  const form=()=>key(['Object','Position','Rotation','EndPosition','EndRotation'].map(s=>el(s).value).concat(el('Moving').checked)),formBefore=form();
  if(props[id]||draft.scene.actors[id]||draft.scene.objects[id])throw Error('Choose a new object name.');
  if(!hash.test(selected.asset_id)||!hash.test(selected.grip_id))throw Error('Choose a saved object grip in the Scene window.');
  const pose=(time,position,rotation)=>({time_s:time,translation_m:triple(el(position).value),rotation_xyzw:xyzQuaternion(triple(el(rotation).value))});
  const keys=[pose(0,'Position','Rotation')];if(el('Moving').checked)keys.push(pose(draft.scene.duration_s,'EndPosition','EndRotation'));
  const asset=await api(`/api/props/${selected.asset_id}`);checked();
  if(before!==revision||key(getGrip())!==key(selected)||form()!==formBefore)throw Error('Object grip or placement changed. Add the intended object again.');
  if(asset.id!==selected.asset_id||!hash.test(asset.geometry_sha256)||!asset.grip_ids.includes(selected.grip_id))throw Error('Saved object grip is unavailable.');
  props[id]={asset_id:asset.id,geometry_sha256:asset.geometry_sha256,keyframes:keys};revision++;draw();status(`Placed ${id}. Select the character's hand or other intended contact patch.`);
 });
 el('AddContact').onclick=action(()=>{checked();const row=meshContact(draft,props,getPatch(),getGrip(),{id:el('Contact').value.trim(),actor:el('Actor').value,prop:el('Target').value,mode:el('Mode').value,start:numeric('Start'),end:numeric('End'),gap:numeric('Gap')/1000,speed:numeric('Speed')});if(contacts.some(c=>c.id===row.id)||draft.scene.contacts.some(c=>c.id===row.id))throw Error('Choose a new contact name.');contacts.push(row);revision++;draw();status('Contact intent added. Save the scene to measure it against the unchanged animation.');});
 const snapshot=()=>{checked();if(!Object.keys(props).length||!contacts.length)throw Error('Add an imported object and a contact first.');return {schema:'strep-studio-mesh-scene-v1',draft:clone(draft),props:clone(props),contacts:clone(contacts)};};
 el('Build').onclick=action(async()=>{const request=snapshot();const response=await post('/api/mesh-scene-jobs',request);if(!/^[a-f0-9]{32}$/.test(response.id))throw Error('Invalid saved scene job.');el('Job').value=response.id;status('Scene queued with a memory guard. Refresh measurements to see its progress.');});
 el('Review').onclick=action(async()=>{const id=el('Job').value;if(!/^[a-f0-9]{32}$/.test(id))throw Error('Choose a saved scene job.');const r=await api(`/api/mesh-scene-jobs/${id}`);if(el('Job').value!==id)throw Error('Saved job selection changed.');el('Results').replaceChildren();if(r.id!==id||r.quality_approved!==false||r.release_approved!==false)throw Error('Invalid scene measurements.');
  if(r.status==='complete'){
   if(typeof r.all_declared_point_contacts_pass!=='boolean'||r.motion_fitted!==false||r.geometry_evaluated!==false||r.original_selected!==true)throw Error('Invalid contact measurement scope.');
   status(`Point-contact checks: ${r.all_declared_point_contacts_pass?'pass':'fail'}. Character motion is unchanged. Collision, grasp realism and engine validation have not run.`);
   for(const row of r.contacts){const p=document.createElement('p');p.textContent=`${row.id}: ${(row.maximum_position_error_m*1000).toFixed(2)} mm peak gap at ${row.peak_time_s.toFixed(3)} s; ${row.passed?'passes':'fails'} declared contact limits.`;el('Results').append(p);}
   for(const entry of r.downloads){if(![`/files/mesh-scene-jobs/${id}/scene-package.zip`,`/files/mesh-scene-jobs/${id}/contact-report.json`].includes(entry.url))throw Error('Unexpected scene download.');const a=document.createElement('a');a.href=entry.url;a.download='';a.className='btn';a.textContent=entry.label;el('Results').append(a);}
   if(r.preview_url){if(!new RegExp(`^/mesh-scene-viewer\\.html\\?job=${id}&result=[a-f0-9]{64}$`).test(r.preview_url))throw Error('Unexpected scene preview.');const a=document.createElement('a');a.href=r.preview_url;a.target='_blank';a.rel='noopener';a.className='btn';a.textContent='View character and object together';el('Results').append(a);}
  }else status(`${r.status}: ${r.error||'waiting for the guarded measurement'}`);
 });
 draw();return {snapshot};
}
