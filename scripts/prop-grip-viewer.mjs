import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {createPropGripEditor} from './prop-grip-editor.mjs';

// The server supplies the complete canonical triangle order used by saved grips.
// GPU positions are Float32; each picked barycentric point is re-evaluated by
// the server on its Float64 source geometry before it can be saved.
export function createPropGripViewer(canvas){
 let renderer,scene,camera,orbit,mesh,marker,picking=null,down=null,extent=1;
 function render(){if(!renderer||!canvas.clientWidth||!canvas.clientHeight)return;renderer.setSize(canvas.clientWidth,canvas.clientHeight,false);camera.aspect=canvas.clientWidth/canvas.clientHeight;camera.updateProjectionMatrix();renderer.render(scene,camera);}
 function init(){if(renderer)return;renderer=new THREE.WebGLRenderer({canvas,antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));scene=new THREE.Scene();scene.background=new THREE.Color(0x222936);camera=new THREE.PerspectiveCamera(40,1,.001,1000);orbit=new OrbitControls(camera,canvas);orbit.addEventListener('change',render);
  scene.add(new THREE.HemisphereLight(0xffffff,0x778899,2));const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(3,5,4);scene.add(light);
  marker=new THREE.Mesh(new THREE.SphereGeometry(1,12,8),new THREE.MeshBasicMaterial({color:0x6cd8ff,depthTest:false}));marker.renderOrder=10;marker.visible=false;scene.add(marker);
  new ResizeObserver(render).observe(canvas);
 }
 function cancel(){picking=null;canvas.style.cursor='';if(orbit)orbit.enabled=true;}
 function clear(){cancel();if(mesh){scene.remove(mesh);mesh.geometry.dispose();mesh.material.dispose();mesh=null;}if(marker)marker.visible=false;render();}
 function home(){if(!mesh)return;const box=new THREE.Box3().setFromObject(mesh),center=box.getCenter(new THREE.Vector3());extent=Math.max(box.getSize(new THREE.Vector3()).length(),1e-6);orbit.target.copy(center);camera.near=Math.max(extent/10000,1e-9);camera.far=extent*100;camera.position.copy(center).add(new THREE.Vector3(.8,.5,1).normalize().multiplyScalar(extent*1.7));orbit.minDistance=extent*.01;orbit.maxDistance=extent*30;orbit.update();render();}
 canvas.addEventListener('pointerdown',e=>{down={x:e.clientX,y:e.clientY,button:e.button};});
 canvas.addEventListener('pointerup',e=>{
  if(!picking||!mesh||!down||down.button!==0||Math.hypot(e.clientX-down.x,e.clientY-down.y)>4)return;
  const rect=canvas.getBoundingClientRect();if(!rect.width||!rect.height)return;
  const ray=new THREE.Raycaster();ray.setFromCamera(new THREE.Vector2((e.clientX-rect.left)/rect.width*2-1,1-(e.clientY-rect.top)/rect.height*2),camera);
  const hit=ray.intersectObject(mesh,false)[0];if(!hit)return;
  const p=mesh.geometry.attributes.position,face=hit.face;
  const triangle=new THREE.Triangle(...[face.a,face.b,face.c].map(i=>new THREE.Vector3().fromBufferAttribute(p,i)));
  const weights=triangle.getBarycoord(hit.point,new THREE.Vector3());if(!weights)return;
  const bary=weights.toArray();if(bary.some(x=>!Number.isFinite(x)||x<0||x>1))return;
  const callback=picking;cancel();callback(hit.faceIndex,bary);
 });
 canvas.tabIndex=0;canvas.addEventListener('keydown',e=>{if(e.key==='Escape')cancel();});
 return {clear,cancel,home,show(data){init();clear();const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(data.vertices_m.flat(),3));geometry.setIndex(data.faces.flat());geometry.computeVertexNormals();mesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:0xa9afb8,roughness:.8,side:THREE.DoubleSide}));scene.add(mesh);home();},
  mark(point){if(!marker)return;marker.visible=!!point;if(point){marker.position.fromArray(point);marker.scale.setScalar(extent*.008);}render();},
  pick(callback){picking=callback;orbit.enabled=false;canvas.style.cursor='crosshair';canvas.focus({preventScroll:true});}};
}
export async function mountPropGripEditor(){
 const request=async(url,options)=>{const response=await fetch(url,options);const data=await response.json();if(!response.ok)throw Error(data.error||'Object request failed.');return data;};
 return createPropGripEditor({request,viewer:createPropGripViewer(document.getElementById('propGripCanvas'))});
}
