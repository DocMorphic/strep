import {checkedRegionOrientation,renderRegionOrientation} from './material-region-orientation.mjs';
import {poseRequest,checkedAuthorPose,renderRegionPose} from './material-region-pose.mjs';
const clone=structuredClone;
const key=v=>JSON.stringify(v,(_,x)=>x&&typeof x==='object'&&!Array.isArray(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,x[k]])):x);
const hash=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const refs=v=>Array.isArray(v)&&v.length>=3&&v.length<=256&&v.every(r=>Array.isArray(r)&&r.length===3&&r.every(n=>Number.isInteger(n)&&n>=0))&&new Set(v.map(key)).size===v.length;
export function authorRequest(draft,contactId,side,patch,form,profileJSON,profileSHA){
 const row=draft.scene.contacts.find(c=>c.id===contactId);if(!row)throw Error('Choose an existing contact.');
 if(!['source','partner'].includes(side)||side==='partner'&&row.target.space!=='actor')throw Error('Choose a source or actor partner region.');
 const actor=draft.scene.actors[side==='source'?row.actor:row.target.actor];
 if(patch?.glb_sha256!==actor?.sha256||!refs(patch?.vertices))throw Error('Pick 3–256 distinct vertices on the contact’s selected character clip.');
 if(!/^[A-Za-z0-9_-]{1,64}$/.test(form.patchId)||typeof form.role!=='string'||!form.role.length||form.role.length>64||typeof form.children!=='boolean'||!Number.isFinite(form.weight)||form.weight<=0||form.weight>1)throw Error('Choose a patch ID, mapped role and explicit ownership settings.');
 if(typeof profileJSON!=='string'||!hash(profileSHA))throw Error('Choose a matching UTF-8 rig profile file.');
 return {schema:'strep-studio-material-region-v1',actor:{glb:actor.glb,sha256:actor.sha256},profile_json:profileJSON,profile_sha256:profileSHA,
  patch_id:form.patchId,role:form.role,vertices:clone(patch.vertices),selector:{include_children:form.children,minimum_weight:form.weight,minimum_twice_area_m2:1e-12,maximum_faces:512,maximum_vertices:256}};
}
export function checkedAuthorPreview(value,request){
 const p=value?.patch;
 if(value?.schema!==request.schema||value.status!=='complete'||!/^[A-Za-z0-9_-]{1,64}$/.test(value.id)||!hash(value.result_sha256)||!hash(value.request_sha256)||!hash(value.patch_sha256)||!hash(value.selection_sha256)||!hash(value.orientation_sha256)||key(value.request)!==key(request)
  ||value.all_picked_vertices_accounted!==true||value.anatomical_review_pending!==true||['animation_edited','motion_contacts_measured','engine_executed','human_reviewed','quality_approved','training_admitted','release_approved'].some(k=>value[k]!==false)
  ||!value.implementation_sha256||!hash(value.implementation_sha256['studio_material_region.py'])||!hash(value.implementation_sha256['material_patch_bundle.py'])||!hash(value.implementation_sha256['material_region_orientation.py'])||Object.values(value.implementation_sha256).some(v=>!hash(v))
  ||key(value.input_sha256)!==key({'character.glb':request.actor.sha256,'rig-profile.json':request.profile_sha256})
  ||p?.schema!=='strep-rig-material-patch-v1'||p.role!==request.role||key(p.selector)!==key(request.selector)||p.source?.character_sha256!==request.actor.sha256||p.source?.profile_sha256!==request.profile_sha256||p.source?.reference_pose!=='default_nodes'||p.source?.weight_normalization!=='RigAsset per-vertex sum'
  ||!refs(p.vertices)||key(p.vertices.map(key).sort())!==key(request.vertices.map(key).sort())||!Array.isArray(p.face_references)||!p.face_references.length||p.face_references.length>512||p.face_references.some(r=>!Array.isArray(r)||r.length!==3||r.some(n=>!Number.isInteger(n)||n<0))||new Set(p.face_references.map(key)).size!==p.face_references.length
  ||!Array.isArray(p.reference_positions_m)||p.reference_positions_m.length!==p.vertices.length||p.reference_positions_m.some(r=>!Array.isArray(r)||r.length!==3||r.some(n=>typeof n!=='number'||!Number.isFinite(n)))
  ||!Number.isInteger(p.mapped_node)||p.mapped_node<0||!Array.isArray(p.selected_nodes)||!p.selected_nodes.includes(p.mapped_node)||p.selected_nodes.some(n=>!Number.isInteger(n)||n<0)||new Set(p.selected_nodes).size!==p.selected_nodes.length
  ||!Array.isArray(p.vertex_ownership)||p.vertex_ownership.length!==p.vertices.length||p.vertex_ownership.some(n=>typeof n!=='number'||!Number.isFinite(n)||n<request.selector.minimum_weight)
  ||p.requires_anatomical_review!==true||['anatomy_verified','contact_target_approved','quality_approved','release_approved'].some(k=>p[k]!==false))throw Error('Region preview does not match the picked vertices and profile.');
 checkedRegionOrientation(value.orientation,p);return clone(value);
}
export function checkedAuthorSave(value,preview){
 if(value?.schema!==preview.schema||value.status!=='complete'||!/^[A-Za-z0-9_-]{1,64}$/.test(value.id)||value.bundle!==`material-region-bundles/${value.id}`||!hash(value.result_sha256)||value.preview_id!==preview.id||value.preview_sha256!==preview.result_sha256||value.orientation_sha256!==preview.orientation_sha256||value.patch_id!==preview.request.patch_id||value.character_sha256!==preview.request.actor.sha256||value.profile_sha256!==preview.request.profile_sha256||value.faces!==preview.patch.face_references.length||value.vertices!==preview.patch.vertices.length
  ||value.explicit_triangle_selection!==true||value.original_selected!==true||value.anatomical_review_pending!==true||['animation_edited','motion_contacts_measured','engine_executed','human_reviewed','quality_approved','training_admitted','release_approved'].some(k=>value[k]!==false))throw Error('Saved region receipt does not match the preview.');
 return clone(value);
}
export function createMaterialRegionAuthor({document=globalThis.document,post,getDraft,getContact,getSide,getPatch,saved,status,digest=async buffer=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',buffer))].map(b=>b.toString(16).padStart(2,'0')).join('')}={}){
 const el=n=>document.getElementById('nativeSceneRegionAuthor'+n);let busy=false,pending=null,serial=0,poseSerial=0;
 const form=()=>({patchId:el('ID').value.trim(),role:el('Role').value.trim(),children:el('Children').checked,weight:Number(el('Weight').value)});
 const selection=()=>({draft:clone(getDraft()),contact:getContact(),side:getSide(),patch:clone(getPatch()),form:form(),file:el('Profile').files?.[0]});
 const stamp=v=>key({...v,file:null});
 const same=v=>{const now=selection();return v.file===now.file&&stamp(v)===stamp(now);};
 const clearPose=()=>{poseSerial++;el('PoseSummary').textContent='';el('PoseFaces').textContent='';el('PoseOrientation').replaceChildren();};
 const clear=()=>{serial++;pending=null;el('Save').disabled=true;el('Pose').disabled=true;el('Summary').textContent='';el('Faces').textContent='';el('Orientation').replaceChildren();clearPose();};
 el('Pose').disabled=true;
 el('Preview').onclick=async()=>{
  let started=false;
  try{
   if(busy)throw Error('Wait for the region request.');const before=selection(),token=++serial;
   if(!before.file||before.file.size<=0||before.file.size>128*1024)throw Error('Choose a UTF-8 rig profile up to 128 KiB.');
   busy=true;started=true;pending=null;el('Preview').disabled=true;el('Save').disabled=true;el('Summary').textContent='';el('Faces').textContent='';el('Orientation').replaceChildren();
   el('Pose').disabled=true;clearPose();
   const buffer=await before.file.arrayBuffer(),text=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(buffer),bound=await digest(buffer);
   const request=authorRequest(before.draft,before.contact,before.side,before.patch,before.form,text,bound);
   if(token!==serial||!same(before))throw Error('Region selection changed; preview again.');
   const value=checkedAuthorPreview(await post('/api/native-scene-material-region-preview',request),request);
   if(token!==serial||!same(before))throw Error('Region selection changed; preview again.');
   renderRegionOrientation(document,el('Orientation'),value.orientation,value.patch);
   pending={before,value,token};el('Save').disabled=false;el('Pose').disabled=false;
   el('Summary').textContent=`${value.patch.face_references.length} complete connected triangles, ${value.patch.vertices.length} selected vertices. Review the default-pose directions; contact during animation has not been measured.`;
   el('Faces').textContent=JSON.stringify({faces:value.patch.face_references,vertices:value.patch.vertices,reference_positions_m:value.patch.reference_positions_m,orientation:value.orientation},null,2);
   status('Review the surface directions and every enclosed triangle, then save the selected region.');
  }catch(error){status(error.message);}finally{if(started){busy=false;el('Preview').disabled=false;}}
 };
 el('Pose').onclick=async()=>{
  let started=false;
  try{
   if(busy)throw Error('Wait for the region request.');const choice=pending;
   if(!choice||choice.token!==serial||!same(choice.before))throw Error('Preview the current picked region first.');
   const text=el('Time').value.trim();if(!text)throw Error('Enter an explicit character-local time.');
   const request=poseRequest(choice.value,choice.before.draft,choice.before.contact,choice.before.side,Number(text));
   clearPose();const token=poseSerial;busy=true;started=true;el('Pose').disabled=true;el('Save').disabled=true;el('Preview').disabled=true;
   const result=checkedAuthorPose(await post('/api/native-scene-material-region-pose',request),request,choice.value);
   if(choice!==pending||choice.token!==serial||token!==poseSerial||text!==el('Time').value.trim()||!same(choice.before))throw Error('Region or time changed; inspect again.');
   renderRegionPose(document,el('PoseOrientation'),result.pose);el('PoseFaces').textContent=JSON.stringify(result,null,2);
   el('PoseSummary').textContent=`${result.pose.animation_name}: ${result.pose.time_s} / ${result.pose.duration_s} s, ${result.pose.face_references.length} triangles, ${result.pose.patch_winding.degenerate_local_faces.length} unavailable triangle normals. Character animation coordinates; scene contacts have not been measured.`;
   status('Recorded one native animation sample. Inspect its surface directions; object and partner contact need separate validation.');
  }catch(error){status(error.message);}finally{if(started){busy=false;el('Preview').disabled=false;el('Save').disabled=!pending;el('Pose').disabled=!pending;}}
 };
 el('Time').onchange=clearPose;
 el('Save').onclick=async()=>{
  let started=false;
  try{
   if(busy)throw Error('Wait for the region request.');const choice=pending;
   if(!choice||choice.token!==serial||!same(choice.before))throw Error('Preview the current picked region first.');
   busy=true;started=true;el('Save').disabled=true;
   const result=checkedAuthorSave(await post('/api/native-scene-material-region-save',{schema:choice.value.schema,id:choice.value.id,preview_sha256:choice.value.result_sha256}),choice.value);
   if(choice!==pending||choice.token!==serial||!same(choice.before))throw Error('Region selection changed; saved output remains separate.');
   saved(result);pending=null;el('Pose').disabled=true;status('Region bundle saved. Choose ordered vertex indices below, then load and stage it.');
  }catch(error){status(error.message);}finally{if(started){busy=false;el('Save').disabled=!pending;}}
 };
 for(const name of ['Profile','ID','Role','Children','Weight'])el(name).onchange=clear;
 return {clear};
}
