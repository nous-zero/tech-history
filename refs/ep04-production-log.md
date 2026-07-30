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

## 4. 환경 실측치 (반복 사고 방지 — 재확인 불요)

- PC 2코어(i5-7200U)/16GB → 본편 렌더 약 70분
- ffmpeg: `C:\Users\745ra\AppData\Local\Programs\Python\Python312\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe` (PATH 없음)
- 캐글 음성: `video/kaggle_gen.py`를 깃허브 raw로 수신 + `gen_config.json`. **Save & Run All(커밋 실행)이 세션 독립**
- 긴 렌더는 독립 프로세스 + **로그 파일 생성으로 시작 확인**(프로세스 띄움 ≠ 실행됨)
- 렌더 중단 시 `--from-anim/--upto-anim/--mux-only`로 재개(`max_files_cached=-1` 적용됨)
- 유튜브 댓글창은 ©·®·™를 삼킨다 → 댓글 본문 금지
- 라우드니스 규격 **-16 LUFS(±1)**
