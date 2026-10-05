import {projectRegionDirections,renderDirectionViews} from './material-region-orientation.mjs';
const key=v=>JSON.stringify(v,(_,x)=>x&&typeof x==='object'&&!Array.isArray(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,x[k]])):x);
const hash=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const finite=v=>typeof v==='number'&&Number.isFinite(v);
const vector=v=>Array.isArray(v)&&v.length===3&&v.every(finite);
const near=(a,b)=>finite(a)&&finite(b)&&Math.abs(a-b)<=1e-12+1e-10*Math.max(Math.abs(a),Math.abs(b));
const vnear=(a,b)=>vector(a)&&vector(b)&&a.every((v,i)=>near(v,b[i]));
const sub=(a,b)=>a.map((v,i)=>v-b[i]);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
export const POSE_SCHEMA='strep-studio-material-region-pose-v1';

export function poseRequest(preview,draft,contact,side,time){
 const row=draft.scene.contacts.find(c=>c.id===contact);
 if(!row||!['source','partner'].includes(side)||side==='partner'&&row.target.space!=='actor')throw Error('Choose the region’s source or partner character.');
 const actor=draft.scene.actors[side==='source'?row.actor:row.target.actor];
 if(actor?.sha256!==preview.request.actor.sha256||actor.glb!==preview.request.actor.glb||!Number.isInteger(actor.animation_index)||actor.animation_index<0||!finite(time)||time<0)throw Error('Choose a finite character-local time on the region’s selected animation.');
 return {schema:POSE_SCHEMA,id:preview.id,preview_sha256:preview.result_sha256,animation_index:actor.animation_index,time_s:time};
}

export function checkedAuthorPose(value,request,preview){
 const p=value?.pose,patch=preview.patch,n=patch.face_references.length,points=p?.positions_m;
 if(value?.schema!==POSE_SCHEMA||value.status!=='complete'||!/^[A-Za-z0-9_-]{1,64}$/.test(value.id)||!['result_sha256','request_sha256','pose_sha256'].every(k=>hash(value[k]))
  ||key(value.request)!==key(request)||value.preview_id!==preview.id||value.preview_sha256!==preview.result_sha256||value.patch_sha256!==preview.patch_sha256||key(value.input_sha256)!==key(preview.input_sha256)
  ||!value.implementation_sha256||!hash(value.implementation_sha256['studio_material_region_pose.py'])||Object.values(value.implementation_sha256).some(h=>!hash(h))||Object.entries(preview.implementation_sha256).some(([k,v])=>value.implementation_sha256[k]!==v)
  ||['animation_edited','engine_executed','human_reviewed','quality_approved','training_admitted','release_approved'].some(k=>value[k]!==false)
  ||p?.coordinate_space!=='character_animation_metres'||p.animation_index!==request.animation_index||p.time_s!==request.time_s||!finite(p.duration_s)||p.duration_s<=0||p.time_s>p.duration_s||typeof p.animation_name!=='string'
  ||key(p.vertices)!==key(patch.vertices)||key(p.face_references)!==key(patch.face_references)||key(p.triangle_vertex_indices)!==key(preview.orientation.triangle_vertex_indices)
  ||!Array.isArray(points)||points.length!==patch.vertices.length||!points.every(vector)||!['triangle_centroids_m','triangle_unit_winding_normals','triangle_twice_areas_m2'].every(k=>Array.isArray(p[k])&&p[k].length===n)
  ||['complete_triangle_population','original_winding_preserved','animation_sampled','anatomical_review_pending'].some(k=>p[k]!==true)||['scene_placement_applied','contact_conditions_measured','contact_intent_approved','quality_approved','release_approved'].some(k=>p[k]!==false))throw Error('Animation surface inspection does not match the selected region and time.');
 const minimum=patch.selector.minimum_twice_area_m2,degenerate=[],sum=[0,0,0];let total=0;
 for(let i=0;i<n;i++){
  const tri=p.triangle_vertex_indices[i].map(k=>points[k]),c=cross(sub(tri[1],tri[0]),sub(tri[2],tri[0])),area=Math.hypot(...c),center=tri[0].map((v,k)=>v+((tri[1][k]-v)+(tri[2][k]-v))/3);
  if(!near(area,p.triangle_twice_areas_m2[i])||!vnear(center,p.triangle_centroids_m[i])||(area<=minimum?p.triangle_unit_winding_normals[i]!==null:!vnear(c.map(v=>v/area),p.triangle_unit_winding_normals[i])))throw Error('Animation surface geometry or winding differs.');
  if(area<=minimum)degenerate.push(i);total+=area;c.forEach((v,k)=>sum[k]+=v);
 }
 const length=Math.hypot(...sum),available=!degenerate.length&&length>minimum,w=p.patch_winding;
 if(!w||!Array.isArray(w.triangle_twice_areas_m2)||w.triangle_twice_areas_m2.length!==n||!w.triangle_twice_areas_m2.every((v,i)=>near(v,p.triangle_twice_areas_m2[i]))||!near(w.summed_twice_area_m2,total)||!near(w.normal_coherence,total>0?length/total:0)||w.normal_available!==available||key(w.degenerate_local_faces)!==key(degenerate)||(available?!vnear(w.area_weighted_winding_normal,sum.map(v=>v/length)):w.area_weighted_winding_normal!==null))throw Error('Animation surface degeneracy or aggregate winding differs.');
 return structuredClone(value);
}

export function renderRegionPose(document,container,pose){
 const views=projectRegionDirections(pose.positions_m,pose.triangle_vertex_indices,pose.triangle_centroids_m,pose.triangle_unit_winding_normals);
 return renderDirectionViews(document,container,views,`animation ${pose.animation_index} at ${pose.time_s} s; character-local`,`Animation ${pose.animation_index} · ${pose.time_s} s · no scene placement`);
}
