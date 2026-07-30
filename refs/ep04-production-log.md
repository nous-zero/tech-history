# 4편(Mosaic·Netscape) 제작 진행 로그 — release-director 6대

> **다음 총감독은 이 파일 + `refs/pipeline-status.md` + 실제 파일 실측으로 인수한다**(GOVERNANCE §6-2).
> 전임 보고 무비판 승계 금지. 이 파일의 "완료" 표기도 산출물 파일을 직접 열어 확인한 뒤 신뢰할 것.

착수: 2026-07-30 / 총감독 6대
원천 원고: `posts/frontend/frontend-story-04-mosaic-netscape.md`
소재: 1993 Mosaic 공개 · 1994 넷스케이프 창업 · 1995-08-09 나스닥 상장(2시간 마비)

## 0. 인수 시점 실측 (2026-07-30, 6대)

| 항목 | 실측 |
|---|---|
| HEAD | `d9e9621` (로컬=origin/main, 작업트리 clean) |
| 4편 산출물 | **0건** — `find . -iname "*04*"` 결과 원고 md 1개 + 이미지 2개뿐. `video/scripts/04.json` 부재, `video/output/04_v2/` 부재 |
| 3편 선례 | 본편 `fQbG07NitUg` · 쇼츠 `IQpaKFhUGbM`·`VITgaxdZeMg` (발행 완료) |

## 1. 공정 진행표 (완료마다 즉시 갱신)

| # | 공정 | 담당 | 상태 | 산출물 경로 | 근거 |
|---|---|---|---|---|---|
| 1 | 영상 대본 04.json | planner-writer | ⏳ | `video/scripts/04.json` | |
| 2 | 소재 조달·대장 등록 | asset-scout | ⏳ | `video/output/assets/ep04_*` + `refs/asset-ledger.md` | |
| 3 | BGM 조달(선행①) | audio-producer | ⏳ | `video/output/assets/bgm/` | |
| 4 | 법무 1차(소재·BGM) | copyright-counsel | ⏳ | `refs/legal-review-ep04.md` | |
| 5 | 캐글 음성 생산 | audio-producer | ⏳ | `video/output/04_v2/audio/` | |
| 6 | STT 전수 검수 | audio-producer | ⏳ | `refs/audio-qc-ep04.md` | |
| 7 | 본편 1080p 렌더 | video-producer | ⏳ | `video/output/04_v2/episode.mp4` | |
| 8 | 쇼츠 2종 | video-producer | ⏳ | `video/output/04_v2/shorts_A.mp4`·`shorts_B.mp4` | |
| 9 | 썸네일 | visual-designer | ⏳ | `video/output/04_v2/thumb*` | |
| 10 | 메타·SEO | channel-adapter | ⏳ | `video/output/04_v2/youtube_meta.txt` | |
| 11 | 법무 최종 심사 | copyright-counsel | ⏳ | `refs/legal-review-ep04.md` | |
| 12 | 스펙 실측 | 총감독 | ⏳ | `video/verify_output_spec.py 04` | |
| 13 | 발행 전 감사 | auditor | ⏳ | `refs/audit-reports/` | |
| 14 | 승인 행 기록 | 총감독 | ⏳ | `refs/publish-reviews.md` | |
| 15 | 업로드·§8 공개 | 총감독 | ⏳ | `refs/youtube-publish-log.md` | |
| 16 | 고정댓글·역링크(선행⑥) | 총감독 | ⏳ | | |

## 2. 선행 과업 6건 (4편 병행 — 원천: `refs/pipeline-status.md` "4편 이월 과업")

| # | 과업 | 담당 | 상태 |
|---|---|---|---|
| ① | 본편 BGM 도입(4편부터 필수) | audio-producer→counsel | ⏳ |
| ② | 법무 캡션 20자 상한을 조립기 문법에 강제 | video-producer | ⏳ |
| ③ | 전 구간 보호영역 등록(현재 애니메이션 0~140 구간 등록 구역 0개) | video-producer | ⏳ |
| ④ | 쇼츠에 보호영역 이식(`build_shorts.py`에 기능 자체 없음) | video-producer | ⏳ |
| ⑤ | 시리즈 재생목록 "기술의 역사" 생성 + 1~3편 편성 | 총감독 | ⏳ **사용자 게이트 판단 보류** — 채널 구조 변경 소지, 발행 후 본선 경유 확인 |
| ⑥ | 1·2·3편 설명란에 4편 역링크 | 총감독 | ⏳ (4편 URL 확정 후) |

## 3. 결정·실측 기록 (세션 소멸 대비 — 여기에 누적)

- (2026-07-30 6대) 착수. 위 표가 유일한 진행 원천.
- (2026-07-30 6대) **1차 병렬 착수 3건**: planner-writer(대본 04.json + 소재 요구서) / audio-producer(BGM 도입 ①) / video-producer(조립기 안전장치 ②③④). 세 과업은 서로 독립이며 `build_v2.py`만 공유 → 양측에 "편집 직전 재Read + 커밋 전 status 확인" 지시함.
- (2026-07-30 6대 실측) **`video/output/`은 통째로 `.gitignore` 대상**(`git ls-files video/output/03_v2/` = 0건). 즉 **영상·음성·메타 산출물은 저장소에 남지 않는다** — 세션이 바뀌어도 파일은 로컬 디스크에 남지만, 다른 PC·클라우드 세션은 인수 불가. 인수의 근거는 이 로그 + 로컬 파일 실측이다.
- (2026-07-30 6대 실측) **에피소드마다 Manim 클래스를 손으로 쓴다** — `build_v2.py:640 Episode01`(552행) / `1193 Episode02`(613행) / `1807 Episode03`(860행), 등록부는 `build_v2.py:2668 episodes = {"01":…,"02":…,"03":…}`. 따라서 **4편은 `Episode04` 클래스 신규 작성(약 800행)이 최대 작업 덩어리**이며, 이것이 렌더 전 최장 공정이다.
- (2026-07-30 6대 실측) **애니메이션 타이밍은 음성 wav 길이에서 나온다**(`build_v2.py:133 load_timed_segments` → `video/output/04_v2/audio/segNNN.wav`를 읽어 `TIMED` 구성). 그래서 **음성이 없으면 Episode04를 실렌더로 검증할 수 없다** → 임계 경로는 `대본 → 캐글 음성 → Episode04 작성 → 렌더`. 소재 조달·썸네일·메타는 이 경로와 병렬 가능.
- (2026-07-30 6대 실측 — 선행⑤ 근거 재검증) **채널 재생목록: 커스텀 0개(단, 총계 2 미해명)**. `playlists.list`를 `mine:true`와 `channelId` 두 경로로 각각 조회한 결과 **둘 다 `items: []`이면서 `pageInfo.totalResults: 2`**. 즉 "3편까지 재생목록 0개"라는 감사 지적은 **표시 가능한 커스텀 재생목록 기준으로는 유지**되지만, 총계 2의 정체는 **미확인**(시스템/자동생성 재생목록 추정 — 확인 필요, 추정으로 처리 금지). 조회 도구: `C:\Users\745ra\.claude\skills\youtube-uploader\scripts\list-playlists.js`(신설, 읽기 전용)
- (2026-07-30 6대 실측) 채널 `UCFDEkjffWuo6CxeOCThTjRA` nous-zero — 구독 4 · 조회 3,220 · **`statistics.videoCount`는 8인데 업로드 재생목록 실계수는 9**(1~3편 본편 3 + 쇼츠 6, 전부 public). 통계 지연/집계 제외 추정이나 **원인 미확인**. 도구: `list-uploads.js`(신설, 읽기 전용)
- (2026-07-30 6대 실측) 업로드 도구는 저장소 밖에 있다: `C:\Users\745ra\.claude\skills\youtube-uploader\scripts\`(`upload-ep03.js`·`publish-ep03.js`·`verify-ep03.js`·`check-links.js`·`fetch-published.js` + OAuth 토큰). 4편은 이 스크립트들을 ep04용으로 복제해 쓴다.

## 4. 환경 실측치 (반복 사고 방지 — 재확인 불요)

- PC 2코어(i5-7200U)/16GB → 본편 렌더 약 70분
- ffmpeg: `C:\Users\745ra\AppData\Local\Programs\Python\Python312\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe` (PATH 없음)
- 캐글 음성: `video/kaggle_gen.py`를 깃허브 raw로 수신 + `gen_config.json`. **Save & Run All(커밋 실행)이 세션 독립**
- 긴 렌더는 독립 프로세스 + **로그 파일 생성으로 시작 확인**(프로세스 띄움 ≠ 실행됨)
- 렌더 중단 시 `--from-anim/--upto-anim/--mux-only`로 재개(`max_files_cached=-1` 적용됨)
- 유튜브 댓글창은 ©·®·™를 삼킨다 → 댓글 본문 금지
- 라우드니스 규격 **-16 LUFS(±1)**
