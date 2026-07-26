# -*- coding: utf-8 -*-
"""업로드 게이트 (저장소 동반 훅) — 로컬·클라우드 공통.

링크드인 게시 도구(execute_zapier_write_action, LinkedIn share) 호출 직전,
전송 본문(comment)을 이 저장소의 원본 md 파일과 자동 대조한다.
- 원본 파일을 못 찾으면 차단 (파일 기반 게시 원칙)
- 한 줄이라도 다르면 차단 (재입력 오탈자 원천 봉쇄 — 2026-07-26 2편 오탈자 실사고)
- 대표 이미지 URL이 4xx/5xx면 차단
종료코드 2 = 차단(사유가 에이전트에게 전달됨), 0 = 통과.
"""
import glob
import json
import os
import re
import sys
import urllib.error
import urllib.request

def norm(text):
    lines = [l.rstrip() for l in text.replace("\r\n", "\n").split("\n")]
    out, prev_blank = [], False
    for l in lines:
        if l.strip() == "":
            if not prev_blank:
                out.append("")
            prev_blank = True
        else:
            out.append(l)
            prev_blank = False
    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out)

def block(msg):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.stderr.write("[업로드 게이트 차단] " + msg + "\n")
    sys.exit(2)

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    ti = data.get("tool_input") or {}
    params = ti.get("params") or {}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except Exception:
            params = {}
    if ti.get("selected_api") != "LinkedInCLIAPI" or ti.get("action") != "share":
        sys.exit(0)
    comment = params.get("comment") or ""
    if not comment.strip():
        block("전송 본문(comment)이 비어 있음")
    first_line = comment.strip().split("\n", 1)[0].strip()
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    src = None
    for f in glob.glob(os.path.join(root, "**", "*.md"), recursive=True):
        sep = os.sep
        if sep + ".git" + sep in f or sep + "node_modules" + sep in f:
            continue
        try:
            t = open(f, encoding="utf-8").read()
        except Exception:
            continue
        if first_line and first_line in t and "## LinkedIn" in t:
            src = f
            break
    if not src:
        block("게시 본문의 첫 줄과 일치하는 원본 md 파일을 프로젝트에서 찾지 못함 — "
              "모든 게시는 저장소 원본 파일에서 그대로 추출해야 함 (첫 줄: %s)" % first_line[:60])
    t = open(src, encoding="utf-8").read()
    m = re.search(r"## LinkedIn 본문\s*\n(.*?)(?:\n---|\n## X )", t, re.S)
    if not m:
        block("%s 에서 'LinkedIn 본문' 섹션을 추출하지 못함" % os.path.basename(src))
    expected_lines = [l for l in m.group(1).split("\n") if not l.strip().startswith("![")]
    expected = norm("\n".join(expected_lines))
    actual = norm(comment)
    if expected != actual:
        a, b = expected.split("\n"), actual.split("\n")
        for i in range(min(len(a), len(b))):
            if a[i] != b[i]:
                block("원본(%s)과 전송 본문 불일치 — %d번째 줄\n  원본: %s\n  전송: %s"
                      % (os.path.basename(src), i + 1, a[i][:80], b[i][:80]))
        block("원본(%s)과 전송 본문 길이 불일치 — 원본 %d줄 vs 전송 %d줄"
              % (os.path.basename(src), len(a), len(b)))
    img = params.get("content__submitted_image_url")
    if img:
        try:
            req = urllib.request.Request(img, method="HEAD")
            resp = urllib.request.urlopen(req, timeout=6)
            if resp.status >= 400:
                block("대표 이미지 URL 응답 오류 HTTP %d: %s" % (resp.status, img))
        except urllib.error.HTTPError as e:
            block("대표 이미지 URL 응답 오류 HTTP %d: %s" % (e.code, img))
        except Exception:
            pass
    sys.exit(0)

if __name__ == "__main__":
    main()
