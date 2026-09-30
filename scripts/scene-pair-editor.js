// Saved scene controls, immutable job submission and recoverable observation.
export function createScenePairEditor({getContext,onComplete}){
 const by=n=>document.getElementById('scenePair'+n),status=t=>by('Status').textContent=t;
 const storage={get(k){try{return localStorage.getItem(k);}catch{return null;}},set(k,v){try{localStorage.setItem(k,v);}catch{}},remove(k){try{localStorage.removeItem(k);}catch{}}};
 let source=null,busy=false,version=0,actors=new Map(),contacts=new Map();
 const enabled=()=>{for(const n of ['Label','Start','End','UseStart','UseEnd','Budget','Apply'])by(n).disabled=busy||!source;for(const el of [...actors.values(),...contacts.values()])el.disabled=busy||!source;};
 async function json(url,options){const r=await fetch(url,{cache:'no-store',...options}),data=await r.json();if(!r.ok)throw Error(data.error||'Request failed');return data;}
 const draft=()=>({start:by('Start').value,end:by('End').value,label:by('Label').value,budget:by('Budget').value,
  actors:Object.fromEntries([...actors].map(([name,el])=>[name,[...el.selectedOptions].map(o=>o.value)])),contacts:[...contacts].filter(([id,el])=>el.checked).map(([id])=>id)});
 function store(){if(source)storage.set('strep:pair:'+source.revision,JSON.stringify(draft()));}
 for(const n of ['Label','Start','End','Budget'])by(n).addEventListener('input',store);
 for(const [n,field] of [['UseStart','Start'],['UseEnd','End']])by(n).onclick=()=>{if(source&&!busy){by(field).value=getContext().frame/30;store();}};
 async function poll(id){
  try{const result=await json('/api/scene-pair-jobs'),job=result.jobs.find(j=>j.id===id);
   if(!job){busy=false;storage.remove('strep:pair-active-job');enabled();status('Saved correction job is unavailable. No replacement was started.');return;}
   status((job.stage||job.status)+(job.progress?.total?` · ${job.progress.completed}/${job.progress.total} mesh samples`:''));
   if(['complete','failed'].includes(job.status)){
    busy=false;storage.remove('strep:pair-active-job');enabled();
    if(job.status==='failed'){status('Partner correction failed: '+(job.error||'See worker output'));return;}
    await onComplete(job.collection,job.default_scene);status(job.accepted_local_step?'Local correction saved for review. Remaining defects and naturalness need review.':'No correction passed the local checks. Showing the preserved original.');return;
   }
  }catch(error){status('Checking saved correction: '+error.message);}
  setTimeout(()=>poll(id),2000);
 }
 by('Apply').onclick=async()=>{
  if(!source||busy)return;
  if(getContext().changed){status('Placement edits are unsaved. Reload the saved scene before fitting.');return;}
  const d=draft(),start=Number(d.start),end=Number(d.end),budget=Number(d.budget),label=d.label.trim();
  if(!Number.isFinite(start)||!Number.isFinite(end)||start<0||end<=start||end>source.duration_s||end-start>5){status('Choose a range inside the clip, at most five seconds long.');return;}
  if(!Number.isFinite(budget)||budget<=0||budget>45){status('Choose a rotation budget above 0 and at most 45 degrees.');return;}
  if(!label||label.length>100){status('Name the correction using 1–100 characters.');return;}
  if(Object.values(d.actors).some(j=>j.length<1||j.length>8)){status('Choose 1–8 editable joints for each character.');return;}
  const request={schema:'strep-paired-rotation-request-v1',source_url:source.source_url,revision:source.revision,
   actors:Object.fromEntries(Object.entries(d.actors).map(([name,joints])=>[name,{joints}])),window_s:[start,end],
   protected_contact_ids:d.contacts,limit_degrees:budget,knots_s:[start,start+(end-start)/4,start+(end-start)/2,start+3*(end-start)/4,end]};
  store();busy=true;enabled();status('Saving original clips and correction controls…');
  try{const job=await json('/api/scene-pair-fits',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({label,request})});storage.set('strep:pair-active-job',job.id);void poll(job.id);}
  catch(error){busy=false;enabled();status(error.message);}
 };
 const active=storage.get('strep:pair-active-job');if(active){busy=true;void poll(active);}enabled();
 return{reset(){version++;source=null;enabled();},async bind(url){const token=++version;source=null;enabled();
  try{const data=await json('/api/scene-pair-source?path='+encodeURIComponent(url));if(token!==version)return;
   source=data;actors=new Map();contacts=new Map();by('Actors').replaceChildren();by('ContactList').replaceChildren();
   let saved=null;try{saved=JSON.parse(storage.get('strep:pair:'+data.revision));}catch{}
   const center=data.contacts[0]?.seconds[0]??Math.min(data.duration_s/2,.5);
   by('Start').value=saved?.start??Math.max(0,center-.5);by('End').value=saved?.end??Math.min(data.duration_s,center+.5);by('Budget').value=saved?.budget??5;by('Label').value=saved?.label??'Partner correction';
   by('Start').max=by('End').max=data.duration_s;
   for(const [name,entry] of Object.entries(data.actors)){
    const label=document.createElement('label'),text=document.createElement('span'),select=document.createElement('select');text.textContent=name+' · editable joints';select.multiple=true;select.size=6;select.setAttribute('aria-label','Editable joints for '+name);
    select.replaceChildren(...entry.joints.map(j=>{const o=document.createElement('option');o.value=j;o.textContent=j;o.selected=saved?.actors?.[name]?.includes(j)??false;return o;}));select.addEventListener('change',store);label.append(text,select);by('Actors').append(label);actors.set(name,select);
   }
   for(const contact of data.contacts){const label=document.createElement('label'),check=document.createElement('input'),text=document.createElement('span');check.type='checkbox';check.style.width='auto';check.checked=saved?saved.contacts?.includes(contact.id)??false:true;check.addEventListener('change',store);text.textContent=` ${contact.id} · ${contact.seconds.map(t=>t.toFixed(4)).join('–')} s`;label.append(check,text);by('ContactList').append(label);contacts.set(contact.id,check);}
   enabled();if(!busy)status('Choose editable joints for both characters and the range to correct.');
  }catch(error){if(token===version){source=null;enabled();if(!busy)status(error.message);}}
 }};
}
