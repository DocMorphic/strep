import * as THREE from 'three';

export function createRigPostureEditor({C,api,post,status,getContext,sampleLocal,pause,seek,closeEditors,onJob}) {
 let binding=null,poses=[],busy=false,epoch=0,rows=[];
 const panel=C('rigPosturePanel'),note=C('rigPostureNote');
 const guard=fn=>async()=>{try{await fn();}catch(e){note.textContent=e.message;status(e.message);}};
 function available(){const c=getContext();return c.result&&c.result.kind!=='neutral'&&c.variant!=='repeated';}
 function ready(){C('rigPosture').disabled=!available()||busy;}
 function hide(){epoch++;panel.hidden=true;}
 function reset(){epoch++;binding=null;poses=[];rows=[];hide();ready();}
 function hand(){return binding.hands.find(h=>h.node===Number(C('rigPostureHand').value));}
 function renderJoints(mode='reference'){
  rows=[];const host=C('rigPostureJoints');host.replaceChildren();
  for(const joint of hand()?.joints||[]){
   const q=mode==='current'?sampleLocal(joint.node):joint.reference_xyzw;
   const e=new THREE.Euler().setFromQuaternion(new THREE.Quaternion().fromArray(q),'XYZ');
   const line=document.createElement('div');line.className='rig-posture-joint';
   const label=document.createElement('span');label.textContent=joint.label;line.append(label);
   const inputs=['X','Y','Z'].map((axis,i)=>{const input=document.createElement('input');input.type='number';input.step='.1';input.min='-180';input.max='180';input.value=String(THREE.MathUtils.radToDeg([e.x,e.y,e.z][i]));input.setAttribute('aria-label',`${joint.label} local ${axis} degrees`);line.append(input);return input;});
   rows.push({node:joint.node,inputs});host.append(line);
  }
  note.textContent=mode==='current'?'Finger rotations captured from the current preview frame. Adjust local XYZ angles, then add the interval.':'Rig default reference rotations loaded. These are not a validated open hand, fist or grasp.';
 }
 function renderIntervals(){
  const host=C('rigPostureIntervals');host.replaceChildren();
  poses.forEach((p,i)=>{const row=document.createElement('div');row.className='rig-toolbar';const text=document.createElement('span');text.className='small';text.textContent=`${binding.hands.find(h=>h.node===p.hand_root).role} · frames ${p.start_frame}–${p.end_frame} · hold ${p.full_start_frame}–${p.full_end_frame} · ${Math.round(p.strength*100)}%`;const jump=document.createElement('button');jump.className='btn';jump.textContent='Go to hold';jump.onclick=()=>{pause();seek(p.full_start_frame);};const remove=document.createElement('button');remove.className='btn';remove.textContent='Remove';remove.disabled=busy;remove.onclick=()=>{poses.splice(i,1);renderIntervals();};row.append(text,jump,remove);host.append(row);});
  C('rigPostureApply').disabled=busy||!poses.length;
 }
 async function open(){
  pause();closeEditors();const c=getContext(),ticket=++epoch;
  if(binding?.job_id===c.job.id&&binding.variant===c.variant){panel.hidden=false;return;}
  const data=await api(`/api/rig-posture-source?job=${encodeURIComponent(c.job.id)}&variant=${encodeURIComponent(c.variant)}`);
  if(ticket!==epoch)return;
  binding=data;poses=[];panel.hidden=false;C('rigPostureHand').replaceChildren();
  for(const h of data.hands){const o=document.createElement('option');o.value=h.node;o.textContent=h.role==='LeftHand'?'Left hand':'Right hand';C('rigPostureHand').append(o);}
  const last=data.frames-1,start=Math.max(0,Math.min(getContext().frame,last-2)),end=Math.min(last,start+60),fade=Math.max(1,Math.floor((end-start)/3));
  for(const [id,value] of [['Start',start],['FullStart',start+fade],['FullEnd',end-fade],['End',end]]){C('rigPosture'+id).value=value;C('rigPosture'+id).max=last;}
  C('rigPostureAdd').disabled=busy||!data.hands.length;C('rigPostureReference').disabled=!data.hands.length;C('rigPostureCapture').disabled=!data.hands.length;
  renderIntervals();renderJoints();if(!data.hands.length)note.textContent='This rig has no skin joints below its mapped hands. Finger posture needs a rig with articulated fingers.';
 }
 C('rigPosture').onclick=guard(open);C('rigPostureClose').onclick=hide;
 C('rigPostureHand').onchange=()=>renderJoints();
 C('rigPostureReference').onclick=guard(()=>renderJoints());
 C('rigPostureCapture').onclick=guard(()=>{pause();renderJoints('current');});
 C('rigPostureAdd').onclick=guard(()=>{
  if(['Start','FullStart','FullEnd','End','Strength'].some(id=>C('rigPosture'+id).value===''))throw Error('Fill every timing and strength field.');
  const a=Number(C('rigPostureStart').value),b=Number(C('rigPostureFullStart').value),c=Number(C('rigPostureFullEnd').value),d=Number(C('rigPostureEnd').value),strength=Number(C('rigPostureStrength').value)/100;
  if(![a,b,c,d].every(Number.isInteger)||!(0<=a&&a<b&&b<=c&&c<d&&d<binding.frames))throw Error('Use start < full start ≤ full end < end, within the clip.');
  if(!Number.isFinite(strength)||strength<0||strength>1)throw Error('Strength must be between 0 and 100%.');
  const targets=rows.map(({node,inputs})=>{const angles=inputs.map(x=>Number(x.value));if(inputs.some(x=>x.value==='')||!angles.every(v=>Number.isFinite(v)&&Math.abs(v)<=180))throw Error('Enter finite local angles between −180° and 180°.');return {node,rotation_xyzw:new THREE.Quaternion().setFromEuler(new THREE.Euler(...angles.map(THREE.MathUtils.degToRad),'XYZ')).toArray()};});
  if(!targets.length)throw Error('Choose an articulated hand.');
  if(poses.some(p=>p.hand_root===hand().node&&Math.max(p.start_frame,a)<Math.min(p.end_frame,d)))throw Error('Intervals on the same hand must not overlap.');
  if(poses.length>=64)throw Error('Use at most 64 intervals.');
  poses.push({id:crypto.randomUUID(),hand_root:hand().node,targets,start_frame:a,full_start_frame:b,full_end_frame:c,end_frame:d,strength});renderIntervals();note.textContent='Interval added. Create a candidate to see the authored motion; the preview still shows your selected source clip.';
 });
 C('rigPostureApply').onclick=guard(async()=>{
  const c=getContext();if(!binding||c.job?.id!==binding.job_id||c.variant!==binding.variant)throw Error('Source changed. Reopen Hand posture.');
  const posture={schema:'strep-hand-posture-v1',source_glb_sha256:binding.glb_sha256,frames:binding.frames,fps:binding.fps,hand_roots:[...new Set(poses.map(p=>p.hand_root))],poses,limits:{rotation_degrees:90,correction_step_degrees:5},provenance:'Authored in Studio using rig-reference or captured local finger rotations and editable local XYZ angles. Not anatomically or contact verified.'};
  const payload={source_job:binding.job_id,variant:binding.variant,label:C('rigPostureName').value,posture};
  if(new TextEncoder().encode(JSON.stringify(payload)).length>32768)throw Error('This draft exceeds the local request size. Create it in smaller batches of intervals.');
  setBusy(true);
  try{const job=await post('/api/rig-posture-edits',payload);onJob(job);hide();status('Creating hand posture candidate. The input clip is retained for comparison.');}catch(e){setBusy(false);throw e;}
 });
 function setBusy(value){busy=value;ready();C('rigPostureAdd').disabled=busy||!binding?.hands.length;renderIntervals();}
 return {reset,hide,ready,setBusy};
}
