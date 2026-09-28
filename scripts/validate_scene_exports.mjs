import fs from 'node:fs';
import path from 'node:path';
import validator from '../assets/viewer/node_modules/gltf-validator/index.js';
const root=path.resolve(process.argv[2]),results=[];
for(const name of fs.readdirSync(root,{recursive:true}).filter(n=>n.endsWith('.glb'))){
 const file=name.replaceAll('\\','/');
 const result=await validator.validateBytes(new Uint8Array(fs.readFileSync(path.join(root,file))),{uri:file,maxIssues:1000});
 results.push({file,errors:result.issues.numErrors,warnings:result.issues.numWarnings,messages:result.issues.messages.filter(m=>m.severity<2)});
}
if(!results.length)throw new Error('No scene GLBs found');
fs.writeFileSync(path.join(root,'export-validation.json'),JSON.stringify(results,null,2)+'\n');
console.log({files:results.length,errors:results.reduce((n,r)=>n+r.errors,0),warnings:results.reduce((n,r)=>n+r.warnings,0)});
if(results.some(r=>r.errors))process.exitCode=1;
