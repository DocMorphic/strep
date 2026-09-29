import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
const source=await readFile(new URL('../scripts/contact-editor.js',import.meta.url),'utf8');
const html=await readFile(new URL('../scripts/action-studio.html',import.meta.url),'utf8');
class Element{
 constructor(tag='div'){this.tag=tag;this.children=[];this.attributes={};this.value='';this._text='';}
 set textContent(value){this._text=value;this.children=[];}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
 append(...items){this.children.push(...items);}
 replaceChildren(...items){this._text='';this.children=items;}
 setAttribute(name,value){this.attributes[name]=value;}
}
const elements=new Map([...html.matchAll(/id="(contact[^"]+)"/g)].map(m=>[m[1],new Element()]));
const context={document:{getElementById:id=>{assert(elements.has(id));return elements.get(id);},createElement:tag=>new Element(tag),createTextNode:text=>({textContent:text})},
 localStorage:{getItem:()=>null,setItem(){}},Option:class extends Element{constructor(text,value){super('option');this.textContent=text;this.value=value;}}};
vm.createContext(context);vm.runInContext(source+'\nglobalThis.rows=contactAuditRows;globalThis.editor=contactEditor;',context);
const sample=()=>({contacts:[{region:'LeftHand',start_frame:50,end_frame:70,samples:81,samples_over_5mm:0,maximum_error_m:.004}],
 phase_rates:[{region:'LeftHand',phase:'release',checked_ceilings:[2,90],variants:{candidate:[1,89]},candidate_excess_over_checked:[0,0]}],
 floor_nonregression:{maximum_added_depth_m:0},variants:{candidate:{maximum_floor_depth_m:.0004}},
 preservation:{all_outside_times:{samples:80,within_numerical_tolerance:true,maximum_errors:{joint_position_error_m:0,basis_error:0,skin_position_error_m:0}}}});
assert(context.rows(sample()).every(r=>r.status==='pass'));
assert(context.rows(sample()).some(r=>r.detail.includes('Total penetration: 0.4 mm')),'Zero added depth must not conceal inherited penetration');
assert(context.rows(null).every(r=>r.status==='unavailable'));
const tiny=sample();tiny.phase_rates[0].variants.candidate[0]=2+7.5e-8;tiny.floor_nonregression.maximum_added_depth_m=1e-12;
const rows=context.rows(tiny);assert.equal(rows.filter(r=>r.status==='fail').length,2);
assert.match(rows.find(r=>r.label.endsWith('speed')).detail,/Over by [1-9]/,'Positive excess cannot round to zero');
assert.match(rows.find(r=>r.label==='Added floor penetration').detail,/1e-9 mm added/);
for(const bad of [null,NaN,Infinity,-1,'0']){
 const audit=sample();audit.phase_rates[0].checked_ceilings[1]=bad;audit.contacts[0].maximum_error_m=bad;
 assert.equal(context.rows(audit).filter(r=>r.status==='unavailable').length,2);
}
const incomplete=sample();delete incomplete.preservation.all_outside_times.maximum_errors.basis_error;
assert.equal(context.rows(incomplete).at(-1).status,'unavailable');
const drift=sample();drift.preservation.all_outside_times.maximum_errors.skin_position_error_m=.0001;
assert.equal(context.rows(drift).at(-1).status,'fail','A contradictory true flag must not hide measured drift');
const missingCount=sample();delete missingCount.contacts[0].samples;
assert.equal(context.rows(missingCount)[0].status,'unavailable');
const mismatch=sample();mismatch.contacts[0].samples_over_5mm=1;
assert.equal(context.rows(mismatch)[0].status,'fail','A recorded miss cannot be hidden by a passing maximum');

const editor=context.editor;editor.mount({frame:()=>50,submit:async()=>{}});
const trial={id:'clip',frames:120,body_correction:{},support_correction:{checked_fit:true,export_audit:tiny}};
editor.load('contact-jobs/example/result',trial);
const result=elements.get('contactResult'),walk=e=>[e,...(e.children||[]).flatMap(walk)];
assert.match(result.textContent,/2 failed · 0 unavailable/);
assert(walk(result).find(e=>e.tag==='details').open);
assert.match(result.textContent,/do not approve the animation/);
assert(walk(result).some(e=>e.href==='/files/contact-jobs/example/result/takes/clip/checked-export-audit.json'&&e.rel==='noopener'));
const malicious=sample();malicious.contacts[0].region='<img src=x onerror=alert(1)>';
editor.load('contact-jobs/second/result',{...trial,id:'second',support_correction:{checked_fit:true,export_audit:malicious}});
assert(result.textContent.includes('<img src=x onerror=alert(1)>'));
assert(!walk(result).some(e=>e.tag==='img'),'Metadata is text, never HTML');
assert(!result.textContent.includes('2 failed'),'Changing clips clears stale failures');
editor.load('contact-jobs/third/result',{...trial,id:'third',support_correction:{checked_fit:true}});
assert.match(result.textContent,/0 failed · 4 unavailable/);
assert(!result.textContent.includes('LeftHand'),'Missing data does not reuse the previous clip');
assert(html.includes('function contactAuditRows(audit)')&&html.includes('id="contactResult" class="small"></div>'));
for(const [step,passed,expected] of [[0,false,'retained the fitted motion'],[.000001,true,'selected a corrected candidate']]){
 editor.load('contact-jobs/feedback/result',{...trial,id:'feedback-'+step,support_correction:{checked_fit:true,export_audit:sample(),export_feedback:{maximum_root_step_m:step,export_and_native_screen:passed}}});
 assert(result.textContent.includes(expected));assert(result.textContent.includes(passed?'sampled export and native checks pass':'measured constraints still fail'));
 assert(result.textContent.includes('Animation remains unapproved'));
 assert(walk(result).some(e=>e.href?.endsWith('/feedback-report.json')));
 assert(walk(result).some(e=>e.href?.endsWith('/initial-fit/motion.npz')));
}
editor.load('contact-jobs/missing-feedback/result',{...trial,id:'unknown-feedback',support_correction:{checked_fit:true,export_feedback:{maximum_root_step_m:NaN}}});
assert(result.textContent.includes('Export repair measurements unavailable'));
editor.load('contact-jobs/no-feedback/result',{...trial,id:'no-feedback',support_correction:{checked_fit:true,export_audit:sample()}});
assert(!result.textContent.includes('Export repair:')&&!walk(result).some(e=>e.href?.endsWith('/feedback-report.json')));
console.log('Contact export review: numeric limits, tiny failures, missing evidence, retained source penetration, safe text, stale-state clearing and audit links pass. No HTTP/browser used.');
