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
    "신기술 tech-scout/발행 publisher/분석 marketing-analyst/감사 auditor)에 해당하면 "
    "본선이 직접 처리하지 말고 해당 에이전트를 자동 호출하고, 산출물이 다음 공정을 부르면 연쇄 호출하라. "
    "예외: 1분 내 잡무. 외부 게시 실행·비용·계정 생성은 사용자 승인 게이트. "
    "발행은 심사 대장(refs/publish-reviews.md) 승인 행 필수(훅 강제). 공정 완료 시 상태판(refs/pipeline-status.md) 갱신."
)
sys.exit(0)
