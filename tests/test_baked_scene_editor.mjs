import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createBakedSceneEditor} from '../scripts/baked-scene-editor.mjs';
// Offline DOM/API doubles; no live browser, renderer or engine evidence.
class Element{constructor(){this.value='';this.children=[];this.textContent='';this.disabled=false;}replaceChildren(...items){this.children=items;this.value=items[0]?.value??'';}append(...items){this.children.push(...items);}}
const html=await readFile(new URL('../scripts/baked-scene-editor.html',import.meta.url),'utf8'),nodes=new Map();
for(const match of html.matchAll(/<[^>]*id="(bakedScene[^"]+)"[^>]*>/g)){assert(!nodes.has(match[1]));nodes.set(match[1],new Element());}
nodes.set('scenePropBakeJobs',new Element());nodes.get('scenePropBakeJobs').value='bake';
const el=name=>{assert(nodes.has('bakedScene'+name));return nodes.get('bakedScene'+name);},document={getElementById:id=>nodes.get(id),createElement:()=>new Element()};
const metadata={bake_job:'bake',source_result_sha256:'a'.repeat(64),source_baked_zip_sha256:'b'.repeat(64),source_scene_conditions_pass:false,exact_physical_event_timing_pass:false,quality_approved:false,release_approved:false};
let bindWaiting=null,reviewWaiting=null,postWaiting=null,posted=null,jobs={jobs:[]},review={id:'saved',status:'processing',stage:'headless audit',downloads:[]};
const api=async url=>{
 if(url.startsWith('/api/baked-scene-source?'))return bindWaiting||structuredClone(metadata);
 if(url==='/api/baked-scene-jobs')return structuredClone(jobs);
 if(url.startsWith('/api/baked-scene-review?'))return reviewWaiting||structuredClone(review);
 throw Error(url);
};
const post=async(url,payload)=>{assert.equal(url,'/api/baked-scene-assets');posted=structuredClone(payload);jobs={jobs:[{id:'saved',status:'starting'}]};return postWaiting||{id:'saved'};};
const editor=createBakedSceneEditor({document,api,post});assert.throws(()=>editor.snapshot(),/Bind/);
await el('Bind').onclick();assert.match(el('Status').textContent,/physical timing: fail/);
assert.deepEqual(editor.snapshot(),{bake_job:'bake',source_result_sha256:metadata.source_result_sha256});
await el('Build').onclick();assert.deepEqual(posted,editor.snapshot());assert.equal(nodes.get('scenePropBakeJobs').value,'bake');assert.equal(el('Jobs').value,'saved');assert.equal(el('Build').disabled,false);
await el('Review').onclick();assert.match(el('Results').children[0].textContent,/processing: headless audit/);
const labels=['runtime/baked-runtime.zip','runtime/result.json','audit/result.json','request.json','result.json'];
review={id:'saved',status:'complete',scene_playback_verified:true,exported_main_scene_verified:true,live_prop_physics:false,source_scene_conditions_pass:false,root_samples_pass:true,exact_physical_event_timing_pass:false,maximum_application_delay_s:.00625,source_end_hold_duration_s:.0073334,
 held_grip_sampled_conditions_pass:true,floor_sampled_screen_pass:null,default_30fps_import_pass:false,quality_approved:false,release_approved:false,downloads:labels.map(label=>({label,url:'/files/baked-scene-jobs/saved/'+label}))};
await el('Review').onclick();assert.equal(el('Results').children.length,6);const text=el('Results').children[0].textContent;
for(const pattern of [/7.333 ms/,/6.250 ms/,/Original scene: fail/,/ground screen: not measured/,/default 30 FPS import: fail/,/No live prop physics/,/unapproved/])assert.match(text,pattern);
for(const field of ['scene_playback_verified','exported_main_scene_verified','live_prop_physics','quality_approved','release_approved']){
 const original=review[field];review[field]=!original;await el('Review').onclick();assert.match(el('Status').textContent,/Invalid saved-scene/);assert.equal(el('Results').children.length,0);review[field]=original;
}
review.downloads[0].url='https://example.test';await el('Review').onclick();assert.match(el('Status').textContent,/Invalid saved-scene downloads/);assert.equal(el('Results').children.length,0);
review={id:'saved',status:'failed',error:'Retained playback failure',downloads:[{url:'/do-not-show'}]};await el('Review').onclick();assert.equal(el('Results').children.length,1);assert.match(el('Status').textContent,/Retained playback failure/);
nodes.get('scenePropBakeJobs').value='other';posted=null;await el('Build').onclick();assert.equal(posted,null);assert.match(el('Status').textContent,/Bind/);
nodes.get('scenePropBakeJobs').value='bake';let resolveBind;bindWaiting=new Promise(r=>resolveBind=r);const pendingBind=el('Bind').onclick();nodes.get('scenePropBakeJobs').value='other';resolveBind(metadata);await pendingBind;assert.throws(()=>editor.snapshot(),/Bind/);
bindWaiting=null;nodes.get('scenePropBakeJobs').value='bake';await el('Bind').onclick();
let resolvePost;postWaiting=new Promise(r=>resolvePost=r);const pendingPost=el('Build').onclick();assert.equal(el('Build').disabled,true);await el('Build').onclick();assert.match(el('Status').textContent,/Wait/);resolvePost({id:'saved'});await pendingPost;assert.equal(el('Build').disabled,false);postWaiting=null;
let resolveReview;reviewWaiting=new Promise(r=>resolveReview=r);const pendingReview=el('Review').onclick();el('Jobs').value='other';resolveReview(review);await pendingReview;assert.match(el('Status').textContent,/review selection changed/);
metadata.source_baked_zip_sha256='invalid';await el('Bind').onclick();assert.match(el('Status').textContent,/Invalid saved-scene source/);assert.throws(()=>editor.snapshot(),/Bind/);
console.log('Offline saved-scene source binding, preserved failures/end holds, fixed downloads, stale replies and busy lifecycle passed.');
