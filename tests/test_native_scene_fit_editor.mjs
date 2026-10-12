import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createNativeSceneFitEditor,stagedScene} from '../scripts/native-scene-fit-editor.mjs';
class Element{
 constructor(){this.value='';this.disabled=false;this.checked=false;this.children=[];this.style={};this.textContent='';}
 replaceChildren(...items){this.children=items;if(items[0]?.value!==undefined)this.value=items[0].value;}
 append(...items){this.children.push(...items);}
}
const html=await readFile(new URL('../scripts/native-scene-fit-editor.html',import.meta.url),'utf8');
const nodes=new Map();for(const m of html.matchAll(/<[^>]*id="(nativeSceneFit[^"]+)"[^>]*>/g)){
 assert(!nodes.has(m[1]));const n=new Element();n.value=m[0].match(/value="([^"]*)"/)?.[1]??'';nodes.set(m[1],n);
}
const el=n=>{assert(nodes.has('nativeSceneFit'+n));return nodes.get('nativeSceneFit'+n);};
const document={getElementById:id=>nodes.get(id),createElement:()=>new Element(),createTextNode:text=>({textContent:text})};
const sourceActor=()=>({glb:'/files/rig-jobs/source/transfer/clip.glb',sha256:'a'.repeat(64),animation_index:0,placement:{translation_m:[0,0,0],rotation_xyzw:[0,0,0,1]}});
let draft={schema:'strep-studio-native-scene-v1',scene:{duration_s:2,actors:{A:sourceActor(),B:sourceActor()},objects:{},contacts:[]},geometry:{clock:{mode:'explicit',times_s:[0,2]},limits:{penetration_m:.005},planes:{}},object_edit:null};
const original=structuredClone(draft);
const channels=[{node:0,name:'root',path:'rotation',eligible:true,keys:11,reason:null},{node:0,name:'root',path:'translation',eligible:true,keys:11,reason:null},{node:1,name:'static',path:'rotation',eligible:false,keys:null,reason:'No native channel'}];
let catalog={schema:'strep-studio-native-scene-fit-catalog-v1',duration_s:2,actors:{A:{sha256:'a'.repeat(64),channels},B:{sha256:'a'.repeat(64),channels}},maximum_controls:96,quality_approved:false};
let saved,posted,review,waiting=null,posting=null,submissions=0,bindings=0;
const api=async url=>{
 if(url==='/api/native-scene-fit-jobs')return {jobs:[{id:'job1',status:'complete'},{id:'failed',status:'failed'}]};
 if(waiting)return waiting;return structuredClone(review);
};
const post=async(url,value)=>{
 if(url==='/api/native-scene-fit-catalog')return waiting??structuredClone(catalog);
 assert.equal(url,'/api/native-scene-fits');submissions++;posted=structuredClone(value);return posting??{id:'job1'};
};
const editor=createNativeSceneFitEditor({document,api,post,getDraft:()=>structuredClone(draft),setDraft:value=>{draft=structuredClone(value);bindings++;},download:value=>saved=value});
await el('Load').onclick();assert.equal(el('Tracks').children.length,3);assert.equal(el('Tracks').children[2].children[0].disabled,true);
assert.throws(()=>editor.request(),/Save bounds/);
const select=(i,value)=>{const row=el('Tracks').children[i];row.children[0].checked=true;row.children[0].onchange();row.children[2].value=String(value);};
select(0,20);select(1,50);await el('SaveActor').onclick();await el('Save').onclick();
assert.equal(saved.actors.A.tracks[0].maximum_change,20);assert.equal(saved.actors.A.tracks[1].maximum_change,.05);
assert.equal(saved.resume_from,null);assert.deepEqual(draft,original);
el('Window').value='1, 0';await el('SaveActor').onclick();assert.match(el('Status').textContent,/ordered/);
el('Window').value='0, 2';el('Protected').value='[[true, 1]]';await el('SaveActor').onclick();assert.match(el('Status').textContent,/ordered/);el('Protected').value='[]';
el('Knots').value='0, 1, 1, 2';await el('SaveActor').onclick();assert.match(el('Status').textContent,/ordered/);el('Knots').value='0, .6, 1.4, 2';
el('Actor').value='B';el('Actor').onchange();select(0,15);await el('SaveActor').onclick();assert.deepEqual(Object.keys(editor.request().actors),['A','B']);
let resolvePost;posting=new Promise(r=>resolvePost=r);const pending=el('Build').onclick();await el('Build').onclick();assert.match(el('Status').textContent,/Wait/);assert.equal(submissions,1);
resolvePost({id:'job1'});await pending;posting=null;assert.equal(el('Build').disabled,false);assert.equal(el('Jobs').value,'job1');assert.deepEqual(posted.draft,original);
const makeReview=()=>({id:'job1',status:'complete',native_conditions_pass:true,geometry_conditions_pass:true,quality_approved:false,original_selected:true,authoring_request:structuredClone(posted),
 actors:Object.fromEntries(['A','B'].map(n=>[n,{original_url:`/files/native-scene-fit-jobs/job1/input/${n}.glb`,original_sha256:'a'.repeat(64),candidate_url:`/files/native-scene-fit-jobs/job1/fit/probes/final/${n}.glb`,candidate_sha256:(n==='A'?'b':'c').repeat(64),correction_requested:true}])),
 downloads:['A','B'].map(n=>({label:`Proposal ${n}`,url:`/files/native-scene-fit-jobs/job1/fit/probes/final/${n}.glb`,sha256:(n==='A'?'b':'c').repeat(64)}))});
review=makeReview();const staging=stagedScene(review);assert.equal(staging.scene.actors.A.sha256,'b'.repeat(64));assert.equal(staging.scene.actors.B.sha256,'c'.repeat(64));assert.deepEqual(draft,original);
for(const fault of ['native','geometry','approval','actor','hash','download','traversal','query','job-id']){
 const value=makeReview();
 if(fault==='native')value.native_conditions_pass=false;
 if(fault==='geometry')value.geometry_conditions_pass=false;
 if(fault==='approval')value.quality_approved=true;
 if(fault==='actor')delete value.actors.B;
 if(fault==='hash')value.actors.A.candidate_sha256='0'.repeat(64);
 if(fault==='download')value.downloads.pop();
 if(fault==='job-id')value.id='..';
 if(['traversal','query'].includes(fault)){value.actors.A.candidate_url+=fault==='query'?'?x=1':'/../other';value.downloads[0].url=value.actors.A.candidate_url;}
 assert.throws(()=>stagedScene(value));
}
review.native_conditions_pass=false;await el('Review').onclick();assert.equal(el('Stage').disabled,true);assert.match(el('Status').textContent,/fail/);assert.deepEqual(draft,original);
review=makeReview();await el('Review').onclick();assert.equal(el('Stage').disabled,false);
let resolve;waiting=new Promise(r=>resolve=r);const stage=el('Stage').onclick();draft.scene.actors.B.placement.translation_m=[4,0,0];resolve(review);await stage;waiting=null;assert.equal(bindings,0);assert.match(el('Status').textContent,/changed/);
draft=structuredClone(original);await el('Review').onclick();await el('Stage').onclick();assert.equal(bindings,1);assert.deepEqual(draft,staging);assert.throws(()=>editor.request(),/Scene changed/);
draft=structuredClone(original);await el('Load').onclick();select(0,20);await el('SaveActor').onclick();
waiting=new Promise(r=>resolve=r);const loading=el('Load').onclick();draft.scene.actors.A.sha256='d'.repeat(64);resolve(catalog);await loading;waiting=null;assert.match(el('Status').textContent,/Scene changed/);assert.throws(()=>editor.request(),/Scene changed/);
draft=structuredClone(original);el('Resume').value='job1';review=makeReview();await el('LoadResume').onclick();assert.equal(editor.request().resume_from,'job1');assert.deepEqual(editor.request().actors,posted.actors);assert.deepEqual(draft,posted.draft);
waiting=new Promise(r=>resolve=r);const oldResume=el('LoadResume').onclick();el('Resume').value='other';resolve(review);await oldResume;waiting=null;assert.match(el('Status').textContent,/selection or scene changed/);
await editor.refresh();assert.deepEqual(el('Resume').children.map(n=>n.value),['','job1']);
draft=structuredClone(original);el('Resume').value='';await editor.load();el('Actor').value='A';el('Actor').onchange();select(0,20);
const speedInput=el('Tracks').children[0].children[4];assert.equal(speedInput.value,'');assert.match(speedInput.ariaLabel,/degrees per second/);
speedInput.value='120';await el('SaveActor').onclick();let speedRequest=editor.request();
assert.equal(speedRequest.schema,'strep-studio-native-scene-fit-v2');assert.deepEqual(speedRequest.rotation_speed_limits,[{actor:'A',node:0,maximum_degrees_per_second:120}]);
speedInput.value='-1';await el('SaveActor').onclick();assert.match(el('Status').textContent,/finite and nonnegative/);assert.equal(editor.request().rotation_speed_limits[0].maximum_degrees_per_second,120);
speedInput.value='';await el('SaveActor').onclick();assert.equal(editor.request().schema,'strep-studio-native-scene-fit-v1');assert(!('rotation_speed_limits' in editor.request()));
speedInput.value='0';await el('SaveActor').onclick();assert.equal(editor.request().rotation_speed_limits[0].maximum_degrees_per_second,0);
speedInput.value='120';await el('SaveActor').onclick();posted=editor.request();review=makeReview();review.rotation_speed_conditions_pass=true;
assert.deepEqual(stagedScene(review).scene.actors.A.sha256,'b'.repeat(64));
assert.equal(stagedScene(review).schema,'strep-studio-native-scene-v2');
assert.deepEqual(stagedScene(review).rotation_speed_limits,posted.rotation_speed_limits);
const inherited=structuredClone(review);inherited.authoring_request.draft.schema='strep-studio-native-scene-v2';
inherited.authoring_request.draft.rotation_speed_limits=[{actor:'A',node:0,maximum_degrees_per_second:5},{actor:'B',node:0,maximum_degrees_per_second:0}];
assert.deepEqual(stagedScene(inherited).rotation_speed_limits,[{actor:'A',node:0,maximum_degrees_per_second:120},{actor:'B',node:0,maximum_degrees_per_second:0}]);
for(const where of ['draft','request']){const invalid=structuredClone(inherited);const tracks=where==='draft'?invalid.authoring_request.draft.rotation_speed_limits:invalid.authoring_request.rotation_speed_limits;tracks.push(structuredClone(tracks[0]));assert.throws(()=>stagedScene(invalid),/once/);}
for(const pass of [false,undefined,'true']){const failed=structuredClone(review);failed.rotation_speed_conditions_pass=pass;assert.throws(()=>stagedScene(failed),/turning-speed/);}
el('Resume').value='job1';await el('LoadResume').onclick();assert.deepEqual(editor.request().rotation_speed_limits,posted.rotation_speed_limits);
assert.equal(el('Tracks').children[0].children[4].value,120);
// Clearance mode keeps the full source request and restores its bound mode.
el('Mode').value='clearance';el('Mode').onchange();assert.equal(el('RepairOptions').hidden,false);
el('RepairStages').value='2';el('RepairProbes').value='8';posted=editor.request();
assert.equal(posted.schema,'strep-studio-native-scene-fit-v3');assert.deepEqual(posted.export_repair,{stages:2,probes:8});
assert.deepEqual(posted.rotation_speed_limits,[{actor:'A',node:0,maximum_degrees_per_second:120}]);
for(const [name,value] of [['RepairStages','0'],['RepairStages','9'],['RepairProbes','0'],['RepairProbes','65'],['RepairProbes','1.5']]){
 const previous=el(name).value;el(name).value=value;assert.throws(()=>editor.request(),/export stages/);el(name).value=previous;
}
review=makeReview();review.rotation_speed_conditions_pass=true;assert.equal(stagedScene(review).schema,'strep-studio-native-scene-v2');
review.geometry_conditions_pass=false;await el('Review').onclick();assert.equal(el('Stage').disabled,true);assert.match(el('Status').textContent,/geometry: fail/);
review=makeReview();review.rotation_speed_conditions_pass=true;el('Mode').value='contacts';el('RepairStages').value='8';
el('Resume').value='job1';await el('LoadResume').onclick();assert.equal(el('Mode').value,'clearance');
assert.equal(el('RepairStages').value,2);assert.equal(el('RepairProbes').value,8);assert.deepEqual(editor.request(),posted);
el('Mode').value='contacts';el('Mode').onchange();assert.equal(el('RepairOptions').hidden,true);
// Mixed clearance explicitly budgets clip edges and restores their acknowledgment.
el('Mode').value='clearance-components';el('Mode').onchange();assert.equal(el('BoundaryOptions').hidden,false);
el('BoundaryStart').checked=true;el('BoundaryStart').onchange();el('BoundaryEnd').checked=true;el('BoundaryEnd').onchange();
await el('SaveActor').onclick();assert.throws(()=>editor.request(),/Acknowledge review/);
el('BoundaryAck').checked=true;posted=editor.request();assert.equal(posted.schema,'strep-studio-native-scene-fit-v4');
assert.deepEqual(posted.boundary_keys.A,{start:'edit',end:'edit'});assert.deepEqual(posted.boundary_keys.B,{start:'preserve',end:'preserve'});
assert.equal(posted.acknowledge_changed_boundary_compatibility,true);assert.match(el('Budget').textContent,/2 clip edges/);
review=makeReview();review.rotation_speed_conditions_pass=true;assert.equal(stagedScene(review).schema,'strep-studio-native-scene-v2');
for(const fault of ['ack','actor','mode']){const bad=structuredClone(review);
 if(fault==='ack')bad.authoring_request.acknowledge_changed_boundary_compatibility=false;
 else if(fault==='actor')delete bad.authoring_request.boundary_keys.B;
 else bad.authoring_request.boundary_keys.A.start='other';
 assert.throws(()=>stagedScene(bad),/clip edges|clip-edge/);
}
el('Mode').value='contacts';el('Mode').onchange();assert.throws(()=>editor.request(),/Clip-edge edits require/);
el('Resume').value='job1';await el('LoadResume').onclick();assert.equal(el('Mode').value,'clearance-components');
assert.equal(el('BoundaryStart').checked,true);assert.equal(el('BoundaryEnd').checked,true);assert.equal(el('BoundaryAck').checked,true);
assert.deepEqual(editor.request(),posted);review.geometry_conditions_pass=false;await el('Review').onclick();assert.equal(el('Stage').disabled,true);
// Live timing changes count the current actor once; oversized saves remain atomic.
{
 const capacityNodes=new Map();for(const m of html.matchAll(/<[^>]*id="(nativeSceneFit[^"]+)"[^>]*>/g)){
  const n=new Element();n.value=m[0].match(/value="([^"]*)"/)?.[1]??'';capacityNodes.set(m[1],n);
 }
 const c=n=>capacityNodes.get('nativeSceneFit'+n),d={getElementById:id=>capacityNodes.get(id),createElement:()=>new Element(),createTextNode:text=>({textContent:text})};
 const many=Array.from({length:9},(_,node)=>({node,name:`joint ${node}`,path:'rotation',eligible:true,keys:11,reason:null}));
 const capacityCatalog={...catalog,actors:{A:{sha256:'a'.repeat(64),channels:many},B:{sha256:'a'.repeat(64),channels:many}}};
 const current=createNativeSceneFitEditor({document:d,api,post:async()=>structuredClone(capacityCatalog),getDraft:()=>structuredClone(original),setDraft:()=>assert.fail('No draft adoption'),download:()=>{}});
 const check=(index,on=true)=>{const box=c('Tracks').children[index].children[0];box.checked=on;box.onchange();};
 await current.load();assert.match(c('Budget').textContent,/0 controls/);
 for(let i=0;i<4;i++)check(i);
 c('Knots').value='0, .2, .4, .6, .8, 1, 1.5, 2';c('Knots').oninput();
 assert.match(c('Budget').textContent,/72 controls/);assert.match(c('Budget').textContent,/Scene after saving: 72 \/ 96/);
 await c('SaveActor').onclick();assert.equal(current.request().actors.A.knots_s.length,8);
 c('Actor').value='B';c('Actor').onchange();for(let i=0;i<4;i++)check(i);
 assert.match(c('Budget').textContent,/Scene after saving: 96 \/ 96/);
 await c('SaveActor').onclick();assert.equal(current.request().actors.B.tracks.length,4);
 const validRequest=current.request();
 check(4);assert.match(c('Budget').textContent,/Scene after saving: 102 \/ 96/);
 assert.match(c('Budget').textContent,/Saved scene: 96 \/ 96/);
 c('Tracks').children[4].children[4].value='250';
 await c('SaveActor').onclick();assert.match(c('Status').textContent,/102 controls/);
 assert.deepEqual(current.request(),validRequest);  // Failed save cannot change speed intent either.
 c('Actor').value='A';c('Actor').onchange();c('Knots').value='0, .2, .4, .6, .8, 1, 1.2, 1.5, 2';c('Knots').oninput();
 assert.match(c('Budget').textContent,/Scene after saving: 108 \/ 96/);
 await c('SaveActor').onclick();assert.match(c('Status').textContent,/Saved bounds stay unchanged/);
 assert.equal(current.request().actors.A.knots_s.length,8);
 c('Knots').value='0, 1, 1, 2';c('Knots').oninput();assert.match(c('Budget').textContent,/ordered/);
 c('Actor').value='B';c('Actor').onchange();await c('RemoveActor').onclick();
 assert.match(c('Budget').textContent,/Scene after saving: 72 \/ 96/);
 assert.deepEqual(Object.keys(current.request().actors),['A']);
 // Edge capacity participates in the same atomic save guard.
 c('Actor').value='A';c('Actor').onchange();c('Mode').value='clearance-components';c('Mode').onchange();
 c('BoundaryStart').checked=true;c('BoundaryStart').onchange();c('BoundaryEnd').checked=true;c('BoundaryEnd').onchange();
 assert.match(c('Budget').textContent,/96 controls/);await c('SaveActor').onclick();c('BoundaryAck').checked=true;
 const edgeRequest=current.request();assert.equal(edgeRequest.acknowledge_changed_boundary_compatibility,true);
 check(4);assert.match(c('Budget').textContent,/120 controls/);await c('SaveActor').onclick();
 assert.match(c('Status').textContent,/Saved bounds stay unchanged/);assert.deepEqual(current.request(),edgeRequest);
}
// Two-key native channels are selectable only with explicit edge authoring.
{
 const map=new Map();for(const m of html.matchAll(/<[^>]*id="(nativeSceneFit[^"]+)"[^>]*>/g)){const n=new Element();n.value=m[0].match(/value="([^"]*)"/)?.[1]??'';map.set(m[1],n);}
 const c=n=>map.get('nativeSceneFit'+n),d={getElementById:id=>map.get(id),createElement:()=>new Element(),createTextNode:text=>({textContent:text})};
 const two={...catalog,actors:{A:{sha256:'a'.repeat(64),channels:[{...channels[0],keys:2,eligible:false,clip_edge_eligible:true}]},B:{sha256:'a'.repeat(64),channels:[]}}};
 const current=createNativeSceneFitEditor({document:d,api,post:async()=>structuredClone(two),getDraft:()=>structuredClone(original),setDraft:()=>assert.fail('No adoption'),download:()=>{}});
 await current.load();const box=c('Tracks').children[0].children[0];assert.equal(box.disabled,true);
 c('Mode').value='clearance-components';c('Mode').onchange();assert.equal(box.disabled,false);box.checked=true;box.onchange();
 await c('SaveActor').onclick();assert.match(c('Status').textContent,/editable actual clip edge/);
 c('BoundaryStart').checked=true;c('BoundaryStart').onchange();await c('SaveActor').onclick();c('BoundaryAck').checked=true;
 assert.equal(current.request().boundary_keys.A.start,'edit');c('Mode').value='contacts';c('Mode').onchange();assert.equal(box.disabled,true);
 assert.throws(()=>current.request(),/Clip-edge edits require/);
}
console.log('Native bounds, timing capacity, speed requests and continuation, failed review, atomic staging and stale-response workflows passed offline.');
