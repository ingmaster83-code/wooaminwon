# 우아민원 (wooaminwon.wooahouse.com)
세무서·건강보험·국민연금·고용복지플러스센터·근로복지공단·노동청·병무청·보훈청·출입국 공공데이터 892건을 시군구 관할로 묶은 정적 사이트(약 1,160페이지).
- 원본 CSV(공공데이터포털 15099881·15010814·15142232·15066368·15040715·15049970·15062525·15029545·15113992) → `python scripts/build_data.py <원본폴더> ../wooapost/data/posts.json` → `data/agencies.json`(커밋), `data/master_sg.json`(시군구 마스터, wooapost에서 추출)
- 관할구역 문자열 파서(`juris()`): 시도 접두어 lookahead, 도 아래 구는 시에 포함, 시도 전체 확장, 개편 전 지명 허용목록(LEGACY_OK), 건강보험 출장소는 이름에서 시군 추정
- 빌드: `python scripts/build_site.py` → `_site/`, 검증: `python scripts/check_site.py`
