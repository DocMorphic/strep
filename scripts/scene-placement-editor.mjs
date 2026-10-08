export function createScenePlacementEditor({getContext,onComplete}){
 const by=id=>document.getElementById('scenePlacement'+id);
 let source=null,busy=false,version=0;
 const status=t=>by('Status').textContent=t;
 const enable=()=>{for(const key of ['Label','Check','Save'])by(key).disabled=busy||!source;};
 async function json(url,options){const response=await fetch(url,{cache:'no-store',...options}),data=await response.json();if(!response.ok)throw Error(data.error||'Placement request failed');return data;}
 function placement(){const scene=getContext().scene;if(!scene)throw Error('Load a scene first');return{actors:Object.fromEntries(Object.entries(scene.actors).map(([id,a])=>[id,structuredClone(a.transform)])),objects:Object.fromEntries(Object.entries(scene.objects).map(([id,o])=>[id,structuredClone(o.keyframes)]))};}
 function show(report){
  if(report?.schema!=='strep-scene-placement-reach-v1'||!['provably_incompatible','not_ruled_out'].includes(report.status)||report.quality_approved!==false||report.release_approved!==false||!Array.isArray(report.rows)||!Array.isArray(report.skipped))throw Error('Invalid reach report; inspect the source before relying on it');
  const items=report.rows.map(row=>{
   if(!Number.isFinite(row.maximum_error_lower_bound_m)||row.maximum_error_lower_bound_m<0||!Number.isFinite(row.authored_tolerance_m)||row.authored_tolerance_m<=0||!Number.isInteger(row.samples)||row.samples<1||!Array.isArray(row.incompatible_frames)||row.incompatible_frames.length>row.samples||!row.incompatible_frames.every(Number.isInteger)||!Number.isInteger(row.worst_frame)||!Number.isFinite(row.worst_seconds))throw Error('Incomplete anchor reach measurements');
   if((row.incompatible_frames.length>0)!==(row.maximum_error_lower_bound_m>row.authored_tolerance_m))throw Error('Contradictory anchor reach measurements');
   const item=document.createElement('li');item.textContent=`${row.actor} · ${row.contact}: ${row.incompatible_frames.length}/${row.samples} native poses ruled out. Minimum remaining error reaches ${(row.maximum_error_lower_bound_m*1000).toFixed(3)} mm, against ${(row.authored_tolerance_m*1000).toFixed(3)} mm tolerance; frame ${row.worst_frame} (${row.worst_seconds.toFixed(3)} s).`;return item;
  });
  if((report.status==='provably_incompatible')!==report.rows.some(row=>row.incompatible_frames.length>0))throw Error('Contradictory reach status');
  for(const row of report.skipped){const item=document.createElement('li');item.textContent=`${row.contact}: ${row.reason}`;items.push(item);}
  by('Results').replaceChildren(...items);
  status(report.status==='provably_incompatible'?'Some anchors conflict with this body-edit budget. Review placement or author a different request.':'No conflict was proved. This is not a feasibility or quality pass; region, speed, collision and human review remain necessary.');
 }
 async function submit(save){
  if(!source||busy)return;
  const token=version,reference=source;
  let request;try{request={source_url:reference.source_url,revision:reference.revision,placement:placement(),label:by('Label').value.trim()};if(!request.label||request.label.length>100)throw Error('Name the placement using 1–100 characters');}catch(error){status(error.message);return;}
  const boundDraft=JSON.stringify(request.placement);
  busy=true;enable();by('Results').replaceChildren();status(save?'Saving a new placement snapshot…':'Checking native anchor reach…');
  try{
   const data=await json(save?'/api/scene-placement-snapshots':'/api/scene-placement-check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)});
   if(token!==version||source!==reference)return;
   if(JSON.stringify(placement())!==boundDraft){status(save?'Placement changed during save. The earlier draft was saved; reload collections to find it. Your current draft stays selected.':'Placement changed during the check. Check the current draft again.');return;}
   if(save){if(typeof data.collection!=='string'||!/^scene-placement-jobs\/placement-[a-f0-9]{32}$/.test(data.collection)||data.scene_id!=='placement'||data.source_url!==request.source_url||data.revision!==request.revision||data.quality_approved!==false||data.release_approved!==false)throw Error('Invalid saved placement result');show(data.reach);await onComplete(data.collection,data.scene_id);if(token===version)status('Placement saved as a new scene. Original clips are preserved; geometry and naturalness need review.');}
   else{if(data.source_url!==request.source_url||data.revision!==request.revision)throw Error('Reach report refers to a different source');show(data);}
  }catch(error){if(token===version)status(error.message);}
  finally{if(token===version){busy=false;enable();}}
 }
 by('Check').onclick=()=>submit(false);by('Save').onclick=()=>submit(true);enable();
 return{changed(){by('Results').replaceChildren();if(source&&!busy)status('Placement changed. Check the current draft or save it as a new scene.');},reset(){version++;source=null;busy=false;by('Results').replaceChildren();enable();},async bind(url){const token=++version;source=null;busy=false;enable();
  try{const data=await json('/api/scene-placement-source?path='+encodeURIComponent(url));if(token!==version)return;if(data.schema!=='strep-scene-placement-source-v1'||data.source_url!==url||typeof data.revision!=='string')throw Error('Invalid saved scene binding');source=data;by('Label').value='Authored placement';enable();status('Check anchors at the current placement, or save a separate scene. Original animations remain unchanged.');}
  catch(error){if(token===version){source=null;enable();status(error.message);}}
 }};
}
