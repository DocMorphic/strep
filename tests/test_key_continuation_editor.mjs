import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createKeyContinuationEditor,checkedReview} from '../scripts/key-continuation-editor.mjs';
class Element{constructor(){this.value='';this.disabled=false;this.children=[];this.textContent='';}replaceChildren(...items){this.children=items;this.value=items[0]?.value??'';}append(...items){this.children.push(...items);}}
const html=await readFile(new URL('../scripts/key-continuation-editor.html',import.meta.url),'utf8');
const app=await readFile(new URL('../scripts/action-studio.html',import.meta.url),'utf8');assert(app.replaceAll('\r\n','\n').includes(html.replaceAll('\r\n','\n').trim()));
const nodes=new Map();for(const m of html.matchAll(/<[^>]*id="(keyContinuation[^"]+)"[^>]*>/g)){assert(!nodes.has(m[1]));const n=new Element();n.value=m[0].match(/value="([^"]*)"/)?.[1]??'';nodes.set(m[1],n);}
const document={getElementById:id=>nodes.get(id),createElement:()=>new Element()};const el=n=>nodes.get('keyContinuation'+n);
const source={id:'a'.repeat(64),label:'Verified saved correction',controls:372,rate_failures:47,floor_failures:18};
const flags={original_selected:true,quality_approved:false,release_approved:false};
let catalog={schema:'strep-studio-key-continuation-catalog-v1',sources:[source],...flags};let posted,posting,waiting,count=0;
const makeReview=()=>({schema:'strep-studio-key-continuation-review-v1',id:'keys-one',status:'complete',completion_sha256:'c'.repeat(64),full_replay_pass:true,sampled_conditions_pass:false,rate_failures:41,floor_failures:17,...flags,
 downloads:['input/saved-start.glb','study/probes/final/character.glb','study/result.json','replay/result.json'].map(n=>({url:`/files/key-continuation-jobs/keys-one/${n}`,label:n,sha256:'b'.repeat(64)}))});
let review=makeReview();
const api=async url=>url==='/api/key-continuation-sources'?catalog:url==='/api/key-continuation-jobs'?{jobs:[{id:'keys-one',status:'complete'}]}:waiting??review;
const post=async(url,value)=>{assert.equal(url,'/api/key-continuations');posted=structuredClone(value);count++;return posting??{id:'keys-one'};};
const editor=createKeyContinuationEditor({document,api,post});
assert.throws(()=>editor.request(),/Choose/);await editor.load();assert.equal(el('Build').disabled,false);assert.match(el('SourceInfo').textContent,/47.*18/);
assert.deepEqual(editor.request(),{schema:'strep-studio-key-continuation-v1',source_id:source.id,iterations:2});
for(const value of ['0','5','true','1.5']){el('Iterations').value=value;assert.throws(()=>editor.request(),/1–4/);}el('Iterations').value='2';
let resolve;posting=new Promise(r=>resolve=r);const build=el('Build').onclick();await el('Build').onclick();assert.equal(count,1);assert.match(el('Status').textContent,/Wait/);resolve({id:'keys-one'});await build;posting=null;assert.equal(el('Jobs').value,'keys-one');assert.equal(el('Build').disabled,false);
await el('Review').onclick();assert.match(el('Status').textContent,/41.*17.*fails acceptance/);assert.equal(el('Results').children.length,6);assert.equal(el('Results').children.at(-1).textContent,'Open comparison');assert.equal(el('Results').children.at(-1).href,'/key-continuation-viewer.html?id=keys-one&completion='+'c'.repeat(64));assert.equal(el('Preview').hidden,false);assert.equal(el('Preview').src,'/key-continuation-viewer.html?id=keys-one&completion='+'c'.repeat(64));
for(const fault of ['approval','release','replay','url','hash','missing','contradiction','negative']){
 const v=makeReview();if(fault==='approval')v.quality_approved=true;else if(fault==='release')v.release_approved=true;else if(fault==='replay')v.full_replay_pass=false;
 else if(fault==='url')v.downloads[0].url+='?x=1';else if(fault==='hash')v.downloads[0].sha256='bad';else if(fault==='missing')v.downloads.pop();else if(fault==='contradiction')v.sampled_conditions_pass=true;else v.floor_failures=-1;
 assert.throws(()=>checkedReview(v,'keys-one'));
}
review={...makeReview(),status:'failed',downloads:[]};await el('Review').onclick();assert.equal(el('Results').children.length,1);assert.match(el('Status').textContent,/failed/);assert.equal(el('Preview').hidden,true);
assert.throws(()=>checkedReview({...review,downloads:makeReview().downloads},'keys-one'),/Incomplete/);
review=makeReview();waiting=new Promise(r=>resolve=r);const reading=el('Review').onclick();el('Jobs').value='other';resolve(review);await reading;waiting=null;assert.match(el('Status').textContent,/selection changed/);
catalog={...catalog,sources:[]};await editor.load();assert.equal(el('Build').disabled,true);assert.throws(()=>editor.request(),/Choose/);
catalog={...catalog,sources:[source,{...source}]};await el('Sources').onclick();assert.match(el('Status').textContent,/Invalid/);
console.log('key continuation editor checks passed');
