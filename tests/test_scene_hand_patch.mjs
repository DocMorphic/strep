import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import * as THREE from '../assets/viewer/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../assets/viewer/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import {validateHandMesh,posedHandVertices,selectHandTriangle,changedHandFaces,createHandPatchPicker} from '../scripts/scene-hand-patch.js';

const binding={mesh_sha256:'test',vertex_count:3,face_count:1,joint_names:['LeftHand','LeftHandIndex'],inverse_bind_matrices:[new THREE.Matrix4().toArray(),new THREE.Matrix4().toArray()],faces:[{id:0,vertices:[0,1,2]}],
 vertices:[[-.2,-.2,0],[.2,-.2,0],[0,.2,0]].map((position,id)=>({id,position,joints:[0,0,0,0,1,0,0,0],weights:[.5,0,0,0,.5,0,0,0]}))};
const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(binding.vertices.flatMap(v=>v.position),3));geometry.setIndex([0,1,2]);
for(const [name,field,start] of [['skinIndex','joints',0],['joints_1','joints',4],['skinWeight','weights',0],['weights_1','weights',4]])geometry.setAttribute(name,new THREE.Float32BufferAttribute(binding.vertices.flatMap(v=>v[field].slice(start,start+4)),4));
const mesh=new THREE.SkinnedMesh(geometry,new THREE.MeshBasicMaterial()),bones=binding.joint_names.map(name=>{const b=new THREE.Bone();b.name=name;return b;});
mesh.add(...bones);mesh.bind(new THREE.Skeleton(bones));mesh.updateMatrixWorld(true);validateHandMesh(mesh,binding);
bones[1].position.x=.2;mesh.updateMatrixWorld(true);
let positions=posedHandVertices(THREE,mesh,binding);assert(Math.abs(positions.get(0).x+.1)<1e-7,'Second influence group must affect picking');
assert.equal(selectHandTriangle(THREE,binding,positions,new THREE.Ray(new THREE.Vector3(.1,0,1),new THREE.Vector3(0,0,-1))),0);
assert.equal(selectHandTriangle(THREE,binding,positions,new THREE.Ray(new THREE.Vector3(4,0,1),new THREE.Vector3(0,0,-1))),null);
assert.deepEqual(changedHandFaces(binding,[],0),[0]);assert.deepEqual(changedHandFaces(binding,[0],0,true),[]);
assert.throws(()=>changedHandFaces(binding,[],9));
const changed=structuredClone(binding);changed.faces[0].vertices=[2,1,0];assert.throws(()=>validateHandMesh(mesh,changed),/ordering/);
changed.faces=binding.faces;changed.vertices[0].weights[4]=.7;assert.throws(()=>validateHandMesh(mesh,changed),/influences/);
const changedBind=structuredClone(binding);changedBind.inverse_bind_matrices[0][12]=1;assert.throws(()=>validateHandMesh(mesh,changedBind),/inverse bind/);
const big={faces:Array.from({length:90},(_,i)=>({id:i,vertices:[i*3,i*3+1,i*3+2]}))};assert.throws(()=>changedHandFaces(big,Array.from({length:85},(_,i)=>i),85),/256/);

const events={},canvas={style:{},addEventListener:(n,f)=>events[n]=f,removeEventListener:n=>delete events[n],focus(){},getBoundingClientRect:()=>({left:0,top:0,width:400,height:400})};
const world=new THREE.Scene();world.add(mesh);world.updateMatrixWorld(true);const camera=new THREE.PerspectiveCamera(42,1,.01,100);camera.position.set(.1,0,1);camera.lookAt(.1,0,0);camera.updateMatrixWorld(true);
const ctx={changed:false,visible:true},controls={enabled:true};let chosen=null,picking=false,status='';
const contact={id:'left',actor:'A',hand:'LeftHand',hand_mesh:binding,patch_face_ids:[0],edit:{patch_radius_m:.045,patch_normal_degrees:60}},edit={patch_mode:'saved',patch_radius_m:.045,patch_normal_degrees:60};
const picker=createHandPatchPicker({THREE,world,camera,canvas,getContext:()=>ctx,getControls:()=>controls,getActor:name=>name==='A'?mesh:null,pause(){},onFaces:(faces,hash)=>{chosen={faces,hash};picker.setDraft(contact,{...edit,patch_mode:'custom',patch_face_ids:faces},true);},onPicking:v=>picking=v,onStatus:s=>status=s});
picker.setDraft(contact,edit,true);picker.frameHand();
assert(new THREE.Vector3(.1,0,0).project(camera).toArray().every(Number.isFinite));
assert(Math.abs(new THREE.Vector3(.1,0,0).project(camera).x)<1e-6);
picker.toggle(true);assert(picking);assert.equal(controls.enabled,false);
events.pointerdown({button:0,clientX:200,clientY:200,preventDefault(){},stopImmediatePropagation(){}});assert.deepEqual(chosen,{faces:[],hash:'test'});assert(picking,'Selection continues across draft updates');
events.keydown({key:'Escape',preventDefault(){},stopPropagation(){}});assert(!picking&&controls.enabled);
picker.toggle();ctx.visible=false;picker.update();assert(!picking&&controls.enabled);ctx.visible=true;controls.enabled=false;picker.toggle();picker.cancel();assert.equal(controls.enabled,false);
ctx.changed=true;picker.toggle();assert(!picking);ctx.changed=false;
picker.setDraft({...contact,actor:'missing'},edit,true);picker.toggle();assert(!picking);assert.match(status,/matching hand mesh/);
picker.setDraft(null);assert(!picking);picker.dispose();assert.equal(world.children.length,1);assert.deepEqual(events,{});

// Optional provisioned real-rig check against independent Python GLB skinning.
if(process.argv[2]){
 const fixture=JSON.parse(await readFile(process.argv[2],'utf8')),bytes=await readFile(fixture.path);
 const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
 const group=new THREE.Group();group.position.fromArray(fixture.actor_translation);group.quaternion.fromArray(fixture.actor_rotation);group.add(gltf.scene);
 let real;gltf.scene.traverse(o=>{if(o.isSkinnedMesh)real=o;});
 // GLTFLoader normalizes four influences; match the application's restoration.
 const first=real.geometry.getAttribute('skinWeight'),extra=real.geometry.getAttribute('weights_1');
 for(let i=0;i<first.count;i++){const remain=1-extra.getX(i)-extra.getY(i)-extra.getZ(i)-extra.getW(i);first.setXYZW(i,first.getX(i)*remain,first.getY(i)*remain,first.getZ(i)*remain,first.getW(i)*remain);}
 const mixer=new THREE.AnimationMixer(gltf.scene),action=mixer.clipAction(gltf.animations[0]);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
 let maximum=0,samples=0,hits=0;
 for(const c of fixture.contacts)validateHandMesh(real,c.hand_mesh);
 for(const sample of fixture.samples){
  action.paused=false;mixer.setTime(sample.frame/30);group.updateMatrixWorld(true);
  for(const c of fixture.contacts){
   const points=posedHandVertices(THREE,real,c.hand_mesh);
   for(const [id,p] of points){maximum=Math.max(maximum,p.distanceTo(new THREE.Vector3().fromArray(sample.hands[c.hand][id])));samples++;}
   for(const f of c.hand_mesh.faces.filter((_,i)=>i%137===0)){
    const [a,b,d]=f.vertices.map(v=>points.get(v)),normal=b.clone().sub(a).cross(d.clone().sub(a)).normalize(),center=a.clone().add(b).add(d).multiplyScalar(1/3);
    const ray=new THREE.Ray(center.clone().addScaledVector(normal,.001),normal.clone().negate());
    assert.equal(selectHandTriangle(THREE,{faces:[f]},points,ray),f.id);hits++;
   }
  }
 }
 assert(maximum<2e-6,`Skinned selection error ${maximum}`);
 const result={posed_vertex_samples:samples,triangle_hits:hits,maximum_position_error_m:maximum,browser_verified:false};
 if(process.argv[3])await writeFile(process.argv[3],JSON.stringify(result,null,2));console.log(result);
}
console.log('Hand selection: eight weights, topology guards, triangle edits, limits, sustained selection, cancellation and control restoration pass. Offline only.');
