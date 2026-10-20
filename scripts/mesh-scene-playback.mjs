import {sourceGLB,bindSourceSkin} from './native-source-skin.mjs';
import {scenePrimitive,scenePrimitiveMesh} from './scene-object-geometry.js';

export function setPose(THREE,object,keys,time){
 let i=0;while(i+1<keys.length&&keys[i+1].time_s<=time)i++;
 const a=keys[i],b=keys[Math.min(i+1,keys.length-1)],u=a===b?0:(time-a.time_s)/(b.time_s-a.time_s);
 object.position.fromArray(a.translation_m).lerp(new THREE.Vector3().fromArray(b.translation_m),u);
 object.quaternion.fromArray(a.rotation_xyzw).slerp(new THREE.Quaternion().fromArray(b.rotation_xyzw),u);
 object.updateMatrixWorld(true);
}

export async function createScenePlayback({THREE,loader,data,readAsset}){
 if(data.schema!=='strep-mesh-scene-preview-v1'||data.skin_weight_policy!=='native-all-influence-unit-sum'||!(data.duration_s>0)||data.motion_fitted!==false||data.geometry_evaluated!==false||data.quality_approved!==false||data.release_approved!==false)throw Error('Saved original scene with an explicit native skin policy required.');
 const root=new THREE.Group(),actors=new Map(),objects=new Map();let time=0,totalBytes=0;
 const dispose=()=>{for(const a of actors.values()){a.mixer.stopAllAction();a.mixer.uncacheRoot(a.model);}root.traverse(n=>{n.geometry?.dispose();if(n.material)for(const m of Array.isArray(n.material)?n.material:[n.material])m.dispose();});root.clear();};
 try{
  async function load(entry){
   const bytes=await readAsset(entry);totalBytes+=bytes.byteLength;if(totalBytes>128*1024**2)throw Error('Combined preview source limit is 128 MiB.');
   const source=sourceGLB(bytes.slice(0));const gltf=await loader.parseAsync(bytes,'');
   return {source,gltf};
  }
  for(const [name,entry] of Object.entries(data.actors)){
   const {source,gltf}=await load(entry),wrapper=new THREE.Group();root.add(wrapper);wrapper.add(gltf.scene);
   setPose(THREE,wrapper,[{time_s:0,...entry.placement}],0);
   const clip=gltf.animations[entry.animation_index];
   if(!Number.isInteger(entry.animation_index)||!clip||Math.abs(clip.duration-data.duration_s)>1e-6)throw Error('Exact saved actor clip and duration required.');
   const mixer=new THREE.AnimationMixer(gltf.scene),action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;
   const skin=await bindSourceSkin(THREE,gltf,source,wrapper);actors.set(name,{model:gltf.scene,wrapper,mixer,action,skin});
  }
  for(const [name,entry] of Object.entries(data.props)){
   const {gltf}=await load(entry),wrapper=new THREE.Group();wrapper.add(gltf.scene);root.add(wrapper);objects.set(name,{wrapper,keys:entry.keyframes});
   gltf.scene.traverse(n=>{if(n.isMesh){n.frustumCulled=false;n.material=n.material.clone();n.material.color.setHex(0xb9a47e);}});
  }
  for(const [name,entry] of Object.entries(data.objects)){
   const wrapper=new THREE.Group(),mesh=new THREE.Mesh(scenePrimitiveMesh(THREE,entry),new THREE.MeshStandardMaterial({color:0xafa48f,roughness:.8}));mesh.scale.fromArray(scenePrimitive(entry).scale);wrapper.add(mesh);root.add(wrapper);objects.set(name,{wrapper,keys:entry.keyframes});
  }
  const planeMeshes=[];
  for(const [name,plane] of Object.entries(data.planes)){
   const mesh=new THREE.Mesh(new THREE.PlaneGeometry(1,1),new THREE.MeshBasicMaterial({color:0xbccbd3,transparent:true,opacity:.18,side:THREE.DoubleSide,depthWrite:false}));
   mesh.position.fromArray(plane.normal_world).multiplyScalar(plane.offset_m);mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),new THREE.Vector3().fromArray(plane.normal_world));mesh.name=name;root.add(mesh);planeMeshes.push(mesh);
  }
  function seek(value){
   if(typeof value!=='number'||!Number.isFinite(value))throw Error('Finite preview time required.');time=Math.max(0,Math.min(data.duration_s,value));
   for(const a of actors.values()){a.action.reset().play();a.mixer.setTime(time);a.wrapper.updateMatrixWorld(true);a.skin.update();}
   for(const o of objects.values())setPose(THREE,o.wrapper,o.keys,time);
   return time;
  }
  function contact(index){
   const c=data.mesh_contacts[index];if(!c)throw Error('Choose a saved mesh contact.');
   const actor=actors.get(c.actor),target=objects.get(c.prop),points=c.vertices.map(ref=>actor.skin.point(ref));
   const effector=points.reduce((sum,p)=>sum.add(p),new THREE.Vector3()).multiplyScalar(1/points.length);
   const grip=new THREE.Vector3().fromArray(c.grip_position_m).applyMatrix4(target.wrapper.matrixWorld);
   return {time_s:time,effector:effector.toArray(),target:grip.toArray(),gap_m:effector.distanceTo(grip),active:time>=c.interval_s[0]-1e-9&&time<=c.interval_s[1]+1e-9};
  }
  function bounds(){
   const before=time,box=new THREE.Box3();
   for(let i=0;i<=24;i++){seek(data.duration_s*i/24);for(const a of actors.values())for(const record of a.skin.meshes)for(let v=0;v<record.positions.count;v++)box.expandByPoint(record.point(v));for(const o of objects.values())box.union(new THREE.Box3().setFromObject(o.wrapper));}
   seek(before);const sphere=box.getBoundingSphere(new THREE.Sphere());sphere.radius=Math.max(.2,sphere.radius);
   for(const plane of planeMeshes)plane.scale.setScalar(sphere.radius*4);
   return sphere;
  }
  seek(0);return {root,actors,objects,seek,contact,bounds,dispose,get time(){return time;}};
 }catch(error){dispose();throw error;}
}
