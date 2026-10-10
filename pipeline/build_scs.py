"""해상 봉수(남중국해 2024) → bongsu/data/scs-data.json. 규칙은 한반도와 동일(결과 보기 전 고정, 2026-10-10):
경보 = WARN(중국 당국·해경·외교부의 '앞으로 할' 조치 경고) 발표, 같은 주체 3일 안 = 원천 1개.
적중 = 경보 후 2~7일 안에 충돌 개시.
정답(필리핀 공식 발표 인용 보도): 3/5 · 3/23 · 4/30 · 6/17 · 8/19 · 8/31
"""
import csv, json, re, collections, datetime as dt

EVENTS = [("2024-03-05", "아융인 보급 · 물대포·충돌", "RFA·VOA (필리핀 측 발표)"),
          ("2024-03-23", "아융인 보급선 물대포", "VOA (3/24 보도 엇갈림)"),
          ("2024-04-30", "스카버러 물대포", "USNI·UPI (필리핀 해경)"),
          ("2024-06-17", "아융인 승선·흉기", "Inquirer·SCMP (AFP)"),
          ("2024-08-19", "사비나 충돌", "필리핀 NSC 발표(FSI)"),
          ("2024-08-31", "사비나 3회 들이받기", "필리핀 해경(FSI·Baird)")]

def actor(t):
    for a, k in (("중국 해경", "coast guard"), ("중국 외교부", "foreign ministry"), ("인민해방군", "pla"), ("중국 정부", "china")):
        if k in t.lower(): return a
    return "중국(주체 미상)"

lab = json.load(open("labscs.json"))
warns = sorted([x for x in lab if x["label"] == "WARN"], key=lambda x: x["date"])
eps = []
for t in warns:
    a, d = actor(t["title"]), dt.date.fromisoformat(t["date"])
    e = next((e for e in eps if e["actor"] == a and 0 <= (d - dt.date.fromisoformat(e["last"])).days <= 3), None)
    if e: e["titles"].append(t); e["last"] = t["date"]
    else: eps.append({"actor": a, "date": t["date"], "last": t["date"], "period": "scs", "titles": [t]})
for e in eps:
    d = dt.date.fromisoformat(e["date"])
    nxt = [x for x in EVENTS if 2 <= (dt.date.fromisoformat(x[0]) - d).days <= 7]
    e["result"] = {"event": nxt[0][0], "lead": (dt.date.fromisoformat(nxt[0][0]) - d).days} if nxt else None
    e["n_articles"] = len(e["titles"]); e["outlets"] = sorted({t["title"].split(" - ")[-1] for t in e["titles"]})
daily = collections.Counter()
for r in csv.DictReader(open("scs2024.csv")): daily[r["date"]] += int(r["n"])
events = [{"date": d, "name": n, "src": s,
           "warned": any(2 <= (dt.date.fromisoformat(d) - dt.date.fromisoformat(w["date"])).days <= 7 for w in warns)} for d, n, s in EVENTS]
json.dump({"daily": daily, "episodes": eps, "events": events}, open("../bongsu/data/scs-data.json", "w"), ensure_ascii=False)
for e in eps: print(e["date"], e["actor"], e["n_articles"], "→", e["result"], "|", e["titles"][0]["title"][:70])
print([(x["date"], x["warned"]) for x in events])
