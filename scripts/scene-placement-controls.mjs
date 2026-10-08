export function placementPose(scene,kind,id,mode,key){
 if(kind==='actor'){if(!scene.actors[id])throw Error('Choose a scene actor');return scene.actors[id].transform;}
 if(kind!=='object'||!scene.objects[id])throw Error('Choose a scene object');
 const keys=scene.objects[id].keyframes;
 if(mode==='path')return keys[0];
 if(mode!=='key'||!Number.isInteger(key))throw Error('Choose a saved prop pose');
 const result=keys.find(pose=>pose.frame===key);if(!result)throw Error('Object pose no longer exists');return result;
}
export function placementKeyOptions(scene,kind,id){
 if(kind!=='object'||!scene.objects[id])return [];
 return scene.objects[id].keyframes.map(pose=>({value:String(pose.frame),label:`${(pose.frame/30).toFixed(3)} s · frame ${pose.frame}`}));
}
export function objectEditKeys(scene,id,mode,key){
 placementPose(scene,'object',id,mode,key);
 return mode==='path'?scene.objects[id].keyframes:[scene.objects[id].keyframes.find(pose=>pose.frame===key)];
}
