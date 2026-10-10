"""북한 도발 10년 — 시작점·대조 기간마다 직전 10일 '북한 담화/경고' 기사 수집 (직렬 4초, 실패 시 30초 쉬고 재시도)
출력: nkdb/news.jsonl {"anchor","kind","date","title"} — 기사 날짜는 pubDate
"""
import json, subprocess, re, time, html, datetime as dt, os
X = json.load(open("nkdb/design.json")); OUT = "nkdb/news.jsonl"
done = set()
if os.path.exists(OUT):
    for l in open(OUT): j = json.loads(l); done.add((j["anchor"], j["win"]))
f = open(OUT, "a")
def fetch(q):
    for att in range(4):
        o = subprocess.run(["curl", "-s", "--max-time", "25", "-A", "Mozilla/5.0", "-G", "https://news.google.com/rss/search", "--data-urlencode", f"q={q}",
                            "--data-urlencode", "hl=ko", "--data-urlencode", "gl=KR", "--data-urlencode", "ceid=KR:ko"], capture_output=True, text=True).stdout
        if "<rss" in o: return re.findall(r"<item><title>(.*?)</title>.*?<pubDate>(.*?)</pubDate>", o, re.S)
        print("blocked/fail, wait", flush=True); time.sleep(30 * (att + 1))
    return None
jobs = [(a, "onset") for a in X["onsets"]] + [(a, "control") for a in X["controls"]]
for a, kind in jobs:
    A = dt.date.fromisoformat(a)
    for w, (s, e) in enumerate(((A - dt.timedelta(10), A - dt.timedelta(5)), (A - dt.timedelta(5), A))):
        if (a, w) in done: continue
        items = fetch(f'북한 (담화 OR 경고 OR 위협 OR 예고) after:{s} before:{e}')
        if items is None: print("FAIL", a, w, flush=True); continue
        for t, d in items:
            try: day = dt.datetime.strptime(d[5:16], "%d %b %Y").date().isoformat()
            except Exception: day = ""
            f.write(json.dumps({"anchor": a, "kind": kind, "win": w, "date": day, "title": html.unescape(t)}, ensure_ascii=False) + "\n")
        if not items: f.write(json.dumps({"anchor": a, "kind": kind, "win": w, "date": "", "title": ""}, ensure_ascii=False) + "\n")
        f.flush(); print(kind, a, w, len(items), flush=True); time.sleep(4)
print("DONE")
