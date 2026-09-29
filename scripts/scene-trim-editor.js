// A shared scene trim preserves all participants on one clock.
export function createSceneTrimEditor({getContext,onComplete}){
 const by=name=>document.getElementById('sceneTrim'+name);
 const storage={get(k){try{return localStorage.getItem(k);}catch{return null;}},set(k,v){try{localStorage.setItem(k,v);}catch{}},remove(k){try{localStorage.removeItem(k);}catch{}}};
 let source=null,busy=false,version=0;
 const status=text=>by('Status').textContent=text;
 const retiming=()=>by('Mode').value==='retime';
 const frames=()=>source?Math.round((source.frames-1)/Number(by('Speed').value))+1:0;
 const enabled=()=>{for(const name of ['Mode','Label','Apply'])by(name).disabled=busy||!source;for(const name of ['First','Last','UseFirst','UseLast'])by(name).disabled=busy||!source||retiming();by('Speed').disabled=busy||!source||!retiming();const n=frames();by('Timing').textContent=source&&retiming()&&Number(by('Speed').value)>0&&n>=3&&n<=901?`${((n-1)/30).toFixed(2)} s of animation · ${((source.frames-1)/(n-1)).toFixed(4)}× actual speed after frame rounding.`:'';};
 async function json(url,options){const response=await fetch(url,{cache:'no-store',...options}),data=await response.json();if(!response.ok)throw Error(data.error||'Request failed');return data;}
 function store(){if(source)storage.set('strep:trim:'+source.revision,JSON.stringify({first:by('First').value,last:by('Last').value,label:by('Label').value,mode:by('Mode').value,speed:by('Speed').value}));}
 for(const name of ['First','Last','Label','Mode','Speed'])by(name).addEventListener('input',()=>{store();enabled();});
 by('UseFirst').onclick=()=>{if(!source||busy)return;by('First').value=getContext().frame;store();};
 by('UseLast').onclick=()=>{if(!source||busy)return;by('Last').value=getContext().frame;store();};
 async function poll(id){
  try{const result=await json('/api/scene-trim-jobs'),job=result.jobs.find(j=>j.id===id);
   if(!job){busy=false;storage.remove('strep:trim-active-job');enabled();status('Saved trim job is unavailable. No replacement was started.');return;}
   status(job.stage||job.status);
   if(['complete','failed'].includes(job.status)){
    busy=false;storage.remove('strep:trim-active-job');enabled();
    if(job.status==='failed'){status('Timing edit failed: '+(job.error||'See worker output'));return;}
    await onComplete(job.collection);status('Timing edit saved. All participants share the new clock; precise events are retained. Motion quality remains unapproved.');return;
   }
  }catch(error){status('Checking saved trim job: '+error.message);}
  setTimeout(()=>poll(id),1500);
 }
 by('Apply').onclick=async()=>{
  if(!source||busy)return;
  if(getContext().changed){status('Placement edits are unsaved. Reload the saved scene before editing timing.');return;}
  const first=Number(by('First').value),last=Number(by('Last').value),label=by('Label').value.trim();
  if(!retiming()&&(!Number.isInteger(first)||!Number.isInteger(last)||first<0||last>=source.frames||last-first<2)){status('Choose at least three frames inside the scene.');return;}
  if(retiming()&&(!Number.isFinite(Number(by('Speed').value))||Number(by('Speed').value)<=0||source.frames>901||frames()<3||frames()>901)){status('Choose a speed that produces 3–901 frames. Source animations can be at most 30 seconds.');return;}
  if(!label||label.length>100){status('Name the edited scene using 1–100 characters.');return;}
  store();busy=true;enabled();status('Saving the shared scene timing edit…');
  try{const job=await json('/api/scene-trims',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source_url:source.source_url,revision:source.revision,label,...(retiming()?{operation:'retime',frames:frames()}:{first,last})})});storage.set('strep:trim-active-job',job.id);poll(job.id);}
  catch(error){busy=false;enabled();status(error.message);}
 };
 const active=storage.get('strep:trim-active-job');if(active){busy=true;poll(active);}enabled();
 return {reset(){version++;source=null;enabled();},async bind(url){const token=++version;source=null;enabled();
  try{const data=await json('/api/scene-trim-source?path='+encodeURIComponent(url));if(token!==version)return;source=data;
   by('First').value=0;by('Last').value=data.frames-1;by('Label').value='Edited scene';by('Mode').value='trim';by('Speed').value=1;by('First').max=by('Last').max=data.frames-1;
   try{const draft=JSON.parse(storage.get('strep:trim:'+data.revision));if(draft){by('First').value=draft.first;by('Last').value=draft.last;by('Label').value=draft.label;by('Mode').value=draft.mode==='retime'?'retime':'trim';by('Speed').value=draft.speed??1;}}catch{}
   enabled();if(!busy)status(`${data.actors} actor(s), ${data.objects} prop(s): edit together on the shared clock. Placement and the recorded path are retained.`);
  }catch(error){if(token===version){source=null;enabled();if(!busy)status(error.message);}}
 }};
}
