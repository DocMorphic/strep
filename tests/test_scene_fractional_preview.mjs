import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
const source=await readFile(new URL('../scripts/scene-viewer.js',import.meta.url),'utf8');
const helper=source.slice(source.indexOf('function sceneContactSample('),source.indexOf('const sceneStudio='));
const context={};vm.createContext(context);vm.runInContext(helper,context);
const sample=context.sceneContactSample;
const track=Array.from({length:150},(_,i)=>[i,i*2,-i]);
assert.deepEqual(Array.from(sample(track,66.75)),[66.75,133.5,-66.75]);
for(const f of [0,66,149])assert.deepEqual(Array.from(sample(track,f)),track[f]);
const p=sample(track,2);p[0]=99;assert.equal(track[2][0],2);
for(const f of [-1,150,NaN,Infinity])assert.throws(()=>sample(track,f));
assert.throws(()=>sample([[0,NaN,0]],0));
// Exercise the actual contact function at the formerly crashing jump time.
const start=source.indexOf(' function points(contact)'),end=source.indexOf(' function dispose()',start);
context.bundle={native_contact_tracks:{touch:{actual:track,target:track.map(p=>p.map(v=>v+1))}}};
context.spec={actors:{A:{transform:{}},B:{transform:{}}}};context.frame=66.75;
context.transform=p=>p;context.vec=p=>p;
vm.runInContext(source.slice(start,end),context);
const found=context.points({id:'touch',actor:'A',target:{space:'actor',actor:'B'}});
assert.deepEqual(Array.from(found.actual),[66.75,133.5,-66.75]);
assert.deepEqual(Array.from(found.desired),[67.75,134.5,-65.75]);
assert.match(source,/interpolated marker gap \(approximate\)/);
// Integer-only editors must enclose or floor the fractional preview time.
for(const [file,startToken,endToken,contextValue,expected] of [
 ['scene-trim-editor.js',"by('UseFirst').onclick=",';\n by(',66.75,66],
 ['scene-trim-editor.js',"by('UseLast').onclick=",';\n async ',66.75,67],
 ['scene-region-editor.js',"by('UseFrame').onclick=",';',66.75,66],
 ['scene-release-editor.js',"by('sceneReleaseSample').onclick=",';',66.75,66]]){
 const text=(await readFile(new URL('../scripts/'+file,import.meta.url),'utf8')).replaceAll('\r\n','\n');
 const from=text.indexOf(startToken)+startToken.length,through=text.indexOf('};',from)+1;
 const elements=new Map();const by=id=>{if(!elements.has(id))elements.set(id,{value:null});return elements.get(id);};
 const c={by,source:{},busy:false,getContext:()=>({frame:contextValue}),store(){},capture(){},storeDraft(){}};
 vm.createContext(c);vm.runInContext('var handler='+text.slice(from,through),c);c.handler();
 assert.equal([...elements.values()][0].value,expected,file);
}
console.log('Fractional partner jump, source/partner contact markers, endpoints, invalid samples and integer edit bounds pass. No browser/rendering claim.');
