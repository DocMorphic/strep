"""Write complete numeric observations to NPZ without retaining earlier arrays.

Transport only: no sample selection, coercion, geometry queries or quality gate.
Scene producers use this transport without changing their complete query population.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import zipfile
import numpy as np
from strep import read,sha256

NAME=re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,255}')


def require(condition,message):
    if not condition:raise ValueError(message)


def write_receipt(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False);stream.write('\n')


def logical_sha256(value):
    """Hash C-order logical bytes in bounded chunks, preserving dtype/NaN bits."""
    digest=hashlib.sha256()
    for chunk in np.nditer(value,flags=['external_loop','buffered','zerosize_ok'],order='C',buffersize=131072):
        digest.update(chunk.tobytes(order='C'))
    return digest.hexdigest()


class ObservationArchive:
    def __init__(self,path,*,maximum_array_bytes=256*1024**2):
        self.path=Path(path).resolve();self.partial=Path(str(self.path)+'.partial')
        self.receipt=Path(str(self.path)+'.receipt.json');self.failed=Path(str(self.partial)+'.receipt.json')
        require(type(maximum_array_bytes) is int and maximum_array_bytes>0,'Positive integer per-array byte budget required')
        require(not any(p.exists() for p in (self.path,self.partial,self.receipt,self.failed)),'Fresh observation archive paths required')
        require(self.path.parent.is_dir(),'Existing archive parent required')
        self.maximum_array_bytes=maximum_array_bytes;self.arrays={};self.closed=False;self.bytes=0
        self.zip=zipfile.ZipFile(self.partial,'x',compression=zipfile.ZIP_DEFLATED,allowZip64=True)

    def __setitem__(self,name,value):
        require(not self.closed,'Archive is closed')
        require(isinstance(name,str) and NAME.fullmatch(name),'Safe flat observation name required')
        require(name not in self.arrays,'Duplicate observation name')
        original=np.asarray(value)
        require(original.dtype.kind in 'biufc' and not original.dtype.hasobject and original.dtype.metadata is None,'Plain numeric non-object observations required')
        require(original.nbytes<=self.maximum_array_bytes,'Observation exceeds complete per-array budget')
        # One complete array snapshot: write it exactly, never truncate or downcast.
        snapshot=np.array(original,copy=True,order='K',subok=False)
        digest=logical_sha256(snapshot)
        require(original.shape==snapshot.shape and original.dtype==snapshot.dtype and logical_sha256(original)==digest,'Observation changed during snapshot')
        with self.zip.open(name+'.npy','w',force_zip64=True) as stream:
            np.lib.format.write_array(stream,snapshot,allow_pickle=False)
        require(original.shape==snapshot.shape and original.dtype==snapshot.dtype and logical_sha256(original)==digest,'Observation changed while writing')
        self.arrays[name]=dict(shape=list(snapshot.shape),dtype=snapshot.dtype.str,
            bytes=int(snapshot.nbytes),logical_sha256=digest)
        self.bytes+=snapshot.nbytes

    def finish(self):
        require(not self.closed,'Archive is closed')
        require(bool(self.arrays),'An empty archive cannot complete')
        self.zip.close();self.closed=True
        with zipfile.ZipFile(self.partial) as z:
            require(z.namelist()==[n+'.npy' for n in self.arrays],'Complete archive entry population required')
        # Fresh destination; retained partials are never reused or overwritten.
        require(not self.path.exists() and not self.receipt.exists(),'Archive destination appeared during writing')
        os.link(self.partial,self.path)  # Atomic fresh publication; never replace a racing destination.
        self.partial.unlink()
        result=dict(schema='strep-native-observation-archive-v1',status='complete',
            archive_sha256=sha256(self.path),arrays=self.arrays,logical_bytes=int(self.bytes),
            maximum_array_bytes=self.maximum_array_bytes,source_values_preserved=True,
            sampling_modified=False,geometry_verified=False,quality_approved=False,release_approved=False)
        write_receipt(self.receipt,result);return result

    def abort(self,error):
        if self.failed.exists():return read(self.failed)
        if not self.closed:self.zip.close();self.closed=True
        # A failed finish may already have moved the archive. Preserve either form.
        retained=self.partial if self.partial.exists() else self.path
        write_receipt(self.failed,dict(schema='strep-native-observation-archive-v1',status='failed',error=str(error),
            retained_path=retained.name,archive_sha256=sha256(retained),completed_arrays=self.arrays,
            quality_approved=False,release_approved=False))

    def __enter__(self):return self

    def __exit__(self,kind,error,traceback):
        if kind is not None:self.abort(error)
        elif not self.closed:
            try:self.finish()
            except Exception as exc:self.abort(exc);raise
        return False


def verify(path,*,maximum_array_bytes=256*1024**2):
    """Read one array at a time and recheck the entire complete transport receipt."""
    path=Path(path).resolve();receipt=Path(str(path)+'.receipt.json');result=read(receipt)
    require(not Path(str(path)+'.partial.receipt.json').exists(),'Failed archive cannot verify complete')
    require(type(maximum_array_bytes) is int and maximum_array_bytes>0,'Positive verifier array budget required')
    require(result['schema']=='strep-native-observation-archive-v1' and result['status']=='complete','Complete archive receipt required')
    require(result['sampling_modified'] is False and result['geometry_verified'] is False
        and result['quality_approved'] is False and result['release_approved'] is False,'Archive is transport only')
    require(result['source_values_preserved'] is True,'Unchanged source values required')
    require(type(result['maximum_array_bytes']) is int and 0<result['maximum_array_bytes']<=maximum_array_bytes,'Invalid or oversized array budget')
    before={path:sha256(path),receipt:sha256(receipt)}
    require(before[path]==result['archive_sha256'],'Observation archive changed')
    entries=result['arrays'];require(isinstance(entries,dict) and bool(entries),'Complete array receipts required')
    with zipfile.ZipFile(path) as z:
        require(z.namelist()==[n+'.npy' for n in entries],'Archive population differs')
        for name,entry in entries.items():
            require(isinstance(name,str) and NAME.fullmatch(name),'Unsafe observation name')
            with z.open(name+'.npy') as stream:
                version=np.lib.format.read_magic(stream)
                require(version in ((1,0),(2,0)),'Supported plain numeric NPY header required')
                reader=np.lib.format.read_array_header_1_0 if version==(1,0) else np.lib.format.read_array_header_2_0
                shape,_,dtype=reader(stream,max_header_size=65536)
                require(all(type(d) is int and d>=0 for d in shape),'Invalid observation shape')
                size=math.prod(shape)*dtype.itemsize
                require(dtype.kind in 'biufc' and not dtype.hasobject and size<=maximum_array_bytes,'Unsafe or oversized observation payload')
                require(list(shape)==entry['shape'] and dtype.str==entry['dtype'] and size==entry['bytes'],'Observation header differs')
                require(z.getinfo(name+'.npy').file_size==stream.tell()+size,'Complete exact NPY payload required')
    logical_bytes=0
    with np.load(path,allow_pickle=False) as saved:
        require(saved.files==list(entries),'Loaded array population differs')
        for name,entry in entries.items():
            require(isinstance(name,str) and NAME.fullmatch(name),'Unsafe observation name')
            value=saved[name]
            require(value.dtype.kind in 'biufc' and not value.dtype.hasobject,'Unsupported observation dtype')
            require(list(value.shape)==entry['shape'] and value.dtype.str==entry['dtype'] and value.nbytes==entry['bytes'],'Observation shape/dtype/bytes differ')
            require(value.nbytes<=result['maximum_array_bytes'] and logical_sha256(value)==entry['logical_sha256'],'Observation data differs')
            logical_bytes+=value.nbytes
    require(logical_bytes==result['logical_bytes'],'Logical byte population differs')
    require(all(sha256(p)==h for p,h in before.items()),'Archive or receipt changed during verification')
    return dict(arrays=len(entries),logical_bytes=logical_bytes,all_values_exact=True,
        geometry_verified=False,quality_approved=False,release_approved=False)
