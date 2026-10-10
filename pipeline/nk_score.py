"""북한 도발 10년 채점 — 규칙 고정(2026-10-10, 수집 결과 보기 전).
분류(LLM, 제목 단위): WARN = 북한 당국·공식 인물(김여정, 국방성, 총참모부, 외무성, 조선중앙통신 등)이 '앞으로 할' 군사적·물리적 행동을 경고·예고·위협
  (이미 일어난 일의 보도, 남측·미국의 발언, 해설은 제외)
경보 = 시점 A 기준 A-7 ~ A-2 날짜(기사 pubDate)에 WARN 제목이 1개 이상
적중률 = 사건 시작점 중 경보가 있던 비율 / 헛경보율 = 대조 기간 중 경보가 있던 비율 / 우도비 = 적중률 ÷ 헛경보율
유형: CSIS Type·Event 기준 — 미사일 / 포격·침범·무인기 / 풍선 / 핵 / 기타
"""
import json, subprocess, os, re, datetime as dt, collections, math
KEY = open(os.path.expanduser("~/.config/openrouter/key")).read().strip()
X = json.load(open("nkdb/design.json")); N = [json.loads(l) for l in open("nkdb/news.jsonl")]
PROMPT = """아래는 한국어 뉴스 제목 목록이다. 각 제목에 라벨 하나.
WARN = 북한 당국 또는 공식 인물(김여정, 국방성, 총참모부, 외무성, 조선중앙통신, 노동신문 등)이 '앞으로 할' 군사적·물리적 행동을 경고·예고·위협하는 내용
OTHER = 그 외 (이미 일어난 일의 보도, 남측·미국·제3자 발언, 해설, 무관)
제목에 없는 사실을 추측하지 마라. JSON 배열만: [{"i":번호,"l":"WARN|OTHER"}]

"""
CACHE = "nkdb/labels.json"; lab = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
def ask(body):
    o = subprocess.run(["curl", "-s", "--max-time", "120", "https://openrouter.ai/api/v1/chat/completions", "-H", "Authorization: Bearer " + KEY, "-H", "Content-Type: application/json",
        "-d", json.dumps({"model": "anthropic/claude-haiku-5.5", "max_tokens": 4000, "temperature": 0, "messages": [{"role": "user", "content": body}]})], capture_output=True, text=True).stdout
    return json.loads(o)["choices"][0]["message"]["content"]
todo = sorted({n["title"] for n in N if n["title"] and n["title"] not in lab})
for s in range(0, len(todo), 70):
    ch = todo[s:s + 70]
    for att in range(3):
        try:
            t = ask(PROMPT + "\n".join(f"{i}. {x}" for i, x in enumerate(ch))); arr = json.loads(t[t.index("["): t.rindex("]") + 1]); break
        except Exception: arr = []
    for a in arr: lab[ch[a["i"]]] = a["l"]
    json.dump(lab, open(CACHE, "w"), ensure_ascii=False); print("labeled", s + len(ch), "/", len(todo), flush=True)
D = dt.date.fromisoformat
def warned(anchor):
    A = D(anchor); hits = [n for n in N if n["anchor"] == anchor and n["title"] and lab.get(n["title"]) == "WARN" and n["date"] and 2 <= (A - D(n["date"])).days <= 7]
    return hits
EV = collections.defaultdict(list)
for e in X["events"]: EV[e["date"][:10]].append(e)
def kind(es):
    s = " ".join(e["type"] + " " + e["event"] for e in es).lower()
    return "핵" if "nuclear" in s and "test" in s else "풍선" if "balloon" in s else "미사일" if "missile" in s or "rocket" in s or "satellite" in s or "icbm" in s or "slbm" in s else "포격·침범·무인기" if any(k in s for k in ("artillery", "dmz", "drone", "uav", "shell", "gps")) else "기타"
rows = []
for a in X["onsets"]:
    h = warned(a); rows.append(dict(anchor=a, kind=kind(EV[a]), warned=bool(h), event=EV[a][0]["event"], titles=[x["title"] for x in h][:3], lead=sorted({(D(a) - D(x["date"])).days for x in h})))
ctl = [dict(anchor=a, warned=bool(warned(a)), titles=[x["title"] for x in warned(a)][:3]) for a in X["controls"]]
def wilson(k, n, z=1.96):
    if not n: return (0, 0)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d; return (round(100 * (c - w), 1), round(100 * (c + w), 1))
k1, n1 = sum(r["warned"] for r in rows), len(rows); k0, n0 = sum(c["warned"] for c in ctl), len(ctl)
by = collections.defaultdict(lambda: [0, 0])
for r in rows: by[r["kind"]][0] += r["warned"]; by[r["kind"]][1] += 1
out = dict(rule=__doc__, onsets=rows, controls=ctl, hit=[k1, n1, wilson(k1, n1)], fa=[k0, n0, wilson(k0, n0)], lr=round((k1 / n1) / max(k0 / n0, 1e-9), 2), by_kind={k: v + [list(wilson(*v))] for k, v in by.items()})
json.dump(out, open("../bongsu/data/nk10-data.json", "w"), ensure_ascii=False)
print(f"적중률 {k1}/{n1} = {100*k1/n1:.0f}% {wilson(k1,n1)} | 헛경보율 {k0}/{n0} = {100*k0/n0:.0f}% {wilson(k0,n0)} | 우도비 {out['lr']}")
for k, v in sorted(by.items(), key=lambda x: -x[1][1]): print(f"  {k}: {v[0]}/{v[1]}")
