import assert from 'node:assert/strict';
import * as THREE from '../assets/viewer/node_modules/three/build/three.module.js';
import {sceneObjectPose,gripSurfaceNormal,pickObjectGrip,createSceneGripPicker} from '../scripts/scene-grip-picker.js';

const box={geometry:{schema:'strep-object-geometry-v1',shape:'box',size_m:[.4,.6,.8]}},sphere={geometry:{schema:'strep-object-geometry-v1',shape:'sphere',radius_m:.27}};
const identity={frame:0,translation_m:[0,0,0],rotation_xyzw:[0,0,0,1]};
const moved={frame:20,translation_m:[2,1,-3],rotation_xyzw:new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),Math.PI/2).toArray()};
box.keyframes=[identity,moved];sphere.keyframes=[identity,moved];
const near=(a,b)=>assert(new THREE.Vector3().fromArray(a).distanceTo(new THREE.Vector3().fromArray(b))<1e-10,`${a} != ${b}`);
const middle=sceneObjectPose(THREE,box,10);near(middle.translation_m,[1,.5,-1.5]);
assert(Math.abs(new THREE.Quaternion().fromArray(middle.rotation_xyzw).angleTo(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),Math.PI/4)))<1e-7);
assert.deepEqual(sceneObjectPose(THREE,box,30),moved);assert.deepEqual(sceneObjectPose(THREE,box,-1),identity);
assert.deepEqual(sceneObjectPose(THREE,{keyframes:[moved]},30),moved);

const cases=[];
for(const object of [box,sphere])for(const frame of [0,5,10,20,30])for(let i=0;i<30;i++){
 const pose=sceneObjectPose(THREE,object,frame),q=new THREE.Quaternion().fromArray(pose.rotation_xyzw),t=new THREE.Vector3().fromArray(pose.translation_m);
 const target=object===box?new THREE.Vector3(.1*Math.cos(i),.2*Math.sin(i),.3*Math.cos(i)):new THREE.Vector3(Math.cos(i),.4,Math.sin(i)).normalize().multiplyScalar(.27);
 if(object===box)target.setComponent(i%3,box.geometry.size_m[i%3]/2*(i%2?1:-1));
 const outward=object===box?new THREE.Vector3().setComponent(i%3,i%2?1:-1):target.clone().normalize();
 const ray=new THREE.Ray(target.clone().add(outward).applyQuaternion(q).add(t),outward.clone().negate().applyQuaternion(q));
 const point=pickObjectGrip(THREE,object,pose,ray);near(point,target.toArray());
 const normal=gripSurfaceNormal(THREE,object,point);near(normal.toArray(),outward.toArray());cases.push({geometry:object.geometry,point,normal:normal.toArray()});
}
assert.equal(pickObjectGrip(THREE,box,identity,new THREE.Ray(new THREE.Vector3(2,2,2),new THREE.Vector3(1,0,0))),null);
assert.equal(pickObjectGrip(THREE,sphere,identity,new THREE.Ray(new THREE.Vector3(2,2,2),new THREE.Vector3(1,0,0))),null);
assert.throws(()=>pickObjectGrip(THREE,box,identity,new THREE.Ray(new THREE.Vector3(1,.3,0),new THREE.Vector3(-1,0,0))),/edges/);
assert.throws(()=>gripSurfaceNormal(THREE,sphere,[0,0,0]),/surface/);
assert.throws(()=>gripSurfaceNormal(THREE,box,[NaN,0,0]),/finite/);
near(pickObjectGrip(THREE,box,identity,new THREE.Ray(new THREE.Vector3(),new THREE.Vector3(1,0,0))),[.2,0,0]);

// Exercise interaction with real Three geometry, but no browser/WebGL/network.
const events={},canvas={style:{},addEventListener:(n,f)=>events[n]=f,removeEventListener:n=>delete events[n],focus(){},getBoundingClientRect:()=>({left:0,top:0,width:400,height:400})};
const world=new THREE.Scene(),camera=new THREE.PerspectiveCamera(42,1,.01,200);camera.position.set(0,0,2);camera.lookAt(0,0,0);camera.updateMatrixWorld(true);
const controls={enabled:true};let picked=null,status='',isPicking=false,pauses=0;
const ctx={spec:{objects:{target:box}},frame:0,visible:true,changed:false};
const savedScene=JSON.stringify(ctx.spec);
const picker=createSceneGripPicker({THREE,world,camera,canvas,getContext:()=>ctx,getControls:()=>controls,pause:()=>pauses++,onPoint:p=>picked=p,onStatus:s=>status=s,onPicking:p=>isPicking=p});
const edit={point_m:[0,0,.4],start_frame:5,end_frame:15};
picker.setDraft({target_object:'target'},edit,true);const marker=world.children.find(c=>c.isMesh),line=world.children.find(c=>c.isLine);
assert.equal(marker.visible,true);assert.equal(line.visible,true);assert.equal(marker.material.color.getHex(),0x8b8592);
ctx.frame=10;picker.update();near(marker.position.toArray(),new THREE.Vector3(0,0,.4).applyQuaternion(new THREE.Quaternion().fromArray(middle.rotation_xyzw)).add(new THREE.Vector3(1,.5,-1.5)).toArray());
assert.equal(marker.material.color.getHex(),0xb64ce1);ctx.frame=0;
picker.toggle();assert(isPicking);assert.equal(controls.enabled,false);assert.equal(pauses,1);
let stopped=0;const event=(x,y)=>({button:0,clientX:x,clientY:y,preventDefault(){},stopImmediatePropagation(){stopped++;}});
events.pointerdown(event(0,0));assert.equal(picked,null);assert(isPicking);assert.match(status,/No target hit/);
events.pointerdown(event(200,200));near(picked,[0,0,.4]);assert.equal(isPicking,false);assert.equal(controls.enabled,true);assert.equal(stopped,2);
picker.toggle();events.keydown({key:'Escape',preventDefault(){},stopPropagation(){}});assert.equal(isPicking,false);assert.equal(controls.enabled,true);
ctx.changed=true;picker.toggle();assert.equal(isPicking,false);assert.match(status,/unsaved/);picker.update();assert.equal(marker.visible,false);
ctx.changed=false;picker.toggle();ctx.visible=false;picker.update();assert.equal(isPicking,false);assert.equal(controls.enabled,true);
ctx.visible=true;controls.enabled=false;picker.toggle();picker.cancel();assert.equal(controls.enabled,false);controls.enabled=true;
picker.setDraft({target_object:'target'},edit,false);assert.equal(marker.visible,false);picker.toggle();assert.equal(isPicking,false);
picker.setDraft(null);picker.update();assert.equal(marker.visible,false);picker.dispose();assert.equal(world.children.length,0);assert.deepEqual(events,{});
assert.equal(JSON.stringify(ctx.spec),savedScene,'Picking must never mutate the saved scene');
if(process.argv.includes('--fixture-json'))console.log(JSON.stringify(cases));
else console.log(`Grip picker: ${cases.length} analytic transformed hits, moving poses, surface rejection, preview tracking, cancellation, source guards and cleanup pass. No browser or network used.`);
