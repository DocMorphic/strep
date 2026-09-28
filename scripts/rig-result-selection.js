// Presentation policy only; retained candidates and their audit results are immutable.
function rigResultSelection(result, requested = null) {
 const variants=result.variants||{};
 const state=key=>{
  const variant=variants[key];
  if(key==='corrected'||variant.source_variant==='corrected')return result.correction_status||'unverified';
  if(key==='transfer'&&result.joint_edit_status)return result.joint_edit_status;
  if(key==='repeated'&&result.inherited_joint_edit)return result.joint_edit_status||'unverified';
  if(result.inherited_correction&&(key==='transfer'||key==='repeated'))return result.correction_status||'unverified';
  return null;
 };
 const failed=status=>['rejected','infeasible','unsupported'].includes(status);
 const passed=status=>['provisional_pass','numerical_screens_met'].includes(status);
 const options=Object.entries(variants).map(([key,v])=>{
  const status=state(key);
  const suffix=failed(status)?' · Failed checks':passed(status)?' · Numerical screens met':status?' · Unverified':'';
  return {key,label:v.label+suffix,status};
 });
 let selected=requested&&Object.hasOwn(variants,requested)?requested:null;
 if(!selected){
  if(variants.corrected&&passed(state('corrected')))selected='corrected';
  else if(variants.transfer&&(!state('transfer')||passed(state('transfer'))))selected='transfer';
  else if(variants.input)selected='input';
  else selected=variants.transfer?'transfer':options[0]?.key;
 }
 const selectedState=selected?state(selected):null;
 let message='';
 if(failed(selectedState))message='Showing a candidate that failed numerical checks. It remains available for comparison and further editing; it is not approved for use.';
 else if(passed(selectedState))message='Showing a candidate within its numerical screens. Action, contacts and naturalness still require review.';
 else if(selectedState)message='Showing an unverified candidate. Inspect its audit before using it.';
 else if(options.some(o=>failed(o.status)))message='Showing the retained input because the candidate failed numerical checks. This input is not quality-approved either. Select the failed candidate to compare or continue editing it.';
 else if(options.some(o=>o.status==='unverified'))message='Showing the retained input. The correction has no recorded numerical decision.';
 return {selected,options,message};
}
