"""국내 국방 특허 전수 수집 (KIPRIS getAdvancedSearch, IPC F41·F42). 직렬 2초, 키 비노출.
출력: emerge_patents.jsonl (출원번호·출원일·발명명칭·출원인·IPC)
"""
import urllib.request, urllib.parse, re, json, time, os, html
KEY = open(os.path.expanduser("~/.config/kipris/key")).read().strip()
URL = "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getAdvancedSearch?"
OUT = "emerge_patents.jsonl"
seen = set()
if os.path.exists(OUT):
    seen = {json.loads(l)["no"] for l in open(OUT)}
f = open(OUT, "a")
for ipc in ("F41", "F42"):
    page = 1
    while True:
        q = {"ipcNumber": ipc, "patent": "true", "utility": "false", "numOfRows": "500", "pageNo": str(page), "ServiceKey": KEY}
        for att in range(3):
            try:
                s = urllib.request.urlopen(URL + urllib.parse.urlencode(q), timeout=60).read().decode(); break
            except Exception as e:
                print("retry", ipc, page, type(e).__name__); time.sleep(8)
        else:
            print("FAIL", ipc, page); break
        items = re.findall(r"<item>(.*?)</item>", s, re.S)
        if not items: break
        g = lambda t, x: (re.findall(rf"<{t}>(.*?)</{t}>", x, re.S) or [""])[0]
        new = 0
        for it in items:
            no = g("applicationNumber", it)
            if no in seen: continue
            seen.add(no); new += 1
            f.write(json.dumps({"no": no, "date": g("applicationDate", it), "title": html.unescape(g("inventionTitle", it)),
                                "applicant": html.unescape(g("applicantName", it)), "ipc": g("ipcNumber", it), "q": ipc}, ensure_ascii=False) + "\n")
        f.flush()
        total = int((re.findall(r"<totalCount>(\d+)", s) or ["0"])[0])
        print(ipc, "page", page, "items", len(items), "new", new, "total", total, flush=True)
        if page * 500 >= total: break
        page += 1; time.sleep(2)
print("done", len(seen))
