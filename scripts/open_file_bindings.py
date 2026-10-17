"""Fresh complete hashes through retained handles; no content/digest cache."""
import hashlib
import os
from pathlib import Path
import stat


class OpenFileBindings:
    def __init__(self, bindings, *, maximum_files=4096, buffer_bytes=128*1024):
        if type(maximum_files) is not int or not 1 <= maximum_files <= 4096:
            raise ValueError('Explicit bounded file count required')
        if type(buffer_bytes) is not int or not 1 <= buffer_bytes <= 1024**2:
            raise ValueError('Explicit read buffer up to1MiB required')
        if not isinstance(bindings, dict) or not 1 <= len(bindings) <= maximum_files:
            raise ValueError('Complete nonempty bounded binding map required')
        entries=[]
        for name,digest in bindings.items():
            if not isinstance(name,(str,Path)) or not Path(name).is_absolute():
                raise ValueError('Explicit absolute source paths required')
            if type(digest) is not str or len(digest)!=64 or set(digest)-set('0123456789abcdef'):
                raise ValueError('Complete lowercase SHA256 bindings required')
            entries.append((Path(name),digest))
        self._files=[];self._buffer=bytearray(buffer_bytes);self._closed=False
        try:
            for path,digest in entries:
                named=path.stat()
                if not stat.S_ISREG(named.st_mode) or not named.st_ino or not named.st_dev:
                    raise ValueError('Stable nonzero regular-file identity required; use ordinary path hashing on unsupported filesystems')
                file=path.open('rb',buffering=0)
                try:
                    info=os.fstat(file.fileno())
                    if not stat.S_ISREG(info.st_mode) or (info.st_dev,info.st_ino)!=(named.st_dev,named.st_ino):
                        raise ValueError('Stable nonzero regular-file identity required; use ordinary path hashing on unsupported filesystems')
                    self._files.append((path,digest,file,(info.st_dev,info.st_ino),info.st_size))
                except BaseException:
                    file.close();raise
            self.verify()
        except BaseException:
            self.close();raise

    @staticmethod
    def _identity(info):return info.st_dev,info.st_ino

    def verify(self):
        if self._closed:raise ValueError('Binding handles are closed')
        total=0;view=memoryview(self._buffer)
        for path,expected,file,identity,size in self._files:
            before=path.stat();opened=os.fstat(file.fileno())
            if (self._identity(before)!=identity or self._identity(opened)!=identity
                    or before.st_size!=size or opened.st_size!=size):
                raise ValueError('Source identity or size changed')
            file.seek(0);digest=hashlib.sha256();remaining=size
            while remaining:
                read=file.readinto(view[:min(remaining,len(view))])
                if not read:raise ValueError('Source shrank while hashing')
                digest.update(view[:read]);remaining-=read
            if file.read(1):raise ValueError('Source grew while hashing')
            after=path.stat();opened_after=os.fstat(file.fileno())
            if (self._identity(after)!=identity or self._identity(opened_after)!=identity
                    or after.st_size!=size or opened_after.st_size!=size
                    or before.st_mtime_ns!=after.st_mtime_ns
                    or opened.st_mtime_ns!=opened_after.st_mtime_ns):
                raise ValueError('Source changed while hashing')
            if digest.hexdigest()!=expected:raise ValueError('Source SHA256 changed')
            total+=size
        return dict(files=len(self._files),bytes_hashed=total,complete_fresh_hashes=True,
            content_cache=False,digest_cache=False,path_and_handle_identity_checked=True)

    def close(self):
        for path,digest,file,identity,size in self._files:file.close()
        self._files=[];self._closed=True

    def __enter__(self):return self

    def __exit__(self,*args):self.close()
