"""국방 특허 제목 → 세부 기술 주제 (분류표를 먼저 고정한 뒤 전수 분류). OpenRouter Claude.
1) 표본 600건으로 분류표 40~60개 생성 → emerge_taxonomy.json (이후 수정 금지)
2) 전수 분류 → emerge_tags.jsonl  {"no", "tags":[...]} (최대 2개, 국방 무관 = "무관")
"""
import json, os, random, subprocess, sys
KEY = open(os.path.expanduser("~/.config/openrouter/key")).read().strip()
def ask(body, model="anthropic/claude-sonnet-5.5"):
    o = subprocess.run(["curl", "-s", "--max-time", "180", "https://openrouter.ai/api/v1/chat/completions", "-H", "Authorization: Bearer " + KEY,
        "-H", "Content-Type: application/json", "-d", json.dumps({"model": model, "max_tokens": 8000, "temperature": 0, "messages": [{"role": "user", "content": body}]})],
        capture_output=True, text=True).stdout
    d = json.loads(o); c = d["choices"][0]["message"].get("content")
    if not c: raise RuntimeError("empty content: " + str(d["choices"][0].get("finish_reason")))
    return c
R = [json.loads(l) for l in open("emerge_patents.jsonl")]
if not os.path.exists("emerge_taxonomy.json"):
    random.seed(7); smp = random.sample(R, 300)
    for att in range(3):
      try:
        t = ask("아래는 한국 국방 관련 특허(IPC F41 무기·F42 탄약) 제목 표본이다. 이 분야의 세부 기술 주제 분류표를 40~60개로 만들어라. "
            "각 주제는 짧은 한국어 명사구(예: '대드론 요격', '원격사격통제', '근접신관'), 서로 겹치지 않게, 너무 넓지도(예: '무기') 좁지도 않게. "
            "국방과 무관한 것(다트·게임·스포츠·완구 등)을 위한 '무관' 항목 포함. JSON 배열만 출력: [{\"topic\":\"...\",\"desc\":\"20자 이내\"}]\n\n" + "\n".join(x["title"] for x in smp)); break
      except Exception as e: print("retry", e)
    tax = json.loads(t[t.index("["): t.rindex("]") + 1]); json.dump(tax, open("emerge_taxonomy.json", "w"), ensure_ascii=False, indent=1)
    print("taxonomy", len(tax)); sys.exit(0)
tax = json.load(open("emerge_taxonomy.json")); names = [x["topic"] for x in tax]
done = set()
if os.path.exists("emerge_tags.jsonl"): done = {json.loads(l)["no"] for l in open("emerge_tags.jsonl")}
todo = [x for x in R if x["no"] not in done]; out = open("emerge_tags.jsonl", "a")
head = "분류표(이 이름만 쓴다):\n" + "\n".join(f"- {x['topic']}: {x['desc']}" for x in tax) + \
       "\n\n각 특허 제목에 분류표 주제를 1~2개 붙여라(가장 맞는 것 먼저). 국방 무관이면 '무관'. JSON 배열만: [{\"i\":번호,\"t\":[\"주제\"]}]\n\n"
for s in range(0, len(todo), 80):
    ch = todo[s:s + 80]
    for att in range(3):
        try:
            t = ask(head + "\n".join(f"{i}. {x['title']}" for i, x in enumerate(ch)), model="anthropic/claude-haiku-5.5")
            arr = json.loads(t[t.index("["): t.rindex("]") + 1]); break
        except Exception as e:
            print("retry", s, type(e).__name__, flush=True)
    else:
        continue
    for a in arr:
        tags = [x for x in a.get("t", []) if x in names][:2]
        out.write(json.dumps({"no": ch[a["i"]]["no"], "tags": tags or ["미분류"]}, ensure_ascii=False) + "\n")
    out.flush(); print("tagged", s + len(ch), "/", len(todo), flush=True)
print("done")
