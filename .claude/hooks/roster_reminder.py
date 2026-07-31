# -*- coding: utf-8 -*-
"""편성 리마인더 (UserPromptSubmit 훅) — 매 사용자 발언마다 본선에 주입.

목적: '본선이 편성을 잊고 직접 처리'하는 거버넌스 위반을 구조적으로 방지(2026-07-28 승격).
출력은 짧게 유지한다(매 턴 컨텍스트에 얹히므로).
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

print(
    "[편성 리마인더] 이 저장소는 공정별 에이전트 12팀 체제(.claude/agents/, 헌법 GOVERNANCE.md). "
    "대화가 공정(기획 planner-writer/각색 channel-adapter/디자인 visual-designer/영상 video-producer/"
    "음성 audio-producer/소재조달 asset-scout/소재제작 asset-creator/저작권 copyright-counsel/"
    "신기술 tech-scout/발행 publisher/분석 marketing-analyst/감사 auditor/보안 security-officer)에 해당하면 "
    "본선이 직접 처리하지 말고 해당 에이전트를 자동 호출하고, 산출물이 다음 공정을 부르면 연쇄 호출하라. "
    "유튜브 릴리스 종단(최종 검토→보완→업로드)은 발행 총감독 release-director 관할 — GOVERNANCE §8 상시 승인으로 "
    "품질 게이트 전 항목 통과 시 사용자 결재 없이 자동 발행(문제 시에만 사용자 호출). "
    "예외: 1분 내 잡무. 비용 발생·계정 생성·게시물 삭제·신규 플랫폼 첫 게시는 여전히 사용자 게이트. "
    "발행은 심사 대장(refs/publish-reviews.md) 승인 행 필수(훅 강제, §8 범위는 release-director가 직접 기록). "
    "공정 완료 시 상태판(refs/pipeline-status.md) 갱신. "
    "컨텍스트 80% 소진 시 인수인계서(메모리 session-handover.md + 저장소 refs/SESSION-HANDOVER.md) 갱신·커밋 후 세션 마무리 — GOVERNANCE §6-2. "
    "완주 의무(§6-3): 에이전트는 목표 완주 전에 멈추지 않는다 — 보고는 정지 사유가 아니며, 대기는 감시(마커 폴링)로 대체하고, "
    "정지는 오직 '스스로 해결 불가한 치명 문제 + 사용자 게이트'뿐. 에이전트를 띄우는 모든 지시서에 이 조항을 포함하라. "
    "사전 경고 게이트(§10, 2026-07-31): 공개 저장소에 새 유형 정보 반출·비가역 작업·가동 인프라 구조 변경·개인정보/자격증명 신규 취급은 "
    "실행 전 [사전 경고] 블록(노출 내용·최악 시나리오·대안)으로 사용자 승인 필수 — §8 상시 승인보다 우선, 애매하면 묻는 것이 기본값. "
    "저장소 구조(A안, 2026-07-31): 비공개 본진 = tech-history-ops(운영·코드·refs), 공개 = tech-history(발행 콘텐츠 posts/). 민감물은 공개 repo 커밋 금지."
)
sys.exit(0)
