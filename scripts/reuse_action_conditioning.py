"""Copy exact text tensors from validated local caches, otherwise encode normally."""
import copy
import shutil
from strep import ROOT,read,save,sha256,now
from action_requests import conditioning_texts,request_digest
from action_encoder import ActionEncoder


def reuse(batch,target):
    texts=conditioning_texts(batch)
    candidates=[ROOT/'reports/action-coverage-v1']+sorted((ROOT/'reports/action-jobs').glob('*'))
    for source in candidates:
        if not (source/'conditioning/manifest.json').exists() or not (source/'request.json').exists():continue
        try:ActionEncoder(source/'conditioning',read(source/'request.json'))
        except (ValueError,KeyError,OSError):continue
        meta=read(source/'conditioning/manifest.json')
        if not set(texts)<=set(meta['entries']):continue
        target.mkdir(exist_ok=False);meta=copy.deepcopy(meta);meta['entries']={text:meta['entries'][text] for text in texts}
        for item in meta['entries'].values():
            shutil.copyfile(source/'conditioning'/item['file'],target/item['file'])
            if sha256(target/item['file'])!=item['sha256']:raise ValueError('Copied conditioning changed')
        meta.update(request_sha256=request_digest(batch),reuse_provenance=dict(source=str(source/'conditioning'),source_manifest_sha256=sha256(source/'conditioning/manifest.json'),copied_at=now(),reason='Exact text and current pinned encoder revisions; unchanged validated tensor bytes.'))
        save(target/'manifest.json',meta);ActionEncoder(target,batch);return True
    return False
