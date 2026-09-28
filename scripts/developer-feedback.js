// Non-blind observations only. These never enter the independent-review rubric.
function developerObservation(context, draft, timestamp=new Date().toISOString()) {
 const hash=/^[0-9a-f]{64}$/;
 if(!context||!hash.test(context.glb_sha256)||!hash.test(context.catalog_sha256)||!Number.isInteger(context.frames)||context.frames<1)throw Error('Load a verified motion first.');
 if(typeof draft.reviewer!=='string'||!draft.reviewer.trim()||draft.reviewer.length>120)throw Error('Enter your reviewer name or alias.');
 if(typeof draft.notes!=='string'||!draft.notes.trim()||draft.notes.length>4000)throw Error('Describe your observation (up to 4,000 characters).');
 if(!Number.isInteger(draft.start)||!Number.isInteger(draft.end)||draft.start<0||draft.end<draft.start||draft.end>=context.frames)throw Error('Choose an ordered frame range within this clip.');
 return {schema:'strep-developer-observation-v1',created_at:timestamp,reviewer_id:draft.reviewer.trim(),
  source:{...context},frame_range:{start:draft.start,end_inclusive:draft.end},notes:draft.notes.trim(),
  review_type:'non_blind_developer',independent_human:false,cleanup_test_performed:false,quality_approved:false};
}

function setupDeveloperFeedback(getContext,getFrame) {
 const el=id=>document.getElementById(id),field=el('correctionFeedbackFields'),status=el('correctionFeedbackStatus');
 let current=null,key=null;
 const ids=['correctionReviewer','correctionNoteStart','correctionNoteEnd','correctionNote'];
 const draft=()=>({reviewer:el(ids[0]).value,start:el(ids[1]).value===''?NaN:Number(el(ids[1]).value),end:el(ids[2]).value===''?NaN:Number(el(ids[2]).value),notes:el(ids[3]).value});
 function valid(){try{developerObservation(current,draft());return true;}catch{return false;}}
 function changed(){
  el('correctionExportFeedback').disabled=!valid();
  if(!key)return;
  try{localStorage.setItem(key,JSON.stringify(draft()));status.textContent='Draft saved in this browser. Export a file to share your feedback.';}
  catch{status.textContent='Browser storage is unavailable. Export your feedback before leaving this page.';}
 }
 function refresh(){
  const next=getContext(),nextKey=next?`strep-developer-note:${next.catalog_sha256}:${next.case_id}:${next.variant}:${next.glb_sha256}`:null;
  if(nextKey===key){el('correctionExportFeedback').disabled=!valid();return;}
  current=next;key=nextKey;field.disabled=!current;
  el(ids[0]).value='';el(ids[3]).value='';
  const frame=Math.max(0,Math.min(current?.frames-1||0,Math.floor(getFrame())));
  el(ids[1]).value=frame;el(ids[2]).value=frame;
  for(const id of ids.slice(1,3))el(id).max=Math.max(0,(current?.frames||1)-1);
  status.textContent=current?'Notes refer to this version only. No ratings are prefilled.':'Load a verified motion to add feedback.';
  if(key){try{const saved=JSON.parse(localStorage.getItem(key)||'null');
   if(saved&&typeof saved.reviewer==='string'&&typeof saved.notes==='string'){
    el(ids[0]).value=saved.reviewer;el(ids[3]).value=saved.notes;
    el(ids[1]).value=Number.isInteger(saved.start)?saved.start:frame;el(ids[2]).value=Number.isInteger(saved.end)?saved.end:frame;
    status.textContent='Restored your draft for this exact clip version.';
   }
  }catch{status.textContent='Draft could not be restored. You can still write and export feedback.';}}
  el('correctionExportFeedback').disabled=!valid();
 }
 for(const id of ids)el(id).addEventListener('input',changed);
 el('correctionNoteHere').onclick=()=>{el(ids[1]).value=el(ids[2]).value=Math.floor(getFrame());changed();};
 el('correctionExportFeedback').onclick=()=>{
  try{
   const result=developerObservation(current,draft());
   const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)+'\n'],{type:'application/json'}));
   const a=document.createElement('a');a.href=url;a.download=`developer-feedback-${current.case_id}-${current.variant}.json`;a.click();
   setTimeout(()=>URL.revokeObjectURL(url),1000);status.textContent='Feedback file downloaded. This is a developer observation, not an independent rating or release approval.';
  }catch(error){status.textContent=error.message;}
 };
 field.disabled=true;el('correctionExportFeedback').disabled=true;
 return {refresh};
}
