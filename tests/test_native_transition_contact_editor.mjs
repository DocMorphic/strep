import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createNativeTransitionContactEditor,reserveDownloads} from '../scripts/native-transition-contact-editor.mjs';
class Element{constructor(){this.value='';this.children=[];this.disabled=false;this.checked=false;this.textContent='';}replaceChildren(...c){this.children=c;}append(c){this.children.push(c);}}
const elements=new Map(),el=n=>{if(!elements.has(n))elements.set(n,new Element());return elements.get(n);};
const document={getElementById:id=>el(id.replace('nativeTransitionContact','')),createElement:()=>new Element()};
const h='a'.repeat(64),source={folder:'source',result_sha256:h};let bridge={schema:'strep-studio-native-transition-fit-v1',source,actors:{A:{}},resume_from:null},waiting=null;
const catalog={schema:'strep-studio-transition-contact-reserve-catalog-v1',source,contacts_sha256:h,source_checks:{contacts:false},contacts:[{id:'touch',actor:'A',mode:'touch',target:{space:'actor',actor:'B'},limits:{position_m:.00002}}],original_selected:true,quality_approved:false,release_approved:false};
const request={schema:'strep-studio-native-transition-contact-fit-v1',bridge:structuredClone(bridge),reserves_m:{touch:.5e-6},seed:null};
const fixed=['candidate-bundle.zip','proposal/result.json','proposal/reserve-binding.json','proposal/candidate/scene.json','proposal/candidate/contacts-audit.json','proposal/candidate/geometry.json','proposal/candidate/tracks/root-motion.json','proposal/candidate/tracks/events.json','proposal/candidate/tracks/contacts.json','proposal/candidate/actors/0.glb'];
const review={id:'job',status:'complete',result_sha256:h,proposal_result_sha256:h,original_selected:true,native_roots_only:true,studio_selection_changed:false,quality_approved:false,training_admitted:false,release_approved:false,engine_playback_verified:false,
checks:{native_motion_and_contacts:true,native_contact_audit:true,actor_transition_conditions:true,whole_scene_geometry:false},all_declared_samples_pass:false,
reserve_binding:{role:'optimization-guidance-only',contacts_sha256:h,original_acceptance_limits_unchanged:true,quality_approved:false,release_approved:false,targets:{touch:{original_limit_m:.00002,reserve_m:.5e-6,solver_target_m:.00002-.5e-6}}},authoring_request:request,
files_sha256:Object.fromEntries(fixed.map(n=>[n,h])),downloads:fixed.map(n=>({label:n,url:'/files/native-transition-contact-fit-jobs/job/'+n,sha256:h}))};
assert.equal(reserveDownloads(review).length,fixed.length);
for(const mutate of [r=>r.quality_approved=true,r=>r.native_roots_only=1,r=>r.checks.whole_scene_geometry=0,r=>r.all_declared_samples_pass=true,r=>r.downloads.pop(),r=>r.downloads[0].url='https://bad.test',r=>r.reserve_binding.targets.touch.original_limit_m=.00003,r=>r.reserve_binding.targets.touch.reserve_m=0,r=>r.authoring_request.bridge.resume_from={},r=>r.files_sha256['private.json']=h]){const r=structuredClone(review);mutate(r);assert.throws(()=>reserveDownloads(r));}
const posts=[];const editor=createNativeTransitionContactEditor({document,api:async url=>waiting??structuredClone(url.endsWith('jobs')?{jobs:[{id:'job',status:'complete'}]}:review),post:async(url,payload)=>{posts.push([url,structuredClone(payload)]);return waiting??structuredClone(url.endsWith('catalog')?catalog:{id:'job'});},getBridgeRequest:()=>bridge,getBridgeReview:()=>null});
await el('Build').onclick();assert.equal(posts.length,0);
await el('Inspect').onclick();el('Contact').value='touch';el('Contact').onchange();assert.match(el('Limit').textContent,/20 Âµm/);
el('Reserve').value='20';await el('Add').onclick();assert.match(el('Status').textContent,/smaller/);
el('Reserve').value='0.5';await el('Add').onclick();assert.deepEqual(editor.request(),request);
await el('Build').onclick();assert.deepEqual(posts.at(-1),['/api/native-transition-contact-fits',request]);
el('Jobs').value='job';await el('Review').onclick();assert.match(el('Results').children[0].textContent,/Original: contacts: fail/);assert.match(el('Results').children[0].textContent,/whole_scene_geometry: fail/);assert.equal(el('Results').children[1].textContent,'Download clips, tracks and correction history');
el('Seed').checked=true;assert.throws(()=>editor.request(),/verified|source-bound/);el('Seed').checked=false;
let resolve;waiting=new Promise(r=>resolve=r);const pending=el('Inspect').onclick();bridge={...bridge,source:{folder:'changed',result_sha256:h}};resolve(catalog);await pending;assert.match(el('Status').textContent,/selection changed/);assert.equal(el('Build').disabled,true);waiting=null;
const normalize=s=>s.replaceAll('\r\n','\n');const html=normalize(await readFile(new URL('../scripts/native-transition-contact-editor.html',import.meta.url),'utf8')),built=normalize(await readFile(new URL('../scripts/action-studio.html',import.meta.url),'utf8'));
assert(built.includes(html));assert(built.includes("import('/native-transition-contact-editor.mjs')"));
console.log('Explicit reserves, unchanged limits, negative review/downloads, seed guards and stale catalog handling passed offline.');
