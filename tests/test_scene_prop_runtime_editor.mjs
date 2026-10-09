import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createScenePropRuntimeEditor,offsetMatrix,timingSummary} from '../scripts/scene-prop-runtime-editor.mjs';

// Offline DOM double; this is not a browser, renderer or live Studio test.
class Element{
 constructor(){this.value='';this.children=[];this.textContent='';this.disabled=false;}
 replaceChildren(...items){this.children=items;this.value=items[0]?.value??'';}
 append(...items){this.children.push(...items);}
}
const html=await readFile(new URL('../scripts/scene-prop-runtime-editor.html',import.meta.url),'utf8'),nodes=new Map();
for(const match of html.matchAll(/<[^>]*id="(scenePropRuntime[^"]+)"[^>]*>/g)){
 assert(!nodes.has(match[1]));const item=new Element();item.value=match[0].match(/value="([^"]*)"/)?.[1]??'';nodes.set(match[1],item);
}
nodes.set('nativeSceneGameJobs',new Element());nodes.get('nativeSceneGameJobs').value='game1';
const el=name=>{assert(nodes.has('scenePropRuntime'+name));return nodes.get('scenePropRuntime'+name);};
const doc={getElementById:id=>nodes.get(id),createElement:()=>new Element()};
const metadata={game_job:'game1',source_result_sha256:'a'.repeat(64),source_game_zip_sha256:'b'.repeat(64),
 actors:{A:{joints:[{node:0,name:'Explicit joint'},{node:4,name:'Custom joint'}]},B:{joints:[{node:3,name:'Other joint'}]}},
 objects:{item:{geometry:{shape:'sphere'}},reference:{geometry:{shape:'box'}}},
 confirmed_events:[{id:'acquireA',name:'grasp',actor:'A',time_s:1/480},{id:'releaseA',name:'handoff A',actor:'A',time_s:.8},
 {id:'acquireB',name:'handoff B',actor:'B',time_s:.8},{id:'releaseB',name:'release',actor:'B',time_s:2}],source_scene_conditions_pass:false};
let waiting=null,alignmentWaiting=null,alignmentFault=false,timingWaiting=null,saved=null,posted=null,jobs={jobs:[]},review={status:'processing',stage:'packaging',downloads:[]};
function timingReport(cap){const clock=Buffer.alloc(24),limit=Buffer.alloc(8),source=1/480,applied=1/120,delay=applied-source;[source,applied,delay].forEach((v,i)=>clock.writeDoubleLE(v,i*8));limit.writeDoubleLE(cap);return {schema:'strep-scene-prop-physics-timing-v1',physics_fps:120,maximum_delay_f64le:limit.toString('hex'),application_clock:{schema:'strep-physics-event-clock-f64le-v1',count:1,bytes_hex:clock.toString('hex')},collapsed_prop_transactions:[],within_requested_delay:delay<=cap,distinct_prop_boundaries:true,contract_satisfied:delay<=cap,quality_approved:false,release_approved:false};}
function timingResponse(payload){return {game_job:payload.game_job,source_result_sha256:payload.source_result_sha256,source_game_zip_sha256:payload.request.source_game_zip_sha256,physical_timing:timingReport(payload.request.maximum_application_delay_s)};}
const api=async url=>{
 if(url.startsWith('/api/scene-prop-runtime-source?'))return waiting||structuredClone(metadata);
 if(url==='/api/scene-prop-runtime-jobs')return structuredClone(jobs);
 if(url.startsWith('/api/scene-prop-runtime-review?'))return structuredClone(review);throw Error(url);
};
const post=async(url,payload)=>{
 if(url==='/api/scene-prop-runtime-timing')return timingWaiting||timingResponse(payload);
 if(url==='/api/scene-prop-runtime-align')return alignmentWaiting||{
  game_job:metadata.game_job,source_result_sha256:metadata.source_result_sha256,source_game_zip_sha256:metadata.source_game_zip_sha256,
  selection:{event_id:payload.request.event_id,object:payload.request.object,joint_node:payload.request.joint_node,actor:payload.request.actor},
  translation_m:alignmentFault?[1,2]:[1,2,3],rotation_xyz_degrees:[10,20,30]};
 assert.equal(url,'/api/scene-prop-runtime-assets');posted=structuredClone(payload);jobs={jobs:[{id:'prop1',status:'starting'}]};return {id:'prop1'};
};
const editor=createScenePropRuntimeEditor({document:doc,api,post,download:value=>saved=value});
const root=name=>el('Actors').children[Object.keys(metadata.actors).indexOf(name)].children[0];
const prop=name=>el('Objects').children[Object.keys(metadata.objects).indexOf(name)].children[0].children[0];
const setting=(name,index)=>el('Objects').children[Object.keys(metadata.objects).indexOf(name)].children[index].children[0];

assert.throws(()=>editor.snapshot(),/Bind/);await el('Bind').onclick();assert.match(el('Status').textContent,/conditions: fail/);
assert.equal(el('Joint').value,'');assert.equal(prop('item').value,'');assert.equal(root('A').value,'');
root('A').value='embedded';assert.throws(()=>editor.snapshot(),/root mode for B/);root('B').value='extracted';
prop('item').value='grip-physics';assert.throws(()=>editor.snapshot(),/mode for reference/);prop('reference').value='authored';
el('Prop').value='item';await el('AddGrip').onclick();assert.match(el('Status').textContent,/valid source joint/);
el('Joint').value='4';await el('AddGrip').onclick();assert.equal(el('Grips').children.length,1);
async function command(grip,object,event,action){el('CommandGrip').value=grip;await el('CommandGrip').onchange();el('CommandProp').value=object;el('CommandEvent').value=event;el('Action').value=action;await el('AddCommand').onclick();}
await command('grip-1','item','acquireB','acquire');assert.match(el('Status').textContent,/confirmed matching actor/);assert.equal(el('Commands').children.length,0);
await command('grip-1','item','acquireA','acquire');await command('grip-1','item','acquireA','release');assert.match(el('Status').textContent,/already has a change/);
await command('grip-1','item','releaseA','release');assert.throws(()=>editor.snapshot(),/physics rate/);el('Rate').value='120';
el('Actor').value='B';await el('Actor').onchange();assert.equal(el('Joint').value,'');assert.deepEqual(el('AlignEvent').children.slice(1).map(e=>e.value),['acquireB','releaseB']);
el('GripId').value='partner';el('Joint').value='3';await el('AddGrip').onclick();await command('partner','item','acquireB','acquire');await command('partner','item','releaseB','release');
const snapshot=editor.snapshot();assert.deepEqual(snapshot.request.root_modes,{A:'embedded',B:'extracted'});
assert.equal('maximum_application_delay_s' in snapshot.request,false);
await el('Timing').onclick();assert.match(el('Status').textContent,/Choose a maximum/);
el('Delay').value='7';assert.equal(editor.snapshot().request.maximum_application_delay_s,.007);await el('Timing').onclick();assert.match(el('TimingResult').textContent,/Timing limit met/);
el('Delay').value='0';el('Panel').oninput();assert.equal(el('TimingResult').textContent,'');await el('Timing').onclick();assert.match(el('TimingResult').textContent,/Timing limit failed/);assert.equal(editor.snapshot().request.maximum_application_delay_s,0);
el('Delay').value='20';assert.equal(editor.snapshot().request.maximum_application_delay_s,.02);el('Delay').value='Infinity';assert.throws(()=>editor.snapshot(),/maximum physical delay/);el('Delay').value='-1';assert.throws(()=>editor.snapshot(),/maximum physical delay/);
el('Delay').value='7';let resolveTiming;timingWaiting=new Promise(r=>resolveTiming=r);const timedPayload=editor.snapshot(),timingPending=el('Timing').onclick();el('Delay').value='6';el('Panel').oninput();resolveTiming(timingResponse(timedPayload));await timingPending;assert.equal(el('TimingResult').textContent,'');assert.match(el('Status').textContent,/Timing selections changed/);timingWaiting=null;el('Delay').value='';
assert.throws(()=>timingSummary({...timingReport(.007),quality_approved:true},120,.007),/decision/);
assert.throws(()=>timingSummary(timingReport(.007),120,.006),/selection changed/);
assert.throws(()=>timingSummary({...timingReport(.007),application_clock:{schema:'strep-physics-event-clock-f64le-v1',count:2,bytes_hex:'00'}},120,.007),/clock/);
assert.equal('collision_profile' in snapshot.request,false);
for(const profile of ['engine-default','ccd-threshold','strict-ccd']){el('Collision').value=profile;assert.equal(editor.snapshot().request.collision_profile,profile);}
el('Collision').value='unknown';assert.throws(()=>editor.snapshot(),/collision profile/);el('Collision').value='ccd-threshold';
assert.deepEqual(snapshot.request.object_modes,{item:'grip-physics',reference:'authored'});assert.equal(snapshot.request.commands.length,4);
assert.equal(snapshot.request.grips.partner.actor,'B');assert.equal(snapshot.request.grips['grip-1'].joint_node,4);
assert.deepEqual(snapshot.request.grips.partner.prop_offsets.item,offsetMatrix([0,0,0],[0,0,0]));
assert.equal(snapshot.source_result_sha256,metadata.source_result_sha256);assert.equal(snapshot.request.source_game_zip_sha256,metadata.source_game_zip_sha256);
setting('item',1).value='';assert.throws(()=>editor.snapshot(),/valid mass/);setting('item',1).value='2';
setting('item',7).value='1.2';assert.throws(()=>editor.snapshot(),/collision mask/);setting('item',7).value='1';
el('PositionLimit').value='0';assert.throws(()=>editor.snapshot(),/positive grip distance/);el('PositionLimit').value='.001';
el('Joint').value='0';await el('AddGrip').onclick();assert.match(el('Status').textContent,/existing joint/);assert.equal(editor.snapshot().request.grips.partner.joint_node,3);
el('Joint').value='3';el('AlignEvent').value='acquireB';await el('Align').onclick();
assert.deepEqual(['OffsetX','OffsetY','OffsetZ'].map(n=>Number(el(n).value)),[1,2,3]);assert.match(el('Status').textContent,/Pose alignment only/);
alignmentFault=true;await el('Align').onclick();assert.match(el('Status').textContent,/Invalid alignment/);assert.equal(el('OffsetZ').value,'3');alignmentFault=false;
let resolveAlign;alignmentWaiting=new Promise(r=>resolveAlign=r);const alignPending=el('Align').onclick();el('OffsetX').value='8';
resolveAlign({game_job:'game1',source_result_sha256:metadata.source_result_sha256,source_game_zip_sha256:metadata.source_game_zip_sha256,
 selection:{actor:'B',joint_node:3,object:'item',event_id:'acquireB'},translation_m:[9,9,9],rotation_xyz_degrees:[0,0,0]});
await alignPending;assert.equal(el('OffsetX').value,'8');assert.match(el('Status').textContent,/selection changed/);alignmentWaiting=null;
await el('Save').onclick();assert.deepEqual(saved,editor.snapshot());await el('Build').onclick();assert.deepEqual(posted,saved);assert.equal(el('Build').disabled,false);
assert.equal(saved.request.collision_profile,'ccd-threshold');assert.equal(posted.request.collision_profile,'ccd-threshold');
assert.equal(nodes.get('nativeSceneGameJobs').value,'game1');assert.equal(el('Jobs').value,'prop1');
await el('Review').onclick();assert.match(el('Results').children[0].textContent,/processing: packaging/);assert.equal(el('Results').children.length,1);
review={status:'complete',source_scene_conditions_pass:false,root_samples_pass:true,downloads:[{url:'/files/scene-prop-runtime-jobs/prop1/runtime/prop-runtime-assets.zip',label:'package'}]};
await el('Review').onclick();assert.match(el('Results').children[0].textContent,/conditions: fail/);assert.match(el('Results').children[0].textContent,/not approved/);assert.equal(el('Results').children[1].href,review.downloads[0].url);
review={status:'failed',error:'Retained packaging failure',downloads:[{url:'/must-not-be-shown'}]};await el('Review').onclick();assert.match(el('Results').children[0].textContent,/Retained packaging failure/);assert.equal(el('Results').children.length,1);
nodes.get('nativeSceneGameJobs').value='game2';posted=null;await el('Build').onclick();assert.equal(posted,null);assert.match(el('Status').textContent,/Bind/);
nodes.get('nativeSceneGameJobs').value='game1';let resolve;waiting=new Promise(r=>resolve=r);const pending=el('Bind').onclick();nodes.get('nativeSceneGameJobs').value='game2';resolve(metadata);await pending;assert.throws(()=>editor.snapshot(),/Bind/);
waiting=null;nodes.get('nativeSceneGameJobs').value='game1';await el('Bind').onclick();assert.equal(el('Grips').children.length,0);assert.equal(root('A').value,'');
root('A').value='embedded';root('B').value='extracted';prop('item').value='grip-physics';prop('reference').value='authored';el('Actor').value='A';await el('Actor').onchange();el('Joint').value='0';el('Prop').value='item';el('GripId').value='new';
await el('AddGrip').onclick();await command('new','item','acquireA','acquire');el('Grips').children[0].children[0].onclick();assert.equal(el('Commands').children.length,0);assert.throws(()=>editor.snapshot(),/explicit grips/);

const rotate=(v,[x,y,z])=>{[x,y,z]=[x,y,z].map(t=>t*Math.PI/180);const [a,b,c]=v;const w=[a,b*Math.cos(x)-c*Math.sin(x),b*Math.sin(x)+c*Math.cos(x)];const u=[w[0]*Math.cos(y)+w[2]*Math.sin(y),w[1],-w[0]*Math.sin(y)+w[2]*Math.cos(y)];return [u[0]*Math.cos(z)-u[1]*Math.sin(z),u[0]*Math.sin(z)+u[1]*Math.cos(z),u[2]];};
for(const angles of [[90,90,0],[10,20,30],[-77,44,121]]){
 const matrix=offsetMatrix([1,2,3],angles),v=[.3,-.7,1.2],expected=rotate(v,angles).map((x,i)=>x+i+1);
 const actual=matrix.slice(0,3).map(row=>row[0]*v[0]+row[1]*v[1]+row[2]*v[2]+row[3]);assert(actual.every((x,i)=>Math.abs(x-expected[i])<1e-12));
}
assert.throws(()=>offsetMatrix([0,0],[0,0,0]),/Finite/);assert.throws(()=>offsetMatrix([0,NaN,0],[0,0,0]),/Finite/);
console.log('Offline explicit source/joint/prop modes, handoff drafts, exact event IDs, alignment math/stale guards, source preservation and failed-result UI passed.');
