import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {enableEightWeights} from '/soma-preview-skin.js';
import {useGreyMaterials} from '/native-grey-loader.mjs';
import {validateNativePreview,selectNativePreviewClip} from '/native-preview-policy.mjs';

export function createNativeReferencePlayer({canvas,onTime}){
 const scene=new THREE.Scene(),loader=new GLTFLoader();useGreyMaterials(loader,THREE);
 const renderer=new THREE.WebGLRenderer({canvas,antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor(0xe3e8ed);
 const camera=new THREE.PerspectiveCamera(40,1,.01,100),controls=new OrbitControls(camera,canvas);controls.enableDamping=true;controls.minDistance=.07;
 scene.add(new THREE.HemisphereLight(0xffffff,0x697589,2.5));const sun=new THREE.DirectionalLight(0xffffff,2.8);sun.position.set(3,5,4);scene.add(sun,new THREE.GridHelper(12,24,0xa4adb8,0xcbd2da));
 let actor=null,bounds=null,time=0,start=0,end=1,playing=false,last=performance.now(),serial=0;
 function pause(){playing=false;}
 function dispose(item){if(!item)return;item.mixer.stopAllAction();item.mixer.uncacheRoot(item.model);scene.remove(item.model);item.model.traverse(n=>{n.geometry?.dispose();for(const m of n.material?(Array.isArray(n.material)?n.material:[n.material]):[]){for(const v of Object.values(m))if(v?.isTexture)v.dispose();m.dispose();}});}
 function seek(value){time=Math.max(start,Math.min(end,value));if(actor){actor.action.enabled=true;actor.action.paused=false;actor.mixer.setTime(time);actor.model.updateMatrixWorld(true);}onTime(time);}
 function fit(){if(!bounds)return;const a=THREE.MathUtils.degToRad(camera.fov)/2,b=Math.atan(Math.tan(a)*camera.aspect),distance=Math.max(.1,bounds.radius)/Math.sin(Math.min(a,b))*1.1;controls.target.copy(bounds.center);camera.position.copy(bounds.center).addScaledVector(new THREE.Vector3(.85,.35,1).normalize(),distance);controls.update();}
 async function load(data){pause();const token=++serial;dispose(actor);actor=null;bounds=null;validateNativePreview(data);const response=await fetch(data.preview_url,{cache:'no-store'});if(!response.ok)throw Error('Native preview unavailable');const bytes=await response.arrayBuffer(),digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');if(digest!==data.preview_sha256)throw Error('Native preview changed');const gltf=await loader.parseAsync(bytes,new URL(data.preview_url,location.href).href);let clip;try{clip=selectNativePreviewClip(data,gltf.animations);}catch(error){dispose({model:gltf.scene,mixer:new THREE.AnimationMixer(gltf.scene)});throw error;}gltf.scene.traverse(n=>{if(n.isMesh){n.frustumCulled=false;if(n.isSkinnedMesh)enableEightWeights(n);}});const mixer=new THREE.AnimationMixer(gltf.scene),action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();const next={model:gltf.scene,mixer,action};if(token!==serial){dispose(next);return;}actor=next;scene.add(actor.model);start=data.preview_start_s;end=data.preview_end_s;const box=new THREE.Box3(),point=new THREE.Vector3();for(let i=0;i<=32;i++){seek(start+(end-start)*i/32);actor.model.traverse(n=>{if(n.isBone)box.expandByPoint(n.getWorldPosition(point));});}if(box.isEmpty())box.setFromObject(actor.model);bounds=box.getBoundingSphere(new THREE.Sphere());bounds.radius+=.18;seek(start);fit();}
 function tick(t){if(playing&&actor){seek(time+Math.max(0,Math.min(.1,(t-last)/1000)));if(time===end)pause();}last=t;const w=canvas.clientWidth,h=canvas.clientHeight;if(w>0&&h>0){if(canvas.width!==Math.floor(w*renderer.getPixelRatio())||canvas.height!==Math.floor(h*renderer.getPixelRatio())){renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();fit();}controls.update();renderer.render(scene,camera);}requestAnimationFrame(tick);}requestAnimationFrame(tick);
 document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
 return {load,pause,seek,fit,toggle(){if(time===end)seek(start);playing=!playing;last=performance.now();}};
}
