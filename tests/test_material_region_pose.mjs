import assert from 'node:assert/strict';
import {checkedAuthorPose,poseRequest,renderRegionPose,POSE_SCHEMA} from '../scripts/material-region-pose.mjs';
const clone=structuredClone,h='a'.repeat(64),ref=[[6,0,0]],vertices=[[6,0,0],[6,0,1],[6,0,2]];
const actor={glb:'/files/rig-jobs/test/character.glb',sha256:h,animation_index:2,placement:{translation_m:[100,200,300]}};
const draft={scene:{actors:{A:actor,B:clone(actor)},contacts:[{id:'touch',actor:'A',target:{space:'actor',actor:'B'}}]}};
const patch={face_references:ref,vertices,selector:{minimum_twice_area_m2:1e-12}};
const preview={id:'preview',result_sha256:h,patch_sha256:h,input_sha256:{'character.glb':h,'rig-profile.json':h},implementation_sha256:{'studio_material_region.py':h},request:{actor:{glb:actor.glb,sha256:h}},patch,orientation:{triangle_vertex_indices:[[0,1,2]]}};
const request=poseRequest(preview,draft,'touch','source',.5);
assert.deepEqual(request,{schema:POSE_SCHEMA,id:'preview',preview_sha256:h,animation_index:2,time_s:.5});
assert.deepEqual(poseRequest(preview,draft,'touch','partner',.5),request);
assert(!('placement' in request));
for(const time of [NaN,Infinity,-1,'0',true])assert.throws(()=>poseRequest(preview,draft,'touch','source',time));
for(const [contact,side]of [['missing','source'],['touch','other']])assert.throws(()=>poseRequest(preview,draft,contact,side,0));
const changed=clone(draft);changed.scene.actors.A.sha256='b'.repeat(64);assert.throws(()=>poseRequest(preview,changed,'touch','source',0));
changed.scene.contacts[0].target={space:'world'};assert.throws(()=>poseRequest(preview,changed,'touch','partner',0));
const pose={coordinate_space:'character_animation_metres',animation_index:2,animation_name:'turn',duration_s:1,time_s:.5,
 vertices:clone(vertices),positions_m:[[0,0,.5],[0,1,.5],[0,1,1.5]],face_references:clone(ref),triangle_vertex_indices:[[0,1,2]],triangle_centroids_m:[[0,2/3,5/6]],triangle_unit_winding_normals:[[1,0,0]],triangle_twice_areas_m2:[1],
 patch_winding:{triangle_twice_areas_m2:[1],summed_twice_area_m2:1,normal_coherence:1,normal_available:true,area_weighted_winding_normal:[1,0,0],degenerate_local_faces:[]},
 complete_triangle_population:true,original_winding_preserved:true,animation_sampled:true,scene_placement_applied:false,contact_conditions_measured:false,anatomical_review_pending:true,contact_intent_approved:false,quality_approved:false,release_approved:false};
const result={schema:POSE_SCHEMA,status:'complete',id:'sample',preview_id:preview.id,preview_sha256:h,patch_sha256:h,result_sha256:h,request_sha256:h,pose_sha256:h,input_sha256:clone(preview.input_sha256),implementation_sha256:{...preview.implementation_sha256,'studio_material_region_pose.py':h},request:clone(request),pose:clone(pose),animation_edited:false,engine_executed:false,human_reviewed:false,quality_approved:false,training_admitted:false,release_approved:false};
assert.deepEqual(checkedAuthorPose(result,request,preview),result);
for(const mutate of [v=>v.request.time_s=0,v=>v.preview_id='other',v=>v.patch_sha256='b'.repeat(64),v=>v.input_sha256['character.glb']='b'.repeat(64),v=>v.pose_sha256=null,v=>delete v.implementation_sha256['studio_material_region_pose.py'],v=>v.implementation_sha256['studio_material_region.py']='b'.repeat(64),v=>v.pose.time_s=0,v=>v.pose.duration_s=.1,v=>v.pose.positions_m.pop(),v=>v.pose.positions_m[0][0]=Infinity,v=>v.pose.triangle_vertex_indices[0].reverse(),v=>v.pose.triangle_centroids_m[0][1]=0,v=>v.pose.triangle_unit_winding_normals[0]=[-1,0,0],v=>v.pose.triangle_unit_winding_normals[0]=null,v=>v.pose.triangle_twice_areas_m2[0]=0,v=>v.pose.patch_winding.normal_coherence=0,v=>v.pose.patch_winding.degenerate_local_faces=[0],v=>v.pose.vertices.reverse(),v=>v.pose.face_references=[],
 ...['animation_edited','engine_executed','human_reviewed','quality_approved','training_admitted','release_approved'].map(k=>v=>v[k]=true),...['scene_placement_applied','contact_conditions_measured','contact_intent_approved','quality_approved','release_approved'].map(k=>v=>v.pose[k]=true)]){const bad=clone(result);mutate(bad);assert.throws(()=>checkedAuthorPose(bad,request,preview));}
class Node{constructor(tag){this.tag=tag;this.attrs={};this.children=[];}setAttribute(k,v){this.attrs[k]=v;}append(...v){this.children.push(...v);}replaceChildren(...v){this.children=v;}}
const document={createElementNS:(_,tag)=>new Node(tag)},container=new Node('div');
const views=renderRegionPose(document,container,pose);assert.equal(views.length,3);assert(views[1].arrows[0].toward);assert.deepEqual(views[1].arrows[0].start,views[1].arrows[0].end);
const collapsed=clone(result);Object.assign(collapsed.pose,{positions_m:[[.5,.5,.5],[.5,.5,.5],[.5,.5,.5]],triangle_centroids_m:[[.5,.5,.5]],triangle_unit_winding_normals:[null],triangle_twice_areas_m2:[0],patch_winding:{triangle_twice_areas_m2:[0],summed_twice_area_m2:0,normal_coherence:0,normal_available:false,area_weighted_winding_normal:null,degenerate_local_faces:[0]}});
assert.deepEqual(checkedAuthorPose(collapsed,request,preview),collapsed);
const unavailable=renderRegionPose(document,container,collapsed.pose);assert.equal(unavailable.length,3);for(const view of unavailable){assert.equal(view.triangles.length,1);assert.equal(view.vertices.length,3);assert(view.arrows[0].unavailable);assert(view.arrows[0].start.every(Number.isFinite));}
for(const svg of container.children){assert.match(svg.attrs['aria-label'],/animation 2 at 0.5 s; character-local/);assert.equal(svg.children.filter(n=>n.tag==='polygon').length,1);assert(svg.children.some(n=>n.tag==='title'&&/unavailable/.test(n.textContent)));assert(svg.children.some(n=>n.tag==='path'&&n.attrs.stroke==='#fb7185'));}
console.log('Pinned native pose receipts, explicit time/animation, all triangles, preserved winding, collapsed surfaces and finite SVG inspection passed offline.');
