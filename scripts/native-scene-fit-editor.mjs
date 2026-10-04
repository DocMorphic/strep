const clone=x=>structuredClone(x);
const key=x=>JSON.stringify(x,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
const hash=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
function numbers(raw){const text=String(raw).trim(),parts=text.split(/[\s,]+/),values=parts.map(Number);if(!text||!values.every(Number.isFinite))throw Error('Enter finite motion times.');return values;}
export function stagedScene(review){
 if(review?.status!=='complete'||review.native_conditions_pass!==true||review.geometry_conditions_pass!==true||review.quality_approved!==false||review.original_selected!==true||typeof review.id!=='string'||!/^[A-Za-z0-9_-]{1,100}$/.test(review.id))throw Error('The proposal must pass its recorded native and geometry checks before staging.');
 const request=review.authoring_request;if(request?.schema!=='strep-studio-native-scene-fit-v1')throw Error('Source-bound correction request is missing.');
 const draft=clone(request.draft);delete draft.contact_revision;
 if(key(Object.keys(review.actors??{}).sort())!==key(Object.keys(draft.scene.actors).sort()))throw Error('Complete character proposals are required.');
 for(const [name,actor] of Object.entries(review.actors)){
  if(actor.original_sha256!==draft.scene.actors[name].sha256||!hash(actor.candidate_sha256)||typeof actor.candidate_url!=='string'||!actor.candidate_url.startsWith(`/files/native-scene-fit-jobs/${review.id}/`)||
     /[?#\\]/.test(actor.candidate_url)||actor.candidate_url.split('/').some(p=>p==='..'||p==='.'||p.includes('%'))||
     !review.downloads?.some(d=>d.url===actor.candidate_url&&d.sha256===actor.candidate_sha256))throw Error('Character proposal receipt is missing or changed.');
  draft.scene.actors[name].glb=actor.candidate_url;draft.scene.actors[name].sha256=actor.candidate_sha256;
 }
 return draft;
}
export function createNativeSceneFitEditor({document=globalThis.document,api,post,getDraft,setDraft,download=saveJSON}={}){
 const el=n=>document.getElementById('nativeSceneFit'+n);let catalog=null,stamp=null,selections={},tracks=[],busy=false,serial=0,review=null;
 const status=text=>{el('Status').textContent=text;};
 const guard=fn=>async()=>{try{await fn();}catch(error){status(error.message);}};
 function options(name,values,empty=false){const chosen=el(name).value;el(name).replaceChildren(...values.map(v=>{const option=document.createElement('option');option.value=v;option.textContent=v||'Fresh correction from submitted clips';return option;}));if(values.includes(chosen))el(name).value=chosen;else if(empty)el(name).value='';}
 function drawSelections(){el('Selections').replaceChildren(...Object.entries(selections).map(([name,a])=>{const p=document.createElement('p');p.textContent=`${name}: ${a.tracks.length} tracks · ${3*(a.knots_s.length-2)*a.tracks.length} controls`;return p;}));}
 function drawActor(){
  const name=el('Actor').value,a=catalog?.actors[name];tracks=[];el('Tracks').replaceChildren();if(!a)return;
  const saved=selections[name];el('Window').value=(saved?.window_s??[0,catalog.duration_s]).join(', ');
  el('Knots').value=(saved?.knots_s??[0,catalog.duration_s/3,catalog.duration_s*2/3,catalog.duration_s]).join(', ');
  el('Protected').value=JSON.stringify(saved?.protected_s??[]);el('Displacement').value=(saved?.maximum_joint_displacement_m??.15)*1000;
  for(const channel of a.channels){const row=document.createElement('label');row.className='small';row.style.display='block';const box=document.createElement('input');box.type='checkbox';box.disabled=!channel.eligible;
   const previous=saved?.tracks.find(t=>t.node===channel.node&&t.path===channel.path);box.checked=!!previous;
   const bound=document.createElement('input');bound.type='number';bound.min=channel.path==='rotation'?'0.000001':'0.001';bound.max=channel.path==='rotation'?'45':'220';bound.step='any';bound.value=previous?(channel.path==='rotation'?previous.maximum_change:previous.maximum_change*1000):(channel.path==='rotation'?20:50);bound.disabled=!box.checked||!channel.eligible;
   box.onchange=()=>{bound.disabled=!box.checked;};row.append(box,document.createTextNode(` ${channel.name} [${channel.node}] · ${channel.path} ${channel.eligible?'':channel.reason} `),bound);el('Tracks').append(row);tracks.push({channel,box,bound});
  }
 }
 async function load(){
  const draft=clone(getDraft()),before=key(draft),token=++serial;const response=await post('/api/native-scene-fit-catalog',draft);
  if(token!==serial||before!==key(getDraft()))throw Error('Scene changed while loading joints; load it again.');
  if(response?.schema!=='strep-studio-native-scene-fit-catalog-v1'||!Number.isFinite(response.duration_s)||response.duration_s!==draft.scene.duration_s||key(Object.keys(response.actors??{}).sort())!==key(Object.keys(draft.scene.actors).sort()))throw Error('Invalid scene joint catalog.');
  for(const [name,a] of Object.entries(response.actors)){
   if(a.sha256!==draft.scene.actors[name].sha256||!Array.isArray(a.channels)||new Set(a.channels.map(c=>`${c.node}:${c.path}`)).size!==a.channels.length||a.channels.some(c=>!Number.isInteger(c.node)||c.node<0||!['rotation','translation'].includes(c.path)||typeof c.eligible!=='boolean'||typeof c.name!=='string'))throw Error('Scene joint catalog changed.');
   if(catalog?.actors[name]?.sha256!==a.sha256)delete selections[name];
  }
  for(const name of Object.keys(selections))if(!response.actors[name])delete selections[name];
  catalog=response;stamp=before;options('Actor',Object.keys(catalog.actors));drawActor();drawSelections();status('Select native joint channels and save explicit bounds for each character to edit.');
 }
 function saveActor(){
  if(!catalog||stamp!==key(getDraft()))throw Error('Load the current scene joints first.');
  const window=numbers(el('Window').value),knots=numbers(el('Knots').value),protectedTimes=JSON.parse(el('Protected').value),displacement=Number(el('Displacement').value)/1000;
  const selected=tracks.filter(t=>t.box.checked).map(t=>({node:t.channel.node,path:t.channel.path,maximum_change:Number(t.bound.value)/(t.channel.path==='rotation'?1:1000)}));
  if(window.length!==2||!Array.isArray(protectedTimes)||knots.length<3||knots.length>12||!selected.length||selected.length>16||!Number.isFinite(displacement)||displacement<=0||displacement>.22||selected.some(t=>!Number.isFinite(t.maximum_change)||t.maximum_change<=0||t.maximum_change>(t.path==='rotation'?45:.22)))throw Error('Choose 1–16 tracks, 3–12 control times and positive bounds within the displayed limits.');
  if(!(0<=window[0]&&window[0]<window[1]&&window[1]<=catalog.duration_s)||knots[0]!==window[0]||knots.at(-1)!==window[1]||knots.some((v,i)=>i>0&&v<=knots[i-1])||protectedTimes.some(s=>!Array.isArray(s)||s.length!==2||s.some(v=>typeof v!=='number'||!Number.isFinite(v))||!(0<=s[0]&&s[0]<=s[1]&&s[1]<=catalog.duration_s)))throw Error('Use ordered control times with exact edit endpoints and protected ranges inside the clip.');
  selections[el('Actor').value]={window_s:window,protected_s:protectedTimes,knots_s:knots,tracks:selected,maximum_joint_displacement_m:displacement};drawSelections();status('Explicit character bounds saved.');
 }
 function request(){
  const draft=clone(getDraft());if(!catalog||stamp!==key(draft))throw Error('Scene changed; reload its joints before proposing a correction.');
  if(!Object.keys(selections).length)throw Error('Save bounds for at least one character.');
  const controls=Object.values(selections).reduce((n,a)=>n+3*(a.knots_s.length-2)*a.tracks.length,0);
  if(controls>96)throw Error('At most 96 controls are supported; reduce tracks or interior control times.');
  const iterations=Number(el('Iterations').value);if(!Number.isInteger(iterations)||iterations<1||iterations>16)throw Error('Choose 1–16 correction iterations.');
  return {schema:'strep-studio-native-scene-fit-v1',draft,actors:clone(selections),options:{iterations},resume_from:el('Resume').value||null};
 }
 async function refresh(){const data=await api('/api/native-scene-fit-jobs');options('Jobs',data.jobs.map(j=>j.id));options('Resume',['',...data.jobs.filter(j=>j.status==='complete').map(j=>j.id)],true);return data;}
 el('Load').onclick=guard(load);el('Actor').onchange=drawActor;el('SaveActor').onclick=guard(saveActor);
 el('RemoveActor').onclick=guard(()=>{delete selections[el('Actor').value];drawActor();drawSelections();});
 el('Save').onclick=guard(()=>download(request()));el('Refresh').onclick=guard(refresh);
 el('LoadResume').onclick=guard(async()=>{const id=el('Resume').value;if(!id)throw Error('Select a completed correction to continue.');
  const before=key(getDraft()),value=await api(`/api/native-scene-fit-review?id=${encodeURIComponent(id)}`);if(value.id!==id||el('Resume').value!==id||before!==key(getDraft()))throw Error('Continuation selection or scene changed.');
  if(value.status!=='complete'||value.authoring_request?.schema!=='strep-studio-native-scene-fit-v1'||value.quality_approved!==false)throw Error('Completed source-bound correction required.');
  setDraft(clone(value.authoring_request.draft));selections=clone(value.authoring_request.actors);catalog=null;
  await load();selections=clone(value.authoring_request.actors);drawActor();drawSelections();el('Resume').value=id;el('Iterations').value=value.authoring_request.options.iterations;status('Continuation loaded. Original clip epochs and edit permissions stay bound; explicit patch revisions are checked separately.');
 });
 el('Build').onclick=guard(async()=>{if(busy)throw Error('Wait for this request.');const value=request();busy=true;el('Build').disabled=true;
  try{const job=await post('/api/native-scene-fits',value);await refresh();el('Jobs').value=job.id;status('Character correction started. Refresh results to inspect original clips, proposals and failures.');}finally{busy=false;el('Build').disabled=false;}
 });
 el('Review').onclick=guard(async()=>{const id=el('Jobs').value;if(!id)throw Error('Select a character correction.');review=null;el('Stage').disabled=true;el('Results').replaceChildren();
  const value=await api(`/api/native-scene-fit-review?id=${encodeURIComponent(id)}`);if(value.id!==id||el('Jobs').value!==id)throw Error('Correction selection changed.');
  const p=document.createElement('p');p.textContent=value.status==='complete'?`Native conditions: ${value.native_conditions_pass?'pass':'fail'}. Sampled geometry: ${value.geometry_conditions_pass?'pass':'fail'}. Original clips remain selected. Import and motion-quality review are required.`:`${value.status}: ${value.stage||value.error||'waiting'}`;el('Results').append(p);
  for(const d of value.downloads??[]){const a=document.createElement('a');a.className='btn';a.href=d.url;a.download='';a.textContent=d.label;el('Results').append(a);}
  review=value;try{stagedScene(value);el('Stage').disabled=false;}catch{}status(p.textContent);
 });
 el('Stage').onclick=guard(async()=>{const before=review;if(!before||el('Jobs').value!==before.id)throw Error('Review the selected correction first.');
  const sceneBefore=key(getDraft());
  const updated=await api(`/api/native-scene-fit-review?id=${encodeURIComponent(before.id)}`);
  if(review!==before||key(updated)!==key(before)||el('Jobs').value!==before.id||sceneBefore!==key(getDraft()))throw Error('Correction or scene changed; review its results again.');
  setDraft(stagedScene(updated));catalog=null;stamp=null;selections={};el('Stage').disabled=true;status('All proposals staged in a new scene draft. Build and review its scene assets before game use; the original job is retained.');
 });
 return {load,refresh,request};
}
function saveJSON(value){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'})),a=globalThis.document.createElement('a');a.href=url;a.download='native-character-correction.json';a.click();URL.revokeObjectURL(url);}
