import {createMotionProfileEditor} from './motion-profile-editor.js';

// One editable profile per actor; planning never dispatches a model worker.
export function createSceneGenerationPlan({getContext,createProfile=createMotionProfileEditor,download}){
 const by=name=>document.getElementById('scenePlan'+name),clone=x=>JSON.parse(JSON.stringify(x));
 const make=(tag,text)=>{const node=document.createElement(tag);if(text)node.textContent=text;return node;};
 const status=text=>by('Status').textContent=text;
 const storage={get(key){try{return localStorage.getItem(key);}catch{return null;}},set(key,value){try{localStorage.setItem(key,value);}catch{}}};
 let scene=null,plan=null,actor=null,version=0,checked=null,key=null,rows=[];
 const profile=createProfile(by('Profile'),()=>{if(scene){saveActor();changed();}},{idPrefix:'scenePlan-'});
 function controls(){for(const name of ['Actor','Add','Seeds','Mode','Budget','Import','Preview'])by(name).disabled=!scene;by('Profile').hidden=!scene;by('Budget').disabled=!scene||by('Mode').value==='dense';by('Download').disabled=!checked;}
 function saveActor(){
  if(!plan||!actor)return;
  const value={segments:rows.map(row=>({prompt:row.prompt.value,duration_s:Number(row.duration.value)})),
   seeds:by('Seeds').value.split(',').map(s=>s.trim()).map(s=>s===''?NaN:Number(s))};
  if(by('Mode').value==='sparse')value.guide_plan={mode:'sparse',maximum_frames:Number(by('Budget').value)};
  const movement=profile.request();if(movement)value.motion_profile=movement;
  plan[actor]=value;
 }
 function changed(){version++;checked=null;by('Results').replaceChildren();controls();if(key&&plan)storage.set(key,JSON.stringify(plan));status('Plan changed. Check all characters before downloading.');}
 function addRow(segment={prompt:'',duration_s:1}){
  const wrap=make('fieldset'),prompt=make('textarea'),duration=make('input'),remove=make('button','Remove action');
  const promptLabel=make('label','Action'),durationLabel=make('label','Duration (seconds)');
  prompt.value=segment.prompt;prompt.maxLength=1000;duration.type='number';duration.min=1;duration.max=9;duration.step=1/30;duration.value=segment.duration_s;
  promptLabel.append(prompt);durationLabel.append(duration);remove.className='btn';remove.type='button';wrap.append(promptLabel,durationLabel,remove);by('Segments').append(wrap);
  const row={wrap,prompt,duration};rows.push(row);
  for(const field of [prompt,duration])field.addEventListener('input',()=>{saveActor();profile.markChanged();changed();});
  remove.onclick=()=>{if(rows.length<=1)return;rows=rows.filter(r=>r!==row);wrap.remove();saveActor();changed();};
 }
 function showActor(name){
  actor=name;const value=plan[name];rows=[];by('Segments').replaceChildren();
  for(const segment of value.segments)addRow(segment);
  by('Seeds').value=value.seeds.join(', ');by('Mode').value=value.guide_plan?'sparse':'dense';by('Budget').value=value.guide_plan?.maximum_frames??19;
  // restore does not trigger onChange while switching actors.
  profile.restore({enabled:!!value.motion_profile,profile:value.motion_profile??null});
  profile.setRequestSource(()=>{saveActor();return {id:'scene-plan-profile',label:name,...clone(plan[name]),generation_constraints:undefined,guide_plan:undefined};});
  controls();
 }
 function payload(){
  if(!scene)throw Error('Select a saved scene.');
  const context=getContext();if(context.changed||JSON.stringify(context.spec)!==JSON.stringify(scene))throw Error('The scene changed. Reload the saved scene before checking its motion plan.');
  saveActor();return {scene:clone(scene),actor_plan:clone(plan)};
 }
 by('Actor').onchange=()=>{saveActor();showActor(by('Actor').value);};
 by('Add').onclick=()=>{if(!scene)return;if(rows.length>=6){status('Use at most six action segments per character.');return;}addRow();saveActor();changed();};
 for(const name of ['Seeds','Mode','Budget'])by(name).addEventListener('input',()=>{saveActor();changed();});
 by('Import').onchange=async()=>{
  const file=by('Import').files?.[0];if(!scene||!file)return;const token=version;
  try{
   if(file.size>1048576)throw Error('Choose an actor-plan JSON up to 1 MiB.');
   const imported=JSON.parse(await file.text());if(token!==version)return;
   if(!imported||Array.isArray(imported)||Object.keys(imported).sort().join('\0')!==Object.keys(scene.actors).sort().join('\0'))throw Error('The plan must cover exactly these scene characters.');
   for(const value of Object.values(imported)){
    if(!value||!Array.isArray(value.segments)||value.segments.length<1||value.segments.length>6||!Array.isArray(value.seeds)||value.seeds.length<1||value.seeds.length>4||Object.keys(value).some(k=>!['segments','seeds','guide_plan','motion_profile'].includes(k)))throw Error('Invalid actor-plan fields.');
    if('guide_plan' in value&&(!value.guide_plan||value.guide_plan.mode!=='sparse'||Object.keys(value.guide_plan).some(k=>!['mode','maximum_frames'].includes(k))))throw Error('This editor supports automatic sparse selection. Keep manual selections in the original JSON.');
    if(value.segments.some(s=>!s||typeof s.prompt!=='string'||typeof s.duration_s!=='number'||Object.keys(s).some(k=>!['prompt','duration_s'].includes(k))))throw Error('Each action needs prompt text and a duration.');
   }
   const response=await fetch('/api/scene-generation-plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scene:clone(scene),actor_plan:imported})}),result=await response.json();
   if(token!==version)return;if(!response.ok)throw Error(result.error||'Invalid actor plan.');
   plan=clone(imported);showActor(actor);changed();status('Actor plan imported. Check its descriptions and contacts.');
  }catch(error){if(token===version)status(error.message);}
 };
 by('Preview').onclick=async()=>{
  let token;try{
   const draft=payload();token=++version;checked=null;controls();status('Checking all characters…');
   const response=await fetch('/api/scene-generation-plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(draft)}),result=await response.json();
   if(token!==version)return;if(!response.ok)throw Error(result.error||'Could not check the plan.');
   if(JSON.stringify(payload())!==JSON.stringify(draft))throw Error('The plan changed during its check.');
   checked={draft,result};by('Results').replaceChildren();
   for(const [name,record] of Object.entries(result.plan.actors)){
    by('Results').append(make('h4',name),make('p',`${record.selected_frames.length} guide frames · ${record.complete_target_frames.length} contact frames retained`));
    const brief=result.plan.motion_profiles?.[name];for(const segment of brief?.segments??draft.actor_plan[name].segments)by('Results').append(make('p',segment.conditioning_prompt??segment.prompt));
    if(brief?.unmapped_stats?.length)by('Results').append(make('p','Saved without motion rules: '+brief.unmapped_stats.map(s=>s.label).join(', ')));
   }
   controls();status('Descriptions and contact timing checked. Source poses and generated quality still need validation.');
  }catch(error){if(token===undefined||token===version){checked=null;controls();status(error.message);}}
 };
 const saveDownload=download??((name,value)=>{const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'}));const link=make('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
 by('Download').onclick=()=>{
  try{if(!checked||JSON.stringify(payload())!==JSON.stringify(checked.draft))throw Error('Check the current plan before downloading.');
   saveDownload('actor-plan.json',checked.draft.actor_plan);saveDownload('scene-generation-planning.json',checked);
   status('Actor plan and planning record downloaded. No animation has been generated.');
  }catch(error){checked=null;controls();status(error.message);}
 };
 controls();
 return {reset(){version++;scene=null;plan=null;actor=null;checked=null;key=null;rows=[];by('Segments').replaceChildren();profile.restore(null);controls();status('Select a saved scene.');},
  async bind(spec,url){
   this.reset();const token=version;
   try{
    if(!spec?.actors||!Number.isInteger(spec.frame_count)||spec.frame_count<30||spec.frame_count>900)throw Error('Choose a scene lasting 1–30 seconds on the 30 fps clock.');
    const names=Object.keys(spec.actors);if(!names.length||names.length>10)throw Error('Choose a scene with 1–10 characters.');
    const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(spec)));if(token!==version)return;
    scene=clone(spec);key='strep:scene-plan:'+url+':'+[...new Uint8Array(digest)].map(n=>n.toString(16).padStart(2,'0')).join('');
    const frames=spec.frame_count,parts=Math.ceil(frames/270);const segments=Array.from({length:parts},(_,i)=>({prompt:'',duration_s:(Math.floor((i+1)*frames/parts)-Math.floor(i*frames/parts))/30}));
    plan=Object.fromEntries(names.map(name=>[name,{segments:clone(segments),seeds:[11,22],guide_plan:{mode:'sparse',maximum_frames:19}}]));
    const saved=storage.get(key);if(saved){try{const value=JSON.parse(saved);if(value&&Object.keys(value).sort().join('\0')===names.sort().join('\0')&&Object.values(value).every(v=>v&&Array.isArray(v.segments)&&v.segments.length&&v.segments.length<=6&&Array.isArray(v.seeds)))plan=value;}catch{}}
    by('Actor').replaceChildren(...Object.keys(plan).map(name=>{const option=make('option',name);option.value=name;return option;}));actor=Object.keys(plan)[0];by('Actor').value=actor;showActor(actor);status('Describe every character, then check the shared scene plan.');
   }catch(error){if(token===version){this.reset();status(error.message);}}
  }};
}
