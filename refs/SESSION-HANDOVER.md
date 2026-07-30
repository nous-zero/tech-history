# 세션 인수인계 (저장소 사본) — 2026-07-30 오전

> 이 파일은 장기 메모리(`~/.claude/projects/.../memory/session-handover.md`)의 저장소 사본이다.
> 메모리에 접근할 수 없는 세션(클라우드 루틴·다른 PC)도 같은 지점에서 이어받도록 커밋해 둔다.
> **원천 상태판은 `refs/pipeline-status.md`** — 진행률은 항상 그 파일과 실제 파일을 실측해 확인할 것.

## 다음 세션 첫 할 일 — 4편(Mosaic·Netscape) 재착수

**상태: 착수 지시했으나 세션 종료로 총감독 정지됨(산출물 없음 — 4편은 백지 상태에서 시작).**
다음 세션은 release-director를 다시 투입해 아래를 인계하라(이번 세션이 준 브리핑과 동일):
①선행 과제 6건(아래) 병행 ②제작 라인은 3편과 동일(대본→소재→캐글 음성→STT 검수→1080p+쇼츠→썸네일·메타→법무→스펙 검사→**발행 전 감사**→승인 행→업로드→§8 공개→고정댓글·로그).
원천: `posts/frontend/frontend-story-04-mosaic-netscape.md`(1993 Mosaic·1994 넷스케이프 창업·1995-08-09 나스닥 2시간 마비 상장).
**총감독 세션은 수명이 짧다** — 소멸하면 파일 실측으로 인수해 새 총감독 투입(3편에서 5대까지 교체).

선행 과제 6건을 병행 지시함 → 상세는 `refs/pipeline-status.md`의 "4편 이월 과업" 절:
법무 캡션 20자 상한 · 전 구간 보호영역 등록 · 쇼츠 보호영역 이식 · **본편 BGM 도입(4편부터 필수)** · 시리즈 재생목록 생성 · 구작 역링크.

## 완료: 유튜브 3편 발행 (2026-07-30)

| 편 | 본편 | 쇼츠 |
|---|---|---|
| #01 | aPR3TsM9Rls | _2sLf6WfwvQ · nDBT7il7H9w |
| #02 | AHESMztkVhI | UtrV_wUskhw · iz-aU-1eN3E |
| #03 | **fQbG07NitUg** | **IQpaKFhUGbM · VITgaxdZeMg** |

3편: 독립 왕복 검증 52 PASS/0 FAIL · 고정댓글 3건 · 승인 3행(`refs/publish-reviews.md`) · 로그 `refs/youtube-publish-log.md`.

## 제도 변화 (이번 세션 — 전부 커밋됨)

- **release-director**(유튜브 릴리스 종단 총괄, 크롬·코랩·캐글 운전) / **ops-analyst**(지연 진단·최적화 정찰) 신설
- **GOVERNANCE §8 상시 승인**: 게이트 전 항목 통과 시 공개까지 자동. 전제조건 = ①스펙 실측 통과 ②발행 전 auditor 감사. 제외 = 비용·계정·삭제·채널 설정·신규 플랫폼 첫 게시
- **§5 자기충족 검증 금지**(기대값은 독립 근거에서) · **완료 마커 파일 계약**(통지 대기 금지, 파일 실측 인수)
- 허용 목록 저장소 고정(`.claude/settings.json`), `cd &&` 복합 명령 금지
- 감사·진단 보고서: `refs/audit-reports/` · `refs/ops-reports/`

## 신설 기계 검사 (4편부터 자동)

- `video/verify_output_spec.py` — 해상도·fps·LUFS(-16±1)·TP·무음(설계분 차감)·BGM 존재·길이 불변식·프레임 이탈·보호영역. `--full` 렌더 끝에 자동 호출, 미달 exit 2
- `video/verify_manual_post.py` — 수동 게시(고정댓글) 자리표시자 게이트
- `build_v2.py`: `fit_frame`·`reserve_zone`·`avoid_zones`·`audit_layout`·`--layout-audit`·`--from-anim/--upto-anim/--mux-only`·`max_files_cached=-1`
- `build_shorts.py`: `keep_in`·`SafeText`·프레임 이탈 감사(**보호영역 미이식 — 4편 과업**)

## 사용자 결정

1·2편 게시물 유지(재게시·삭제 없음) · BGM은 4편부터 · 라우드니스 **-16 LUFS** · **code-steward는 4편 발행 후 착수**.

## 환경 실측 (반복 사고 방지)

- PC 2코어(i5-7200U)·16GB → 본편 렌더 70분. 클라우드 이관이 최대 개선책(검토 대기)
- ffmpeg: `C:\Users\745ra\AppData\Local\Programs\Python\Python312\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe`(PATH 없음)
- 캐글 음성: `video/kaggle_gen.py`를 깃허브 raw로 수신 + `gen_config.json`. **"Save & Run All(커밋 실행)"이 세션 독립** — 밤샘 작업은 이 모드로
- 긴 렌더는 독립 프로세스 + **로그 파일 생성으로 시작 확인**(프로세스 띄움 ≠ 실행됨)
- 유튜브 댓글창은 **©·®·™를 삼킨다** → 댓글에 쓰지 말 것

## 미결

4편 진행 · 태그 정렬 주체 미확인 · 48kHz 상향(TTS 출력 단계) · 고정댓글·자막 API(`youtube.force-ssl` 재인증 판단) · 유형 R3 누적 3회 훅 승격 · 틱톡·릴스(계정)·네이버·티스토리(ToS) · 대시보드 재게시(https://claude.ai/code/artifact/7cff8466-d173-430e-add0-e3fa6ddc2134)
