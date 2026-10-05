import assert from 'node:assert/strict';
import {checkedRegionOrientation,orientationViews,renderRegionOrientation} from '../scripts/material-region-orientation.mjs';

function fixture(){
 const winding={triangle_twice_areas_m2:[1,1],summed_twice_area_m2:2,normal_coherence:1,normal_available:true,area_weighted_winding_normal:[0,0,1],degenerate_local_faces:[]};
 const patch={reference_positions_m:[[0,0,0],[1,0,0],[1,1,0],[0,1,0]],face_references:[[6,0,0],[6,0,1]],selector:{minimum_twice_area_m2:1e-12},winding};
 const value={schema:'strep-material-region-orientation-v1',coordinate_space:'character_default_pose_metres',face_references:structuredClone(patch.face_references),
  triangle_vertex_indices:[[0,1,2],[0,2,3]],triangle_centroids_m:[[2/3,1/3,0],[1/3,2/3,0]],triangle_unit_winding_normals:[[0,0,1],[0,0,1]],triangle_twice_areas_m2:[1,1],area_weighted_centroid_m:[.5,.5,0],patch_winding:structuredClone(winding),
  complete_triangle_population:true,original_winding_preserved:true,animation_sampled:false,anatomical_review_pending:true,contact_intent_approved:false,quality_approved:false,release_approved:false};
 return {patch,value};
}
const {patch,value}=fixture();assert.deepEqual(checkedRegionOrientation(value,patch),value);
for(const mutate of [v=>v.schema='other',v=>v.coordinate_space='world',v=>v.face_references.reverse(),v=>v.triangle_vertex_indices.pop(),v=>v.triangle_vertex_indices[0]=[0,0,1],v=>v.triangle_vertex_indices[0][0]=true,v=>v.triangle_vertex_indices[0][0]=4,
 v=>v.triangle_centroids_m[0][0]=NaN,v=>v.triangle_centroids_m[0][0]+=.1,v=>v.triangle_unit_winding_normals[0][2]=-1,v=>v.triangle_twice_areas_m2[0]=0,v=>v.area_weighted_centroid_m[0]+=.1,v=>v.patch_winding.normal_coherence=0,
 ...['complete_triangle_population','original_winding_preserved','anatomical_review_pending'].map(k=>v=>v[k]=false),...['animation_sampled','contact_intent_approved','quality_approved','release_approved'].map(k=>v=>v[k]=true)]){
 const bad=structuredClone(value);mutate(bad);assert.throws(()=>checkedRegionOrientation(bad,patch));
}
const dangling=structuredClone(patch);dangling.reference_positions_m.push([2,2,0]);assert.throws(()=>checkedRegionOrientation(value,dangling));
const views=orientationViews(value,patch);assert.equal(views.length,3);
for(const v of views){assert.equal(v.vertices.length,4);assert.equal(v.triangles.length,2);assert.equal(v.arrows.length,2);for(const p of [...v.vertices,...v.arrows.flatMap(a=>[a.start,a.end])]){assert(p.every(Number.isFinite));assert(p[0]>=28&&p[0]<=292&&p[1]>=38&&p[1]<=194);}}
assert(views[0].arrows.every(a=>a.toward));assert.deepEqual(views[0].arrows[0].start,views[0].arrows[0].end);
assert(views[1].arrows[0].end[0]<views[1].arrows[0].start[0]);assert(views[2].arrows[0].end[1]>views[2].arrows[0].start[1]);
const reversed=structuredClone(value);reversed.triangle_vertex_indices=[[0,2,1],[0,3,2]];reversed.triangle_unit_winding_normals=[[0,0,-1],[0,0,-1]];
reversed.patch_winding.area_weighted_winding_normal=[0,0,-1];const reversePatch=structuredClone(patch);reversePatch.winding=structuredClone(reversed.patch_winding);
assert(orientationViews(reversed,reversePatch)[0].arrows.every(a=>!a.toward));
// Distinct original faces with the same corners stay visible, including opposing winding.
const overlap=fixture();overlap.patch.reference_positions_m=overlap.patch.reference_positions_m.slice(0,3);
overlap.value.triangle_vertex_indices=[[0,1,2],[0,2,1]];overlap.value.triangle_centroids_m=[[2/3,1/3,0],[2/3,1/3,0]];
overlap.value.area_weighted_centroid_m=[2/3,1/3,0];overlap.value.triangle_unit_winding_normals=[[0,0,1],[0,0,-1]];
for(const w of [overlap.patch.winding,overlap.value.patch_winding])Object.assign(w,{normal_coherence:0,normal_available:false,area_weighted_winding_normal:null});
assert.equal(orientationViews(overlap.value,overlap.patch)[0].triangles.length,2);
// Projection is translation invariant and still shows a normal along a very large shared coordinate.
const shifted=fixture();for(const p of shifted.patch.reference_positions_m)p[2]=1e300;for(const p of shifted.value.triangle_centroids_m)p[2]=1e300;shifted.value.area_weighted_centroid_m[2]=1e300;
assert.deepEqual(orientationViews(shifted.value,shifted.patch),views);
class Node{constructor(tag){this.tag=tag;this.attrs={};this.children=[];this.textContent='';}setAttribute(k,v){this.attrs[k]=v;}append(...v){this.children.push(...v);}replaceChildren(...v){this.children=v;}}
const document={createElementNS:(_,tag)=>new Node(tag)},container=new Node('div');renderRegionOrientation(document,container,value,patch);
assert.equal(container.children.length,3);for(const svg of container.children){assert.equal(svg.tag,'svg');assert.equal(svg.attrs.role,'img');assert.match(svg.attrs['aria-label'],/default-pose/);assert.equal(svg.children.filter(c=>c.tag==='polygon').length,2);assert.equal(svg.children.filter(c=>c.tag==='text'&&/^[0-3]$/.test(c.textContent)).length,4);}
renderRegionOrientation(document,container,reversed,reversePatch);assert.equal(container.children.length,3);assert(container.children[0].children.some(c=>c.tag==='path'));
console.log('Complete winding geometry, reversed/opposing faces, finite fitted projections, translated poses and accessible SVG output passed offline.');
