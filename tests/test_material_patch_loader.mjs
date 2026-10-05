import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {regionRequest,checkedRegion,createMaterialPatchLoader} from '../scripts/material-patch-loader.mjs';
import {createNativeSceneEditor,emptyDraft} from '../scripts/native-scene-editor.mjs';
const clone=structuredClone,hash='a'.repeat(64);
const draft=emptyDraft();draft.scene.duration_s=2;
const actor={glb:'/files/rig-jobs/a/transfer/character.glb',sha256:hash,animation_index:0,placement:{translation_m:[0,0,0],rotation_xyzw:[0,0,0,1]}};
draft.scene.actors={A:clone(actor),B:{...clone(actor),glb:'/files/rig-jobs/b/transfer/character.glb',sha256:'b'.repeat(64)}};
draft.scene.contacts=[{id:'meeting',actor:'A',vertices:[[6,0,0]],reduction:'centroid',target:{space:'actor',actor:'B',vertices:[[6,0,0]],reduction:'centroid'},mode:'touch',interval_s:[1,1],limits:{position_m:.005}}];
const form={side:'source',bundle:'test/regions',result:'c'.repeat(64),patch:'left-surface',indices:'[2,0,1]',reduction:'individual'};
function response(request){return {schema:request.schema,request:clone(request),implementation_sha256:{'studio_material_patch.py':hash,'material_patch_bundle.py':hash},
 patch:{glb_sha256:request.actor.sha256,vertices:request.vertex_indices.map(i=>[6,0,i]),reduction:request.reduction},
 binding:{bundle:request.bundle,result_sha256:request.result_sha256,patch_id:request.patch_id,patch_sha256:hash,source:{character_sha256:request.actor.sha256,profile_sha256:hash,reference_pose:'default_nodes',weight_normalization:'RigAsset per-vertex sum'},vertex_indices:clone(request.vertex_indices),reduction:request.reduction},
 explicit_vertex_correspondence:true,original_selected:true,anatomical_review_pending:true,animation_edited:false,motion_contacts_measured:false,engine_executed:false,human_reviewed:false,quality_approved:false,training_admitted:false,release_approved:false};}
const request=regionRequest(draft,'meeting',form),good=response(request);
assert.deepEqual(checkedRegion(good,request),good);
assert.deepEqual(regionRequest(draft,'meeting',{...form,side:'partner'}).actor,{glb:draft.scene.actors.B.glb,sha256:draft.scene.actors.B.sha256});
for(const change of [{indices:'[]'},{indices:'[true]'},{indices:'[0,0]'},{indices:'[-1]'},{indices:'no'},{indices:JSON.stringify(Array.from({length:257},(_,i)=>i))},{result:'A'.repeat(64)},{bundle:'../regions'},{bundle:'C:/regions'},{patch:'../patch'},{side:'auto'},{reduction:'auto'}])assert.throws(()=>regionRequest(draft,'meeting',{...form,...change}));
assert.throws(()=>regionRequest(draft,'missing',form));
const world=clone(draft);world.scene.contacts[0].target={space:'world',points_m:[[0,0,0]]};assert.throws(()=>regionRequest(world,'meeting',{...form,side:'partner'}));
for(const mutate of [v=>v.request.vertex_indices.reverse(),v=>v.patch.glb_sha256='b'.repeat(64),v=>v.patch.vertices.pop(),v=>v.patch.vertices[0]=[true,0,0],v=>v.patch.vertices[1]=v.patch.vertices[0],v=>v.binding.vertex_indices.reverse(),v=>v.binding.source.profile_sha256='bad',v=>v.binding.patch_sha256='bad',v=>v.binding.source.reference_pose='animated',v=>delete v.implementation_sha256['studio_material_patch.py'],v=>v.implementation_sha256.extra='bad',
 ...['animation_edited','motion_contacts_measured','engine_executed','human_reviewed','quality_approved','training_admitted','release_approved'].map(k=>v=>v[k]=true)]){const bad=clone(good);mutate(bad);assert.throws(()=>checkedRegion(bad,request));}

class Element{constructor(){this.value='';this.checked=false;this.disabled=false;this.children=[];this.textContent='';}replaceChildren(...items){this.children=items;this.value=items[0]?.value??'';}append(...items){this.children.push(...items);}}
const html=await readFile(new URL('../scripts/native-scene-editor.html',import.meta.url),'utf8');
function elements(){const nodes=new Map();for(const m of html.matchAll(/<[^>]*id="(nativeScene[^"]+)"[^>]*>/g)){assert(!nodes.has(m[1]));const n=new Element();n.value=m[0].match(/value="([^"]*)"/)?.[1]??'';nodes.set(m[1],n);}return {nodes,document:{getElementById:id=>nodes.get(id),createElement:()=>new Element()}};}
function fill(nodes){for(const [name,v]of Object.entries({Side:form.side,Bundle:form.bundle,Result:form.result,Patch:form.patch,Indices:form.indices,Reduction:form.reduction}))nodes.get('nativeSceneRegion'+name).value=v;}
for(const stale of ['draft','contact','form','clear']){
 const {nodes,document}=elements();fill(nodes);const el=n=>nodes.get('nativeSceneRegion'+n);let current=clone(draft),contact='meeting',reply,staged=null,status='';
 const widget=createMaterialPatchLoader({document,post:async(_,p)=>new Promise(r=>reply=()=>r(response(p))),getDraft:()=>current,getContact:()=>contact,stage:(...p)=>staged=p,status:s=>status=s,download:()=>{}});
 const pending=el('Load').onclick();assert(el('Load').disabled);await el('Load').onclick();assert(el('Load').disabled);assert.match(status,/Wait/);
 if(stale==='draft')current.geometry.limits.penetration_m=.004;
 if(stale==='contact')contact='changed';
 if(stale==='form')el('Indices').value='[0,1,2]';
 if(stale==='clear')widget.clear();
 reply();await pending;assert.equal(staged,null);assert.match(status,/changed/);assert(!el('Load').disabled);assert(el('Receipt').disabled);
}
{
 const {nodes,document}=elements();fill(nodes);let saved=null,staged=null;
 const el=n=>nodes.get('nativeSceneRegion'+n);
 const widget=createMaterialPatchLoader({document,post:async(_,p)=>response(p),getDraft:()=>draft,getContact:()=> 'meeting',stage:(...p)=>staged=p,status:()=>{},download:(...p)=>saved=p});
 await el('Load').onclick();assert.deepEqual(staged,['source',good.patch]);el('Receipt').onclick();assert.deepEqual(saved,[good,'saved-region-receipt.json']);
 widget.clear();assert(el('Receipt').disabled);
}
{
 const {nodes,document}=elements(),posts=[];let last=null;
 const editor=createNativeSceneEditor({document,api:async()=>({jobs:[]}),post:async(url,p)=>{posts.push([url,clone(p)]);if(url==='/api/native-scene-material-patch')return response(p);last=clone(p);throw Error('Captured preview request');},getContext:()=>({}),getPatch:()=>null,download:()=>{}});
 editor.bind(draft);fill(nodes);const el=n=>nodes.get('nativeScene'+n);el('RevisionContact').value='meeting';
 await el('RegionLoad').onclick();assert.deepEqual(editor.snapshot(),draft);
 el('RegionSide').value='partner';await el('RegionLoad').onclick();assert.deepEqual(editor.snapshot(),draft);
 await el('RevisionPreview').onclick();assert.equal(posts.at(-1)[0],'/api/native-scene-contact-revision');
 assert.deepEqual(last.contact_revision.baseline,draft);assert.deepEqual(last.scene.contacts[0].vertices,[[6,0,2],[6,0,0],[6,0,1]]);assert.deepEqual(last.scene.contacts[0].target.vertices,last.scene.contacts[0].vertices);
 assert.equal(last.scene.contacts[0].reduction,'individual');assert.equal(last.scene.contacts[0].target.reduction,'individual');assert.deepEqual(last.geometry,draft.geometry);
}
const integrated=await readFile(new URL('../scripts/action-studio.html',import.meta.url),'utf8');
for(const id of ['Side','Bundle','Result','Patch','Indices','Reduction','Load','Receipt','Summary'])assert.equal([...integrated.matchAll(new RegExp(`id="nativeSceneRegion${id}"`,'g'))].length,1);
console.log('Saved-region request/receipt checks, atomic partner staging, stale selections, double-click ownership and receipt downloads passed offline.');
