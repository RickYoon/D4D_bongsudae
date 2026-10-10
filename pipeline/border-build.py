"""추세 봉수 데이터 → bongsu/data/border-data.json. 2026-09·10은 사건 이후라 그래프 척도에서 제외(값은 notes에)."""
import csv, json, collections
r = list(csv.DictReader(open("example/border.csv")))
ks = ["국경선 요새화", "지뢰 매설", "군사분계선 침범"]
S = {k: {} for k in ks}
for x in r: S[x["kw"]][x["month"]] = int(x["n"] or 0)
months = sorted({x["month"] for x in r if x["month"] <= "2026-08"})
avg = lambda k, a, b: round(sum(S[k][m] for m in months if a <= m <= b) / len([m for m in months if a <= m <= b]), 1)
out = {"keywords": ks, "months": months, "series": S,
  "marks": [{"month": "2024-04", "label": "요새화 착수(합참)", "color": "#8b95a4", "row": 0},
            {"month": "2026-08", "label": "8/16 MDL 침범·경고사격", "color": "#f2b33a", "row": 1},
            {"month": "2026-08", "label": "→ 9/21 DMZ 지뢰 폭발", "color": "#e04f5f", "row": 2}],
  "verdict": "느린 상승 + 5주 전 MDL 침범 — 경계 상향 근거, 예측 아님",
  "notes": [f"'국경선 요새화' 월평균: 2024년 1~3월(착수 전) {avg('국경선 요새화','2024-01','2024-03')}건 = 검색 잡음 바닥 → 2025년 7~12월 {avg('국경선 요새화','2025-07','2025-12')}건 → 2026년 1~8월 {avg('국경선 요새화','2026-01','2026-08')}건",
            "사건 직전 급등은 없었다: 2026년 8월 요새화 보도는 오히려 31건으로 줄었다",
            "2026-08-16 동부전선 북한군 MDL 침범, 군 올해 첫 경고사격(연합뉴스TV·KBS 등) — 폭발 36일 전",
            "같은 'MDL 침범' 보도 급등이 2024-06(49)·2025-04(15)·2025-11(20)에도 있었고 그때는 사상 사고 없음 → 4회 중 1회",
            f"사건 후: 2026-09 요새화 {S['국경선 요새화']['2026-09']}건·지뢰 매설 {S['지뢰 매설']['2026-09']}건(상한 도달, 주 단위 합산) — 척도에서 제외",
            "폭발 2026-09-21(RFA, 합참 발표 인용) · 9/28 합참 '북한 지뢰 가능성 매우 높아' · 이후 고의 매설 결론(MBC)",
            "한계: Google 뉴스 검색 수는 실제 보도량의 표본이다. 사건 1건이라 통계적 증명이 아니다"]}
json.dump(out, open("bongsu/data/border-data.json", "w"), ensure_ascii=False)
print(out["notes"][0])
