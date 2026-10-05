import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createNativeTransferEditor} from '../scripts/native-transfer-editor.mjs';
class Element{constructor(){this.value='';this.disabled=false;this.children=[];this.hidden=true;this.src='';this.textContent='';}replaceChildren(...a){this.children=a;this.value=a[0]?.value??'';}append(...a){this.children.push(...a);}}
const html=await readFile(new URL('../scripts/native-transfer-editor.html',import.meta.url),'utf8'),nodes=new Map();
for(const m of html.matchAll(/<[^>]*id="(nativeTransfer[^"]+)"[^>]*>/g)){assert(!nodes.has(m[1]));nodes.set(m[1],new Element());}
const el=n=>nodes.get('nativeTransfer'+n),document={getElementById:id=>nodes.get(id),createElement:()=>new Element()};
el('Rate').value='120';const a='a'.repeat(64),b='b'.repeat(64),pa='c'.repeat(64),pb='d'.repeat(64),digest='e'.repeat(64);
const chars={characters:[{id:a,name:'Source'},{id:b,name:'Target'}]};
const source={asset_id:a,name:'Source',profile_id:pa,source_profile_ready:true,quality_approved:false,clips:[{index:0,name:'Wave',supported:true},{index:1,name:'Cubic',supported:false}]};
const target={asset_id:b,name:'Target',profile_id:pb,quality_approved:false};
const labels=['candidate.zip','transfer/character.glb','edit-profile.json','transfer/root-motion.json','transfer/report.json','audit/animation.res','audit/result.json','result.json'];
let metadataWaiting=null,reviewWaiting=null,buildWaiting=null,importWaiting=null,posted=[],opened=[];
let review={id:'job',status:'complete',source_skin_joints:19,target_skin_joints:17,quality_approved:false,release_approved:false,contact_verified:false,original_selected:true,
 transfer_fidelity:{passed:true},sampled_runtime_conditions_pass:true,result_sha256:digest,preview_url:`/native-transfer-viewer.html?id=job&result=${digest}`,downloads:labels.map(label=>({label,url:'/files/native-transfer-jobs/job/'+label}))};
const api=async url=>{
 if(url==='/api/characters')return structuredClone(chars);
 if(url.startsWith('/api/native-transfer-character?id='))return metadataWaiting||structuredClone(url.endsWith(a)?source:target);
 if(url==='/api/native-transfer-jobs')return {jobs:[{id:'job',status:'complete'}]};
 if(url.startsWith('/api/native-transfer-review?'))return reviewWaiting||structuredClone(review);
 throw Error(url);
};
const post=async(url,payload)=>{posted.push({url,payload:structuredClone(payload)});return url.endsWith('-assets')?(buildWaiting||{id:'job'}):(importWaiting||{asset_id:'f'.repeat(64),profile_id:'1'.repeat(64),quality_approved:false});};
const editor=createNativeTransferEditor({document,api,post,onImported:async id=>opened.push(id)});
assert.throws(()=>editor.snapshot(),/Bind/);await editor.characters();assert.equal(el('Source').value,a);assert.equal(el('Target').value,b);
await el('Bind').onclick();assert.equal(el('Clip').children.length,1);assert.deepEqual(editor.snapshot(),{source_asset_id:a,source_profile_id:pa,target_asset_id:b,target_profile_id:pb,animation_index:0,rate:120});
await el('Build').onclick();assert.equal(opened.length,0);assert.equal(el('Source').value,a);assert.equal(el('Jobs').value,'job');
await el('Review').onclick();assert.equal(el('Import').disabled,false);assert.equal(el('Preview').src,review.preview_url);assert.equal(el('Results').children.length,9);
await el('Import').onclick();assert.deepEqual(posted.at(-1),{url:'/api/native-transfer-import',payload:{job:'job',result_sha256:digest}});assert.equal(opened.length,1);
for(const field of ['quality_approved','release_approved','contact_verified','original_selected']){const old=review[field];review[field]=!old;await el('Review').onclick();assert.match(el('Status').textContent,/Invalid/);assert.equal(el('Import').disabled,true);review[field]=old;}
review.sampled_runtime_conditions_pass='false';await el('Review').onclick();assert.match(el('Status').textContent,/Invalid/);
review.sampled_runtime_conditions_pass=false;await el('Review').onclick();assert.equal(el('Import').disabled,true);assert.match(el('Status').textContent,/playback: fail/);
review.sampled_runtime_conditions_pass=true;const old=review.downloads[0].url;review.downloads[0].url='https://example.test';await el('Review').onclick();assert.match(el('Status').textContent,/Invalid/);review.downloads[0].url=old;
const completed=review;review={id:'job',status:'failed',error:'Retained input',downloads:[]};await el('Review').onclick();assert.match(el('Status').textContent,/Retained input/);assert.equal(el('Preview').hidden,true);review=completed;
el('Target').value=a;el('Target').onchange();assert.throws(()=>editor.snapshot(),/Bind/);el('Target').value=b;
let resolveMeta;metadataWaiting=new Promise(r=>resolveMeta=r);const binding=el('Bind').onclick();el('Source').value=b;el('Source').onchange();resolveMeta(source);await binding;assert.match(el('Status').textContent,/selection changed/);metadataWaiting=null;el('Source').value=a;await el('Bind').onclick();
let resolveBuild;buildWaiting=new Promise(r=>resolveBuild=r);const building=el('Build').onclick();assert.equal(el('Build').disabled,true);await el('Build').onclick();assert.match(el('Status').textContent,/Wait/);resolveBuild({id:'job'});await building;buildWaiting=null;
let resolveReview;reviewWaiting=new Promise(r=>resolveReview=r);const reviewing=el('Review').onclick();el('Jobs').value='other';el('Jobs').onchange();resolveReview(review);await reviewing;assert.match(el('Status').textContent,/selection changed/);reviewWaiting=null;el('Jobs').value='job';await el('Review').onclick();
let resolveImport;importWaiting=new Promise(r=>resolveImport=r);const importing=el('Import').onclick();el('Jobs').value='other';el('Jobs').onchange();resolveImport({asset_id:'f'.repeat(64),profile_id:'1'.repeat(64),quality_approved:false});await importing;assert.equal(opened.length,1);assert.match(el('Status').textContent,/not opened/);assert.equal(el('Import').disabled,true);
console.log('Offline native transfer selection, lifecycle, fixed downloads, rejected results, stale callbacks and explicit candidate import passed.');
