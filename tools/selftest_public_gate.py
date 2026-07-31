# -*- coding: utf-8 -*-
"""공개 분류 게이트 자기시험 (카나리아) — 보안 장치가 살아 있는지 기계로 확인.

보안 에이전트의 '판단'을 믿지 않기 위한 감시 장치다(사용자 지시 2026-07-31:
"보안 에이전트가 잘 거를 수 있도록 철저한 감시가 필요").
게이트가 조용히 꺼지거나 허용 목록이 넓어지면 이 시험이 실패한다.

실행: python tools/selftest_public_gate.py   (auditor 주간 감사·보안 스캔 시 필수 실행)
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(ROOT, ".claude", "hooks", "verify_git_push.py")
SYNC = os.path.join(ROOT, "tools", "sync_public.py")


def run_gate(cmd):
    p = subprocess.run([sys.executable, GATE],
                       input=json.dumps({"tool_input": {"command": cmd}}).encode("utf-8"),
                       capture_output=True, cwd=ROOT, env=dict(os.environ, CLAUDE_PROJECT_DIR=ROOT))
    return p.returncode, p.stderr.decode("utf-8", "replace")


def main():
    results = []

    # T1: 공개 저장소로 운영물 포함 푸시 시도 → 반드시 차단(2)
    rc, err = run_gate("git push public main")
    results.append(("T1 공개 remote 푸시 = 차단", rc == 2 and "공개 분류" in err, rc))

    # T2: 비공개(origin=ops)로 푸시 → 분류 게이트가 걸리지 않아야 함
    rc2, err2 = run_gate("git push origin main")
    results.append(("T2 비공개 remote 푸시 = 분류 통과", "공개 분류" not in err2, rc2))

    # T3: git push 아닌 명령은 무동작
    rc3, _ = run_gate("git status")
    results.append(("T3 비대상 명령 = 무동작", rc3 == 0, rc3))

    # T4: 허용 목록이 몰래 넓어졌는지(민감 경로가 허용에 들어갔는지) 확인
    src = open(GATE, encoding="utf-8").read()
    line = [l for l in src.split("\n") if l.startswith("PUBLIC_ALLOW")]
    banned_in_allow = any(k in (line[0] if line else "") for k in ("refs/", ".claude", "video/", "tools/"))
    results.append(("T4 허용 목록 무결(민감 경로 미포함)", bool(line) and not banned_in_allow, line[0][:60] if line else "없음"))

    # T5: 공개 배포기가 존재하고 허용 목록이 게이트와 일치
    ok5 = os.path.exists(SYNC) and 'ALLOW_DIRS = ("posts",)' in open(SYNC, encoding="utf-8").read()
    results.append(("T5 공개 배포기 존재·허용 일치", ok5, os.path.basename(SYNC)))

    allpass = all(r[1] for r in results)
    for name, ok, info in results:
        print(("PASS " if ok else "FAIL ") + name + "  [%s]" % info)
    print("RESULT:", "ALL PASS" if allpass else "FAILURES PRESENT")
    sys.exit(0 if allpass else 1)


if __name__ == "__main__":
    main()
