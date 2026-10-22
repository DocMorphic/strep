import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import * as THREE from '../assets/viewer/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../assets/viewer/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import {useGreyMaterials} from '../scripts/native-grey-loader.mjs';
import {prepareNativeReview,extendNativeReviewBounds} from '../scripts/review-native-skin.mjs';
globalThis.ProgressEvent??=class{constructor(type,options){Object.assign(this,{type},options);}};
function fixture(slots){
 const doc={asset:{version:'2.0'},buffers:[{byteLength:0}],bufferViews:[],accessors:[],nodes:[],meshes:[],skins:[],animations:[],scenes:[{nodes:[]}],scene:0},chunks=[];let length=0;
 function acc(values,width,type='VEC4',component=5126){const array=component===5123?new Uint16Array(values):new Float32Array(values),bytes=new Uint8Array(array.buffer),index=doc.accessors.length;doc.bufferViews.push({buffer:0,byteOffset:length,byteLength:bytes.length});doc.accessors.push({bufferView:index,componentType:component,count:values.length/width,type,...(type==='SCALAR'&&component===5126?{min:[Math.min(...values)],max:[Math.max(...values)]}:{})});chunks.push(bytes);length+=bytes.length;const pad=(4-length%4)%4;if(pad){chunks.push(new Uint8Array(pad));length+=pad;}return index;}
 const positions=[.2,.3,.4,.4,.3,.4,.2,.5,.4],attributes={POSITION:acc(positions,3,'VEC3')};doc.accessors[attributes.POSITION].min=[.2,.3,.4];doc.accessors[attributes.POSITION].max=[.4,.5,.4];
 const weights=slots===2?[.05,.1,.15,.2,.1,.1,.15,.1496]:[.1,.2,.3,.3996];
 for(let slot=0;slot<slots;slot++){attributes['JOINTS_'+slot]=acc(Array.from({length:3},()=>[0,1,2,3].map(i=>i+slot*4)).flat(),4,'VEC4',5123);attributes['WEIGHTS_'+slot]=acc(Array.from({length:3},()=>weights.slice(slot*4,slot*4+4)).flat(),4);}
 const joints=Array.from({length:slots*4},(_,i)=>i+1),inverse=joints.flatMap(i=>new THREE.Matrix4().makeTranslation(-i*.5,0,0).toArray());
 doc.meshes.push({primitives:[{attributes}]});doc.nodes.push({mesh:0,skin:0,translation:[7,0,0]});for(const i of joints)doc.nodes.push({translation:[i,0,0]});doc.scenes[0].nodes=doc.nodes.map((_,i)=>i);
 doc.skins.push({joints,inverseBindMatrices:acc(inverse,16,'MAT4')});
 const input=acc([0,1],1,'SCALAR'),output=acc([1,0,0,2,2,3],3,'VEC3');doc.animations.push({samplers:[{input,output,interpolation:'LINEAR'}],channels:[{sampler:0,target:{node:1,path:'translation'}}]});doc.animations.push(structuredClone(doc.animations[0]));
 doc.buffers[0].byteLength=length;let json=new TextEncoder().encode(JSON.stringify(doc)),padding=(4-json.length%4)%4;const padded=new Uint8Array(json.length+padding);padded.fill(32);padded.set(json);json=padded;
 const buffer=new ArrayBuffer(28+json.length+length),view=new DataView(buffer);[0x46546c67,2,buffer.byteLength,json.length,0x4e4f534a].forEach((v,i)=>view.setUint32(i*4,v,true));new Uint8Array(buffer,20,json.length).set(json);view.setUint32(20+json.length,length,true);view.setUint32(24+json.length,0x004e4942,true);let offset=28+json.length;for(const chunk of chunks){new Uint8Array(buffer,offset,chunk.length).set(chunk);offset+=chunk.length;}
 return {buffer,weights:weights.map(Math.fround),positions:positions.map(Math.fround)};
}

for(const slots of [1,2]){
 const {buffer,weights,positions}=fixture(slots),original=buffer.slice(0),loader=new GLTFLoader();useGreyMaterials(loader,THREE);
 const gltf=await loader.parseAsync(buffer,''),selected={reference_node_index:1,animation_index:1,duration_s:1};
 const {model,skin,root,clip}=await prepareNativeReview(THREE,gltf,buffer,selected);
 assert.equal(root,gltf.parser.associations&&await gltf.parser.getDependency('node',1));assert.equal(clip,gltf.animations[1]);
 const mixer=new THREE.AnimationMixer(model),action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
 const local=new THREE.Box3(),world=new THREE.Box3();
 for(const t of [0,.25,1,0,.8,.1]){
  action.enabled=true;action.paused=false;mixer.setTime(t);model.updateMatrixWorld(true);skin.update();
  extendNativeReviewBounds(THREE,model,skin,root,local,world);
  for(let v=0;v<3;v++){
   const p=new THREE.Vector3().fromArray(positions,v*3),expected=new THREE.Vector3();
   weights.forEach((w,i)=>expected.addScaledVector(p.clone().add(new THREE.Vector3((i+1)*.5,0,0)).add(i===0?new THREE.Vector3(t,2*t,3*t):new THREE.Vector3()),w/weights.reduce((a,b)=>a+b,0)));
   assert(skin.point([0,0,v]).distanceTo(expected)<1e-7);assert(world.containsPoint(skin.point([0,0,v])));
  }
 }
 const mesh=new THREE.Mesh(new THREE.BoxGeometry(20,20,20),new THREE.MeshStandardMaterial());mesh.position.x=30;model.add(mesh);model.updateMatrixWorld(true);
 extendNativeReviewBounds(THREE,model,skin,root,local,world);assert.equal(world.max.x,40);assert.equal(world.max.y,10);
 const rootPosition=root.getWorldPosition(new THREE.Vector3());assert.equal(local.max.x,40-rootPosition.x);
 const shader={uniforms:{},vertexShader:'#include <skinbase_vertex>\n#include <skinnormal_vertex>\n#include <skinning_vertex>'};skin.meshes[0].mesh.material.onBeforeCompile(shader);
 assert.match(shader.vertexShader,/nativePoint.w = 1.0/);if(slots===2)assert.match(shader.vertexShader,/boneMatD\*skinVertex\*weights_1.w/);
 assert.deepEqual(buffer,original);mixer.stopAllAction();mixer.uncacheRoot(model);model.traverse(n=>{n.geometry?.dispose();n.material?.dispose();});
}
const html=await readFile(new URL('../scripts/human-review.html',import.meta.url),'utf8');
assert.match(html,/useGreyMaterials\(loader,THREE\)/);assert.match(html,/manifest.native_asset_bytes_preserved===true/);
assert.match(html,/if\(token!==version\)\{dispose\(prepared.model\);return;/);
assert.match(html,/nativeSkin\?\.update\(\)/);assert.match(html,/if\(nativeSkin\)extendNativeReviewBounds/);
assert(!html.includes('SOMA preview asset: NVIDIA Kimodo'));
// Execute the actual camera handlers: changing viewpoint must keep skin updates live.
const cameraHandlers=html.split("$('front').onclick=")[1].split('\n')[0];
const controls=Object.fromEntries(['front','side','fit','follow','ground'].map(id=>[id,{checked:true}]));
const native={update(){}};let fits=0;const ground={visible:false};
const cameraState=Function('$','fitCamera','ground','skin',
 "let view='side',nativeSkin=skin; $('front').onclick="+cameraHandlers+'; return ()=>({view,nativeSkin});'
)(id=>controls[id],()=>{fits++;},ground,native);
for(const id of ['front','side','fit','follow']){
 (controls[id].onclick??controls[id].onchange)();
 assert.equal(cameraState().nativeSkin,native,`${id} must preserve native playback`);
 if(id==='front'||id==='side')assert.equal(cameraState().view,id);
}
assert.equal(fits,4);controls.ground.onchange();assert.equal(ground.visible,true);
console.log('Native review: actual loader, four/eight influences, source inverse binds, independent skin positions, endpoint/backward playback, complete mesh framing and byte preservation passed. WebGL rasterization not exercised.');
