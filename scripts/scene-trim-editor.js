// A shared scene trim preserves all participants on one clock.
export function createSceneTrimEditor({getContext,onComplete}){
 const by=name=>document.getElementById('sceneTrim'+name);
 const storage={get(k){try{return localStorage.getItem(k);}catch{return null;}},set(k,v){try{localStorage.setItem(k,v);}catch{}},remove(k){try{localStorage.removeItem(k);}catch{}}};
 let source=null,busy=false,version=0;
 const status=text=>by('Status').textContent=text;
 const retiming=()=>by('Mode').value==='retime';
 const carrying=()=>by('Mode').value==='carry';
 const frames=()=>source?Math.round((source.frames-1)/Number(by('Speed').value))+1:0;
 const enabled=()=>{for(const name of ['Mode','Label','Apply'])by(name).disabled=busy||!source;for(const name of ['First','Last','UseFirst','UseLast'])by(name).disabled=busy||!source||retiming()||carrying();by('Speed').disabled=busy||!source||!retiming();for(const name of ['Actor','Object','Reference'])by(name).disabled=busy||!source||!carrying();by('CarryFields').hidden=!carrying();const n=frames();by('Timing').textContent=source&&retiming()&&Number(by('Speed').value)>0&&n>=3&&n<=901?`${((n-1)/30).toFixed(2)} s of animation · ${((source.frames-1)/(n-1)).toFixed(4)}× actual speed after frame rounding.`:'';};
 async function json(url,options){const response=await fetch(url,{cache:'no-store',...options}),data=await response.json();if(!response.ok)throw Error(data.error||'Request failed');return data;}
 function store(){if(source)storage.set('strep:trim:'+source.revision,JSON.stringify({first:by('First').value,last:by('Last').value,label:by('Label').value,mode:by('Mode').value,speed:by('Speed').value,actor:by('Actor').value,object:by('Object').value,reference:by('Reference').value}));}
 for(const name of ['First','Last','Label','Mode','Speed','Actor','Object','Reference'])by(name).addEventListener('input',()=>{store();enabled();});
 by('UseFirst').onclick=()=>{if(!source||busy)return;by('First').value=getContext().frame;store();};
 by('UseLast').onclick=()=>{if(!source||busy)return;by('Last').value=getContext().frame;store();};
 async function poll(id){
  try{const result=await json('/api/scene-trim-jobs'),job=result.jobs.find(j=>j.id===id);
   if(!job){busy=false;storage.remove('strep:trim-active-job');enabled();status('Saved trim job is unavailable. No replacement was started.');return;}
   status(job.stage||job.status);
   if(['complete','failed'].includes(job.status)){
    busy=false;storage.remove('strep:trim-active-job');enabled();
    if(job.status==='failed'){status('Scene edit failed: '+(job.error||'See worker output'));return;}
    await onComplete(job.collection);status('Scene edit saved. Event timing follows the selected operation. Motion quality remains unapproved.');return;
   }
  }catch(error){status('Checking saved trim job: '+error.message);}
  setTimeout(()=>poll(id),1500);
 }
 by('Apply').onclick=async()=>{
  if(!source||busy)return;
  if(getContext().changed){status('Placement edits are unsaved. Reload the saved scene before editing the scene.');return;}
  const first=Number(by('First').value),last=Number(by('Last').value),label=by('Label').value.trim();
  if(!retiming()&&!carrying()&&(!Number.isInteger(first)||!Number.isInteger(last)||first<0||last>=source.frames||last-first<2)){status('Choose at least three frames inside the scene.');return;}
  if(retiming()&&(!Number.isFinite(Number(by('Speed').value))||Number(by('Speed').value)<=0||source.frames>901||frames()<3||frames()>901)){status('Choose a speed that produces 3–901 frames. Source animations can be at most 30 seconds.');return;}
  if(carrying()&&(!(source.actor_ids||[]).includes(by('Actor').value)||!(source.object_ids||[]).includes(by('Object').value)||!Number.isInteger(Number(by('Reference').value))||Number(by('Reference').value)<0||Number(by('Reference').value)>=source.frames||source.frames>901)){status('Choose an actor, carrier object and reference frame inside a scene of at most 30 seconds.');return;}
  if(!label||label.length>100){status('Name the edited scene using 1–100 characters.');return;}
  store();busy=true;enabled();status('Saving the scene edit…');
  try{const job=await json('/api/scene-trims',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source_url:source.source_url,revision:source.revision,label,...(carrying()?{operation:'carry',actor:by('Actor').value,object:by('Object').value,reference_frame:Number(by('Reference').value)}:retiming()?{operation:'retime',frames:frames()}:{first,last})})});storage.set('strep:trim-active-job',job.id);poll(job.id);}
  catch(error){busy=false;enabled();status(error.message);}
 };
 const active=storage.get('strep:trim-active-job');if(active){busy=true;poll(active);}enabled();
 return {reset(){version++;source=null;enabled();},async bind(url){const token=++version;source=null;enabled();
  try{const data=await json('/api/scene-trim-source?path='+encodeURIComponent(url));if(token!==version)return;source=data;
   by('First').value=0;by('Last').value=data.frames-1;by('Label').value='Edited scene';by('Mode').value='trim';by('Speed').value=1;by('First').max=by('Last').max=by('Reference').max=data.frames-1;by('Reference').value=0;
   for(const [control,ids] of [['Actor',data.actor_ids||[]],['Object',data.object_ids||[]]]){by(control).replaceChildren(...ids.map(id=>{const option=document.createElement('option');option.value=id;option.textContent=id;return option;}));by(control).value=ids[0]||'';}
   try{const draft=JSON.parse(storage.get('strep:trim:'+data.revision));if(draft){by('First').value=draft.first;by('Last').value=draft.last;by('Label').value=draft.label;by('Mode').value=['retime','carry'].includes(draft.mode)?draft.mode:'trim';by('Speed').value=draft.speed??1;if((data.actor_ids||[]).includes(draft.actor))by('Actor').value=draft.actor;if((data.object_ids||[]).includes(draft.object))by('Object').value=draft.object;by('Reference').value=draft.reference??0;}}catch{}
   enabled();if(!busy)status(`${data.actors} actor(s), ${data.objects} prop(s): choose a scene edit. Original motion remains available for comparison.`);
  }catch(error){if(token===version){source=null;enabled();if(!busy)status(error.message);}}
 }};
}
