import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createNativeSceneTransferEditor,stagedScene,checkedDownloads} from '../scripts/native-scene-transfer-editor.mjs';
class Element{constructor(){this.value='';this.disabled=false;this.checked=false;this.children=[];this.style={};this.textContent='';}replaceChildren(...c){this.children=c;if(c[0]?.value!==undefined)this.value=c[0].value;}append(...c){this.children.push(...c);}}
const html=await readFile(new URL('../scripts/native-scene-transfer-editor.html',import.meta.url),'utf8'),nodes=new Map();
for(const m of html.matchAll(/<[^>]*id="(nativeSceneTransfer[^"]+)"[^>]*>/g)){assert(!nodes.has(m[1]));const n=new Element();n.value=m[0].match(/value="([^"]*)"/)?.[1]??'';nodes.set(m[1],n);}
const el=n=>{assert(nodes.has('nativeSceneTransfer'+n));return nodes.get('nativeSceneTransfer'+n);};
const document={getElementById:id=>nodes.get(id),createElement:()=>new Element(),createTextNode:text=>({textContent:text})};
const actor=h=>({glb:`/files/character-assets/${h.repeat(64)}/character.glb`,sha256:h.repeat(64),animation_index:0,placement:{translation_m:[0,0,0],rotation_xyzw:[0,0,0,1]}});
let draft={schema:'strep-studio-native-scene-v1',scene:{duration_s:2,actors:{A:actor('a'),B:actor('b'),C:actor('c')},objects:{box:{keyframes:[]}},contacts:[
 {id:'grip',actor:'A',vertices:[[0,0,1]],reduction:'centroid',target:{space:'object',object:'box',points_m:[[0,0,0]]},mode:'touch',interval_s:[1,1],limits:{position_m:.005}},
 {id:'incoming',actor:'B',vertices:[[0,0,3]],reduction:'centroid',target:{space:'actor',actor:'A',vertices:[[0,0,2]],reduction:'centroid'},mode:'touch',interval_s:[1,1],limits:{position_m:.005}}
 ]},geometry:{clock:{mode:'explicit',times_s:[0,2]},limits:{penetration_m:.0001},planes:{}},object_edit:null};
const original=structuredClone(draft),cats={A:{source_sha256:'a'.repeat(64),source_animation_index:0,target_sha256:'d'.repeat(64),target_roles:['LeftHand','RightHand'],output_animation_index:1,required_vertices:[[0,0,1],[0,0,2]],job:'t1',result_sha256:'1'.repeat(64)},B:{source_sha256:'b'.repeat(64),source_animation_index:0,target_sha256:'e'.repeat(64),target_roles:['RightHand'],output_animation_index:1,required_vertices:[[0,0,3]],job:'t2',result_sha256:'2'.repeat(64)}};
let review,waiting=null,posting=null,patch,saved,posted,submissions=0,staged=0;
const api=async url=>{if(url==='/api/native-transfer-jobs')return {jobs:[{id:'t1',status:'complete'},{id:'t2',status:'complete'},{id:'bad',status:'failed'}]};if(url==='/api/native-scene-transfer-jobs')return {jobs:[{id:'s1',status:'complete'}]};if(waiting)return waiting;if(url.startsWith('/api/native-transfer-review')){const id=url.endsWith('t1')?'t1':'t2';return {id,status:'complete',result_sha256:(id==='t1'?'1':'2').repeat(64),sampled_runtime_conditions_pass:true};}return structuredClone(review);};
const post=async(url,value)=>{if(url==='/api/native-scene-transfer-catalog'){const name=Object.keys(value.transfers)[0];return waiting??{schema:'strep-studio-native-scene-transfer-catalog-v1',duration_s:2,actors:{[name]:structuredClone(cats[name])},quality_approved:false};}assert.equal(url,'/api/native-scene-transfer-assets');submissions++;posted=structuredClone(value);return posting??{id:'s1'};};
const editor=createNativeSceneTransferEditor({document,api,post,getDraft:()=>structuredClone(draft),setDraft:value=>{draft=structuredClone(value);staged++;},getPatch:()=>patch,download:value=>saved=structuredClone(value)});
await editor.refresh();assert.deepEqual(el('Transfer').children.map(c=>c.value),['t1','t2']);assert.throws(()=>editor.request(),/Save correspondence/);
await editor.load();assert.equal(el('Vertices').children.length,2);assert.equal(el('Roles').children.length,2);
await el('SaveActor').onclick();assert.match(el('Status').textContent,/distinct target/);
patch={glb_sha256:'a'.repeat(64),vertices:[[4,0,1],[4,0,2]]};await el('Pick').onclick();assert.match(el('Status').textContent,/exact target/);
patch={glb_sha256:'d'.repeat(64),vertices:[[4,0,1],[4,0,2]]};await el('Pick').onclick();
assert.equal(el('Vertices').children[0].children[1].value,'[4,0,1]');
await el('SaveActor').onclick();assert.match(el('Status').textContent,/rotation roles/);
const role=el('Roles').children[0];role.children[0].checked=true;role.children[0].onchange();role.children[2].value='15';
await el('SaveActor').onclick();assert.throws(()=>editor.request(),/unit target normal/);
el('Normals').value=JSON.stringify({grip:{target_normal:{space:'object',normals:[[0,0,1]]}},incoming:{target_normal:{space:'partner-surface'}}});
await el('Save').onclick();assert.deepEqual(saved.transfers.A.vertex_map,[{source:[0,0,1],target:[4,0,1]},{source:[0,0,2],target:[4,0,2]}]);assert.equal(saved.calibration.actors.A.maximum_joint_displacement_m,.02);assert.equal(saved.calibration.surface.limits.backface_allowance_m,.00005);
el('Actor').value='B';el('Actor').onchange();el('Transfer').value='t2';await editor.load();
patch={glb_sha256:'e'.repeat(64),vertices:[[5,0,3]]};await el('Pick').onclick();const br=el('Roles').children[0];br.children[0].checked=true;br.children[2].value='10';await el('SaveActor').onclick();
assert.deepEqual(Object.keys(editor.request().transfers),['A','B']);assert.deepEqual(draft,original);
for(const [field,value] of [['Queries','true'],['Angle','NaN'],['Starts','8'],['Calls',''],['Seconds','Infinity']]){const before=el(field).value;el(field).value=value;assert.throws(()=>editor.request(),/finite/);el(field).value=before;}
const normalBefore=el('Normals').value;el('Normals').value=JSON.stringify({grip:{target_normal:{space:'object',normals:[[0,0,2]]}},incoming:{target_normal:{space:'partner-surface'}}});assert.throws(()=>editor.request(),/unit/);el('Normals').value=normalBefore;
let resolve;posting=new Promise(r=>resolve=r);const building=el('Build').onclick();await Promise.resolve();assert(el('Build').disabled);await el('Build').onclick();assert.equal(submissions,1);resolve({id:'s1'});await building;posting=null;assert.equal(el('Build').disabled,false);
const proposed=structuredClone(original);proposed.scene.contacts[0].vertices=[[4,0,1]];proposed.scene.contacts[1].vertices=[[5,0,3]];proposed.scene.contacts[1].target.vertices=[[4,0,2]];
const downloads=[];for(const [i,[name,a]] of Object.entries(proposed.scene.actors).entries()){const url=`/files/native-scene-transfer-jobs/s1/actors/actor-${i}.glb`;if(name!=='C')a.glb=url;if(name==='A'){a.sha256='f'.repeat(64);a.animation_index=1;}if(name==='B'){a.sha256='9'.repeat(64);a.animation_index=1;}downloads.push({label:`actors/actor-${i}.glb`,url,sha256:a.sha256});}
review={id:'s1',status:'complete',result_sha256:'7'.repeat(64),staging_conditions_pass:true,original_selected:true,source_bytes_unchanged:true,engine_playback_verified:false,human_reviewed:false,anatomical_reviewed:false,quality_approved:false,release_approved:false,continuous_collision_certified:false,studio_selection_changed:false,
 checks:Object.fromEntries(['candidate_contact_samples_pass','source_rates_pass','joint_displacement_pass','surface_common_clock_pass','surface_contact_samples_pass','geometry_samples_pass'].map(k=>[k,true])),authoring_request:posted,stage_draft:proposed,downloads,
 actors:Object.fromEntries(Object.entries(proposed.scene.actors).map(([n,a],i)=>[n,{original_sha256:original.scene.actors[n].sha256,candidate_sha256:a.sha256,candidate_url:downloads[i].url,animation_index:a.animation_index}]))};
assert.deepEqual(stagedScene(review),proposed);
for(const mutate of [r=>r.staging_conditions_pass=1,r=>r.quality_approved=0,r=>r.checks.geometry_samples_pass=false,r=>r.stage_draft.scene.actors.C.sha256='8'.repeat(64),r=>delete r.stage_draft.scene.actors.C,r=>r.stage_draft.scene.contacts[0].target.points_m=[[99,0,0]],r=>r.stage_draft.geometry.limits.penetration_m=1,r=>r.stage_draft.scene.actors.A.placement.translation_m=[99,0,0],r=>r.authoring_request.transfers.A.vertex_map.pop(),r=>r.authoring_request.transfers.A.vertex_map.push({source:[0,0,99],target:[4,0,99]}),r=>r.downloads[0].url='https://remote.test/private',r=>r.downloads[0].label='input/source.glb',r=>r.downloads.push(r.downloads[0])]){const bad=structuredClone(review);mutate(bad);assert.throws(()=>stagedScene(bad));}
await el('Review').onclick();assert.equal(el('Stage').disabled,false);assert.equal(el('Results').children.length,4);
waiting=new Promise(r=>resolve=r);const stage=el('Stage').onclick();await Promise.resolve();draft.geometry.limits.penetration_m=.2;resolve(structuredClone(review));await stage;waiting=null;assert.equal(staged,0);assert.match(el('Status').textContent,/changed/);draft=structuredClone(original);
await el('Review').onclick();await el('Stage').onclick();assert.equal(staged,1);assert.deepEqual(draft,proposed);assert.throws(()=>editor.request(),/Scene changed/);
draft=structuredClone(original);await editor.refresh();el('Actor').value='A';el('Transfer').value='t1';
waiting=new Promise(r=>resolve=r);const loading=editor.load();await Promise.resolve();draft.scene.actors.A.placement.translation_m=[1,0,0];resolve({id:'t1',status:'complete',result_sha256:'1'.repeat(64),sampled_runtime_conditions_pass:true});await assert.rejects(loading,/changed|catalog/);waiting=null;draft=structuredClone(original);
review={id:'s1',status:'failed',downloads:[],error:'retained failure',quality_approved:false,release_approved:false};await el('Review').onclick();assert(el('Stage').disabled);assert.equal(checkedDownloads(review).length,0);
console.log('Scene transfer editor: multiple actors, incoming correspondence, authored normals, bounded requests, fixed downloads, protected staging and stale selections passed. No browser or engine used.');
