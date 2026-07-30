# 발행 편성표 — 02 백엔드 (전 12편)

> 원칙: [02-backend.md](./02-backend.md)의 모든 항목을 압축 없이 스토리로 만든다.
> 한 편에 다 안 들어가면 편수를 늘린다(임의 압축 금지 — 2026-07-24 지시).
> 각 편 = 대화 장면 + 비유 실명 태그 + 검증된 현대 사례 1개 + 이미지 2~3장.
> 파일명 규칙: `backend-story-<2자리 편번호>-<주제>.md`.
> 본문은 별표(**) 없는 "그대로 복붙해 게시하는 버전"으로 작성(링크드인·X는 마크다운 미지원).
> 게시물 수정은 손 편집 금지(빈 줄 유실) — 삭제 후 자동 재게시가 표준.
> **초안·마스터 문서 문장을 영상 대본에 직접 복사 금지 — 반드시 스토리(대화체)→영상 JSON(구어체·TTS 발음 표기) 변환 공정을 거친다.**

| 편 | 제목 | 파일 | 현대 사례 (검증) | 이미지 | 상태 |
|---|---|---|---|---|---|
| 1 | 1993년 CGI — 방명록 하나 못 만들던 웹, 서버가 요리를 시작했다 | backend-story-01-cgi.md | 스페이스 잼 1996 사이트 현존 ✅ | 계획 2장 | 기획 |
| 2 | 1994년 쿠키 — 23세 루 몬툴리가 장바구니 때문에 발명한 웹의 기억 | backend-story-02-cookie.md | 구글 서드파티 쿠키 퇴출 철회(2024.7) ✅ | 계획 2장 | 기획 |
| 3 | 1995년 PHP — 이력서 조회수 세던 개인 도구가 웹의 74%를 접수했다 | backend-story-03-php.md | PHP 74.5%·WordPress 43.5% (W3Techs) ✅ | 계획 2장 | 기획 |
| 4 | 2004년 Ruby on Rails — 15분 블로그 데모가 낳은 트위터·깃허브·쇼피파이 | backend-story-04-rails.md | 쇼피파이 BFCM 2025 $146억 ✅ | 계획 2장 | 기획 |
| 5 | 2000년 REST — 박사논문 한 편이 API의 문법이 되다, 그리고 JSON | backend-story-05-rest-json.md | REST 사용률 93% (Postman 2025) ✅ | 계획 2장 | 기획 |
| 6 | 2005년 AJAX — 구글맵과 Gmail이 새로고침을 없앤 날 | backend-story-06-ajax.md | Gmail 1GB, 만우절 농담 오인(2004.4.1) ✅ | 계획 2장 | 기획 |
| 7 | 세션에서 JWT까지 — 링크드인 비밀번호 1억 1,700만 개가 깨진 이유 | backend-story-07-jwt-hashing.md | 링크드인 2012 유출, 72시간 내 90% 크랙 ✅ | 계획 2장 | 기획 |
| 8 | 1999년 C10K 문제 — 동시접속 1만 명과 Node.js의 웨이터 한 명 | backend-story-08-c10k-node.md | 페이팔 Node 전환: 응답 35% 단축(2013) ✅ | 계획 2장 | 기획 |
| 9 | 2022년 티켓마스터 마비 — 35억 요청이 가르쳐준 "서버를 키우지 말고 늘려라" | backend-story-09-scaling.md | 테일러 스위프트 티켓 대란·상원 청문회 ✅ | 계획 2장 | 기획 |
| 10 | 2014년 마이크로서비스 — 넷플릭스는 쪼갰고, 아마존은 다시 합쳐 90%를 아꼈다 | backend-story-10-microservices.md | 프라임 비디오 모놀리스 회귀(2023.3) ✅ | 계획 2장 | 기획 |
| 11 | 2014년 AWS Lambda — 서버 관리라는 일이 사라지기 시작했다, 그리고 GraphQL | backend-story-11-serverless-graphql.md | Lambda 월 150만+ 고객·수십조 요청 ✅ | 계획 2장 | 기획 |
| 12 | 2018년 FastAPI와 언어 전쟁 — Java·Go·Node·Python 중 뭘 배워야 하나 (완결) | backend-story-12-languages-fastapi.md | FastAPI 15.1%, Flask 첫 추월(SO 2025) ✅ | 계획 2장 | 기획 |

발행 일정: 01 프론트엔드 시리즈 완주(8/4 예정) 후 확정. 발행 주기·시각은 프론트엔드 실측 데이터(링크드인 골든타임 16:00) 승계 예정 — 시작 전 재검증(규칙 1-6). 게시 이력은 publish-log.md.

제목 검증(규칙 8 두 질문 — 검색어가 들어있나 + 클릭하고 싶나): 전 편에 고유명사(CGI·쿠키·PHP·Rails·REST·JSON·AJAX·JWT·C10K·Node.js·티켓마스터·마이크로서비스·Lambda·GraphQL·FastAPI)와 구체 숫자/사건(15분·1억 1,700만·1만 명·35억·90%·74% 등) 배치 완료. 추상 제목 0건.

## 사실 검증 기록 (규칙 1 — 전부 2026-07-30 검색·확인, 영어 쿼리 포함)

### 연대·인물·사건 (마스터 문서 근거)

- ✅ 쿠키: 1994.6 루 몬툴리(23세, 넷스케이프) 고안, 개발 동기는 고객사 MCI의 장바구니 앱, 1994.10.13 Mosaic Netscape 0.9beta부터 지원. 실서비스 최초 사용은 넷스케이프 사이트 재방문 확인용 — Guinness World Records·historyofinformation.com·Hidden Heroes(netguru)
- ✅ PHP: 1994년 라스무스 러도프 작성(이력서 열람 추적용), 1995.6.8 "Personal Home Page Tools" 공개 — php.net 공식 연혁·tutorialspoint
- ✅ Rails: 2004.7 오픈소스 공개(DHH). "15분 블로그" 데모는 2005년 브라질 FISL — Wikipedia·avohq.io·dev.to(맥락 일치 복수 출처)
- ✅ 트위터·깃허브·쇼피파이 초기 Rails 사용: 3사 모두 확인. 트위터는 이후 Scala/JVM 계열로 이전, 쇼피파이는 현재도 Rails — rootstack·nascenia·rails.github.io (주의: 일부 출처의 "트위터 2004 개발"은 오류 — 트위터 창립은 2006, 마스터 문서에는 연도 미기재로 처리)
- ✅ Spring 1.0: 2004.3.24 최종판 — spring.io 공식 블로그
- ✅ Django: 2005.7 공개(7.13 최초 공개 커밋, 7.21 릴리스) — djangoproject.com 20주년 타임라인·Wikipedia
- ✅ Laravel: 2011.6.9 첫 공개(테일러 오트웰) — Wikipedia·acquaintsoft
- ✅ REST: 로이 필딩 UC 어바인 박사논문 2000년 — roy.gbiv.com 원문·Wikipedia
- ✅ JSON: json.org 문서화 2002, RFC 4627 2006.7 — rfc-editor.org·build5nines
- ✅ AJAX: 2005.2 제시 제임스 가렛 "Ajax: A New Approach to Web Applications"(Adaptive Path)에서 명명, Google Maps·Google Suggest·Gmail 언급 — 에세이 원문 PDF·jessejamesgarrett.com "Ajax at 20"(2025.2.18)
- ✅ C10K: 1999년 댄 케걸 명명(kegel.com/c10k.html), cdrom.com 동시 1만 클라이언트 사례 인용 — kegel.com 원문·Wikipedia
- ✅ Node.js: 2009.11 JSConf EU 베를린(청중 150명) 라이언 달 발표, 콘퍼런스 최초 기립박수 — jsconf.eu 2009 공식 페이지·Sequoia Capital 인터뷰
- ✅ Express.js: 2010.5.22 첫 공개(TJ 홀로웨이척) — Wikipedia·Medium(복수 일치)
- ✅ Servlet 1.0: 1997(Sun) / JSP 1.0: 1999 — encyclopedia.pub·d.umn.edu JSP History
- ✅ ASP: 1996.12, IIS 3.0 탑재 — Wikipedia "Active Server Pages"
- ✅ 마이크로서비스 명명: 파울러&루이스 "Microservices" 2014.3.25 게재 — martinfowler.com·notes.davidkopp.de(서지)
- ✅ AWS Lambda: 2014.11.13 re:Invent 발표, GA는 2015 — hidekazu-konishi.com AWS 타임라인·Forbes
- ✅ GraphQL: 2012 페이스북 사내 개발, 2015 오픈소스(스펙 공개 2015.9.14) — engineering.fb.com·graphql.org
- ✅ JWT: RFC 7519, 2015.5 발행 — rfc-editor.org
- ✅ FastAPI: 2018.12 첫 공개(0.1.0 2018.12.8, 세바스티안 라미레스) — Wikipedia·Sequoia Capital
- ⚠️ 베조스 API 명령(2002경): 스티브 예기 2011년 회고("Google Platforms Rant")가 유일 근거 — 1차 사료 아님. 마스터 문서·스토리에 "회고 기반" 명기 의무

### 현대 사례 (편별 배정분)

- ✅ 1편 스페이스 잼: 1996년 원본 사이트가 spacejam.com/1996/ 경로에 현존(워너브라더스 유지, 2021년 신작 개봉 때도 보존) — Web Design Museum·Internet Archive 블로그(2021.4)
- ✅ 2편 쿠키 철회: 구글, 2024.7 크롬 서드파티 쿠키 퇴출 계획 공식 철회(2020 선언 후 4년 만) — Digital Commerce 360(2024.7.24)·Privacy Sandbox 블로그
- ✅ 3편 PHP 점유율: 서버사이드 언어가 확인되는 웹사이트의 74.5%가 PHP, WordPress는 전체 웹의 43.5% — W3Techs(2025~2026 조사, w3techs.com 원페이지 확인)
- ✅ 4편 쇼피파이: BFCM 2025 주말 매출 $146억(전년 대비 +27%), 피크 분당 $510만 — Shopify 공식 보도자료(shopify.com/news/bfcm-data-2025)
- ✅ 5편 REST 점유율: API의 93%가 REST(GraphQL 33%·WebSocket 35% 병행) — Postman State of the API 2025
- ✅ 6편 Gmail: 2004.4.1 출시, 무료 1GB(당시 핫메일 2MB·야후 4MB) — 만우절 발표라 대중·언론이 농담으로 오인 — TIME 10주년 기사·NPR(2024.4.1)·PBS
- ✅ 7편 링크드인: 2012 유출이 2016.5에 1억 1,700만 건으로 확대 확인, SHA-1 무염(salt 없음) 저장, 72시간 내 90% 크랙 — Krebs on Security(2016.5)·TechCrunch·arXiv:1703.06586
- ✅ 8편 페이팔: 2013 계정 개요 페이지를 Java→Node.js 재작성 — 응답 시간 35% 단축, 코드 33%·파일 40% 감소, 초당 요청 2배(자체 측정) — PayPal 기술 블로그 "Node.js at PayPal"·High Scalability(2013.12)
- ✅ 9편 티켓마스터: 2022.11.15 테일러 스위프트 Eras Tour 발매에서 35억 건 요청(봇·스캘퍼 포함, 사측 주장 수치)으로 마비, 단일 아티스트 일일 판매 기록 240만 장, 2023.1 상원 법사위 청문회 — Wikipedia(Taylor Swift–Ticketmaster controversy)·PBS·NPR
- ✅ 10편 프라임 비디오: 2023.3 스트리밍 품질 모니터링(VQA) 서비스를 마이크로서비스→모놀리스 전환, 인프라 비용 90%+ 절감. **전체 플랫폼이 아니라 한 서비스 한정** — 이 한정을 스토리에 반드시 명기 — Prime Video Tech Blog·The Stack·devclass(2023.5)
- ✅ 11편 Lambda 규모: 월 150만+ 고객, 월 수십조 건 요청 처리(출시 10년 시점) — Forbes "A Decade Of AWS Lambda"(2025.2)
- ✅ 12편 FastAPI: Stack Overflow 2025 설문 사용률 15.1%, Python 웹 프레임워크 중 Flask 첫 추월 — survey.stackoverflow.co/2025

### [A] 학습 메모 대비 정정된 사실 오류 (원자료 검증 결과)

1. "본격 웹 프레임워크의 시작점은 Laravel" → **오류.** 시작점은 Ruby on Rails(2004.7), Laravel은 2011.6.9 — Rails가 7년 선행
2. "2005년 Python 등장" → **오류.** Python은 1991년생. 2005년은 Python 기반 웹 프레임워크 **Django**의 등장
3. "1994 — 두번째 도구 PHP" → **부정확.** 1994년은 작성 연도, 공개는 1995.6.8 (마스터 문서는 "1995 공개(1994 작성)"로 표기)
4. 트위터 초기 Rails의 "2004 개발" 표기(검색 결과 일부) → **오류.** 트위터 창립은 2006 — 연도 미기재로 회피 처리
