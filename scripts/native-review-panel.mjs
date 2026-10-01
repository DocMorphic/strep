// Native clips keep their own seconds clock; the existing scene editor is separate.
export function createNativeReviewPanel({document=globalThis.document,fetch=globalThis.fetch,Option=globalThis.Option,MutationObserver=globalThis.MutationObserver}={}){
  const el=id=>document.getElementById(id),panel=el('nativeReviewPanel'),select=el('nativeReviewSelect'),frame=el('nativeReviewFrame'),status=el('nativeReviewStatus');
  let reviews=[],serial=0;
  function unload(){frame.removeAttribute('src');frame.hidden=true;}
  async function refresh(){
    const token=++serial;unload();el('nativeReviewOpen').disabled=true;status.textContent='Checking saved native comparisons…';
    try{
      const response=await fetch('/api/native-contact-reviews',{cache:'no-store'});if(!response.ok)throw Error('Comparisons unavailable');
      const data=await response.json();if(token!==serial||!panel.open)return;
      reviews=data.reviews.filter(r=>typeof r.id==='string'&&/^[a-zA-Z0-9_-]{1,80}$/.test(r.id)&&r.viewer_url===`/files/native-contact-reviews/${r.id}/viewer.html`&&/^[0-9a-f]{64}$/.test(r.build_sha256)&&r.quality_approved===false);
      const previous=select.value;select.replaceChildren(...reviews.map(r=>new Option(`${r.label} · ${r.versions} alternatives`,r.id)));if(reviews.some(r=>r.id===previous))select.value=previous;
      select.disabled=!reviews.length;el('nativeReviewOpen').disabled=!reviews.length;
      status.textContent=reviews.length?`Choose a comparison. ${data.rejected.length?data.rejected.length+' package(s) failed integrity checks.':''}`:'No verified native comparisons available.';
    }catch(error){if(token===serial){reviews=[];select.replaceChildren();select.disabled=true;status.textContent=error.message;}}
  }
  el('nativeReviewOpen').onclick=()=>{const review=reviews.find(r=>r.id===select.value);if(!review||!panel.open)return;frame.src=review.viewer_url+'?build='+review.build_sha256;frame.hidden=false;status.textContent='Development comparison: observations do not approve animation quality.';};
  select.onchange=unload;
  el('nativeReviewRefresh').onclick=refresh;
  panel.addEventListener('toggle',()=>{if(panel.open)void refresh();else{++serial;unload();}});
  const owner=panel.closest?.('.window');
  if(owner&&MutationObserver)new MutationObserver(()=>{if(owner.hidden)frame.contentWindow?.postMessage('strep-native-pause',globalThis.location.origin);}).observe(owner,{attributes:true,attributeFilter:['hidden']});
  if(panel.open)void refresh();
  return {refresh,unload};
}
