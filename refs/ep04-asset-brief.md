# 4편(Mosaic·Netscape) 소재 요구서 — planner-writer → asset-scout / asset-creator / copyright-counsel

작성: 2026-07-30 planner-writer · 대본 원본: `video/scripts/04.json`(15세그먼트, 1,641자, 예상 낭독 195.4초)
선례: 3편은 실사 사료 12종 + 파생 2종(`refs/asset-ledger.md` "3편" 절). 4편도 **같은 급(실사 12종 이상 + 파생/재현)** 을 목표로 한다.

## 0. 이 편의 저작권 지형 — 먼저 읽을 것 (사전 경고)

4편은 **1~3편과 지형이 완전히 다르다.** 1~3편의 주력 사료는 미 정부 저작물(PD)·CERN 약관·CC 사진이었지만,
4편의 "가장 보고 싶은 화면"은 전부 **살아있는 민간 기업의 저작물·상표**다.

| 위험 부류 | 구체 대상 | 권리자(추정) | 판정 |
|---|---|---|---|
| 🔴 **높음** | NCSA Mosaic 화면·아이콘·UI | 일리노이대(UIUC/NCSA) | 3편에서 이미 **배제 판정**(아래 §3 참조) |
| 🔴 **높음** | Netscape Navigator 화면·"N" 로고·throbber(회전 로고) | 현 Verizon/Yahoo 계열 승계[추정] | 상표+저작권 이중. 로고는 어떤 경우도 사용 금지 |
| 🔴 **높음** | Internet Explorer 1.0 화면·MS 로고 | Microsoft | 상표. 보증 오인 연출 절대 금지 |
| 🔴 **높음** | Mozilla 공룡 마스코트(1994, Dave Titus 작) | Mozilla Foundation | 캐릭터 저작권+상표. **사용 금지, 대체 연출로 갈 것** |
| 🔴 **높음** | 나스닥(NASDAQ) 로고·워드마크·MarketSite 전광판 | Nasdaq, Inc. | 상표. 게다가 MarketSite(타임스스퀘어)는 **2000년 개관 — 1995년 장면에 쓰면 시대 오류** |
| 🔴 **높음** | 1995년 신문 1면·잡지 표지(WSJ·Time·Newsweek 등) | 각 발행사 | 유료. 무료 대체 없음 → 배제 |
| 🟠 **보통** | 생존 인물 사진(마크 앤드리슨·짐 클라크·에릭 비나) | 촬영자 CC + 초상권 별개 | 2·3편 선례(초상권 4조건) 준용 → counsel 조건부 가 예상 |
| 🟠 **보통** | 앤드리슨의 1993-02-25 아이엠지 제안 메일 **원문 텍스트** | 작성자 | 짧은 발췌는 인용 항변 여지 → counsel 판정 필요 |
| 🟢 **낮음** | 수치·연대 데이터로 우리가 그리는 차트(주가·점유율·웹 성장) | 우리 | 사실 데이터에는 저작권 없음. **4편의 주력 화면으로 삼는다** |
| 🟢 **낮음** | 현대 스톡(Pexels/Pixabay/Unsplash), 1990년대 컴퓨터실 PD 사진 | 각 라이선스 | 3편과 동일 절차 |

> **총평(planner 판단)**: 4편은 "사료를 구해 오는 편"이 아니라 **"데이터 그래픽으로 짓는 편"** 이다.
> 주가 3점(28 → 71 → 74.75 → 58.25)과 점유율·웹 성장 곡선이 이 편의 시각적 클라이맥스이고,
> 이것들은 전부 저작권 위험 0이다. 실사 사료는 **인물·장소·시대 공기**에만 쓰고, 화면(UI)은 재현으로 간다.

---

## 1. 세그먼트별 소재 요구서

표기: **유형** = 실사(사진/영상) · 재현(우리가 만드는 그래픽) · 재사용(기존 대장 등록분)
**위험** = 🔴높음 / 🟠보통 / 🟢낮음 (라이선스·상표·초상 종합)

| id | scene | 필요한 화면 | 유형 | 검색 키워드(영어 포함) | 위험 | 대체안 |
|---|---|---|---|---|---|---|
| 0 | `nasdaq_halt` | 훅. "거래가 열리지 않는다"는 정지의 이미지 — 1990년대 증권 시세 단말·시세판, 멈춘 티커 | 실사 + 재현 | `stock ticker 1990s`, `trading floor 1995`, `stock quote terminal 1990s`, `NYSE trading floor` (PD-US-Gov 촬영분 우선), Commons `Category:Stock exchanges` | 🟠 (나스닥 로고·MarketSite는 🔴 금지) | 재현: 검은 화면에 호가만 깜빡이다 "거래 개시 지연" 자막. 로고 없이 만들 것 |
| 1 | `recap_free_web` | 3편 회수 — CERN 무료 공개 성명서 + 최초 웹사이트 화면 | **재사용** | 대장 `EP03-IMG-09`(`ep03_free_release_p1.jpg`), `EP03-IMG-08`(`ep03_first_website.png`) | 🟠 (© CERN 크레딧 승계 필수 / "재현 화면" 표기 승계) | 신규 조달 불요. 조건만 승계 확인 |
| 2 | `text_only_web` | 글자만 나오는 초기 웹 — 초록 텍스트 터미널, 라인모드 브라우저 | **재현** | (조달 대상 아님) 3편 미확보 항목 ②에 이미 **"재현 필요 플래그"** 로 남아 있음 | 🟢 (자체 제작) | 실사 보조: `1990s computer lab`, `VT100 terminal`, `monochrome CRT monitor` (Commons/Pexels) |
| 3 | `ncsa_parttimer` | ①일리노이대 캠퍼스/NCSA 건물 ②1990년대 대학 전산실(알바생 자리) | 실사 | Commons 실측 후보: `New NCSA Building UIUC by Ragib.jpg`(**주의: 2007년 신축 — 1993년 장면엔 시대 오류**), `Beckman Institute UIUC`(1993년 당시 NCSA 입주처 — 확인 요), `University of Illinois Urbana Champaign quad`, `Altgeld Hall`; 전산실은 `computer lab 1990s`, `university computer lab 1993` | 🟠 (CC BY-SA면 TASL 표기) | 건물 확보 실패 시 → 캠퍼스 전경 + 전산실 조합. **급여 명세는 실물 없음 → "시간당 6달러 85센트" 자막 그래픽으로 처리** |
| 4 | `img_tag_mail` | 1993-02-25 www-talk 메일 "proposed new tag: IMG" | **재현**(우선) / 실사(조건부) | 원문 소재지: `1997.webhistory.org/www.lists/www-talk.1993q1/0182.html` (아카이브 미러) — **캡처 전 counsel 인용 판정 필수** | 🟠→🔴 | 재현: 당대 메일 클라이언트/터미널 룩으로 **제목줄과 한 문장만** 재현 + "재현 화면" 자막. 원문 전문 노출 금지 |
| 5 | `mosaic_release` | **모자이크 실제 화면** (이 편의 최대 난관) | 실사 불가 추정 → 재현 | ①counsel에게 **인용(공표저작물의 인용) 판정** 의뢰 ②UIUC/NCSA에 **교육·보도용 스크린샷 허용 방침이 있는지 실측**(`NCSA Mosaic license`, `NCSA Open Source License`, `distributedmuseum.illinois.edu/exhibit/mosaic/` 이용약관) ③실패 시 asset-creator 재현 | 🔴 | 재현: 회색 모티프 창틀 + 글·그림 나란한 문서 레이아웃(모자이크 UI 도안 복제 금지, 2편 배지 선례 절차 = 자체 레이아웃 + "재현 화면" 표기) |
| 6 | `explosion` | 웹 폭증 — 1993~1995 웹 서버/호스트 수 급증 곡선 | **재현(데이터 차트)** | 데이터 출처 후보(수치만 인용, 도표 복제 금지): Matthew Gray "Web Growth Summary", ISC Internet Domain Survey 호스트 수. **scout는 수치와 출처 URL만 가져올 것** | 🟢 | 실사 보조: `1990s office computers`, `crowd using computers 1990s` (Pexels/Commons) |
| 7 | `clark_email` | ①짐 클라크 인물 ②실리콘 그래픽스(SGI) — 워크스테이션 실물이 안전 ③이메일 첫 줄 | 실사 + 재현 | Commons: `James H. Clark`, `Jim Clark Netscape`; SGI는 **로고 대신 하드웨어** → `SGI Indigo`, `Silicon Graphics Onyx`, `SGI workstation` | 🟠 (인물=초상권 4조건 / SGI 로고는 🔴 회피) | 인물 확보 실패 시 → SGI 워크스테이션 + 재현 메일 화면("저를 모르시겠지만…" 한 줄, 한글 자막) |
| 8 | `rewrite_mozilla` | "코드를 한 줄도 못 쓴다 → 처음부터 다시" | **재현** | (조달 대상 아님) — **모질라 공룡 마스코트 절대 금지**, 넷스케이프 "N" 로고 절대 금지 | 🟢 | 재현 연출: 빈 편집기 화면에 커서만 깜빡임 / 코드가 지워졌다 다시 채워지는 모션. 실사 보조 `1990s startup office`, `programmer 1990s` |
| 9 | `netscape_wins` | 1995년 브라우저 점유율 — 넷스케이프 압도 | **재현(데이터 차트)** | 대본이 "조사마다 다르지만 80퍼센트 안팎"이라고 이미 헤지했으므로 **차트에도 "조사기관별 상이" 캡션 필수**. scout는 독립 출처 2건의 수치 범위를 가져올 것 | 🟢 | 넷스케이프 실제 화면은 🔴 → seg5와 같은 재현 원칙 |
| 10 | `ipo_day` | 1995-08-09 상장일 — 주문 폭주 / 개시 지연 | 실사 + 재현 | `1995 stock market`, `trading desk 1995`, `telephone trading floor`; **1995년 8월 9일 당일 사진은 사실상 유료(Getty/AP) → 추적 금지(시간 낭비)** | 🟠 | 재현 주력: "공모가 한 주에 28달러" 카드 + 주문 폭주 시각화(막대가 한쪽으로만 쌓임) |
| 11 | `ipo_numbers` | **이 편의 클라이맥스** — 주가 그래프: 28 → 71 → 최고 74.75 → 종가 58.25 (단위 달러) | **재현(데이터 차트)** | 수치는 대본에 확정(NPR·Motley Fool 교차검증 완료). scout 조달 불요 — **visual-designer/video-producer 발주 항목** | 🟢 | 없음(필수 자체 제작). 시가총액 "약 30억 달러" 보조 자막 |
| 12 | `dotcom_trigger` | ①닷컴 열풍(1995~2000 나스닥 종합지수 곡선) ②오늘의 AI 투자 열기 | 재현(차트) + 실사(스톡) | 지수 데이터는 수치만 인용. AI 쪽은 Pexels `server rack`, `data center`, `stock chart on screen`, `AI conference` | 🟢 | 대본이 "이 비교는 제 관찰입니다"로 명시 → **화면에도 '작성자 견해' 자막 권장**(counsel 확인) |
| 13 | `law_giant` | 마이크로소프트의 등장 | 실사(건물) + 재현 | `Microsoft campus Redmond`, `Microsoft building sign` (Commons CC BY-SA). **IE 1.0 화면·MS 로고 클로즈업은 🔴 금지** | 🟠 | 대체: 거대한 그림자/실루엣 연출 + "1995년 8월, 인터넷 익스플로러" 자막. 로고 없이 |
| 14 | `next` | 5편 예고 — 열흘 만에 만든 언어 | **재현** | (조달 대상 아님) | 🟢 | 달력 10칸 카운트다운 + 코드 커서. 3편 아웃트로 카드 포맷 승계 |

---

## 2. 조달 우선순위 (scout 착수 순서)

1. **1순위(없으면 편이 안 굴러감)**: seg3 캠퍼스/전산실, seg7 짐 클라크 인물, seg13 마이크로소프트 건물, seg0/10 1990년대 증권 시세 화면
2. **2순위(있으면 좋음)**: seg3 마크 앤드리슨 인물(Commons 실측 후보 `Marc Andreessen.jpg` 등 — 단 전부 2010년대 촬영이라 **1993년 장면에 쓰면 시대 불일치**. 회고 컷·아웃트로에만 배치 권장), seg7 SGI 워크스테이션, seg5 에릭 비나 인물
3. **3순위(수치만 조달)**: seg6 웹 성장 수치, seg9 점유율 수치 범위(독립 2출처), seg12 나스닥 지수 데이터
4. **counsel 선행 판정 대기**: seg5 모자이크 화면, seg4 메일 원문 — **판정 나오기 전에는 파일을 내려받지도 말 것**

## 3. 3편에서 이월된 미해결 건 (asset-ledger 하단 "3편 미확보·배제")

> 원문: "**NCSA Mosaic 스크린샷**(scene 14, 4편 재사용 예정) — Commons `NCSA_Mosaic_Browser_Screenshot.png`는 CC0 태그이나 업로더(스크린샷 촬영자)는 자기 권리만 포기 가능하고 화면 속 Mosaic UI 저작권(일리노이대/NCSA)은 별개 → **CC0 태그 신뢰 불가로 배제**. 4편 제작 시 counsel 인용 판정 또는 asset-creator 재현으로 처리할 것."

→ **4편이 그 "제작 시"다.** 위 §1 seg5의 3단계 절차로 처리한다. 판정 결과는 `refs/legal-review-ep04.md`에 기록.

## 4. 음향 요구 (audio-producer 참고 — 선행과업 ① 본편 BGM 4편부터 필수)

- 전반(seg0~6): 호기심·발명. 3편보다 템포 조금 빠르게
- seg10~11(상장): **이 편 유일한 고조 구간** — 상승 후 종가 하락에서 살짝 꺾이는 진행
- seg13~14: 그림자가 드리우는 저음, 5편으로 넘어가는 미해결감
- 효과음 후보: 모뎀 접속음(당대 공기), 타자기/키보드 타건, 시세 단말 비프. **모두 대장 등록 후 사용**

## 5. 제작 규격 메모 (video-producer·visual-designer)

- 3편 실측 기준: 본편 194.47초 / 4편 대본 예상 낭독 195.4초 → 본편 약 205초 예상
- 법무 캡션 20자 상한(선행과업 ②)이 4편부터 조립기 문법에 강제될 예정 — **크레딧 문구를 20자 안에 설계**할 것
  (예: `© CERN`, `Geni, CC BY-SA 4.0`)
- 보호영역(선행과업 ③④) 전 구간 등록 필요 — 재현 차트 구간이 많아 자막 충돌 위험이 3편보다 크다

## 6. 확인한 것 / 확인 못 한 것 (이 요구서의 신뢰 범위)

**확인한 것**
- 대본 04.json의 15세그먼트 전부에 소재 요구를 배정했다(누락 0 — id 0~14 전수 대조)
- 3편 자산 대장의 "미확보·배제" 항목을 읽고 4편 이월 건(Mosaic 스크린샷)을 §3에 명시했다
- Commons에 `Marc Andreessen` 이미지 다수, `New NCSA Building UIUC by Ragib.jpg`가 **존재한다는 것**(검색 결과 실측)

**확인 못 한 것(scout가 실측할 것)**
- 위 Commons 파일들의 **개별 라이선스·해상도·초상권 태그** — 파일 페이지를 열어보지 않았다
- 1993년 당시 NCSA의 실제 입주 건물(Beckman Institute 추정) — **추정이며 미확인**
- 넷스케이프/모자이크 UI 권리의 현 승계자 — **[추정]** 표기이며 counsel이 확정할 것
- 나스닥 지수·웹 성장·점유율 수치의 인용 가능한 원출처 — scout가 URL과 함께 가져올 것
