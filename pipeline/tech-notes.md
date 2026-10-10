# 기술 봉수 — 방법·한계 (2026-10-10)

## 상태 (큰 소리로)
- **OpenAlex 미완료 2개 기술**: 레이저 무기(15콜 실패: 2020~2025 국가·기관 전부 0으로 들어가 있음 = 결측, 실측 0 아님) · 전자전(27콜 전부 실패, 논문 데이터 없음)
- 원인: OpenAlex 무키 요청은 **IP 공유 일일 예산**(group_by 1콜=10크레딧). 1차 실행 중 429 → 126회 + ConnectionError 1회. 리셋 = 매일 자정 UTC(09:00 KST)
- 완료 3개: 극초음속 · 드론 군집 · 대드론 (`openalex_failed_calls`=0)
- 재개: `python3 tech-build.py` (캐시 `tech-cache/` 재사용, 빠진 콜만 요청). 예산 소진 중엔 `OA_CACHE_ONLY=1`로 돌리면 결측 콜을 실패로 기록만 함
- 실패 목록 전부 → `tech-data.json` 의 `failures`

## OpenAlex 쿼리 (전부 `title.search`, 제목만)
| key | filter |
|---|---|
| hypersonic | `"hypersonic missile"|"hypersonic missiles"|"hypersonic weapon"|"hypersonic weapons"|"hypersonic glide"|"hypersonic vehicle"|"hypersonic vehicles"|scramjet` |
| drone_swarm | `"drone swarm"|"drone swarms"|"UAV swarm"|"UAV swarms"|"swarm of drones"|"swarm of UAVs"|"UAS swarm"` |
| counter_uas | `"counter-UAS"|"counter UAS"|"counter-drone"|"anti-drone"|"drone detection"|"UAV detection"|"drone interception"` |
| laser_weapon | `"laser weapon"|"laser weapons"|"high-energy laser"|"high energy laser"|"directed energy weapon"|"directed energy weapons"` |
| ew | `"electronic warfare"|"radar jamming"|"jamming suppression"|"anti-jamming"|"deceptive jamming"|"jamming signal"` |

- 연도별: `+publication_year:2014-2025`, `group_by=publication_year`
- 국가·기관: 연도마다 `group_by=authorships.countries` / `authorships.institutions.lineage` (per_page 200 = 그 해 상위 200개만). 상위권 합계는 정확, 꼬리 기관은 과소
- 국가 수 = 해당 국가 소속 저자가 1명 이상인 논문 수(공저 중복 계산)
- 한국 기관(`kr_inst`): `authorships.institutions.country_code:KR` 필터 후 기관 group_by → **한국 논문의 공저 외국기관도 섞임**(예: University of Houston). 상위기관 lineage에 "Government of the Republic of Korea"·부처 같은 상위 조직이 끼어 있음
- `hypersonic vehicle`·`scramjet`은 민수 공력·추진 연구도 포함 → 무기 전용 아님

## KIPRIS 쿼리
- 1차: `getWordSearch word=...` → **폐기**. 단어 분해 OR 검색으로 "레이저 무기" 101,344건, 전문 검색이라 노이즈. 결과 미사용(캐시엔 남음)
- 최종: `getAdvancedSearch inventionTitle=키워드` (발명명칭), 500행×최대 10쪽/키워드, 출원번호 중복 제거
- 키워드: 극초음속 / 드론 군집·군집 드론 / 대드론·드론 무력화·안티 드론·드론 방어 / 레이저 무기·레이저무기·고에너지 레이저 / 전자전·재밍
- 키워드는 사용자 지정에서 확장함(대드론 3건뿐이라 동의어 추가, 띄어쓰기 변형). 지정 원안: 극초음속·드론 군집·대드론/드론 무력화·레이저 무기·전자전/재밍
- 기관/개인 구분: 정규식(주식회사·연구원·대학·산학협력단·국방과학·Inc 등) 또는 7자 이상 → 기관. 규칙 기반이라 오분류 가능
- 출원인 이름 변경 미병합: LIG넥스원 → 엘아이지디펜스앤에어로스페이스, 한화디펜스 → 한화에어로스페이스 등 따로 셈
- 특허 출원 공개는 출원 후 18개월 → **2025·2026 출원 수는 구조적으로 과소**

## 색인 지연
- OpenAlex 2025 수치는 2026-10 시점 색인분. 2025·2026은 지연 가능 → 백테스트에 2021~2024 기준 적중을 병기

## 백테스트 규칙 (코드 작성 시 고정, 결과 본 뒤 변경 없음)
- 판정(2016~2020만): 2018~2020 연평균 ≥ 1.5 × 2016~2017 연평균 AND 2016~2020 합계 ≥ 10 → "뜨는" 판정. 2016~2017이 0이면 성장 무한대로 판정 포함(`early_growth`=null)
- 대상: 국가 = 2016~2020 합계 상위 15개국, 기관 = 상위 20개
- 채점: 2021~2025 연평균 > 2018~2020 연평균 → 적중
- 특허 출원인에도 같은 규칙 적용 → 2016~2020 합계 10건 이상 기관이 **0곳**이라 판정 대상 없음(표본 부족이 결과)
- 변경 기록: 없음. 단 2021~2024 병기는 규칙 작성 시점에 넣은 보조지표

## 결과 (완료 3개 기술)
| 기술 | 판정 | 적중 | 2021~24 기준 |
|---|---|---|---|
| 극초음속 | 10 | 4 | 4 |
| 드론 군집 | 16 | 13 | 12 |
| 대드론 | 3 | 2 | 2 |
| **합** | **29** | **19 (66%)** | 18 |

- 극초음속은 분야 전체가 정체(2016 313 → 2020 326)라 "1.5배" 판정이 소규모 국가 노이즈(AU·FR·IT·SE)를 잡음 → 미적중 다수
- 드론 군집은 분야 자체 급성장(2016 21 → 2025 878) → 거의 모든 판정 적중. **기저율 효과**라 규칙의 실력으로 보기 어려움
- 대비군(판정 안 된 엔티티의 후기 성장률)은 미산출 → 규칙이 무작위보다 나은지는 아직 모름

## 한국 관점 (완료 3개)
- 극초음속: 국가 5위(누적). KR 2016 3 → 2024 19편. CN은 같은 해 246, US 62. 상위 기관 전원 중국(서북공업대·국방과기대·하얼빈공대)
- 드론 군집: 국가 7위. KR 2020 10 → 2025 8편 정체. CN 2025 421편(2016 4편). 백테스트상 KR "뜨는" 판정은 적중(1.94배)
- 대드론: 국가 4위. 2016~2020 초기엔 KAIST가 기관 2위(9편) → 2021~2025엔 중국 기관이 상위 독식, KR 판정은 미적중(0.89배)
- 특허(국내): 전자전·재밍 546건 중 국방과학연구소 99 · LIG 62 · 한화시스템 25. 대드론 77건 중 삼정솔루션 7 · ETRI 4. 극초음속 26건뿐
