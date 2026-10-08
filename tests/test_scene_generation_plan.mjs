import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {webcrypto} from 'node:crypto';
import {createSceneGenerationPlan} from '../scripts/scene-generation-plan.js';
import {createMotionProfileEditor} from '../scripts/motion-profile-editor.js';
const html=await readFile(new URL('../scripts/action-studio.html',import.meta.url),'utf8');
assert(html.includes('if(token===loadVersion)await generationPlan.bind(spec,bundleUrl);'),'Older scene loads must not rebind generation plans');
class Element{
 constructor(tag='div'){this.tag=tag;this.value='';this.children=[];this.events={};this.style={};this.id='';}
 addEventListener(n,f){this.events[n]=f;}setAttribute(){}append(...nodes){for(const n of nodes)n.parent=this;this.children.push(...nodes);}prepend(...nodes){this.children.unshift(...nodes);}replaceChildren(...nodes){this.children=[];this.append(...nodes);}remove(){this.parent.children=this.parent.children.filter(n=>n!==this);}
}
const elements=new Map([...html.matchAll(/id="(scenePlan[^"]+)"/g)].map(m=>[m[1],Object.assign(new Element(),{id:m[1]})]));
globalThis.document={createElement:tag=>new Element(tag),getElementById:id=>{assert(elements.has(id),'Missing '+id);return elements.get(id);}};
if(!globalThis.crypto)Object.defineProperty(globalThis,'crypto',{value:webcrypto});
const stored=new Map();globalThis.localStorage={getItem:key=>stored.get(key)||null,setItem:(k,v)=>stored.set(k,v)};
const by=n=>elements.get('scenePlan'+n);
let selectedProfile=null,profileChange;const fakeProfile=(_host,onChange)=>{profileChange=onChange;return{request:()=>structuredClone(selectedProfile),restore(value){selectedProfile=value?.enabled?structuredClone(value.profile):null;},setRequestSource(){},markChanged(){}};};
const scene={frame_count:120,actors:{A:{},B:{}},contacts:[]};let context={spec:scene,changed:false},posted=[],downloads=[],reject=false,pending=null;
let showConflict=false;
const resultFor=draft=>({plan:{actors:Object.fromEntries(Object.keys(draft.actor_plan).map(name=>[name,{selected_frames:[60],complete_target_frames:[60]}]))},contact_consistency:{has_proven_pair_conflict:showConflict,overlapping_pairs:showConflict?[{contact_ids:['grip-1','grip-2'],contact_indices:[0,1],overlap_frames:[50,90],status:'contradiction'}]:[]}});
globalThis.fetch=async(url,options)=>{assert.equal(url,'/api/scene-generation-plan');const draft=JSON.parse(options.body);posted.push(draft);if(pending)return pending(draft);return{ok:!reject,json:async()=>reject?{error:'Duration does not match'}:resultFor(draft)};};
const editor=createSceneGenerationPlan({getContext:()=>context,createProfile:fakeProfile,download:(name,value)=>downloads.push({name,value:structuredClone(value)})});
const flush=async()=>{for(let i=0;i<4;i++)await new Promise(r=>setImmediate(r));};
await editor.bind(scene,'/files/scene.json');assert.equal(by('Download').disabled,true);
const prompt=()=>by('Segments').children[0].children[0].children[0];
prompt().value='Vault then hand over a parcel.';prompt().events.input();selectedProfile={name:'Courier',stats:[]};profileChange();
by('Actor').value='B';by('Actor').onchange();assert.equal(selectedProfile,null);prompt().value='Accept the parcel and bow.';prompt().events.input();selectedProfile={name:'Guard',stats:[]};profileChange();
await by('Preview').onclick();assert.equal(by('Download').disabled,false);
assert.equal(posted.at(-1).actor_plan.A.motion_profile.name,'Courier');assert.equal(posted.at(-1).actor_plan.B.motion_profile.name,'Guard');
by('Download').onclick();assert.equal(downloads.length,2);assert.equal(downloads[0].name,'actor-plan.json');
by('Actor').value='A';by('Actor').onchange();assert.equal(selectedProfile.name,'Courier');
context.changed=true;by('Download').onclick();assert.equal(downloads.length,2);assert.match(by('Status').textContent,/scene changed/);context.changed=false;
await by('Preview').onclick();prompt().value='Changed';prompt().events.input();assert.equal(by('Download').disabled,true);
reject=true;await by('Preview').onclick();assert.match(by('Status').textContent,/Duration/);reject=false;
let release;pending=draft=>new Promise(resolve=>{release=()=>resolve({ok:true,json:async()=>resultFor(draft)});});
const old=by('Preview').onclick();await flush();prompt().value='Another edit';prompt().events.input();release();await old;assert.equal(by('Download').disabled,true);pending=null;
await editor.bind(scene,'/files/scene.json');assert.equal(prompt().value,'Another edit');assert.equal(selectedProfile.name,'Courier');
const imported={A:{segments:[{prompt:'Lift a box',duration_s:4}],seeds:[33],motion_profile:{name:'Lifter',stats:[]}},B:{segments:[{prompt:'Watch',duration_s:4}],seeds:[44]}};
by('Import').files=[{size:100,text:async()=>JSON.stringify(imported)}];await by('Import').onchange();assert.equal(prompt().value,'Lift a box');assert.equal(selectedProfile.name,'Lifter');
const manual=structuredClone(imported);manual.A.guide_plan={mode:'sparse',frame_indices:[60]};by('Import').files=[{size:100,text:async()=>JSON.stringify(manual)}];await by('Import').onchange();assert.match(by('Status').textContent,/manual selections/);assert.equal(prompt().value,'Lift a box');
await by('Preview').onclick();assert.equal(posted.at(-1).actor_plan.A.motion_profile.name,'Lifter');assert.equal(posted.at(-1).actor_plan.B.motion_profile,undefined);
showConflict=true;await by('Preview').onclick();assert.match(by('Status').textContent,/Contact targets conflict/);assert(by('Results').children.some(node=>node.textContent?.includes('grip-1 + grip-2')));
by('Download').onclick();assert.equal(downloads.at(-1).value.result.contact_consistency.has_proven_pair_conflict,true);showConflict=false;
editor.reset();assert.equal(by('Preview').disabled,true);assert.equal(by('Download').disabled,true);
await editor.bind({...scene,frame_count:901},'long');assert.match(by('Status').textContent,/1–30/);
// Actual reusable profile widgets retain unique IDs and discard slow templates on actor switches.
const template={schema:'strep-motion-profile-v1',name:'Default',policy_name:'Rules',style:'',training:'',state:'',stats:[]};
const walk=node=>[node,...node.children.flatMap(walk)];const host=new Element();host.id='scenePlanProfile';
let finishTemplate;globalThis.fetch=async()=>({ok:true,json:()=>new Promise(resolve=>{finishTemplate=resolve;})});
const real=createMotionProfileEditor(host,()=>{}, {idPrefix:'scenePlan-'});const toggle=walk(host).find(n=>n.id==='scenePlan-motionProfileEnabled');toggle.checked=true;
const switching=toggle.onchange();await flush();real.restore({enabled:true,profile:{...template,name:'Other actor'}});finishTemplate(template);await switching;assert.equal(real.request().name,'Other actor');
const ids=walk(host).map(n=>n.id).filter(Boolean);assert(ids.every(id=>id.startsWith('scenePlan-')||id==='scenePlanProfile'));
const composeHost=new Element();composeHost.id='movementProfile';createMotionProfileEditor(composeHost,()=>{});
const legacyIds=walk(composeHost).map(n=>n.id).filter(Boolean);assert(legacyIds.includes('motionProfileEnabled')&&legacyIds.includes('motionBriefPreview'));
assert(!ids.some(id=>legacyIds.includes(id)));
globalThis.localStorage={getItem(){throw Error('Denied');},setItem(){throw Error('Denied');}};await editor.bind(scene,'private');assert.equal(by('Preview').disabled,false);
console.log('Scene plans: per-actor profiles, checked downloads, drafts, imports, stale checks, placement changes and profile-template races pass without a browser.');
