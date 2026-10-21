"""Serve only this reviewer packet on loopback; Python 3 standard library only."""
import argparse
import functools
import http.server
from pathlib import Path
import webbrowser


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=8771)
    p.add_argument('--open',action='store_true',help='Open the viewer in your default browser')
    a=p.parse_args(argv)
    if not 1 <= a.port <= 65535:
        p.error('Choose a port between 1 and 65535')
    packet=Path(__file__).resolve().parent
    if not (packet/'manifest.json').is_file():
        p.error('Run the copy of this script supplied inside a reviewer packet')
    handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(packet))
    try:
        server=http.server.ThreadingHTTPServer(('127.0.0.1',a.port),handler)
    except OSError as error:
        p.exit(1,f'Could not start the review on port {a.port}: {error}\n'
            'Close an earlier review window, or run: py -3 serve.py --port 8772 --open\n'
            'Use the same port when returning to saved browser reviews.\n')
    url=f'http://127.0.0.1:{a.port}/viewer.html'
    print(f'Open {url} in a browser. Keep this window open. Ctrl+C stops the server.',flush=True)
    try:
        if a.open:
            try:
                if not webbrowser.open(url):
                    print('Browser did not open automatically. Open the URL above yourself.',flush=True)
            except Exception as error:
                print(f'Browser could not open: {error}. Open the URL above yourself.',flush=True)
        server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
