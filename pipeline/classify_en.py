"""EN v1 (2026-10-10 남중국해, 결과 보기 전 고정 — 한국어 v4와 같은 정의를 영어·중국 주체로)\nv4 (2026-10-10, 결과 보기 전 고정): TRIG 라벨 추가. v3 WARN 정의 불변.
v3: LLM 분류기. 프롬프트는 결과 보기 전 고정 (2026-10-10). 2024·2023에 동일 적용.
1차 거름(느슨): 제목에 전단·삐라·오물·풍선·쓰레기 중 하나.
2차 LLM: 제목마다 라벨 하나
  WARN   = 북한 당국·공식 인물(김여정, 국방성, 조선중앙통신 등)이 앞으로 할 행동을 경고·예고·위협
  REPORT = 이미 일어난 살포·발견·피해·대응의 보도
  OTHER  = 그 외 (남측 단체·정부·정치권 발언, 해설 등)
경보 = 그날 WARN 제목 ≥1. 적중 = 경보 후 1~7일 내 살포 개시.
사용: python3 classify.py <csv> <out.json>
"""
import csv, json, re, sys, os
import subprocess

PROMPT_KO_UNUSED = """아래는 한국어 뉴스 제목 목록이다. 각 제목에 라벨 하나를 붙여라.
WARN = 북한 당국 또는 공식 인물(김여정, 국방성, 조선중앙통신, 노동신문 등)이 '앞으로 할' 행동을 경고·예고·위협하는 내용
REPORT = 이미 일어난 살포·발견·피해·대응을 보도하는 내용
TRIG = 남측 민간단체(탈북민단체 등)가 대북전단·풍선을 북으로 실제로 날렸다는 보도
OTHER = 그 외 (남측 정부·정치권 발언, 해설, 무관한 내용)
제목에 없는 사실을 추측하지 마라. JSON 배열만 출력: [{"i":번호,"l":"WARN|TRIG|REPORT|OTHER"}]

"""
PROMPT = """Label each English news headline with exactly one label.
WARN = Chinese government, China Coast Guard, PLA or Chinese foreign ministry officially warns, threatens or announces a FUTURE action against Philippine vessels/missions (e.g. "will take measures", new detention rules, "warns Manila")
TRIG = a Philippine resupply/patrol mission or deployment that is announced or underway (not yet a confrontation)
REPORT = a confrontation that already happened (water cannon, ramming, collision, boarding, blocking) or its aftermath
OTHER = anything else (analysis, diplomacy without warning, unrelated)
Do not infer facts not in the headline. Output only a JSON array: [{"i":number,"l":"WARN|TRIG|REPORT|OTHER"}]

"""
TARGET = re.compile(r"China|Chinese|Beijing|coast guard|Coast Guard|shoal|Shoal|Philippine|Manila", re.I)
KEY = open(os.path.expanduser("~/.config/openrouter/key")).read().strip()

def ask(body):  # OpenRouter 경유 Claude (anthropic 키 파일은 형식 불일치, 10/10)
    o = subprocess.run(["curl", "-s", "--max-time", "120", "https://openrouter.ai/api/v1/chat/completions",
        "-H", "Authorization: Bearer " + KEY, "-H", "Content-Type: application/json", "-d",
        json.dumps({"model": "anthropic/claude-haiku-5.5", "max_tokens": 4000, "temperature": 0,
                    "messages": [{"role": "user", "content": body}]})], capture_output=True, text=True).stdout
    return json.loads(o)["choices"][0]["message"]["content"]

src, out = sys.argv[1], sys.argv[2]
first = {}
for r in csv.DictReader(open(src)):
    for t in r["sample_titles"].split(" || "):
        t = t.strip()
        if t and TARGET.search(t) and (t not in first or r["date"] < first[t]):
            first[t] = r["date"]
titles = sorted(first, key=lambda t: first[t])
labels = {}
for s in range(0, len(titles), 60):
    chunk = titles[s:s + 60]
    body = PROMPT + "\n".join(f"{i}. {t}" for i, t in enumerate(chunk))
    txt = ask(body)
    arr = json.loads(txt[txt.index("["): txt.rindex("]") + 1])
    for x in arr:
        labels[chunk[x["i"]]] = x["l"]
json.dump([{"date": first[t], "title": t, "label": labels.get(t, "MISSING")} for t in titles],
          open(out, "w"), ensure_ascii=False, indent=0)
print(len(titles), "titles;", {l: list(labels.values()).count(l) for l in set(labels.values())},
      "missing", sum(1 for t in titles if t not in labels))
