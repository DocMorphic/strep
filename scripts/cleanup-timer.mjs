// Active intervals are explicitly started/paused by the reviewer, not inferred editing.
const hash=/^[a-f0-9]{64}$/;
const clone=value=>structuredClone(value);
export function createCleanupSession(context,limit=null,id=crypto.randomUUID()){
  if(typeof id!=='string'||!id||id.length>120)throw Error('Session identifier required.');
  if(!context||Object.keys(context).sort().join()!==['packet_id','manifest_sha256','clip_id','source_sha256','review_type','reviewer_id'].sort().join()||
      !hash.test(context.manifest_sha256)||!hash.test(context.source_sha256)||!['developer','independent'].includes(context.review_type)||
      ['packet_id','clip_id','reviewer_id'].some(k=>typeof context[k]!=='string'||!context[k].trim()||context[k].length>120))throw Error('A verified clip and reviewer identifier are required.');
  if(limit!==null&&(!Number.isFinite(limit)||limit<=0))throw Error('Choose a positive time limit before starting, or leave it empty.');
  return {schema:'strep-cleanup-timing-v1',session_id:id,context:clone(context),preselected_limit_seconds:limit,
    state:'new',segments:[],open:null,interruptions:[],finished_at:null,output_artifact:null,quality_approved:false,release_approved:false};
}
function clock(ms,at){if(!Number.isFinite(ms)||ms<0||typeof at!=='string'||!Number.isFinite(Date.parse(at)))throw Error('Valid monotonic clock and timestamp required.');}
export function startCleanup(session,page,ms,at){
  clock(ms,at);if(!['new','paused'].includes(session.state)||!page)throw Error('Pause or finish the current interval first.');
  const previous=session.segments.filter(s=>s.page_id===page).at(-1);if(previous&&ms<previous.end_ms)throw Error('Monotonic clock moved backwards.');
  session.open={page_id:page,start_ms:ms,started_at:at};session.state='running';return session;
}
export function pauseCleanup(session,page,ms,at){
  clock(ms,at);if(session.state!=='running'||session.open?.page_id!==page||ms<session.open.start_ms)throw Error('Matching running interval required.');
  session.segments.push({...session.open,end_ms:ms,ended_at:at});session.open=null;session.state='paused';return session;
}
export function recoverCleanup(session,at){
  if(session.state==='running'){
    session.interruptions.push({...session.open,detected_at:at});session.open=null;session.state='paused';
  }
  return session;
}
export function finishCleanup(session,page,ms,at){
  clock(ms,at);if(session.state==='running')pauseCleanup(session,page,ms,at);
  if(session.state!=='paused'||!session.segments.length)throw Error('Start and pause actual cleanup before finishing.');
  session.state='finished';session.finished_at=at;return session;
}
export function activeCleanupSeconds(session){return session.segments.reduce((sum,s)=>sum+(s.end_ms-s.start_ms)/1000,0);}
export function cleanupTrace(session){
  validateStoredCleanup(session);
  if(session.state!=='finished')throw Error('Finish the timer before exporting its trace.');
  return {...clone(session),active_seconds:activeCleanupSeconds(session),duration_complete:session.interruptions.length===0};
}
export function validateStoredCleanup(session){
  const base=createCleanupSession(session.context,session.preselected_limit_seconds,session.session_id);
  if(Object.keys(session).sort().join()!==Object.keys(base).sort().join()||session.schema!==base.schema||
      session.quality_approved!==false||session.release_approved!==false||!['new','running','paused','finished'].includes(session.state)||
      !Array.isArray(session.segments)||session.segments.length>10000||!Array.isArray(session.interruptions)||session.interruptions.length>10000)throw Error('Invalid saved cleanup timer.');
  const checkOpen=s=>{if(!s||typeof s.page_id!=='string'||!s.page_id||s.page_id.length>120)throw Error('Invalid timing page.');clock(s.start_ms,s.started_at);};
  const ends=new Map();
  for(const s of session.segments){checkOpen(s);clock(s.end_ms,s.ended_at);if(s.end_ms<s.start_ms||s.start_ms<(ends.get(s.page_id)||0))throw Error('Invalid active intervals.');ends.set(s.page_id,s.end_ms);}
  for(const s of session.interruptions){checkOpen(s);clock(s.start_ms,s.detected_at);}
  if(session.state==='running'){checkOpen(session.open);}else if(session.open!==null)throw Error('Stopped timer has an open interval.');
  if(session.state==='finished')clock(0,session.finished_at);else if(session.finished_at!==null)throw Error('Unexpected finish timestamp.');
  const a=session.output_artifact;
  if(a!==null&&(!a||Object.keys(a).sort().join()!==['name','bytes','sha256'].sort().join()||typeof a.name!=='string'||!a.name.toLowerCase().endsWith('.glb')||
      !Number.isInteger(a.bytes)||a.bytes<=0||a.bytes>128*1024**2||!hash.test(a.sha256)))throw Error('Invalid edited artifact fingerprint.');
  return session;
}

export function mountCleanupTimer({container,context,onMeasured,storage=localStorage,doc=document,readClock=()=>performance.now(),wallClock=()=>new Date().toISOString(),pageId=crypto.randomUUID(),schedule=fn=>setInterval(fn,250),cancel=clearInterval}){
  let selected=null,session=null,storeKey=null;const page=pageId;
  const make=(tag,text)=>{const e=doc.createElement(tag);if(text)e.textContent=text;container.append(e);return e;};
  make('p','Optional cleanup stopwatch: start only while editing the downloaded clip. Pause for breaks and review playback. Export its trace with your ratings.');
  const label=make('label','Timer limit in seconds (set before Start)'),limit=doc.createElement('input');limit.type='number';limit.min='0';limit.step='any';label.append(limit);
  const display=make('output','No cleanup recorded'),status=make('p');status.setAttribute('role','status');
  const controls=make('div');controls.className='row';
  const button=(name,action)=>{const e=doc.createElement('button');e.type='button';e.textContent=name;e.onclick=async()=>{try{await action();}catch(error){status.textContent=error.message;}render();};controls.append(e);return e;};
  const persist=()=>{if(storeKey)try{storage.setItem(storeKey,JSON.stringify(session));}catch{status.textContent='Timer storage failed. Keep this page open and export the trace before leaving.';}};
  const start=button('Start / resume cleanup',()=>{
    const c=context();if(!c)throw Error('Load a verified clip first.');
    if(!session)session=createCleanupSession(c,limit.value===''?null:Number(limit.value));
    if(JSON.stringify(c)!==JSON.stringify(session.context))throw Error('Reviewer or clip changed; restore the original selection.');
    startCleanup(session,page,readClock(),wallClock());persist();
    status.textContent='Timer running. It records the interval you designate as editing; it cannot observe your editor.';
  });
  const pause=button('Pause cleanup',()=>{pauseCleanup(session,page,readClock(),wallClock());persist();status.textContent='Paused. Breaks and review playback do not add time.';});
  const finish=button('Finish cleanup timer',()=>{finishCleanup(session,page,readClock(),wallClock());persist();status.textContent='Timing finished. Record your own outcome and operations; completion is not inferred.';});
  const outputLabel=make('label','Edited GLB (optional for timing; required to verify a completed cleanup)'),file=doc.createElement('input');file.type='file';file.accept='.glb';outputLabel.append(file);
  file.onchange=async()=>{try{
    const chosen=file.files?.[0];if(!session||session.state==='finished')throw Error('Attach the edited GLB before finishing.');
    if(!chosen||!chosen.name.toLowerCase().endsWith('.glb')||chosen.size>128*1024**2)throw Error('Select a GLB up to 128 MiB.');
    const target=session;
    const bytes=await chosen.arrayBuffer(),sha256=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
    if(session!==target||session.state==='finished')throw Error('Cleanup selection changed while hashing; select the file again before finishing.');
    session.output_artifact={name:chosen.name,bytes:chosen.size,sha256};persist();status.textContent='Edited file fingerprint saved locally. No file is uploaded and no motion quality is inferred.';
  }catch(error){status.textContent=error.message;}render();};
  const use=button('Use measured time in review',()=>{
    const trace=cleanupTrace(session);if(!trace.duration_complete)throw Error('An interrupted interval has unknown duration. Keep the partial trace; do not use it as complete cleanup time.');
    if(JSON.stringify(context())!==JSON.stringify(session.context))throw Error('Reviewer or clip changed.');
    onMeasured(trace.active_seconds,trace.preselected_limit_seconds);status.textContent='Measured seconds copied. Choose your actual outcome and describe the operations yourself.';
  });
  const download=button('Export cleanup timing trace',()=>{
    const trace=cleanupTrace(session),url=URL.createObjectURL(new Blob([JSON.stringify(trace,null,2)+'\n'],{type:'application/json'}));
    const a=doc.createElement('a');a.href=url;a.download=`cleanup-timing-${trace.context.clip_id}-${trace.session_id}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    status.textContent='Timing trace downloaded. Submit it with the ratings and edited GLB when applicable.';
  });
  function render(){
    const total=session?activeCleanupSeconds(session)+(session.open?(readClock()-session.open.start_ms)/1000:0):0;
    display.textContent=`${total.toFixed(2)} active seconds · ${session?.state||'not started'}`;
    if(session?.interruptions.length)display.textContent+=' · interrupted interval excluded; total incomplete';
    start.disabled=!selected||!context()||!['new','paused'].includes(session?.state||'new');pause.disabled=session?.state!=='running';
    finish.disabled=!['running','paused'].includes(session?.state);limit.disabled=!!session;file.disabled=!session||session.state==='finished';
    use.disabled=session?.state!=='finished'||session.interruptions.length>0;download.disabled=session?.state!=='finished';
  }
  function bind(next){
    if(session?.state==='running'){pauseCleanup(session,page,readClock(),wallClock());persist();}
    selected=next;session=null;limit.value='';file.value='';storeKey=next?'strep-cleanup-timer:'+JSON.stringify(next):null;
    if(storeKey)try{const raw=storage.getItem(storeKey);if(raw){session=validateStoredCleanup(JSON.parse(raw));if(JSON.stringify(session.context)!==JSON.stringify(next))throw Error('Stored timer belongs to another clip.');recoverCleanup(session,wallClock());limit.value=session.preselected_limit_seconds??'';persist();}}catch(error){session=null;status.textContent='Timer could not be restored: '+error.message;}
    render();
  }
  const interval=schedule(render);render();
  return {bind,refresh:render,destroy(){cancel(interval);}};
}
