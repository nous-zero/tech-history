# -*- coding: utf-8 -*-
"""푸시 게이트 (전역+저장소 훅) — 규칙 3의 기계 강제판.

검사 2종:
 A. 최신성: 로컬이 원격보다 뒤처지면 차단(충돌·역사 꼬임 예방).
 B. 공개 분류(2026-07-31 신설, A안): **공개 저장소로 향하는 푸시에 공개 허용 목록 밖 경로가
    섞이면 차단**한다. 민감물(운영 문서·지시서·코드·성과 데이터)은 자동으로 비공개 본진에만
    남는다 — 사용자 승인이 아니라 배관으로 막는다.
종료코드 2 = 차단, 0 = 통과. git push가 아닌 명령은 즉시 통과.
"""
import json
import os
import re
import subprocess
import sys

# 공개 저장소(github.com/nous-zero/tech-history)에 나가도 되는 것만.
PUBLIC_ALLOW = ("posts/", "LICENSE.md", "README.md", ".gitignore", ".gitattributes")
PUBLIC_REPO_RE = re.compile(r"nous-zero/tech-history(\.git)?$")


def block(msg):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.stderr.write(msg + "\n")
    sys.exit(2)


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

    # --- 검사 B: 공개 분류 (원격 URL로 공개 저장소 판별) ---
    m = re.search(r"\bgit\s+push\s+(?:--\S+\s+)*(\S+)", cmd)
    remote = m.group(1) if m and not m.group(1).startswith("-") else ""
    if remote:
        url = run(["git", "remote", "get-url", remote]).stdout.strip()
        if url and PUBLIC_REPO_RE.search(url.rstrip("/")):
            branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip() or "main"
            run(["git", "fetch", remote, "--quiet"])
            rng = run(["git", "diff", "--name-only", "%s/%s..HEAD" % (remote, branch)])
            files = [f for f in rng.stdout.split("\n") if f.strip()] if rng.returncode == 0 else []
            if not files:  # 범위 산출 실패 시 전체 추적 파일로 보수 판정
                files = [f for f in run(["git", "ls-files"]).stdout.split("\n") if f.strip()]
            bad = sorted({f for f in files if not f.startswith(PUBLIC_ALLOW)})
            if bad:
                block(
                    "[공개 분류 게이트 차단] 공개 저장소(%s)로 향하는 푸시에 비공개 대상 %d개 경로가 섞였습니다.\n"
                    "  예: %s\n"
                    "  공개 허용: %s\n"
                    "  → 운영·코드·성과 데이터는 비공개 본진(tech-history-ops)에만 둡니다. "
                    "`git push origin <브랜치>`(origin=비공개)로 보내고, 공개 콘텐츠 배포는 "
                    "`python tools/sync_public.py` 를 쓰세요. (GOVERNANCE §10-2 자동 격리)"
                    % (url, len(bad), ", ".join(bad[:5]), ", ".join(PUBLIC_ALLOW))
                )

    # --- 검사 A: 최신성 ---
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
        block("[푸시 게이트 차단] 원격 origin/%s 에 로컬에 없는 새 커밋 %s건이 있음 — "
              "git pull --rebase origin %s 로 합친 뒤 다시 푸시하세요" % (branch, n, branch))
    sys.exit(0)


if __name__ == "__main__":
    main()
