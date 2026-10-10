"""GDELT 북한 위협 신호 채점 — 규칙 고정(2026-10-10, 결과 보기 전).
일별 위협 비중 s_t = r13_threat / total (total ≥ 30인 날만). z_t = (s_t − 직전 90일 평균) / 직전 90일 표준편차.
경보일 = z_t ≥ 2. 시점 A에서 '경보' = A-7 ~ A-2 사이 경보일 1개 이상.
비교: CSIS 도발 시작점 114 vs 대조 114 (nkdb/design.json, 뉴스 채점과 동일 설계) → 적중률·헛경보율·우도비.
추가: 10년 일별 시계열(주 단위 평균)을 차트용으로 저장.
"""
import csv, json, math, statistics as st, datetime as dt
R = [r for r in csv.DictReader(open("nkdb/gdelt_daily.csv"))]
S = {r["date"]: (int(r["r13_threat"]) / int(r["total"]) if int(r["total"]) >= 30 else None) for r in R}
T = {r["date"]: int(r["total"]) for r in R}
days = sorted(S); D = dt.date.fromisoformat
Z = {}
for i, d in enumerate(days):
    hist = [S[x] for x in days[max(0, i - 90):i] if S[x] is not None]
    if S[d] is None or len(hist) < 45: continue
    sd = st.pstdev(hist) or 1e-9; Z[d] = (S[d] - st.mean(hist)) / sd
alarm = {d for d, z in Z.items() if z >= 2}
X = json.load(open("nkdb/design.json"))
def warned(a): A = D(a); return any(str(A - dt.timedelta(k)) in alarm for k in range(2, 8))
def wil(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d; return [round(100 * (c - h), 1), round(100 * (c + h), 1)]
on = [a for a in X["onsets"] if any(str(D(a) - dt.timedelta(k)) in Z for k in range(2, 8))]
ct = [a for a in X["controls"] if any(str(D(a) - dt.timedelta(k)) in Z for k in range(2, 8))]
k1 = sum(map(warned, on)); k0 = sum(map(warned, ct))
weekly = {}
for d in days:
    wk = str(D(d) - dt.timedelta(D(d).weekday()))
    if S[d] is not None: weekly.setdefault(wk, []).append(S[d])
out = dict(rule=__doc__, n_days=len(days), n_events=sum(T.values()), alarm_days=len(alarm), hit=[k1, len(on), wil(k1, len(on))], fa=[k0, len(ct), wil(k0, len(ct))],
           lr=round((k1 / len(on)) / max(k0 / len(ct), 1e-9), 2), weekly=[[w, round(100 * st.mean(v), 2)] for w, v in sorted(weekly.items())],
           events=[{"date": e["date"][:10], "type": e["type"], "event": e["event"]} for e in X["events"]])
json.dump(out, open("../bongsu/data/gdelt-nk.json", "w"), ensure_ascii=False)
print(f"일수 {len(days)} · 북한 사건 {out['n_events']:,} · 경보일 {len(alarm)} | 적중 {k1}/{len(on)} {out['hit'][2]} · 헛경보 {k0}/{len(ct)} {out['fa'][2]} · 우도비 {out['lr']}")
