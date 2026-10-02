// Display measured drift without turning height/rate checks into contact approval.
export function nativeSupportAuditUrl(review){return review.native_conversion_url||review.result_url;}
export function formatNativeContactDiagnostics(report){
 if(!report)return '';
 const rows=(diagnostic,version)=>{
  if(!Array.isArray(diagnostic?.supports)||!diagnostic.supports.length)return `${version}: measurements unavailable.`;
  return diagnostic.supports.map(row=>{
   const value=row.candidate,drift=value?.maximum_patch_vertex_tangential_drift_m,speed=value?.maximum_patch_vertex_tangential_speed_m_s;
   if(!Number.isFinite(drift)||drift<0||!Number.isFinite(speed)||speed<0)return `${version} · ${row.id}: measurements unavailable.`;
   return `${version} · ${row.id}: maximum drift ${(drift*1000).toFixed(2)} mm, maximum tangential speed ${(speed*1000).toFixed(2)} mm/s.`;
  }).join(' ');
 };
 const parts=[rows(report.selected_contact_diagnostics,'Selected native clip')];
 if(report.proposal_contact_diagnostics)parts.push(rows(report.proposal_contact_diagnostics,'Converted proposal'));
 parts.push(report.selected_planting_audit?'Drift diagnostic on fixed source vertices. Explicit planting gates are reported separately; animation quality remains unapproved.':'Measured on fixed source foot vertices at 120 Hz and stance boundaries. Planted contact remains unverified.');
 return parts.join(' ');
}

export function formatNativePlanting(planting){
 if(!planting)return '';
 const audit=planting.selected_audit,contacts=audit?.contacts;
 if(!Array.isArray(contacts)||!contacts.length)return 'Selected planted-contact checks unavailable.';
 const finite=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0,mm=v=>Number((v*1000).toPrecision(9)).toString();
 let allContactsPass=true;
 const rows=contacts.map(row=>{
  if(![row.maximum_patch_anchor_error_m,row.maximum_patch_speed_m_s,row.maximum_anchor_error_m,row.maximum_speed_m_s].every(finite)||typeof row.passed!=='boolean'){allContactsPass=false;return `${row.id||'Foot'}: checks unavailable.`;}
  const pass=row.passed&&row.maximum_patch_anchor_error_m<=row.maximum_anchor_error_m&&row.maximum_patch_speed_m_s<=row.maximum_speed_m_s;
  allContactsPass=allContactsPass&&pass;
  return `${row.id||'Foot'}: ${pass?'contact gates pass':'contact gates fail'}; source-anchor error ${mm(row.maximum_patch_anchor_error_m)} / ${mm(row.maximum_anchor_error_m)} mm; patch speed ${mm(row.maximum_patch_speed_m_s)} / ${mm(row.maximum_speed_m_s)} mm/s.`;
 });
 rows.push(audit.passed===true&&allContactsPass?'All configured sampled planting, support and rate gates pass. Animation quality remains unapproved.':'Full planting acceptance has not passed; contact precision alone cannot approve this clip.');
 return rows.join(' ');
}
