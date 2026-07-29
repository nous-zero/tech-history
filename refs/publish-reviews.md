# 발행 전 심사 대장 (publish-reviews)

**⚠️ 기계 검사 범위 정정(2026-07-29 감사)**: 업로드 게이트 훅은 **링크드인 경로에만 걸려 있었다**(verify_upload_gate.py는 selected_api≠LinkedInCLIAPI면 즉시 통과). 유튜브 발행 3건은 기계 검사 없이 나갔다 — "이 대장을 기계 검사한다"는 기존 문구는 사실과 달랐으므로 정정한다.
**현재 상태**: 링크드인 = 훅 강제 ✅ / 유튜브 = 승인 행은 **절차상 필수**이나 기계 강제는 미구축(구축 예정: 승인 행 기록 시점 훅 + 산출물 스펙 실측 판정). 그때까지는 release-director·auditor의 절차 준수로 담보한다.
절차: copyright-counsel 심사(소재 라이선스·초상·AI 라벨·음원 플랫폼 적합성) → 승인 행 추가 → 발행. 판정 값: 승인 / 조건부(조치 완료 후 승인으로 변경) / 반려.

| 파일 | 채널 | 판정 | 일자 | 비고 |
|---|---|---|---|---|
| frontend-story-01-arpanet.md | LinkedIn | 승인 | 2026-07-28 | 소급 — 2026-07-24 전수 검증·기게시분 |
| frontend-story-02-tcpip.md | LinkedIn | 승인 | 2026-07-28 | 소급 — 기게시분(7/26) |
| frontend-story-03-web.md | LinkedIn | 승인 | 2026-07-28 | 소급 — 기게시분(7/27) |
| frontend-story-04-mosaic-netscape.md | LinkedIn | 승인 | 2026-07-28 | 소급 — 7/24 전수 검증분, 자체 제작 이미지만 사용 |
| frontend-story-05-javascript.md | LinkedIn | 승인 | 2026-07-28 | 소급 — 7/24 전수 검증분 |
| frontend-story-06-ie-css.md | LinkedIn | 승인 | 2026-07-28 | 소급 — 7/24 전수 검증분 |
| frontend-story-07-chrome-v8.md | LinkedIn | 승인 | 2026-07-28 | 소급 — 7/24 전수 검증분 |
| frontend-story-08-jquery-node.md | LinkedIn | 승인 | 2026-07-28 | 소급 — 7/24 전수 검증분 |
| frontend-story-09-npm-lego.md | LinkedIn | 승인 | 2026-07-28 | 소급 — 7/24 전수 검증분 |
| frontend-story-10-react.md | LinkedIn | 승인 | 2026-07-28 | 소급 — 7/24 전수 검증분 |
| frontend-story-11-spa-ssr.md | LinkedIn | 승인 | 2026-07-28 | 소급 — 7/24 전수 검증분 |
| 01-frontend.md | LinkedIn | 승인 | 2026-07-28 | 소급 — 시리즈 소개문 |
| video/output/02_v2/episode.mp4 (2편 본편) | YouTube @nous-zero | 승인 | 2026-07-28 | release-director 최종 검토(§8 상시 승인). 근거: ①counsel 심사 결과서(657a301 — 사료 9종 자산 대장·배지 재현 판정, 조건=재현 표기·TASL 크레딧 → 영상 내 "재현 이미지" 표기+설명란 TASL 전문 이행 확인) ②STT 전수 검수 audio_qc_report.md(사본 refs/audio-qc-ep02.md, 3차 재생산 포함 미해결 0) ③길이 불변식 171.97s=트랙 실측 일치, 1080p, 프레임 표본 6장 육안 ④SRT 갱신 대조 ⑤썸네일 공식 준수 ⑥메타 rule8(제목 키워드+숫자+훅) |
| video/output/02_v2/shorts_A.mp4 (배지 반전 28s) | YouTube Shorts | 승인 | 2026-07-28 | 최종 음성 반영 재렌더(22:05), 1080x1920, 27.8s, 프레임 검수. 설명·고정댓글에 본편 링크 의무(analyst 지적) |
| video/output/02_v2/shorts_B.mp4 (요약 40s) | YouTube Shorts | 승인 | 2026-07-28 | 최종 음성 반영 재렌더(22:19), 1080x1920, 40.1s, 프레임 검수. 동일 본편 링크 의무 |

> 소급 승인 사유: 위 항목은 2026-07-24 사례 전수 검증을 통과하고 자체 제작 이미지만 사용한 기존 발행 라인이다(가동 중인 매일 16시 자동 게시의 연속성 보장). **신규 콘텐츠(유튜브 본편·쇼츠 포함)는 소급 없이 건별 심사가 원칙.**
