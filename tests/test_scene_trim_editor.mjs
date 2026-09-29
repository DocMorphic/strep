import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createSceneTrimEditor} from '../scripts/scene-trim-editor.js';
const html=await readFile(new URL('../scripts/action-studio.html',import.meta.url),'utf8');
class Element{constructor(){this.value='';this.disabled=false;this.events={};}addEventListener(n,f){this.events[n]=f;}replaceChildren(...children){this.children=children;}}
const elements=new Map([...html.matchAll(/id="(sceneTrim[^"]+)"/g)].map(m=>[m[1],new Element()]));
globalThis.document={createElement(){return new Element();},getElementById(id){assert(elements.has(id),'Missing '+id);return elements.get(id);}};
const storage=new Map();globalThis.localStorage={getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)};
let posted=null,completed=null,changed=false,reject=false;
const source={source_url:'/files/example/scene.json',revision:'v1',frames:180,actors:2,objects:0};
globalThis.fetch=async(url,options)=>{
 if(url.startsWith('/api/scene-trim-source'))return {ok:true,json:async()=>source};
 if(url==='/api/scene-trims'){posted=JSON.parse(options.body);return {ok:!reject,json:async()=>reject?{error:'Wait for the running job'}:{id:'trim1'}};}
 assert.equal(url,'/api/scene-trim-jobs');return {ok:true,json:async()=>({jobs:[{id:'trim1',status:'complete',collection:'scene-trim-jobs/trim1'}]})};
};
const editor=createSceneTrimEditor({getContext:()=>({changed,frame:60}),onComplete:async c=>{completed=c;}});
const el=n=>elements.get('sceneTrim'+n);
await editor.bind(source.source_url);assert.match(el('Status').textContent,/2 actor\(s\), 0 prop/);
el('UseFirst').onclick();el('UseLast').onclick();await el('Apply').onclick();assert.equal(posted,null);assert.match(el('Status').textContent,/at least three/);
el('Last').value=100;changed=true;await el('Apply').onclick();assert.equal(posted,null);assert.match(el('Status').textContent,/unsaved/);
changed=false;reject=true;await el('Apply').onclick();assert.equal(el('Apply').disabled,false);assert.match(el('Status').textContent,/running job/);
reject=false;await el('Apply').onclick();for(let i=0;i<5;i++)await new Promise(r=>setImmediate(r));
assert.equal(posted.first,60);assert.equal(posted.last,100);assert.equal(posted.revision,'v1');assert.equal(completed,'scene-trim-jobs/trim1');assert.equal(storage.get('strep:trim-active-job'),undefined);
assert.match(el('Status').textContent,/unapproved/);
await editor.bind(source.source_url);assert.equal(Number(el('First').value),60);assert.equal(Number(el('Last').value),100);
editor.reset();assert.equal(el('Apply').disabled,true);
globalThis.localStorage={getItem(){throw Error('Denied');},setItem(){throw Error('Denied');},removeItem(){throw Error('Denied');}};
const privateEditor=createSceneTrimEditor({getContext:()=>({changed:false,frame:0}),onComplete:async()=>{}});
await privateEditor.bind(source.source_url);assert.equal(el('Apply').disabled,false);
console.log('Scene trim editor: clock range, unsaved source, busy rejection, submission, recovery and private storage pass. No HTTP/browser used.');

el('Mode').value='retime';el('Mode').events.input();assert(el('First').disabled);assert(!el('Speed').disabled);
el('Speed').value=0;posted=null;await el('Apply').onclick();assert.equal(posted,null);
el('Speed').value=1.5;el('Speed').events.input();assert.match(el('Timing').textContent,/actual speed/);
await el('Apply').onclick();for(let i=0;i<5;i++)await new Promise(r=>setImmediate(r));
assert.equal(posted.operation,'retime');assert.equal(posted.frames,120);assert.equal(posted.first,undefined);

el('Mode').value='carry';el('Mode').events.input();posted=null;await el('Apply').onclick();assert.equal(posted,null);
source.actor_ids=['A','B'];source.object_ids=['platform'];source.objects=1;
await privateEditor.bind(source.source_url);el('Mode').value='carry';el('Mode').events.input();
assert(!el('Actor').disabled);assert(el('Speed').disabled);assert(!el('CarryFields').hidden);
el('Reference').value=180;await el('Apply').onclick();assert.equal(posted,null);
el('Reference').value=37;await el('Apply').onclick();for(let i=0;i<5;i++)await new Promise(r=>setImmediate(r));
assert.equal(posted.operation,'carry');assert.equal(posted.actor,'A');assert.equal(posted.object,'platform');assert.equal(posted.reference_frame,37);assert.equal(posted.frames,undefined);

source.actors_with_carrier_motion=['A'];await privateEditor.bind(source.source_url);el('Mode').value='carry';el('Mode').events.input();
assert.match(el('CarryNote').textContent,/does not replace/);el('Actor').value='B';el('Actor').events.input();assert.equal(el('CarryNote').textContent,'');
