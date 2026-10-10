"""봉수대 프로토타입 데이터 빌드 → proto-data.js
입력: lab2024.json(5~7월, 규칙 고정 전 = 개발 기간) · laboos.json(8~10월, 시험 기간) · lab2023.json(대조) · cyc2024/oos2024/ctl2023.csv(일별 기사 수)
정답 = EVENTS (합참 인용 보도 9건). 입력 라벨 = v4*.json (classify_v4.py)
"""
import csv, json, re, collections, datetime as dt

EVENTS = [  # 전부 합참 발표 인용 보도로 확인 (10/10)
    ("2024-05-28", "1차 살포", "뉴시스(합참)"),
    ("2024-06-01", "2차 살포", "서울신문(합참)"),
    ("2024-06-08", "3차 살포", "뉴시스(합참)"),
    ("2024-06-24", "5차 살포", "아주경제(합참)"),
    ("2024-07-18", "8차 살포", "아주경제(합참)"),
    ("2024-07-21", "9차 살포", "이투데이"),
    ("2024-07-24", "10차 살포", "RFA·세계일보(합참)"),
    ("2024-08-10", "11차 · 17일 만에 재개", "아주경제(합참)"),
    ("2024-09-04", "12차 · 25일 만에 재개", "YTN·데일리안(합참)"),
]
# 사람이 검수해서 고친 라벨 (사유 남김)
OVERRIDE = {"북한, 이틀 연속 쓰레기 풍선 부양…\"적재물 낙하 주의\" - 연합뉴스TV": ("REPORT", "이미 일어난 살포 보도를 예고로 오분류")}

def actor(t):
    for a in ("김여정", "국방성", "조선중앙"):
        if a in t: return a
    return "북한(주체 미상)"

def load(path, period):
    out = []
    for x in json.load(open(path)):
        l, why = x["label"], ""
        if x["title"] in OVERRIDE: l, why = OVERRIDE[x["title"]]
        out.append({**x, "label": l, "fix": why, "period": period})
    return out

titles = load("v4dev.json", "dev") + load("v4test.json", "test") + load("v4ctl.json", "ctl")

# 원천 묶기: 같은 주체 + 3일 안 = 같은 발표 하나
warns = sorted([t for t in titles if t["label"] == "WARN"], key=lambda t: t["date"])
eps = []
for t in warns:
    a, d = actor(t["title"]), dt.date.fromisoformat(t["date"])
    e = next((e for e in eps if e["actor"] == a and 0 <= (d - dt.date.fromisoformat(e["last"])).days <= 3), None)
    if e: e["titles"].append(t); e["last"] = t["date"]
    else: eps.append({"actor": a, "date": t["date"], "last": t["date"], "period": t["period"], "titles": [t]})
for e in eps:
    d = dt.date.fromisoformat(e["date"])
    nxt = [x for x in EVENTS if 2 <= (dt.date.fromisoformat(x[0]) - d).days <= 7]
    e["result"] = {"event": nxt[0][0], "lead": (dt.date.fromisoformat(nxt[0][0]) - d).days} if nxt else None
    e["n_articles"] = len(e["titles"])
    e["outlets"] = sorted({re.split(r" - ", t["title"])[-1] for t in e["titles"]})

daily = collections.Counter()
for p in ("cyc2024.csv", "oos2024.csv", "ctl2023.csv"):
    for r in csv.DictReader(open(p)):
        if r["kw"] == "대북전단": daily[r["date"]] += int(r["n"])

events = [{"date": d, "name": n, "src": s, "warned": any(2 <= (dt.date.fromisoformat(d) - dt.date.fromisoformat(t["date"])).days <= 7 for t in warns)} for d, n, s in EVENTS]
json.dump({"daily": daily, "episodes": eps, "events": events,
           "fixes": [{"title": k, "to": v[0], "why": v[1]} for k, v in OVERRIDE.items()]},
          open("proto-data.json", "w"), ensure_ascii=False)
open("proto-data.js", "w").write("window.BONGSU=" + open("proto-data.json").read() + ";")
for e in eps: print(e["period"], e["date"], e["actor"], e["n_articles"], "기사", len(e["outlets"]), "매체 →", e["result"])
print([(x["date"], x["warned"]) for x in events])
