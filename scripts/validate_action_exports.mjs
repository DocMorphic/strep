import fs from 'node:fs';
import path from 'node:path';
import validator from '../assets/viewer/node_modules/gltf-validator/index.js';
const root=path.resolve(process.argv[2]||'reports/action-coverage-v1');
const summary=JSON.parse(fs.readFileSync(path.join(root,'summary.json'),'utf8'));
const files=summary.trials.map(t=>`takes/${t.id}/soma.glb`);
const results=[];
for(const file of files){
 const report=await validator.validateBytes(new Uint8Array(fs.readFileSync(path.join(root,file))),{uri:file,maxIssues:1000});
 results.push({file,errors:report.issues.numErrors,warnings:report.issues.numWarnings,messages:report.issues.messages.filter(m=>m.severity<2)});
}
fs.writeFileSync(path.join(root,'export-validation.json'),JSON.stringify(results,null,2));
console.log({files:results.length,errors:results.reduce((n,r)=>n+r.errors,0),warnings:results.reduce((n,r)=>n+r.warnings,0)});
if(results.some(r=>r.errors))process.exitCode=1;
