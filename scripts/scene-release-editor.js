// Explicit saved-scene release authoring; drafts and active jobs survive reload.
export function createSceneReleaseEditor({getContext,onComplete}){
 const by=id=>document.getElementById(id),fields=['Object','Frame','Mass','Friction','Restitution','Label','CollisionMode'];
 let source=null,version=0,busy=false;
 const status=text=>by('sceneReleaseStatus').textContent=text;
 async function json(url,options){const r=await fetch(url,{cache:'no-store',...options}),data=await r.json();if(!r.ok)throw Error(data.error||'Request failed');return data;}
 function enabled(){for(const name of fields)by('sceneRelease'+name).disabled=busy||!source;by('sceneReleaseApply').disabled=busy||!source;by('sceneReleaseSample').disabled=busy||!source;}
 function storeDraft(){if(!source)return;const draft=Object.fromEntries(fields.map(n=>[n,by('sceneRelease'+n).value]));try{localStorage.setItem('strep:release:'+source.revision,JSON.stringify(draft));}catch{}}
 for(const name of fields)by('sceneRelease'+name).addEventListener('input',storeDraft);
 by('sceneReleaseObject').addEventListener('change',()=>{if(source)by('sceneReleaseFrame').value=source.earliest_release[by('sceneReleaseObject').value];storeDraft();});
 by('sceneReleaseSample').onclick=()=>{by('sceneReleaseFrame').value=Math.floor(getContext().frame);storeDraft();};
 async function addResult(row){await onComplete(row.collection);status('Release candidate saved. Review floor/contact failures and exports; completion is not quality approval.');}
 async function poll(id){
  try{const response=await json('/api/scene-release-jobs'),row=response.jobs.find(j=>j.id===id);
   if(!row){status('Saved release job is unavailable. No replacement job was started.');busy=false;localStorage.removeItem('strep:release-active-job');enabled();return;}
   status(row.stage||row.status);
   if(row.status==='complete'||row.status==='failed'){
    busy=false;localStorage.removeItem('strep:release-active-job');enabled();
    if(row.status==='complete')await addResult(row);else status('Release failed: '+(row.error||'See saved worker output'));return;
   }
  }catch(error){status('Checking saved release job: '+error.message);}
  setTimeout(()=>poll(id),1500);
 }
 by('sceneReleaseApply').onclick=async()=>{
  if(!source||busy)return;const context=getContext();
  if(context.changed){status('Placement edits are not saved in this source. Reload the saved scene before simulating its release.');return;}
  const payload={source_url:source.source_url,revision:source.revision,object:by('sceneReleaseObject').value,
   release_frame:Number(by('sceneReleaseFrame').value),mass_kg:Number(by('sceneReleaseMass').value),
   friction:Number(by('sceneReleaseFriction').value),restitution:Number(by('sceneReleaseRestitution').value),label:by('sceneReleaseLabel').value.trim(),collision_mode:by('sceneReleaseCollisionMode').value};
  busy=true;enabled();status('Preparing immutable scene and starting release…');
  try{const job=await json('/api/scene-releases',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
   localStorage.setItem('strep:release-active-job',job.id);poll(job.id);
  }catch(error){busy=false;enabled();status(error.message);}
 };
 const active=localStorage.getItem('strep:release-active-job');if(active){busy=true;poll(active);}enabled();
 return {reset(){version++;source=null;enabled();},async bind(url){const token=++version;source=null;enabled();
  try{const data=await json('/api/scene-release-source?path='+encodeURIComponent(url));if(token!==version)return;source=data;
   by('sceneReleaseObject').replaceChildren(...data.objects.map(n=>new Option(n,n)));by('sceneReleaseFrame').max=data.frames-2;
   by('sceneReleaseFrame').value=data.earliest_release[data.objects[0]];by('sceneReleaseLabel').value='Object release';
   by('sceneReleaseMass').value='5';by('sceneReleaseFriction').value='.6';by('sceneReleaseRestitution').value='0';by('sceneReleaseCollisionMode').value='floor_only';
   try{const draft=JSON.parse(localStorage.getItem('strep:release:'+data.revision));if(draft)for(const name of fields)if(draft[name]!==undefined)by('sceneRelease'+name).value=draft[name];}catch{}
   enabled();if(!busy)status('Saved scene ready. Boxes and spheres use their matching collision shapes. Static mode requires stationary props. Moving mode follows other props on the shared clock using Jolt; prescribed props do not react to impacts. Sphere release uses Jolt. Cylinder tracks can be previewed and exported; cylinder physics release is not available yet. Materials apply to both surfaces. Actors are not colliders in this mode.');
  }catch(error){if(token===version){source=null;enabled();if(!busy)status(error.message);}}
 }};
}
