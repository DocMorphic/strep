import {sourceGLB,bindSourceSkin} from './native-source-skin.mjs';
import {selectReviewMotion} from './review-native-selection.mjs';

// The developer packet keeps original bytes; rendering uses the same complete
// influence and source inverse-bind convention as the measured native mesh.
export async function prepareNativeReview(THREE,gltf,bytes,selected){
 const source=sourceGLB(bytes.slice(0)),selection=selectReviewMotion(selected,gltf),model=new THREE.Group();
 model.add(gltf.scene);model.updateMatrixWorld(true);
 const previous=[];gltf.scene.traverse(n=>{if(n.isMesh)previous.push([n,n.geometry,n.material]);});
 const skin=await bindSourceSkin(THREE,gltf,source,model);
 const usedGeometry=new Set(),usedMaterial=new Set();model.traverse(n=>{if(n.geometry)usedGeometry.add(n.geometry);for(const m of n.material?(Array.isArray(n.material)?n.material:[n.material]):[])usedMaterial.add(m);});
 const released=new Set();
 for(const [,geometry,material] of previous){
  if(!usedGeometry.has(geometry)&&!released.has(geometry)){geometry.dispose();released.add(geometry);}
  for(const m of Array.isArray(material)?material:[material])if(!usedMaterial.has(m)&&!released.has(m)){m.dispose();released.add(m);}
 }
 return {model,skin,...selection};
}

// Framing only: include complete posed mesh vertices, not just joint locations.
export function extendNativeReviewBounds(THREE,model,skin,root,local,world){
 skin.update();const origin=root.getWorldPosition(new THREE.Vector3());
 const add=p=>{world.expandByPoint(p);p.x-=origin.x;p.z-=origin.z;local.expandByPoint(p);};
 for(const record of skin.meshes)for(let i=0;i<record.positions.count;i++)add(record.point(i));
 model.traverse(n=>{if(n.isMesh&&!n.isSkinnedMesh){const positions=n.geometry.getAttribute('position');for(let i=0;i<positions.count;i++)add(n.getVertexPosition(i,new THREE.Vector3()).applyMatrix4(n.matrixWorld));}});
}
