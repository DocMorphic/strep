"""Installed as sitecustomize: isolate caches and reject external Python sockets.

This is an offline guard, not an OS sandbox; native libraries are not covered.
"""
import ipaddress
import os
from pathlib import Path
import sys

ROOT = Path(sys.executable).resolve().parents[2]
for key in ('HF_TOKEN', 'HUGGING_FACE_HUB_TOKEN', 'TEXT_ENCODER_URL', 'TEXT_ENCODERS_DIR', 'PYTHONPATH', 'PYTHONHOME'):
    os.environ.pop(key, None)
os.environ.update(HF_HOME=str(ROOT / '.cache/huggingface'),
                  HF_HUB_CACHE=str(ROOT / '.cache/huggingface/hub'),
                  HF_TOKEN_PATH=str(ROOT / '.cache/no-credentials'),
                  HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                  HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1',
                  PYTHONNOUSERSITE='1')


def local(host):
    if isinstance(host, bytes):
        host = host.decode('ascii')
    if host == 'localhost':
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def guard(event, args):
    host = None
    if event in ('socket.connect', 'socket.bind', 'socket.sendto', 'socket.sendmsg') and isinstance(args[1], tuple):
        host = args[1][0]
    elif event in ('socket.getaddrinfo', 'socket.gethostbyname', 'socket.gethostbyaddr'):
        host = args[0]
    elif event == 'socket.getnameinfo':
        host = args[0][0]
    if host is not None and not local(host):
        raise PermissionError('Strep offline runtime rejects external Python networking')


sys.addaudithook(guard)
