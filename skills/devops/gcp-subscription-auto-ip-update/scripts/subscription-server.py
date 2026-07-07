#!/usr/bin/env python3
"""轻量 HTTP 文件服务 — 专供 Stash 拉取 Clash 格式订阅覆写文件"""
import http.server
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
FILE_PATH = '/etc/s-box/custom-sub.yaml'

class SubHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/custom.yaml', '/clmi.yaml', '/sub'):
            try:
                with open(FILE_PATH, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/yaml; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
            except FileNotFoundError:
                self.send_error(404, 'File not found')
        elif self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok')
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(f'订阅地址: http://{self.headers["Host"]}/custom.yaml\n'.encode())

    def log_message(self, format, *args):
        if '/custom.yaml' in str(args) or '/health' not in str(args):
            super().log_message(format, *args)

if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', PORT), SubHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
