"""봉수대 코파일럿 — 질문 → 도구 선택 → 근거 달린 문장 → 숫자 검증 → 신뢰도 등급.
NAIS 해커톤 agent.py의 두 원칙을 가져옴: ① 답은 도구 결과로만 ② 도구 결과에 없는 숫자가 든 문장은 버린다.
신뢰도 = 문장을 받치는 '독립 출처 계열' 수 (뉴스·북측 발표·군 발표·논문·특허·센서). 같은 담화를 받아쓴 기사는 1개.
LLM: OpenRouter 경유 Claude.
"""
import json, os, re, subprocess, datetime as dt, html
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
MODEL = "anthropic/claude-sonnet-5.5"
import os as _os
_kp = Path.home() / ".config/openrouter/key"
KEY = (_os.environ.get("OPENROUTER_API_KEY") or (_kp.read_text().strip() if _kp.exists() else ""))  # 없으면 실시간 질의만 꺼지고 사전 실행본은 동작


def _load(name, default=None):
    p = DATA / name
    return json.loads(p.read_text()) if p.exists() else default


def _llm(messages, tools=None):
    if not KEY: raise RuntimeError("OPENROUTER_API_KEY가 없어 실시간 질의를 할 수 없습니다 — 예시 질문(사전 실행본)은 동작합니다")
    body = {"model": MODEL, "max_tokens": 8000, "temperature": 0, "messages": messages}
    if tools: body["tools"] = tools
    o = subprocess.run(["curl", "-s", "--max-time", "120", "https://openrouter.ai/api/v1/chat/completions",
                        "-H", "Authorization: Bearer " + KEY, "-H", "Content-Type: application/json",
                        "-d", json.dumps(body)], capture_output=True, text=True).stdout
    d = json.loads(o)
    if "error" in d: raise RuntimeError(str(d["error"])[:300])
    return d["choices"][0]["message"]


# ---------- 도구 ----------
def _verdict(eps, base):
    import math
    n = len(eps); k = sum(1 for e in eps if e.get("result"))
    if not n or not base: return {}
    z = 1.96; p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    lo, hi = 100 * (c - w), 100 * (c + w)
    v = "신호" if lo / base > 1 else "미결"
    return {"예고묶음": n, "7일내실행": k, "실행률%": round(100 * p, 1), "기준선%": base, "배수": round(100 * p / base, 1),
            "95%구간배수": [round(lo / base, 1), round(hi / base, 1)], "판정": v,
            "한줄": f"예고 {n}묶음 중 {k}건이 7일 안에 실행 — 기준선 {base}%의 {round(100*p/base,1)}배, 판정 '{v}'"}


def t_warnings(**_):
    B = _load("proto-data.json", {})
    return {"핵심판정": _verdict(B.get("episodes", []), (B.get("baseline") or {}).get("pct")),
            "설명": "북측 공식 주체의 예고 발표(원천 단위로 묶음)와 그 뒤 2~7일 내 살포 여부",
            "발표": [{"날짜": e["date"], "주체": e["actor"], "기사수": e["n_articles"], "매체수": len(e["outlets"]),
                    "결과": (f"{e['result']['lead']}일 뒤 살포 {e['result']['event']}" if e["result"] else "7일 내 살포 없음"),
                    "제목예": e["titles"][0]["title"], "출처계열": "북측 발표(언론 인용)"} for e in B.get("episodes", [])],
            "기준선": {**B.get("baseline", {}), "뜻": "아무 날이나 골랐을 때 2~7일 안에 살포가 있을 확률(%)"},
            "살포정답지": [{"날짜": x["date"], "이름": x["name"], "출처": x["src"], "사전경보": x["warned"]} for x in B.get("events", [])]}


def t_backtest(**_):
    B = _load("proto-data.json", {}); ev = B.get("events", [])
    dev = [e for e in ev if e["date"] < "2024-08-01"]; tst = [e for e in ev if e["date"] >= "2024-08-01"]
    B2 = _load("proto-data.json", {})
    return {"핵심판정": _verdict(B2.get("episodes", []), (B2.get("baseline") or {}).get("pct")),
            "개발기간_5~7월": f"{sum(e['warned'] for e in dev)}/{len(dev)} 사전경보(2~7일 전), 규칙을 이 기간에서 고름",
            "시험기간_8~10월": f"{sum(e['warned'] for e in tst)}/{len(tst)} — 예고 없는 재개, 공개 뉴스에 전조 없음",
            "대조_2023": "예고 1회(2023-11-07 '불소나기') 실행 없음 = 오경보 1",
            "실패한_두번째_계열": ["풍향(살포일 8건 중 2건만 남하풍, 평소 30%)", "남측 단체 살포 보도(8/10·9/4 직전 보도 없음)"]}


def t_trend(**_):
    d = _load("border-data.json", {"없음": "추세 데이터 미생성"})
    d["출처계열"] = "언론(Google 뉴스 월별 집계) — 근거 계열은 '언론'으로 적는다"
    return d


def t_tech(tech="", **_):
    T = _load("tech-data.json")
    if not T: return {"없음": "기술 데이터 미생성"}
    techs = T.get("techs", [])
    if tech:
        hit = [t for t in techs if tech.lower() in (t.get("key", "") + t.get("name_ko", "")).lower()]
        techs = hit or techs
    out = []
    for t in techs:
        out.append({"기술": t.get("name_ko"), "논문_연도별": t.get("yearly"), "국가별": t.get("countries"),
                    "기관_초기": (t.get("top_inst") or {}).get("early", [])[:8], "기관_최근": (t.get("top_inst") or {}).get("late", [])[:8],
                    "특허": {k: v for k, v in (t.get("patents") or {}).items() if k in ("total", "yearly", "top_applicants_org")},
                    "백테스트": {k: v for k, v in (t.get("backtest") or {}).items() if k != "calls"}, "판정예": (t.get("backtest") or {}).get("calls", [])[:8], "미완": t.get("incomplete"), "출처계열": "논문(OpenAlex)·특허(KIPRIS)"})
    return {"기술": out, "종합판정": T.get("verdict"), "주의": "2025년 이후 논문·특허는 색인 지연으로 적게 잡힐 수 있음"}


def t_news(query, after="", before="", **_):
    q = query + (f" after:{after}" if after else "") + (f" before:{before}" if before else "")
    o = subprocess.run(["curl", "-s", "--max-time", "25", "-A", "Mozilla/5.0", "-G", "https://news.google.com/rss/search",
                        "--data-urlencode", f"q={q}", "--data-urlencode", "hl=ko", "--data-urlencode", "gl=KR",
                        "--data-urlencode", "ceid=KR:ko"], capture_output=True, text=True).stdout
    if "<rss" not in o:
        return {"검색어": q, "오류": "뉴스 검색 일시 차단·실패 — 0건이 아니라 확인 불가. 이 사실을 답에 밝힌다"}
    items = re.findall(r"<item><title>(.*?)</title><link>(.*?)</link>.*?<pubDate>(.*?)</pubDate>", o, re.S)
    res = []
    for t, l, d in items[:25]:
        try: day = dt.datetime.strptime(d[5:16], "%d %b %Y").date().isoformat()
        except Exception: day = d
        res.append({"날짜": day, "제목": html.unescape(t), "링크": l})
    return {"검색어": q, "건수": len(items), "기사": res, "주의": "같은 발표를 여러 매체가 받아쓰면 출처는 1개로 센다"}


def t_sea(**_):
    S = _load("scs-data.json")
    if not S: return {"없음": "해상 데이터 미생성"}
    return {"핵심판정": _verdict(S["episodes"], (S.get("baseline") or {}).get("pct")),
            "설명": "남중국해 2024: 중국 당국·해경 경고 발표 → 2~7일 내 필리핀 선박 물대포·충돌. 규칙은 한반도에서 고정 후 그대로 적용",
            "경고발표": [{"날짜": e["date"], "주체": e["actor"], "기사수": e["n_articles"], "결과": (f"{e['result']['lead']}일 뒤 충돌 {e['result']['event']}" if e["result"] else "7일 내 충돌 없음"), "제목예": e["titles"][0]["title"], "출처계열": "중국 당국 발표(언론 인용)"} for e in S["episodes"]],
            "기준선": {**S.get("baseline", {}), "뜻": "아무 날이나 골랐을 때 2~7일 안에 충돌이 있을 확률(%)"},
            "경고후충돌": f"{sum(1 for e in S['episodes'] if e['result'])}/{len(S['episodes'])}",
            "충돌정답지": [{"날짜": x["date"], "이름": x["name"], "출처": x["src"], "출처계열": "필리핀 정부 발표", "사전경보": x["warned"]} for x in S["events"]]}


def t_iran(**_):
    I = _load("iran-data.json")
    if not I: return {"없음": "이란 데이터 미생성"}
    out = {"설명": "이란↔이스라엘·미국: 공식 예고 → 2~7일 내 공격. 규칙은 한반도에서 고정 후 적용", "유가출처": "FRED DCOILBRENTEU"}
    for k, nm in (("IR", "이란 예고→이란 공격"), ("IL", "이스라엘·미국 예고→타격")):
        s = I["sides"][k]
        out[nm] = {"예고묶음": [{"날짜": e["date"], "기사수": e["n_articles"], "결과": (f"{e['result']['lead']}일 뒤 공격 {e['result']['event']}" if e["result"] else "7일 내 공격 없음"), "제목예": e["titles"][0]["title"], "출처계열": "이란 당국 발표" if k == "IR" else "이스라엘·미국 정부 발표"} for e in s["episodes"]][:25],
                   "공격정답지": [{"날짜": e["date"], "이름": e["name"], "사전경보": e["warned"], "출처계열": "언론(공식 발표 인용)"} for e in s["events"]], "기준선": s["baseline"]}
    P = I["brent"]; ds = sorted(P)
    def near(d, k):
        i = next(j for j, x in enumerate(ds) if x >= d); return ds[max(0, min(len(ds) - 1, i + k))]
    out["유가반응"] = [{"날짜": e["date"], "사건": e["name"], "당일": P[near(e["date"], 0)], "5일뒤%": round(100 * (P[near(e["date"], 5)] / P[near(e["date"], 0)] - 1), 1), "20일뒤%": round(100 * (P[near(e["date"], 20)] / P[near(e["date"], 0)] - 1), 1)} for k in ("IR", "IL") for e in I["sides"][k]["events"]]
    out["유가최신"] = {"날짜": ds[-1], "가격": P[ds[-1]]}
    return out


def t_nk10(**_):
    d = _load("nk10-data.json")
    if not d: return {"없음": "북한 10년 데이터 미생성"}
    st = d["strict"]
    return {"설명": "북한 도발 10년(2016~2026, CSIS 도발 데이터베이스) — 도발 시작점 114건 vs 도발 없던 대조 기간 114개. 직전 2~7일에 북한 당국의 '앞으로 할 행동' 경고가 있었나",
            "핵심판정": {"적중": f"{st['hit'][0]}/{st['hit'][1]} (95% 구간 {st['hit'][2]})", "헛경보": f"{st['fa'][0]}/{st['fa'][1]} (95% 구간 {st['fa'][2]})", "평소대비배수": st["lr"],
                       "한줄": f"북한이 경고하면 며칠 안 도발 가능성이 평소의 약 {st['lr']}배 — 단 도발 10건 중 7건은 경고 없이 일어남"},
            "주의": st["note"], "참고_2010": "천안함(2010-03-26)·연평도(2010-11-23) 직전 10일 북한 당국 경고 기사 없음 — 예고 없는 도발",
            "경고있던도발예": [{"날짜": r["anchor"], "도발": r["event"], "경고제목": r["titles"][0], "며칠전": r["lead"], "출처계열": "북측 발표(언론 인용)"} for r in st["onsets"] if r["warned"]][:15],
            "정답지출처": "CSIS Beyond Parallel North Korean Provocations Database"}


def t_outlook(actor="", keywords="", **_):
    """이번 발언 → 앞으로: 과거 10년 비슷한 북한 당국 경고와 그 뒤에 벌어진 일."""
    C = _load("nk-cases.json")
    if not C: return {"없음": "사례집 미생성"}
    cs = C["cases"]; kw = [k for k in re.split(r"[ ,·]+", keywords or "") if len(k) >= 2]
    def score(c):
        return (3 if actor and actor in c["actor"] else 0) + sum(1 for k in kw if k in c["title"])
    ranked = sorted(cs, key=lambda c: (score(c), c["date"]), reverse=True)[:8]
    P = C["prob"]
    return {"확률": f"북한 당국의 미래 행동 경고 뒤 2~7일 안 도발이 시작될 확률 약 {P['post']}% (평소 {P['base']}%의 약 {P['lr']}배)",
            "확률근거": P["note"], "지켜볼기간": "경고일 기준 2~7일 뒤", "도발 10건 중 7건은 경고 없이 일어남": True,
            "장소경향": "큰 무기 시험장(동창리·신포)은 예고 후 실행 절반, 단거리 다발 지역(순안·원산)은 대부분 무예고(표본 작음)",
            "비슷한선례": [{"날짜": c["date"], "주체": c["actor"], "경고": c["title"], "그뒤": ([f"{e['date']} {e['event']} ({e['site']})" for e in c["events"]] or ["2~7일 안 도발 없음"]), "출처계열": "북측 발표(언론 인용)"} for c in ranked],
            "주의": "선례는 비슷한 말이 나왔던 과거일 뿐, 이번에 같은 일이 벌어진다는 뜻이 아니다"}


TOOLS_IMPL = {"warnings": t_warnings, "backtest": t_backtest, "border_trend": t_trend, "tech": t_tech, "news": t_news, "sea": t_sea, "iran": t_iran, "nk10": t_nk10, "outlook": t_outlook}
TOOLS = [
    {"type": "function", "function": {"name": "warnings", "description": "회색지대(풍선) 도발: 북측 예고 발표 목록과 실제 살포 정답지(합참 인용).", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "backtest", "description": "봉수대 경보가 과거에 얼마나 맞았는지 성적표(성공·실패 포함).", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "border_trend", "description": "북한 국경선 요새화·지뢰 매설·군사분계선 침범 보도의 월별 추세와 2026-09-21 DMZ 지뢰 폭발 전후.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "tech", "description": "무기 기술(극초음속·드론 군집·대드론·레이저·전자전)의 논문·특허 추이, 국가·기관, 뜨는 기관 판정의 백테스트.", "parameters": {"type": "object", "properties": {"tech": {"type": "string", "description": "기술 이름 일부(예: 극초음속). 비우면 전체"}}}}},
    {"type": "function", "function": {"name": "sea", "description": "해상 회색지대(남중국해 2024 중국 해경 vs 필리핀): 중국 측 경고 발표와 실제 충돌 정답지, 사전경보 여부.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "outlook", "description": "이번에 북한(김정은·김여정·외무성 등)이 경고·위협했을 때 앞으로 벌어질 일 전망: 과거 10년 비슷한 경고의 선례와 그 뒤 도발, 확률, 지켜볼 기간. '누가 뭐 했는데 어떻게 될까' 질문에 먼저 쓴다.", "parameters": {"type": "object", "properties": {"actor": {"type": "string", "description": "김정은/김여정/외무성/국방성/총참모부"}, "keywords": {"type": "string", "description": "이번 발언의 핵심어(예: 무인기 보복 영토)"}}}}},
    {"type": "function", "function": {"name": "nk10", "description": "북한 도발 10년(2016~2026, 114건): 북한 당국 경고가 도발 직전에 있었던 비율 vs 평소, 우도비, 천안함·연평도 참고.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "iran", "description": "이란↔이스라엘·미국 공식 예고와 실제 공격(2024~2026), 기준선 대비 배수, 사건 전후 브렌트유 반응(FRED).", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "news", "description": "Google 뉴스 실시간 검색(한국어). 날짜 범위 YYYY-MM-DD 선택.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "after": {"type": "string"}, "before": {"type": "string"}}, "required": ["query"]}}},
]

SYSTEM = """너는 '봉수대' — 국방 OSINT 분석관을 돕는 공개정보 코파일럿이다. 판단은 분석관이 한다.
규칙:
1. 반드시 도구를 먼저 불러 근거를 모은다. 도구 결과에 없는 사실·숫자는 쓰지 않는다.
2. 원리: 첩보를 모아 독립적으로 겹치는 것만 정보로 본다. 같은 발표를 받아쓴 기사 여러 건은 출처 1개.
3. 최종 답은 JSON만: {"요약": "한 문장", "문장": [{"text": "...", "근거": [{"제목": "...", "링크": "선택", "계열": "북측 발표|군 발표|중국 당국 발표|필리핀 정부 발표|이란 당국 발표|이스라엘·미국 정부 발표|시장 데이터|언론|논문|특허|센서|내부집계"}]}], "한계": ["..."], "다음확인": ["분석관이 다음에 확인할 것 2~3개. 도구 결과에서 나온 근거(과거 실행률·시점 범위·출처 계열 공백)로만"]}
4. 한 문장을 서로 다른 계열의 근거가 함께 받치면 근거에 모두 단다(예: 북측 예고 기사 + 그 뒤 살포를 확인한 합참 발표). 실제로 받치지 않는 근거를 억지로 붙이지 않는다. 교차 확인되는 사실을 먼저 쓴다.
5. 봉수대 자체 집계(backtest·warnings의 결과 칸)는 독립 출처가 아니다. 근거로 달 때 계열을 "내부집계"로 적는다.
6. 예고 묶음 수·실행 수·기준선은 도구가 준 숫자를 그대로 쓴다. 다시 묶거나 다시 세지 않는다(화면과 숫자가 달라진다).
7. "우도비" 같은 통계 용어 대신 "평소의 N배"처럼 쉬운 말을 쓴다.
7-1. 짧게 쓴다: 문장은 최대 3개, 각 50자 이내, 한 문장에 사실 하나. 핵심 숫자를 먼저. "다음확인"은 2개(각 35자 이내), "한계"는 1개(40자 이내). 설명·접속사·반복 금지.
8. "누가 뭐 했는데 어떻게 될까" 질문이면: 먼저 news로 이번 발언을 찾고, outlook으로 확률·지켜볼 기간·선례를 가져와 [이번 발언 → 확률 → 지켜볼 기간 → 선례 2~3건] 순서로 답한다. 기간은 실제 날짜로 계산해 쓴다.
8-1. 도구에 "핵심판정"이 있으면 그 판정(신호/미결·배수)을 첫 문장으로 쓰고, 예외·실패는 그 다음에 쓴다.
9. (구) 문장은 4~7개, 짧게. 과거 성적·실패도 숨기지 않는다. 예측을 단정하지 않는다.
"""


NAMES = ["김여정", "김정은", "국방성", "총참모부", "조선중앙통신", "노동신문", "유엔사", "합참", "국방부", "통일부", "국정원"]


def _parse(t):
    try: return json.loads(t[t.index("{"): t.rindex("}") + 1], strict=False)
    except Exception: return None


def _nums(s):
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*\.?\d*", s)}


def _brief(name, r):
    if not isinstance(r, dict): return ""
    for k in ("기사", "발표", "경고발표", "기술", "충돌정답지", "살포정답지"):
        if isinstance(r.get(k), list): return f"{k} {len(r[k])}건"
    if "months" in r: return f"{len(r['months'])}개월 추세"
    return f"{len(json.dumps(r, ensure_ascii=False))}자"


def ask(question, log=None):
    emit = log or (lambda *a, **k: None)
    emit("plan", text="질문 해석 · 쓸 도구 고르는 중")
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    evidence = ""
    steps = []
    for _ in range(6):
        m = _llm(msgs, TOOLS)
        calls = m.get("tool_calls") or []
        if not calls: break
        if m.get("content"): emit("think", text=m["content"][:200])
        msgs.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": calls})
        for c in calls:
            name = c["function"]["name"]; args = json.loads(c["function"]["arguments"] or "{}")
            emit("tool", name=name, args=args)
            try: r = TOOLS_IMPL[name](**args)
            except Exception as e: r = {"오류": str(e)}
            s = json.dumps(r, ensure_ascii=False)[:14000]
            evidence += s; steps.append({"도구": name, "인자": args})
            emit("result", name=name, text=_brief(name, r))
            msgs.append({"role": "tool", "tool_call_id": c["id"], "content": s})
    else:
        m = _llm(msgs)
    emit("draft", text=f"근거 {len(steps)}묶음으로 답 작성")
    txt = m.get("content") or ""
    ans = _parse(txt)
    if ans is None:  # 깨진 JSON → 한 번 고쳐 받는다
        fix = _llm([{"role": "user", "content": "아래를 같은 내용의 올바른 JSON 객체 하나로만 다시 출력하라. 문자열 안 큰따옴표는 작은따옴표로 바꿔라.\n\n" + txt}])
        ans = _parse(fix.get("content") or "")
    if ans is None: return {"요약": "답을 구조화하지 못했다", "문장": [], "버린문장": [], "한계": [txt[:300]], "도구": steps}
    ok_nums = _nums(evidence + question)
    # 증거 숫자끼리 계산한 값(차·합·백분율)도 허용 — '20건 중 4건 → 나머지 16건' 같은 문장
    ints = sorted({int(float(n)) for n in ok_nums if n.replace(".", "", 1).isdigit() and float(n) <= 1000})[:400]
    for a in ints:
        for b in ints:
            if a > b: ok_nums.add(str(a - b))
            if a + b <= 1000: ok_nums.add(str(a + b))
            if b and a <= b: ok_nums.add(str(round(100 * a / b))); ok_nums.add(str(round(100 * a / b, 1)))
    kept, dropped = [], []
    for s in ans.get("문장", []):
        bad = [n for n in _nums(s.get("text", "")) if n not in ok_nums]
        bad += [w for w in NAMES if w in s.get("text", "") and w not in evidence + question]
        fams = {g.get("계열") for g in s.get("근거", []) if g.get("계열") and g.get("계열") != "내부집계"}
        if "언론" in fams and fams & {"군 발표", "북측 발표", "중국 당국 발표", "필리핀 정부 발표", "이란 당국 발표", "이스라엘·미국 정부 발표"}: fams.discard("언론")  # 발표를 받아쓴 언론은 독립 출처 아님
        internal = any(g.get("계열") == "내부집계" for g in s.get("근거", []))
        s["등급"] = "다중" if len(fams) >= 3 else "교차" if len(fams) == 2 else "단일" if fams else "집계"
        (dropped if bad or s["등급"] == "근거없음" else kept).append({**s, "검증실패": bad} if bad else s)
    emit("check", text=f"숫자·이름 대조: 통과 {len(kept)} · 탈락 {len(dropped)}")
    emit("verify", text=f"검증자 LLM이 {len(kept)}문장 대조 중")
    kept, dropped2 = _verify(kept, evidence)
    emit("verified", text=f"검증 통과 {len(kept)} · 탈락 {len(dropped2)}")
    # 요약은 검증을 통과한 문장만으로 다시 쓴다 (버린 내용이 요약에 남는 모순 방지)
    if kept:
        t = _llm([{"role": "user", "content": "질문: " + question + "\n아래 문장들만 근거로 45자 이내 한 문장 요약을 써라. 질문에 대한 직접 답(예/아니오/일부)으로 시작. 새 사실·숫자 추가 금지. 요약 문장만 출력.\n\n" + "\n".join(x["text"] for x in kept)}])
        ans["요약"] = (t.get("content") or "").strip() or kept[0]["text"]
    else:
        ans["요약"] = "근거로 확인된 답이 없다"
    ans["문장"], ans["버린문장"], ans["도구"] = kept, dropped + dropped2, steps
    emit("done", text="봉수 올림")
    return ans


VERIFY = """너는 검증자다. 아래 '증거'만 보고, 각 문장이 증거로 완전히 뒷받침되는지 판정하라.
숫자가 증거에 있어도 다른 대상·기간의 숫자를 갖다 붙였으면 'no'. 증거에 없는 사실이 하나라도 있으면 'no'.
JSON 배열만: [{"i":번호,"ok":"yes|no","why":"no일 때 15자 이내"}]
"""


def _verify(sents, evidence):
    if not sents: return [], []
    body = VERIFY + "\n증거:\n" + evidence[:60000] + "\n\n문장:\n" + "\n".join(f"{i}. {s['text']}" for i, s in enumerate(sents))
    try:
        t = _llm([{"role": "user", "content": body}])["content"]
        res = {x["i"]: x for x in json.loads(t[t.index("["): t.rindex("]") + 1])}
    except Exception as e:  # 검증자 실패 → 통과시키되 '미검증'으로 표시 (조용히 넘기지 않는다)
        return [{**x, "미검증": True} for x in sents], []
    ok, bad = [], []
    for i, s in enumerate(sents):
        r = res.get(i, {"ok": "yes"})
        (ok if r.get("ok") == "yes" else bad).append(s if r.get("ok") == "yes" else {**s, "검증실패": ["검증자: " + r.get("why", "")]})
    return ok, bad


if __name__ == "__main__":
    import sys
    print(json.dumps(ask(" ".join(sys.argv[1:]) or "오물풍선 예고 발표가 실제 살포로 이어졌나?"), ensure_ascii=False, indent=1))
