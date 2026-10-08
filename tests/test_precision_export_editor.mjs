import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createPrecisionExportEditor,precisionRequest,precisionDownloads} from '../scripts/precision-export-editor.mjs';
class Element{constructor(){this.value='';this.disabled=false;this.children=[];this.textContent='';}replaceChildren(...c){this.children=c;if(c[0]?.value!==undefined)this.value=c[0].value;}append(...c){this.children.push(...c);}}
const html=await readFile(new URL('../scripts/precision-export-editor.html',import.meta.url),'utf8'),nodes=new Map();
for(const m of html.matchAll(/<[^>]*id="(precisionExport[^"]+)"[^>]*>/g)){assert(!nodes.has(m[1]));nodes.set(m[1],new Element());}
const el=n=>{assert(nodes.has('precisionExport'+n));return nodes.get('precisionExport'+n);};
const document={getElementById:id=>nodes.get(id),createElement:()=>new Element()};
let source={source:{kind:'scene',job:'s1',result_sha256:'1'.repeat(64)},package_sha256:'2'.repeat(64),engine_sha256:'3'.repeat(64),source_clock_sha256:'4'.repeat(64),actor_count:2,original_selected:true,quality_approved:false,release_approved:false};
let waiting=null,posting=null,posts=0,posted,review;
const api=async url=>{
 if(['/api/native-scene-jobs','/api/native-scene-game-jobs'].includes(url))return {jobs:[{id:'s1',status:'complete'},{id:'bad',status:'failed'}]};
 if(url==='/api/precision-export-jobs')return {jobs:[{id:'out1',status:'complete'}]};
 return waiting??structuredClone(url.startsWith('/api/precision-export-source?')?source:review);
};
const post=async(url,p)=>{assert.equal(url,'/api/precision-export-assets');posts++;posted=structuredClone(p);return posting??{id:'out1'};};
el('Kind').value='scene';
const editor=createPrecisionExportEditor({document,api,post});await editor.refresh();
assert.deepEqual(el('Source').children.map(o=>o.value),['s1']);await el('Build').onclick();assert.equal(posts,0);
await editor.bind();assert.equal(precisionRequest(source,'scene','s1').source.job,'s1');
for(const edit of [s=>s.original_selected=false,s=>s.quality_approved=0,s=>s.source.result_sha256='bad',s=>s.engine_sha256='bad',s=>s.source_clock_sha256='bad']){const bad=structuredClone(source);edit(bad);assert.throws(()=>precisionRequest(bad,'scene','s1'));}
let resolve;waiting=new Promise(r=>resolve=r);const stale=el('Build').onclick();await Promise.resolve();el('Source').value='other';el('Source').onchange();resolve(structuredClone(source));await stale;waiting=null;assert.equal(posts,0);assert.match(el('Status').textContent,/changed/);
el('Source').value='s1';await editor.bind();posting=new Promise(r=>resolve=r);const building=el('Build').onclick();await Promise.resolve();await Promise.resolve();assert.equal(el('Build').disabled,true);await el('Build').onclick();assert.equal(posts,1);resolve({id:'out1'});await building;posting=null;assert.equal(el('Build').disabled,false);assert.equal(posted.source.result_sha256,source.source.result_sha256);
const flags=['studio_selection_changed','quality_approved','release_approved','training_admitted','physics_verified','gpu_render_checked','continuous_collision_certified'];
const names=['result.json','original-assets.zip','fidelity.json','fidelity.npz','actors/0.glb','actors/0.glb.weights.json','actors/1.glb','actors/1.glb.weights.json','checked-assets.zip'];
review={id:'out1',status:'complete',schema:'strep-studio-precision-export-v1',result_sha256:'5'.repeat(64),actor_count:2,original_selected:true,original_skin_samples_passed:true,scene_samples_passed:true,inherited_surface_checked:true,inherited_surface_samples_passed:true,root_event_tracks_included:true,root_samples_passed:true,event_dispatch_verified:true,checked_package_available:true,...Object.fromEntries(flags.map(k=>[k,false])),downloads:names.map(label=>({label,url:`/files/precision-export-jobs/out1/${label}`,sha256:'6'.repeat(64)}))};
assert.equal(precisionDownloads(review).length,9);await el('Review').onclick();assert.equal(el('Results').children.length,10);
for(const edit of [r=>r.checked_package_available=1,r=>r.quality_approved=0,r=>r.original_skin_samples_passed=false,r=>r.scene_samples_passed=1,r=>r.inherited_surface_samples_passed=false,r=>r.root_samples_passed=false,r=>r.event_dispatch_verified=false,r=>r.actor_count=1,r=>r.downloads.pop(),r=>r.downloads.push(r.downloads[0]),r=>r.downloads[0].url='https://external.test/private',r=>r.downloads[0].sha256='bad']){const bad=structuredClone(review);edit(bad);assert.throws(()=>precisionDownloads(bad));}
review.original_skin_samples_passed=false;review.checked_package_available=false;review.downloads.pop();await el('Review').onclick();assert.equal(el('Results').children.length,9);assert.match(el('Status').textContent,/no checked package/);
review={id:'out1',status:'failed',error:'retained failure',downloads:[]};await el('Review').onclick();assert.equal(el('Results').children.length,1);assert.throws(()=>precisionDownloads({...review,downloads:[{}]}));
waiting=new Promise(r=>resolve=r);const staleReview=el('Review').onclick();await Promise.resolve();el('Jobs').value='other';resolve(structuredClone(review));await staleReview;waiting=null;assert.equal(el('Results').children.length,0);
el('Kind').value='game';el('Kind').onchange();source.source.kind='game';await editor.bind();assert.equal(precisionRequest(source,'game','s1').source.kind,'game');
waiting=new Promise(r=>resolve=r);const staleBind=editor.bind();await Promise.resolve();el('Source').value='other';resolve(structuredClone(source));await assert.rejects(staleBind,/changed/);
console.log('Precision export editor bound-source, stale-selection, busy and typed-download checks passed.');
