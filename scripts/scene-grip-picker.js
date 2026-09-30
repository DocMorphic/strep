import {scenePrimitive} from './scene-object-geometry.js';

// Use the same pose for the object, draft marker and ray query.
export function sceneObjectPose(THREE, object, frame) {
 const keys=object.keyframes;
 if(frame<=keys[0].frame)return keys[0];
 const right=keys.findIndex(k=>k.frame>=frame);
 if(right<0)return keys[keys.length-1];
 const a=keys[right-1],b=keys[right],t=(frame-a.frame)/(b.frame-a.frame);
 return {translation_m:new THREE.Vector3().fromArray(a.translation_m).lerp(new THREE.Vector3().fromArray(b.translation_m),t).toArray(),
  rotation_xyzw:new THREE.Quaternion().fromArray(a.rotation_xyzw).slerp(new THREE.Quaternion().fromArray(b.rotation_xyzw),t).toArray()};
}

export function gripSurfaceNormal(THREE, object, point) {
 if(!Array.isArray(point)||point.length!==3||point.some(x=>typeof x!=='number'||!Number.isFinite(x)))throw Error('Enter three finite grip coordinates.');
 const primitive=scenePrimitive(object),p=new THREE.Vector3().fromArray(point);
 if(primitive.shape==='sphere'){
  if(Math.abs(p.length()-primitive.scale[0]/2)>1e-6||p.length()<=1e-12)throw Error('Grip must lie on the sphere surface.');
  return p.normalize();
 }
 if(primitive.shape==='cylinder'){
  const radius=primitive.scale[0]/2,half=primitive.scale[1]/2,rho=Math.hypot(point[0],point[2]);
  const side=rho-radius,cap=Math.abs(point[1])-half;
  const outsideLength=Math.hypot(Math.max(0,side),Math.max(0,cap));
  const distance=outsideLength+Math.min(Math.max(side,cap),0);
  if(Math.abs(distance)>1e-6||(outsideLength<=1e-12&&Math.abs(side-cap)<=1e-12))throw Error('Choose the cylinder side or a cap, away from the rim.');
  if(outsideLength>1e-12){
   const radial=Math.max(0,side)/outsideLength,vertical=Math.max(0,cap)/outsideLength;
   return new THREE.Vector3(radial?radial*point[0]/rho:0,vertical*Math.sign(point[1]),radial?radial*point[2]/rho:0);
  }
  if(side>cap){if(rho<=1e-12)throw Error('Cylinder side normal is undefined at the axis.');return new THREE.Vector3(point[0]/rho,0,point[2]/rho);}
  if(Math.abs(point[1])<=1e-12)throw Error('Cylinder cap normal is undefined at the center.');
  return new THREE.Vector3(0,Math.sign(point[1]),0);
 }
 const q=point.map((x,i)=>Math.abs(x)-primitive.scale[i]/2),maximum=Math.max(...q);
 const distance=Math.hypot(...q.map(x=>Math.max(0,x)))+Math.min(maximum,0);
 const faces=q.map((x,i)=>Math.abs(x-maximum)<=1e-12?i:-1).filter(i=>i>=0);
 if(Math.abs(distance)>1e-6||faces.length!==1)throw Error('Choose a smooth box face, away from edges and corners.');
 return new THREE.Vector3().setComponent(faces[0],Math.sign(point[faces[0]]));
}

export function pickObjectGrip(THREE, object, pose, ray) {
 const primitive=scenePrimitive(object),rotation=new THREE.Quaternion().fromArray(pose.rotation_xyzw);
 const inverse=new THREE.Matrix4().compose(new THREE.Vector3().fromArray(pose.translation_m),rotation,new THREE.Vector3(1,1,1)).invert();
 const localRay=ray.clone().applyMatrix4(inverse),point=new THREE.Vector3();
 if(primitive.shape==='cylinder'){
  const radius=primitive.scale[0]/2,half=primitive.scale[1]/2,o=localRay.origin,d=localRay.direction,hits=[];
  const a=d.x*d.x+d.z*d.z,b=2*(o.x*d.x+o.z*d.z),c=o.x*o.x+o.z*o.z-radius*radius;
  if(a>0){
   const discriminant=b*b-4*a*c;
   if(discriminant>=0){
    // Stable quadratic roots even when the near intersection is very close.
    const q=-.5*(b+(b>=0?1:-1)*Math.sqrt(discriminant));
    const roots=q===0?[-b/(2*a)]:[q/a,c/q];
    for(const t of roots)if(t>=0&&Math.abs(o.y+t*d.y)<=half+1e-12)hits.push(t);
   }
  }
  if(d.y!==0)for(const y of [-half,half]){
   const t=(y-o.y)/d.y;
   if(t>=0&&Math.hypot(o.x+t*d.x,o.z+t*d.z)<=radius+1e-12)hits.push(t);
  }
  if(!hits.length)return null;
  localRay.at(Math.min(...hits),point);
  const local=point.toArray();gripSurfaceNormal(THREE,object,local);return local;
 }
 const hit=primitive.shape==='sphere'
  ?localRay.intersectSphere(new THREE.Sphere(new THREE.Vector3(),primitive.scale[0]/2),point)
  :localRay.intersectBox(new THREE.Box3(new THREE.Vector3().fromArray(primitive.scale).multiplyScalar(-.5),new THREE.Vector3().fromArray(primitive.scale).multiplyScalar(.5)),point);
 if(!hit)return null;
 // Analytic intersections avoid placing grips inside inscribed render triangles.
 const local=point.toArray();gripSurfaceNormal(THREE,object,local);return local;
}

export function createSceneGripPicker({THREE,world,camera,canvas,getContext,getControls,pause,onPoint,onStatus,onPicking}) {
 let draft=null,picking=false,previousControls=true;
 const marker=new THREE.Mesh(new THREE.SphereGeometry(.012,12,8),new THREE.MeshBasicMaterial({color:0xb64ce1,depthTest:false}));
 const normal=new THREE.Line(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({color:0xb64ce1,depthTest:false}));
 marker.renderOrder=32;normal.renderOrder=32;marker.visible=normal.visible=false;world.add(marker,normal);
 function cancel(){if(picking){const controls=getControls();if(controls)controls.enabled=previousControls;}picking=false;canvas.style.cursor='';onPicking(false);}
 function update(){
  marker.visible=normal.visible=false;
  const ctx=getContext(),object=ctx.spec?.objects[draft?.object];
  if(!object||ctx.changed||!ctx.visible){if(picking)cancel();return;}
  if(!draft?.include)return;
  const point=draft.edit.point_m;if(!Array.isArray(point)||point.length!==3||point.some(x=>!Number.isFinite(x)))return;
  const pose=sceneObjectPose(THREE,object,ctx.frame),rotation=new THREE.Quaternion().fromArray(pose.rotation_xyzw);
  marker.position.fromArray(point).applyQuaternion(rotation).add(new THREE.Vector3().fromArray(pose.translation_m));marker.visible=true;
  const active=ctx.frame>=draft.edit.start_frame&&ctx.frame<=draft.edit.end_frame;
  marker.material.color.setHex(active?0xb64ce1:0x8b8592);normal.material.color.copy(marker.material.color);
  try{const direction=gripSurfaceNormal(THREE,object,point).negate().applyQuaternion(rotation);normal.geometry.setFromPoints([marker.position,marker.position.clone().addScaledVector(direction,.06)]);normal.visible=true;}catch{}
 }
 function toggle(){
  if(picking){cancel();onStatus('Grip picking cancelled. Draft preserved.');return;}
  const ctx=getContext();
  if(!draft||!draft.include||!ctx.spec?.objects[draft.object]){onStatus('Include a hand-to-object contact first.');return;}
  if(ctx.changed){onStatus('Placement edits are unsaved. Reload the saved scene before picking.');return;}
  pause();const controls=getControls();previousControls=controls?.enabled??true;if(controls)controls.enabled=false;
  picking=true;canvas.style.cursor='crosshair';canvas.tabIndex=0;canvas.scrollIntoView?.({block:'center',behavior:'smooth'});canvas.focus({preventScroll:true});onPicking(true);
  onStatus(`Click ${draft.object} in the preview to place the grip. Only this target object is picked. Escape cancels.`);
 }
 function pointer(event){
  if(!picking||event.button!==0)return;
  event.preventDefault();event.stopImmediatePropagation();
  const ctx=getContext();if(ctx.changed||!ctx.visible){cancel();onStatus('Scene changed. Pick again from a saved scene.');return;}
  try{
   const rect=canvas.getBoundingClientRect();if(rect.width<=0||rect.height<=0)return;
   const ray=new THREE.Raycaster();ray.setFromCamera(new THREE.Vector2((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1),camera);
   const object=ctx.spec.objects[draft.object],point=pickObjectGrip(THREE,object,sceneObjectPose(THREE,object,ctx.frame),ray.ray);
   if(!point){onStatus('No target hit. Click the selected object, or press Escape.');return;}
   cancel();onPoint(point);onStatus('Draft grip placed. The purple marker follows the object; fit to create a separate animation candidate.');update();
  }catch(error){onStatus(error.message);}
 }
 function key(event){if(picking&&event.key==='Escape'){event.preventDefault();event.stopPropagation();cancel();onStatus('Grip picking cancelled. Draft preserved.');}}
 canvas.addEventListener('pointerdown',pointer,true);canvas.addEventListener('keydown',key);
 return {toggle,cancel,update,setDraft(contact,edit,include){cancel();draft=contact?{object:contact.target_object,edit:structuredClone(edit),include}:null;update();},
  dispose(){cancel();canvas.removeEventListener('pointerdown',pointer,true);canvas.removeEventListener('keydown',key);for(const item of [marker,normal]){world.remove(item);item.geometry.dispose();item.material.dispose();}}};
}
