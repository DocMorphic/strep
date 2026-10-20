import assert from 'node:assert/strict';
import * as THREE from '../assets/viewer/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../assets/viewer/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import {useGreyMaterials} from '../scripts/native-grey-loader.mjs';
import {sourceGLB} from '../scripts/native-source-skin.mjs';
import {createScenePlayback,setPose} from '../scripts/mesh-scene-playback.mjs';
globalThis.ProgressEvent??=class{constructor(type,options){Object.assign(this,{type},options);}};

// Deliberately non-unit original weights, nonidentity inverse binds, translated
// mesh node, eight distinct joints and explicit second clip. Normalizing the
// first four, retaining raw non-unit totals, or placing before LBS gives a wrong answer.
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
 const rotation=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),.4),placement={translation_m:[10,5,-3],rotation_xyzw:rotation.toArray()};
 const data={schema:'strep-mesh-scene-preview-v1',skin_weight_policy:'native-all-influence-unit-sum',duration_s:1,actors:{A:{animation_index:1,placement}},props:{},objects:{},planes:{},mesh_contacts:[],motion_fitted:false,geometry_evaluated:false,quality_approved:false,release_approved:false};
 const player=await createScenePlayback({THREE,loader,data,readAsset:async()=>buffer.slice(0)}),skin=player.actors.get('A').skin;
 for(const time of [0,.25,1,0,.8,.1]){
  player.seek(time);
  for(let v=0;v<3;v++){
   const p=new THREE.Vector3().fromArray(positions,v*3),expected=new THREE.Vector3();
   weights.forEach((w,i)=>expected.addScaledVector(p.clone().add(new THREE.Vector3((i+1)*.5,0,0)).add(i===0?new THREE.Vector3(time,2*time,3*time):new THREE.Vector3()),w/weights.reduce((a,b)=>a+b,0)));expected.applyQuaternion(rotation).add(new THREE.Vector3(...placement.translation_m));
   assert(skin.point([0,0,v]).distanceTo(expected)<1e-7,`source LBS ${slots} sets at ${time}`);
  }
 }
 const record=skin.meshes[0];for(let v=0;v<3;v++)for(let k=0;k<4;k++)assert.equal(record.mesh.geometry.attributes.skinWeight.getComponent(v,k),Math.fround(weights[k]/weights.reduce((a,b)=>a+b,0)));
 const shader={uniforms:{},vertexShader:'#include <skinbase_vertex>\n#include <skinnormal_vertex>\n#include <skinning_vertex>'};record.mesh.material.onBeforeCompile(shader);assert.match(shader.vertexShader,/nativePoint.w = 1.0/);if(slots===2)assert.match(shader.vertexShader,/boneMatD\*skinVertex\*weights_1.w/);
 assert.throws(()=>skin.point([0,1,0]),/missing/);assert.throws(()=>skin.point([0,0,3]),/Unknown/);assert.throws(()=>player.seek(NaN),/Finite/);
 player.bounds();assert.equal(player.time,.1);player.dispose();assert.equal(player.root.children.length,0);assert.deepEqual(buffer,original);
}
const object=new THREE.Group(),keys=[{time_s:0,translation_m:[0,0,0],rotation_xyzw:[0,0,0,1]},{time_s:2,translation_m:[2,4,6],rotation_xyzw:[0,1,0,0]}];setPose(THREE,object,keys,1);assert.deepEqual(object.position.toArray(),[1,2,3]);assert(Math.abs(object.quaternion.y-Math.SQRT1_2)<1e-14);setPose(THREE,object,keys,0);assert.deepEqual(object.position.toArray(),[0,0,0]);
assert.throws(()=>sourceGLB(new ArrayBuffer(32)),/GLB/);
console.log('Saved scene playback: joint normalization of all 4/8 source influences, explicit clips, non-unit input sums, placement after LBS, backwards/end scrubbing and object interpolation pass.');
