import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {formatNativeContactDiagnostics as format,nativeSupportAuditUrl} from '../scripts/native-contact-diagnostics.mjs';
assert.equal(nativeSupportAuditUrl({result_url:'/fitter.json',native_conversion_url:'/native.json'}),'/native.json');
assert.equal(nativeSupportAuditUrl({result_url:'/fitter.json'}),'/fitter.json');
const metric=(drift,speed)=>({supports:[{id:'left',candidate:{maximum_patch_vertex_tangential_drift_m:drift,maximum_patch_vertex_tangential_speed_m_s:speed}}]});
assert.equal(format(null),'');
assert.match(format({}),/measurements unavailable/);
const retained=format({retained_input:true,selected_contact_diagnostics:metric(.005,.03),proposal_contact_diagnostics:metric(.00488,.0286)});
assert.match(retained,/Selected native clip · left: maximum drift 5.00 mm, maximum tangential speed 30.00 mm\/s/);
assert.match(retained,/Converted proposal · left: maximum drift 4.88 mm/);
assert.match(retained,/Planted contact remains unverified/);
assert.doesNotMatch(retained,/approved|satisfied|certified|passed/);
assert.match(format({selected_contact_diagnostics:metric(0,0)}),/drift 0.00 mm/);
for(const value of [NaN,Infinity,-.001,'0.005',undefined]){
 assert.match(format({selected_contact_diagnostics:metric(value,.03)}),/measurements unavailable/);
 assert.match(format({selected_contact_diagnostics:metric(.005,value)}),/measurements unavailable/);
}
const html=await readFile(new URL('../scripts/native-support-viewer.html',import.meta.url),'utf8');
const viewer=await readFile(new URL('../scripts/native-support-viewer.mjs',import.meta.url),'utf8');
assert.equal([...html.matchAll(/id="contacts"/g)].length,1);
assert.match(viewer,/el\('contacts'\)\.textContent=contactText/);
assert.doesNotMatch(viewer,/el\('contacts'\)\.innerHTML/);
console.log('Native foot-drift formatting, retained/proposed distinction and unavailable metrics pass; no browser/GPU claim.');
