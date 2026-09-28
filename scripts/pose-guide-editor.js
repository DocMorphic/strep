// Compose model pose guides from the exact visible clip and frame.
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {enableEightWeights} from './soma-preview-skin.js';

function targetPreview(host,result){
 const canvas=document.createElement('canvas');canvas.style.cssText='width:100%;height:240px;display:block';canvas.setAttribute('aria-label','Authored pose target preview');host.append(canvas);
 const renderer=new THREE.WebGLRenderer({canvas,antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor(0xe7eaed);
 const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(40,1,.01,100),controls=new OrbitControls(camera,canvas),loader=new GLTFLoader();
 scene.add(new THREE.HemisphereLight(0xffffff,0x727780,2.5));const light=new THREE.DirectionalLight(0xffffff,2);light.position.set(3,5,3);scene.add(light,new THREE.GridHelper(6,24));
 const target=new THREE.Mesh(new THREE.SphereGeometry(.018),new THREE.MeshBasicMaterial({color:0xc87b14,depthTest:false}));target.renderOrder=3;target.position.fromArray(result.audit.target_m);scene.add(target);
 let alive=true,id=0,models=[];
 function dispose(model){model.traverse(n=>{n.geometry?.dispose();for(const m of n.material?(Array.isArray(n.material)?n.material:[n.material]):[])m.dispose();});}
 Promise.all(['original','candidate'].map(async(name,i)=>{const gltf=await loader.loadAsync(result.base+name+'.glb');if(!alive){dispose(gltf.scene);return;}gltf.scene.traverse(n=>{if(n.isMesh){for(const m of Array.isArray(n.material)?n.material:[n.material])m.dispose();n.material=new THREE.MeshStandardMaterial({color:0x969ca3,roughness:.8,transparent:!i,opacity:i?1:.2,depthWrite:!!i});enableEightWeights(n);n.frustumCulled=false;}});const mixer=new THREE.AnimationMixer(gltf.scene);mixer.clipAction(gltf.animations[0]).play();mixer.setTime(0);gltf.scene.updateMatrixWorld(true);models.push(gltf.scene);scene.add(gltf.scene);})).catch(()=>{if(alive)host.append(document.createTextNode('Pose preview unavailable; inspect the audit before use.'));});
 const point=result.audit.target_m;controls.target.set(point[0]*.3,1,point[2]*.3);camera.position.copy(controls.target).add(new THREE.Vector3(2,1,3));controls.update();
 function tick(){if(!alive)return;const w=Math.max(1,canvas.clientWidth),h=Math.max(1,canvas.clientHeight);renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();controls.update();renderer.render(scene,camera);id=requestAnimationFrame(tick);}tick();
 return()=>{alive=false;cancelAnimationFrame(id);controls.dispose();dispose(scene);renderer.dispose();};
}

export function createPoseGuideEditor(){
 const list=document.getElementById('poseGuideList');
 let guides=[],previews=[];
 const kinds=[['right-hand','Right hand'],['left-hand','Left hand'],['right-foot','Right foot'],['left-foot','Left foot'],['fullbody','Whole body'],['root2d','Root path and heading']];
 function changed(){document.getElementById('requestForm').dispatchEvent(new Event('input',{bubbles:true}));}
 function render(){
  previews.forEach(dispose=>dispose());previews=[];
  list.replaceChildren();document.getElementById('poseGuideEmpty').hidden=guides.length>0;
  guides.forEach((guide,index)=>{
   const row=document.createElement('div');row.className='segment';
   const source=document.createElement('p');source.className='small';source.textContent=`Source frame ${guide.source_frames.join(', ')} · ${guide.motion.split('/').slice(-2,-1)[0]}`;
   const kindLabel=document.createElement('label');kindLabel.textContent='Guide movement';
   const kind=document.createElement('select');kind.setAttribute('aria-label',`Pose guide ${index+1} movement`);
   for(const [value,label] of kinds)kind.add(new Option(label,value));
   const customJoints=guide.joint_names?.slice();
   if(guide.type==='end-effector')kind.add(new Option(guide.joint_names.join(' + '),'end-effector'));
   kind.value=guide.type;kind.onchange=()=>{guide.type=kind.value;if(kind.value!=='end-effector')delete guide.joint_names;else guide.joint_names=customJoints.slice();changed();};kindLabel.append(kind);
   const label=document.createElement('label');label.textContent='Target frame (30 frames per second)';
   const target=document.createElement('input');target.value=guide.frame_indices.join(', ');target.required=true;target.setAttribute('aria-label',`Pose guide ${index+1} target frame`);
   target.oninput=()=>{guide.frame_indices=target.value.split(',').map(v=>/^\d+$/.test(v.trim())?Number(v.trim()):NaN);changed();};label.append(target);
   const remove=document.createElement('button');remove.type='button';remove.className='btn';remove.textContent='Remove pose guide';remove.onclick=()=>{guides.splice(index,1);render();changed();};
   const editor=document.createElement('details'),title=document.createElement('summary');title.textContent='Move this hand or foot target';editor.append(title);
   const help=document.createElement('p');help.className='small';help.textContent='For a single captured hand or foot. Offset is world XYZ in metres (Y up). Root, other limbs and hand/foot orientation stay fixed. This is a pose target, not an animation or collision correction.';editor.append(help);
   const offsets=['X','Y','Z'].map(axis=>{const l=document.createElement('label');l.textContent=axis+' offset (m)';const input=document.createElement('input');input.type='number';input.min=-.5;input.max=.5;input.step=.01;input.value=0;input.setAttribute('aria-label',`Pose guide ${index+1} ${axis} offset`);l.append(input);editor.append(l);return input;});
   const budgetLabel=document.createElement('label');budgetLabel.textContent='Maximum joint edit (degrees)';const budget=document.createElement('input');budget.type='number';budget.min=1;budget.max=90;budget.value=45;budget.setAttribute('aria-label',`Pose guide ${index+1} rotation budget`);budgetLabel.append(budget);editor.append(budgetLabel);
   const solve=document.createElement('button');solve.type='button';solve.className='btn';solve.textContent='Try target';editor.append(solve);const output=document.createElement('div');output.setAttribute('aria-live','polite');editor.append(output);
   let disposePreview=null;previews.push(()=>disposePreview?.());
   solve.onclick=async()=>{
    const named={'right-hand':'RightHand','left-hand':'LeftHand','right-foot':'RightFoot','left-foot':'LeftFoot'};
    const effector=named[guide.type]||(guide.type==='end-effector'&&guide.joint_names?.length===1?guide.joint_names[0]:null);
    if(!effector||guide.source_frames.length!==1){output.textContent='Select one hand or foot and one source frame before moving a target.';return;}
    const sourceHash=guide.sha256;solve.disabled=true;disposePreview?.();disposePreview=null;output.textContent='Solving bounded pose target…';
    try{const response=await fetch('/api/pose-target',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({motion:guide.motion,sha256:guide.sha256,source_frame:guide.source_frames[0],effector,offset_m:offsets.map(x=>Number(x.value)),max_edit_degrees:Number(budget.value)})});const result=await response.json();if(!response.ok)throw Error(result.error||'Target authoring failed');if(!guides.includes(guide)||guide.sha256!==sourceHash)return;
     output.replaceChildren();const note=document.createElement('p');note.textContent=`${result.reached?'Target reached':'Target not reached; guide unchanged'}. Error ${(result.audit.actual_native_fk_target_error_m*1000).toFixed(1)} mm. Maximum edit ${result.audit.max_local_edit_degrees.toFixed(1)}°. Floor depth ${(result.audit.candidate_floor_depth_m*1000).toFixed(1)} mm. No collision or realism approval.`;output.append(note);
     const audit=document.createElement('a');audit.href=result.base+'audit.json';audit.target='_blank';audit.rel='noopener';audit.textContent='Pose audit';output.append(audit);disposePreview=targetPreview(output,result);
     if(result.reached){const apply=document.createElement('button');apply.type='button';apply.className='btn';apply.textContent='Use this target';apply.onclick=()=>{if(!guides.includes(guide)||guide.sha256!==sourceHash)return;const frames=guide.frame_indices.slice();Object.keys(guide).forEach(k=>delete guide[k]);Object.assign(guide,result.guide,{frame_indices:frames});render();changed();};output.append(apply);}
    }catch(error){output.textContent=error.message;}finally{solve.disabled=false;}
   };
   row.append(source,kindLabel,label,editor,remove);list.append(row);
  });
 }
 return {
  snapshot:()=>structuredClone(guides),
  replace(value){guides=structuredClone(value||[]);render();},
  async capture(context,frame){
   if(guides.length>=32)throw Error('Use at most 32 pose guides.');
   const response=await fetch(context.base+'motion.npz');if(!response.ok)throw Error('Could not read the selected pose source.');
   const bytes=await response.arrayBuffer(),digest=await crypto.subtle.digest('SHA-256',bytes);
   const sha256=Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,'0')).join('');
   guides.push({type:'right-hand',motion:context.base.replace('/files/','reports/')+'motion.npz',sha256,source_frames:[frame],frame_indices:[frame]});render();changed();
  },
  request(frameCount){
   const occupied=new Set();
   for(const guide of guides){
    if(guide.frame_indices.length!==guide.source_frames.length)throw Error('Each pose guide needs one target frame per source frame.');
    let previous=-1;
    for(const frame of guide.frame_indices){
     if(!Number.isInteger(frame)||frame<0||frame>=frameCount||frame<=previous)throw Error(`Pose guide frames must be sorted and within 0–${frameCount-1}.`);
     if(occupied.has(frame))throw Error('Pose guides share a target frame. Use one guide for that frame.');
     previous=frame;occupied.add(frame);
    }
   }
   return structuredClone(guides);
  }
 };
}
