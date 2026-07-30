# -*- coding: utf-8 -*-
"""컨텍스트 유입 게이트 (PreToolUse) — 규칙 5의 기계 강제판.

에이전트 "세대 교체"의 실측 원인 1번: 한 번의 도구 호출이 컨텍스트(에이전트가
기억할 수 있는 총량)를 크게 먹는 것. 2026-07-30 전사 스캔 실측 —
  · release-director 16.0MB 중 브라우저 도구 11.7MB(73%)
  · audio-producer   8.8MB 중 computer 7.83MB(89%)
  · auditor          6.4MB 중 browser_batch 4.43MB(70%)
  · read_page 기본 반환 상한 = 50,000자 (스키마 실측)

이 훅은 '들어오기 전에' 상한을 건다.
  1) read_page (단독·browser_batch 내부 모두) → max_chars 를 상한으로 교정
  2) 대용량 파일 Read 에 limit 이 없으면 차단 (부분 읽기·Grep 유도)

출력 규약: PreToolUse 의 hookSpecificOutput
  · permissionDecision=deny → 차단, 이유가 모델에게 전달됨
  · updatedInput            → 입력을 교정해서 통과
"""
import json
import os
import sys

# read_page 반환 상한(문자). 명시하지 않은 호출(기본 50,000자)은 IMPLICIT_CAP 으로,
# 일부러 크게 요청한 호출도 HARD_CAP 을 넘지 못한다.
IMPLICIT_CAP = 12000
HARD_CAP = 20000

# limit 없는 Read 를 차단할 파일 크기(바이트)
READ_BLOCK_BYTES = 120000

# 크기 규칙에서 제외 — 이미지/영상/음성은 Read 방식이 다르다
MEDIA_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg",
             ".mp4", ".mov", ".mkv", ".webm", ".wav", ".mp3", ".m4a",
             ".pdf", ".ipynb", ".zip"}

PAGE_TOOLS = ("read_page",)


def out(payload):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.exit(0)


def clamp_page_input(inp):
    """read_page 입력의 max_chars 를 상한으로 교정. 바뀌었으면 True."""
    if not isinstance(inp, dict):
        return False
    cur = inp.get("max_chars")
    if cur is None:
        inp["max_chars"] = IMPLICIT_CAP
        return True
    try:
        cur = int(cur)
    except (TypeError, ValueError):
        inp["max_chars"] = IMPLICIT_CAP
        return True
    if cur > HARD_CAP:
        inp["max_chars"] = HARD_CAP
        return True
    return False


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool = data.get("tool_name") or ""
    ti = data.get("tool_input") or {}

    # ── 1) read_page 단독 호출 ────────────────────────────────────────────
    if tool.endswith(PAGE_TOOLS):
        new = dict(ti)
        if clamp_page_input(new):
            out({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason":
                    "[컨텍스트 게이트] read_page 반환량을 %d자로 제한했습니다. "
                    "더 필요하면 ref_id·depth·filter=interactive 로 범위를 좁혀 다시 부르세요."
                    % new.get("max_chars", IMPLICIT_CAP),
                "updatedInput": new}})
        sys.exit(0)

    # ── 2) browser_batch 안에 끼어 있는 read_page ────────────────────────
    if tool.endswith("browser_batch"):
        actions = ti.get("actions")
        if not isinstance(actions, list):
            sys.exit(0)
        changed = False
        new_actions = []
        for a in actions:
            if isinstance(a, dict) and str(a.get("name", "")).endswith(PAGE_TOOLS):
                a = dict(a)
                inp = dict(a.get("input") or {})
                if clamp_page_input(inp):
                    changed = True
                a["input"] = inp
            new_actions.append(a)
        if changed:
            new = dict(ti)
            new["actions"] = new_actions
            out({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason":
                    "[컨텍스트 게이트] 배치 안 read_page 반환량을 %d자로 제한했습니다." % IMPLICIT_CAP,
                "updatedInput": new}})
        sys.exit(0)

    # ── 3) limit 없는 대용량 Read ────────────────────────────────────────
    if tool == "Read":
        path = ti.get("file_path") or ""
        if ti.get("limit") or ti.get("pages"):
            sys.exit(0)
        ext = os.path.splitext(path)[1].lower()
        if ext in MEDIA_EXT:
            sys.exit(0)
        try:
            size = os.path.getsize(path)
        except OSError:
            sys.exit(0)
        if size > READ_BLOCK_BYTES:
            out({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason":
                    "[컨텍스트 게이트] %s 는 %.0fKB입니다. 통독하면 컨텍스트를 크게 먹습니다. "
                    "① Grep 으로 필요한 줄만 뽑거나 ② Read 에 offset/limit 을 주어 부분만 읽으세요. "
                    "정말 전체가 필요하면 하위 에이전트에 위임해 요약만 받으세요."
                    % (os.path.basename(path), size / 1024.0)}})
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
