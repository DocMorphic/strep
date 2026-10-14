// Bind framing to original glTF node indices, including renamed/namespace bones.
export function selectReviewMotion(selected,gltf){
 const index=selected.animation_index??0;
 if(!Number.isInteger(index)||index<0||!Array.isArray(gltf.animations)||!gltf.animations[index])throw Error('Selected review animation unavailable');
 let root;
 if(selected.reference_node_index!==undefined){
  if(!Number.isInteger(selected.reference_node_index)||selected.reference_node_index<0||!gltf.parser?.associations?.get)throw Error('Native review joint binding unavailable');
  const matches=[];gltf.scene.traverse(node=>{if(gltf.parser.associations.get(node)?.nodes===selected.reference_node_index)matches.push(node);});
  if(matches.length!==1)throw Error('Native review joint binding is missing or ambiguous');root=matches[0];
 }else root=gltf.scene.getObjectByName(selected.reference_node||'Hips');
 if(!root)throw Error('Review reference joint unavailable');
 const clip=gltf.animations[index];
 if(selected.duration_s!==undefined&&(!Number.isFinite(selected.duration_s)||selected.duration_s<=0||!Number.isFinite(clip.duration)||Math.abs(clip.duration-selected.duration_s)>1e-5))throw Error('Selected review animation duration changed');
 return {root,clip};
}
