# -*- coding: utf-8 -*-
"""수동 게시 경로(고정 댓글 등)의 자리표시자 게이트 — 2026-07-30 2차 감사 처방.

## 왜 이 파일이 있나

`upload-ep03.js`에는 전송 전 자리표시자 가드가 박혀 있다(DRYRUNID·BODY_URL 등이 남아
있으면 종료코드 2로 중단). 그런데 그 가드는 **API로 나가는 것만** 덮는다. 고정 댓글은
현 OAuth 토큰에 댓글 권한이 없어 **브라우저로 사람이 붙여넣는 경로**이고, 거기에는
검사가 한 대도 없었다 — 2차 감사가 이것을 "가드가 덮지 못하는 유일한 사각지대"로
지적했다. 실제로 `ep03_pinned_comments.md` 두 줄에 `BODY_URL`이 그대로 남아 있었다.

쉬운 말: 공항 검색대를 국제선에 세워 놨는데, 고정 댓글은 걸어서 활주로로 나가는
쪽문이었다. 이 파일이 그 쪽문에 세우는 검색대다.

## 쓰는 법

    python video/verify_manual_post.py <파일...> [--expect-url=https://youtu.be/<id>]

종료 코드: 0 = 통과 / 2 = 미달(게시 금지) / 1 = 실행 오류

원칙(GOVERNANCE §5 자기충족 검증 금지): 이 검사는 "파일이 스스로 옳다"고 말하게 두지
않는다. `--expect-url`로 **실제 업로드 응답에서 받은 URL**을 넣으면, 파일에 그 URL이
정말 들어 있는지까지 대조한다. 넣지 않으면 자리표시자 검사만 하고 그 사실을 밝힌다.
"""
import io, os, re, sys

BAN = re.compile(r"DRYRUNID|BODY_URL|TODO|PLACEHOLDER|XXXX|<videoId>|\{\{.*?\}\}")
YT_ID = re.compile(r"https?://(?:youtu\.be/|(?:www\.)?youtube\.com/(?:watch\?v=|shorts/))"
                   r"([A-Za-z0-9_-]{11})")


def read(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()


def main(argv):
    files, expect = [], None
    for a in argv:
        if a.startswith("--expect-url="):
            expect = a.split("=", 1)[1].strip()
        elif a.startswith("--"):
            return 1, ["알 수 없는 옵션: %s" % a]
        else:
            files.append(a)
    if not files:
        return 1, ["사용: python video/verify_manual_post.py <파일...> "
                   "[--expect-url=https://youtu.be/<id>]"]

    problems, notes = [], []
    for p in files:
        if not os.path.exists(p):
            problems.append("파일 없음: %s" % p)
            continue
        txt = read(p)
        # 각주(※)는 "치환하라"는 지시문이라 자리표시자 단어가 정상적으로 등장한다 →
        # 게시 본문에서 제외하고 검사한다. 본문 정의를 좁히는 것이지 검사를 느슨하게
        # 하는 것이 아니다(각주는 붙여넣지 않는 줄).
        body = [l for l in txt.split("\n") if not l.strip().startswith("※")]
        for i, l in enumerate(body, 1):
            m = BAN.search(l)
            if m:
                problems.append("%s: 게시 본문 %d행에 자리표시자 %r 잔존\n      → %s"
                                % (os.path.basename(p), i, m.group(0), l.strip()[:100]))
        ids = set(YT_ID.findall("\n".join(body)))
        if expect:
            want = YT_ID.findall(expect)
            if not want:
                return 1, ["--expect-url 형식 오류: %r (유튜브 URL이어야 한다)" % expect]
            if want[0] in ids:
                notes.append("%s: 기대 URL(%s) 실재 확인" % (os.path.basename(p), expect))
            else:
                problems.append("%s: 기대 URL %s 이 본문에 없다 (본문에서 찾은 영상 ID: %s)"
                                % (os.path.basename(p), expect, sorted(ids) or "없음"))
        else:
            notes.append("%s: 자리표시자 검사만 수행 — 링크 실재 대조는 안 함"
                         "(--expect-url 미지정)" % os.path.basename(p))
        if not ids:
            notes.append("%s: 본문에 유튜브 링크가 없다(링크가 필요한 원고면 누락 의심)"
                         % os.path.basename(p))
    return (2 if problems else 0), (problems or notes)


if __name__ == "__main__":
    code, lines = main(sys.argv[1:])
    tag = {0: "[통과]", 1: "[오류]", 2: "[미달 — 게시 금지]"}[code]
    for l in lines:
        print("%s %s" % (tag if code else "[확인]", l))
    print("%s 수동 게시 게이트: %s" % (tag, "게시해도 된다" if code == 0 else "게시하지 마라"))
    sys.exit(code)
