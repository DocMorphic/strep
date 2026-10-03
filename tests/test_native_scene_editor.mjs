import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {createNativeSceneEditor,triplet,contactFromPatch,emptyDraft} from '../scripts/native-scene-editor.mjs';
assert.deepEqual(triplet('1, 2, 3'),[1,2,3]);
for(const value of ['', 'NaN','Infinity'])assert.throws(()=>triplet(value,1));
assert.throws(()=>triplet('1,',2));
const code=await readFile(new URL('../scripts/character-contacts.js',import.meta.url),'utf8');
const sandbox={};vm.runInNewContext(code.slice(0,code.indexOf('function createRigContactEditor')),sandbox);
const references=sandbox.rigNativePatchReferences;
const primitives=[{node:7,primitive:0,vertex_offset:0,vertices:3},{node:8,primitive:1,vertex_offset:3,vertices:2}];
assert.equal(JSON.stringify(references(primitives,[4,0,3])),JSON.stringify([[8,1,1],[7,0,0],[8,1,0]]));
for(const ids of [[],[1,1],[5],[-1],[true]])assert.throws(()=>references(primitives,ids));
assert.throws(()=>references([...primitives,{node:9,primitive:0,vertex_offset:0,vertices:3}],[0]));
class Element{
 constructor(){this.value='';this.checked=false;this.disabled=false;this.children=[];this.textContent='';}
 replaceChildren(...items){this.children=items;this.value=items[0]?.value??'';}
 append(...items){this.children.push(...items);}
}
const html=await readFile(new URL('../scripts/native-scene-editor.html',import.meta.url),'utf8');
const nodes=new Map();for(const match of html.matchAll(/<[^>]*id="(nativeScene[^"]+)"[^>]*>/g)){
 assert(!nodes.has(match[1]));const node=new Element();node.value=match[0].match(/value="([^"]*)"/)?.[1]??'';nodes.set(match[1],node);
}
const el=name=>{assert(nodes.has('nativeScene'+name));return nodes.get('nativeScene'+name);};
for(const [id,value]of Object.entries({Shape:'box',TargetType:'object',Mode:'hold'}))el(id).value=value;
const context={job:{id:'parent'},variant:'transfer'};const metadata={source_url:'/files/rig-jobs/parent/transfer/character.glb',glb_sha256:'a'.repeat(64),duration_s:2,animation_index:0,label:'Procedural fixture'};
let patch={glb_sha256:metadata.glb_sha256,vertices:[[7,0,1],[8,1,0]]},waiting=null,posted=null,saved=null;
let jobs={jobs:[]},review={status:'processing',stage:'actors-engine',completed_stages:[{}],downloads:[]};
const doc={getElementById:id=>nodes.get(id),createElement:()=>new Element()};
const api=async url=>{
 if(url.startsWith('/api/native-scene-actor?'))return waiting||structuredClone(metadata);
 if(url==='/api/native-scene-jobs')return structuredClone(jobs);
 if(url.startsWith('/api/native-scene-review?'))return structuredClone(review);
 throw Error(url);
};
const editor=createNativeSceneEditor({document:doc,api,post:async(url,payload)=>{assert.equal(url,'/api/native-scene-assets');posted=structuredClone(payload);jobs={jobs:[{id:'job1'}]};return {id:'job1'};},getContext:()=>context,getPatch:()=>structuredClone(patch),download:value=>saved=value});
assert.equal(editor.snapshot().object_edit,null);assert.deepEqual(editor.snapshot().geometry.planes,{});
await el('AddActor').onclick();assert.equal(editor.snapshot().scene.duration_s,2);
assert.deepEqual(editor.snapshot().geometry.clock.times_s,[0,2]);
el('ActorName').value='B';el('ActorPosition').value='2, 0, 0';metadata.duration_s=3;await el('AddActor').onclick();assert.match(el('Status').textContent,/different durations/);assert.equal(Object.keys(editor.snapshot().scene.actors).length,1);
metadata.duration_s=2;let resolve;waiting=new Promise(r=>resolve=r);const stale=el('AddActor').onclick();context.variant='edited';resolve(metadata);await stale;assert.match(el('Status').textContent,/selection changed/);assert.equal(Object.keys(editor.snapshot().scene.actors).length,1);
context.variant='transfer';waiting=null;await el('AddActor').onclick();assert.equal(editor.snapshot().scene.actors.B.placement.translation_m[0],2);
await el('AddObject').onclick();assert.deepEqual(editor.snapshot().scene.objects.item.geometry.size_m,[.4,.4,.4]);
el('ContactActor').value='A';el('Target').value='item';el('ContactName').value='grip-A';el('Start').value='.8';el('End').value='1';el('Point').value='-.2, 0, 0';await el('AddContact').onclick();
assert.deepEqual(editor.snapshot().scene.contacts[0].vertices,patch.vertices);assert.deepEqual(editor.snapshot().scene.contacts[0].interval_s,[.8,1]);
patch.glb_sha256='b'.repeat(64);el('ContactName').value='wrong';await el('AddContact').onclick();assert.match(el('Status').textContent,/this character clip/);assert.equal(editor.snapshot().scene.contacts.length,1);patch.glb_sha256=metadata.glb_sha256;
el('ContactActor').value='B';el('ContactName').value='grip-B';await el('AddContact').onclick();
el('Fit').checked=true;el('FitObject').value='item';el('FirstGrip').value='grip-A';el('SecondGrip').value='grip-B';el('EditWindow').value='.6, 1.2';
await el('Save').onclick();assert.deepEqual(saved.object_edit.contact_ids,['grip-A','grip-B']);assert.equal(saved.object_edit.maximum_translation_m,.01);
el('TargetType').value='actor';el('TargetType').onchange();el('Target').value='B';await el('PartnerPatch').onclick();el('ContactActor').value='A';el('ContactName').value='high-five';el('Mode').value='touch';el('Mode').onchange();el('Start').value='1';el('End').value='';el('SpeedLimit').value='';await el('AddContact').onclick();
const meeting=editor.snapshot().scene.contacts[2];assert.deepEqual(meeting.target.vertices,patch.vertices);assert.deepEqual(meeting.interval_s,[1,1]);assert.deepEqual(meeting.limits,{position_m:.005});
el('TargetType').value='world';el('TargetType').onchange();el('ContactName').value='world-touch';el('Point').value='1, 2, 3';await el('AddContact').onclick();assert.deepEqual(editor.snapshot().scene.contacts[3].target.points_m,[[1,2,3]]);
const imported=editor.snapshot();imported.geometry.clock.times_s=[0,.123456789,2];imported.geometry.planes={floor:{normal_world:[1,0,0],offset_m:-3},wall:{normal_world:[0,0,1],offset_m:-2}};
const preciseLimit=.0021177467174925877;assert.notEqual(preciseLimit*1000/1000,preciseLimit);
imported.geometry.limits.penetration_m=preciseLimit;imported.object_edit.maximum_translation_m=preciseLimit;
editor.bind(imported);assert.equal(el('Floor').disabled,true);assert.deepEqual(editor.snapshot().geometry,imported.geometry);assert.deepEqual(editor.snapshot().object_edit,imported.object_edit);
await el('Build').onclick();assert.deepEqual(posted,editor.snapshot());assert.equal(el('Build').disabled,false);assert.equal(el('Jobs').value,'job1');
await el('Review').onclick();assert.match(el('Results').children[0].textContent,/actors-engine/);assert.equal(el('Results').children.length,1);
review={status:'complete',sampled_conditions_pass:false,source_contacts_pass:false,samples:1101,downloads:[{url:'/files/native-scene-jobs/job1/assets.zip',label:'Scene asset package'}]};
await el('Review').onclick();assert.match(el('Results').children[0].textContent,/conditions: fail/);assert.match(el('Results').children[0].textContent,/approval remain open/);assert.equal(el('Results').children[1].href,review.downloads[0].url);
assert.equal(context.variant,'transfer');assert.equal(context.job.id,'parent');
review={status:'failed',error:'Retained fixture failure',downloads:[]};await el('Review').onclick();assert.match(el('Results').children[0].textContent,/Retained fixture failure/);
const wrong=emptyDraft();wrong.scene.actors.A={sha256:'different'};assert.throws(()=>contactFromPatch(wrong,'A',patch,{}));
console.log('Native scene draft, patch, source selection, bounds and saved-result workflows passed offline.');
