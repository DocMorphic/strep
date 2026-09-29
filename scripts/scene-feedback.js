// Observations describe the exact loaded scene and all actors, never release approval.
async function sceneReviewBytes(url){
 const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw Error('Saved scene asset unavailable');
 const bytes=await response.arrayBuffer(),sha256=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
 return {bytes,sha256};
}
function sceneReviewEmbeddedGLB(bytes){
 try{const v=new DataView(bytes);if(v.getUint32(0,true)!==0x46546c67||v.getUint32(4,true)!==2||v.getUint32(8,true)!==bytes.byteLength||v.getUint32(16,true)!==0x4e4f534a)return false;
  const doc=JSON.parse(new TextDecoder().decode(bytes.slice(20,20+v.getUint32(12,true))));
  return [...(doc.buffers||[]),...(doc.images||[])].every(row=>!row.uri||row.uri.startsWith('data:'));
 }catch{return false;}
}
function sceneObservation(source,draft,timestamp=new Date().toISOString()){
 const hash=/^[0-9a-f]{64}$/;
 if(!source||!hash.test(source.bundle_sha256)||!Number.isInteger(source.frames)||source.frames<1||source.fps!==30||!source.actors?.length||source.actors.some(a=>!hash.test(a.glb_sha256)))throw Error('Load a saved scene before recording feedback.');
 if(typeof draft.reviewer!=='string'||!draft.reviewer.trim()||draft.reviewer.length>120)throw Error('Enter your name or alias.');
 if(typeof draft.notes!=='string'||!draft.notes.trim()||draft.notes.length>4000)throw Error('Describe your observation (up to 4,000 characters).');
 if(!Number.isInteger(draft.start)||!Number.isInteger(draft.end)||draft.start<0||draft.end<draft.start||draft.end>=source.frames)throw Error('Choose a frame range within this scene.');
 return {schema:'strep-scene-observation-v1',created_at:timestamp,reviewer_id:draft.reviewer.trim(),source:structuredClone(source),frame_range:{start:draft.start,end_inclusive:draft.end},notes:draft.notes.trim(),review_type:'non_blind_developer',independent_human:false,cleanup_test_performed:false,quality_approved:false};
}
function setupSceneFeedback(getFrame){
 const el=id=>document.getElementById('scene'+id),status=el('FeedbackStatus');let source=null,key=null;
 const fields=['Reviewer','NoteStart','NoteEnd','ReviewNote'];
 const draft=()=>({reviewer:el('Reviewer').value,notes:el('ReviewNote').value,start:el('NoteStart').value===''?NaN:Number(el('NoteStart').value),end:el('NoteEnd').value===''?NaN:Number(el('NoteEnd').value)});
 function valid(){try{sceneObservation(source,draft());return true;}catch{return false;}}
 function changed(){el('ExportFeedback').disabled=!valid();if(!key)return;try{localStorage.setItem(key,JSON.stringify(draft()));status.textContent='Draft saved in this browser. Export it to share your feedback.';}catch{status.textContent='Storage unavailable. Export your feedback before leaving.';}}
 function bind(next){
  source=next?structuredClone(next):null;key=source?'strep-scene-note:'+JSON.stringify(source):null;
  el('FeedbackFields').disabled=!source;el('Reviewer').value='';el('ReviewNote').value='';
  const frame=Math.max(0,Math.min(source?.frames-1||0,Math.floor(getFrame())));
  for(const id of ['NoteStart','NoteEnd']){el(id).value=frame;el(id).max=source?source.frames-1:0;}
  status.textContent=source?'Notes refer to this saved scene and these actor versions.':'Reload a saved scene to add notes. Unsaved placement changes cannot use saved-scene feedback.';
  if(key)try{const saved=JSON.parse(localStorage.getItem(key)||'null');if(saved&&typeof saved.reviewer==='string'&&typeof saved.notes==='string'){el('Reviewer').value=saved.reviewer;el('ReviewNote').value=saved.notes;el('NoteStart').value=Number.isInteger(saved.start)?saved.start:frame;el('NoteEnd').value=Number.isInteger(saved.end)?saved.end:frame;status.textContent='Restored your draft for this exact scene and actor versions.';}}catch{status.textContent='Draft could not be restored. You can still write and export notes.';}
  el('ExportFeedback').disabled=!valid();
 }
 for(const id of fields)el(id).addEventListener('input',changed);
 el('NoteHere').onclick=()=>{el('NoteStart').value=el('NoteEnd').value=Math.floor(getFrame());changed();};
 el('ExportFeedback').onclick=()=>{try{const result=sceneObservation(source,draft()),url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)+'\n'],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='scene-developer-feedback.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);status.textContent='Feedback downloaded. It does not count as an independent rating or timed cleanup test.';}catch(error){status.textContent=error.message;}};
 bind(null);return {bind};
}
