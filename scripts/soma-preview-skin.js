// Restore all eight SOMA influences after Three.js normalizes its first four.
export function enableEightWeights(mesh){
 const extra=mesh.geometry.getAttribute('weights_1');if(!extra)return;
 const weights=mesh.geometry.getAttribute('skinWeight');
 for(let i=0;i<weights.count;i++){const remaining=1-extra.getX(i)-extra.getY(i)-extra.getZ(i)-extra.getW(i);weights.setXYZW(i,weights.getX(i)*remaining,weights.getY(i)*remaining,weights.getZ(i)*remaining,weights.getW(i)*remaining);}
 weights.needsUpdate=true;
 mesh.material.onBeforeCompile=shader=>{
  shader.vertexShader='attribute vec4 joints_1;\nattribute vec4 weights_1;\n'+shader.vertexShader;
  shader.vertexShader=shader.vertexShader.replace('#include <skinbase_vertex>',THREE_SKINBASE+'\n#ifdef USE_SKINNING\nmat4 boneMatA=getBoneMatrix(joints_1.x); mat4 boneMatB=getBoneMatrix(joints_1.y); mat4 boneMatC=getBoneMatrix(joints_1.z); mat4 boneMatD=getBoneMatrix(joints_1.w);\n#endif\n');
  shader.vertexShader=shader.vertexShader.replace('#include <skinnormal_vertex>',THREE_SKINNORMAL.replace('skinMatrix = bindMatrixInverse','skinMatrix += weights_1.x*boneMatA+weights_1.y*boneMatB+weights_1.z*boneMatC+weights_1.w*boneMatD;\nskinMatrix = bindMatrixInverse'));
  shader.vertexShader=shader.vertexShader.replace('#include <skinning_vertex>',THREE_SKINNING.replace('transformed =','skinned += boneMatA*skinVertex*weights_1.x+boneMatB*skinVertex*weights_1.y+boneMatC*skinVertex*weights_1.z+boneMatD*skinVertex*weights_1.w;\ntransformed ='));
 };
 mesh.material.customProgramCacheKey=()=> 'soma-eight-weights-v1';mesh.material.needsUpdate=true;
}
import {ShaderChunk} from 'three';
const THREE_SKINBASE=ShaderChunk.skinbase_vertex,THREE_SKINNORMAL=ShaderChunk.skinnormal_vertex,THREE_SKINNING=ShaderChunk.skinning_vertex;
