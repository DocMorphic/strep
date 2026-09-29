import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
const html=await readFile(new URL('../scripts/action-studio.html',import.meta.url),'utf8');
class Element{constructor(){this.value='';this.textContent='';this.children=[];}replaceChildren(...c){this.children=c;}append(...c){this.children.push(...c);}setAttribute(){}}
const elements=new Map([...html.matchAll(/id="(contact[^"]+)"/g)].map(m=>[m[1],new Element()]));
const el=n=>elements.get('contact'+n);const storage=new Map();let calls=[];
const context={document:{getElementById:id=>{assert(elements.has(id));return elements.get(id);},createElement:()=>new Element(),createTextNode:text=>({textContent:text})},
 Option:class extends Element{constructor(text,value){super();this.textContent=text;this.value=value;}},
 localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},console};
vm.createContext(context);vm.runInContext((await readFile(new URL('../scripts/contact-editor.js',import.meta.url),'utf8'))+'\nglobalThis.editor=contactEditor;',context);
const editor=context.editor;editor.mount({frame:()=>40,submit:async(...args)=>calls.push(args)});
const trial={id:'test',frames:180,body_correction:{}};
editor.load('body-contact-v1',trial);el('WindowStart').value=20;el('WindowEnd').value=159;el('WindowStart').oninput();
await el('Check').onclick();assert.equal(calls.length,1);assert.equal(JSON.stringify(calls[0][2]),JSON.stringify({edit_window:[20,159]}));
editor.setBusy(false);await el('Apply').onclick();assert.equal(calls[1][2],undefined,'Legacy correction receives no rate policy');
editor.setBusy(false);el('WindowStart').value=0;await el('Check').onclick();assert.equal(calls.length,2);assert.match(el('Status').textContent,/held interior/);
const job={id:'job1',source:'body-contact-v1/takes/test',timing_message:'Three conflicts',timing_report:'/files/contact-jobs/job1/window-preflight.txt',bound_contacts:'/files/contact-jobs/job1/bound-contact-spec.json'};
editor.showTiming({...job,source:'other/takes/test'});assert.equal(el('TimingResult').textContent,'');
editor.showTiming(job);assert.match(el('TimingResult').textContent,/current draft may differ/);assert.match(el('TimingResult').textContent,/Three conflicts/);
assert.equal(el('TimingLinks').children.length,2);
el('Status').textContent='New draft';editor.showTiming(job);assert.equal(el('Status').textContent,'New draft','Polling must not overwrite new draft messages');
editor.load('other',trial);editor.load('body-contact-v1',trial);assert.equal(Number(el('WindowStart').value),20);assert.equal(Number(el('WindowEnd').value),159);
assert.match(html,/timing_check:timingCheck/);assert.match(html,/needs_authoring_change/);
console.log('Contact timing UI: distinct check payload, unchanged legacy apply, held bounds, source-matched results, safe links, persistence and polling pass. No HTTP/browser used.');

const checked={...job,id:'contact-jobs/checked1/result',status:'checked',check_schema_version:3,check_revision:'a'.repeat(64)};
editor.setBusy(false);editor.showTiming({...checked,status:'needs_authoring_change'});
assert(el('FitChecked').disabled);const count=calls.length;await el('FitChecked').onclick();assert.equal(calls.length,count);
editor.showTiming({...checked,id:'contact-jobs/checked2/result'});assert(!el('FitChecked').disabled);
await el('FitChecked').onclick();assert.equal(calls.length,count+1);
assert.equal(JSON.stringify(calls.at(-1)[3]),JSON.stringify({checked_plan:'checked2',revision:'a'.repeat(64)}));
assert.equal(calls.at(-1)[1],null,'Fit sends saved identity instead of substituting the current draft');
editor.setBusy(false);editor.load('contact-jobs/fit/result',{...trial,support_correction:{checked_fit:true}});
const descendants=e=>[e,...(e.children||[]).flatMap(descendants)];
assert(descendants(el('Result')).some(a=>a.href?.endsWith('/checked-export-audit.json')));
editor.load('body-contact-v1',trial);editor.setBusy(false);editor.showTiming({...checked,id:'contact-jobs/legacy/result',check_schema_version:2});
assert(el('FitChecked').disabled);assert.match(el('TimingResult').textContent,/predates pose-screen/);
const legacyCount=calls.length;await el('FitChecked').onclick();assert.equal(calls.length,legacyCount);
editor.showTiming({...checked,id:'contact-jobs/pose-conflict/result',status:'needs_authoring_change',timing_message:'LeftHand requires 53.65 cm; current body screen permits 22.00 cm.',pose_report:'/files/contact-jobs/pose-conflict/pose-preflight.json'});
assert(el('FitChecked').disabled);assert.match(el('TimingResult').textContent,/53.65 cm/);
assert(el('TimingLinks').children.some(a=>a.href==='/files/contact-jobs/pose-conflict/pose-preflight.json'));
console.log('Checked fit UI: conflict rejection, exact saved revision payload and separate exported audit link pass.');
