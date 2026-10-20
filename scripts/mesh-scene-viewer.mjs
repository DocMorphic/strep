import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {useGreyMaterials} from './native-grey-loader.mjs';
import {createScenePlayback} from './mesh-scene-playback.mjs';

const el=id=>document.getElementById(id);let playing=false,preview=null,last=0,disposed=false;
const pause=()=>{playing=false;el('play').textContent='Play';};
const fail=error=>{pause();el('status').textContent=error.message;el('status').className='error';for(const id of ['play','time','contact','worst','frame'])el(id).disabled=true;};
try{
 const params=new URLSearchParams(location.search),job=params.get('job'),digest=params.get('result');
 if(!/^[a-f0-9]{32}$/.test(job)||!/^[a-f0-9]{64}$/.test(digest))throw Error('Open a completed saved scene from Studio.');
 const response=await fetch(`/api/mesh-scene-jobs/${job}/preview/${digest}`,{cache:'no-store'}),data=await response.json();if(!response.ok)throw Error(data.error||'Saved scene is unavailable.');
 if(data.job!==job||data.result_sha256!==digest)throw Error('Saved scene identity changed.');
 const loader=new GLTFLoader();useGreyMaterials(loader,THREE);
 preview=await createScenePlayback({THREE,loader,data,readAsset:async entry=>{
  if(!new RegExp(`^/files/mesh-scene-previews/${job}/${digest}/(?:actors|props)/[A-Za-z0-9_-]{1,64}\\.glb$`).test(entry.url))throw Error('Unexpected scene asset URL.');
  const result=await fetch(entry.url,{cache:'no-store'});if(!result.ok)throw Error('Saved scene asset is unavailable.');const bytes=await result.arrayBuffer();
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');if(hash!==entry.sha256)throw Error('Saved scene asset changed.');return bytes;
 }});
 const renderer=new THREE.WebGLRenderer({canvas:el('view'),antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor(0xe8edf2);renderer.outputColorSpace=THREE.SRGBColorSpace;
 const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(40,1,.01,1000),controls=new OrbitControls(camera,el('view'));controls.enableDamping=true;
 scene.add(preview.root,new THREE.HemisphereLight(0xffffff,0x596675,2));const light=new THREE.DirectionalLight(0xffffff,2);light.position.set(3,7,4);scene.add(light);
 const bounds=preview.bounds(),grid=new THREE.GridHelper(Math.max(4,bounds.radius*6),20,0x9baab7,0xc6d0d8);scene.add(grid);
 const markerSize=Math.max(.008,Math.min(.025,bounds.radius*.012)),markers=[0x1674df,0xe6a13c].map(color=>new THREE.Mesh(new THREE.SphereGeometry(markerSize,16,12),new THREE.MeshBasicMaterial({color,depthTest:false})));markers.forEach(m=>{m.renderOrder=10;scene.add(m);});
 const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(),new THREE.Vector3()]),new THREE.LineBasicMaterial({color:0xbc4b45,depthTest:false}));line.renderOrder=9;scene.add(line);
 function frame(){controls.target.copy(bounds.center);camera.position.copy(bounds.center).add(new THREE.Vector3(1,.55,1.5).normalize().multiplyScalar(bounds.radius/Math.sin(THREE.MathUtils.degToRad(camera.fov/2))*1.15/Math.min(1,camera.aspect)));camera.near=Math.max(.001,bounds.radius/1000);camera.far=Math.max(100,bounds.radius*100);camera.updateProjectionMatrix();controls.update();}
 function update(){
  el('time').value=preview.time;el('clock').textContent=`${preview.time.toFixed(3)} / ${data.duration_s.toFixed(3)} s`;
  const index=Number(el('contact').value),c=data.mesh_contacts[index],live=preview.contact(index);
  markers[0].position.fromArray(live.effector);markers[1].position.fromArray(live.target);
  const position=line.geometry.attributes.position;position.setXYZ(0,...live.effector);position.setXYZ(1,...live.target);position.needsUpdate=true;line.geometry.computeBoundingSphere();
  line.material.color.setHex(live.active?(live.gap_m<=c.limits.position_m?0x27885b:0xbc4b45):0x73818e);
  el('measure').textContent=`${c.id}: ${(live.gap_m*1000).toFixed(3)} mm live gap. ${live.active?'Inside':'Outside'} the declared ${c.mode} time (${c.interval_s.join('–')} s). Position limit: ${(c.limits.position_m*1000).toFixed(3)} mm. Live gap alone does not determine the saved result.`;
  el('measure').dataset.observation=JSON.stringify(live);
 }
 for(const [i,c] of data.mesh_contacts.entries()){const option=document.createElement('option');option.value=i;option.textContent=`${c.id} · ${c.actor} → ${c.prop}`;el('contact').append(option);}
 if(!data.mesh_contacts.length)throw Error('No imported-object contacts in this saved scene.');
 el('contact').value='0';el('time').max=data.duration_s;
 el('time').oninput=()=>{pause();preview.seek(Number(el('time').value));update();};
 el('contact').onchange=update;
 el('worst').onclick=()=>{pause();const c=data.mesh_contacts[Number(el('contact').value)],row=data.contacts.find(r=>r.id===c.id);preview.seek(row.peak_time_s);update();};
 el('play').onclick=()=>{if(preview.time>=data.duration_s)preview.seek(0);playing=!playing;last=performance.now();el('play').textContent=playing?'Pause':'Play';update();};el('frame').onclick=frame;
 for(const id of ['play','time','contact','worst','frame'])el(id).disabled=false;
 el('status').textContent=`Saved point-contact checks: ${data.all_declared_point_contacts_pass?'pass':'fail'}. ${data.other_contact_count} other contact conditions are included in the saved report. No quality or release approval.`;
 el('binding').textContent=`Job ${job} · Result ${digest}`;
 let sized=false;
 function draw(now){if(disposed)return;try{if(playing){preview.seek(preview.time+Math.max(0,Math.min(.1,(now-last)/1000)));if(preview.time===data.duration_s)pause();update();}last=now;
  const w=el('view').clientWidth,h=el('view').clientHeight;if(w&&h){if(el('view').width!==Math.floor(w*renderer.getPixelRatio())||el('view').height!==Math.floor(h*renderer.getPixelRatio())){renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();if(!sized){frame();sized=true;}}controls.update();renderer.render(scene,camera);}requestAnimationFrame(draw);
 }catch(error){fail(error);}}
 update();requestAnimationFrame(draw);
 document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
 addEventListener('pagehide',()=>{disposed=true;pause();preview.dispose();controls.dispose();scene.traverse(n=>{n.geometry?.dispose();n.material?.dispose();});renderer.dispose();},{once:true});
}catch(error){preview?.dispose();fail(error);}
