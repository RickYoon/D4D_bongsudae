"""앞으로 성장할 국방 기술 — 규칙 고정(2026-10-10, 분류 결과 보기 전). 국내 특허 F41·F42, 주제 = emerge_taxonomy(55개 고정).
지표(기준연도 c 시점에서 c까지의 기록만 사용):
  S1 성장   : 주제 비중(무관 제외 전체 대비) 최근 3년(c-2..c) 평균 ≥ 그 전 3년(c-5..c-3) 평균 × 1.5, 최근 3년 건수 ≥ 8
  S2 새 출원인: 최근 3년 출원인 중 c-3 이전에 이 주제에 출원한 적 없는 출원인 비율 ≥ 60%, 최근 3년 건수 ≥ 8
  S3 조용함 : 최근 3년 비중이 전체 주제 중앙값 이하 (= 아직 뜨지 않은 주제)
판정 '오를 후보' = S1 그리고 S2 (S3는 표시만)
채점: 미래 4년(c+1..c+4, 단 ≤2024 — 2025·26은 공개 지연) 비중 평균 > 최근 3년 평균 × 1.2 이면 '성장'
기준연도 c = 2016~2020 (미래 4년이 2024 안에 들어오는 해). 대조군 = 같은 해 판정 안 된 주제(건수 ≥ 8).
지금 후보: c = 2024 (최근 2022~2024)에서 S1·S2 둘 다 켜진 주제 + 하나만 켜진 주제.
"""
import json, collections
P = {json.loads(l)["no"]: json.loads(l) for l in open("emerge_patents.jsonl")}
import glob
TG = [json.loads(l) for f in glob.glob("emerge_tags*.jsonl") for l in open(f)]
rows = []
for t in TG:
    p = P.get(t["no"]); y = int(p["date"][:4] or 0) if p and p["date"] else 0
    if not y or "무관" in t["tags"] or "미분류" in t["tags"]: continue
    for tag in t["tags"][:1]: rows.append((y, tag, p["applicant"].split("|")[0].strip()))
yt = collections.Counter(y for y, _, _ in rows)
cnt = collections.Counter((y, tg) for y, tg, _ in rows)
apps = collections.defaultdict(set); firsty = {}
for y, tg, a in sorted(rows):
    firsty.setdefault((tg, a), y)
topics = sorted({tg for _, tg, _ in rows})
share = lambda tg, ys: sum(cnt[(y, tg)] for y in ys) / max(1, sum(yt[y] for y in ys))
n = lambda tg, ys: sum(cnt[(y, tg)] for y in ys)
def sig(tg, c):
    rec, pre = range(c - 2, c + 1), range(c - 5, c - 2)
    if n(tg, rec) < 8: return None
    s1 = share(tg, rec) >= 1.5 * max(share(tg, pre), 1e-9)
    ra = {a for y, t2, a in rows if t2 == tg and y in rec}
    newr = sum(1 for a in ra if firsty[(tg, a)] >= c - 2) / max(1, len(ra))
    s2 = newr >= .6
    return dict(s1=s1, s2=s2, new=round(newr, 2), r=share(tg, rec), p=share(tg, pre))
med = lambda c: sorted(share(tg, range(c - 2, c + 1)) for tg in topics)[len(topics) // 2]
res = {"flag": [0, 0], "ctrl": [0, 0], "s1only": [0, 0], "calls": []}
for c in range(2016, 2021):
    fut = [y for y in range(c + 1, c + 5) if y <= 2024]
    for tg in topics:
        s = sig(tg, c)
        if not s: continue
        grew = share(tg, fut) > s["r"] * 1.2
        key = "flag" if s["s1"] and s["s2"] else "ctrl"
        res[key][0] += grew; res[key][1] += 1
        if s["s1"]: res["s1only"][0] += grew; res["s1only"][1] += 1
        if key == "flag": res["calls"].append(dict(c=c, topic=tg, grew=grew, new=s["new"], r=round(100 * s["r"], 2), fut=round(100 * share(tg, fut), 2)))
cand = []
for tg in topics:
    s = sig(tg, 2024)
    if s and (s["s1"] or s["s2"]):
        cand.append(dict(topic=tg, s1=s["s1"], s2=s["s2"], new=s["new"], quiet=s["r"] <= med(2024), share_recent=round(100 * s["r"], 2), share_prev=round(100 * s["p"], 2),
                         n_recent=n(tg, range(2022, 2025)), yearly={y: cnt[(y, tg)] for y in range(2010, 2026)}))
cand.sort(key=lambda x: (-(x["s1"] and x["s2"]), -x["share_recent"] / max(x["share_prev"], .01)))
out = dict(rule=__doc__, backtest=res, candidates=cand, topics=len(topics), n=len(rows),
           yearly_total={y: yt[y] for y in sorted(yt)}, topic_yearly={tg: {y: cnt[(y, tg)] for y in range(2007, 2027)} for tg in topics})
json.dump(out, open("../bongsu/data/emerge-data.json", "w"), ensure_ascii=False)
f, ct, s1 = res["flag"], res["ctrl"], res["s1only"]
print(f"주제 {len(topics)} · 특허 {len(rows)} | 판정(S1+S2) 성장 {f[0]}/{f[1]} = {100*f[0]/max(1,f[1]):.0f}% | 대조 {ct[0]}/{ct[1]} = {100*ct[0]/max(1,ct[1]):.0f}% | S1만 {s1[0]}/{s1[1]}")
for c in cand[:15]: print(("★" if c["s1"] and c["s2"] else " "), c["topic"], c["share_prev"], "→", c["share_recent"], "% | 새출원인", c["new"], "| 조용" if c["quiet"] else "")
