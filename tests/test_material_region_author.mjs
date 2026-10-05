import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {authorRequest,checkedAuthorPreview,checkedAuthorSave,createMaterialRegionAuthor} from '../scripts/material-region-author.mjs';
import {emptyDraft,createNativeSceneEditor} from '../scripts/native-scene-editor.mjs';
const clone=structuredClone,hash='a'.repeat(64),profile='{"mapping":{"LeftHand":1}}',bound=createHash('sha256').update(profile).digest('hex');
const draft=emptyDraft();draft.scene.duration_s=2;const actor={glb:'/files/rig-jobs/test/transfer/character.glb',sha256:hash,animation_index:0,placement:{translation_m:[0,0,0],rotation_xyzw:[0,0,0,1]}};
draft.scene.actors={A:clone(actor),B:{...clone(actor),sha256:'b'.repeat(64)}};
draft.scene.contacts=[{id:'meeting',actor:'A',vertices:[[6,0,0]],reduction:'centroid',target:{space:'actor',actor:'B',vertices:[[6,0,0]],reduction:'centroid'},mode:'touch',interval_s:[1,1],limits:{position_m:.005}}];
const patch={glb_sha256:hash,vertices:[[6,0,2],[6,0,0],[6,0,1]]},form={patchId:'left-picked',role:'LeftHand',children:true,weight:1};
function preview(request){return {schema:request.schema,status:'complete',id:'preview',at:'fixture',result_sha256:hash,request_sha256:hash,patch_sha256:hash,selection_sha256:hash,
 input_sha256:{'character.glb':request.actor.sha256,'rig-profile.json':request.profile_sha256},implementation_sha256:{'studio_material_region.py':hash,'material_patch_bundle.py':hash},
 request:clone(request),patch:{schema:'strep-rig-material-patch-v1',role:request.role,selector:clone(request.selector),source:{character_sha256:request.actor.sha256,profile_sha256:request.profile_sha256,reference_pose:'default_nodes',weight_normalization:'RigAsset per-vertex sum'},vertices:[[6,0,0],[6,0,1],[6,0,2]],face_references:[[6,0,0]],reference_positions_m:[[0,0,0],[1,0,0],[1,1,0]],mapped_node:1,selected_nodes:[1,5],vertex_ownership:[1,1,1],requires_anatomical_review:true,anatomy_verified:false,contact_target_approved:false,quality_approved:false,release_approved:false},
 all_picked_vertices_accounted:true,anatomical_review_pending:true,animation_edited:false,motion_contacts_measured:false,engine_executed:false,human_reviewed:false,quality_approved:false,training_admitted:false,release_approved:false};}
function saved(v){return {schema:v.schema,status:'complete',id:'saved',bundle:'material-region-bundles/saved',result_sha256:hash,preview_id:v.id,preview_sha256:v.result_sha256,patch_id:v.request.patch_id,character_sha256:v.request.actor.sha256,profile_sha256:v.request.profile_sha256,faces:v.patch.face_references.length,vertices:v.patch.vertices.length,explicit_triangle_selection:true,original_selected:true,anatomical_review_pending:true,animation_edited:false,motion_contacts_measured:false,engine_executed:false,human_reviewed:false,quality_approved:false,training_admitted:false,release_approved:false};}
const request=authorRequest(draft,'meeting','source',patch,form,profile,bound),good=preview(request),goodSave=saved(good);
assert.deepEqual(checkedAuthorPreview(good,request),good);assert.deepEqual(checkedAuthorSave(goodSave,good),goodSave);
for(const change of [{patchId:'../bad'},{role:''},{children:1},{weight:0},{weight:NaN}])assert.throws(()=>authorRequest(draft,'meeting','source',patch,{...form,...change},profile,bound));
for(const bad of [{...patch,glb_sha256:'b'.repeat(64)},{...patch,vertices:[[6,0,0],[6,0,0],[6,0,1]]},{...patch,vertices:[[true,0,0],[6,0,1],[6,0,2]]}])assert.throws(()=>authorRequest(draft,'meeting','source',bad,form,profile,bound));
assert.throws(()=>authorRequest(draft,'missing','source',patch,form,profile,bound));
const world=clone(draft);world.scene.contacts[0].target={space:'world',points_m:[[0,0,0]]};assert.throws(()=>authorRequest(world,'meeting','partner',patch,form,profile,bound));
for(const change of [v=>v.request.vertices.reverse(),v=>v.input_sha256['rig-profile.json']='b'.repeat(64),v=>v.patch.vertices[0]=[6,0,9],v=>v.patch.face_references.push(v.patch.face_references[0]),v=>v.patch.reference_positions_m.pop(),v=>v.patch.reference_positions_m[0][0]=NaN,v=>v.patch.selected_nodes=[],v=>v.patch.vertex_ownership[0]=.5,v=>v.patch.anatomy_verified=true,v=>v.patch.contact_target_approved=true,
 ...['animation_edited','motion_contacts_measured','engine_executed','human_reviewed','quality_approved','training_admitted','release_approved'].map(k=>v=>v[k]=true)]){const bad=clone(good);change(bad);assert.throws(()=>checkedAuthorPreview(bad,request));}
for(const change of [v=>v.bundle='../saved',v=>v.preview_sha256='b'.repeat(64),v=>v.character_sha256='b'.repeat(64),v=>v.faces=0,v=>v.explicit_triangle_selection=false,v=>v.engine_executed=true,v=>v.quality_approved=true]){const bad=clone(goodSave);change(bad);assert.throws(()=>checkedAuthorSave(bad,good));}
class Element{constructor(){this.value='';this.checked=false;this.disabled=false;this.textContent='';this.children=[];this.files=[];}replaceChildren(...v){this.children=v;this.value=v[0]?.value??'';}append(...v){this.children.push(...v);}}
const html=await readFile(new URL('../scripts/native-scene-editor.html',import.meta.url),'utf8');
function nodes(){const map=new Map();for(const m of html.matchAll(/<[^>]*id="(nativeScene[^"]+)"[^>]*>/g)){assert(!map.has(m[1]));const el=new Element();el.value=m[0].match(/value="([^"]*)"/)?.[1]??'';map.set(m[1],el);}return {map,document:{getElementById:id=>map.get(id),createElement:()=>new Element()}};}
const buffer=new TextEncoder().encode(profile).buffer,file={size:buffer.byteLength,arrayBuffer:async()=>buffer};
function fill(map){for(const [k,v]of Object.entries({ID:form.patchId,Role:form.role,Weight:'1'}))map.get('nativeSceneRegionAuthor'+k).value=v;map.get('nativeSceneRegionAuthorChildren').checked=true;map.get('nativeSceneRegionAuthorProfile').files=[file];}
function setup(){const {map,document}=nodes();fill(map);let state=clone(draft),picked=clone(patch),side='source',reply=null,result=null,status='';const posts=[];
 const widget=createMaterialRegionAuthor({document,getDraft:()=>state,getContact:()=> 'meeting',getSide:()=>side,getPatch:()=>picked,status:v=>status=v,saved:v=>result=v,digest:async b=>createHash('sha256').update(new Uint8Array(b)).digest('hex'),post:async(url,p)=>{posts.push([url,clone(p)]);return reply?reply(url,p):url.endsWith('-preview')?preview(p):goodSave;}});
 return {map,widget,el:n=>map.get('nativeSceneRegionAuthor'+n),posts,result:()=>result,status:()=>status,changeDraft:()=>state.geometry.limits.penetration_m=.002,changePick:()=>picked.vertices.reverse(),changeSide:()=>side='partner',reply:v=>reply=v};}
{
 const s=setup();await s.el('Preview').onclick();assert(!s.el('Save').disabled);assert.equal(s.result(),null);await s.el('Save').onclick();assert.deepEqual(s.result(),goodSave);assert.deepEqual(s.posts.map(p=>p[0]),['/api/native-scene-material-region-preview','/api/native-scene-material-region-save']);assert(s.el('Save').disabled);
}
for(const fault of ['draft','pick','side','profile','clear']){
 const s=setup();let resolve;s.reply((url,p)=>new Promise(r=>resolve=()=>r(preview(p))));const pending=s.el('Preview').onclick();
 await new Promise(r=>setTimeout(r,0));await s.el('Preview').onclick();assert(s.el('Preview').disabled);assert.match(s.status(),/Wait/);
 if(fault==='draft')s.changeDraft();if(fault==='pick')s.changePick();if(fault==='side')s.changeSide();if(fault==='profile')s.el('Profile').files=[{...file}];if(fault==='clear')s.widget.clear();
 resolve();await pending;assert(s.el('Save').disabled);assert.match(s.status(),/changed/);assert.equal(s.result(),null);assert(!s.el('Preview').disabled);
}
{
 const s=setup();await s.el('Preview').onclick();let resolve;s.reply((_,p)=>new Promise(r=>resolve=()=>r(goodSave)));const saving=s.el('Save').onclick();await s.el('Save').onclick();assert.equal(s.posts.length,2);assert.match(s.status(),/Wait/);s.changePick();resolve();await saving;assert.equal(s.result(),null);assert.match(s.status(),/changed/);
}
{
 const s=setup();await s.el('Preview').onclick();s.el('Weight').value='.8';s.el('Weight').onchange();await s.el('Save').onclick();assert.equal(s.posts.length,1);assert.match(s.status(),/Preview/);
}
{
 const {map,document}=nodes();const editor=createNativeSceneEditor({document,api:async()=>({jobs:[]}),post:async(url,p)=>url.endsWith('-preview')?preview(p):goodSave,getContext:()=>({}),getPatch:()=>patch,download:()=>{}});
 editor.bind(draft);fill(map);map.get('nativeSceneRegionSide').value='source';map.get('nativeSceneRevisionContact').value='meeting';
 await map.get('nativeSceneRegionAuthorPreview').onclick();await map.get('nativeSceneRegionAuthorSave').onclick();assert.equal(map.get('nativeSceneRegionBundle').value,goodSave.bundle);assert.equal(map.get('nativeSceneRegionResult').value,goodSave.result_sha256);assert.equal(map.get('nativeSceneRegionIndices').value,'');assert.deepEqual(editor.snapshot(),draft);
}
const integrated=await readFile(new URL('../scripts/action-studio.html',import.meta.url),'utf8');for(const suffix of ['Profile','ID','Role','Weight','Children','Preview','Save','Summary','Faces'])assert.equal([...integrated.matchAll(new RegExp(`id="nativeSceneRegionAuthor${suffix}"`,'g'))].length,1);
console.log('Picked-region preview/save, profile bindings, complete region receipts, stale edits, click ownership and explicit post-save correspondence passed offline.');
