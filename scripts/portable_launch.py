"""Entrypoint for the personal Windows offline installation."""
import argparse
import runpy
import sys
from pathlib import Path
from strep import ROOT, read, save, now, source_check
from portable_integrity import verify_files


def probe():
    import torch
    import kimodo
    import site
    import socket
    import sitecustomize
    paths = {'executable': sys.executable, 'prefix': sys.prefix,
             'torch': torch.__file__, 'kimodo': kimodo.__file__,
             'sitecustomize': sitecustomize.__file__}
    if not all(Path(p).resolve().is_relative_to(ROOT) for p in paths.values()):
        raise RuntimeError('Runtime resolved outside this installation')
    if site.ENABLE_USER_SITE or not sys.flags.isolated:
        raise RuntimeError('Python runtime is not isolated')
    try:
        socket.getaddrinfo('example.com', 443)
    except PermissionError:
        blocked = True
    else:
        raise RuntimeError('External DNS was not rejected')
    cuda = torch.cuda.is_available()
    if cuda:
        x = torch.arange(16, device='cuda').float().reshape(4, 4)
        assert bool(torch.isfinite(x @ x.T).all())
    result = {'checked_at': now(), 'paths': paths, 'sys_path': sys.path,
              'source_commit': source_check(), 'cuda_available': cuda,
              'gpu': torch.cuda.get_device_name(0) if cuda else None,
              'python_external_network_blocked': blocked,
              'network_scope': 'Python audit hook; not OS-level network isolation'}
    save(ROOT / 'reports/portable-runtime.json', result)
    print(result, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['studio', 'verify', 'probe', 'generate'], nargs='?', default='studio')
    parser.add_argument('--port', type=int, default=8768)
    parser.add_argument('--request', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.mode == 'verify':
        manifest = read(ROOT / 'installation.json')
        verify_files(ROOT, manifest['files_sha256'])
        source_check()
        save(ROOT / 'reports/portable-integrity.json', {'checked_at': now(), 'verified_files': len(manifest['files_sha256'])})
        print('All installation files verified', flush=True)
    elif args.mode == 'probe':
        probe()
    elif args.mode == 'generate':
        if not args.request or not args.output:
            parser.error('generate requires --request and --output')
        from run_actions import main as generate
        generate(args.request, args.output)
    else:
        source_check()
        from action_studio_server import main as studio
        studio(args.port)


if __name__ == '__main__':
    main()
