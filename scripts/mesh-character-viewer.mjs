import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {useGreyMaterials} from './native-grey-loader.mjs';
import {createScenePlayback} from './mesh-scene-playback.mjs';
const el=id=>document.getElementById(id),players={};let playing=false,last=0,disposed=false,time=0;
const pause=()=>{playing=false;el('play').textContent='Play';};
const fail=error=>{pause();el('status').textContent=error.message;el('status').className='error';for(const id of ['play','time','variant','contact','worst','frame'])el(id).disabled=true;};
try{
 const params=new URLSearchParams(location.search),job=params.get('job'),digest=params.get('result');
 if(!/^[a-f0-9]{32}$/.test(job)||!/^[a-f0-9]{64}$/.test(digest))throw Error('Open a completed correction from Studio.');
 const response=await fetch(`/api/mesh-character-jobs/${job}/preview/${digest}`,{cache:'no-store'}),data=await response.json();
 if(!response.ok)throw Error(data.error||'Comparison unavailable.');
 if(data.schema!=='strep-mesh-character-comparison-v1'||data.job!==job||data.result_sha256!==digest||data.original_selected!==true||data.quality_approved!==false||data.release_approved!==false)throw Error('Saved comparison identity or scope changed.');
 const duration=data.original.duration_s,loader=new GLTFLoader();useGreyMaterials(loader,THREE);let total=0;
 for(const role of ['original','candidate']){
  const source=data[role];if(!source)continue;
  if(source.role!==role||source.duration_s!==duration)throw Error('Comparison role or duration changed.');
  players[role]=await createScenePlayback({THREE,loader,data:source,readAsset:async entry=>{
   if(!new RegExp(`^/files/mesh-character-previews/${job}/${digest}/${role}/(?:actors|props)/[A-Za-z0-9_-]{1,64}\\.glb$`).test(entry.url))throw Error('Unexpected comparison asset.');
   const r=await fetch(entry.url,{cache:'no-store'});if(!r.ok)throw Error('Saved comparison asset unavailable.');const bytes=await r.arrayBuffer();total+=bytes.byteLength;if(total>128*1024**2)throw Error('Combined comparison limit is 128 MiB.');
   const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');if(hash!==entry.sha256)throw Error('Saved comparison asset changed.');return bytes;
  }});
 }
 if(data.candidate&&JSON.stringify(data.original.mesh_contacts)!==JSON.stringify(data.candidate.mesh_contacts))throw Error('Original contact intent changed.');
 const renderer=new THREE.WebGLRenderer({canvas:el('view'),antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor(0xe8edf2);renderer.outputColorSpace=THREE.SRGBColorSpace;
 const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(40,1,.01,1000),controls=new OrbitControls(camera,el('view'));controls.enableDamping=true;
 scene.add(new THREE.HemisphereLight(0xffffff,0x596675,2));const light=new THREE.DirectionalLight(0xffffff,2);light.position.set(3,7,4);scene.add(light);
 const bounds=new THREE.Sphere();let first=true;
 for(const p of Object.values(players)){scene.add(p.root);const b=p.bounds();if(first){bounds.copy(b);first=false;}else bounds.union(b);}
 scene.add(new THREE.GridHelper(Math.max(4,bounds.radius*6),20,0x9baab7,0xc6d0d8));
 const markerSize=Math.max(.008,Math.min(.025,bounds.radius*.012)),markers=[0x1674df,0xe6a13c].map(color=>new THREE.Mesh(new THREE.SphereGeometry(markerSize,16,12),new THREE.MeshBasicMaterial({color,depthTest:false})));
 for(const m of markers){m.renderOrder=10;scene.add(m);}
 function frame(){controls.target.copy(bounds.center);camera.position.copy(bounds.center).add(new THREE.Vector3(1,.55,1.5).normalize().multiplyScalar(bounds.radius/Math.sin(THREE.MathUtils.degToRad(camera.fov/2))*1.15/Math.min(1,camera.aspect)));camera.near=Math.max(.001,bounds.radius/1000);camera.far=Math.max(100,bounds.radius*100);camera.updateProjectionMatrix();controls.update();}
 function update(){
  const role=el('variant').value,index=Number(el('contact').value),live={};
  for(const [name,p] of Object.entries(players)){p.root.visible=name===role;p.seek(time);live[name]=p.contact(index);}
  markers[0].position.fromArray(live[role].effector);markers[1].position.fromArray(live[role].target);
  el('time').value=time;el('clock').textContent=`${time.toFixed(3)} / ${duration.toFixed(3)} s`;
  el('measure').textContent=`Showing ${role}. `+Object.entries(live).map(([name,c])=>`${name}: ${(c.gap_m*1000).toFixed(3)} mm${c.active?' at contact time':' outside contact time'}`).join(' · ');
  el('measure').dataset.observation=JSON.stringify({time_s:time,role,...live});
  const source=data[role];el('status').textContent=`${role==='original'?'Original':'Candidate'} contacts: ${source.all_declared_point_contacts_pass?'pass':'fail'}; sampled geometry: ${source.sampled_geometry_pass?'pass':'fail'}. ${data.candidate?(data.sampled_candidate_pass?'Candidate passes all declared sampled checks.':'Candidate remains incomplete.'):'No improved candidate was accepted.'} Original remains selected. No engine, quality or release approval.`;
 }
 if(!data.original.mesh_contacts.length)throw Error('No saved object contacts.');
 data.original.mesh_contacts.forEach((c,i)=>{const option=document.createElement('option');option.value=i;option.textContent=c.id;el('contact').append(option);});
 el('variant').value='original';el('variant').querySelector('[value=candidate]').disabled=!players.candidate;el('contact').value='0';el('time').max=duration;
 el('time').oninput=()=>{pause();time=Math.max(0,Math.min(duration,Number(el('time').value)));update();};el('variant').onchange=update;el('contact').onchange=update;
 el('worst').onclick=()=>{pause();const source=data[el('variant').value],row=source.contacts.find(r=>r.id===source.mesh_contacts[Number(el('contact').value)].id);time=row.peak_time_s;update();};
 el('play').onclick=()=>{if(time>=duration)time=0;playing=!playing;last=performance.now();el('play').textContent=playing?'Pause':'Play';update();};el('frame').onclick=frame;
 for(const id of ['play','time','variant','contact','worst','frame'])el(id).disabled=false;
 el('binding').textContent=`Correction ${job} · Result ${digest}`;let sized=false;
 function draw(now){if(disposed)return;try{if(playing){time=Math.min(duration,time+Math.max(0,Math.min(.1,(now-last)/1000)));if(time===duration)pause();update();}last=now;
  const w=el('view').clientWidth,h=el('view').clientHeight;if(w&&h){if(el('view').width!==Math.floor(w*renderer.getPixelRatio())||el('view').height!==Math.floor(h*renderer.getPixelRatio())){renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();if(!sized){frame();sized=true;}}controls.update();renderer.render(scene,camera);}requestAnimationFrame(draw);
 }catch(error){fail(error);}}
 update();requestAnimationFrame(draw);document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
 addEventListener('pagehide',()=>{disposed=true;pause();Object.values(players).forEach(p=>p.dispose());controls.dispose();scene.traverse(n=>{n.geometry?.dispose();n.material?.dispose();});renderer.dispose();},{once:true});
}catch(error){Object.values(players).forEach(p=>p.dispose());fail(error);}
