import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createSurfaceExportEditor,validatePolicy,checkedDownloads} from '../scripts/surface-export-editor.mjs';

class Element{constructor(){this.value='';this.disabled=false;this.checked=false;this.children=[];this.textContent='';}replaceChildren(...c){this.children=c;if(c[0]?.value!==undefined)this.value=c[0].value;}append(...c){this.children.push(...c);}}
const html=await readFile(new URL('../scripts/surface-export-editor.html',import.meta.url),'utf8'),nodes=new Map();
for(const m of html.matchAll(/<[^>]*id="(surfaceExport[^"]+)"[^>]*>/g)){assert(!nodes.has(m[1]));nodes.set(m[1],new Element());}
const el=n=>{assert(nodes.has('surfaceExport'+n));return nodes.get('surfaceExport'+n);};
const document={getElementById:id=>nodes.get(id),createElement:()=>new Element()};
const policy={limits:{maximum_opposition_error_degrees:1,backface_allowance_m:.00005,minimum_normal_area_m2:1e-12,minimum_normal_coherence:.1},maximum_actor_pose_queries:20000,contacts:{box:{target_normal:{space:'object',normals:[[0,1,0]]}},feet:{target_normal:{space:'world',normals:[[0,1,0],[0,1,0]]}},partner:{target_normal:{space:'partner-surface'}}}};
let source={schema:'strep-studio-surface-export-source-v1',source:{kind:'scene',job:'s1',result_sha256:'1'.repeat(64)},normal_origins_sha256:'2'.repeat(64),package_sha256:'3'.repeat(64),contacts_sha256:'4'.repeat(64),portable_scene_sha256:'5'.repeat(64),scene:{duration_s:2,actors:{A:{sha256:'a'.repeat(64),animation_index:1},B:{sha256:'b'.repeat(64),animation_index:0}},contacts:[{id:'box',reduction:'centroid',vertices:[[0,0,1],[0,0,2]],target:{space:'object'}},{id:'feet',reduction:'points',vertices:[[0,0,3],[0,0,4]],target:{space:'world'}},{id:'partner',reduction:'centroid',vertices:[[0,0,5]],target:{space:'actor'}}]},normal_origins:[{job:'origin'}],inherited_surface:structuredClone(policy),scene_conditions_pass:true,root_event_tracks_included:false,quality_approved:false,release_approved:false};
let review,waiting=null,posting=null,posts=0,saved,posted;
const api=async url=>{
 if(['/api/native-scene-jobs','/api/native-scene-game-jobs'].includes(url))return {jobs:[{id:'s1',status:'complete'},{id:'bad',status:'failed'}]};
 if(url==='/api/surface-export-jobs')return {jobs:[{id:'out1',status:'complete'}]};
 if(waiting)return waiting;
 return structuredClone(url.startsWith('/api/surface-export-source?')?source:review);
};
const post=async(url,p)=>{assert.equal(url,'/api/surface-export-assets');posts++;posted=structuredClone(p);return posting??{id:'out1'};};
el('Kind').value='scene';
const editor=createSurfaceExportEditor({document,api,post,download:v=>saved=structuredClone(v)});
await editor.refresh();assert.deepEqual(el('Source').children.map(n=>n.value),['s1']);assert.throws(()=>editor.request(),/Bind/);
await editor.bind();assert.deepEqual(JSON.parse(el('Policy').value),policy);assert.equal(el('Revise').disabled,false);
await el('Save').onclick();assert.equal(saved.source.result_sha256,source.source.result_sha256);assert.equal(saved.normal_revision,null);
saved.source.job='mutated-copy';assert.equal(editor.request().source.job,'s1');
for(const mutate of [p=>p.extra=true,p=>p.maximum_actor_pose_queries=true,p=>p.maximum_actor_pose_queries=20001,p=>p.limits.maximum_opposition_error_degrees=Infinity,p=>p.contacts.feet.target_normal.normals.pop(),p=>p.contacts.box.target_normal.normals=[[0,2,0]],p=>p.contacts.partner.target_normal={space:'world',normals:[[0,1,0]]},p=>delete p.contacts.box,p=>p.contacts.extra=p.contacts.box]){const bad=structuredClone(policy);mutate(bad);assert.throws(()=>validatePolicy(bad,source.scene));}
const changed=structuredClone(policy);changed.limits.maximum_opposition_error_degrees=30;el('Policy').value=JSON.stringify(changed);assert.throws(()=>editor.request(),/separate normal intent/);
el('Revise').checked=true;assert.throws(()=>editor.request(),/reason/);el('Notes').value='Explicit fixture explores different normal intent.';assert.equal(editor.request().normal_revision.notes,el('Notes').value);
el('Policy').value=JSON.stringify(policy);assert.throws(()=>editor.request(),/Unchanged/);el('Revise').checked=false;
let resolve;waiting=new Promise(r=>resolve=r);const buildStale=el('Build').onclick();await Promise.resolve();el('Policy').value=JSON.stringify(changed);el('Revise').checked=true;resolve(structuredClone(source));await buildStale;waiting=null;assert.equal(posts,0);assert.match(el('Status').textContent,/changed/);el('Policy').value=JSON.stringify(policy);el('Revise').checked=false;
posting=new Promise(r=>resolve=r);const building=el('Build').onclick();await Promise.resolve();await Promise.resolve();assert.equal(el('Build').disabled,true);await el('Build').onclick();assert.equal(posts,1);resolve({id:'out1'});await building;posting=null;assert.equal(el('Build').disabled,false);assert.equal(posted.normal_revision,null);
const flags=['quality_approved','release_approved','training_admitted','human_reviewed','anatomical_reviewed','physics_verified','continuous_collision_certified','real_time_playback_verified','gpu_render_checked','studio_selection_changed'];
const fixed=['result.json','audit/result.json','replay.json','source.json','surface-policy.json','checked-assets.zip','surface-gate.json','portable-surface-policy.json'];
review={id:'out1',status:'complete',result_sha256:'6'.repeat(64),source:source.source,original_selected:true,checked_package_available:true,all_declared_scene_and_surface_samples_pass:true,scene_conditions_pass:true,point_conditions_pass:true,surface_conditions_pass:true,root_event_conditions_pass:true,root_event_tracks_included:false,normal_intent_revised:false,new_engine_executed:false,engine_queries_reused:true,...Object.fromEntries(flags.map(k=>[k,false])),downloads:fixed.map(label=>({label,url:`/files/surface-export-jobs/out1/${label}`,sha256:'7'.repeat(64)}))};
assert.equal(checkedDownloads(review).length,8);await el('Review').onclick();assert.equal(el('Results').children.length,9);
for(const mutate of [r=>r.checked_package_available=1,r=>r.quality_approved=0,r=>r.scene_conditions_pass=1,r=>r.surface_conditions_pass=false,r=>r.root_event_conditions_pass=false,r=>r.new_engine_executed=true,r=>r.engine_queries_reused=false,r=>r.source.result_sha256='invalid',r=>r.downloads[0].url='https://outside.test/private',r=>r.downloads.push(r.downloads[0]),r=>r.downloads.pop(),r=>r.downloads[0].label='source-assets.zip',r=>r.downloads[0].sha256='invalid']){const bad=structuredClone(review);mutate(bad);assert.throws(()=>checkedDownloads(bad));}
review.surface_conditions_pass=false;review.checked_package_available=false;review.all_declared_scene_and_surface_samples_pass=false;review.downloads=review.downloads.slice(0,5);await el('Review').onclick();assert.equal(el('Results').children.length,6);assert.match(el('Status').textContent,/No checked package/);
review={id:'out1',status:'failed',downloads:[],error:'retained audit failure'};await el('Review').onclick();assert.equal(el('Results').children.length,1);assert.throws(()=>checkedDownloads({...review,downloads:[{label:'checked-assets.zip'}]}),/Partial/);
waiting=new Promise(r=>resolve=r);const staleReview=el('Review').onclick();await Promise.resolve();el('Jobs').value='other';resolve({...review});await staleReview;waiting=null;assert.equal(el('Results').children.length,0);assert.match(el('Status').textContent,/changed/);
source.inherited_surface=null;await editor.bind();el('Policy').value=JSON.stringify(policy);assert.throws(()=>editor.request(),/separate normal intent/);
source.normal_origins=[];source.normal_origins_sha256='8'.repeat(64);await editor.bind();el('Policy').value=JSON.stringify(policy);assert.equal(editor.request().normal_revision,null);assert.equal(el('Revise').disabled,true);
el('Kind').value='game';el('Kind').onchange();assert.throws(()=>editor.request(),/Bind/);source.source.kind='game';source.root_event_tracks_included=true;await editor.bind();el('Policy').value=JSON.stringify(policy);assert.equal(editor.request().source.kind,'game');
waiting=new Promise(r=>resolve=r);const staleBind=editor.bind();await Promise.resolve();el('Source').value='other';resolve(structuredClone(source));await assert.rejects(staleBind,/changed/);waiting=null;assert.throws(()=>editor.request(),/Bind/);
console.log('Surface export editor: scene/game bindings, complete authored normals, inherited revision, stale selections, submission races, negative gates and fixed downloads passed. Mock DOM/API only; no browser or engine.');
