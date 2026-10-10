# 🔥 봉수대 — 온톨로지를 활용한 북한의 말과 도발을 잇는 조기경보

D4D × EDTH Korean Defense Tech Hackathon 2026 · **T2 OSINT**

북한 당국의 공개 경고가 실제 도발로 이어졌는지 지난 10년 기록과 대조하고, 지금 나온 경고에 대해
"앞으로 무슨 일이 벌어질 수 있는지"를 확률·지켜볼 기간·과거 선례와 함께 답하는 OSINT 코파일럿.

| 2–7일 안에 북한 도발이 시작될 확률 (2016–2026, 도발 114건) | |
|---|---|
| 아무 날이나 | 17% |
| 북한 당국이 직접 '앞으로 하겠다'고 경고한 뒤 | **약 49%** (평소의 4.6배) |
| GDELT 152만 건을 기계로 세서 '위협'이 많던 날 뒤 | 약 22% (1.3배) |

→ 데이터 양이 아니라 **누가 한 말인지 가려내는 것**이 경보를 만든다.

## 실행
```bash
cd app
python3 server.py          # http://127.0.0.1:8790  (Python 3.10+, 표준 라이브러리 + curl)
```
- 예시 질문 버튼 = 사전 실행본(키 없이 동작)
- 실시간 질의: `export OPENROUTER_API_KEY=...` (Claude via OpenRouter)

## 구조
- `app/` — 제품: `agent.py`(에이전트·도구·3중 검증) · `server.py`(SSE 스트림) · `web/index.html`(작전 화면: 위성 지도·지식 그래프·근거 답) · `data/`(대조 결과)
- `pipeline/` — 수집·분류·대조 스크립트 (원래 작업 폴더 기준 상대 경로 — 결과물은 `app/data/`에 들어 있음)
- `deck/` — 발표 자료
- `app/README.md` — 방법·검증 이력 상세 · `app/demo-script.md` — 3분 시연 대본

## 데이터 출처
- 도발 정답지: [CSIS Beyond Parallel — Database: North Korean Provocations](https://beyondparallel.csis.org/database-north-korean-provocations/)
- 발사장 좌표: [CNS North Korea Missile Test Database (NTI)](https://www.nti.org/analysis/articles/cns-north-korea-missile-test-database/)
- 사건 데이터: [GDELT 1.0 Events](https://www.gdeltproject.org/) · 뉴스: Google News RSS · 유가: FRED DCOILBRENTEU
- 원본 파일은 저장소에 포함하지 않음(각 출처에서 받기)

## 한계
도발 10건 중 7건은 경고 없이 일어남 → 경보는 판정이 아니라 우선순위 · 표본이 작아 구간이 넓음 · 지도 위치 일부는 지역 수준
