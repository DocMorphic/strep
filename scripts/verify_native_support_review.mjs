// Offline GLB loader/clock checks, without browser rendering or quality approval.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {GLTFLoader} from '../assets/viewer/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import {AnimationMixer,LoopOnce,MeshStandardMaterial} from '../assets/viewer/node_modules/three/build/three.module.js';
import {useGreyMaterials} from './native-grey-loader.mjs';
import validator from '../assets/viewer/node_modules/gltf-validator/index.js';
const review=JSON.parse(fs.readFileSync(process.argv[2])),folder=path.resolve(process.argv[3]),output=path.resolve(process.argv[4]);
if(fs.existsSync(output))throw Error('Fresh loader receipt required');
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const resultBytes=fs.readFileSync(path.join(folder,'result.json')),result=JSON.parse(resultBytes);
if(hash(resultBytes)!==review.result_sha256||result.quality_approved!==false||review.quality_approved!==false)throw Error('Changed/unapproved support result required');
const helper=fs.readFileSync(new URL('./soma-preview-skin.js',import.meta.url),'utf8'),threeURL=new URL('../assets/viewer/node_modules/three/build/three.module.js',import.meta.url).href;
const {enableEightWeights}=await import('data:text/javascript;base64,'+Buffer.from(helper.replace("from 'three'",'from '+JSON.stringify(threeURL))).toString('base64'));
const loader=new GLTFLoader(),rows=[],seeks=[0,...review.supports.flatMap(s=>s.stance_s),review.duration_s,...review.supports.flatMap(s=>s.stance_s).reverse(),0];
useGreyMaterials(loader,{MeshStandardMaterial});
let originalClocks;
for(const version of review.versions){
 if(!/^(input|candidate|trial-[0-3])\.glb$/.test(version.id)||version.url!==`/files/native-support-jobs/${review.id}/${version.id}`)throw Error('Invalid support asset identity');
 const file=path.join(folder,version.id),bytes=fs.readFileSync(file);
 if(hash(bytes)!==version.sha256||result.outputs[version.id]!==version.sha256)throw Error('Changed support clip');
 const validation=await validator.validateBytes(new Uint8Array(bytes),{uri:version.id,maxIssues:1000});
 const gltf=await loader.parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),pathToFileURL(folder+path.sep).href);
 if(gltf.animations.length!==1||gltf.animations[0].duration!==review.duration_s)throw Error('Different native clip duration');
 const clocks=gltf.animations[0].tracks.map(t=>({name:t.name,type:t.ValueTypeName,times:Array.from(t.times)}));
 if(!originalClocks)originalClocks=clocks;else if(JSON.stringify(clocks)!==JSON.stringify(originalClocks))throw Error('Changed native clock/track population');
 let meshes=0,vertices=0,maxWeightError=0,eightWeights=0;
 gltf.scene.traverse(n=>{if(!n.isSkinnedMesh)return;meshes++;n.material=new MeshStandardMaterial({color:0x9b9fa5,roughness:.8});enableEightWeights(n);const a=n.geometry.getAttribute('skinWeight'),b=n.geometry.getAttribute('weights_1');if(b)eightWeights++;vertices+=a.count;for(let i=0;i<a.count;i++)maxWeightError=Math.max(maxWeightError,Math.abs(a.getX(i)+a.getY(i)+a.getZ(i)+a.getW(i)+(b?b.getX(i)+b.getY(i)+b.getZ(i)+b.getW(i):0)-1));});
 if(!meshes||maxWeightError>1e-5)throw Error('Incomplete preview skin');
 const mixer=new AnimationMixer(gltf.scene),action=mixer.clipAction(gltf.animations[0]);action.setLoop(LoopOnce,1);action.clampWhenFinished=true;action.play();
 const seen=new Map();
 for(const time of seeks){action.enabled=true;action.paused=false;mixer.setTime(time);gltf.scene.updateMatrixWorld(true);const pose=[];gltf.scene.traverse(n=>{if(!n.isBone)return;if(!n.matrixWorld.elements.every(Number.isFinite))throw Error('Invalid forward/backward pose');pose.push(n.matrixWorld.elements.slice());});if(Math.abs(action.time-time)>1e-10)throw Error('Animation playhead did not seek to requested seconds');const encoded=JSON.stringify(pose);if(seen.has(time)&&seen.get(time)!==encoded)throw Error('Repeated fractional seek changed the pose');seen.set(time,encoded);}
 mixer.stopAllAction();mixer.uncacheRoot(gltf.scene);
 rows.push({id:version.id,sha256:version.sha256,errors:validation.issues.numErrors,warnings:validation.issues.numWarnings,warning_messages:validation.issues.messages.filter(m=>m.severity<=1),meshes,vertices,eight_weight_meshes:eightWeights,maximum_weight_sum_error:maxWeightError,native_duration_s:gltf.animations[0].duration});
}
if(rows.some(r=>r.errors))throw Error('GLB validation errors');
fs.writeFileSync(output,JSON.stringify({result_sha256:review.result_sha256,assets:rows,seeks_s:seeks,native_clocks_unchanged:true,repeat_seek_poses_exact:true,browser_render_verified:false,quality_approved:false},null,2)+'\n');
console.log(JSON.stringify({assets:rows.length,errors:rows.reduce((n,r)=>n+r.errors,0),warnings:rows.reduce((n,r)=>n+r.warnings,0),browser_render_verified:false}));
