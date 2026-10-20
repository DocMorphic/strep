const clone=x=>structuredClone(x);
const key=x=>JSON.stringify(x,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
const id=x=>typeof x==='string'&&/^[a-f0-9]{32}$/.test(x);
export function correctionRequest(sceneJob,digest,mesh,correction,edges,ack){
 if(!id(sceneJob)||typeof digest!=='string'||!/^[a-f0-9]{64}$/.test(digest))throw Error('Choose a complete saved object-contact scene.');
 if(correction?.schema!=='strep-studio-native-scene-fit-v1'||correction.resume_from!==null||key(Object.keys(correction).sort())!==key(['actors','draft','options','resume_from','schema']))throw Error('Use fresh Contact adjustment bounds, without turning-speed limits or clearance options.');
 if(key(correction.draft)!==key(mesh.draft)||correction.draft.rotation_speed_limits?.length)throw Error('Save bounds for this exact scene; turning-speed limits are not supported here.');
 if(!Object.keys(correction.actors??{}).length)throw Error('Save bounds for at least one character.');
 if(edges.some(e=>!['start','end'].includes(e))||new Set(edges).size!==edges.length)throw Error('Choose distinct clip edges.');
 if(edges.length&&!ack)throw Error('Acknowledge review of changed starts, ends and transitions.');
 return {schema:'strep-studio-mesh-character-v1',scene_job:sceneJob,scene_result_sha256:digest,mesh_request:clone(mesh),correction:clone(correction),editable_clip_boundaries:Object.fromEntries(Object.keys(correction.actors).map(name=>[name,[...edges]])),acknowledge_changed_boundary_compatibility:edges.length>0&&ack};
}
export function createMeshCharacterEditor({document=globalThis.document,api,post,getScene,getBounds}){
 const el=n=>document.getElementById('meshCharacter'+n);let busy=false;
 const status=s=>{el('Status').textContent=s;};
 const action=fn=>async()=>{if(busy)return;busy=true;el('Build').disabled=true;try{await fn();}catch(error){status(error.message);}finally{busy=false;el('Build').disabled=false;}};
 el('Build').onclick=action(async()=>{
  const selection=()=>({scene:getScene(),bounds:getBounds(),edges:['start','end'].filter(e=>el(e==='start'?'Start':'End').checked),ack:el('Ack').checked});
  const before=clone(selection());if(!id(before.scene.job))throw Error('Save the object-contact scene first.');
  const saved=await api(`/api/mesh-scene-jobs/${before.scene.job}`);
  if(key(before)!==key(selection()))throw Error('Scene or bounds changed while checking the saved scene; run it again.');
  const match=typeof saved.preview_url==='string'&&saved.preview_url.match(new RegExp(`^/mesh-scene-viewer\\.html\\?job=${before.scene.job}&result=([a-f0-9]{64})$`));
  if(saved.id!==before.scene.job||saved.status!=='complete'||saved.original_selected!==true||saved.quality_approved!==false||!match)throw Error('Wait for a complete saved scene measurement.');
  const request=correctionRequest(before.scene.job,match[1],before.scene.request,before.bounds,before.edges,before.ack);
  const result=await post('/api/mesh-character-jobs',request);if(!id(result.id))throw Error('Invalid correction job.');
  el('Job').value=result.id;status('Correction queued with a memory guard. Refresh to inspect progress and retained failures.');
 });
 el('Review').onclick=action(async()=>{
  const job=el('Job').value;if(!id(job))throw Error('Choose a correction job.');
  const result=await api(`/api/mesh-character-jobs/${job}`);if(el('Job').value!==job||result.id!==job||result.original_selected!==true||result.quality_approved!==false||result.release_approved!==false)throw Error('Correction selection or scope changed.');
  el('Results').replaceChildren();if(result.status!=='complete'){status(`${result.status}: ${result.error||'waiting for the guarded correction'}`);return;}
  const r=result.result;if(typeof r.sampled_candidate_pass!=='boolean'||r.original_selected!==true||r.quality_approved!==false||r.release_approved!==false)throw Error('Invalid correction measurements.');
  status(`${r.accepted_steps} accepted edits from ${r.probes} attempts. ${r.sampled_candidate_pass?'Candidate passes declared sampled checks.':r.candidate?'Candidate still fails some declared checks.':'No improved candidate accepted.'} Originals remain selected. Engine and motion-quality review are still required.`);
  if(!new RegExp(`^/mesh-character-viewer\\.html\\?job=${job}&result=[a-f0-9]{64}$`).test(result.comparison_url)||result.download_url!==`/files/mesh-character-jobs/${job}/correction-package.zip`)throw Error('Unexpected correction artifact link.');
  for(const [label,url] of [['Compare original and candidate',result.comparison_url],['Download correction and all attempts',result.download_url]]){const a=document.createElement('a');a.className='btn';a.textContent=label;a.href=url;a.target='_blank';a.rel='noopener';el('Results').append(a);}
 });
}
