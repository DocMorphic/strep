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
console.log('Native character bounds, failed review, atomic staging, stale-response and continuation workflows passed offline.');
