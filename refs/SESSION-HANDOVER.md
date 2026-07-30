# 세션 인수인계 (저장소 사본) — 2026-07-30 저녁

> 이 파일은 장기 메모리(`~/.claude/projects/.../memory/session-handover.md`)의 저장소 사본이다.
> 메모리에 접근할 수 없는 세션(클라우드 루틴·다른 PC)도 같은 지점에서 이어받도록 커밋해 둔다.
> **원천 상태판은 `refs/pipeline-status.md`** — 진행률은 항상 그 파일과 실제 파일을 실측해 확인할 것.
> 4편 제작·발행 전 과정의 상세 원천: **`refs/ep04-production-log.md`** (총감독 6대 기록).

## 완료: 유튜브 4편 발행 (2026-07-30, release-director 6대 — §8 자동 집행)

| 편 | 본편 | 쇼츠 |
|---|---|---|
| #01 | aPR3TsM9Rls | _2sLf6WfwvQ · nDBT7il7H9w |
| #02 | AHESMztkVhI | UtrV_wUskhw · iz-aU-1eN3E |
| #03 | fQbG07NitUg | IQpaKFhUGbM · VITgaxdZeMg |
| #04 | **DFwU4SxZGd8** | **DcYlMMYowMQ($28→$71) · d4ZAN6gpnKM(시급 $6.85)** |

4편: 발행 전 감사 조건부 가·차단 0(조건 5건 전건 이행) · 왕복 43 PASS/0 FAIL · 승인 3행(`refs/publish-reviews.md` 5695c70) · 발행 로그 `refs/youtube-publish-log.md` · **사용자 청음 2건 통과**(음성·BGM 모두 "괜찮습니다") · 1~3편 역링크 3건 완료(무손실 왕복).

## 다음 세션 첫 할 일

1. **고정댓글 고정(pin) 3건 — 사용자 클릭 6회 대기 중**(댓글 게시·대조는 완료, ⋮ 메뉴가 합성 클릭을 무시하는 환경 결함 실측 — 본선이 요청해 둠). 사용자가 했는지 브라우저로 확인만.
2. **push 미실행** — 로컬 커밋 다수(4편 전 과정). push는 본선 게이트, 본선 판단 대기.
3. **재생목록 "기술의 역사" 재상정** — 사용자 결정 "4편 완료 후 재상정"(지금이 그 시점). 업로드 스크립트 `--playlist` 옵션 실재 확인됨. 커스텀 재생목록 0개 실측(`list-playlists.js`).
4. **code-steward 착수** — 사용자 결정 "4편 발행 후"(지금이 그 시점).
5. 4편 성과 분석(marketing-analyst) · 태그 순서 실험 결과 실측(4편 게시본 태그가 원고 순서 보존인지).

## 4편에서 신설·확정된 제도 (전부 커밋됨 — 5편에 그대로 적용)

- **본편 BGM 상시**: `video/bgm.py` + Pixabay 트랙별 `hasYoutubeContentId` 실측 선별 + 발행 직전 재실측(`recheck-bgm-ep04.js` 방식) + RFC 3161 증빙(`refs/evidence/`)
- **법무 캡션 2단 게이트**: 20자+3.5초 기계 강제 + counsel 면제 등록부(`video/legal_caption_exceptions.json`, 완전 일치·counsel 커밋만)
- **보호영역 전 구간**(그림자류 비사진 패널 포함) + 쇼츠 이식 + **실사용 manifest 자동 기록**(`_render_manifest.json` — 크레딧 12항 양방향 대조는 최종 --full 매니페스트로만)
- **발행 전 체크리스트 12항 체제**(`refs/ep04-production-log.md` — BGM 청음·Content ID 재실측·AI 라디오 3조건·크레딧 양방향 등)
- **GOVERNANCE 증보**: §5 정책 차단 우회 금지·경로 지정 커밋 의무 / §6-3 완주 의무 / §9 컨텍스트 예산(총감독=지휘자, 브라우저·대용량은 위임)
- **캐글 TTS**: 04.json이 origin에 있으므로(db045ef) 5편은 raw 경로 복귀 가능. "자/초>9.8=꼬리 결손 예고" 지표 검수 편입 후보

## 5편 준비 메모 (감사·현장 발의 누적)

- 훅 승격 후보: 기획 A/B 배정↔렌더 라벨 기계 대조(4편에서 사람 눈이 잡음) · 파서-원고 섹션 계약 명시(신선도 사고 1건) · 유형 R3 누적 3회(3편 이월)
- 쇼츠 엔딩 본편 유도 문구 개선 · IMG-05 화면 사용 시 counsel 축약 선행(유예 중) · 48kHz 상향(TTS 출력 단계)
- 감사 적립 10건 처리: `refs/audit-reports/2026-07-30-ep04-prepublish-audit.md` + `refs/agent-audit-log.md`(사고 3호 = 정책 차단 JS 우회 위반 기록)

## 환경 실측 (반복 사고 방지 — 4편 갱신분 포함)

- PC 2코어/16GB → 본편 렌더 ~70분(480p 초벌 선행 표준). 파노라마 대형 이미지는 `_render_source` 축소 훅(9f57dde)
- ffmpeg: `C:\Users\745ra\AppData\Local\Programs\Python\Python312\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe`
- 유튜브: 댓글창 ©·®·™ 삼킴 / 고정(pin)은 API 없음+합성 클릭 무시(사용자 손) / **videos.update 직후 videos.list는 읽기 전파 지연 가능**(재조회로 판정 — 4편 실측) / 태그 정렬 주체 미확정(4편 게시본이 실험 대상)
- 라우드니스 -16 LUFS(±1) · BGM 차 -18~-22dB(4편 실측 19.0 LU)
- **하위 에이전트**: 자식→총감독 SendMessage 경로 없음(보고는 본선 경유, 인수는 마커 파일) / 지시서 필수 문구 3종 = 마커에 요약 기재·정책 차단 우회 금지·§6-3 완주 의무 / 총감독 재연결은 본선이 보유한 ID로 SendMessage(§9-3)

## 미결

push(본선 게이트) · 고정 3건(사용자) · 재생목록(재상정 시점 도래) · code-steward(착수 시점 도래) · 태그 정렬 실험 · 자막 SRT 업로드(`youtube.force-ssl` 재인증 판단) · 틱톡·릴스(계정)·네이버·티스토리(ToS) · 링크드인·X 소급 정정 잔여 확인
