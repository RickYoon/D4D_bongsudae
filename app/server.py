"""봉수대 로컬 서버: web/ 정적 파일 + data/ + POST /api/ask (코파일럿).
실행: python3 server.py  → http://127.0.0.1:8790
"""
import json, traceback
from urllib.parse import urlsplit, parse_qs
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import agent

ROOT = Path(__file__).parent


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(ROOT), **k)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        p = urlsplit(self.path).path
        if p == "/api/stream":
            return self._stream()
        if p in ("/", "/index.html"):
            self.path = "/web/index.html"
        elif not (p.startswith("/web/") or p.startswith("/data/")) or p.endswith("/"):
            return self.send_error(404)  # 소스·로그·폴더 목록 노출 금지
        return super().do_GET()

    def _stream(self):
        q = parse_qs(urlsplit(self.path).query).get("q", [""])[0]
        self.send_response(200); self.send_header("Content-Type", "text/event-stream; charset=utf-8"); self.end_headers()
        def send(kind, **d):
            self.wfile.write(("data: " + json.dumps({"kind": kind, **d}, ensure_ascii=False) + "\n\n").encode()); self.wfile.flush()
        try:
            out = agent.ask(q, log=send); send("answer", answer=out)
        except Exception as e:
            send("error", text=str(e)[:300])

    def do_POST(self):
        if self.path != "/api/ask":
            return self.send_error(404)
        try:
            q = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}").get("q", "")
            out = agent.ask(q)
            code = 200
        except Exception as e:
            out, code = {"요약": "오류", "문장": [], "버린문장": [], "한계": [str(e)[:300]], "trace": traceback.format_exc()[-500:]}, 500
        b = json.dumps(out, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("봉수대 → http://127.0.0.1:8790")
    ThreadingHTTPServer(("127.0.0.1", 8790), H).serve_forever()
