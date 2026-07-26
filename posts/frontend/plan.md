# 발행 편성표 — 01 프론트엔드 (전 11편)

> 원칙: [01-frontend.md](./01-frontend.md)의 모든 항목을 압축 없이 스토리로 만든다.
> 한 편에 다 안 들어가면 편수를 늘린다(임의 압축 금지 — 2026-07-24 지시).
> 각 편 = 대화 장면 + 비유 실명 태그 + 검증된 현대 사례 1개 + 이미지 2~3장.
> 파일명 규칙: `frontend-story-<2자리 편번호>-<주제>.md`.
> 본문은 별표(**) 없는 "그대로 복붙해 게시하는 버전"으로 작성(링크드인·X는 마크다운 미지원).
> 게시물 수정은 손 편집 금지(빈 줄 유실) — 삭제 후 자동 재게시가 표준.
> 이미지는 [images/generate_images.py](./images/generate_images.py)로 일괄 생성(톤앤매너 코드 고정).

| 편 | 제목 | 파일 | 현대 사례 (검증) | 이미지 | 상태 |
|---|---|---|---|---|---|
| 1 | 인터넷의 첫마디는 "LO"였다 | frontend-story-01-arpanet.md | 통가 5주 고립 ✅ | 3장 ✅ | ✅ **게시됨 2026-07-24** |
| 2 | 하루 만에 언어를 갈아탄 날 | frontend-story-02-tcpip.md | IPv6 20년째 50.1% ✅ | 3장 ✅ | ✅ 게시됨 2026-07-26 |
| 3 | "모호하지만 흥미로움" | frontend-story-03-web.md | Vague but exciting 메모·1993 무료 개방 ✅ | 2장 ✅ | 완성 — 7/27 |
| 4 | 알바생이 연 그림의 시대 | frontend-story-04-mosaic-netscape.md | 넷스케이프 IPO $28→$71 ✅ | 2장 ✅ | 완성 — 7/28 |
| 5 | 10일 만에 만든 언어 | frontend-story-05-javascript.md | SO 2025 개발자 66% 사용 ✅ | 2장 ✅ | 완성 — 7/29 |
| 6 | 끼워팔기 전쟁 | frontend-story-06-ie-css.md | 2022 IE 종료 한국 혼란 ✅ | 2장 ✅ | 완성 — 7/30 |
| 7 | 속도의 전쟁 | frontend-story-07-chrome-v8.md | Chrome 65.23%(2026.5) ✅ | 2장 ✅ | 완성 — 7/31 |
| 8 | 통역사와 탈옥 | frontend-story-08-jquery-node.md | jQuery 전체 사이트 67.3% ✅ | 2장 ✅ | 완성 — 8/1 |
| 9 | 레고와 밀키트 | frontend-story-09-npm-lego.md | 2016 left-pad 사태 ✅ | 2장 ✅ | 완성 — 8/2 |
| 10 | 알아서 바뀌는 화면 | frontend-story-10-react.md | SO 2025 React 약 45% ✅ | 2장 ✅ | 완성 — 7/280 |
| 11 | 앱이 된 웹 (완결) | frontend-story-11-spa-ssr.md | OG 태그(ogp.me 표준) | 2장 ✅ | 완성 — 7/283 |

발행 주기: 매일 1편, 오전 10시 자동 게시(2026-07-27~08-04, 예약 작업 techstory-daily-linkedin). 게시 이력은 publish-log.md. 게시 직전 절차 = 본문 최종 확인 → 자동 게시(share 액션, 본문+대표 이미지 카드+깃허브 문서 링크) → 게시물 URL 확인.

## 사례 검증 기록 (규칙 1 — 전부 2026-07-24 검색·확인)

- ✅ 통가: 2022.1 분화로 해저케이블 절단, 2.22 복구(5주) — Al Jazeera·NPR·CBS
- ✅ 1983 flag day: 호스트 약 400대, "I survived the TCP transition, 1/1/83" 배지 500개(댄 린치 사비) — Internet Society·The Register
- ✅ IPv6: Google 측정 2026-03-28 최초 50.10% — Internet Society Pulse·APNIC
- ✅ "Vague but exciting": 1989.3 버너스리 제안서에 상사 마이크 센달이 기재 — CERN·CNBC·TIME
- ✅ CERN 웹 무료 개방: 1993.4.30 퍼블릭 도메인 — CERN
- ✅ 넷스케이프 IPO(1995.8.9): 공모 $28 → 개장 $71 → 최고 $74.75 → 종가 $58.25, 나스닥 개장 약 2시간 지연 — Washington Post·NPR·Motley Fool
- ✅ JS 사용률: Stack Overflow 2025 설문 66%, 2011년 이후 대부분 연도 1위(2013~14 SQL 제외)
- ✅ IE 종료: 2022.6.15 공식 종료, 국내 일부 공공·금융 IE모드 의존 보도 — 컴퓨터월드·디지털데일리
- ✅ Chrome 점유율: 65.23%(StatCounter 2026.5)
- ✅ jQuery: 전체 웹사이트의 67.3%(W3Techs, 2026.7.24 페이지 원문 확인)
- ✅ left-pad: 2016.3.22 삭제 → Babel·React 등 수천 프로젝트 실패, npm 강제 복구·정책 변경 — Wikipedia·The Register
- ✅ React: Stack Overflow 2025 전문 개발자 약 44.7~46.9%(출처별 상이 — "약 45%"로 표기)
- OG 태그: ogp.me 공개 표준(프로토콜 사실 — 별도 수치 주장 없음)
