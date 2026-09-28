import * as THREE from 'three';

// Sparse goals use the original GLB node identity and world coordinate system.
export function createRigJointEditor({C,post,status,getContext,pause,seek,sampleJoint,onJob,getRecipe}) {
  let binding=null,goals=[],busy=false;
  const safe=fn=>async()=>{try{await fn();}catch(e){status(e.message);}};
  const key=()=>`strep:joint-edit:${binding.glb_sha256}`;
  function save(){if(binding)try{localStorage.setItem(key(),JSON.stringify({glb_sha256:binding.glb_sha256,goals}));}catch{}}
  function render(){C('rigJointList').replaceChildren();goals.forEach((g,i)=>{
    const row=document.createElement('div');row.className='rig-contact-row';
    const text=document.createElement('span');text.textContent=`${C('rigJointBone').querySelector(`option[value="${g.node}"]`)?.textContent||g.node} · frame ${g.frame} · XYZ ${g.position_m.map(v=>v.toFixed(3)).join(', ')} m`;
    const go=document.createElement('button');go.className='btn';go.textContent='Go to frame';go.onclick=()=>{pause();seek(g.frame);};
    const remove=document.createElement('button');remove.className='btn';remove.textContent='Remove';remove.setAttribute('aria-label',`Remove joint target ${i+1}`);
    remove.onclick=()=>{goals.splice(i,1);save();render();};row.append(text,go,remove);C('rigJointList').append(row);
  });state();}
  function state(){const disabled=busy||!binding||!!binding.period_frames;
    C('rigJointApply').disabled=disabled||!goals.length;C('rigJointAdd').disabled=disabled;C('rigJointSample').disabled=disabled;
    C('rigJointNote').textContent=binding?.period_frames?'Edit a finite source before making a loop; periodic joint fitting is unavailable.':
      'Experimental: uses the source range above, preserving two frames at each edge. Position tolerance 5 mm; orientation 5°. Existing joint/root limits remain fixed. Unmet targets and floor/contact failures stay visible. Speed and local pose curves are separate edits.';
  }
  function sample(){if(!binding)return;pause();const context=getContext(),node=Number(C('rigJointBone').value),pose=sampleJoint(node);
    C('rigJointFrame').value=context.frame;
    const euler=new THREE.Euler().setFromQuaternion(new THREE.Quaternion(...pose.rotation_xyzw),'XYZ');
    ['X','Y','Z'].forEach((axis,i)=>{C('rigJoint'+axis).value=pose.position_m[i].toFixed(6);C('rigJointR'+axis).value=THREE.MathUtils.radToDeg(euler.toArray()[i]).toFixed(5);});
    status('Copied the displayed joint pose in world metres. Adjust the target, then add it.');
  }
  C('rigJointSample').onclick=safe(sample);
  C('rigJointAdd').onclick=safe(()=>{if(!binding)throw Error('Open an existing clip first');
    const frame=Number(C('rigJointFrame').value),node=Number(C('rigJointBone').value),position_m=['X','Y','Z'].map(a=>Number(C('rigJoint'+a).value)),rotation=['X','Y','Z'].map(a=>Number(C('rigJointR'+a).value));
    if(!Number.isInteger(frame)||frame<0||frame>=binding.frames||![...position_m,...rotation].every(Number.isFinite))throw Error('Use a valid frame and finite world coordinates');
    if(goals.length>=8||goals.some(g=>g.frame===frame&&g.node===node))throw Error('Use up to eight targets, without repeating a joint at the same frame');
    const q=new THREE.Quaternion().setFromEuler(new THREE.Euler(...rotation.map(THREE.MathUtils.degToRad),'XYZ'));
    goals.push({frame,node,position_m,rotation_xyzw:q.toArray()});save();render();
  });
  C('rigJointApply').onclick=safe(async()=>{const context=getContext(),recipe=getRecipe();
    if(!binding||context.job?.id!==binding.job_id||context.variant!==binding.variant)throw Error('Reopen joint edits for the displayed clip');
    const a=Number(C('rigClipStart').value),b=Number(C('rigClipEnd').value);
    if(!Number.isInteger(a)||!Number.isInteger(b)||a<0||b>=binding.frames||b-a<6||b-a>120||goals.some(g=>g.frame<=a+1||g.frame>=b-1))throw Error('Choose a 6–120 frame source range with every target inside its two fixed edge samples');
    const edit={schema:'strep-rig-joint-edit-v1',glb_sha256:binding.glb_sha256,label:C('rigClipName').value||recipe.label,start_frame:a,last_frame:b,goals};
    const job=await post('/api/rig-joint-edits',{source_job:binding.job_id,variant:binding.variant,edit});onJob(job);status('Joint-target job started. Input, fitting stages and any failed candidate will remain available.');
  });
  return {
    bind(data){binding=data;goals=[];try{const draft=JSON.parse(localStorage.getItem(key()));if(draft?.glb_sha256===data.glb_sha256&&Array.isArray(draft.goals))goals=draft.goals;}catch{}
      C('rigJointBone').replaceChildren(...[{node:data.spec.root_node,label:'Hips'},...data.editable_joints].map(j=>new Option(j.label,j.node)));
      C('rigJointFrame').max=data.frames-1;render();sample();},
    reset(){binding=null;goals=[];render();},setBusy(value){busy=value;state();}
  };
}
