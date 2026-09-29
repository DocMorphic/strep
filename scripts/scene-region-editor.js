// Readable diagnostics for independently measured exports; never quality approval.
export function sceneRateDetails(assessment,scene){
 const output=[];
 function windowLabel(value){
  const slash=value.lastIndexOf('/'),id=value.slice(0,slash),phase=value.slice(slash+1);
  const contact=scene?.contacts?.find(c=>c.id===id),end=(scene?.frame_count??1)-1;
  const names={approach:'approach',grasp:'grasp',release:'release',start_boundary:'contact-start boundary',end_boundary:'contact-end boundary'};
  if(value==='whole_clip')return 'whole clip';
  if(!contact||!names[phase])return value;
  const a=contact.start_frame,b=contact.end_frame;
  const spans={approach:[0,a],grasp:[a,b],release:[b,end],start_boundary:[Math.max(0,a-2),Math.min(end,a+2)],end_boundary:[Math.max(0,b-2),Math.min(end,b+2)]};
  return `${id}: ${names[phase]} (frames ${spans[phase].join('–')})`;
 }
 for(const [key,label] of [['speed','Speed'],['acceleration','Acceleration']]){
  const row=assessment?.rate_diagnostics?.[key];if(!row)continue;
  const count=row.increased_joint_peaks,windows=Array.isArray(row.increased_window_peaks)?row.increased_window_peaks.filter(v=>typeof v==='string'):[];
  if(!Number.isInteger(count)||count<0)continue;
  output.push(`${label}: ${count} ${count===1?'joint has':'joints have'} higher whole-clip peaks. ${windows.length?'Higher peaks in '+windows.map(windowLabel).join('; ')+'.':'No higher phase or boundary peaks reported.'}`);
 }
 if(output.length)output.push('Compared with the source clip using a 0.00001 reporting allowance in m/s or m/s². These measurements are not a naturalness rating. Download the per-joint report for individual values.');
 return output;
}

export function sceneSupportDetails(assessment){
 const row=assessment?.preserved_support;if(!row)return [];
 const {samples,failures,maximum_error_m:peak,vertex_identity_gaps:gaps}=row;
 if(![samples,failures,gaps].every(n=>Number.isInteger(n)&&n>=0)||failures>samples||
    (samples>0&&(!Number.isFinite(peak)||peak<0))||typeof row.sampled_point_preservation_passed!=='boolean')
  return ['Support-point evidence is incomplete or invalid; no pass can be shown.'];
 const pass=samples>0&&failures===0&&gaps===0&&row.sampled_point_preservation_passed;
 return [
  `Source support points: ${pass?'sampled checks pass':'preservation not verified'}. ${failures}/${samples} samples exceed the recorded tolerance.${samples?' Maximum drift: '+(peak*1000).toFixed(3)+' mm.':' No support samples were measured.'}`,
  `${gaps} ${gaps===1?'sample could':'samples could'} not be checked because material-point identity changes between keys. These are gaps in the audit coverage.`,
  'These checks preserve inferred source points. They do not establish a planted sole, balance, contact forces or naturalness. Download the support report for the measured points.'
 ];
}

export function sceneWindowDetails(assessment){
 const geometry=assessment?.window_geometry;if(!geometry)return [];
 const range=geometry.requested_window,next=geometry.suggested_geometry_envelope,counts=geometry.failure_counts;
 const validRange=r=>Array.isArray(r)&&r.length===2&&r.every(Number.isInteger)&&r[0]>=0&&r[0]<=r[1]&&r[1]<geometry.frames;
 if(!Number.isInteger(geometry.frames)||!validRange(range)||!validRange(next)||next[0]>range[0]||next[1]<range[1]||!counts||
    !['locked_segments','boundary_segments','edited_window'].every(k=>Number.isInteger(counts[k])&&counts[k]>=0)||
    geometry.sampled_failures!==counts.locked_segments+counts.boundary_segments+counts.edited_window||geometry.sampled_failures>(geometry.frames-1)*4+1||
    geometry.locked_geometry_conflict!==(counts.locked_segments>0))
  return ['Edit-range evidence is incomplete or invalid; inspect the downloaded geometry report.'];
 const output=[`Edit range: frames ${range.join('–')}. Remaining geometry failures: ${counts.edited_window} inside, ${counts.boundary_segments} across the boundary, ${counts.locked_segments} in locked segments.`];
 if(counts.locked_segments)output.push('Another fit that preserves the same outside keys cannot repair these locked-segment failures.');
 if(next[0]!==range[0]||next[1]!==range[1])output.push(`Suggested range for the observed geometry failures: frames ${next.join('–')}. Your edit range has not been changed.`);
 output.push('The suggested range covers sampled collisions; it does not guarantee a successful fit or natural motion. Download the range report for affected frames.');
 return output;
}

// Region drafts and job IDs survive reload; completion is separate from quality.
export function createSceneRegionEditor({getContext,onComplete,onDraft=()=>{},onPick=()=>{},onCancelPick=()=>{},onHandPick=()=>{},onHandFrame=()=>{}}){
 const storage={
  getItem(key){try{return globalThis.localStorage.getItem(key);}catch{return null;}},
  setItem(key,value){try{globalThis.localStorage.setItem(key,value);}catch{}},
  removeItem(key){try{globalThis.localStorage.removeItem(key);}catch{}}
 };
 const by=id=>document.getElementById('sceneRegion'+id);
 const fields=['Start','End','X','Y','Z','Anchor','PatchMode','PatchRadius','Cone','Clearance','Gap','Spacing','Area','Centroid','TargetRadius','Normal'];
 let source=null,drafts={},busy=false,version=0;
 const status=value=>by('Status').textContent=value;
 async function json(url,options){const response=await fetch(url,{cache:'no-store',...options}),data=await response.json();if(!response.ok)throw Error(data.error||'Request failed');return data;}
 function enabled(){for(const field of [...fields,'Actor','Contact','Include','Label','Apply','UseFrame','Pick','Paint','Erase','ClearPatch','FrameHand'])by(field).disabled=busy||!source;if(busy||!source)onCancelPick();}
 function preview(){const c=selected();if(c){const d=drafts[c.id];onDraft(c,d.edit,d.include);}else onDraft(null);}
 function selected(){return source?.contacts.find(c=>c.id===by('Contact').value);}
 function store(){if(!source)return;try{storage.setItem('strep:regions:'+source.revision,JSON.stringify({drafts,label:by('Label').value}));}catch{}}
 function fill(){const c=selected();if(!c)return;const d=drafts[c.id],e=d.edit;
  by('Include').checked=d.include;by('Start').value=e.start_frame;by('End').value=e.end_frame;
  ['X','Y','Z'].forEach((a,i)=>by(a).value=e.point_m[i]);by('Anchor').value=e.anchor_tolerance_m*1000;
  by('PatchMode').value=e.patch_mode;by('PatchMode').querySelector('[value="saved"]').disabled=c.edit.patch_mode!=='saved';
  by('PatchRadius').value=e.patch_radius_m*100;by('Cone').value=e.patch_normal_degrees;
  for(const [id,key,scale] of [['Clearance','clearance_m',1000],['Gap','contact_gap_m',1000],['Spacing','spacing_m',1000],['Area','area_m2',1e6],['Centroid','centroid_error_m',1000],['TargetRadius','local_radius_m',100],['Normal','normal_degrees',1]])by(id).value=e.limits[key]*scale;
  by('PatchCount').textContent=e.patch_mode==='custom'?`${e.patch_face_ids.length} triangles selected by you`:`${c.patch_face_ids?.length??'?'} triangles in the initial patch`;
  by('PatchMode').querySelector('[value="custom"]').disabled=!Array.isArray(e.patch_face_ids);
  by('ContactInfo').textContent=`${c.hand} → ${c.target_object}. Grip coordinates are local to the object. Purple: draft grip and inward normal; grey outside its interval. The animation stays unchanged until a fit completes.`;preview();
 }
 function capture(){const c=selected();if(!c)return;const d=drafts[c.id],e=d.edit;d.include=by('Include').checked;
  e.start_frame=Number(by('Start').value);e.end_frame=Number(by('End').value);e.point_m=['X','Y','Z'].map(a=>Number(by(a).value));
  e.anchor_tolerance_m=Number(by('Anchor').value)/1000;e.patch_mode=by('PatchMode').value;e.patch_radius_m=Number(by('PatchRadius').value)/100;e.patch_normal_degrees=Number(by('Cone').value);
  for(const [id,key,scale] of [['Clearance','clearance_m',1000],['Gap','contact_gap_m',1000],['Spacing','spacing_m',1000],['Area','area_m2',1e6],['Centroid','centroid_error_m',1000],['TargetRadius','local_radius_m',100],['Normal','normal_degrees',1]])e.limits[key]=Number(by(id).value)/scale;
  store();preview();
 }
 function actorContacts(){const list=source.contacts.filter(c=>c.supported&&c.actor===by('Actor').value);by('Contact').replaceChildren(...list.map(c=>new Option(c.id,c.id)));fill();}
 for(const field of [...fields,'Include'])by(field).addEventListener('input',capture);
 by('Label').addEventListener('input',store);by('Actor').onchange=actorContacts;by('Contact').onchange=fill;
 by('UseFrame').onclick=()=>{by('Start').value=getContext().frame;capture();};
 by('Pick').onclick=()=>{if(source&&!busy)onPick();};
 by('FrameHand').onclick=()=>{if(source&&!busy)onHandFrame();};
 by('Paint').onclick=()=>{if(source&&!busy)onHandPick(false);};
 by('Erase').onclick=()=>{if(source&&!busy)onHandPick(true);};
 by('ClearPatch').onclick=()=>{if(source&&!busy&&selected()?.hand_mesh)setHandFaces([],selected().hand_mesh.mesh_sha256);};
 function setHandFaces(faces,identity){const c=selected();if(!source||busy||!c?.hand_mesh||identity!==c.hand_mesh.mesh_sha256)return;const e=drafts[c.id].edit;e.patch_mode='custom';e.patch_face_ids=[...faces];e.patch_mesh_sha256=identity;store();fill();}
 async function poll(id){
  try{const result=await json('/api/scene-region-jobs'),job=result.jobs.find(j=>j.id===id);
   if(!job){busy=false;storage.removeItem('strep:region-active-job');enabled();status('Saved fitting job unavailable. No replacement was started.');return;}
   status(job.stage||job.status);
   if(job.status==='failed'||job.status==='complete'){
    busy=false;storage.removeItem('strep:region-active-job');enabled();
    if(job.status==='failed'){status('Fitting failed: '+(job.error||'See worker output'));return;}
    await onComplete(job.collection);const a=job.assessment;
    status(`${a?.contact_geometry_passed?'Contact and clearance samples pass.':'Needs correction: '+(a?.contact_failures??'?')+' contact samples and '+(a?.geometry_failures??'?')+' clearance samples fail.'} ${a?.motion_regressions?.length?'Motion regressions were also measured. ':''}Human review is still required.`);return;
   }
  }catch(error){status('Checking saved fitting job: '+error.message);}
  setTimeout(()=>poll(id),1500);
 }
 by('Apply').onclick=async()=>{
  if(!source||busy)return;if(getContext().changed){status('Placement edits are unsaved. Reload the saved scene before fitting.');return;}
  capture();const actor=by('Actor').value,contacts=source.contacts.filter(c=>c.supported&&c.actor===actor&&drafts[c.id]?.include).map(c=>{const e=structuredClone(drafts[c.id].edit);if(e.patch_mode!=='custom'){delete e.patch_face_ids;delete e.patch_mesh_sha256;}return e;});
  if(!contacts.length){status('Include at least one contact.');return;}
  if(contacts.some(c=>c.patch_mode==='custom'&&!c.patch_face_ids?.length)){status('Select hand triangles before fitting.');return;}
  busy=true;enabled();status('Saving authored regions and starting the fit…');
  try{const job=await json('/api/scene-region-fits',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source_url:source.source_url,revision:source.revision,actor,label:by('Label').value.trim(),contacts})});storage.setItem('strep:region-active-job',job.id);poll(job.id);}
  catch(error){busy=false;enabled();status(error.message);}
 };
 const active=storage.getItem('strep:region-active-job');if(active){busy=true;poll(active);}enabled();
 return {setHandFaces,setGripPoint(point){if(!source||busy||!selected())return;['X','Y','Z'].forEach((axis,i)=>by(axis).value=point[i]);capture();},reset(){version++;source=null;onDraft(null);enabled();},async bind(url){const token=++version;source=null;onDraft(null);enabled();
  try{const data=await json('/api/scene-region-source?path='+encodeURIComponent(url));if(token!==version)return;
   const supported=data.contacts.filter(c=>c.supported);if(!supported.length){status('No editable hand-to-object contacts in this scene. '+data.contacts.map(c=>c.reason||'').join(' '));return;}
   source=data;drafts=Object.fromEntries(supported.map(c=>[c.id,{include:true,edit:structuredClone(c.edit)}]));by('Label').value='Hand contact fit';
   try{const saved=JSON.parse(storage.getItem('strep:regions:'+data.revision));if(saved){for(const c of supported)if(saved.drafts?.[c.id])drafts[c.id]=saved.drafts[c.id];by('Label').value=saved.label||'Hand contact fit';}}catch{}
   by('Actor').replaceChildren(...[...new Set(supported.map(c=>c.actor))].map(a=>new Option(a,a)));actorContacts();enabled();
   if(!busy)status('Edit one or more contacts, then fit. Suggested palm regions need review; a saved candidate may still fail its checks.');
  }catch(error){if(token===version){source=null;enabled();if(!busy)status(error.message);}}
 }};
}
