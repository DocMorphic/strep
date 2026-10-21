const clone=x=>structuredClone(x);
const key=x=>JSON.stringify(x,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
const id=x=>typeof x==='string'&&/^[a-f0-9]{32}$/.test(x);
export function diagnosticLines(summary,result){
 if(summary===undefined)return null;
 if(summary?.schema!=='strep-studio-mesh-diagnostics-v1'||summary.quality_approved!==false||summary.release_approved!==false||typeof summary.available!=='boolean')throw Error('Invalid saved attempt checks.');
 if(!summary.available)return ['Detailed attempt checks were not included in this saved result.'];
 const count=x=>Number.isSafeInteger(x)&&x>=0;
 if(!count(summary.attempts)||summary.attempts!==result.probes||!count(summary.accepted)||summary.accepted!==result.accepted_steps||summary.accepted>summary.attempts||!Array.isArray(summary.checks)||summary.checks.length!==10)throw Error('Saved attempt counts differ.');
 const keys=new Set();
 return summary.checks.map(check=>{
  if(!check||typeof check.key!=='string'||keys.has(check.key)||typeof check.label!=='string'||!check.label.trim())throw Error('Invalid saved attempt check.');
  keys.add(check.key);
  const states=['passed','failed','not_checked','not_recorded'];
  if(states.some(s=>!count(check[s]))||states.reduce((n,s)=>n+check[s],0)!==summary.attempts)throw Error('Saved check counts differ.');
  return `${check.label}: ${check.passed} passed, ${check.failed} failed, ${check.not_checked} not checked, ${check.not_recorded} not recorded.`;
 });
}
export function correctionRequest(sceneJob,digest,mesh,correction,edges,ack,maxRuntimeSeconds=900){
 if(!id(sceneJob)||typeof digest!=='string'||!/^[a-f0-9]{64}$/.test(digest))throw Error('Choose a complete saved object-contact scene.');
 if(correction?.schema!=='strep-studio-native-scene-fit-v1'||correction.resume_from!==null||key(Object.keys(correction).sort())!==key(['actors','draft','options','resume_from','schema']))throw Error('Use fresh Contact adjustment bounds, without turning-speed limits or clearance options.');
 if(key(correction.draft)!==key(mesh.draft)||correction.draft.rotation_speed_limits?.length)throw Error('Save bounds for this exact scene; turning-speed limits are not supported here.');
 if(!Object.keys(correction.actors??{}).length)throw Error('Save bounds for at least one character.');
 if(edges.some(e=>!['start','end'].includes(e))||new Set(edges).size!==edges.length)throw Error('Choose distinct clip edges.');
 if(edges.length&&!ack)throw Error('Acknowledge review of changed starts, ends and transitions.');
 if(![900,1800,3600].includes(maxRuntimeSeconds))throw Error('Choose a processing time limit of 15, 30 or 60 minutes.');
 return {schema:'strep-studio-mesh-character-v1',scene_job:sceneJob,scene_result_sha256:digest,mesh_request:clone(mesh),correction:clone(correction),editable_clip_boundaries:Object.fromEntries(Object.keys(correction.actors).map(name=>[name,[...edges]])),acknowledge_changed_boundary_compatibility:edges.length>0&&ack,max_runtime_seconds:maxRuntimeSeconds,recoverable:true};
}
export function createMeshCharacterEditor({document=globalThis.document,api,post,getScene,getBounds}){
 const el=n=>document.getElementById('meshCharacter'+n);let busy=false,continuation=null;
 const status=s=>{el('Status').textContent=s;};
 const resetContinuation=()=>{continuation=null;el('Continue').disabled=true;};
 const validReport=(result,job)=>{if(el('Job').value!==job||result.id!==job||result.original_selected!==true||result.quality_approved!==false||result.release_approved!==false)throw Error('Correction selection or scope changed.');};
 const action=fn=>async()=>{if(busy)return;busy=true;el('Build').disabled=true;el('Continue').disabled=true;try{await fn();}catch(error){resetContinuation();status(error.message);}finally{busy=false;el('Build').disabled=false;el('Continue').disabled=!continuation;}};
 resetContinuation();el('Job').oninput=resetContinuation;
 el('Build').onclick=action(async()=>{
  const selection=()=>({scene:getScene(),bounds:getBounds(),edges:['start','end'].filter(e=>el(e==='start'?'Start':'End').checked),ack:el('Ack').checked,maxRuntimeSeconds:Number(el('TimeLimit').value)});
  const before=clone(selection());if(!id(before.scene.job))throw Error('Save the object-contact scene first.');
  const saved=await api(`/api/mesh-scene-jobs/${before.scene.job}`);
  if(key(before)!==key(selection()))throw Error('Scene or bounds changed while checking the saved scene; run it again.');
  const match=typeof saved.preview_url==='string'&&saved.preview_url.match(new RegExp(`^/mesh-scene-viewer\\.html\\?job=${before.scene.job}&result=([a-f0-9]{64})$`));
  if(saved.id!==before.scene.job||saved.status!=='complete'||saved.original_selected!==true||saved.quality_approved!==false||!match)throw Error('Wait for a complete saved scene measurement.');
  const request=correctionRequest(before.scene.job,match[1],before.scene.request,before.bounds,before.edges,before.ack,before.maxRuntimeSeconds);
  resetContinuation();const result=await post('/api/mesh-character-jobs',request);if(!id(result.id))throw Error('Invalid correction job.');
  el('Job').value=result.id;status(`Correction queued with a ${before.maxRuntimeSeconds/60}-minute processing limit and a memory guard. Refresh to inspect progress and retained failures.`);
 });
 el('Review').onclick=action(async()=>{
  const job=el('Job').value;if(!id(job))throw Error('Choose a correction job.');
  resetContinuation();const result=await api(`/api/mesh-character-jobs/${job}`);validReport(result,job);
  const limit=result.max_runtime_seconds??900;if(![900,1800,3600].includes(limit))throw Error('Invalid saved processing time limit.');
  el('Results').replaceChildren();if(result.status!=='complete'){
   if(result.recoverable===true&&result.can_continue===true&&['failed','deferred'].includes(result.status)&&result.continuation){continuation={job,ticket:clone(result.continuation)};}
   status(`${result.status} (${limit/60}-minute limit): ${result.error||'waiting for the guarded correction'}${continuation?' Continue uses the saved scene and bounds.':result.continuation_error?` ${result.continuation_error}`:''}`);return;}
  const r=result.result;if(typeof r.sampled_candidate_pass!=='boolean'||r.original_selected!==true||r.quality_approved!==false||r.release_approved!==false)throw Error('Invalid correction measurements.');
  const lines=diagnosticLines(result.diagnostics,r);
  status(`${r.accepted_steps} accepted edits from ${r.probes} attempts (${limit/60}-minute limit). ${r.sampled_candidate_pass?'Candidate passes declared sampled checks.':r.candidate?'Candidate still fails some declared checks.':'No improved candidate accepted.'} Originals remain selected. Engine and motion-quality review are still required.`);
  if(!new RegExp(`^/mesh-character-viewer\\.html\\?job=${job}&result=[a-f0-9]{64}$`).test(result.comparison_url)||result.download_url!==`/files/mesh-character-jobs/${job}/correction-package.zip`)throw Error('Unexpected correction artifact link.');
  for(const [label,url] of [['Compare original and candidate',result.comparison_url],['Download correction and all proposals',result.download_url]]){const a=document.createElement('a');a.className='btn';a.textContent=label;a.href=url;a.target='_blank';a.rel='noopener';el('Results').append(a);}
  if(lines){const details=document.createElement('details'),heading=document.createElement('summary'),explanation=document.createElement('p'),list=document.createElement('ul');
   heading.textContent='View attempt checks';explanation.textContent='Counts refer to correction attempts, including rejected proposals. Geometry is checked only after motion, edit and contact safeguards pass. A failed geometry check can also mean the measurement was inconclusive. Accepted edits can still need cleanup; these checks do not approve motion quality.';
   for(const line of lines){const item=document.createElement('li');item.textContent=line;list.append(item);}
   details.append(heading,explanation,list);el('Results').append(details);}
 });
 el('Continue').onclick=action(async()=>{
  const selected=continuation;if(!selected||el('Job').value!==selected.job)throw Error('Refresh the interrupted correction first.');
  const current=await api(`/api/mesh-character-jobs/${selected.job}`);validReport(current,selected.job);
  if(current.can_continue!==true||current.recoverable!==true||!['failed','deferred'].includes(current.status)||key(current.continuation)!==key(selected.ticket))throw Error('Saved correction progress changed; refresh before continuing.');
  const result=await post(`/api/mesh-character-jobs/${selected.job}/continue`,selected.ticket);
  if(result.id!==selected.job||el('Job').value!==selected.job)throw Error('Correction selection changed.');
  resetContinuation();status('Continuing the saved correction with its original scene, bounds and processing limit. Earlier attempts remain available. Refresh to check progress.');
 });
}
