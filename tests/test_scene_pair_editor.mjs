import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createScenePairEditor} from '../scripts/scene-pair-editor.js';
const html=await readFile(new URL('../scripts/action-studio.html',import.meta.url),'utf8');
class Element{
 constructor(){this.value='';this.children=[];this.events={};this.style={};}
 addEventListener(n,f){this.events[n]=f;}setAttribute(){}replaceChildren(...v){this.children=v;}append(...v){this.children.push(...v);}
 get selectedOptions(){return this.children.filter(c=>c.selected);}
}
const elements=new Map([...html.matchAll(/id="(scenePair[^"]+)"/g)].map(m=>[m[1],new Element()]));
globalThis.document={createElement:()=>new Element(),getElementById:id=>{assert(elements.has(id),'Missing '+id);return elements.get(id);}};
const stored=new Map();globalThis.localStorage={getItem:k=>stored.get(k)||null,setItem:(k,v)=>stored.set(k,v),removeItem:k=>stored.delete(k)};
const el=n=>elements.get('scenePair'+n);
const source={source_url:'/files/saved/scene.json',revision:'one',duration_s:3.7,actors:{Runner:{joints:['Shoulder','Elbow']},Partner:{joints:['Wrist']}},contacts:[{id:'touch',seconds:[2.0917225950783,2.0917225950783]}]};
let posted=null,changed=false,completed=null,reject=false,accepted=false,terminal='complete';
globalThis.fetch=async(url,options)=>{
 if(url.startsWith('/api/scene-pair-source'))return{ok:true,json:async()=>source};
 if(url==='/api/scene-pair-fits'){posted=JSON.parse(options.body);return{ok:!reject,json:async()=>reject?{error:'Wait for the local worker'}:{id:'pair1'}};}
 assert.equal(url,'/api/scene-pair-jobs');return{ok:true,json:async()=>({jobs:[{id:'pair1',status:terminal,collection:'scene-region-jobs/paired-one',default_scene:accepted?'candidate':'source',accepted_local_step:accepted,error:'Preserved failed attempt'}]})};
};
const editor=createScenePairEditor({getContext:()=>({changed,frame:62.75167785234899}),onComplete:async(...args)=>{completed=args;}});
const flush=async()=>{for(let i=0;i<8;i++)await new Promise(r=>setImmediate(r));};
await editor.bind(source.source_url);assert.equal(Number(el('Start').value),source.contacts[0].seconds[0]-.5);
await el('Apply').onclick();assert.equal(posted,null);assert.match(el('Status').textContent,/1–8/);
const selects=()=>el('Actors').children.map(label=>label.children[1]);
for(const select of selects())select.children[0].selected=true;
changed=true;await el('Apply').onclick();assert.equal(posted,null);assert.match(el('Status').textContent,/unsaved/);
changed=false;el('Budget').value=46;await el('Apply').onclick();assert.equal(posted,null);
el('Budget').value=5;reject=true;await el('Apply').onclick();assert(!el('Apply').disabled);assert.match(el('Status').textContent,/local worker/);
reject=false;await el('Apply').onclick();await flush();assert.deepEqual(completed,['scene-region-jobs/paired-one','source']);
assert.match(el('Status').textContent,/No correction passed/);assert.equal(stored.get('strep:pair-active-job'),undefined);
assert.equal(posted.request.revision,'one');assert.deepEqual(posted.request.protected_contact_ids,['touch']);
assert.deepEqual(posted.request.actors,{Runner:{joints:['Shoulder']},Partner:{joints:['Wrist']}});
assert.equal(posted.request.knots_s[0],posted.request.window_s[0]);assert.equal(posted.request.knots_s[4],posted.request.window_s[1]);
await editor.bind(source.source_url);assert.equal(selects()[0].selectedOptions.length,1);el('UseStart').onclick();assert.equal(Number(el('Start').value),62.75167785234899/30);
accepted=true;await el('Apply').onclick();await flush();assert.equal(completed[1],'candidate');
terminal='failed';completed=null;await el('Apply').onclick();await flush();assert.equal(completed,null);assert.match(el('Status').textContent,/Preserved failed attempt/);
editor.reset();assert(el('Apply').disabled);
// A slow old source cannot rebind controls after a later selection.
let release;globalThis.fetch=async url=>({ok:true,json:()=>url.includes('old')?new Promise(r=>{release=r;}):Promise.resolve({...source,revision:'new'})});
const old=editor.bind('old');await flush();await editor.bind('new');release({...source,revision:'old'});await old;
assert.equal(el('Start').value,source.contacts[0].seconds[0]-.5);
globalThis.localStorage={getItem(){throw Error('Denied');},setItem(){throw Error('Denied');},removeItem(){throw Error('Denied');}};
const privateEditor=createScenePairEditor({getContext:()=>({changed:false,frame:0}),onComplete:async()=>{}});await privateEditor.bind('new');assert(!el('Apply').disabled);
console.log('Paired controls: exact seconds, both actors, protected contacts, immutable revision, busy/error handling, retained-source outcome, saved drafts and stale binds pass. No browser used.');
