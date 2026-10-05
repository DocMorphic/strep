export function createNativeTransferEditor({document=globalThis.document,api,post,onImported=async()=>{}}={}){
 const el=n=>document.getElementById('nativeTransfer'+n),status=t=>{el('Status').textContent=t;},guard=f=>async()=>{try{await f();}catch(e){status(e.message);}};
 const option=(v,t)=>{const n=document.createElement('option');n.value=String(v);n.textContent=t;return n;};
 let binding=null,epoch=0,reviewEpoch=0,busy=false,reviewed=null;
 function clearReview(){++reviewEpoch;reviewed=null;el('Import').disabled=true;el('Results').replaceChildren();el('Preview').hidden=true;el('Preview').src='about:blank';}
 function invalidate(){++epoch;binding=null;el('Clip').replaceChildren();el('Clip').disabled=true;clearReview();}
 el('Source').onchange=invalidate;el('Target').onchange=invalidate;el('Jobs').onchange=clearReview;
 async function characters(){const old=[el('Source').value,el('Target').value],data=await api('/api/characters');invalidate();
  for(const [i,n] of ['Source','Target'].entries()){el(n).replaceChildren(...data.characters.map(a=>option(a.id,a.name)));if(data.characters.some(a=>a.id===old[i]))el(n).value=old[i];}
  if(el('Source').value===el('Target').value&&data.characters.length>1)el('Target').value=data.characters[1].id;
 }
 el('Characters').onclick=guard(characters);
 el('Bind').onclick=guard(async()=>{const source=el('Source').value,target=el('Target').value;if(!source||!target||source===target)throw Error('Choose two different imported characters.');invalidate();const token=epoch;
  const [a,b]=await Promise.all([api('/api/native-transfer-character?id='+encodeURIComponent(source)),api('/api/native-transfer-character?id='+encodeURIComponent(target))]);
  if(token!==epoch||el('Source').value!==source||el('Target').value!==target)throw Error('Character selection changed; bind again.');
  if(a.asset_id!==source||b.asset_id!==target||![a.asset_id,b.asset_id,a.profile_id,b.profile_id].every(v=>/^[a-f0-9]{64}$/.test(v))||a.quality_approved!==false||b.quality_approved!==false||a.source_profile_ready!==true)throw Error('Save valid source/target mappings; source offset and custom axes must be zero.');
  const clips=a.clips.filter(c=>c.supported);if(!clips.length)throw Error('Source has no supported LINEAR clip.');
  binding={source_asset_id:source,source_profile_id:a.profile_id,target_asset_id:target,target_profile_id:b.profile_id};
  el('Clip').replaceChildren(...clips.map(c=>option(c.index,c.name)));el('Clip').disabled=false;status(`Bound ${a.name} → ${b.name}. Original assets remain unchanged.`);
 });
 function snapshot(){if(!binding||binding.source_asset_id!==el('Source').value||binding.target_asset_id!==el('Target').value)throw Error('Bind the saved mappings again.');const animation_index=Number(el('Clip').value),rate=Number(el('Rate').value);if(!Number.isInteger(animation_index)||animation_index<0||![60,120,240].includes(rate))throw Error('Choose a clip and supported sampling rate.');return {...binding,animation_index,rate};}
 async function refresh(){const value=el('Jobs').value,data=await api('/api/native-transfer-jobs');el('Jobs').replaceChildren(...data.jobs.map(j=>option(j.id,j.id+' · '+j.status)));if(data.jobs.some(j=>j.id===value))el('Jobs').value=value;return data;}
 el('Refresh').onclick=guard(refresh);
 el('Build').onclick=guard(async()=>{if(busy)throw Error('Wait for the current request.');const payload=snapshot(),token=epoch;busy=true;el('Build').disabled=true;
  try{const r=await post('/api/native-transfer-assets',payload);await refresh();if(token===epoch){clearReview();el('Jobs').value=r.id;}status(`Transfer ${r.id} started. Review it when complete; originals stay selected.`);}finally{busy=false;el('Build').disabled=false;}
 });
 el('Review').onclick=guard(async()=>{clearReview();const id=el('Jobs').value,token=reviewEpoch;if(!id)throw Error('Choose a transfer job.');const r=await api('/api/native-transfer-review?id='+encodeURIComponent(id));
  if(token!==reviewEpoch||el('Jobs').value!==id||r.id!==id)throw Error('Review selection changed; request it again.');const p=document.createElement('p');
  if(r.status!=='complete'){p.textContent=`${r.status}: ${r.error||r.stage||'waiting'}`;el('Results').append(p);status(p.textContent);return;}
  const labels=['candidate.zip','transfer/character.glb','edit-profile.json','transfer/root-motion.json','transfer/report.json','audit/animation.res','audit/result.json','result.json'];
  if(r.quality_approved!==false||r.release_approved!==false||r.contact_verified!==false||r.original_selected!==true||r.transfer_fidelity?.passed!==true||typeof r.sampled_runtime_conditions_pass!=='boolean'||!/^[a-f0-9]{64}$/.test(r.result_sha256)||r.preview_url!==`/native-transfer-viewer.html?id=${id}&result=${r.result_sha256}`||!Array.isArray(r.downloads)||r.downloads.length!==labels.length||new Set(r.downloads.map(d=>d.label)).size!==labels.length||r.downloads.some(d=>!labels.includes(d.label)||d.url!==`/files/native-transfer-jobs/${id}/${d.label}`))throw Error('Invalid source-bound transfer result.');
  p.textContent=`${r.source_skin_joints} → ${r.target_skin_joints} bones. Transfer interpolation: pass. Saved-resource/root playback: ${r.sampled_runtime_conditions_pass?'pass':'fail'}. Contacts and motion quality remain unverified.`;el('Results').append(p);
  for(const d of r.downloads){const a=document.createElement('a');a.href=d.url;a.download='';a.className='btn';a.textContent=d.label;el('Results').append(a);}
  el('Preview').src=r.preview_url;el('Preview').hidden=false;reviewed=r.sampled_runtime_conditions_pass?{job:id,result_sha256:r.result_sha256}:null;el('Import').disabled=!reviewed;status(p.textContent);
 });
 el('Import').onclick=guard(async()=>{if(busy)throw Error('Wait for the current request.');if(!reviewed||reviewed.job!==el('Jobs').value||el('Import').disabled)throw Error('Review a playback-verified candidate first.');const payload={...reviewed},token=reviewEpoch;busy=true;el('Import').disabled=true;
  try{const result=await post('/api/native-transfer-import',payload);if(token!==reviewEpoch||el('Jobs').value!==payload.job)throw Error('Candidate was added to the library; selection changed, so it was not opened.');if(!/^[a-f0-9]{64}$/.test(result.asset_id)||!/^[a-f0-9]{64}$/.test(result.profile_id)||result.quality_approved!==false)throw Error('Invalid imported candidate mapping.');await onImported(result.asset_id);status('Candidate and baked edit mapping added to the library. Contacts and motion quality still need review.');}finally{busy=false;el('Import').disabled=!reviewed;}
 });
 return {snapshot,characters,refresh};
}
