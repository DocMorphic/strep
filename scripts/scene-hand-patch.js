// Triangle IDs are meaningful only on the canonical mesh supplied by the backend.
const component=(attribute,index,column)=>attribute[['getX','getY','getZ','getW'][column]](index);

export function validateHandMesh(mesh,binding){
 const g=mesh.geometry,position=g?.getAttribute('position'),index=g?.index;
 if(!mesh.isSkinnedMesh||position?.count!==binding.vertex_count||index?.count!==binding.face_count*3)throw Error('Preview mesh does not match the hand-selection mesh.');
 if(mesh.skeleton.bones.length!==binding.joint_names.length||mesh.skeleton.bones.some((b,i)=>b.name!==binding.joint_names[i]))throw Error('Preview skeleton differs from the authored hand mesh.');
 if(!binding.inverse_bind_matrices||mesh.skeleton.boneInverses.some((matrix,j)=>matrix.elements.some((v,i)=>!Number.isFinite(v)||Math.abs(v-binding.inverse_bind_matrices[j][i])>1e-6)))throw Error('Preview inverse bind matrices changed.');
 for(const f of binding.faces)for(let i=0;i<3;i++)if(index.getX(f.id*3+i)!==f.vertices[i])throw Error('Preview triangle ordering changed.');
 for(const v of binding.vertices){
  for(let i=0;i<3;i++)if(!Number.isFinite(component(position,v.id,i))||Math.abs(component(position,v.id,i)-v.position[i])>1e-7)throw Error('Preview bind positions changed.');
  for(let i=0;i<8;i++){
   const joints=g.getAttribute(i<4?'skinIndex':'joints_1'),weights=g.getAttribute(i<4?'skinWeight':'weights_1');
   if(!joints||!weights||!Number.isFinite(component(weights,v.id,i%4))||component(joints,v.id,i%4)!==v.joints[i]||Math.abs(component(weights,v.id,i%4)-v.weights[i])>1e-6)throw Error('Preview skin influences changed.');
  }
 }
 return mesh;
}

export function posedHandVertices(THREE,mesh,binding){
 // Match the displayed eight-influence skin, including actor placement.
 mesh.updateWorldMatrix(true,false);
 const result=new Map(),matrix=new THREE.Matrix4(),point=new THREE.Vector3(),weighted=new THREE.Vector3();
 for(const v of binding.vertices){
  const bind=new THREE.Vector3().fromArray(v.position).applyMatrix4(mesh.bindMatrix);point.set(0,0,0);
  for(let i=0;i<8;i++)if(v.weights[i]){
   const joint=v.joints[i];matrix.multiplyMatrices(mesh.skeleton.bones[joint].matrixWorld,mesh.skeleton.boneInverses[joint]);
   weighted.copy(bind).applyMatrix4(matrix);point.addScaledVector(weighted,v.weights[i]);
  }
  result.set(v.id,point.clone().applyMatrix4(mesh.bindMatrixInverse).applyMatrix4(mesh.matrixWorld));
 }
 return result;
}

export function selectHandTriangle(THREE,binding,points,ray){
 let closest=null;
 for(const face of binding.faces){
  const hit=ray.intersectTriangle(...face.vertices.map(v=>points.get(v)),true,new THREE.Vector3());
  if(hit){const distance=ray.origin.distanceToSquared(hit);if(!closest||distance<closest.distance)closest={id:face.id,distance};}
 }
 return closest?.id??null;
}

export function changedHandFaces(binding,current,face,remove=false){
 const allowed=new Map(binding.faces.map(f=>[f.id,f.vertices]));
 if(!allowed.has(face))throw Error('Pick a triangle on the selected hand.');
 const next=new Set(current);if(remove)next.delete(face);else next.add(face);
 if([...next].some(f=>!allowed.has(f)))throw Error('Saved selection contains a triangle outside this hand.');
 const ids=[...next].sort((a,b)=>a-b);
 if(ids.length>512||new Set(ids.flatMap(f=>allowed.get(f))).size>256)throw Error('A hand region can contain at most 256 vertices.');
 return ids;
}

export function createHandPatchPicker({THREE,world,camera,canvas,getContext,getControls,getActor,pause,onFaces,onStatus,onPicking}){
 let draft=null,mesh=null,picking=false,remove=false,priorControls=true;
 const overlay=new THREE.Mesh(new THREE.BufferGeometry(),new THREE.MeshBasicMaterial({vertexColors:true,transparent:true,opacity:.48,side:THREE.DoubleSide,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-2}));
 overlay.frustumCulled=false;overlay.visible=false;overlay.renderOrder=33;world.add(overlay);
 function cancel(){if(picking){const c=getControls();if(c)c.enabled=priorControls;}picking=false;canvas.style.cursor='';onPicking(false);}
 function resolve(){
  if(mesh)return mesh;
  const actor=getActor(draft.contact.actor),found=[];actor?.traverse(o=>{if(o.isSkinnedMesh)found.push(o);});
  const matches=[];for(const candidate of found){try{validateHandMesh(candidate,draft.contact.hand_mesh);matches.push(candidate);}catch{}}
  if(matches.length!==1)throw Error('A unique matching hand mesh is required. Reload the saved scene.');
  mesh=matches[0];return mesh;
 }
 function update(){
  overlay.visible=false;const ctx=getContext();
  if(!draft||!draft.include||ctx.changed||!ctx.visible){cancel();return;}
  try{
   const binding=draft.contact.hand_mesh,points=posedHandVertices(THREE,resolve(),binding),selected=new Set(draft.faces);
   const faces=picking?binding.faces:binding.faces.filter(f=>selected.has(f.id));
   const positions=[],colors=[];
   for(const face of faces)for(const v of face.vertices){positions.push(...points.get(v).toArray());colors.push(...(selected.has(face.id)?[.1,.85,.95]:[.9,.55,.1]));}
   if(overlay.geometry.getAttribute('position')?.array.length!==positions.length){
    overlay.geometry.dispose();overlay.geometry=new THREE.BufferGeometry();
    overlay.geometry.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));overlay.geometry.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));
   }else{
    for(const [name,values] of [['position',positions],['color',colors]]){const attribute=overlay.geometry.getAttribute(name);attribute.array.set(values);attribute.needsUpdate=true;}
   }
   overlay.visible=faces.length>0;
  }catch(error){cancel();onStatus(error.message);}
 }
 function toggle(erase=false){
  if(picking){const same=remove===erase;cancel();if(same){update();return;}}
  const ctx=getContext();if(!draft?.include||ctx.changed||!ctx.visible){onStatus('Include a contact in a saved, visible scene before selecting its hand.');return;}
  try{resolve();}catch(error){onStatus(error.message);return;}
  pause();remove=erase;const c=getControls();priorControls=c?.enabled??true;if(c)c.enabled=false;
  picking=true;canvas.style.cursor='crosshair';canvas.tabIndex=0;canvas.scrollIntoView?.({block:'center',behavior:'smooth'});canvas.focus({preventScroll:true});onPicking(true);
  onStatus(`${erase?'Remove':'Add'} triangles by clicking the selected ${draft.contact.hand}. Cyan is selected; amber is available. Escape finishes. Orbit before entering selection mode.`);update();
 }
 function frameHand(){
  const ctx=getContext();if(!draft?.include||ctx.changed||!ctx.visible){onStatus('Select a contact in a saved, visible scene first.');return;}
  try{
   cancel();pause();const points=[...posedHandVertices(THREE,resolve(),draft.contact.hand_mesh).values()];
   const box=new THREE.Box3().setFromPoints(points),center=box.getCenter(new THREE.Vector3()),size=box.getSize(new THREE.Vector3());
   const angle=Math.min(THREE.MathUtils.degToRad(camera.fov)/2,Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov)/2)*camera.aspect));
   const distance=Math.max(.12,size.length()/2/Math.sin(angle)*1.2),direction=camera.position.clone().sub(center).normalize();
   if(direction.lengthSq()===0)direction.set(0,0,1);
   camera.position.copy(center).addScaledVector(direction,distance);camera.lookAt(center);getControls()?.target?.copy(center);getControls()?.update?.();camera.updateMatrixWorld(true);
  }catch(error){onStatus(error.message);}
 }
 function pointer(event){
  if(!picking||event.button!==0)return;event.preventDefault();event.stopImmediatePropagation();
  const ctx=getContext();if(ctx.changed||!ctx.visible){cancel();return;}
  try{
   const rect=canvas.getBoundingClientRect();if(!rect.width||!rect.height)return;
   const ray=new THREE.Raycaster();ray.setFromCamera(new THREE.Vector2((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1),camera);
   const binding=draft.contact.hand_mesh,id=selectHandTriangle(THREE,binding,posedHandVertices(THREE,resolve(),binding),ray.ray);
   if(id===null){onStatus('No triangle on the selected hand was hit. Escape to orbit the view.');return;}
   const faces=changedHandFaces(binding,draft.faces,id,remove||event.shiftKey);draft.faces=faces;onFaces(faces,binding.mesh_sha256);
   onStatus(`${faces.length} hand triangles selected. ${faces.length?'Fit creates a separate audited candidate.':'Add triangles before fitting.'} Escape finishes selection.`);update();
  }catch(error){onStatus(error.message);}
 }
 function key(event){if(picking&&event.key==='Escape'){event.preventDefault();event.stopPropagation();cancel();update();}}
 canvas.addEventListener('pointerdown',pointer,true);canvas.addEventListener('keydown',key);
 return {toggle,cancel,update,frameHand,setDraft(contact,edit,include){
   if(!contact?.hand_mesh){cancel();draft=null;mesh=null;overlay.visible=false;return;}
   if(draft?.contact.id!==contact.id||draft?.contact.actor!==contact.actor||draft?.contact.hand_mesh.mesh_sha256!==contact.hand_mesh.mesh_sha256){cancel();mesh=null;}
   // Suggested shape parameters are resolved server-side; do not pretend their
   // stale initial patch is a preview after those parameters change.
   const suggestedChanged=edit.patch_mode==='suggested'&&(edit.patch_radius_m!==contact.edit.patch_radius_m||edit.patch_normal_degrees!==contact.edit.patch_normal_degrees);
   draft={contact,include,faces:[...(edit.patch_mode==='custom'?edit.patch_face_ids:contact.patch_face_ids)]};
   if(suggestedChanged){cancel();draft=null;overlay.visible=false;onStatus('Suggested patch shape changed. Reload its original shape before visual selection, or fit the new suggestion.');return;}
   update();
  },dispose(){cancel();canvas.removeEventListener('pointerdown',pointer,true);canvas.removeEventListener('keydown',key);world.remove(overlay);overlay.geometry.dispose();overlay.material.dispose();}};
}
