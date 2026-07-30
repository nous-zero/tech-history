# -*- coding: utf-8 -*-
"""컨텍스트 예산계 (PostToolUse) — 보이지 않던 벽을 '남은 연료 계기판'으로 바꾼다.

배경(2026-07-30 전사 실측): 에이전트는 크래시로 죽지 않는다. 컨텍스트(기억할 수
있는 총량)를 다 태우고 그 자리에서 최종 보고를 하고 끝난다. 압축 이벤트는 0회였고
누적 토큰은 239K~411K. 문제는 **당사자가 소진 속도를 모른다**는 것 — 계기판이 없어
"갑자기 끝난 것처럼" 보였고, 그래서 매번 새 세대를 스폰해 파일로 인수인계했다.

이 훅은 도구 결과 바이트를 세션별로 누적해, 임계마다 당사자에게 직접 알린다.
  1단계 위임 권고 → 2단계 인계 준비 → 3단계 인계 후 종료.

바이트는 토큰의 '대리 지표'다(정확한 환산이 아님 — 실측상 16.0MB↔411K, 6.4MB↔384K로
비례하지 않는다). 임계는 이 저장소에서 실제 세대 교체가 일어난 구간(3.8~16.0MB)의
아래쪽에 보수적으로 잡았다.
"""
import json
import os
import sys

MB = 1024 * 1024
LEVELS = [
    (1.5 * MB, "1", "[컨텍스트 예산 40% 추정 소진] 지금부터 무거운 작업(브라우저 조종, "
                    "긴 로그 판독, 대용량 파일 통독)은 직접 하지 말고 하위 에이전트에 "
                    "위임해 '요약만' 받으세요. 그래야 이 세션이 목표까지 완주합니다."),
    (3.5 * MB, "2", "[컨텍스트 예산 70% 추정 소진] 지금 인계 파일을 갱신하세요 — 진행 상황·"
                    "실측치·다음 단계를 refs/ 아래 기록하고 커밋. 갱신 뒤 남은 작업을 계속하되, "
                    "새로 시작하는 무거운 공정은 반드시 위임하십시오."),
    (5.5 * MB, "3", "[컨텍스트 예산 임박] 곧 이 세션은 더 못 갑니다. ①인계 파일 최종 갱신·커밋 "
                    "②남은 목표를 하위 에이전트에 넘기거나 호출자에게 정확히 인계 "
                    "③'확인한 것 / 못 한 것'을 명시해 종료 보고. 새 작업을 시작하지 마세요."),
]


def state_path(base, key):
    d = os.path.join(base, ".claude", ".ctx-budget")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        return None
    safe = "".join(c for c in str(key) if c.isalnum() or c in "-_")[:64] or "unknown"
    return os.path.join(d, safe + ".json")


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    base = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    # 서브에이전트마다 별도 계량이 되도록, 있는 식별자 중 가장 좁은 것을 키로 쓴다.
    key = (data.get("agent_id") or data.get("subagent_id")
           or data.get("session_id") or "unknown")
    p = state_path(base, key)
    if not p:
        sys.exit(0)

    tool = data.get("tool_name") or "?"
    try:
        size = len(json.dumps(data.get("tool_response"), ensure_ascii=False))
    except Exception:
        size = 0

    st = {"bytes": 0, "calls": 0, "warned": [], "by_tool": {},
          "payload_keys": sorted(data.keys())}
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as fh:
                st.update(json.load(fh))
        except Exception:
            pass

    st["bytes"] = st.get("bytes", 0) + size
    st["calls"] = st.get("calls", 0) + 1
    st["by_tool"][tool] = st["by_tool"].get(tool, 0) + size
    st["payload_keys"] = sorted(data.keys())

    fired = None
    for threshold, tag, msg in LEVELS:
        if st["bytes"] >= threshold and tag not in st["warned"]:
            st["warned"].append(tag)
            fired = msg  # 여러 단계를 한 번에 넘었으면 가장 심각한 단계만 알린다

    try:
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False)
    except OSError:
        pass

    if not fired:
        sys.exit(0)

    top = sorted(st["by_tool"].items(), key=lambda kv: -kv[1])[:3]
    detail = " · ".join("%s %.1fMB" % (k.split("__")[-1], v / MB) for k, v in top)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.stdout.write(json.dumps({
        "suppressOutput": True,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "%s\n(누적 도구 결과 %.1fMB / 호출 %d회. 최대 소비: %s)"
                                 % (fired, st["bytes"] / MB, st["calls"], detail),
        }}, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
