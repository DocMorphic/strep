const clone=structuredClone;
const key=v=>JSON.stringify(v,(_,x)=>x&&typeof x==='object'&&!Array.isArray(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,x[k]])):x);
const hash=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
export function regionRequest(draft,contactId,form){
 const row=draft.scene.contacts.find(c=>c.id===contactId);
 if(!row)throw Error('Choose an existing contact.');
 if(!['source','partner'].includes(form.side)||form.side==='partner'&&row.target.space!=='actor')throw Error('Choose a source or an actor partner region.');
 const actor=draft.scene.actors[form.side==='source'?row.actor:row.target.actor];
 let indices;try{indices=JSON.parse(form.indices);}catch{throw Error('Enter an ordered JSON array of patch vertex indices.');}
 if(!Array.isArray(indices)||!indices.length||indices.length>256||indices.some(i=>!Number.isInteger(i)||i<0)||new Set(indices).size!==indices.length)throw Error('Choose 1–256 distinct ordered patch vertex indices.');
 if(!hash(form.result)||!hash(actor?.sha256))throw Error('Enter the saved bundle result SHA256.');
 if(typeof form.bundle!=='string'||form.bundle.length>512||!form.bundle.split('/').every(p=>/^[A-Za-z0-9_-]+$/.test(p)))throw Error('Enter a bundle folder relative to reports.');
 if(!/^[A-Za-z0-9_-]{1,64}$/.test(form.patch)||!['individual','centroid'].includes(form.reduction))throw Error('Choose an explicit saved patch and measurement.');
 return {schema:'strep-studio-material-patch-v1',actor:{glb:actor.glb,sha256:actor.sha256},bundle:form.bundle,result_sha256:form.result,patch_id:form.patch,vertex_indices:indices,reduction:form.reduction};
}
export function checkedRegion(value,request){
 const p=value?.patch,b=value?.binding;
 if(value?.schema!==request.schema||key(value.request)!==key(request)||value.explicit_vertex_correspondence!==true||value.original_selected!==true||value.anatomical_review_pending!==true
  ||['animation_edited','motion_contacts_measured','engine_executed','human_reviewed','quality_approved','training_admitted','release_approved'].some(k=>value[k]!==false)
  ||!value.implementation_sha256||!hash(value.implementation_sha256['studio_material_patch.py'])||!hash(value.implementation_sha256['material_patch_bundle.py'])||Object.values(value.implementation_sha256).some(h=>!hash(h))
  ||p?.glb_sha256!==request.actor.sha256||p?.reduction!==request.reduction||!Array.isArray(p.vertices)||p.vertices.length!==request.vertex_indices.length||p.vertices.some(v=>!Array.isArray(v)||v.length!==3||v.some(i=>!Number.isInteger(i)||i<0))||new Set(p.vertices.map(key)).size!==p.vertices.length
  ||b?.bundle!==request.bundle||b?.result_sha256!==request.result_sha256||b?.patch_id!==request.patch_id||!hash(b?.patch_sha256)||b?.source?.character_sha256!==request.actor.sha256||!hash(b?.source?.profile_sha256)||b?.source?.reference_pose!=='default_nodes'||b?.source?.weight_normalization!=='RigAsset per-vertex sum'||key(b?.vertex_indices)!==key(request.vertex_indices)||b?.reduction!==request.reduction)throw Error('Saved region receipt does not match the selected clip and point order.');
 return clone(value);
}
export function createMaterialPatchLoader({document=globalThis.document,post,getDraft,getContact,stage,status,download}={}){
 const el=n=>document.getElementById('nativeSceneRegion'+n);let busy=false,receipt=null,serial=0;
 const form=()=>({side:el('Side').value,bundle:el('Bundle').value.trim(),result:el('Result').value.trim(),patch:el('Patch').value.trim(),indices:el('Indices').value,reduction:el('Reduction').value});
 el('Load').onclick=async()=>{
  let started=false;
  try{
   if(busy)throw Error('Wait for the saved region request.');
   const draft=clone(getDraft()),contact=getContact(),choice=form(),request=regionRequest(draft,contact,choice),token=++serial;
   busy=true;started=true;el('Load').disabled=true;receipt=null;el('Receipt').disabled=true;el('Summary').textContent='';
   const result=checkedRegion(await post('/api/native-scene-material-patch',request),request);
   if(token!==serial||key(draft)!==key(getDraft())||contact!==getContact()||key(choice)!==key(form()))throw Error('Scene or region selection changed; load again.');
   stage(choice.side,result.patch);receipt=result;el('Receipt').disabled=false;
   el('Summary').textContent=`${request.patch_id}: ${result.patch.vertices.length} ordered vertices staged for ${choice.side}.`;
   status('Saved region staged. Preview contact changes before applying.');
  }catch(error){status(error.message);}finally{if(started){busy=false;el('Load').disabled=false;}}
 };
 el('Receipt').onclick=()=>{if(receipt)download(clone(receipt),'saved-region-receipt.json');};
 return {clear(){serial++;receipt=null;el('Receipt').disabled=true;el('Summary').textContent='';}};
}
