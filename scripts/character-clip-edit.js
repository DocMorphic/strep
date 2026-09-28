function createRigClipEditor({C,api,post,status,getContext,seek,pause,closeContacts,onJob,sampleJoint}){
 let binding=null,recipe=null,epoch=0,busy=false,mirrorBinding=null;
 const jointEditor=createRigJointEditor({C,post,status,getContext,pause,seek,sampleJoint,onJob,getRecipe:()=>recipe});
 const guard=fn=>async()=>{try{await fn();}catch(e){status(e.message);}};
 const key=()=> 'strep:clip-edit:'+binding.glb_sha256;
 function store(){if(!recipe||!binding)return;recipe.label=C('rigClipName').value;recipe.start_frame=Number(C('rigClipStart').value);recipe.last_frame=Number(C('rigClipEnd').value);recipe.speed=Number(C('rigClipSpeed').value);try{localStorage.setItem(key(),JSON.stringify(recipe));}catch{}clock();}
 function clock(){const span=recipe.last_frame-recipe.start_frame,speed=recipe.speed;if(!(span>0&&speed>=.25&&speed<=4)){C('rigClipClock').textContent='Choose a valid trim range and speed between 0.25 and 4.';return;}const steps=Math.max(1,Math.floor(span/speed+.5));C('rigClipClock').textContent=`${steps+1} frames · ${(steps/30).toFixed(2)} seconds at 30fps · effective speed ${(span/steps).toFixed(3)}×. Both trim endpoints are kept.`;}
 function poses(){C('rigPoseList').replaceChildren();recipe.poses.forEach((pose,i)=>{const row=document.createElement('div');row.className='rig-contact-row';const label=document.createElement('span');label.textContent=`${C('rigPoseBone').querySelector('option[value="'+pose.node+'"]')?.textContent||pose.node} · ${pose.start_frame} → ${pose.peak_frame} → ${pose.end_frame} · XYZ ${pose.rotation_degrees.join(', ')}°`;const jump=document.createElement('button');jump.className='btn';jump.textContent='Go to source peak';jump.onclick=()=>{pause();seek(pose.peak_frame);};const remove=document.createElement('button');remove.className='btn';remove.textContent='×';remove.setAttribute('aria-label','Remove pose adjustment '+(i+1));remove.onclick=()=>{recipe.poses.splice(i,1);poses();store();};row.append(label,jump,remove);C('rigPoseList').append(row);});}
 function hide(){C('rigClipPanel').hidden=true;C('rigMappingPanel').hidden=false;}
 function resetMirror(){mirrorBinding=null;C('rigMirrorFields').hidden=true;C('rigMirrorApply').disabled=true;C('rigMirrorNote').textContent='Prepare the mirror to inspect the bone pairs and reflection plane.';}
 function reset(){epoch++;binding=null;recipe=null;resetMirror();jointEditor.reset();C('rigClipPanel').hidden=true;C('rigEditClip').disabled=true;}
 async function open(){const context=getContext();if(!context.job||!context.result||context.result.kind==='neutral')throw Error('Choose an existing motion first');pause();const token=++epoch;const data=await api('/api/rig-contact-source?'+new URLSearchParams({job:context.job.id,variant:context.variant}));if(token!==epoch||context.model!==getContext().model)return;
  binding=data;resetMirror();recipe={schema:'strep-rig-clip-edit-v1',glb_sha256:data.glb_sha256,label:('Edit · '+context.job.label).slice(0,160),start_frame:0,last_frame:data.frames-1,speed:1,poses:[]};
  try{const saved=JSON.parse(localStorage.getItem(key()));if(saved?.glb_sha256===data.glb_sha256)recipe=saved;}catch{}
  closeContacts();C('rigJoinPanel').hidden=true;C('rigLoopPanel').hidden=true;C('rigEventPanel').hidden=true;C('rigMappingPanel').hidden=true;C('rigClipPanel').hidden=false;C('rigClipBinding').textContent=`${context.job.label} · ${context.variant} · ${data.frames} source frames. Draft belongs to this exact clip.`;
  C('rigClipName').value=recipe.label;C('rigClipStart').value=recipe.start_frame;C('rigClipEnd').value=recipe.last_frame;C('rigClipSpeed').value=recipe.speed;
  C('rigPoseBone').replaceChildren(...[{node:data.spec.root_node,label:'Hips'},...data.editable_joints].map(j=>new Option(j.label,j.node)));
  const peak=Math.min(data.frames-2,Math.max(1,context.frame));C('rigPoseStart').value=Math.max(0,peak-8);C('rigPosePeak').value=peak;C('rigPoseEnd').value=Math.min(data.frames-1,peak+8);C('rigPoseAdd').disabled=data.frames<3;
  for(const id of ['rigClipStart','rigClipEnd','rigPoseStart','rigPosePeak','rigPoseEnd'])C(id).max=data.frames-1;
  poses();clock();promptState();jointEditor.bind(data);C('rigClipApply').disabled=busy;status('Edit the trim, speed, local pose curves or world joint targets, then create a new candidate.');
 }
 C('rigEditClip').onclick=guard(open);C('rigClipClose').onclick=hide;
 for(const id of ['rigClipName','rigClipStart','rigClipEnd','rigClipSpeed'])C(id).oninput=store;
 C('rigClipIn').onclick=()=>{C('rigClipStart').value=getContext().frame;store();};C('rigClipOut').onclick=()=>{C('rigClipEnd').value=getContext().frame;store();};
 C('rigPoseAdd').onclick=guard(()=>{if(!recipe)throw Error('Open clip edits first');const a=Number(C('rigPoseStart').value),c=Number(C('rigPosePeak').value),b=Number(C('rigPoseEnd').value);if(![a,c,b].every(Number.isInteger)||!(a>=0&&a<c&&c<b&&b<binding.frames))throw Error('Pose frames must satisfy start < peak < end inside the source clip');if(recipe.poses.length>=24)throw Error('At most 24 pose adjustments');recipe.poses.push({node:Number(C('rigPoseBone').value),start_frame:a,peak_frame:c,end_frame:b,rotation_degrees:['X','Y','Z'].map(k=>Number(C('rigPose'+k).value))});poses();store();});
 C('rigClipApply').onclick=guard(async()=>{store();const context=getContext();if(!binding||context.job?.id!==binding.job_id||context.variant!==binding.variant)throw Error('Reopen edits for the displayed clip');const job=await post('/api/rig-clip-edits',{source_job:binding.job_id,variant:binding.variant,edit:recipe});onJob(job);status('Clip edit started. The selected input, recipe and source files are retained.');});
 C('rigMirrorPrepare').onclick=guard(async()=>{
  const context=getContext(),token=epoch;if(!binding||context.job?.id!==binding.job_id||context.variant!==binding.variant)throw Error('Reopen edits for the displayed clip');
  const data=await api('/api/rig-mirror-source?'+new URLSearchParams({job:binding.job_id,variant:binding.variant}));
  if(token!==epoch||context.model!==getContext().model||getContext().job?.id!==data.job_id||getContext().variant!==data.variant)return;
  mirrorBinding=data;C('rigMirrorName').value=data.recipe.label;const n=data.recipe.plane_normal;
  C('rigMirrorHeading').value=(Math.atan2(n[2],n[0])*180/Math.PI).toFixed(6);
  C('rigMirrorPlane').textContent=`Vertical plane through starting pelvis: ${data.recipe.plane_point.map(v=>v.toFixed(3)).join(', ')} m. Heading 0° reflects world X; 90° reflects world Z. Default follows reference thighs.`;
  C('rigMirrorPairs').replaceChildren();for(const [node,partner] of Object.entries(data.recipe.counterparts)){
   if(Number(node)>partner)continue;const row=document.createElement('p');row.textContent=Number(node)===partner?`${data.names[node]} · centre`:`${data.names[node]} ↔ ${data.names[partner]}`;C('rigMirrorPairs').append(row);
  }
  C('rigMirrorNote').textContent=data.scope;C('rigMirrorFields').hidden=false;C('rigMirrorApply').disabled=busy;
 });
 C('rigMirrorApply').onclick=guard(async()=>{
  const context=getContext();if(!mirrorBinding||context.job?.id!==mirrorBinding.job_id||context.variant!==mirrorBinding.variant)throw Error('Prepare a mirror for the displayed clip');
  const heading=Number(C('rigMirrorHeading').value);if(!C('rigMirrorHeading').value.trim()||!Number.isFinite(heading)||heading < -180||heading > 180)throw Error('Use a plane heading from −180° to 180°');
  const mirror=structuredClone(mirrorBinding.recipe),angle=heading*Math.PI/180;mirror.label=C('rigMirrorName').value;mirror.plane_normal=[Math.cos(angle),0,Math.sin(angle)];
  C('rigMirrorApply').disabled=true;
  try{const job=await post('/api/rig-mirror-edits',{source_job:mirrorBinding.job_id,variant:mirrorBinding.variant,recipe:mirror});onJob(job);status('Creating a mirrored variation. Original clip, bone pairs, plane and annotation history remain in the package.');}
  finally{C('rigMirrorApply').disabled=busy||!mirrorBinding;}
 });
 C('rigPromptApply').onclick=guard(async()=>{store();const context=getContext();if(!binding||context.job?.id!==binding.job_id||context.variant!==binding.variant)throw Error('Reopen edits for the displayed clip');const edit={schema:'strep-rig-prompt-edit-v1',glb_sha256:binding.glb_sha256,label:recipe.label,prompt:C('rigPromptText').value,start_frame:recipe.start_frame,last_frame:recipe.last_frame,blend_frames:Number(C('rigPromptBlend').value),seed:Number(C('rigPromptSeed').value)};const job=await post('/api/rig-prompt-edits',{source_job:binding.job_id,variant:binding.variant,edit});onJob(job);status('Regenerating the selected section. Original clip, boundary guides and raw model output will be retained.');});
 function promptState(){C('rigPromptApply').disabled=busy||!!binding?.period_frames||!binding||binding.frames<30;C('rigPromptNote').textContent=binding?.period_frames?'Regenerate a finite source before making a loop; periodic section regeneration is not yet supported.':'Choose 30–270 source frames. Two samples at each edge stay unchanged. Converted pose guides and generated action/contact quality need review.';}
 return {reset,hide,ready:()=>{C('rigEditClip').disabled=!getContext().result||getContext().result.kind==='neutral'||getContext().variant==='repeated';promptState();},setBusy:value=>{busy=value;C('rigClipApply').disabled=busy;C('rigMirrorPrepare').disabled=busy;C('rigMirrorApply').disabled=busy||!mirrorBinding;jointEditor.setBusy(value);promptState();}};
}
