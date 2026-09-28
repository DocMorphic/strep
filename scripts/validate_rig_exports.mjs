import fs from 'node:fs';
import path from 'node:path';
import validator from '../assets/viewer/node_modules/gltf-validator/index.js';
const root=path.resolve(process.argv[2]);
const manifest=JSON.parse(fs.readFileSync(path.join(root,'manifest.json'),'utf8'));
const results=[];
for(const item of manifest.cases){
 const report=await validator.validateBytes(new Uint8Array(fs.readFileSync(path.join(root,item.path))),{uri:item.path,maxIssues:1000});
 results.push({file:item.path,errors:report.issues.numErrors,warnings:report.issues.numWarnings,messages:report.issues.messages.filter(m=>m.severity<2)});
}
fs.writeFileSync(path.join(root,'export-validation.json'),JSON.stringify(results,null,2));
console.log(results);
if(results.some(r=>r.errors))process.exitCode=1;
