# -*- coding: utf-8 -*-
"""푸시 게이트 (전역 훅) — 규칙 3의 기계 강제판.

Bash로 git push 를 실행하기 직전, 자동으로 원격을 fetch해서
로컬이 원격보다 뒤처져 있으면 푸시를 차단한다 (충돌·역사 꼬임 예방).
종료코드 2 = 차단, 0 = 통과. git push가 아닌 명령은 즉시 통과.
"""
import json
import os
import re
import subprocess
import sys

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    cmd = (data.get("tool_input") or {}).get("command", "")
    if not re.search(r"\bgit\s+push\b", cmd):
        sys.exit(0)
    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    def run(args):
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=60)

    try:
        fetch = run(["git", "fetch", "origin", "--quiet"])
    except Exception:
        sys.exit(0)
    if fetch.returncode != 0:
        sys.exit(0)
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    if not branch or branch == "HEAD":
        sys.exit(0)
    behind = run(["git", "rev-list", "--count", "HEAD..origin/%s" % branch])
    n = behind.stdout.strip()
    if behind.returncode == 0 and n.isdigit() and int(n) > 0:
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
        sys.stderr.write("[푸시 게이트 차단] 원격 origin/%s 에 로컬에 없는 새 커밋 %s건이 있음 — "
                         "git pull --rebase origin %s 로 합친 뒤 다시 푸시하세요\n" % (branch, n, branch))
        sys.exit(2)
    sys.exit(0)

if __name__ == "__main__":
    main()
