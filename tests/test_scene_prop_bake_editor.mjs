import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createScenePropBakeEditor} from '../scripts/scene-prop-bake-editor.mjs';

// Offline DOM/API double; no live browser, model, engine or GPU evidence.
class Element{
 constructor(){this.value='';this.children=[];this.textContent='';this.disabled=false;}
 replaceChildren(...items){this.children=items;this.value=items[0]?.value??'';}
 append(...items){this.children.push(...items);}
}
const html=await readFile(new URL('../scripts/scene-prop-bake-editor.html',import.meta.url),'utf8'),nodes=new Map();
for(const match of html.matchAll(/<[^>]*id="(scenePropBake[^"]+)"[^>]*>/g)){
 assert(!nodes.has(match[1]));const node=new Element();node.value=match[0].match(/value="([^"]*)"/)?.[1]??'';nodes.set(match[1],node);
}
nodes.set('scenePropRuntimeJobs',new Element());nodes.get('scenePropRuntimeJobs').value='runtime';
const el=name=>{assert(nodes.has('scenePropBake'+name));return nodes.get('scenePropBake'+name);};
const document={getElementById:id=>nodes.get(id),createElement:()=>new Element()};
const metadata={runtime_job:'runtime',source_result_sha256:'a'.repeat(64),source_runtime_zip_sha256:'b'.repeat(64),physics_fps:120,source_scene_conditions_pass:false,root_samples_pass:true,quality_approved:false,release_approved:false};
let bindWaiting=null,reviewWaiting=null,postWaiting=null,posted=null,saved=null,jobs={jobs:[]},review={id:'bake1',status:'processing',stage:'offline bake',downloads:[]};
const api=async url=>{
 if(url.startsWith('/api/scene-prop-bake-source?'))return bindWaiting||structuredClone(metadata);
 if(url==='/api/scene-prop-bake-jobs')return structuredClone(jobs);
 if(url.startsWith('/api/scene-prop-bake-review?'))return reviewWaiting||structuredClone(review);
 throw Error(url);
};
const post=async(url,payload)=>{assert.equal(url,'/api/scene-prop-bake-assets');posted=structuredClone(payload);jobs={jobs:[{id:'bake1',status:'starting'}]};return postWaiting||{id:'bake1'};};
const editor=createScenePropBakeEditor({document,api,post,download:v=>saved=structuredClone(v)});
assert.throws(()=>editor.snapshot(),/Bind/);await el('Bind').onclick();assert.match(el('Status').textContent,/scene conditions: fail/);
assert.throws(()=>editor.snapshot(),/ground/);el('Floor').value='plane';el('Y').value='2';el('RY').value='30';
const payload=editor.snapshot();assert.equal(payload.request.floor.enabled,true);assert.equal(payload.source_result_sha256,metadata.source_result_sha256);
assert.equal(payload.request.source_runtime_zip_sha256,metadata.source_runtime_zip_sha256);assert.equal(payload.request.parent_world_transform[1][3],2);
assert(Math.abs(payload.request.parent_world_transform[0][2]-.5)<1e-12);
el('Friction').value='';assert.throws(()=>editor.snapshot(),/friction/);el('Friction').value='1.1';assert.throws(()=>editor.snapshot(),/friction/);el('Friction').value='.6';
el('Height').value='10001';assert.throws(()=>editor.snapshot(),/height/);el('Height').value='0';el('Floor').value='none';assert.equal(editor.snapshot().request.floor.enabled,false);
await el('Save').onclick();assert.deepEqual(saved,editor.snapshot());await el('Build').onclick();assert.deepEqual(posted,saved);
assert.equal(nodes.get('scenePropRuntimeJobs').value,'runtime');assert.equal(el('Jobs').value,'bake1');assert.equal(el('Build').disabled,false);
await el('Review').onclick();assert.match(el('Results').children[0].textContent,/processing: offline bake/);assert.equal(el('Results').children.length,1);
const labels=['bake/baked-assets.zip','bake-request.json','bake/result.json','result.json'];
review={id:'bake1',status:'complete',source_scene_conditions_pass:false,root_samples_pass:true,engine_import_verified:true,exact_physical_event_timing_pass:false,maximum_application_delay_s:.00625,
 held_grip_sampled_conditions_pass:false,floor_sampled_screen_pass:null,default_30fps_import_pass:false,quality_approved:false,release_approved:false,
 downloads:labels.map(label=>({label,url:'/files/scene-prop-bake-jobs/bake1/'+label}))};
await el('Review').onclick();assert.equal(el('Results').children.length,5);assert.match(el('Results').children[0].textContent,/6.250 ms/);
assert.match(el('Results').children[0].textContent,/grip agreement: fail/);assert.match(el('Results').children[0].textContent,/ground screen: not measured/);
assert.match(el('Results').children[0].textContent,/not approved/);assert.equal(el('Results').children[1].href,review.downloads[0].url);
review.downloads[0].url='https://example.test';await el('Review').onclick();assert.match(el('Status').textContent,/Invalid bake downloads/);assert.equal(el('Results').children.length,0);
review.downloads[0].url='/files/scene-prop-bake-jobs/bake1/'+labels[0];review.quality_approved=true;
await el('Review').onclick();assert.match(el('Status').textContent,/Invalid completed/);assert.equal(el('Results').children.length,0);
review={id:'bake1',status:'failed',error:'Retained capture failure',downloads:[{url:'/do-not-show'}]};await el('Review').onclick();assert.equal(el('Results').children.length,1);assert.match(el('Status').textContent,/Retained capture failure/);
nodes.get('scenePropRuntimeJobs').value='other';posted=null;await el('Build').onclick();assert.equal(posted,null);assert.match(el('Status').textContent,/Bind/);
nodes.get('scenePropRuntimeJobs').value='runtime';let resolveBind;bindWaiting=new Promise(r=>resolveBind=r);const pendingBind=el('Bind').onclick();nodes.get('scenePropRuntimeJobs').value='other';resolveBind(metadata);await pendingBind;
assert.throws(()=>editor.snapshot(),/Bind/);bindWaiting=null;nodes.get('scenePropRuntimeJobs').value='runtime';await el('Bind').onclick();
let resolvePost;postWaiting=new Promise(r=>resolvePost=r);const pendingPost=el('Build').onclick();assert.equal(el('Build').disabled,true);await el('Build').onclick();assert.match(el('Status').textContent,/Wait/);resolvePost({id:'bake1'});await pendingPost;assert.equal(el('Build').disabled,false);postWaiting=null;
let resolveReview;reviewWaiting=new Promise(r=>resolveReview=r);const pendingReview=el('Review').onclick();el('Jobs').value='another';resolveReview(review);await pendingReview;assert.match(el('Status').textContent,/review selection changed/);reviewWaiting=null;
metadata.source_runtime_zip_sha256='invalid';await el('Bind').onclick();assert.match(el('Status').textContent,/Invalid bound/);assert.throws(()=>editor.snapshot(),/Bind/);
console.log('Offline source-bound prop bake drafts, fixed downloads, preserved failure/N-A review, stale response guards and busy request lifecycle passed.');
