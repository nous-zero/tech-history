# -*- coding: utf-8 -*-
"""공개 배포기 (A안) — 발행 콘텐츠만 공개 저장소로 자동 동기화.

원칙: 비공개 본진(tech-history-ops)이 진짜 저장소다. 공개 저장소에는
'공개 허용 목록'에 든 것만, 경로를 그대로 유지한 채 복사해 올린다
(경로 유지 = 이미 게시된 링크드인 이미지 카드의 raw URL 생존).

사용: python tools/sync_public.py [--dry-run] [-m "메시지"]
승인 불필요 — 허용 목록 밖은 애초에 복사 대상이 아니므로 유출 경로가 없다.
(GOVERNANCE §10-2 자동 격리)
"""
import argparse
import filecmp
import os
import shutil
import subprocess
import sys

ALLOW_DIRS = ("posts",)
ALLOW_FILES = ("LICENSE.md", "README.md", ".gitignore", ".gitattributes")
PUBLIC_URL = "https://github.com/nous-zero/tech-history.git"

# 공개 허용 목록 안이라도 절대 나가면 안 되는 것(2차 안전망 — 실수로 posts/에 둔 민감물)
DENY_SUBSTR = ("private-", "token", "secret", "credential", "_internal", "-internal")


def sh(args, cwd=None, check=True):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and p.returncode != 0:
        sys.stderr.write((p.stderr or p.stdout).strip() + "\n")
        sys.exit(1)
    return p.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("-m", "--message", default="")
    a = ap.parse_args()

    src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    work = os.path.join(os.path.expanduser("~"), ".cache", "tech-history-public")
    if not os.path.isdir(os.path.join(work, ".git")):
        os.makedirs(os.path.dirname(work), exist_ok=True)
        if os.path.isdir(work):
            shutil.rmtree(work)
        sh(["git", "clone", "--quiet", PUBLIC_URL, work])
    else:
        sh(["git", "-C", work, "fetch", "--quiet", "origin"])
        sh(["git", "-C", work, "reset", "--hard", "--quiet", "origin/main"])

    # 1) 원본에서 허용 목록만 수집 (git 추적 파일 기준 — 미추적 잔재 유입 차단)
    tracked = [f for f in sh(["git", "-C", src, "ls-files"]).split("\n") if f.strip()]
    keep = []
    for f in tracked:
        top = f.split("/")[0]
        if top in ALLOW_DIRS or f in ALLOW_FILES:
            base = os.path.basename(f).lower()
            if any(d in base for d in DENY_SUBSTR):
                print("[제외] 거부 목록 일치: %s" % f)
                continue
            keep.append(f)

    # 2) 공개 클론을 허용 목록 상태로 맞춤 (없어진 것은 삭제, 바뀐 것은 갱신)
    keepset = set(keep)
    existing = [f for f in sh(["git", "-C", work, "ls-files"]).split("\n") if f.strip()]
    removed = [f for f in existing if f not in keepset]
    changed = []
    for f in keep:
        s, d = os.path.join(src, f), os.path.join(work, f)
        if not os.path.exists(d) or not filecmp.cmp(s, d, shallow=False):
            changed.append(f)

    print("공개 대상 %d개 / 갱신 %d개 / 제거 %d개" % (len(keep), len(changed), len(removed)))
    if a.dry_run:
        for f in changed[:20]:
            print("  갱신:", f)
        for f in removed[:20]:
            print("  제거:", f)
        return

    for f in removed:
        sh(["git", "-C", work, "rm", "--quiet", "-f", f], check=False)
    for f in changed:
        d = os.path.join(work, f)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(os.path.join(src, f), d)
        sh(["git", "-C", work, "add", "--", f])
    if not sh(["git", "-C", work, "status", "--porcelain"]):
        print("변경 없음 — 푸시 생략")
        return
    msg = a.message or "publish: 콘텐츠 동기화 (tools/sync_public.py)"
    sh(["git", "-C", work, "commit", "-q", "-m", msg])
    sh(["git", "-C", work, "push", "--quiet", "origin", "HEAD:main"])
    print("공개 저장소 푸시 완료:", sh(["git", "-C", work, "rev-parse", "--short", "HEAD"]))


if __name__ == "__main__":
    main()
