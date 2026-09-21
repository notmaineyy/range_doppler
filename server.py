"""Serve the smooth browser-based SAR app: python3 server.py [--port 8503].
Only the web/ directory is exposed. Signal processing runs in a browser worker.
"""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import argparse

class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.mjs': 'text/javascript'}
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8503)
    args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),partial(Handler,directory=str(Path(__file__).parent/'web')))
    print(f'SAR image laboratory: http://127.0.0.1:{args.port}',flush=True)
    server.serve_forever()
