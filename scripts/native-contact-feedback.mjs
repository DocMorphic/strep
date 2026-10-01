// Developer observations only; exports do not count as animator approval.
const digest=value=>typeof value==='string'&&/^[0-9a-f]{64}$/.test(value);
export function observation(source,draft,at=new Date().toISOString()){
  if(!source||!digest(source.build_sha256)||!digest(source.manifest_sha256)||!digest(source.source_result_sha256)||typeof source.version!=='string'||! /^[0-7]$/.test(source.version)||typeof source.comparison_url!=='string'||!source.comparison_url.endsWith('/viewer.html')||!Array.isArray(source.actors)||source.actors.length!==2)throw Error('Verified comparison source required');
  for(const [i,a] of source.actors.entries()){
    const p=a.placement,t=p?.translation_m,q=p?.rotation_xyzw;
    if(!digest(a.sha256)||a.url!==`assets/${source.version}-${i}.glb`||!Array.isArray(t)||t.length!==3||!Array.isArray(q)||q.length!==4||![...t,...q].every(v=>typeof v==='number'&&Number.isFinite(v))||Math.abs(Math.hypot(...q)-1)>1e-6)throw Error('Exact paired assets and placements required');
  }
  const duration=source.duration_s,event=source.event_time_s,start=draft.start_s,end=draft.end_s;
  if(![duration,event,start,end].every(v=>typeof v==='number'&&Number.isFinite(v))||duration<=0||event<0||event>duration||start<0||start>end||end>duration)throw Error('Observation times must be within the native clip');
  if(typeof draft.reviewer!=='string'||!draft.reviewer.trim()||draft.reviewer.length>100||typeof draft.notes!=='string'||!draft.notes.trim()||draft.notes.length>10000)throw Error('Reviewer and observation required');
  return {schema_version:1,kind:'native_contact_developer_observation',at,source:structuredClone(source),interval_s:[start,end],reviewer:draft.reviewer.trim(),notes:draft.notes.trim(),independent_human:false,cleanup_test_performed:false,quality_approved:false};
}

export function createFeedback({getTime,document=globalThis.document,storage=globalThis.localStorage,download}={}){
  const el=id=>document.getElementById(id);let source=null,key=null;
  const draft=()=>({reviewer:el('nativeReviewer').value,notes:el('nativeReviewNote').value,start_s:el('nativeNoteStart').value===''?NaN:Number(el('nativeNoteStart').value),end_s:el('nativeNoteEnd').value===''?NaN:Number(el('nativeNoteEnd').value)});
  function refresh(){
    let enabled=false;
    if(source){try{observation(source,draft());enabled=true;}catch{}}
    el('nativeExportFeedback').disabled=!enabled;
    if(source){try{storage?.setItem(key,JSON.stringify(draft()));}catch{}}
  }
  for(const id of ['nativeReviewer','nativeReviewNote','nativeNoteStart','nativeNoteEnd'])el(id).addEventListener('input',refresh);
  el('nativeNoteHere').onclick=()=>{if(!source)return;const time=getTime();el('nativeNoteStart').value=time;el('nativeNoteEnd').value=time;refresh();};
  el('nativeExportFeedback').onclick=()=>{try{download(observation(source,draft()));el('nativeFeedbackStatus').textContent='Observation downloaded. This does not submit or approve a review.';}catch(error){el('nativeFeedbackStatus').textContent=error.message;}};
  return {bind(next){
    source=next?structuredClone(next):null;key=source?'strep-native-observation:'+JSON.stringify(source):null;
    let saved;try{saved=JSON.parse(storage?.getItem(key)||'null');}catch{}
    el('nativeFeedbackFields').disabled=!source;
    el('nativeReviewer').value=saved?.reviewer||'';el('nativeReviewNote').value=saved?.notes||'';
    el('nativeNoteStart').value=saved?.start_s??source?.event_time_s??'';el('nativeNoteEnd').value=saved?.end_s??source?.event_time_s??'';
    el('nativeFeedbackStatus').textContent=source?'Record an observation for these exact assets.':'Load a verified version to record an observation.';refresh();
  }};
}
