import assert from 'node:assert/strict';
import * as THREE from '../assets/viewer/node_modules/three/build/three.module.js';
import {scenePrimitive,scenePrimitiveMesh} from '../scripts/scene-object-geometry.js';
for(const [radius,height] of [[.02,.15],[.3,1.2],[2.3,.04]]){
 const obj={geometry:{schema:'strep-object-geometry-v1',shape:'cylinder',radius_m:radius,height_m:height}};
 const primitive=scenePrimitive(obj);assert.deepEqual(primitive,{shape:'cylinder',scale:[2*radius,height,2*radius]});
 const mesh=scenePrimitiveMesh(THREE,obj).toNonIndexed();
 mesh.scale(...primitive.scale);
 const position=mesh.attributes.position,normal=mesh.attributes.normal;
 const a=new THREE.Vector3(),b=new THREE.Vector3(),c=new THREE.Vector3(),center=new THREE.Vector3();
 let worstInset=0;
 for(let i=0;i<position.count;i+=3){
  a.fromBufferAttribute(position,i);b.fromBufferAttribute(position,i+1);c.fromBufferAttribute(position,i+2);
  const cross=b.clone().sub(a).cross(c.clone().sub(a));center.copy(a).add(b).add(c).multiplyScalar(1/3);
  assert(cross.dot(center)>0,'Outward winding required');
  for(const p of [a,b,c,a.clone().add(b).multiplyScalar(.5),center]){
   const q=[Math.hypot(p.x,p.z)-radius,Math.abs(p.y)-height/2];
   const d=Math.hypot(...q.map(x=>Math.max(0,x)))+Math.min(Math.max(...q),0);
   assert(d<=1e-6);worstInset=Math.max(worstInset,-d);
  }
  for(let j=0;j<3;j++)assert(Math.abs(new THREE.Vector3().fromBufferAttribute(normal,i+j).length()-1)<1e-6);
 }
 assert(worstInset<=.001+1e-6);mesh.dispose();
}
for(const geometry of [
 {schema:'strep-object-geometry-v1',shape:'cylinder',radius_m:true,height_m:1},
 {schema:'strep-object-geometry-v1',shape:'cylinder',radius_m:.3},
 {schema:'strep-object-geometry-v1',shape:'cylinder',radius_m:.3,height_m:NaN},
 {schema:'strep-object-geometry-v1',shape:'cylinder',radius_m:.3,height_m:1,size_m:[1,1,1]}
])assert.throws(()=>scenePrimitive({geometry}));
assert.throws(()=>scenePrimitive({shape:'box',size_m:[1,1,1],height_m:1}));
assert.throws(()=>scenePrimitiveMesh(THREE,{geometry:{schema:'strep-object-geometry-v1',shape:'cylinder',radius_m:1000,height_m:1}}),/resource/);
console.log('Cylinder Three.js mesh dimensions, side/cap normals, winding, inset bounds and invalid schema rejection pass. No browser/network used.');
