#!/usr/bin/env python3
"""기술 봉수 데이터 빌더 — OpenAlex + KIPRIS Plus → tech-data.json
직렬·2초 간격. KIPRIS 키는 ~/.config/kipris/key 에서 읽고 어디에도 출력하지 않는다.
원응답 캐시: ./tech-cache/ (키 포함 URL은 저장하지 않음)
"""
import json, os, re, time, hashlib, datetime, xml.etree.ElementTree as ET
from collections import Counter, defaultdict
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "tech-cache"); os.makedirs(CACHE, exist_ok=True)
KEY = open(os.path.expanduser("~/.config/kipris/key")).read().strip()
YEARS = list(range(2014, 2026))
FOCUS = ["CN", "US", "KR", "IN", "RU"]
KIPRIS_ROWS, KIPRIS_MAX_PAGES = 500, 10   # 키워드당 최대 5,000건
FAILS = []

TECHS = [
  dict(key="hypersonic", name_ko="극초음속",
       oa='title.search:"hypersonic missile"|"hypersonic missiles"|"hypersonic weapon"|"hypersonic weapons"|"hypersonic glide"|"hypersonic vehicle"|"hypersonic vehicles"|scramjet',
       kw=["극초음속"]),
  dict(key="drone_swarm", name_ko="드론 군집",
       oa='title.search:"drone swarm"|"drone swarms"|"UAV swarm"|"UAV swarms"|"swarm of drones"|"swarm of UAVs"|"UAS swarm"',
       kw=["드론 군집", "군집 드론"]),
  dict(key="counter_uas", name_ko="대드론",
       oa='title.search:"counter-UAS"|"counter UAS"|"counter-drone"|"anti-drone"|"drone detection"|"UAV detection"|"drone interception"',
       kw=["대드론", "드론 무력화", "안티 드론", "드론 방어"]),
  dict(key="laser_weapon", name_ko="레이저 무기",
       oa='title.search:"laser weapon"|"laser weapons"|"high-energy laser"|"high energy laser"|"directed energy weapon"|"directed energy weapons"',
       kw=["레이저 무기", "레이저무기", "고에너지 레이저"]),
  dict(key="ew", name_ko="전자전",
       oa='title.search:"electronic warfare"|"radar jamming"|"jamming suppression"|"anti-jamming"|"deceptive jamming"|"jamming signal"',
       kw=["전자전", "재밍"]),
]

_last = [0.0]
def get(url, params, tag, secret=False):
    h = hashlib.md5((url + json.dumps(params, sort_keys=True)).encode()).hexdigest()[:16]
    fp = os.path.join(CACHE, f"{tag}-{h}.txt")
    if os.path.exists(fp):
        return open(fp, encoding="utf-8").read()
    if tag == "oa" and os.environ.get("OA_CACHE_ONLY"):
        FAILS.append(dict(tag=tag, params=params, error="skipped: OpenAlex 일일 예산 소진(429), 캐시 없음", attempt=2)); return None
    wait = 2.0 - (time.time() - _last[0])
    if wait > 0: time.sleep(wait)
    p = dict(params)
    if secret: p["ServiceKey"] = KEY
    for attempt in range(3):
        try:
            r = requests.get(url, params=p, timeout=60); _last[0] = time.time()
            if r.status_code == 200:
                t = r.text.replace(KEY, "***")
                open(fp, "w", encoding="utf-8").write(t); return t
            FAILS.append(dict(tag=tag, params={k: v for k, v in params.items()}, status=r.status_code, attempt=attempt))
        except Exception as e:
            _last[0] = time.time()
            FAILS.append(dict(tag=tag, params=params, error=type(e).__name__, attempt=attempt))
        time.sleep(5)
    return None

def oa(filt, group):
    t = get("https://api.openalex.org/works", {"filter": filt, "group_by": group, "per_page": 200}, "oa")
    if t is None: return None
    return [(g["key"], g.get("key_display_name"), g["count"]) for g in json.loads(t)["group_by"]]

# ---------- 백테스트 규칙 (데이터 보기 전에 고정, 2026-10-10) ----------
RULE = ("판정(2016~2020만 사용): 2018~2020 연평균 ≥ 1.5 × 2016~2017 연평균 AND 2016~2020 합계 ≥ 10건 → '뜨는' 판정. "
        "대상 = 국가: 2016~2020 합계 상위 15개국 / 기관: 2016~2020 합계 상위 20개 기관. "
        "채점: 2021~2025 연평균 > 2018~2020 연평균 이면 적중(계속 늘었음). "
        "주의: 2025는 색인 지연 가능 → 보조로 2021~2024 기준 적중도 함께 기록(규칙 변경 아님, 병기).")

def avg(d, ys): return sum(d.get(y, 0) for y in ys) / len(ys)

def backtest(series_by_entity, top_n):
    early_tot = {e: sum(s.get(y, 0) for y in range(2016, 2021)) for e, s in series_by_entity.items()}
    cand = sorted(early_tot, key=lambda e: -early_tot[e])[:top_n]
    calls = Calls()
    for e in cand:
        s = series_by_entity[e]
        a, b = avg(s, [2016, 2017]), avg(s, [2018, 2019, 2020])
        if early_tot[e] < 10: continue
        if a == 0 or b >= 1.5 * a:
            c, c4 = avg(s, range(2021, 2026)), avg(s, range(2021, 2025))
            calls.append(dict(entity=e, early_growth=round(b / a, 2) if a else None,
                              late_growth=round(c / b, 2) if b else None, hit=c > b,
                              hit_2021_2024=c4 > b, avg_16_17=a, avg_18_20=round(b, 2), avg_21_25=round(c, 2)))
        else:  # 대조군: 같은 후보 풀에서 '뜨는' 판정을 받지 않은 것 (10/10 추가, 판정 규칙은 불변)
            calls.ctrl.append(avg(s, range(2021, 2026)) > b)
    return calls


class Calls(list):
    def __init__(self): super().__init__(); self.ctrl = []

# ---------- KIPRIS ----------
ORG_PAT = re.compile(r"(주식회사|\(주\)|㈜|유한|재단|법인|연구원|연구소|대학|학교|공사|공단|국방과학|청$|부$|본부|센터|협회|조합|"
                     r"Inc|INC|Corp|CORP|Co\.|CO\.|Ltd|LTD|LLC|GmbH|AG$|S\.A|University|UNIVERSITY|Institute|INSTITUTE|Company|COMPANY|Technologies|"
                     r"엘아이지|한화|LIG|현대|삼성|엘지|에스케이|기아|대한항공|국방|공업|산업|테크|시스템|전자|에어로|넥스원|디펜스|코리아)")
def is_org(n): return bool(ORG_PAT.search(n)) or len(n) > 6

def kipris(word):
    items, total, pages = {}, None, 0
    for p in range(1, KIPRIS_MAX_PAGES + 1):
        t = get("http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getAdvancedSearch",
                {"inventionTitle": word, "numOfRows": KIPRIS_ROWS, "pageNo": p}, "kp", secret=True)
        if t is None: break
        root = ET.fromstring(t); pages += 1
        if root.findtext(".//successYN") not in (None, "Y"):
            FAILS.append(dict(tag="kp", word=word, page=p, msg=root.findtext(".//resultMsg"))); break
        total = int(root.findtext(".//totalCount") or 0)
        its = root.findall(".//item")
        for it in its:
            items[it.findtext("applicationNumber")] = dict(
                date=it.findtext("applicationDate") or "", appl=it.findtext("applicantName") or "",
                title=it.findtext("inventionTitle") or "")
        if p * KIPRIS_ROWS >= total or not its: break
    return items, total, pages

def main():
    out = []
    for T in TECHS:
        print("==", T["key"]); f0 = sum(1 for f in FAILS if f["tag"] == "oa" and f.get("attempt") == 2)
        base = T["oa"]
        yearly = oa(base + ",publication_year:2014-2025", "publication_year")
        yearly = sorted([dict(y=int(k), n=c) for k, _, c in (yearly or [])], key=lambda r: r["y"])
        ctry = defaultdict(dict); inst = defaultdict(dict); inst_name = {}
        for y in YEARS:
            g = oa(base + f",publication_year:{y}", "authorships.countries")
            for k, _, c in g or []:
                ctry[k.rsplit("/", 1)[-1].upper()][y] = c
            g = oa(base + f",publication_year:{y}", "authorships.institutions.lineage")
            for k, nm, c in g or []:
                iid = k.rsplit("/", 1)[-1]; inst[iid][y] = c; inst_name[iid] = nm
        def topn(ys, n=15):
            tot = {i: sum(s.get(y, 0) for y in ys) for i, s in inst.items()}
            return [dict(name=inst_name[i], id=i, n=tot[i]) for i in sorted(tot, key=lambda i: -tot[i])[:n]]
        # 한국 기관: country 필터로 별도 조회 (기관 국적 판별용)
        kr = {}
        for per, ys in (("early", "2016-2020"), ("late", "2021-2025")):
            g = oa(base + f",publication_year:{ys},authorships.institutions.country_code:KR", "authorships.institutions.lineage")
            kr[per] = g
        # KR 필터 group_by는 공저 외국기관도 포함 → 기관 국가 조회 대신 이름으로 표시만 하고, 국가 필터 count 사용
        kr_top = {}
        for per in ("early", "late"):
            kr_top[per] = [dict(name=nm, id=k.rsplit("/", 1)[-1], n=c) for k, nm, c in (kr[per] or [])[:30]]
        # 특허
        allp, totals = {}, {}
        for w in T["kw"]:
            its, tot, pages = kipris(w); totals[w] = dict(total=tot, fetched=len(its), pages=pages)
            allp.update(its)
        py = Counter(v["date"][:4] for v in allp.values() if v["date"][:4].isdigit())
        org = Counter(); person = Counter(); orgy = defaultdict(Counter)
        for v in allp.values():
            for a in [a.strip() for a in re.split(r"[|;]", v["appl"]) if a.strip()]:
                if is_org(a): org[a] += 1; orgy[a][v["date"][:4]] += 1
                else: person[a] += 1
        pat_series = {a: {int(y): n for y, n in c.items() if y.isdigit()} for a, c in orgy.items()}
        bt_c = backtest({k: v for k, v in ctry.items()}, 15)
        bt_i = backtest({inst_name[i]: s for i, s in inst.items()}, 20)
        bt_p = backtest(pat_series, 20)
        calls = [dict(c, kind="country") for c in bt_c] + [dict(c, kind="institution") for c in bt_i]
        out.append(dict(
            key=T["key"], name_ko=T["name_ko"], query_openalex=base,
            openalex_failed_calls=sum(1 for f in FAILS if f["tag"] == "oa" and f.get("attempt") == 2) - f0,
            yearly=yearly,
            countries={c: [dict(y=y, n=ctry.get(c, {}).get(y, 0)) for y in YEARS] for c in FOCUS},
            countries_all_total={c: sum(s.values()) for c, s in sorted(ctry.items(), key=lambda x: -sum(x[1].values()))[:25]},
            top_inst=dict(early=topn(range(2016, 2021)), late=topn(range(2021, 2026))),
            kr_inst=kr_top,
            patents=dict(query=T["kw"], per_keyword=totals, total=len(allp),
                         yearly=[dict(y=int(y), n=n) for y, n in sorted(py.items()) if int(y) >= 2000],
                         top_applicants_org=[dict(name=a, n=n) for a, n in org.most_common(20)],
                         n_org_filings=sum(org.values()), n_person_filings=sum(person.values()),
                         backtest_org=dict(calls=bt_p, hits=sum(c["hit"] for c in bt_p), total=len(bt_p))),
            backtest=dict(rule=RULE, calls=calls, hits=sum(c["hit"] for c in calls), total=len(calls),
                          control=dict(hits=sum(sum(x.ctrl) for x in (bt_c, bt_i)), total=sum(len(x.ctrl) for x in (bt_c, bt_i)),
                                       desc="같은 후보 풀에서 '뜨는' 판정을 안 받은 국가·기관 중 2021~25 연평균이 2018~20보다 큰 비율"),
                          hits_2021_2024=sum(c["hit_2021_2024"] for c in calls)),
        ))
    res = dict(techs=out, generated_at=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
               sources=dict(openalex="https://api.openalex.org/works (group_by, 직렬 2초)",
                            kipris="KIPRIS Plus patUtiModInfoSearchSevice/getAdvancedSearch inventionTitle=키워드 (발명명칭 검색, 500행×최대10쪽/키워드, 키워드 간 출원번호로 중복 제거)"),
               failures=FAILS)
    json.dump(res, open(os.path.join(HERE, "tech-data.json"), "w"), ensure_ascii=False, indent=1)
    print("failures:", len(FAILS))

if __name__ == "__main__":
    main()
