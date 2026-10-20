// Read untouched embedded source coefficients before GLTFLoader can normalize them.
export function sourceGLB(buffer){
 const view=new DataView(buffer),uint=i=>view.getUint32(i,true);
 if(buffer.byteLength<28||uint(0)!==0x46546c67||uint(4)!==2||uint(8)!==buffer.byteLength||uint(16)!==0x4e4f534a)throw Error('Embedded GLB 2 required.');
 const jsonLength=uint(12),binHeader=20+jsonLength;
 if(jsonLength%4||binHeader+8>buffer.byteLength||uint(binHeader+4)!==0x004e4942||binHeader+8+uint(binHeader)!==buffer.byteLength)throw Error('Exact JSON and BIN chunks required.');
 const document=JSON.parse(new TextDecoder().decode(new Uint8Array(buffer,20,jsonLength))),binStart=binHeader+8,binLength=uint(binHeader);
 if(document.buffers?.length!==1||document.buffers[0].uri||document.buffers[0].byteLength>binLength)throw Error('One embedded buffer required.');
 function accessor(index){
  const a=document.accessors?.[index],b=document.bufferViews?.[a?.bufferView],width={SCALAR:1,VEC2:2,VEC3:3,VEC4:4,MAT4:16}[a?.type],component={5121:[1,'getUint8',255],5123:[2,'getUint16',65535],5125:[4,'getUint32',4294967295],5126:[4,'getFloat32',1]}[a?.componentType];
  if(!a||a.sparse||!b||b.buffer!==0||!width||!component||!Number.isInteger(a.count)||a.count<1)throw Error('Explicit supported source accessor required.');
  const [size,method,denominator]=component,offset=a.byteOffset??0,start=b.byteOffset??0,stride=b.byteStride??width*size;
  if(![offset,start,stride,b.byteLength].every(Number.isSafeInteger)||offset<0||start<0||stride<width*size||start%size||offset%size||stride%size||offset+(a.count-1)*stride+width*size>b.byteLength||start+b.byteLength>document.buffers[0].byteLength||a.normalized&&![5121,5123].includes(a.componentType))throw Error('Source accessor range or normalization is invalid.');
  const result=new Float64Array(a.count*width);
  for(let i=0;i<a.count;i++)for(let j=0;j<width;j++){const value=view[method](binStart+start+offset+i*stride+j*size,true)/(a.normalized?denominator:1);if(!Number.isFinite(value))throw Error('Nonfinite source coefficient.');result[i*width+j]=value;}
  return {values:result,width,count:a.count};
 }
 return {document,accessor};
}

// Match RigAsset's measurement convention: normalize all source influences
// together, never only the first four. Original GLB bytes remain unchanged.
// Place after LBS; Float32 GPU coefficients can still sum to slightly non-unit w.
export async function bindSourceSkin(THREE,gltf,source,wrapper){
 const table=new Map(),nodeObjects=new Map(),meshes=[];
 for(const [i] of source.document.nodes.entries())nodeObjects.set(i,await gltf.parser.getDependency('node',i));
 gltf.scene.traverse(mesh=>{if(!mesh.isSkinnedMesh)return;
  let node=mesh,association;
  while(node){const a=gltf.parser.associations.get(node);if(Number.isInteger(a?.nodes)){association=a;break;}node=node.parent;}
  const meshAssociation=gltf.parser.associations.get(mesh),nodeId=association?.nodes,primitiveId=meshAssociation?.primitives??0;
  const description=source.document.nodes[nodeId],primitive=source.document.meshes?.[description?.mesh]?.primitives?.[primitiveId],skin=source.document.skins?.[description?.skin];
  if(!primitive||!skin||table.has(`${nodeId}:${primitiveId}`))throw Error('Unambiguous native skin primitive required.');
  const positions=source.accessor(primitive.attributes.POSITION),sets=[];
  for(let slot=0;slot<2;slot++){
   if(primitive.attributes['JOINTS_'+slot]===undefined){if(slot===0)throw Error('Source joints required.');continue;}
   const j=source.accessor(primitive.attributes['JOINTS_'+slot]),w=source.accessor(primitive.attributes['WEIGHTS_'+slot]);
   if(j.width!==4||w.width!==4||j.count!==positions.count||w.count!==positions.count||[...j.values].some(i=>!Number.isInteger(i)||i<0||i>=skin.joints.length))throw Error('Source skin coefficient shape mismatch.');
   sets.push({j:j.values,w:w.values});
  }
  for(let vertex=0;vertex<positions.count;vertex++){
   let sum=0;for(const set of sets)for(let k=0;k<4;k++){const w=set.w[vertex*4+k];if(w<0)throw Error('Nonnegative source weights required.');sum+=w;}
   if(Math.abs(sum-1)>1e-3)throw Error('Source weights exceed the native measurement tolerance.');
   for(const set of sets)for(let k=0;k<4;k++)set.w[vertex*4+k]/=sum;
  }
  const inverse=source.accessor(skin.inverseBindMatrices);if(inverse.width!==16||inverse.count!==skin.joints.length)throw Error('Explicit source inverse binds required.');
  // Clone attributes: GLTFLoader can share a geometry between node instances.
  mesh.geometry=mesh.geometry.clone();
  for(let slot=0;slot<sets.length;slot++){
   mesh.geometry.setAttribute(slot?'joints_1':'skinIndex',new THREE.Float32BufferAttribute(sets[slot].j,4));
   mesh.geometry.setAttribute(slot?'weights_1':'skinWeight',new THREE.Float32BufferAttribute(sets[slot].w,4));
  }
  const placementInverse=new THREE.Matrix4(),placement=wrapper.matrixWorld;
  const material=mesh.material.clone();mesh.material=material;mesh.frustumCulled=false;
  material.onBeforeCompile=shader=>{
   shader.uniforms.strepPlacement={value:placement};shader.uniforms.strepPlacementInverse={value:placementInverse};
   shader.vertexShader='uniform mat4 strepPlacement;\nuniform mat4 strepPlacementInverse;\n'+(sets.length===2?'attribute vec4 joints_1;\nattribute vec4 weights_1;\n':'')+shader.vertexShader;
   if(sets.length===2){
    shader.vertexShader=shader.vertexShader.replace('#include <skinbase_vertex>',THREE.ShaderChunk.skinbase_vertex+'\n#ifdef USE_SKINNING\nmat4 boneMatA=getBoneMatrix(joints_1.x), boneMatB=getBoneMatrix(joints_1.y), boneMatC=getBoneMatrix(joints_1.z), boneMatD=getBoneMatrix(joints_1.w);\n#endif');
    shader.vertexShader=shader.vertexShader.replace('#include <skinnormal_vertex>',THREE.ShaderChunk.skinnormal_vertex.replace('skinMatrix = bindMatrixInverse','skinMatrix += weights_1.x*boneMatA+weights_1.y*boneMatB+weights_1.z*boneMatC+weights_1.w*boneMatD;\nskinMatrix = bindMatrixInverse'));
   }
   let skinning=THREE.ShaderChunk.skinning_vertex;
   const extra=sets.length===2?'skinned += boneMatA*skinVertex*weights_1.x+boneMatB*skinVertex*weights_1.y+boneMatC*skinVertex*weights_1.z+boneMatD*skinVertex*weights_1.w;\n':'';
   skinning=skinning.replace('transformed = ( bindMatrixInverse * skinned ).xyz;',extra+'vec4 nativePoint = strepPlacementInverse * skinned;\nnativePoint.w = 1.0;\ntransformed = (bindMatrixInverse * strepPlacement * nativePoint).xyz;');
   shader.vertexShader=shader.vertexShader.replace('#include <skinning_vertex>',skinning);
  };
  material.customProgramCacheKey=()=>`strep-native-measured-skin-v1-${sets.length}`;material.needsUpdate=true;
  const matrices=skin.joints.map(()=>new THREE.Matrix4()),inverses=skin.joints.map((_,i)=>new THREE.Matrix4().fromArray(inverse.values,i*16));
  const record={mesh,nodeId,primitiveId,positions,sets,matrices,
   update(){placementInverse.copy(placement).invert();for(let i=0;i<matrices.length;i++)matrices[i].multiplyMatrices(placementInverse,nodeObjects.get(skin.joints[i]).matrixWorld).multiply(inverses[i]);},
   point(index){
    if(!Number.isInteger(index)||index<0||index>=positions.count)throw Error('Unknown source skin vertex.');
    const p=positions.values,x=p[index*3],y=p[index*3+1],z=p[index*3+2],result=new THREE.Vector3();
    for(const set of sets)for(let k=0;k<4;k++){const w=set.w[index*4+k],m=matrices[set.j[index*4+k]].elements;result.x+=w*(m[0]*x+m[4]*y+m[8]*z+m[12]);result.y+=w*(m[1]*x+m[5]*y+m[9]*z+m[13]);result.z+=w*(m[2]*x+m[6]*y+m[10]*z+m[14]);}
    return result.applyMatrix4(placement);
   }};
  table.set(`${nodeId}:${primitiveId}`,record);meshes.push(record);
 });
 if(!meshes.length)throw Error('No native skin geometry found.');
 return {meshes,update(){for(const record of meshes)record.update();},point(ref){const record=table.get(`${ref[0]}:${ref[1]}`);if(!record)throw Error('Contact refers to a missing skin primitive.');return record.point(ref[2]);}};
}
