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
 parts.push('Measured on fixed source foot vertices at 120 Hz and stance boundaries. Planted contact remains unverified.');
 return parts.join(' ');
}
