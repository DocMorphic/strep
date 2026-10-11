// SOMA30 pose channels, not an action vocabulary or anatomical contact model.
export const JOINT_CHOICES=Object.freeze([
 ['Hips','Pelvis'],['Spine1','Lower spine'],['Spine2','Middle spine'],['Chest','Chest'],
 ['Neck1','Lower neck'],['Neck2','Upper neck'],['Head','Head'],['Jaw','Jaw'],
 ['LeftEye','Left eye'],['RightEye','Right eye'],['LeftShoulder','Left shoulder'],
 ['LeftArm','Left upper arm'],['LeftForeArm','Left elbow'],['LeftHand','Left hand'],
 ['LeftHandThumbEnd','Left thumb tip'],['LeftHandMiddleEnd','Left middle-finger tip'],
 ['RightShoulder','Right shoulder'],['RightArm','Right upper arm'],['RightForeArm','Right elbow'],
 ['RightHand','Right hand'],['RightHandThumbEnd','Right thumb tip'],['RightHandMiddleEnd','Right middle-finger tip'],
 ['LeftLeg','Left hip'],['LeftShin','Left knee'],['LeftFoot','Left ankle'],['LeftToeBase','Left toes'],
 ['RightLeg','Right hip'],['RightShin','Right knee'],['RightFoot','Right ankle'],['RightToeBase','Right toes'],
].map(row=>Object.freeze(row)));
const names=new Set(JOINT_CHOICES.map(([name])=>name));
export function validateJointSelection(selected){
 if(!Array.isArray(selected)||selected.length<1||selected.length>JOINT_CHOICES.length
    ||selected.some(name=>typeof name!=='string'||!names.has(name))||new Set(selected).size!==selected.length)
  throw Error('Choose at least one distinct body part for the pose guide.');
 return selected.slice();
}
