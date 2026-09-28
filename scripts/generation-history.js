// Original generation intent retained by a package, independent of its current pose.
function createGenerationHistoryPanel(host) {
  let version = 0, controller = null, current = null;
  const summary = host.querySelector('summary');
  const body = host.querySelector('.generation-history-body');
  const node = (tag, text, cls) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = String(text);
    if (cls) el.className = cls;
    return el;
  };
  function packageURL(path, base) {
    if (typeof path !== 'string' || !path || /[\\?#%]/.test(path)) throw Error('Invalid package path');
    if (path.split('/').some(part => part === '.' || part === '..')) throw Error('Invalid package path');
    const url = new URL(path, base);
    if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname)) throw Error('File is outside this package');
    return url.href;
  }
  function fileLink(text, path, base) {
    const el = node('a', text);
    el.href = packageURL(path, base); el.target = '_blank'; el.rel = 'noopener';
    return el;
  }
  async function read(path, base, hash, signal) {
    const response = await fetch(packageURL(path, base), {signal});
    if (!response.ok) throw Error('A saved history file is unavailable');
    const bytes = await response.arrayBuffer();
    if (bytes.byteLength > 4 * 1024 * 1024) throw Error('History file is too large to display');
    if (!/^[a-f0-9]{64}$/.test(hash || '')) throw Error('History checksum is missing');
    const actual = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2, '0')).join('');
    if (actual !== hash) throw Error('Saved history does not match its checksum');
    return JSON.parse(new TextDecoder().decode(bytes));
  }
  async function entryCard(entry, number, base, signal) {
    const card = node('article', undefined, 'generation-source');
    const heading = node('h3', `Source ${number}`);
    card.append(heading);
    if (entry.status !== 'recorded') {
      card.append(node('p', 'Generation details were not retained for this source.', 'small'));
      return card;
    }
    try {
      const locations = entry.locations;
      if (!Array.isArray(locations) || !locations.length) throw Error('Source location is missing');
      const files = locations[0].metadata_files || {};
      const find = name => Object.keys(files).find(path => path.split('/').pop() === name);
      const recordPath = find('generation-record.json'), briefPath = find('motion-brief.json');
      if (!recordPath) throw Error('Generation record is missing');
      const record = await read(recordPath, base, files[recordPath], signal);
      const brief = briefPath ? await read(briefPath, base, files[briefPath], signal) : null;
      heading.textContent = `Source ${number} · ${record.request?.label || 'Generated motion'}`;
      const seed = record.seed ?? entry.seed;
      card.append(node('p', `${seed === undefined ? 'Seed unavailable' : `Seed ${seed}`} · ${locations.length} retained ${locations.length === 1 ? 'copy' : 'copies'}`, 'small'));
      const segments = brief?.segments || record.request?.segments || [];
      if (segments.length) {
        const list = node('ol', undefined, 'generation-prompts');
        for (const segment of segments) {
          const item = node('li');
          item.append(node('p', segment.original_prompt ?? segment.prompt ?? 'Prompt unavailable'));
          if (Number.isFinite(segment.duration_s)) item.append(node('span', `${segment.duration_s} seconds requested`, 'small'));
          list.append(item);
        }
        card.append(list);
      } else card.append(node('p', 'Original prompt unavailable.', 'small'));
      if (brief) {
        card.append(node('h4', 'Original movement profile'));
        if (brief.profile?.name) card.append(node('p', brief.profile.name, 'small'));
        if (brief.description) card.append(node('p', brief.description));
        if (brief.applied_rules?.length) {
          const rules = node('ul', undefined, 'generation-rules');
          for (const rule of brief.applied_rules) rules.append(node('li', `${rule.label || rule.id}: ${rule.value} — ${rule.description}`));
          card.append(rules);
        }
        if (brief.unmapped_stats?.length) card.append(node('p', 'Some supplied stats had no conditioning rule. See the movement brief.', 'small'));
        card.append(node('p', 'Profile values are authored text directions. The motion’s response still needs review.', 'small'));
      } else card.append(node('p', 'No resolved movement brief was retained.', 'small'));
      const links = node('div', undefined, 'rig-links');
      links.append(fileLink('Generation record', recordPath, base));
      if (briefPath) links.append(fileLink('Movement brief', briefPath, base));
      card.append(links);
      const copies = node('details'); copies.append(node('summary', 'Retained source files'));
      const paths = node('ul');
      for (const location of locations) {
        const item = node('li'); item.append(fileLink(location.motion, location.motion, base)); paths.append(item);
      }
      copies.append(paths); card.append(copies);
    } catch (error) {
      if (signal.aborted) throw error;
      card.replaceChildren(heading, node('p', `Could not display this source: ${error.message}.`, 'small'));
    }
    return card;
  }
  function clear() {
    version++; controller?.abort(); controller = null; current = null;
    host.hidden = true; body.replaceChildren(); summary.textContent = 'Source generation history';
  }
  async function show(job) {
    if (job.id === current) return;
    clear(); current = job.id; host.hidden = false;
    const token = version, base = new URL(`/files/rig-jobs/${encodeURIComponent(job.id)}/`, location.origin);
    const result = job.result || {}, index = result.generation_sources;
    if (!index) {
      body.append(node('p', 'This older package has no combined source-history index.', 'small'));
      const legacy = result.source_generation_origin;
      if (legacy?.generation_record) {
        body.append(node('p', 'Only the original primary-source record is available here. Other contributors may not be listed.', 'small'));
        try {
          const links = node('div', undefined, 'rig-links');
          links.append(fileLink('Original-source record', legacy.generation_record, base));
          if (legacy.motion_brief) links.append(fileLink('Original movement brief', legacy.motion_brief, base));
          body.append(links);
        } catch { body.append(node('p', 'The saved history links are invalid.', 'small')); }
      } else body.append(node('p', 'Generation details are unavailable. Imported animation may have no model-generation record.', 'small'));
      return;
    }
    body.append(node('p', 'Loading original source records…', 'small'));
    controller = new AbortController(); const signal = controller.signal;
    try {
      const inventory = await read(index.manifest, base, index.manifest_sha256, signal);
      if (inventory.schema !== 'strep-generation-sources-v1' || !Array.isArray(inventory.entries)) throw Error('Unsupported source-history format');
      if (inventory.entries.length > 256) throw Error('Too many records to display; use the package index');
      const cards = await Promise.all(inventory.entries.map((entry, i) => entryCard(entry, i + 1, base, signal)));
      if (token !== version) return;
      summary.textContent = `Source generation history · ${cards.length} ${cards.length === 1 ? 'source' : 'sources'}`;
      body.replaceChildren(node('p', 'Original prompts and profiles from saved source motions. Editing and blending may change the result; this history does not describe the current style or contribution timing.', 'small'));
      body.append(fileLink('Source index', index.manifest, base));
      if (!cards.length) body.append(node('p', 'No model-generation records were retained in this package.', 'small'));
      const sources = node('div', undefined, 'generation-source-list'); sources.append(...cards); body.append(sources);
    } catch (error) {
      if (token !== version || signal.aborted) return;
      body.replaceChildren(node('p', `Source history unavailable: ${error.message}.`, 'small'));
    }
  }
  return {clear, show};
}
