// Offline loader/asset checks. This does not render a browser or certify motion.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {GLTFLoader} from '../assets/viewer/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import {AnimationMixer, LoopOnce} from '../assets/viewer/node_modules/three/build/three.module.js';
import validator from '../assets/viewer/node_modules/gltf-validator/index.js';
const folder=path.resolve(process.argv[2]),output=path.resolve(process.argv[3]);
if(fs.existsSync(output))throw Error('Choose fresh verification output');
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const manifestBytes=fs.readFileSync(path.join(folder,'viewer-manifest.json')),manifest=JSON.parse(manifestBytes);
const buildBytes=fs.readFileSync(path.join(folder,'build.json')),build=JSON.parse(buildBytes);
for(const [relative,digest] of Object.entries(build.outputs)){
  const file=path.resolve(folder,relative),inside=path.relative(folder,file);
  if(inside.startsWith('..')||path.isAbsolute(inside)||hash(fs.readFileSync(file))!==digest)throw Error('Changed or escaping package file');
}
// Resolve only the copied helper's bare Three.js import for Node. Its skinning
// function remains identical to the browser module checked in the build record.
const helper=fs.readFileSync(path.join(folder,'soma-preview-skin.js'),'utf8');
const threeURL=new URL('../assets/viewer/node_modules/three/build/three.module.js',import.meta.url).href;
if(!helper.includes("from 'three'"))throw Error('Unexpected eight-weight helper import');
const {enableEightWeights}=await import('data:text/javascript;base64,'+Buffer.from(helper.replace("from 'three'",'from '+JSON.stringify(threeURL))).toString('base64'));
const rows=[],loader=new GLTFLoader();
for(const version of manifest.versions)for(const actor of version.actors){
  if(!/^assets\/\d+-[01]\.glb$/.test(actor.url))throw Error('Expected packaged actor asset');
  const file=path.join(folder,actor.url),bytes=fs.readFileSync(file);
  if(hash(bytes)!==actor.sha256)throw Error('Actor hash mismatch');
  const validation=await validator.validateBytes(new Uint8Array(bytes),{uri:actor.url,maxIssues:1000});
  const gltf=await loader.parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),pathToFileURL(folder+path.sep).href);
  if(gltf.animations.length!==1||Math.abs(gltf.animations[0].duration-version.duration_s)>1e-7)throw Error('Preview clock differs from recorded native duration');
  let meshes=0,vertices=0,maximumWeightError=0;
  gltf.scene.traverse(n=>{if(!n.isSkinnedMesh)return;meshes++;enableEightWeights(n);const a=n.geometry.getAttribute('skinWeight'),b=n.geometry.getAttribute('weights_1'),j=n.geometry.getAttribute('joints_1');
    if(!b||!j||a.count!==b.count||a.count!==j.count)throw Error('All eight SOMA influences required');
    vertices+=a.count;for(let i=0;i<a.count;i++)maximumWeightError=Math.max(maximumWeightError,Math.abs(a.getX(i)+a.getY(i)+a.getZ(i)+a.getW(i)+b.getX(i)+b.getY(i)+b.getZ(i)+b.getW(i)-1));
  });
  if(!meshes||maximumWeightError>1e-5)throw Error('Incomplete or unnormalized preview skin');
  const mixer=new AnimationMixer(gltf.scene),action=mixer.clipAction(gltf.animations[0]);action.setLoop(LoopOnce,1);action.clampWhenFinished=true;action.play();
  const seeks=[0,version.event_time_s,version.duration_s,version.event_time_s,0];
  for(const time of seeks){action.enabled=true;action.paused=false;mixer.setTime(time);gltf.scene.updateMatrixWorld(true);gltf.scene.traverse(n=>{if(n.isBone&&!n.matrixWorld.elements.every(Number.isFinite))throw Error('Invalid pose during forward/backward seek');});}
  mixer.stopAllAction();mixer.uncacheRoot(gltf.scene);
  rows.push({version:version.id,asset:actor.url,sha256:actor.sha256,duration_s:gltf.animations[0].duration,meshes,vertices,maximumWeightError,seeks,errors:validation.issues.numErrors,warnings:validation.issues.numWarnings,messages:validation.issues.messages.filter(m=>m.severity<2)});
}
const result={manifest_sha256:hash(manifestBytes),build_sha256:hash(buildBytes),verifier_sha256:hash(fs.readFileSync(new URL(import.meta.url))),rows,browser_render_verified:false,quality_approved:false};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(result,null,2),{flag:'wx'});
console.log({assets:rows.length,errors:rows.reduce((n,r)=>n+r.errors,0),warnings:rows.reduce((n,r)=>n+r.warnings,0),browser_render_verified:false});
if(rows.some(r=>r.errors))process.exitCode=1;
