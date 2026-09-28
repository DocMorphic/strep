"""Serve only this reviewer packet on loopback; Python 3 standard library only."""
import argparse
import functools
import http.server
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=8771)
    a=p.parse_args()
    packet=Path(__file__).resolve().parent
    if not (packet/'manifest.json').is_file():
        p.error('Run the copy of this script supplied inside a reviewer packet')
    handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(packet))
    server=http.server.ThreadingHTTPServer(('127.0.0.1',a.port),handler)
    print(f'Open http://127.0.0.1:{a.port}/viewer.html in a browser. Ctrl+C stops the server.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
