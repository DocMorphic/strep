(() => {
  const $ = id => document.getElementById(id);
  let iconCounter=0;
  const paths={
    compose:'<path d="M22 15h17l8 8v27H22z" fill="white" opacity=".95"/><path d="M39 15v9h8" fill="none" stroke="#e0ccff" stroke-width="2"/><path d="m20 42 17-17 5 5-17 17-7 2z" fill="#f8ca61" stroke="#916230" stroke-width="1"/>',
    library:'<path d="M10 21q0-4 4-4h13l5 5h19q3 0 3 4v22H10z" fill="#baefff"/><path d="M9 27q0-3 3-3h40q3 0 3 3v22q0 3-3 3H12q-3 0-3-3z" fill="#54c6f5" stroke="#e7ffff" stroke-width=".8"/><path d="M12 28h40" stroke="#dcfbff" opacity=".7"/>',
    preview:'<rect x="11" y="13" width="42" height="34" rx="5" fill="#effaff"/><rect x="14" y="16" width="36" height="28" rx="3" fill="#397bdd"/><path d="m27 22 13 8-13 8z" fill="white"/><path d="M25 51h14M32 47v4" stroke="white" stroke-width="3" stroke-linecap="round"/>',
    character:'<circle cx="32" cy="17" r="8" fill="white"/><path d="M23 30q9-5 18 0l5 18H18z" fill="#e0f0ff"/><path d="M26 46v10m12-10v10" stroke="white" stroke-width="5" stroke-linecap="round"/>',
    scene:'<rect x="8" y="26" width="20" height="23" rx="3" fill="#ffe2ab"/><circle cx="44" cy="20" r="7" fill="white"/><path d="M44 30v14m-9-9h18m-9 9-8 10m8-10 8 10" stroke="white" stroke-width="5" stroke-linecap="round"/>',
    inspector:'<circle cx="29" cy="28" r="13" fill="#effcff" fill-opacity=".85" stroke="white" stroke-width="3"/><path d="m39 38 11 12" stroke="#e1eeff" stroke-width="7" stroke-linecap="round"/><path d="M22 32v-8m7 12V21m7 11v-7" stroke="#127aaa" stroke-width="3" stroke-linecap="round"/>',
    jobs:'<rect x="9" y="12" width="46" height="40" rx="5" fill="#162b2b" stroke="#b8d5cf" stroke-width="2"/><path d="M11 23h42M11 33h42M11 43h42M22 14v36M33 14v36M44 14v36" stroke="#ffffff16"/><path d="M12 34h9l5-13 8 23 5-13h13" fill="none" stroke="#55f1a2" stroke-width="2.7" stroke-linejoin="round"/>',
    settings:'<g fill="none" stroke="#4f5663" stroke-width="5"><circle cx="32" cy="32" r="17" stroke-dasharray="7 3"/><circle cx="32" cy="32" r="12"/><circle cx="32" cy="32" r="5"/></g>',
    guide:'<path d="M17 11h22l10 10v33H17z" fill="#fff"/><path d="M39 11v11h10" fill="#d8e6f6"/><path d="M24 30h18M24 36h18M24 42h12" stroke="#8d9fb6" stroke-width="2"/>'
  };
  const colors={compose:['#cc8bff','#8752df'],library:['#bce5ff','#6fb9ec'],preview:['#91c8ff','#407bde'],inspector:['#66e1f2','#1089b7'],jobs:['#a9bcbf','#6a818d'],settings:['#e6eaf1','#a4aab6'],guide:['#e5edfc','#acbdd4']};
  function icon(name){const id='app-icon-'+(++iconCounter),c=colors[name]||colors.preview;return `<svg viewBox="0 0 64 64" aria-hidden="true"><defs><linearGradient id="${id}" x2="0" y2="1"><stop stop-color="${c[0]}"/><stop offset="1" stop-color="${c[1]}"/></linearGradient></defs><rect x="2" y="2" width="60" height="60" rx="14" fill="url(#${id})" stroke="#ffffffa0"/><rect x="4" y="4" width="56" height="56" rx="12" fill="none" stroke="#ffffff25"/>${paths[name]||paths.preview}</svg>`;}
  document.querySelectorAll('[data-icon]').forEach(el=>el.innerHTML=icon(el.dataset.icon));
  __WINDOW_MANAGER__
  let library=[];function drawLibrary(){const query=$('librarySearch').value.toLowerCase();const filtered=library.filter(t=>(t.label+' '+t.seed+' '+t.request.segments.map(s=>s.prompt).join(' ')).toLowerCase().includes(query));$('libraryCount').textContent=library.length+' clips';$('libraryList').replaceChildren();$('libraryEmpty').hidden=filtered.length>0;
    for(const t of filtered){const b=document.createElement('button');b.className='motion-file';b.dataset.take=t.id;b.innerHTML=icon('preview');const title=document.createElement('strong');title.textContent=t.label;const sub=document.createElement('small');sub.textContent=`${t.duration_s.toFixed(1)}s · seed ${t.seed}`;const mark=document.createElement('span');mark.className='file-mark';mark.textContent=t.flags.length?'◇ Review flags':'○ Unreviewed';b.append(title,sub,mark);b.onclick=()=>{window.dispatchEvent(new CustomEvent('strep:select',{detail:t.id}));open('preview');};$('libraryList').append(b);}}
  $('librarySearch').oninput=drawLibrary;window.addEventListener('strep:library',e=>{library=e.detail;drawLibrary();});
  window.addEventListener('strep:take',e=>{const t=e.detail;$('previewTitle').textContent=t.label;$('inspectName').textContent=t.label+' / seed '+t.seed;$('clipFooter').textContent=`${t.frames} frames · 30 fps · SOMA77`;$('libraryList').querySelectorAll('button').forEach(b=>b.classList.toggle('selected',b.dataset.take===t.id));if(focused==='preview')$('menuApp').textContent=t.label;});
  initializeDesktop();
})();
