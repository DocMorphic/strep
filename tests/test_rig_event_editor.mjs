import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
class Element{
 constructor(){this.value='';this.textContent='';this.children=[];this.hidden=false;this.disabled=false;}
 replaceChildren(...children){this.children=children;}
 append(...children){this.children.push(...children);}
 setAttribute(){}
}
const html=await readFile(new URL('../scripts/character-events.html',import.meta.url),'utf8');
const elements=new Map([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));
for(const id of ['rigEvents','rigMappingPanel'])elements.set(id,new Element());
const C=id=>{assert(elements.has(id),id);return elements.get(id);};
const shift=(error)=>({operation:'clip_retime',rounded_timing_requires_review:true,timing_error_s:error});
let data={job_id:'clip',variant:'transfer',glb_sha256:'hash',frames:16,events:{events:[
 {id:'late',name:'grasp',frame:1,kind:'authored',requires_review:true,lineage:[shift(1/60)]},
 {id:'early',name:'release',frame:3,kind:'authored',requires_review:true,lineage:[shift(-1/90)]},
 {id:'unknown',name:'unknown cue',frame:4,kind:'authored'},
 {id:'exact',name:'exact cue',frame:8,kind:'authored',requires_review:false},
 {name:'transition_start',frame:0,kind:'authoring_boundary'}]}};
const model={};let state={job:{id:'clip',label:'Test clip'},variant:'transfer',model,frame:0,result:{}},posts=[],jumps=[],errors=[];
const context={document:{createElement:()=>new Element()},URLSearchParams,crypto:{randomUUID:()=> 'new-cue'}};
vm.createContext(context);
vm.runInContext((await readFile(new URL('../scripts/character-events.js',import.meta.url),'utf8'))+'\nglobalThis.create=createRigEventEditor;',context);
const editor=context.create({C,api:async()=>data,post:async(url,payload)=>{posts.push({url,payload});return {};},
 status:text=>errors.push(text),getContext:()=>state,seek:frame=>jumps.push(frame),pause:()=>{},closeEditors:()=>{},onJob:()=>{}});
await C('rigEvents').onclick();
const rows=()=>C('rigEventsList').children;
const button=(row,label)=>row.children.find(c=>c.textContent===label);
assert.match(rows()[0].children[0].textContent,/needs timing review.*\+16\.667 ms/);
assert.match(rows()[1].children[0].textContent,/-11\.111 ms/);
assert.match(rows()[2].children[0].textContent,/needs timing review/);
assert.match(rows()[3].children[0].textContent,/timing authored/);
assert.equal(button(rows()[3],'Confirm timing for exact cue'),undefined);
button(rows()[0],'Go to grasp').onclick();assert.deepEqual(jumps,[1]);
await C('rigEventsApply').onclick();
assert.equal(posts[0].payload.markers[0].confirmed,false);
assert.equal(posts[0].payload.markers[2].confirmed,false,'Missing confirmation cannot become approval on save');
button(rows()[0],'Confirm timing for grasp').onclick();
await C('rigEventsApply').onclick();
assert.equal(posts[1].payload.markers[0].confirmed,true);
assert.equal(posts[1].payload.markers[1].confirmed,false);
for(const marker of posts[1].payload.markers)assert.deepEqual(Object.keys(marker).sort(),['confirmed','frame','id','name']);
assert.equal(data.events.events[0].requires_review,true,'Draft confirmation must not mutate source evidence');
state={...state,variant:'corrected'};await C('rigEventsApply').onclick();
assert.equal(posts.length,2);assert.match(errors.at(-1),/Reopen/);
editor.reset();state={...state,variant:'transfer'};
data={...data,events:{events:[{id:'late',name:'new source cue',frame:2,kind:'authored',requires_review:false}]}};
await C('rigEvents').onclick();assert.doesNotMatch(rows()[0].children[0].textContent,/Previous speed edit/);
const bundled=await readFile(new URL('../scripts/action-studio.html',import.meta.url),'utf8');
assert(bundled.includes('confirmed:e.requires_review===false'));
assert(bundled.includes('Previous speed edit rounded'));
console.log('Event editor: explicit confirmation, rounding notes, preview, unchanged source, clean payload and source reset pass. DOM simulation only.');
