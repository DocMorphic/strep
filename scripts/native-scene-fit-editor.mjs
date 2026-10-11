const clone=x=>structuredClone(x);
const key=x=>JSON.stringify(x,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
const hash=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
function numbers(raw){const text=String(raw).trim(),parts=text.split(/[\s,]+/),values=parts.map(Number);if(!text||!values.every(Number.isFinite))throw Error('Enter finite motion times.');return values;}
export function stagedScene(review){
 if(review?.status!=='complete'||review.native_conditions_pass!==true||review.geometry_conditions_pass!==true||review.quality_approved!==false||review.original_selected!==true||typeof review.id!=='string'||!/^[A-Za-z0-9_-]{1,100}$/.test(review.id))throw Error('The proposal must pass its recorded native and geometry checks before staging.');
 const request=review.authoring_request;if(!['strep-studio-native-scene-fit-v1','strep-studio-native-scene-fit-v2'].includes(request?.schema))throw Error('Source-bound correction request is missing.');
 if(request.schema==='strep-studio-native-scene-fit-v2'&&review.rotation_speed_conditions_pass!==true)throw Error('The proposal must pass its authored turning-speed limits before staging.');
 const draft=clone(request.draft);delete draft.contact_revision;
 if(key(Object.keys(review.actors??{}).sort())!==key(Object.keys(draft.scene.actors).sort()))throw Error('Complete character proposals are required.');
 for(const [name,actor] of Object.entries(review.actors)){
  if(actor.original_sha256!==draft.scene.actors[name].sha256||!hash(actor.candidate_sha256)||typeof actor.candidate_url!=='string'||!actor.candidate_url.startsWith(`/files/native-scene-fit-jobs/${review.id}/`)||
     /[?#\\]/.test(actor.candidate_url)||actor.candidate_url.split('/').some(p=>p==='..'||p==='.'||p.includes('%'))||
     !review.downloads?.some(d=>d.url===actor.candidate_url&&d.sha256===actor.candidate_sha256))throw Error('Character proposal receipt is missing or changed.');
  draft.scene.actors[name].glb=actor.candidate_url;draft.scene.actors[name].sha256=actor.candidate_sha256;
 }
 if(request.schema==='strep-studio-native-scene-fit-v2'){
  if(!Array.isArray(request.rotation_speed_limits)||!request.rotation_speed_limits.length||request.rotation_speed_limits.length>64)throw Error('Complete export turning-speed limits are required.');
  const merged=new Map((draft.rotation_speed_limits??[]).map(t=>[`${t.actor}:${t.node}`,clone(t)]));
  if(merged.size!==(draft.rotation_speed_limits??[]).length||new Set(request.rotation_speed_limits.map(t=>`${t.actor}:${t.node}`)).size!==request.rotation_speed_limits.length)throw Error('Choose each export joint speed limit once.');
  for(const t of request.rotation_speed_limits){if(!draft.scene.actors[t.actor]||!Number.isInteger(t.node)||t.node<0||typeof t.maximum_degrees_per_second!=='number'||!Number.isFinite(t.maximum_degrees_per_second)||t.maximum_degrees_per_second<0)throw Error('Explicit character joint and finite nonnegative export speed required.');merged.set(`${t.actor}:${t.node}`,clone(t));}
  draft.schema='strep-studio-native-scene-v2';draft.rotation_speed_limits=[...merged.values()];
  if(draft.rotation_speed_limits.length>64)throw Error('At most 64 current export turning-speed limits are supported.');
 }
 return draft;
}
export function createNativeSceneFitEditor({document=globalThis.document,api,post,getDraft,setDraft,download=saveJSON}={}){
 const el=n=>document.getElementById('nativeSceneFit'+n);let catalog=null,stamp=null,selections={},speedLimits={},tracks=[],busy=false,serial=0,review=null;
 const status=text=>{el('Status').textContent=text;};
 const guard=fn=>async()=>{try{await fn();}catch(error){status(error.message);}};
 function options(name,values,empty=false){const chosen=el(name).value;el(name).replaceChildren(...values.map(v=>{const option=document.createElement('option');option.value=v;option.textContent=v||'Fresh correction from submitted clips';return option;}));if(values.includes(chosen))el(name).value=chosen;else if(empty)el(name).value='';}
 const controlCount=a=>3*(a.knots_s.length-2)*a.tracks.length;
 const sceneControlCount=values=>Object.values(values).reduce((n,a)=>n+controlCount(a),0);
 function drawBudget(){
  const name=el('Actor').value;if(!catalog?.actors[name]){el('Budget').textContent='Load scene joints to preview timing capacity.';return;}
  try{
   const knots=numbers(el('Knots').value),selected=tracks.filter(t=>t.box.checked);
   if(knots.length<3||knots.length>12||knots.some((v,i)=>i>0&&v<=knots[i-1]))throw Error('Enter 3–12 ordered motion control times to preview capacity.');
   const current=controlCount({knots_s:knots,tracks:selected}),other=sceneControlCount(Object.fromEntries(Object.entries(selections).filter(([actor])=>actor!==name))),total=current+other;
   el('Budget').textContent=`${name}: ${selected.length} tracks × ${knots.length-2} interior times × 3 = ${current} controls. Scene after saving: ${total} / 96. Saved scene: ${sceneControlCount(selections)} / 96. ${total>96?'Reduce selected tracks or interior times before saving.':'Save character bounds to apply timing changes.'}`;
  }catch(error){el('Budget').textContent=error.message;}
 }
 function drawSelections(){el('Selections').replaceChildren(...Object.entries(selections).map(([name,a])=>{const p=document.createElement('p');p.textContent=`${name}: ${a.tracks.length} tracks · ${controlCount(a)} controls`;return p;}));drawBudget();}
 function drawActor(){
  const name=el('Actor').value,a=catalog?.actors[name];tracks=[];el('Tracks').replaceChildren();if(!a){drawBudget();return;}
  const saved=selections[name];el('Window').value=(saved?.window_s??[0,catalog.duration_s]).join(', ');
  el('Knots').value=(saved?.knots_s??[0,catalog.duration_s/3,catalog.duration_s*2/3,catalog.duration_s]).join(', ');
  el('Protected').value=JSON.stringify(saved?.protected_s??[]);el('Displacement').value=(saved?.maximum_joint_displacement_m??.15)*1000;
  for(const channel of a.channels){const row=document.createElement('label');row.className='small';row.style.display='block';const box=document.createElement('input');box.type='checkbox';box.disabled=!channel.eligible;
   const previous=saved?.tracks.find(t=>t.node===channel.node&&t.path===channel.path);box.checked=!!previous;
   const bound=document.createElement('input');bound.type='number';bound.min=channel.path==='rotation'?'0.000001':'0.001';bound.max=channel.path==='rotation'?'45':'220';bound.step='any';bound.value=previous?(channel.path==='rotation'?previous.maximum_change:previous.maximum_change*1000):(channel.path==='rotation'?20:50);bound.disabled=!box.checked||!channel.eligible;
   box.onchange=()=>{bound.disabled=!box.checked;drawBudget();};row.append(box,document.createTextNode(` ${channel.name} [${channel.node}] · ${channel.path} ${channel.eligible?'':channel.reason} `),bound);
   let speed=null;if(channel.path==='rotation'){
    speed=document.createElement('input');speed.type='number';speed.min='0';speed.step='any';speed.placeholder='No turning-speed limit';speed.value=speedLimits[name]?.[channel.node]??'';speed.disabled=!channel.eligible;speed.ariaLabel=`${channel.name} maximum turning speed in degrees per second`;
    row.append(document.createTextNode(' Maximum turning speed (°/s), optional '),speed);
   }
   el('Tracks').append(row);tracks.push({channel,box,bound,speed});
  }
  drawBudget();
 }
 async function load(){
  const draft=clone(getDraft()),before=key(draft),token=++serial;const response=await post('/api/native-scene-fit-catalog',draft);
  if(token!==serial||before!==key(getDraft()))throw Error('Scene changed while loading joints; load it again.');
  if(response?.schema!=='strep-studio-native-scene-fit-catalog-v1'||!Number.isFinite(response.duration_s)||response.duration_s!==draft.scene.duration_s||key(Object.keys(response.actors??{}).sort())!==key(Object.keys(draft.scene.actors).sort()))throw Error('Invalid scene joint catalog.');
  for(const [name,a] of Object.entries(response.actors)){
   if(a.sha256!==draft.scene.actors[name].sha256||!Array.isArray(a.channels)||new Set(a.channels.map(c=>`${c.node}:${c.path}`)).size!==a.channels.length||a.channels.some(c=>!Number.isInteger(c.node)||c.node<0||!['rotation','translation'].includes(c.path)||typeof c.eligible!=='boolean'||typeof c.name!=='string'))throw Error('Scene joint catalog changed.');
   if(catalog?.actors[name]?.sha256!==a.sha256){delete selections[name];delete speedLimits[name];for(const t of draft.rotation_speed_limits??[]){if(t.actor===name){speedLimits[name]??={};speedLimits[name][t.node]=t.maximum_degrees_per_second;}}}
  }
  for(const name of Object.keys(selections))if(!response.actors[name]){delete selections[name];delete speedLimits[name];}
  catalog=response;stamp=before;options('Actor',Object.keys(catalog.actors));drawActor();drawSelections();status('Select native joint channels and save explicit bounds for each character to edit.');
 }
 function saveActor(){
  if(!catalog||stamp!==key(getDraft()))throw Error('Load the current scene joints first.');
  const window=numbers(el('Window').value),knots=numbers(el('Knots').value),protectedTimes=JSON.parse(el('Protected').value),displacement=Number(el('Displacement').value)/1000;
  const selected=tracks.filter(t=>t.box.checked).map(t=>({node:t.channel.node,path:t.channel.path,maximum_change:Number(t.bound.value)/(t.channel.path==='rotation'?1:1000)}));
  if(window.length!==2||!Array.isArray(protectedTimes)||knots.length<3||knots.length>12||!selected.length||selected.length>16||!Number.isFinite(displacement)||displacement<=0||displacement>.22||selected.some(t=>!Number.isFinite(t.maximum_change)||t.maximum_change<=0||t.maximum_change>(t.path==='rotation'?45:.22)))throw Error('Choose 1–16 tracks, 3–12 control times and positive bounds within the displayed limits.');
  if(!(0<=window[0]&&window[0]<window[1]&&window[1]<=catalog.duration_s)||knots[0]!==window[0]||knots.at(-1)!==window[1]||knots.some((v,i)=>i>0&&v<=knots[i-1])||protectedTimes.some(s=>!Array.isArray(s)||s.length!==2||s.some(v=>typeof v!=='number'||!Number.isFinite(v))||!(0<=s[0]&&s[0]<=s[1]&&s[1]<=catalog.duration_s)))throw Error('Use ordered control times with exact edit endpoints and protected ranges inside the clip.');
  const speeds={};for(const t of tracks){if(!t.speed||t.speed.disabled||String(t.speed.value).trim()==='')continue;const maximum=Number(t.speed.value);if(!Number.isFinite(maximum)||maximum<0)throw Error('Turning-speed limits must be finite and nonnegative; leave blank to omit one.');speeds[t.channel.node]=maximum;}
  const name=el('Actor').value,proposed={window_s:window,protected_s:protectedTimes,knots_s:knots,tracks:selected,maximum_joint_displacement_m:displacement};
  const controls=sceneControlCount({...selections,[name]:proposed});
  if(controls>96)throw Error(`This scene needs ${controls} controls; at most 96 are supported. Reduce selected tracks or interior times. Saved bounds stay unchanged.`);
  selections[name]=proposed;speedLimits[name]=speeds;drawSelections();status('Explicit character bounds and turning-speed choices saved.');
 }
 function request(){
  const draft=clone(getDraft());if(!catalog||stamp!==key(draft))throw Error('Scene changed; reload its joints before proposing a correction.');
  if(!Object.keys(selections).length)throw Error('Save bounds for at least one character.');
  const controls=sceneControlCount(selections);
  if(controls>96)throw Error('At most 96 controls are supported; reduce tracks or interior control times.');
  const iterations=Number(el('Iterations').value);if(!Number.isInteger(iterations)||iterations<1||iterations>16)throw Error('Choose 1–16 correction iterations.');
  const limits=Object.entries(speedLimits).flatMap(([actor,nodes])=>Object.entries(nodes).map(([node,maximum_degrees_per_second])=>({actor,node:Number(node),maximum_degrees_per_second})));
  if(limits.length>64)throw Error('Choose at most 64 explicit joint turning-speed limits.');
  return {schema:limits.length?'strep-studio-native-scene-fit-v2':'strep-studio-native-scene-fit-v1',draft,actors:clone(selections),options:{iterations},resume_from:el('Resume').value||null,...(limits.length?{rotation_speed_limits:limits}:{})};
 }
 async function refresh(){const data=await api('/api/native-scene-fit-jobs');options('Jobs',data.jobs.map(j=>j.id));options('Resume',['',...data.jobs.filter(j=>j.status==='complete').map(j=>j.id)],true);return data;}
 el('Load').onclick=guard(load);el('Actor').onchange=drawActor;el('SaveActor').onclick=guard(saveActor);
 el('Knots').oninput=drawBudget;
 el('RemoveActor').onclick=guard(()=>{delete selections[el('Actor').value];delete speedLimits[el('Actor').value];drawActor();drawSelections();});
 el('Save').onclick=guard(()=>download(request()));el('Refresh').onclick=guard(refresh);
 el('LoadResume').onclick=guard(async()=>{const id=el('Resume').value;if(!id)throw Error('Select a completed correction to continue.');
  const before=key(getDraft()),value=await api(`/api/native-scene-fit-review?id=${encodeURIComponent(id)}`);if(value.id!==id||el('Resume').value!==id||before!==key(getDraft()))throw Error('Continuation selection or scene changed.');
  if(value.status!=='complete'||!['strep-studio-native-scene-fit-v1','strep-studio-native-scene-fit-v2'].includes(value.authoring_request?.schema)||value.quality_approved!==false)throw Error('Completed source-bound correction required.');
  setDraft(clone(value.authoring_request.draft));selections=clone(value.authoring_request.actors);catalog=null;
  await load();selections=clone(value.authoring_request.actors);speedLimits={};for(const t of value.authoring_request.rotation_speed_limits??[]){speedLimits[t.actor]??={};speedLimits[t.actor][t.node]=t.maximum_degrees_per_second;}drawActor();drawSelections();el('Resume').value=id;el('Iterations').value=value.authoring_request.options.iterations;status('Continuation loaded. Original clip epochs, edit permissions and turning-speed limits stay bound; explicit patch revisions are checked separately.');
 });
 el('Build').onclick=guard(async()=>{if(busy)throw Error('Wait for this request.');const value=request();busy=true;el('Build').disabled=true;
  try{const job=await post('/api/native-scene-fits',value);await refresh();el('Jobs').value=job.id;status('Character correction started. Refresh results to inspect original clips, proposals and failures.');}finally{busy=false;el('Build').disabled=false;}
 });
 el('Review').onclick=guard(async()=>{const id=el('Jobs').value;if(!id)throw Error('Select a character correction.');review=null;el('Stage').disabled=true;el('Results').replaceChildren();
  const value=await api(`/api/native-scene-fit-review?id=${encodeURIComponent(id)}`);if(value.id!==id||el('Jobs').value!==id)throw Error('Correction selection changed.');
  const p=document.createElement('p');p.textContent=value.status==='complete'?`Native conditions: ${value.native_conditions_pass?'pass':'fail'}. Sampled geometry: ${value.geometry_conditions_pass?'pass':'fail'}. Original clips remain selected. Import and motion-quality review are required.`:`${value.status}: ${value.stage||value.error||'waiting'}`;el('Results').append(p);
  for(const d of value.downloads??[]){const a=document.createElement('a');a.className='btn';a.href=d.url;a.download='';a.textContent=d.label;el('Results').append(a);}
  if(value.rotation_speed_conditions_pass!==undefined)p.textContent+=` Turning-speed limits: ${value.rotation_speed_conditions_pass?'pass':'fail'}.`;
  review=value;try{stagedScene(value);el('Stage').disabled=false;}catch{}status(p.textContent);
 });
 el('Stage').onclick=guard(async()=>{const before=review;if(!before||el('Jobs').value!==before.id)throw Error('Review the selected correction first.');
  const sceneBefore=key(getDraft());
  const updated=await api(`/api/native-scene-fit-review?id=${encodeURIComponent(before.id)}`);
  if(review!==before||key(updated)!==key(before)||el('Jobs').value!==before.id||sceneBefore!==key(getDraft()))throw Error('Correction or scene changed; review its results again.');
  setDraft(stagedScene(updated));catalog=null;stamp=null;selections={};speedLimits={};el('Stage').disabled=true;status('All proposals staged in a new scene draft. Build and review its scene assets before game use; the original job is retained.');
 });
 return {load,refresh,request};
}
function saveJSON(value){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'})),a=globalThis.document.createElement('a');a.href=url;a.download='native-character-correction.json';a.click();URL.revokeObjectURL(url);}
