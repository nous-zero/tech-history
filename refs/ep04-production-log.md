# 4편(Mosaic·Netscape) 제작 진행 로그 — release-director 6대

> **다음 총감독은 이 파일 + `refs/pipeline-status.md` + 실제 파일 실측으로 인수한다**(GOVERNANCE §6-2).
> 전임 보고 무비판 승계 금지. 이 파일의 "완료" 표기도 산출물 파일을 직접 열어 확인한 뒤 신뢰할 것.

착수: 2026-07-30 / 총감독 6대
원천 원고: `posts/frontend/frontend-story-04-mosaic-netscape.md`
소재: 1993 Mosaic 공개 · 1994 넷스케이프 창업 · 1995-08-09 나스닥 상장(주문 폭주로 **NSCP 한 종목의 첫 거래 약 2시간 지연** — "시장 마비" 아님, 사실 판정 `refs/ep04-fact-check-nasdaq.md`)

## 0. 인수 시점 실측 (2026-07-30, 6대)

| 항목 | 실측 |
|---|---|
| HEAD | `d9e9621` (로컬=origin/main, 작업트리 clean) |
| 4편 산출물 | **0건** — `find . -iname "*04*"` 결과 원고 md 1개 + 이미지 2개뿐. `video/scripts/04.json` 부재, `video/output/04_v2/` 부재 |
| 3편 선례 | 본편 `fQbG07NitUg` · 쇼츠 `IQpaKFhUGbM`·`VITgaxdZeMg` (발행 완료) |

## 1. 공정 진행표 (완료마다 즉시 갱신)

| # | 공정 | 담당 | 상태 | 산출물 경로 | 근거 |
|---|---|---|---|---|---|
| 1 | 영상 대본 04.json | planner-writer | ✅ | `video/scripts/04.json` | 15세그먼트·예상 낭독 195.4초(03편 wav 실측 환산). 커밋 87a25f8·93ab331. 마커 `video/scripts/_DONE_ep04_script.txt` |
| 1b | 소재 요구서 | planner-writer | ✅ | `refs/ep04-asset-brief.md` | 커밋 44526f8 |
| 1c | **사실 재검증: "나스닥 두 시간 멈췄다"** | planner-writer | ✅ | `refs/ep04-fact-check-nasdaq.md` | **과장 오류 확정**(영어 1차 사료 3출처 — 시장 전체 정지 서술 0건). 04.json title·seg0·seg10 정정(커밋 9e9ca81, scene `nasdaq_halt`→`nasdaq_delay`), 총감독이 파일 직접 재실측으로 정정 확인. 후속: 캐글 해제·메타 정정·썸네일 기준 갱신 지시 완료. **링크드인 기게시분 동일 과장은 사용자 결정 사안(본선 상신) — 4편 라인에서 소급 금지** |
| 2 | 소재 조달·대장 등록 | asset-scout | 🔄 | `video/output/assets/ep04_*` + `refs/asset-ledger.md` | **게이트 해제**(법무 판정 404dcd8). 착수 순서: ⓪BGM Wayback 스냅샷 2건(시급 — 후행 불가) → ①9부류 조달. 금지 9건·조건부 6건은 판정서 §1~3 |
| 3 | BGM 조달·믹싱(선행①) | audio-producer | ✅(법무 ⚠️) | `video/output/assets/bgm/` + `video/bgm.py` | 커밋 00438f3·0f638a7·d28eca0. **대장 등급 ⚠️ counsel 판정 대기 — 발행 게이트에 물림**. 별도로 **사용자 BGM 청음 1회** 필요(아래 5절) |
| 4 | 법무 **선행** 판정(소재·BGM) | copyright-counsel | ✅(추가 3건 포함) | `refs/legal-review-ep04.md` | 커밋 404dcd8·89e519e·c007162(§15). 3단: 즉시 9부류/조건부 6/금지 9. 로고-이름 분리. BGM 조건부 가. **추가 3건 확정**: ①AI 라디오 '아니요'(조건 3 — 재현 표기 프레임 계수·ref.wav 동일성·AI 얼굴 0건, 하나라도 깨지면 재회부) ②크레딧은 실사용에서 올려 적기(파일명+md5 양방향 대조 통과가 치환 자격) ③쇼츠 축약 크레딧 부류 나열 + 고정댓글 © 배제 변형 |
| 5 | 캐글 음성 생산 | audio-producer(별도 세션) | 🔄(**해제됨**) | `video/output/04_v2/audio/seg000~014.wav` | **임계 경로**. 1c 확정으로 Run All 해제(2026-07-30) — 04.json 재Read 후 정정본(1,657자)으로 생산. scene명 변경(nasdaq_delay) 반영 주의 |
| 6 | STT 전수 검수 | audio-producer(별도 세션) | 🔄 | `refs/audio-qc-ep04.md` | 고유명사·숫자 단어별 검수 행 의무 |
| 6b | **Episode04 클래스 신작(약 800행)** | video-producer | 🔄 | `video/build_v2.py` + 등록부 | **음성과 병렬 착수**(2026-07-30 — 작성은 지금, 실렌더 검증만 wav 마커 폴링 후). 미조달 소재는 자리표시 Rect+`_PENDING_ASSETS.txt`(임의 대체 금지). 더미 wav 렌더 금지(길이 불변식 오염). seg11 재현 차트가 클라이맥스 |
| 7 | 본편 1080p 렌더 | video-producer | ⏳ | `video/output/04_v2/episode.mp4` | 약 70분 |
| 8 | 쇼츠 2종 | video-producer | ⏳ | `video/output/04_v2/shorts_A.mp4`·`shorts_B.mp4` | |
| 9 | 썸네일 | visual-designer | ✅ | `video/output/04_v2/thumbnail.png`(주안 A)·`thumbnail_alt_b.png` + `refs/ep04-thumbnail-spec.md` | **총감독 육안 검수 통과**(2026-07-30 이미지 직접 열람): 도형 로고 0·실존 얼굴 0·실캡처 0·시장 정지 연출 0, NSCP는 자체 서체, "재현 화면" 표기 실재, 앰버 키워드+폴라로이드 차트(28→71→74.75→58.25)+1995 뱃지 공식 준수. 전량 자체 재현(외부 다운로드 0). A안 주력(구체 소수점 훅 $6.85). 잔여: 실기기 축소 확인·업로드 후 A/B(analyst) |
| 10 | 메타·SEO | channel-adapter | 🔄(**정정 중**) | `refs/ep04-youtube-meta.md`(사본, 커밋 1655455) + `video/output/04_v2/youtube_meta.txt` | 1차 완료(제목 77자·태그 18건·md5 일치)했으나 **1c 판정으로 제목·설명 첫 문단·쇼츠 B 제목 정정 재가동** — 새 04.json title 기준, 전수 grep + md5 재대조 지시 |
| 11 | 법무 최종 심사 | copyright-counsel | ⏳ | `refs/legal-review-ep04.md` | |
| 12 | 스펙 실측 | 총감독 | ⏳ | `video/verify_output_spec.py 04` | |
| 13 | 발행 전 감사 | auditor | ⏳ | `refs/audit-reports/` | |
| 14 | 승인 행 기록 | 총감독 | ⏳ | `refs/publish-reviews.md` | |
| 15 | 업로드·§8 공개 | 총감독 | ⏳ | `refs/youtube-publish-log.md` | |
| 16 | 고정댓글·역링크(선행⑥) | 총감독 | ⏳ | | |

## 2. 선행 과업 6건 (4편 병행 — 원천: `refs/pipeline-status.md` "4편 이월 과업")

| # | 과업 | 담당 | 상태 |
|---|---|---|---|
| ① | 본편 BGM 도입(4편부터 필수) | audio-producer→counsel | ✅ 집행 완료(법무 ⚠️ 잔여) — 아래 3절 실측 참조 |
| ② | 법무 캡션 20자 상한을 조립기 문법에 강제 | video-producer | ✅ 커밋 845a170. **빌드 실패(예외)** 채택 — 자동 연장은 길이 불변식(영상=Σwav)과 충돌해 실행 불가. 실질 규칙 "≤20자 + 3.5초 하한" 이중 게이트(입력 상한 + 출력 프레임 계수). 3편 33자는 사유 기록 레거시 면제, 4편에선 같은 문자열도 즉사(selftest 확인) |
| ③ | 전 구간 보호영역 등록 | video-producer | ✅ 3편 실측 3→**15개**, 커버리지 16/16(미달 시 스펙 FAIL). 자동 구역은 감사 전용(enforce=False — 화면 불변). 1~3편 권고 / **4편부터 차단**(`ZONE_STRICT_FROM_EP=4`). 3편 권고 23건 중 20건은 의도된 화면 문법 |
| ④ | 쇼츠에 보호영역 이식 | video-producer | ✅ Short03A 구역 4·커버리지 5/5. UI 가림 대역 카메라 상대 계산. **하단 20%·우측 12%는 추정치**(구글 공식 수치 부재 — PNG 템플릿뿐, 제3자 실측 보수 상한 채택, 재검증 대상) |
| ⑤ | 시리즈 재생목록 "기술의 역사" 생성 + 1~3편 편성 | 총감독 | ⏳ **사용자 결정: "4편 완료 후 재상정"**(2026-07-30, 상태판 기록) |
| ⑥ | 1·2·3편 설명란에 4편 역링크 | 총감독 | ✅ 발행 절차 편입 완료(4편 URL 확정 후 집행) |

**추가 완료 2건(counsel §15 회부분, 커밋 f10c87a)**: ⑦실사용 소재 자동 기록(`_render_manifest.json` — build_v2 파일 열기 후킹. 3편 실측: 실사용 9·대장 미발견 5·조달-미사용 14) ⑧재현 표기 프레임 전수 계수(verify_output_spec가 완성 mp4 계수 — 자기 코드 오차를 픽셀로 2회 적발, 최종 게이트는 프레임 계수). **동작 동일성: 재렌더 md5 본편 8/8·쇼츠 47/47 동일**(리팩터링 화면 영향 0을 바이트로 증명). 자가 검사 `video/selftest_guards.py` 신설.

## 2-2. 가동 중인 에이전트 세션 ID (GOVERNANCE §9-3 — 이름으로는 재연결 불가)

> §9-3: 총감독·팀장을 이어 쓸 때는 **새로 스폰하지 말고 스폰 시 받은 에이전트 ID로 SendMessage**한다.
> ID를 잃으면 새 세대를 스폰해야 하고, 그때마다 인수 비용이 든다. 그래서 여기에 적어 둔다.
> **총감독 자신의 재연결은 본선 경유**(본선이 총감독 ID를 보유). 자식→총감독 직접 SendMessage 경로는 없다(3-4절 실측) — 총감독 앞 보고는 전부 본선을 거친다.

| 역할 | 과업 | 에이전트 ID | 상태 |
|---|---|---|---|
| planner-writer | 대본 04.json + 소재 요구서 | `ae78b58dcaf053a63` | ✅ 완료 |
| audio-producer #1 | 선행① BGM 도입 | `a59f54dc7ceb4968c` | 🔄 |
| video-producer | 선행②③④+회부2건 조립기 안전장치 | `a6b228c9dc4be20fe` | ✅ 완료 — **Episode04 신작은 이 세션에 이어 지시 예정** |
| copyright-counsel | 4편 소재 **선행 법무 판정** | `a541df49978cf920f` | 🔄 |
| audio-producer #2 | 캐글 음성 생산 + STT 전수 검수 | `a6333c78931694396` | 🔄 |
| channel-adapter | 유튜브 메타·SEO 원고(제목 확정 → 썸네일 해금) | `a0c8df4598e1cbfb1` | ✅ 완료 |
| planner-writer(재가동) | 사실 재검증: 나스닥 2시간 쟁점 | `ae78b58dcaf053a63` | 🔄 |
| asset-scout | BGM Wayback 스냅샷(시급) + 소재 조달 | `af5bd9def977d2dd6` | 🔄 |
| visual-designer | 썸네일 주안+alt | `a82e140a278b5d2ae` | ✅ 완료 |
| marketing-analyst 하위 #1 | 브라우저 댓글 census + 채널 홈 레이아웃 실측 | `ac04fcbb5a20482f2` | 🔄 |
| marketing-analyst 하위 #2 | force-ssl 스코프·커뮤니티 탭 요건·재생목록 SEO 리서치 | `a0db61574764c6239` | 🔄 |

## 3. 결정·실측 기록 (세션 소멸 대비 — 여기에 누적)

- (2026-07-30 6대) 착수. 위 표가 유일한 진행 원천.
- (2026-07-30 6대) **1차 병렬 착수 3건**: planner-writer(대본 04.json + 소재 요구서) / audio-producer(BGM 도입 ①) / video-producer(조립기 안전장치 ②③④). 세 과업은 서로 독립이며 `build_v2.py`만 공유 → 양측에 "편집 직전 재Read + 커밋 전 status 확인" 지시함.
- (2026-07-30 6대 실측) **`video/output/`은 통째로 `.gitignore` 대상**(`git ls-files video/output/03_v2/` = 0건). 즉 **영상·음성·메타 산출물은 저장소에 남지 않는다** — 세션이 바뀌어도 파일은 로컬 디스크에 남지만, 다른 PC·클라우드 세션은 인수 불가. 인수의 근거는 이 로그 + 로컬 파일 실측이다.
- (2026-07-30 6대 실측) **에피소드마다 Manim 클래스를 손으로 쓴다** — `build_v2.py:640 Episode01`(552행) / `1193 Episode02`(613행) / `1807 Episode03`(860행), 등록부는 `build_v2.py:2668 episodes = {"01":…,"02":…,"03":…}`. 따라서 **4편은 `Episode04` 클래스 신규 작성(약 800행)이 최대 작업 덩어리**이며, 이것이 렌더 전 최장 공정이다.
- (2026-07-30 6대 실측) **애니메이션 타이밍은 음성 wav 길이에서 나온다**(`build_v2.py:133 load_timed_segments` → `video/output/04_v2/audio/segNNN.wav`를 읽어 `TIMED` 구성). 그래서 **음성이 없으면 Episode04를 실렌더로 검증할 수 없다** → 임계 경로는 `대본 → 캐글 음성 → Episode04 작성 → 렌더`. 소재 조달·썸네일·메타는 이 경로와 병렬 가능.
- (2026-07-30 6대 실측 — 선행⑤ 근거 재검증) **채널 재생목록: 커스텀 0개(단, 총계 2 미해명)**. `playlists.list`를 `mine:true`와 `channelId` 두 경로로 각각 조회한 결과 **둘 다 `items: []`이면서 `pageInfo.totalResults: 2`**. 즉 "3편까지 재생목록 0개"라는 감사 지적은 **표시 가능한 커스텀 재생목록 기준으로는 유지**되지만, 총계 2의 정체는 **미확인**(시스템/자동생성 재생목록 추정 — 확인 필요, 추정으로 처리 금지). 조회 도구: `C:\Users\745ra\.claude\skills\youtube-uploader\scripts\list-playlists.js`(신설, 읽기 전용)
- (2026-07-30 6대 실측) 채널 `UCFDEkjffWuo6CxeOCThTjRA` nous-zero — 구독 4 · 조회 3,220 · **`statistics.videoCount`는 8인데 업로드 재생목록 실계수는 9**(1~3편 본편 3 + 쇼츠 6, 전부 public). 통계 지연/집계 제외 추정이나 **원인 미확인**. 도구: `list-uploads.js`(신설, 읽기 전용)
- (2026-07-30 6대) **GOVERNANCE §9(컨텍스트 예산) 첫 적용 대상**. 총감독은 이 시점부터 **실행자가 아니라 지휘자**다 — 브라우저 조종·긴 로그 판독·대용량 통독을 직접 하지 않고 하위 에이전트에 위임해 요약만 받는다. 본선 실측: 역대 총감독 전사는 크래시 0건, 전부 컨텍스트 상한까지 태운 뒤의 정상 종료였고 그 누적의 73%가 브라우저 도구 결과였다. **주의: `PreToolUse` 유입 게이트는 설정 재적재 전까지 미발동** — 기계가 막아주지 않으므로 규율로 지킨다(`read_page`는 `max_chars`≤12000 + `filter=interactive`/`ref_id` 명시, 큰 파일은 Grep·offset/limit).
- (2026-07-30 6대) **4편은 1~3편과 저작권 지형이 다르다**(planner-writer 경고). Mosaic UI·Netscape 로고·IE 화면·모질라 마스코트·나스닥 로고가 전부 살아있는 민간 저작물·상표(위험 🔴). 1~3편은 정부·공공연구기관 사료라 퍼블릭도메인이 많았다. 처방: **주가·점유율 재현 차트를 주력 화면으로**(seg11이 시각적 클라이맥스, 저작권 0). **소재 조달은 법무 선행 판정 뒤로 차단**했고 seg5 모자이크 화면·seg4 아이엠지 메일 원문은 판정 전 다운로드 금지로 못 박았다.
- (2026-07-30 6대 실측) 업로드 도구는 저장소 밖에 있다: `C:\Users\745ra\.claude\skills\youtube-uploader\scripts\`(`upload-ep03.js`·`publish-ep03.js`·`verify-ep03.js`·`check-links.js`·`fetch-published.js` + OAuth 토큰). 4편은 이 스크립트들을 ep04용으로 복제해 쓴다.

## 3-2. 선행① BGM 집행 결과 (2026-07-30, audio-producer 보고 — 총감독 인수)

- 음원 **Pixabay #568180 "Corporate Explainer Video"** 209.52초·48kHz. 핵심 근거는 "Pixabay니까 안전"이 아니라 **트랙 단위 실측**: 346곡을 수집해 `hasYoutubeContentId` 필드를 트랙별로 재고 **false인 것만** 채택.
- 코드: 로직을 **`video/bgm.py`로 분리**하고 `build_v2.py`에는 호출 3곳만. video-producer와 동시 편집 중이라 **부분 스테이징으로 자기 30줄만 커밋**(상대 미커밋 변경 보존).
- 볼륨 실측(3편 트랙으로 종단 시험): 내레이션 -16.1 LUFS / BGM -35.1 → **차 19.0 LU**(기준 -18~-22 통과). 믹스 -16.1 LUFS · TP -4.7 dBTP. `verify_output_spec --file` **PASS(미달 0·경고 0)**. 시험 잔재는 03_v2에서 전량 삭제(3편 발행본에는 BGM 없음 — 게시본과 로컬 파일의 불일치 방지).
- 그 과정에서 실제로 잡은 결함: **모노를 스테레오로 복제하면 측정 라우드니스가 +3dB 올라 규격을 벗어난다** → 채널당 -3.01dB 보정으로 복귀. 부수 소득으로 샘플레이트·채널 축 경고가 통과로 전환.
- ACE-Step 미채택(가중치 8.28GB·노트북 0건 실측) → tech-scout 이월. **5편부터 자체 생성이 되면 Content ID 리스크가 원천 소멸**한다.
- **남은 것 2개**: ①counsel 판정(쟁점 A Standalone 재배포 금지의 사정거리 / 쟁점 B Content ID 정책 승격) — 회부 완료 ②**사용자 BGM 청음**(곡 분위기 적합성은 메타데이터로만 판단됨 — 사람 귀 미검증).

## 3-3. 발행 전 체크리스트 4편 증보분

기존 8항목(release-director 지시서)에 더해 4편부터 아래를 통과해야 §8 자동 집행이 성립한다.

9. **BGM 청음 확인** — 사용자 1회. 곡 분위기가 편의 톤과 맞는지는 기계가 판정할 수 없다(메타데이터로만 고른 상태). 3편 음성 청음과 동일 절차: 렌더 후 짧은 발췌를 만들어 본선 경유로 사용자에게 묻는다. **미확인 상태의 발행은 §8 범위 밖**(품질 의심 잔존 = "큰 문제" 후보).
10. **BGM 라이선스 이행 3종** — ①발행 직전 `hasYoutubeContentId` 재실측(신규 트랙이라 사후 등록 가능 — counsel 조건①) ②Wayback 스냅샷 2건 대장 기재 확인 ③쇼츠는 내레이션 트랙 동반 필수(정지이미지+음악만 금지).
11. **AI 라디오 '아니요' 조건 3종 실측**(counsel §15) — ①전 재현 컷 `(재현 화면)` 표기를 최종 렌더 프레임 계수로 검증 ②ref.wav가 3편과 동일 파일(대장 기재) ③AI 생성 실존 인물 얼굴 0건. 하나라도 깨지면 판정 무효 → counsel 재회부 후에만 진행.
12. **크레딧 양방향 전수 대조** — video-producer의 실사용 파일 목록(파일명+md5)과 크레딧 블록 대조: 미사용 행 삭제, 누락 발견 시 발행 차단. 이 대조를 통과해야 `[[CREDITS_PENDING]]` 치환 자격.

## 3-3b. auditor 발행 전 감사 의뢰 시 전달 항목 (누적)

1. **§5 모범 사례 기록 요청**: channel-adapter가 메타 자기 체크리스트에 금지 문자열 4종을 예시로 나열했다가 자기 검사에 걸려 제거 — "검사 문서가 검사에 걸리는" 자기충족 함정을 스스로 적발(본선 확인).
2. **커밋 경합 2건 참고**: ①visual-designer 파일 3건이 타 세션 커밋 `eac5a0a`에 쓸려 들어감(designer 1차 커밋이 PowerShell 5.1 따옴표 깨짐으로 실패한 사이 동시 세션이 커밋. 내용 무결 실측 확인, 히스토리 재작성 안 함) ②video-producer 과업④가 `5ca7cf0`(타 세션)에 혼입. **동일 유형 2회 — 본선이 §5 경로 지정 커밋 의무를 신설(커밋 5412e23)해 구조 처방 완료**, 이후 커밋은 준수 중. 감사 시 커밋 메시지-내용 불일치로 오인하지 말고, 재발 시 §4 누적 3회 임계로 훅 승격 검토.
3. **대본 내용 품질 독립 검증**: 총감독이 §9 예산 규율로 04.json 전문을 통독하지 않음 — planner-writer 교차검증 보고와 STT 검수가 1차 담보, 감사에서 독립 확인 요망.
4. **counsel 판정서(§15 포함) 전문 대조**: 총감독은 마커 요약+하류 팀 직접 Read로 운용 — 판정 조건의 이행 여부를 감사가 원문 기준으로 대조.

## 3-4. 하위 에이전트 운용 규율 (2026-07-30 실측 — §9-3의 두 번째 구멍)

**자식 에이전트에서 총감독으로 보내는 SendMessage 경로가 없다**(실측: BGM 팀 완료 보고가 총감독에 닿지 못하고 본선으로 감). 따라서 하위를 띄울 때 지시서에 다음을 반드시 명시한다:
- **결과를 마커 파일에 요약까지 써 넣을 것**(보고서 위치만 남기지 말고 판정·수치 요약을 마커 안에). 총감독은 파일로 인수한다.
- 보고는 본선 경유. 총감독에게 직접 말이 닿는다고 가정하지 말 것.

## 4. 환경 실측치 (반복 사고 방지 — 재확인 불요)

- PC 2코어(i5-7200U)/16GB → 본편 렌더 약 70분
- ffmpeg: `C:\Users\745ra\AppData\Local\Programs\Python\Python312\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe` (PATH 없음)
- 캐글 음성: `video/kaggle_gen.py`를 깃허브 raw로 수신 + `gen_config.json`. **Save & Run All(커밋 실행)이 세션 독립**
- 긴 렌더는 독립 프로세스 + **로그 파일 생성으로 시작 확인**(프로세스 띄움 ≠ 실행됨)
- 렌더 중단 시 `--from-anim/--upto-anim/--mux-only`로 재개(`max_files_cached=-1` 적용됨)
- 유튜브 댓글창은 ©·®·™를 삼킨다 → 댓글 본문 금지
- 라우드니스 규격 **-16 LUFS(±1)**
