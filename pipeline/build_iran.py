"""이란 봉수 → bongsu/data/iran-data.json. 규칙 고정(2026-10-10, 결과 보기 전): 예고 후 2~7일 내 공격 = 적중. 원천 묶기 = 같은 방향 3일 안.
정답(인용 보도): 이란 공격 2024-04-13·2024-10-01·2025-06-13·2026-02-28 / 이스라엘·미국 공격 2024-04-19·2024-10-26·2025-06-13·2025-06-22·2026-02-28
유가: FRED DCOILBRENTEU. 기준선 = 관측 기간 중 아무 날 2~7일 안 공격 확률.
"""
import csv, json, collections, datetime as dt
EV = {"IR": [("2024-04-13", "이란 1차 직접 공격"), ("2024-10-01", "이란 2차 직접 공격"), ("2025-06-13", "이란 True Promise III"), ("2026-02-28", "이란 반격(재전쟁)")],
      "IL": [("2024-04-19", "이스라엘 제한 타격"), ("2024-10-26", "이스라엘 이란 공개 타격"), ("2025-06-13", "이스라엘 기습(12일 전쟁)"), ("2025-06-22", "미군 핵시설 타격"), ("2026-02-28", "미·이스라엘 공습(재전쟁)")]}
PER = [("2024-03-15", "2024-10-31"), ("2025-05-15", "2025-06-30"), ("2026-02-01", "2026-04-15")]
labs = []
for f in ("labiran24.json", "labiran25.json", "labiran26.json"):
    try: labs += json.load(open(f))
    except FileNotFoundError: pass
D = lambda s: dt.date.fromisoformat(s)
out = {"sides": {}}
for side, lab in (("IR", "WARN_IR"), ("IL", "WARN_IL")):
    w = sorted([x for x in labs if x["label"] == lab], key=lambda x: x["date"]); eps = []
    for t in w:
        e = next((e for e in eps if 0 <= (D(t["date"]) - D(e["last"])).days <= 3), None)
        if e: e["titles"].append(t); e["last"] = t["date"]
        else: eps.append({"date": t["date"], "last": t["date"], "titles": [t]})
    ev = EV[side]
    for e in eps:
        n = [x for x in ev if 2 <= (D(x[0]) - D(e["date"])).days <= 7]
        e["result"] = {"event": n[0][0], "lead": (D(n[0][0]) - D(e["date"])).days} if n else None; e["n_articles"] = len(e["titles"])
    days = [D(a) + dt.timedelta(i) for a, b in PER for i in range((D(b) - D(a)).days + 1)]
    bh = sum(any(2 <= (D(x[0]) - d).days <= 7 for x in ev) for d in days)
    out["sides"][side] = {"episodes": eps, "events": [{"date": d, "name": n, "warned": any(2 <= (D(d) - D(e["date"])).days <= 7 for e in eps)} for d, n in ev],
                          "baseline": {"hit": bh, "days": len(days), "pct": round(100 * bh / len(days), 1)}}
    print(side, "예고 묶음", len(eps), "→ 2~7일 내 공격", sum(1 for e in eps if e["result"]), "| 공격", [(x["date"], x["warned"]) for x in out["sides"][side]["events"]], "| 기준선", out["sides"][side]["baseline"])
P = {r["observation_date"]: float(r["DCOILBRENTEU"]) for r in csv.DictReader(open("brent.csv")) if r["DCOILBRENTEU"] not in ("", ".")}
out["brent"] = P
daily = collections.Counter()
for f in ("iran24.csv", "iran25.csv", "iran26.csv"):
    try:
        for r in csv.DictReader(open(f)): daily[r["date"]] += int(r["n"])
    except FileNotFoundError: pass
out["daily"] = daily; out["periods"] = PER
import os
out["partial"] = "DONE" not in (open("iran.log").read() if os.path.exists("iran.log") else "")
json.dump(out, open("../bongsu/data/iran-data.json", "w"), ensure_ascii=False)
