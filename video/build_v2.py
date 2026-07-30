# -*- coding: utf-8 -*-
"""tech-history 영상 공장 v2 — 대본(json) + 코랩 음성(wav) → Manim 애니메이션 MP4.

v1(정적 슬라이드)과 달리 장면을 도형 애니메이션으로 그린다.
설계 원칙(1편 피드백 14건 반영):
  - 텍스트 슬라이드 금지 — 핵심 단어만 팝(pop), 나머지는 도형 연출
  - 하단 한 줄 자막(장면 안에 직접 그림) + SRT 별도 생성
  - © nous-zero 는 인트로/아웃트로에만
  - 흰 배경 + v1 팔레트(잉크/회색/파랑/빨강), 둥근 모서리 톤
  - 마킹(형광펜 박스·밑줄) 연출

사용:
  python video/build_v2.py 01           # 시안(480p15, 빠름) → episode_480p_draft.mp4
  python video/build_v2.py 01 --full    # 완성(1080p30)      → episode.mp4
  python video/build_v2.py 01 --full --sub  # 자막을 영상에 구움(자막 기능 없는 플랫폼용)

산출물 이름 규칙(2026-07-29 감사 처방 P2): **시안은 절대 episode.mp4 를 차지하지 않는다.**
비 --full 렌더는 파일명에 '_draft' 가 강제로 붙고, 로그의 '완성'이라는 단어도 --full
에서만 나온다. 예전에는 480p 시안이 episode.mp4 라는 이름으로 발행 직전까지 갔다.

스펙 검사(자동): --full 렌더가 끝나면 video/verify_output_spec.py 가 자동 실행돼
해상도·라우드니스·무음 비율·길이 불변식을 실측 판정하고 _spec_report.json 을 남긴다.
수동 실행: python video/verify_output_spec.py 01 --body   (종료코드 2 = 규격 미달)

자막 기본값은 '굽지 않음' — 유튜브에는 episode.srt 를 따로 올린다
(시청자가 켜고 끄기 + 자동 번역 + 검색 노출. 화면 핵심 단어 팝은 유지).

음성: video/output/NN_v2/audio/segNNN.wav 가 있으면 그 길이에 맞춰 조립+음성 합성.
      없으면 글자 수로 길이를 추정해 무음 시안만 렌더(구조 확인용).
"""
import glob
import json
import os
import re
import subprocess
import sys
import wave

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EP = next((a for a in sys.argv[1:] if not a.startswith("-")), "01")
FULL = "--full" in sys.argv
BURN_SUB = "--sub" in sys.argv  # 자막을 영상에 구울지 (기본: SRT만 생성)
OUT = os.path.join(ROOT, "video", "output", f"{EP}_v2")


def _optval(name, default):
    """--이름=값 꼴 옵션 파싱 (예: --audio-dir=audio_take2)."""
    pref = f"--{name}="
    for a in sys.argv[1:]:
        if a.startswith(pref):
            return a.split("=", 1)[1]
    return default


# 음성 폴더 선택: 음성팀이 audio/를 재작업 중일 때 스냅샷(audio_take2 등)으로
# 타이밍만 잡아 시안을 렌더할 수 있게 한다. 기본값은 기존과 동일한 audio/.
# 부분 재렌더(청크) 옵션 — 긴 렌더가 외부 종료로 끊겼을 때 남은 구간만 다시 굽는다.
#   --from-anim=N : N번 애니메이션부터 렌더(앞 구간은 계산만 하고 프레임을 굽지 않음)
#   --no-mux      : 조립(오디오 먹싱·스펙검사)을 생략하고 파셜 생산만 — 청크를 이어붙일 때 사용
# 배경(2026-07-30): 1080p 전량 렌더가 70분대에서 두 번 외부 종료됨. 파셜 무비 파일
# (animation 단위 조각 영상)은 인덱스 이름으로 남으므로, 끊긴 지점부터 다시 구워
# 전체를 이어붙이면 처음부터 다시 굽지 않아도 된다(rule7 — 순단은 운영 조건).
#   --mux-only    : 렌더를 하지 않고, 이미 남아 있는 파셜 전량을 이어붙여 오디오만 먹싱
#                   (청크 재렌더 뒤 복구용 — 결번·0바이트 파셜이 있으면 조립을 거부한다)
#   --layout-audit: 프레임을 한 장도 굽지 않고 장면을 끝까지 '계산만' 해서 레이아웃
#                   불변식(프레임 이탈·보호 영역 침범)만 판정한다. 70분 렌더 없이 몇 초.
FROM_ANIM = _optval("from-anim", None)
UPTO_ANIM = _optval("upto-anim", None)
NO_MUX = "--no-mux" in sys.argv
MUX_ONLY = "--mux-only" in sys.argv
LAYOUT_AUDIT = "--layout-audit" in sys.argv
AUDIO_SUB = _optval("audio-dir", "audio")
AUDIO_DIR = os.path.join(OUT, AUDIO_SUB)
# 렌더 규격(해상도·프레임률)의 단일 출처. 파일명·로그 표기·검사기 모두 이 값을 쓴다.
VW, VH, VFPS = (1920, 1080, 30) if FULL else (854, 480, 15)

# 출력 파일명 선택: 시안을 episode.mp4 와 다른 이름으로 남겨 최종본과 섞이지 않게.
# [P2 / 2026-07-29 감사 처방] 시안(비 --full)이 최종 파일명(episode.mp4)을 차지한 채
# 발행 직전까지 간 사고(854x480 본편) 재발 방지 — 시안 산출물은 '_draft' 를 강제한다.
# refs/audit-reports/2026-07-29-quality-gate-failure.md §3-P2, 근본원인 R4(도구가 오인 유발).
OUT_NAME = _optval("out-name", "episode.mp4" if FULL else f"episode_{VH}p_draft.mp4")
if not FULL and "_draft" not in OUT_NAME:
    _stem, _ext = os.path.splitext(OUT_NAME)
    OUT_NAME = f"{_stem}_{VH}p_draft{_ext or '.mp4'}"
    print(f"[v2] 시안 모드 — 최종 파일명 보호: 출력명을 {OUT_NAME} 로 강제")
OUT_STEM = os.path.splitext(OUT_NAME)[0]
os.makedirs(OUT, exist_ok=True)

GAP = 0.35          # 세그먼트 사이 쉼(초) — 음성에도 같은 길이 무음 삽입
INTRO_D = 2.8       # 인트로 카드 길이
SEC_PER_CHAR = 0.155  # 음성 없을 때 길이 추정(한국어 낭독 대략치)

INK = "#1F2937"
GRAY = "#6B7280"
LGRAY = "#9CA3AF"
BLUE = "#2563EB"
RED = "#DC2626"
AMBER = "#F59E0B"
PAPER = "#F9FAFB"
KFONT = "Malgun Gothic"
MONO = "Consolas"


# ---------- 대본 → 문장·시간 배분 ----------

def split_sents(text):
    parts = [p.strip() for p in re.findall(r"[^.?!]+[.?!]*", text) if p.strip()]
    out, buf = [], ""
    for p in parts:
        cand = (buf + " " + p).strip()
        if len(cand) < 7:
            buf = cand
            continue
        out.append(cand)
        buf = ""
    if buf:
        if out:
            out[-1] += " " + buf
        else:
            out = [buf]
    return out


def wav_seconds(path):
    with wave.open(path, "rb") as w:
        return w.getnframes() / float(w.getframerate())


def load_timed_segments():
    with open(os.path.join(ROOT, "video", "scripts", f"{EP}.json"), encoding="utf-8") as f:
        data = json.load(f)
    timed, have_audio = [], True
    for seg in data["segments"]:
        sents = split_sents(seg["text"])
        wav = os.path.join(AUDIO_DIR, f"seg{seg['id']:03d}.wav")
        if os.path.exists(wav):
            total = wav_seconds(wav)
        else:
            have_audio = False
            total = sum(SEC_PER_CHAR * len(s) + 0.45 for s in sents)
        chars = sum(len(s) for s in sents) or 1
        durs = [max(0.7, total * len(s) / chars) for s in sents]
        scale = total / sum(durs)
        durs = [d * scale for d in durs]
        timed.append({"id": seg["id"], "scene": seg["scene"],
                      "sents": list(zip(sents, durs)), "total": total, "wav": wav})
    return data, timed, have_audio


DATA, TIMED, HAVE_AUDIO = load_timed_segments()

# ---------- Manim 장면 ----------

from manim import (  # noqa: E402
    config, Scene, VGroup, VMobject, Group, Text, Dot, Circle, Line, DashedLine,
    Rectangle, RoundedRectangle, RegularPolygon, Triangle, Arrow, Underline,
    SurroundingRectangle, DashedVMobject, ArcBetweenPoints, ImageMobject,
    Create, FadeIn, FadeOut, Transform, ReplacementTransform, Indicate, Wiggle,
    Flash, MoveAlongPath, LaggedStart, GrowFromCenter, linear,
    UP, DOWN, LEFT, RIGHT, ORIGIN, UL, UR, DL, DR, WHITE, PI,
)

ASSETS = os.path.join(ROOT, "video", "output", "assets")  # 실사 사료(퍼블릭 도메인 검증분)

config.background_color = WHITE
config.pixel_width, config.pixel_height, config.frame_rate = VW, VH, VFPS
config.media_dir = os.path.join(OUT, "media")
config.output_file = "ep_silent"
config.disable_caching = True
# 파셜 무비 파일(애니메이션 단위 조각 영상)을 하나도 버리지 않는다.
# 기본값 100이면 101번째를 구울 때 가장 오래된 조각부터 지운다(manim scene_file_writer.clean_cache).
# 3편 렌더가 외부 종료된 뒤 남은 조각으로 복구하려다, 앞부분 0~53번이 이미 지워진 것을 실측 발견
# (2026-07-30). 조각을 남겨두면 끊긴 지점부터만 다시 구워 이어붙일 수 있다 — 153개 × 약 85KB로
# 용량 부담도 미미하다. -1 = 무제한(manim default.cfg:137 주석 근거).
config.max_files_cached = -1
if FROM_ANIM is not None:
    config.from_animation_number = int(FROM_ANIM)
    print(f"[v2] 부분 렌더: {FROM_ANIM}번 애니메이션부터 굽는다(앞 구간은 계산만).")
if UPTO_ANIM is not None:
    config.upto_animation_number = int(UPTO_ANIM)
    print(f"[v2] 부분 렌더: {UPTO_ANIM}번 애니메이션까지만 굽는다.")
if LAYOUT_AUDIT:
    # 전 애니메이션을 '건너뛰기' 상태로 통과시킨다 — mobject 상태는 정상 갱신되지만
    # 프레임 인코딩이 없어 몇 초에 끝난다. 배치 검사 전용 모드.
    config.from_animation_number = 10 ** 9
    config.dry_run = True
    print("[v2] 레이아웃 감사 모드: 프레임을 굽지 않고 배치 불변식만 판정한다.")

MESH_P =[(-4.5, 1.6), (-2.2, 2.2), (0.2, 1.9), (2.6, 2.1), (4.6, 1.5),
          (-3.4, 0.1), (-1.0, 0.5), (1.4, 0.3), (3.6, 0.2),
          (-2.3, -1.3), (0.1, -1.1), (2.4, -1.4)]
MESH_E = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (1, 5), (1, 6), (2, 6),
          (2, 7), (3, 7), (3, 8), (4, 8), (5, 6), (6, 7), (7, 8),
          (5, 9), (6, 9), (6, 10), (7, 10), (7, 11), (8, 11), (9, 10), (10, 11)]


def P3(xy, z=0.0):
    return [xy[0], xy[1], z]


def ktext(s, fs=36, color=INK, bold=False):
    t = Text(s, font=KFONT, font_size=fs, color=color,
             weight="BOLD" if bold else "NORMAL")
    if t.width > 13:
        t.scale_to_fit_width(13)
    return t


def ktext_block(s, fs=24, color=GRAY, max_width=13.0, bold=False, buff=0.16,
                aligned_edge=ORIGIN):
    """긴 한 줄을 max_width 안에 담기도록 어절(띄어쓰기) 단위로 줄바꿈한 글자 덩어리.

    쉬운 말: 글자 크기를 줄여 억지로 우겨넣는 대신 신문처럼 줄을 나눠 담는다.
    글자를 줄이면 안 읽히고, 안 줄이면 옆 요소를 침범한다 — 그 사이의 정답이 줄바꿈이다.
    (2026-07-30: 3편 아웃트로 예고 부제가 한 줄 7.28 폭으로 구독 버튼·예고 사진을
    동시에 침범한 결함의 수리 수단. ktext() 의 scale_to_fit_width 는 폭만 맞추고
    가독성을 버리므로 좁은 칸에는 부적합했다.)
    """
    lines, cur = [], ""
    for w in s.split(" "):
        cand = (cur + " " + w).strip()
        probe = Text(cand, font=KFONT, font_size=fs,
                     weight="BOLD" if bold else "NORMAL")
        if cur and probe.width > max_width:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    mobs = []
    for ln in lines:
        m = Text(ln, font=KFONT, font_size=fs, color=color,
                 weight="BOLD" if bold else "NORMAL")
        if m.width > max_width:   # 한 어절이 통째로 칸을 넘으면 그 줄만 축소
            m.scale_to_fit_width(max_width)
        mobs.append(m)
    return VGroup(*mobs).arrange(DOWN, buff=buff, aligned_edge=aligned_edge)


def rect_overlap(a, b, eps=0.01):
    """두 바운딩박스(왼,오른,아래,위)의 겹침 폭·높이. 안 겹치면 None.
    eps: 맞닿음(gap 0)에서 부동소수 오차가 '겹침 1e-16'으로 오보되는 것을 막는 문턱값
    (0.01 월드 단위 ≈ 1080p 에서 1.4픽셀 — 눈에 보이지 않는 크기)."""
    ox = min(a[1], b[1]) - max(a[0], b[0])
    oy = min(a[3], b[3]) - max(a[2], b[2])
    return (ox, oy) if (ox > eps and oy > eps) else None


def mtext(s, fs=48, color=INK, bold=True):
    return Text(s, font=MONO, font_size=fs, color=color,
                weight="BOLD" if bold else "NORMAL")


def chip(s, color=BLUE, fs=30):
    t = Text(s, font=KFONT, font_size=fs, color=WHITE, weight="BOLD")
    box = RoundedRectangle(corner_radius=0.16, width=t.width + 0.55,
                           height=t.height + 0.42)
    box.set_fill(color, 1).set_stroke(width=0)
    t.move_to(box)
    return VGroup(box, t)


# ---------- 법무 표기 캡션(재현 화면·크레딧)의 기계 강제 (2026-07-30 신설) ----------
#
# 배경: copyright-counsel §9-4 는 화면 표기가 "읽을 수 있을 만큼" 떠 있을 것을 요구하고,
# 그 최소치를 max(2.0초, 문자수÷6) 로 정한다. 3편 seg10 의 재현 표기는 33자여서
# 요구 5.50초 / 실측 5.50~5.75초 — **여유 0의 경계 통과**였다(refs/publish-reviews.md
# 3편 본편 행 근거 ⑦, refs/pipeline-status.md "4편 이월 과업").
#
# 왜 '빌드 실패(예외)'이고 '표시 시간 자동 연장'이 아닌가 —
#   이 조립기의 최상위 불변식은 **영상 길이 = Σwav 길이**다(자막 SRT·오디오 트랙이 같은
#   TIMED 표에서 나온다). 캡션 하나를 늘리려면 그 컷의 길이를 늘려야 하고, 그러면 뒤따르는
#   모든 세그먼트가 밀려 내레이션과 그림이 어긋난다. 게다가 캡션은 사진과 한 몸으로 뜨고
#   지므로(Group(ph, cap)) 캡션만 늘리면 사진이 사라진 자리에 표기만 떠 있게 된다.
#   즉 '자동 연장'은 이 구조에서 실행 불가능한 처방이다. 대신 **글자 수를 줄이도록**
#   렌더 시작 몇 초 안에 예외로 막는다(70분 렌더를 버리지 않는 지점에서 실패시킨다).
#
# 20자 상한만으로 충분한가 — **충분하지 않다.** 20자면 요구 지속은 20÷6 = 3.33초이고,
#   그보다 짧게 띄우면 여전히 위반이다. 그래서 상한(입력)과 **실제 표기 지속 실측(출력)**
#   두 개를 함께 건다: 지속 미달은 [audit] 줄로 남고 verify_output_spec.py 가 FAIL 로
#   판정한다(--layout-audit 모드에서는 종료코드 2).
#
# ⚠️ 이 캡션은 저작권 표기이자 **유튜브 AI 공개 답변의 전제**다 (counsel 판정서
#   refs/legal-review-ep04.md §6-2·§8-2, 총감독 회부 2026-07-30).
#   "재현 화면" 표기가 화면에 떠 있어야 시청자가 그 장면을 실사 사료로 오인하지 않고,
#   그래서 업로드 시 "실재하지 않는 장면을 생성했는가" 문항에 지금의 답을 유지할 수 있다.
#   **캡션을 지우면 저작권 축과 AI 공개 축이 동시에 무너진다** — 둘은 한 몸이다.
#   캡션을 지우거나 시간을 줄이려는 사람은 반드시 counsel 을 먼저 거칠 것.
LEGAL_CAPTION_MAX = 20        # 화면 법무 표기 최대 글자 수(공백 포함)
LEGAL_MIN_SEC = 2.0           # counsel §9-4 하한
LEGAL_CHARS_PER_SEC = 6.0     # counsel §9-4 읽기 속도(문자수 ÷ 6)
# counsel 4편 단일 규칙(§6-3): "20자 이내 + 최소 3.5초 연속 표시".
# 20자의 요구 하한이 20÷6 = 3.34초이므로, 상수 3.5초 하나로 20자 이내 **모든** 문구를
# 덮는다 — 캡션마다 문자수를 세어 시간을 계산할 필요가 없어진다. 다만 레거시 예외처럼
# 20자를 넘는 문구는 3.5초로 부족하므로(33자=5.50초), 두 값의 **큰 쪽**을 요구한다.
LEGAL_MIN_HOLD = 3.5

# 이미 발행된 편의 표기는 소급 변경하지 않는다(사용자 결정 "1~3편 소급 없음").
# 이 표에 없는 문구가 20자를 넘으면 즉시 빌드가 죽는다 — 예외는 여기 적힌 것뿐이고,
# 각 항목은 '왜 남아 있는지'를 함께 적는다(조용한 예외 금지).
LEGAL_CAPTION_LEGACY = {
    ("03", "최초의 웹사이트 — '웹이란 무엇인가' 안내문 (재현 화면)"):
        "3편 발행본(2026-07-30, YouTube fQbG07NitUg)의 seg10 표기. 33자 = 요구 5.50초, "
        "실측 5.50~5.75초로 경계 통과했다. 재렌더 시 화면이 달라지므로 소급 수정 금지 — "
        "이 예외가 곧 '20자 상한' 규칙이 생긴 이유의 물증이다.",
}


class LegalCaptionError(RuntimeError):
    """법무 표기 캡션이 문법 규칙을 어겼을 때 — 렌더를 진행시키지 않는다."""


LEGAL_CAPTIONS = []   # 이번 렌더에서 만들어진 법무 표기 대장(지속 시간 실측 대상)

# ---------- 실사용 소재 대장 (2026-07-30 counsel §15 / 총감독 회부) ----------
#
# 왜: 3편에서 **실제로는 안 쓴 소재 5건이 크레딧에 남아** 발행 직전에 사람 눈으로
# 걸러졌다. 반대 방향(썼는데 크레딧에 없음)은 저작권 사고다. 두 방향을 기계로 대조하려면
# 먼저 "이 렌더가 정말 연 파일이 무엇인가"라는 사실 데이터가 있어야 한다.
# 수기 목록은 그 자체가 오류 주입 경로이므로, **파일을 여는 지점을 후킹**해 자동 기록한다.
ASSET_USES = {}       # {파일명: {"md5":…, "bytes":…, "segs":[…], "count":n}}
_MD5_CACHE = {}


def record_asset_use(path, seg):
    """소재 파일이 실제로 열릴 때마다 대장에 적는다(md5 는 파일당 1회만 계산)."""
    import hashlib
    name = os.path.basename(path)
    if name not in ASSET_USES:
        if path not in _MD5_CACHE:
            h = hashlib.md5()
            with open(path, "rb") as f:
                for blk in iter(lambda: f.read(1 << 20), b""):
                    h.update(blk)
            _MD5_CACHE[path] = h.hexdigest()
        ASSET_USES[name] = {"md5": _MD5_CACHE[path],
                            "bytes": os.path.getsize(path), "segs": [], "count": 0}
    rec = ASSET_USES[name]
    rec["count"] += 1
    if seg not in rec["segs"]:
        rec["segs"].append(seg)
    return name


def legal_min_seconds(text):
    """요구 표기 지속 = max(counsel §9-4 공식, 4편 단일 규칙 3.5초).

    쉬운 말: "이 문구는 최소 몇 초 동안 화면에 떠 있어야 하나"를 계산한다.
    §9-4 공식은 max(2.0초, 문자수÷6), 여기에 4편 단일 규칙의 바닥 3.5초를 얹는다.
    """
    return max(LEGAL_MIN_SEC, len(text) / LEGAL_CHARS_PER_SEC, LEGAL_MIN_HOLD)


def legal_chip(s, color=GRAY, fs=20, kind="재현 표기"):
    """법무가 요구하는 화면 표기(재현 이미지·재현 화면·크레딧)를 만드는 **유일한 경로**.

    쉬운 말: "이건 법으로 반드시 화면에 띄워야 하는 문구"라고 조립기에 신고하는 것.
    신고된 문구만 글자 수 상한과 표기 지속을 기계가 재 준다. 그냥 chip() 으로 만들면
    법무 표기로 세지 않는다 — 그래서 법무 표기는 반드시 이 함수로 만든다.
    """
    if len(s) > LEGAL_CAPTION_MAX and (EP, s) not in LEGAL_CAPTION_LEGACY:
        raise LegalCaptionError(
            f"법무 표기 캡션 {len(s)}자 — 상한 {LEGAL_CAPTION_MAX}자 초과: {s!r}\n"
            f"  counsel §9-4 요구 표기 지속 = max(2.0, {len(s)}÷6) = "
            f"{legal_min_seconds(s):.2f}초. 컷이 그만큼 길지 않으면 위반이다.\n"
            f"  조치: 문구를 {LEGAL_CAPTION_MAX}자 이내로 줄이거나(권장), 정말 못 줄이면 "
            f"build_v2.LEGAL_CAPTION_LEGACY 에 사유와 함께 등록할 것.")
    g = chip(s, color, fs)
    g.legal_note = {"text": s, "chars": len(s), "need": legal_min_seconds(s),
                    "kind": kind, "first": None, "last": None, "box": None,
                    "legacy": (EP, s) in LEGAL_CAPTION_LEGACY}
    LEGAL_CAPTIONS.append(g)
    return g


def missile(scale=1.0):
    m = Triangle().scale(0.22 * scale).rotate(PI)  # 아래를 향한 삼각형
    m.set_fill(RED, 1).set_stroke(RED, 2)
    return m


def build_mesh(scale=1.0, shift=(0, 0), square=False):
    pts = [P3((x * scale + shift[0], y * scale + shift[1])) for x, y in MESH_P]
    if square:
        nodes = VGroup(*[RoundedRectangle(corner_radius=0.05, width=0.34 * scale,
                                          height=0.34 * scale)
                         .set_fill(WHITE, 1).set_stroke(INK, 3).move_to(p)
                         for p in pts])
    else:
        nodes = VGroup(*[Dot(p, radius=0.13 * scale, color=INK) for p in pts])
    edges = VGroup(*[Line(pts[a], pts[b], buff=0.16 * scale).set_stroke(LGRAY, 3)
                     for a, b in MESH_E])
    return nodes, edges, pts


class EpisodeBase(Scene):
    CLEAR_AFTER = set()  # 세그 종료 후 무대를 비울 번호 — 에피소드별로 지정

    def construct(self):
        self.subtitle = None
        self.st = {}
        self._cur_seg = "intro"
        self.reserve_standing_zones()
        self.intro()
        for k, seg in enumerate(TIMED):
            self._cur_seg = k
            getattr(self, f"seg{k:02d}")(seg["sents"])
            if self.subtitle:
                self.remove(self.subtitle)
                self.subtitle = None
            if k in self.CLEAR_AFTER:
                self.clear_stage(GAP)
            else:
                self.wait(GAP)
        self.wait(1.2)
        self.report_layout()
        self.write_render_manifest()

    # --- 레이아웃 불변식: 프레임 이탈 + 보호 영역 침범 (2026-07-30 신설) ----------
    #
    # 배경: 감사가 지적한 "본편 프레임 이탈 불변식 부재"(유형 A 누적 5회)에 더해,
    # 3편 아웃트로에서 **프레임 안인데 요소끼리 겹치는** 새 유형이 나왔다
    # (예고 부제가 구독 버튼 밑으로 파묻힘 — 2026-07-30 실측 가로 1.19 세로 0.10).
    # fit_frame() 은 '액자 밖으로 나갔나'만 보므로 이 유형을 구조적으로 못 잡는다.
    # 쇼츠(build_shorts.audit_frame)에만 있던 이탈 감사를 본편에 이식하고,
    # '남의 자리를 밟았나'를 보는 보호 영역 감사를 함께 세운다(rule5-4 승격).
    #
    # 감사 시점은 매 play/wait 직후(애니메이션 종료 상태). 애니메이션 도중의
    # 순간적 확대(FadeIn scale=1.5 등)는 이 검사 범위 밖 — 쇼츠와 동일한 한계다.
    LAYOUT_MARGIN = 0.16   # 요소 사이 최소 여유(월드 단위, 프레임 폭 14.22 기준)

    _zones = None       # 보호 영역(침범 금지 구역) 대장
    _overflow = None    # 프레임 이탈 적발 기록
    _intrusion = None   # 보호 영역 침범 적발 기록
    _crowding = None    # 여유(마진)만 침범 — 경고
    _zones_seen = None  # 실제로 '살아 있던' 구역 이름들(등록만 하고 잠든 것 제외)
    _seg_covered = None # 구역이 하나라도 살아 있던 구간(인트로 + 세그 번호)
    _cur_seg = "intro"  # 지금 그리고 있는 구간
    _photo_n = 0        # 사진 구역 일련번호(같은 사진을 두 번 써도 이름이 안 겹치게)

    # --- 전 구간 보호영역(2026-07-30 4편 이월 과업 ③) --------------------------
    #
    # 문제: 3편까지 reserve_cta() 가 아웃트로에만 있어 **애니메이션 0~140 구간은 등록
    # 구역 0개**였다. 구역이 없으면 "침범 0건"은 아무것도 검사하지 않고 참이 된다
    # (공허한 참). refs/publish-reviews.md 3편 본편 행 근거 ⑧.
    #
    # 조치: 장면 시작 시 상시 구역 2개(자막 대역·하단 UI 대역)를 깔고, 사진이 만들어질
    # 때마다 그 사진을 따라다니는 구역을 자동 등록한다. **전부 enforce=False(감사 전용)**
    # — 배치 계산에 끼어들면 기존 편(01·02·03)의 화면이 달라진다. 감사는 새로 보되
    # 그림은 1픽셀도 건드리지 않는다는 것이 이 설계의 핵심 제약이다.
    #
    # 좌표 근거(프레임 14.222 × 8.0, 1080p 기준 1px ≈ 0.0074 월드):
    #  · 자막: sub() 이 fs30 텍스트를 to_edge(DOWN, buff=0.32) 에 놓고 폭 상한 12.8
    #          → 글자가 차지하는 칸은 대략 y -3.68~-3.20, x ±6.4
    #  · 하단 UI: 유튜브 플레이어 진행바·시간 표시가 덮는 최하단 띠(화면 높이의 약 5%)
    #          → y -4.0~-3.60 전폭. (플랫폼 오버레이라 화면 밖 요인 — 추정치로 표기)
    #
    # 왜 '자동 등록 구역'은 4편부터만 차단인가 — **실측 결과**다(2026-07-30).
    # 3편에 자동 구역을 깔고 --layout-audit 을 돌리니 23건이 걸렸는데, 뜯어보니
    # 20건이 이 시리즈의 확립된 화면 문법이었다: 사진 위에 일부러 얹는 도장·라벨
    # (「무료 — 영원히」 3.00×1.44, 「각색 아님」 4.45×1.30 …)과 하단 캡션 칩.
    # 문법 자체를 결함으로 세면 경보가 무뎌지고(경보 피로), 이미 발행된 3편을
    # 소급 재설계하라는 요구가 된다(사용자 결정 "1~3편 소급 없음").
    # 그래서 **1~3편은 권고(경고)로 보고만 하고, 4편부터 차단**으로 올린다.
    # 4편 저자는 의도한 겹침을 claim_all_photos()/claim_bottom() 으로 신고하면 된다
    # — "의도"를 말로 남기게 만드는 것이 이 규칙의 목적이다. (BGM 4편 필수와 같은 방식)
    ZONE_STRICT_FROM_EP = 4
    SUB_BAND = "자막 대역"
    UI_BAND = "하단 UI·로고 대역"
    PHOTO_ZONE_PREFIX = "사진/스크린샷"

    @staticmethod
    def _auto_zone_blocks():
        """자동 등록 구역의 침범을 '차단(FAIL)'으로 셀지 '권고(WARN)'로 셀지."""
        try:
            epn = int(re.sub(r"\D", "", EP) or 0)
        except ValueError:
            epn = 0
        return epn >= EpisodeBase.ZONE_STRICT_FROM_EP

    def reserve_standing_zones(self):
        """장면 전 구간에 깔리는 상시 보호영역. 인트로 첫 컷부터 살아 있다."""
        self.reserve_zone(self.UI_BAND, (-config.frame_width / 2, config.frame_width / 2,
                                         -config.frame_height / 2, -3.60),
                          pad=0.0, kind="block", enforce=False)
        self.reserve_zone(self.SUB_BAND, (-6.4, 6.4, -3.60, -3.10),
                          pad=0.0, kind="block", enforce=False)

    def claim_bottom(self, *mobs):
        """하단 두 띠의 '정식 거주자'로 신고한다 — © 배지·CTA 버튼처럼 거기 있는 게 설계인 것.

        쉬운 말: "이 자리는 원래 얘 자리예요"라고 검사관 명부에 올리는 것.
        신고 안 된 요소가 그 띠에 들어가면 감사가 적발한다(자막이 가려지는 자리이므로).
        """
        for nm in (self.UI_BAND, self.SUB_BAND):
            self.claim_zone(nm, *mobs)
        return mobs[0] if mobs else None

    def _describe(self, m):
        txts = [s.text for s in m.get_family() if isinstance(s, Text)]
        if txts:
            return "「" + " / ".join(t[:16] for t in txts[:2]) + "」"
        return type(m).__name__

    @staticmethod
    def bbox(m, pad=0.0):
        return (m.get_left()[0] - pad, m.get_right()[0] + pad,
                m.get_bottom()[1] - pad, m.get_top()[1] + pad)

    def reserve_zone(self, name, m, pad=None, owners=(), kind="block",
                     enforce=True, track=None):
        """침범 금지 구역(보호 영역)을 등록한다.

        쉬운 말: "여기는 나중에 구독 버튼이 앉을 자리니 비워둬"라고 미리 금줄을 치는 것.
        아직 화면에 없는 요소의 자리도 예약할 수 있다 — 아웃트로는 예고 부제(먼저)와
        CTA 버튼(나중)이 다른 컷에서 생기므로, 자리 예약 없이는 저자가 겹침을 볼 수 없다.

        kind    "block" = 조금이라도 겹치면 침범 / "edge" = **테두리를 걸칠 때만** 침범.
                'edge' 는 사진·스크린샷용이다: 사진 위에 일부러 올리는 도장·라벨은
                정상 연출이고, 사진 밖에 있는 것도 정상이다. 결함은 그 중간 —
                "반은 사진 안, 반은 사진 밖"으로 테두리를 물고 있는 상태다
                (3편 seg10 배지가 스크린샷 테두리를 문 유형).
        enforce 배치 계산(avoid_zones·free_x_band)이 이 구역을 피할지 여부.
                **False = 감사 전용**. 자동 등록 구역은 전부 False 다 — 등록만으로
                기존 편(01·02·03)의 화면이 1픽셀이라도 달라지면 안 되기 때문이다
                (배치 계산에 새 장애물이 끼면 요소가 밀려 그림이 바뀐다).
        track   이 mobject 를 따라다니는 구역. 켄 번즈로 사진이 커지고 밀려도 금줄이
                같이 움직이고, 그 mobject 가 무대에서 내려가면 구역도 잠든다.
        """
        if self._zones is None:
            self._zones = {}
        pad = self.LAYOUT_MARGIN if pad is None else pad
        box = self.bbox(m) if hasattr(m, "get_left") else tuple(m)
        self._zones[name] = {"box": box, "pad": pad, "owners": set(),
                             "kind": kind, "enforce": enforce, "track": track}
        if owners:
            self.claim_zone(name, *owners)
        return box

    def claim_zone(self, name, *owners):
        """보호 영역의 '주인'을 등록 — 주인은 자기 구역을 침범한 것으로 세지 않는다."""
        z = (self._zones or {}).get(name)
        if not z:
            return
        for o in owners:
            z["owners"].add(id(o))
            z["owners"].update(id(c) for c in o.get_family())

    def claim_all_photos(self, *mobs, why=""):
        """사진 위에 **일부러** 올리는 요소(도장·라벨)를 '정상 연출'로 신고한다.

        쉬운 말: "이건 사진에 겹쳐 찍는 게 의도"라고 검사관에게 미리 말해 두는 것.
        신고 없이 사진 테두리를 물면 감사가 결함으로 적발한다(그게 목적이다).
        """
        for nm, z in (self._zones or {}).items():
            if z["kind"] == "edge" and nm.startswith(self.PHOTO_ZONE_PREFIX):
                self.claim_zone(nm, *mobs)
        return mobs[0] if mobs else None

    def _obstacles(self, exclude=()):
        # enforce=False 구역(자동 등록분)은 배치 계산에서 제외한다 — 감사에만 쓴다.
        boxes = [(nm, self._zone_box(z), z["pad"])
                 for nm, z in (self._zones or {}).items() if z.get("enforce", True)]
        boxes += [(self._describe(m), self.bbox(m), self.LAYOUT_MARGIN) for m in exclude]
        return boxes

    @staticmethod
    def _zone_box(z):
        """구역의 지금 위치 — track 이 있으면 그 mobject 를 다시 재고, 없으면 고정 좌표."""
        tr = z.get("track")
        if tr is not None:
            try:
                return (tr.get_left()[0], tr.get_right()[0],
                        tr.get_bottom()[1], tr.get_top()[1])
            except Exception:  # noqa: BLE001
                return z["box"]
        return z["box"]

    def free_x_band(self, y_lo, y_hi, anchor=0.0, exclude=(), pad=None):
        """세로 [y_lo, y_hi] 구간에서 보호 영역·지정 요소를 피해 쓸 수 있는 가로 구간.

        반환: (왼쪽 한계, 오른쪽 한계, 폭). 저자가 폭 상한을 눈대중이 아니라 수치로 잡게 한다
        — 3편 결함의 직접 원인은 "이 정도면 들어가겠지"라는 눈대중이었다(rule6).
        """
        pad = self.LAYOUT_MARGIN if pad is None else pad
        left = -config.frame_width / 2 + pad
        right = config.frame_width / 2 - pad
        for _nm, (l, r, b, t), zpad in self._obstacles(exclude):
            if t + zpad <= y_lo or b - zpad >= y_hi:   # 세로로 안 겹치면 가로를 막지 않는다
                continue
            if r + zpad <= anchor:
                left = max(left, r + zpad)
            elif l - zpad >= anchor:
                right = min(right, l - zpad)
            else:                                       # 기준점을 덮은 장애물 — 넓은 쪽을 취함
                if (l - zpad) - left >= right - (r + zpad):
                    right = min(right, l - zpad)
                else:
                    left = max(left, r + zpad)
        return left, right, max(0.0, right - left)

    def avoid_zones(self, m, pad=None, allow_shrink=True, rounds=4):
        """m 이 보호 영역을 침범하면 자동 회피시킨다 — fit_frame() 의 '겹침' 짝.

        순서: ①가로로 살짝 밀어내기 ②(폭이 남는 칸보다 크면) 폭 줄이기 ③세로로 밀어내기.
        밀어낸 뒤 프레임 이탈을 다시 막는다(회피가 새 결함을 만들지 않게).
        완전한 자동 배치는 아니고 '작은 겹침의 자동 해소'용 — 큰 충돌은 감사가 적발해
        저자가 재배치하도록 남긴다(조용히 예쁘지 않게 고치는 것보다 시끄럽게 막는 게 낫다).
        """
        pad = self.LAYOUT_MARGIN if pad is None else pad
        for _ in range(rounds):
            worst = None
            for nm, z in (self._zones or {}).items():
                if id(m) in z["owners"] or not z.get("enforce", True):
                    continue   # 감사 전용 구역은 배치를 건드리지 않는다(기존 편 화면 불변)
                ov = rect_overlap(self.bbox(m, pad * 0.5), self._zone_box(z))
                if ov and (worst is None or min(ov) > min(worst[1])):
                    worst = (nm, ov, z)
            if worst is None:
                break
            _nm, (ox, oy), z = worst
            zl, zr, zb, zt = self._zone_box(z)
            l, r, b, t = self.bbox(m)
            band_l, band_r, band_w = self.free_x_band(b, t, anchor=(l + r) / 2, pad=pad)
            if allow_shrink and (r - l) > band_w > 0.8:
                m.scale_to_fit_width(band_w)
                m.move_to(P3(((band_l + band_r) / 2, (b + t) / 2)))
            elif ox <= oy:                        # 가로로 비켜 가는 편이 싸다
                away = -1.0 if (l + r) / 2 <= (zl + zr) / 2 else 1.0
                m.shift(RIGHT * (ox + pad * 0.5) * away)
            else:
                away = 1.0 if (b + t) / 2 >= (zb + zt) / 2 else -1.0
                m.shift(UP * (oy + pad * 0.5) * away)
            self.fit_frame(m)
        return m

    # --- 법무 표기 지속 실측 --------------------------------------------------
    def _scene_time(self):
        """지금까지 흐른 장면 시각(초). manim CE 0.20 의 renderer.time."""
        return float(getattr(self.renderer, "time", 0.0) or 0.0)

    def _live_ids(self):
        """무대에 올라 있는 모든 요소의 id 집합(자식까지) — 캡션은 Group 안에 들어 있어서
        self.mobjects(최상위)만 훑으면 '무대에 없다'고 오판한다."""
        live = set()
        for m in self.mobjects:
            try:
                live.update(id(x) for x in m.get_family())
            except Exception:  # noqa: BLE001
                live.add(id(m))
        return live

    _t_before = 0.0     # 직전 play/wait 가 시작된 장면 시각

    def _track_legal(self, live):
        """법무 표기 캡션이 **완전 불투명하게** 떠 있던 구간을 기록한다.

        counsel §9-4 의 자는 "완전 불투명 연속 표시"다. 등장 애니메이션(FadeIn)
        구간은 투명도가 0→100% 로 올라가는 중이므로 세지 않는다 — 감사 시점이
        애니메이션 '종료 직후'이므로, 처음 보인 감사 시각을 그대로 시작으로 잡으면
        자연히 페이드가 빠진다. 끝 시각도 마지막으로 보인 감사 시점(퇴장 페이드 제외).
        양쪽 다 **과소 계상 = 안전한 쪽**이다.
        (2026-07-30 실측으로 교정: 페이드 시작 시각을 쓰면 3편 seg10 이 6.07초로
        나오는데, 그 순간 프레임을 뽑아 보면 캡션 칸이 아직 흰 배경이었다(RGB 255).
        조립기가 스스로 낸 숫자를 픽셀이 반증한 사례 — 숫자를 픽셀에 맞췄다.)
        """
        if not LEGAL_CAPTIONS:
            return
        t = self._scene_time()
        for g in LEGAL_CAPTIONS:
            if id(g) in live:
                n = g.legal_note
                if n["first"] is None:
                    n["first"] = t
                n["last"] = t
                # 표기가 떠 있던 **모든 순간에 공통으로 덮고 있던 칸**(교집합)을 남긴다.
                # 켄 번즈로 캡션이 밀려도 이 칸은 창 내내 캡션이 차지한 자리이므로,
                # 렌더 후 프레임을 뽑아 "정말 떠 있었나"를 픽셀로 검산할 수 있다
                # (counsel §8-2 조건① 프레임 계수 검증의 좌표 근거).
                b = self.bbox(g)
                n["box"] = b if n.get("box") is None else (
                    max(n["box"][0], b[0]), min(n["box"][1], b[1]),
                    max(n["box"][2], b[2]), min(n["box"][3], b[3]))

    # 조립기 추정의 계통 오차 여유(초). 감사 시점이 애니메이션 경계뿐이라 앞뒤로
    # 최대 한 단계씩 놓친다 — 3편 seg10 실측: 추정 5.46초 vs **프레임 전수 계수 5.600초**
    # (0.14초 과소). 이 여유 없이 차단하면 멀쩡한 렌더가 0.04초 차로 막힌다.
    # 확정 판정은 언제나 verify_output_spec 의 프레임 계수이고, 여기 값은 사전 경보다.
    LEGAL_EST_SLACK = 0.25

    def legal_shortfalls(self):
        """표기 지속이 counsel 요구치에 못 미친 캡션 목록. (문구, 실측, 요구) 튜플."""
        out = []
        for g in LEGAL_CAPTIONS:
            n = g.legal_note
            if n["first"] is None or n["last"] is None:
                out.append((n["text"], 0.0, n["need"], "화면에 한 번도 안 뜸"))
                continue
            shown = n["last"] - n["first"]
            if shown + self.LEGAL_EST_SLACK < n["need"]:
                out.append((n["text"], shown, n["need"], "지속 미달"))
        return out

    @staticmethod
    def _contains(outer, inner, eps=0.01):
        """outer 상자가 inner 상자를 통째로 품고 있나."""
        return (outer[0] - eps <= inner[0] and inner[1] <= outer[1] + eps
                and outer[2] - eps <= inner[2] and inner[3] <= outer[3] + eps)

    def _live_zones(self, live):
        """지금 판정 대상인 구역만 골라 (이름, 상자, 구역) 로 돌려준다.

        track 이 달린 구역은 그 mobject 가 무대에 없으면 잠든다 — 사진이 사라진 뒤에도
        금줄이 남아 있으면 뒤 컷의 멀쩡한 배치를 결함으로 오보한다.
        """
        out = []
        for nm, z in (self._zones or {}).items():
            tr = z.get("track")
            if tr is not None and id(tr) not in live:
                continue
            out.append((nm, self._zone_box(z), z))
        return out

    def audit_layout(self):
        """지금 무대에 올라 있는 모든 요소를 상대로 두 불변식을 기계 판정한다."""
        if self._overflow is None:
            self._overflow, self._intrusion, self._crowding = {}, {}, {}
            self._zones_seen, self._seg_covered, self._advice = set(), set(), {}
        live = self._live_ids()
        self._track_legal(live)
        zones = self._live_zones(live)
        for nm, _box, _z in zones:
            self._zones_seen.add(nm)
        if zones:
            self._seg_covered.add(self._cur_seg)
        hw, hh = config.frame_width / 2, config.frame_height / 2
        for m in self.mobjects:
            if m is self.subtitle:
                continue
            try:
                l, r, b, t = self.bbox(m)
            except Exception:  # noqa: BLE001  (좌표를 못 내는 특수 mobject는 건너뜀)
                continue
            ox = max(0.0, -hw - l, r - hw)
            oy = max(0.0, -hh - b, t - hh)
            if max(ox, oy) > 0.02:
                k = self._describe(m)
                p = self._overflow.get(k, (0.0, 0.0))
                self._overflow[k] = (max(p[0], ox), max(p[1], oy))
            for nm, zbox, z in zones:
                if id(m) in z["owners"]:
                    continue
                hard = rect_overlap((l, r, b, t), zbox)
                if hard and z.get("kind") == "edge":
                    # 사진·스크린샷은 '테두리를 무는 것'만 결함이다. 완전히 안(의도한
                    # 겹쳐 찍기)이거나 완전히 바깥(정상)이면 넘어간다.
                    if self._contains(zbox, (l, r, b, t)) or \
                            self._contains((l, r, b, t), zbox):
                        continue
                if hard:
                    # 자동 등록 구역(상시 띠·사진)은 1~3편에서 '권고', 4편부터 '차단'.
                    # 두 장부를 분리해 두어야 경보가 무뎌지지 않는다.
                    auto = not z.get("enforce", True)
                    bucket = (self._intrusion
                              if (not auto or self._auto_zone_blocks())
                              else self._advice)
                    k = f"{self._describe(m)} ↔ {nm}"
                    p = bucket.get(k, (0.0, 0.0))
                    bucket[k] = (max(p[0], hard[0]), max(p[1], hard[1]))
                    continue
                if z.get("kind") == "edge":
                    continue          # 사진 바깥의 '근접'은 경고 대상이 아니다
                zl, zr, zb, zt = zbox
                pz = (zl - z["pad"], zr + z["pad"], zb - z["pad"], zt + z["pad"])
                soft = rect_overlap((l, r, b, t), pz)
                if soft:
                    k = f"{self._describe(m)} ↔ {nm}"
                    self._crowding[k] = max(self._crowding.get(k, 0.0), min(soft))

    def write_render_manifest(self):
        """이 렌더의 '사실 데이터'를 파일로 남긴다 — 사람의 기억·수기 목록을 대체한다.

        ①실사용 소재(파일명·md5·바이트·등장 구간) — 크레딧과 양방향 대조의 근거
        ②법무 표기(문구·요구/실측 지속·화면 좌표) — 렌더 후 프레임 계수 검산의 좌표
        읽는 쪽: verify_output_spec.py. 없으면 검사기가 '미확인'으로 낮춘다.
        """
        caps = []
        for g in LEGAL_CAPTIONS:
            n = g.legal_note
            box = n.get("box")
            frac = None
            if box:
                # 픽셀이 아니라 **화면 비율(0~1)** 로 남긴다. 시안(854x480)에서 잰
                # 좌표를 완성본(1920x1080)에 그대로 쓰면 엉뚱한 칸을 검사하게 된다 —
                # 비율로 두면 검사기가 그 mp4 의 실제 해상도에 맞춰 환산한다.
                fw, fh = config.frame_width, config.frame_height
                frac = [round((box[0] + fw / 2) / fw, 5),   # left
                        round((fh / 2 - box[3]) / fh, 5),   # top
                        round((box[1] + fw / 2) / fw, 5),   # right
                        round((fh / 2 - box[2]) / fh, 5)]   # bottom
            caps.append({"text": n["text"], "chars": n["chars"],
                         "need_sec": round(n["need"], 3),
                         "first_sec": None if n["first"] is None else round(n["first"], 3),
                         "last_sec": None if n["last"] is None else round(n["last"], 3),
                         "shown_sec": 0.0 if (n["first"] is None or n["last"] is None)
                         else round(n["last"] - n["first"], 3),
                         "legacy": n["legacy"], "box_frac": frac})
        data = {"ep": EP, "scene": type(self).__name__,
                "render": f"{config.pixel_width}x{config.pixel_height}"
                          f"@{config.frame_rate}fps",
                "full": FULL, "layout_audit_only": LAYOUT_AUDIT,
                "partial_render": not (FROM_ANIM is None and UPTO_ANIM is None),
                "assets": ASSET_USES, "legal_captions": caps}
        path = os.path.join(OUT, "_render_manifest.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print(f"[v2] 실사용 소재 {len(ASSET_USES)}건 · 법무 표기 {len(caps)}건 "
              f"→ {os.path.basename(path)}")
        return path

    def zone_coverage(self):
        """(구역이 하나라도 살아 있던 구간 수, 전체 구간 수).

        '등록 구역 N개'만으로는 어디를 봤는지 알 수 없다 — 3편은 3개였지만 전부
        아웃트로에 몰려 있어 애니메이션 0~140 구간은 무방비였다(2차 감사 지적).
        이 값이 전 구간을 덮어야 "전 구간 등록"이라 말할 수 있다.
        """
        total = len(TIMED) + 1          # 인트로 + 세그먼트들
        return len(self._seg_covered or set()), total

    def report_layout(self):
        """[audit] 줄 출력 — verify_output_spec.py 가 이 줄을 읽어 PASS/FAIL을 판정한다.
        (형식을 바꾸면 검사기의 정규식도 같이 고쳐야 한다: verify_output_spec.audit_lines)"""
        name = type(self).__name__
        ov = self._overflow or {}
        it = self._intrusion or {}
        cr = self._crowding or {}
        print(f"[audit] {name}: 프레임 이탈 {len(ov)}건")
        for k, (ox, oy) in sorted(ov.items(), key=lambda x: -max(x[1])):
            print(f"    - 이탈 {k}: 가로 +{ox:.2f} / 세로 +{oy:.2f}")
        # '등록 구역'은 **실제로 살아 있던 구역 수**를 센다 — 등록만 해두고 한 번도
        # 판정에 쓰이지 않은 구역을 세면 커버리지를 부풀린다(공허한 참의 변종).
        seen = self._zones_seen or set()
        blocking = sum(1 for nm in seen
                       if (self._zones or {}).get(nm, {}).get("enforce", True))
        cov, tot = self.zone_coverage()
        strict = "차단" if self._auto_zone_blocks() else "권고"
        print(f"[audit] {name}: 보호영역 침범 {len(it)}건 "
              f"(등록 구역 {len(seen)}개[명시 {blocking}·자동 {len(seen) - blocking}"
              f"={strict}], 구간 커버리지 {cov}/{tot})")
        for k, (ox, oy) in sorted(it.items(), key=lambda x: -min(x[1])):
            print(f"    - 침범 {k}: 겹침 가로 {ox:.2f} / 세로 {oy:.2f}")
        if cov < tot:
            missing = [s for s in (["intro"] + list(range(len(TIMED))))
                       if s not in (self._seg_covered or set())]
            print(f"    - 구역 미등록 구간 {len(missing)}개: {missing}")
        # 권고 장부 — 1~3편의 자동 구역 위반. 차단하지 않지만 **반드시 보이게** 남긴다
        # (안 보이면 없는 것과 같다 — 이번 과업의 출발점이 바로 그 교훈이다).
        ad = self._advice or {}
        print(f"[audit] {name}: 표시영역 권고 위반 {len(ad)}건 "
              f"({EpisodeBase.ZONE_STRICT_FROM_EP}편부터 차단)")
        for k, (ox, oy) in sorted(ad.items(), key=lambda x: -min(x[1])):
            print(f"    - 권고 {k}: 겹침 가로 {ox:.2f} / 세로 {oy:.2f}")
        if cr:
            print(f"[audit] {name}: 여유 침범(경고) {len(cr)}건 — 겹치진 않으나 "
                  f"최소 여유 {self.LAYOUT_MARGIN} 미달")
            for k, v in sorted(cr.items(), key=lambda x: -x[1]):
                print(f"    - 근접 {k}: 여유 잔량 {self.LAYOUT_MARGIN - v:.2f}")
        # 법무 표기(재현 화면·크레딧) 지속 실측 — counsel §9-4. 상한(20자)만으로는
        # 부족하다: 20자여도 3.33초 미만으로 띄우면 위반이므로 출력을 함께 잰다.
        short = self.legal_shortfalls()
        print(f"[audit] {name}: 법무 표기 지속 미달 {len(short)}건 "
              f"(표기 {len(LEGAL_CAPTIONS)}건, 상한 {LEGAL_CAPTION_MAX}자)")
        for g in LEGAL_CAPTIONS:
            n = g.legal_note
            shown = 0.0 if (n["first"] is None or n["last"] is None) else n["last"] - n["first"]
            flag = "레거시 예외" if n["legacy"] else "규격"
            mark = ("미달" if shown + self.LEGAL_EST_SLACK < n["need"]
                    else ("여유 적음" if shown + 1e-6 < n["need"] else "OK"))
            print(f"    - 표기 「{n['text']}」 {n['chars']}자 [{flag}]: "
                  f"추정 하한 {shown:.2f}초 / 요구 {n['need']:.2f}초 ({mark})")
        print(f"    ※ 위 '추정 하한'은 애니메이션 경계에서만 재는 값이라 실제보다 "
              f"최대 {self.LEGAL_EST_SLACK}초 짧게 나온다. **확정 판정은 완성본 프레임 "
              f"전수 계수**(verify_output_spec.py '재현 표기' 행).")

    def play(self, *a, **kw):
        self._t_before = self._scene_time()
        super().play(*a, **kw)
        self.audit_layout()

    def wait(self, *a, **kw):
        self._t_before = self._scene_time()
        super().wait(*a, **kw)
        self.audit_layout()

    # --- 아웃트로 CTA(구독·좋아요) — 자리 예약과 실제 버튼이 같은 출처를 쓴다 -------
    # 예약(예고 부제를 배치하는 컷)과 생성(버튼이 뜨는 컷)이 서로 다른 좌표를 쓰면
    # 예약이 거짓말이 된다. 그래서 좌표를 편별 CTA 스펙 한 곳에만 둔다.
    CTA = None   # dict(pos=, w=, h=, buff=, like=bool, fs=(구독,좋아요), cc=코너, cc_shift=)

    def cc_badge(self):
        """아웃트로 © 배지 — 위치를 CTA 스펙 한 곳에서 가져온다(자리 예약과 동일 출처)."""
        spec = self.CTA or {}
        cc = Text("© nous-zero", font=KFONT, font_size=22, color=LGRAY)
        cc.to_corner(spec.get("cc", DR), buff=0.4)
        if spec.get("cc_shift") is not None:
            cc.shift(spec["cc_shift"])
        return cc

    def cta_group(self):
        spec = self.CTA
        sub_box = RoundedRectangle(corner_radius=0.3, width=spec["w"], height=spec["h"])
        sub_box.set_stroke(width=0).set_fill(RED, 1)
        sub_t = ktext("구독", spec["fs"][0], WHITE, bold=True).move_to(sub_box)
        sub_btn = VGroup(sub_box, sub_t).move_to(spec["pos"])
        parts = [sub_btn]
        if spec.get("like"):
            like_box = RoundedRectangle(corner_radius=0.3, width=spec["w"], height=spec["h"])
            like_box.set_stroke(BLUE, 4).set_fill(WHITE, 1)
            like_t = ktext("좋아요", spec["fs"][1], BLUE, bold=True).move_to(like_box)
            parts.append(VGroup(like_box, like_t).next_to(sub_btn, DOWN,
                                                          buff=spec.get("buff", 0.25)))
        grp = VGroup(*parts)
        self.fit_frame(grp)   # 프레임 이탈 방어(3편 좋아요 6.7px 잘림 재발 방지)
        return grp, parts

    CTA_ZONE = "CTA(구독·좋아요)"
    CC_ZONE = "© 배지"

    def reserve_cta(self):
        """CTA 버튼·© 배지가 앉을 자리를 미리 금줄 친다 — 이들보다 먼저 그려지는 요소용.
        아웃트로는 예고 문구(먼저)와 CTA·©(나중)가 다른 컷에서 생기므로, 예약 없이는
        저자도 검사기도 겹침을 볼 수 없다 — 3편 결함이 발행 직전까지 살아남은 이유."""
        ghost, _ = self.cta_group()
        a = self.reserve_zone(self.CTA_ZONE, ghost)
        b = self.reserve_zone(self.CC_ZONE, self.cc_badge())
        return a, b

    def show_cta(self, d):
        """아웃트로 CTA 등장 — 1·2·3편 공통 문법."""
        grp, parts = self.cta_group()
        cc = self.cc_badge()
        for nm, owners in ((self.CTA_ZONE, [grp, *parts]), (self.CC_ZONE, [cc])):
            if nm in (self._zones or {}):
                self.claim_zone(nm, *owners)
            else:
                self.reserve_zone(nm, owners[0], owners=owners)
        # CTA 버튼·© 배지는 하단 띠의 '정식 거주자'다(v2 확정 문법). 신고해 두지 않으면
        # 상시 구역(자막·하단 UI)이 이들을 침범으로 오보한다 — 감사 장부만 바뀌고
        # 화면은 그대로다.
        self.claim_bottom(grp, cc, *parts)
        t1 = max(0.4, min(0.9, d * 0.35))
        self.play(*[FadeIn(p, scale=1.5 if i == 0 else 1.3) for i, p in enumerate(parts)],
                  run_time=t1)
        t2 = max(0.3, min(0.5, d * 0.2))
        self.play(Indicate(parts[0], color=RED, scale_factor=1.12), FadeIn(cc), run_time=t2)
        self.hold(d - t1 - t2)
        return grp

    # --- 공통 도우미 ---
    def sub(self, txt):
        if not BURN_SUB:
            return
        t = Text(txt, font=KFONT, font_size=30, color=INK)
        if t.width > 12.8:
            t.scale_to_fit_width(12.8)
        t.to_edge(DOWN, buff=0.32)
        if self.subtitle:
            self.remove(self.subtitle)
        self.add(t)
        self.subtitle = t

    def act(self, d, *anims, rt=None):
        if anims:
            rt = rt if rt is not None else min(1.4, d * 0.6)
            rt = max(0.3, min(rt, d))
            self.play(*anims, run_time=rt)
            d -= rt
        if d > 2.0 / config.frame_rate:
            self.wait(d)

    def hold(self, d):
        if d > 2.0 / config.frame_rate:
            self.wait(d)

    def clear_stage(self, rt):
        ms = [m for m in self.mobjects if m is not self.subtitle]
        if ms:
            self.play(*[FadeOut(m) for m in ms], run_time=rt)
        else:
            self.wait(rt)

    # --- 실사 사료 도우미 (하이브리드 v3) ---
    def photo(self, fname, height=5.4, pos=ORIGIN, framed=True):
        """흰 테두리 액자에 담긴 실사 사진. Group 반환(사진, [테두리]).

        만들어지는 즉시 '테두리를 물면 안 되는 구역'으로 자동 등록된다(과업 ③).
        구역은 사진을 따라다니므로 켄 번즈로 커지고 밀려도 금줄이 같이 움직인다.
        """
        path = os.path.join(ASSETS, fname)
        record_asset_use(path, self._cur_seg)   # 실사용 소재 대장(크레딧 양방향 대조용)
        img = ImageMobject(path)
        img.height = height
        img.move_to(pos)
        grp = Group(img, self._photo_border(img)) if framed else Group(img)
        self._register_photo_zone(grp, fname)
        return grp

    @staticmethod
    def _photo_border(img):
        border = Rectangle(width=img.width + 0.1, height=img.height + 0.1)
        # 흰 배경에서도 보이는 잉크색 액자
        border.set_stroke(INK, 4).set_fill(None, 0).move_to(img)
        return border

    def _register_photo_zone(self, grp, label):
        """사진 1장 = 보호영역 1개(kind='edge'). 무대에 오르는 동안에만 살아 있다."""
        type(self)._photo_n += 1
        nm = f"{self.PHOTO_ZONE_PREFIX} {type(self)._photo_n}: {label}"
        self.reserve_zone(nm, grp, pad=0.0, owners=[grp], kind="edge",
                          enforce=False, track=grp)
        return nm

    def fit_frame(self, m, margin=0.15):
        """프레임(화면) 밖으로 삐져나간 요소를 안쪽으로 밀어 넣는다 — 본편 프레임 이탈 방어.

        쉬운 말: 액자 밖으로 걸친 도형을 '액자 안으로 밀어 넣는' 안전장치.
        쇼츠에는 이미 keep_in() 같은 장치가 있었으나 본편에는 없어서, 3편 아웃트로의
        '좋아요' 버튼이 화면 아래로 6.7px 잘려 나갔다(2026-07-30 release-director 실측).
        같은 부류를 사람 눈이 두 번 잡지 않도록 기계 장치로 승격한다(rule5-4).
        """
        half_w = config.frame_width / 2 - margin
        half_h = config.frame_height / 2 - margin
        dx = dy = 0.0
        if m.get_bottom()[1] < -half_h:
            dy = -half_h - m.get_bottom()[1]
        elif m.get_top()[1] > half_h:
            dy = half_h - m.get_top()[1]
        if m.get_left()[0] < -half_w:
            dx = -half_w - m.get_left()[0]
        elif m.get_right()[0] > half_w:
            dx = half_w - m.get_right()[0]
        if dx or dy:
            m.shift(RIGHT * dx + UP * dy)
        return m

    def show_photo(self, grp, d_in=0.8):
        self.play(FadeIn(grp, scale=1.04), run_time=max(0.3, d_in))
        if self.subtitle:  # 자막이 사진에 가려지지 않게 맨 위로
            self.remove(self.subtitle)
            self.add(self.subtitle)

    def ken_burns(self, grp, d, zoom=1.06, drift=None):
        """느린 줌/팬 — 정지 사진에 생명을 주는 다큐 문법.
        액자째 함께 키운다(사진만 키우면 테두리를 삐져나옴)."""
        if d <= 2.0 / config.frame_rate:
            return
        if drift is not None:
            move = grp.animate.scale(zoom).shift(drift)
        else:
            move = grp.animate.scale(zoom)
        self.play(move, run_time=d, rate_func=linear)

    def run_beats(self, S, acts):
        for i, (txt, d) in enumerate(S):
            self.sub(txt)
            if i < len(acts) and acts[i]:
                acts[i](d)
            else:
                self.hold(d)


class Episode01(EpisodeBase):
    CLEAR_AFTER = {2, 3, 5, 6, 7, 8, 9, 11, 12, 13}
    CTA = {"pos": RIGHT * 2.8 + DOWN * 0.9, "w": 2.6, "h": 0.85,
           "like": False, "fs": (40, 34), "cc": DR, "cc_shift": UP * 0.55}

    # --- 인트로 ---
    def intro(self):
        title = mtext("ARPANET", fs=110, color=INK).move_to(UP * 0.9)
        sub = ktext("핵전쟁이 만든 인터넷의 시작", fs=40, color=GRAY).next_to(title, DOWN, buff=0.5)
        num = chip("#01", BLUE, 30).to_corner(UL, buff=0.6)
        cc = Text("© nous-zero", font=KFONT, font_size=22, color=LGRAY).to_corner(DR, buff=0.45)
        self.claim_bottom(cc)   # 하단 띠의 정식 거주자 신고(감사 장부만 변경 — 화면 불변)
        self.play(FadeIn(title, scale=1.15), FadeIn(num), run_time=0.9)
        self.play(FadeIn(sub, shift=UP * 0.2), FadeIn(cc), run_time=0.7)
        self.wait(INTRO_D - 0.9 - 0.7 - 0.6)
        self.play(*[FadeOut(m) for m in (title, sub, num, cc)], run_time=0.6)

    # --- 0~2: 터미널 / LO ---
    def terminal_win(self):
        win = RoundedRectangle(corner_radius=0.25, width=9.6, height=4.8)
        win.set_stroke(INK, 4).set_fill(PAPER, 1).move_to(UP * 0.5)
        dots = VGroup(*[Dot(radius=0.07, color=LGRAY) for _ in range(3)])
        dots.arrange(RIGHT, buff=0.18)
        dots.move_to(win.get_corner(UL) + RIGHT * 0.6 + DOWN * 0.33)
        bar = Line(win.get_corner(UL) + DOWN * 0.62, win.get_corner(UR) + DOWN * 0.62)
        bar.set_stroke(LGRAY, 2)
        return VGroup(win, dots, bar)

    def seg00(self, S):
        term = self.terminal_win()
        prompt = mtext(">", fs=44, color=GRAY)
        prompt.move_to(term[0].get_corner(UL) + RIGHT * 0.65 + DOWN * 1.35)
        self.st["term"] = term
        self.st["prompt"] = prompt

        def a0(d):
            self.act(d, Create(term), FadeIn(prompt), rt=min(1.6, d * 0.7))

        def a1(d):
            hello = mtext("HELLO", fs=54, color=GRAY).next_to(prompt, RIGHT, buff=0.35)
            strike = Line(hello.get_left() + LEFT * 0.1, hello.get_right() + RIGHT * 0.1)
            strike.set_stroke(RED, 6)
            t1 = max(0.3, min(0.8, d * 0.35))
            self.play(FadeIn(hello), run_time=t1)
            t2 = max(0.3, min(0.5, d * 0.25))
            self.play(Create(strike), run_time=t2)
            self.st["hello"] = VGroup(hello, strike)
            self.hold(d - t1 - t2)

        def a2(d):
            lo = mtext("LO", fs=120, color=BLUE).move_to(self.st["term"][0].get_center() + DOWN * 0.35)
            self.st["lo"] = lo
            t1 = max(0.4, min(1.0, d * 0.4))
            self.play(FadeIn(lo, scale=1.5), run_time=t1)
            self.play(Flash(lo.get_center(), color=BLUE, flash_radius=1.6), run_time=min(0.6, max(0.3, d * 0.2)))
            self.hold(d - t1 - min(0.6, max(0.3, d * 0.2)))

        self.run_beats(S, [a0, a1, a2])

    def seg01(self, S):
        def a0(d):
            date = chip("1969.10.29", INK, 28).to_corner(UL, buff=0.5)
            self.st["date"] = date
            outs = []
            if "hello" in self.st:
                outs.append(FadeOut(self.st["hello"]))
            if "lo" in self.st:
                outs.append(self.st["lo"].animate.scale(0.4).move_to(
                    self.st["term"][0].get_corner(UR) + LEFT * 0.9 + DOWN * 1.05))
            self.act(d, FadeIn(date, shift=DOWN * 0.2), *outs)

        def a1(d):
            win = self.st["term"][0]
            y = win.get_bottom()[1] + 0.75
            a = Dot(P3((-3.2, y)), radius=0.16, color=BLUE)
            b = Dot(P3((3.2, y)), radius=0.16, color=INK)
            la = ktext("UCLA", 24, GRAY).next_to(a, DOWN, buff=0.18)
            lb = ktext("스탠퍼드", 24, GRAY).next_to(b, DOWN, buff=0.18)
            link = Line(a.get_center(), b.get_center(), buff=0.2).set_stroke(LGRAY, 3)
            pkt = Dot(a.get_center(), radius=0.1, color=BLUE)
            self.st["route"] = VGroup(a, b, la, lb, link, pkt)
            t1 = max(0.4, min(1.0, d * 0.4))
            self.play(FadeIn(a), FadeIn(b), FadeIn(la), FadeIn(lb), Create(link), run_time=t1)
            t2 = max(0.4, min(1.2, d * 0.35))
            self.play(MoveAlongPath(pkt, Line(a.get_center(), b.get_center())), run_time=t2)
            self.hold(d - t1 - t2)

        def a2(d):
            boxes = VGroup()
            for i, ch in enumerate("LOGIN"):
                sq = RoundedRectangle(corner_radius=0.1, width=1.0, height=1.0)
                sq.set_stroke(LGRAY, 3).set_fill(WHITE, 1)
                letter = mtext(ch, fs=52, color=GRAY)
                letter.move_to(sq)
                boxes.add(VGroup(sq, letter))
            boxes.arrange(RIGHT, buff=0.28)
            boxes.move_to(self.st["term"][0].get_center() + UP * 0.35)
            self.st["login"] = boxes
            lo_out = [FadeOut(self.st["lo"])] if "lo" in self.st else []
            if lo_out:
                del self.st["lo"]
            self.act(d, LaggedStart(*[FadeIn(b, scale=1.2) for b in boxes], lag_ratio=0.15), *lo_out,
                     rt=min(1.6, d * 0.6))

        self.run_beats(S, [a0, a1, a2])

    def seg02(self, S):
        def a0(d):
            boxes = self.st["login"]
            win = self.st["term"][0]
            steps = []
            for i in (0, 1):  # L, O 점등
                steps.append((boxes[i][0].animate.set_stroke(BLUE, 5).set_fill("#DBEAFE", 1),
                              boxes[i][1].animate.set_color(BLUE)))
            t_each = max(0.35, min(0.8, d * 0.18))
            for pair in steps:
                self.play(*pair, run_time=t_each)
            xmark = VGroup(
                Line(UL * 0.5, DR * 0.5), Line(UR * 0.5, DL * 0.5)
            ).set_stroke(RED, 10).move_to(win.get_corner(UR) + LEFT * 1.2 + DOWN * 1.2)
            t3 = max(0.4, min(1.0, d * 0.3))
            self.play(Wiggle(self.st["term"], scale_value=1.02),
                      FadeIn(xmark, scale=1.4),
                      *[boxes[i][1].animate.set_color(LGRAY) for i in (2, 3, 4)],
                      run_time=t3)
            self.st["xmark"] = xmark
            self.hold(d - 2 * t_each - t3)

        def a1(d):
            # 실사 전환: 재연 화면을 걷어내고 1969년 실제 로그 노트를 보여준다
            outs = []
            for k in ("term", "prompt", "login", "xmark", "route"):
                if k in self.st:
                    outs.append(FadeOut(self.st.pop(k)))
            ph = self.photo("imp_log.jpg", height=4.6, pos=DOWN * 0.15)
            cap = chip("1969.10.29 — UCLA 실제 기록", INK, 24).next_to(ph, UP, buff=0.3)
            self.st["logph"] = ph
            t1 = max(0.3, min(0.7, d * 0.25))
            self.play(*outs, run_time=t1)
            self.show_photo(ph, 0.6)
            self.play(FadeIn(cap), run_time=0.3)
            self.ken_burns(ph, d - t1 - 0.9, zoom=1.07)

        def a2(d):
            ph = self.st["logph"]
            hl = RoundedRectangle(corner_radius=0.08, width=3.6, height=0.66)
            hl.set_fill(AMBER, 0.4).set_stroke(AMBER, 3)
            hl.move_to(ph[0].get_center() + UP * 0.2)
            t1 = max(0.3, min(0.8, d * 0.4))
            self.play(FadeIn(hl, scale=1.2), run_time=t1)
            self.hold(d - t1)

        self.run_beats(S, [a0, a1, a2])

    # --- 3: 냉전 ---
    def seg03(self, S):
        def a0(d):
            why = ktext("왜?", fs=96, color=INK, bold=True)
            self.st["why"] = why
            self.act(d, FadeIn(why, scale=1.5))

        def a1(d):
            # 실사 전환: 냉전의 무게는 실제 핵실험 기록 사진으로
            ph = self.photo("baker.jpg", height=5.8, pos=UP * 0.35, framed=False)
            cold = chip("냉전 시대", INK, 30).to_corner(UL, buff=0.5)
            cap = chip("1946 크로스로즈 핵실험 — 미 해군 기록", GRAY, 20).to_edge(DOWN, buff=1.05)
            t1 = max(0.3, min(0.7, d * 0.25))
            self.play(FadeOut(self.st.pop("why")), run_time=0.3)
            self.show_photo(ph, t1)
            self.play(FadeIn(cold), FadeIn(cap), run_time=0.4)
            self.ken_burns(ph, d - t1 - 0.7, zoom=1.07)

        self.run_beats(S, [a0, a1])

    # --- 4~5: 별 모양 → 붕괴 ---
    def seg04(self, S):
        def a0(d):
            # 실사: 냉전 미사일의 실체 — 1975년 타이탄II 발사 기록
            ph = self.photo("titan.jpg", height=5.8, pos=RIGHT * 3.6 + UP * 0.25)
            cap = chip("1975 타이탄II — 미 공군 기록", GRAY, 19).next_to(ph, DOWN, buff=0.22)
            self.st["titan"] = Group(ph, cap)
            t1 = max(0.3, min(0.7, d * 0.3))
            self.show_photo(ph, t1)
            self.play(FadeIn(cap), run_time=0.3)
            self.ken_burns(ph, d - t1 - 0.3, zoom=1.06, drift=UP * 0.12)

        def a1(d):
            outs = [FadeOut(self.st.pop("titan"))]
            center = Circle(radius=0.4).set_stroke(BLUE, 5).set_fill("#DBEAFE", 1).move_to(UP * 0.4)
            clab = ktext("교환국", 24, GRAY).next_to(center, DOWN, buff=0.22)
            outer, spokes = VGroup(), VGroup()
            import math
            for i in range(8):
                ang = i * PI / 4
                p = P3((3.1 * math.cos(ang), 0.4 + 2.15 * math.sin(ang)))
                dot = Dot(p, radius=0.14, color=INK)
                outer.add(dot)
                spokes.add(Line(center.get_center(), p, buff=0.3).set_stroke(LGRAY, 3))
            self.st["star"] = VGroup(spokes, outer, center, clab)
            t1 = max(0.6, min(2.0, d * 0.55))
            self.play(*outs, Create(center), FadeIn(clab),
                      LaggedStart(*[Create(s) for s in spokes], lag_ratio=0.08),
                      LaggedStart(*[FadeIn(o) for o in outer], lag_ratio=0.08),
                      run_time=t1)
            m = missile(1.2).move_to(UP * 3.4 + RIGHT * 0.2)
            self.st["missile"] = m
            t2 = max(0.3, min(0.8, d * 0.2))
            self.play(FadeIn(m, shift=DOWN * 0.4), run_time=t2)
            self.hold(d - t1 - t2)

        def a2(d):
            star = self.st["star"]
            tag = chip("별 모양 구조", INK, 30).to_corner(UR, buff=0.5)
            self.st["startag"] = tag
            self.act(d, FadeIn(tag), Indicate(star[2], color=BLUE))

        self.run_beats(S, [a0, a1, a2])

    def seg05(self, S):
        def a0(d):
            star = self.st["star"]
            spokes, outer, center, clab = star
            m = self.st.pop("missile")
            t1 = max(0.3, min(0.7, d * 0.25))
            self.play(m.animate.move_to(center.get_center()), run_time=t1)
            broken = VGroup(*[DashedLine(s.get_start(), s.get_end()).set_stroke(LGRAY, 2)
                              for s in spokes])
            t2 = max(0.4, min(1.0, d * 0.35))
            self.play(FadeOut(m),
                      Flash(center.get_center(), color=RED, flash_radius=1.2),
                      center.animate.set_fill(RED, 1).set_stroke(RED, 5),
                      Transform(spokes, broken),
                      *[o.animate.set_color(LGRAY) for o in outer],
                      run_time=t2)
            self.hold(d - t1 - t2)

        def a1(d):
            grp = VGroup(self.st["star"], self.st["startag"])
            self.act(d, grp.animate.set_opacity(0.25))

        def a2(d):
            phrase = ktext("심장이 없는 통신망", fs=64, color=INK, bold=True)
            ul = Underline(phrase, color=BLUE).set_stroke(BLUE, 8)
            self.act(d, FadeIn(phrase, scale=1.2), Create(ul), rt=min(1.2, d * 0.6))

        self.run_beats(S, [a0, a1, a2])

    # --- 6: 그물망 ---
    def seg06(self, S):
        def a0(d):
            nodes, edges, pts = build_mesh(0.95, (0, 0.1))
            self.st["mesh"] = (nodes, edges, pts)
            self.act(d, LaggedStart(*[FadeIn(n, scale=1.3) for n in nodes], lag_ratio=0.05),
                     LaggedStart(*[Create(e) for e in edges], lag_ratio=0.04),
                     rt=min(2.2, d * 0.75))

        def a1(d):
            _, edges, _ = self.st["mesh"]
            self.act(d, Indicate(edges, color=BLUE, scale_factor=1.0))

        def a2(d):
            nodes, edges, pts = self.st["mesh"]
            cut_i = MESH_E.index((6, 7))
            cut = edges[cut_i]
            broken = DashedVMobject(Line(cut.get_start(), cut.get_end()), num_dashes=7)
            broken.set_stroke(RED, 4)
            t1 = max(0.35, min(0.8, d * 0.3))
            self.play(Transform(cut, broken), run_time=t1)
            alt = [edges[MESH_E.index(p)] for p in ((6, 10), (7, 10))]
            t2 = max(0.4, min(1.0, d * 0.35))
            self.play(*[e.animate.set_stroke(BLUE, 7) for e in alt], run_time=t2)
            self.hold(d - t1 - t2)

        self.run_beats(S, [a0, a1, a2])

    # --- 7: 패킷 ---
    def seg07(self, S):
        def a0(d):
            block = RoundedRectangle(corner_radius=0.2, width=3.4, height=2.1)
            block.set_stroke(BLUE, 5).set_fill("#DBEAFE", 0.7).move_to(UP * 0.5)
            blab = ktext("데이터", 32, INK, bold=True).move_to(block)
            whole = VGroup(block, blab)
            t1 = max(0.35, min(0.9, d * 0.3))
            self.play(FadeIn(whole, scale=1.15), run_time=t1)
            pieces = VGroup()
            for _ in range(4):
                sq = RoundedRectangle(corner_radius=0.12, width=1.15, height=1.15)
                sq.set_stroke(BLUE, 4).set_fill("#DBEAFE", 0.7)
                pieces.add(sq)
            pieces.arrange(RIGHT, buff=0.55).move_to(UP * 0.5)
            t2 = max(0.4, min(1.0, d * 0.3))
            self.play(ReplacementTransform(whole, pieces), run_time=t2)
            tags = VGroup(*[chip("주소", RED, 16).scale(0.9).move_to(
                p.get_corner(UR) + UP * 0.18 + RIGHT * 0.1) for p in pieces])
            t3 = max(0.35, min(0.9, d * 0.25))
            self.play(LaggedStart(*[FadeIn(t, shift=DOWN * 0.15) for t in tags],
                                  lag_ratio=0.15), run_time=t3)
            self.st["pieces"] = pieces
            self.st["tags"] = tags
            self.hold(d - t1 - t2 - t3)

        def a1(d):
            name = chip("패킷", BLUE, 36).next_to(self.st["pieces"], UP, buff=0.8)
            self.act(d, FadeIn(name, scale=1.3))

        def a2(d):
            self.act(d, Wiggle(self.st["tags"], scale_value=1.2))

        self.run_beats(S, [a0, a1, a2])

    # --- 8: 패킷 여행 ---
    def seg08(self, S):
        def a0(d):
            nodes, edges, pts = build_mesh(0.85, (0, 0.15), square=True)
            self.st["mesh8"] = (nodes, edges, pts)
            self.act(d, LaggedStart(*[FadeIn(n) for n in nodes], lag_ratio=0.04),
                     LaggedStart(*[Create(e) for e in edges], lag_ratio=0.03),
                     rt=min(1.8, d * 0.65))

        def a1(d):
            nodes, edges, pts = self.st["mesh8"]
            pkt = Dot(pts[0], radius=0.13, color=BLUE)
            self.st["pkt"] = pkt
            path = VMobject().set_points_as_corners([pts[0], pts[5], pts[6]])
            t1 = max(0.3, min(0.6, d * 0.2))
            self.play(FadeIn(pkt, scale=1.5), run_time=t1)
            t2 = max(0.5, min(1.6, d * 0.5))
            self.play(MoveAlongPath(pkt, path), run_time=t2)
            self.hold(d - t1 - t2)

        def a2(d):
            nodes, edges, pts = self.st["mesh8"]
            dead = nodes[7]
            x = VGroup(Line(UL * 0.28, DR * 0.28), Line(UR * 0.28, DL * 0.28))
            x.set_stroke(RED, 7).move_to(dead)
            self.act(d, dead.animate.set_stroke(LGRAY, 3), FadeIn(x, scale=1.4))

        def a3(d):
            nodes, edges, pts = self.st["mesh8"]
            pkt = self.st["pkt"]
            alt = [edges[MESH_E.index(p)] for p in ((6, 10), (10, 11), (8, 11), (4, 8))]
            path = VMobject().set_points_as_corners([pts[6], pts[10], pts[11], pts[8], pts[4]])
            t1 = max(0.3, min(0.7, d * 0.25))
            self.play(*[e.animate.set_stroke(BLUE, 6) for e in alt], run_time=t1)
            t2 = max(0.6, min(2.0, d * 0.5))
            self.play(MoveAlongPath(pkt, path), run_time=t2)
            self.hold(d - t1 - t2)

        self.run_beats(S, [a0, a1, a2, a3])

    # --- 9: IMP → 라우터 ---
    def seg09(self, S):
        def a0(d):
            # 실사: "비유가 아니라 실물" — IMP 전면 패널 사진
            ph = self.photo("imp_panel.jpg", height=4.4, pos=LEFT * 3.0 + UP * 0.3)
            tag = chip("IMP — 실물", BLUE, 24).next_to(ph, UP, buff=0.28)
            self.st["imp"] = ph
            self.st["imptag"] = tag
            t1 = max(0.3, min(0.7, d * 0.3))
            self.show_photo(ph, t1)
            self.play(FadeIn(tag), run_time=0.3)
            self.ken_burns(ph, d - t1 - 0.3, zoom=1.05)

        def a1(d):
            size = chip("냉장고 크기", INK, 26).next_to(self.st["imp"], DOWN, buff=0.3)
            self.st["impsize"] = size
            self.act(d, FadeIn(size))

        def a2(d):
            arrow = Arrow(RIGHT * 0.7 + UP * 0.2, RIGHT * 1.9 + UP * 0.2, color=GRAY, stroke_width=6)
            box = RoundedRectangle(corner_radius=0.12, width=1.8, height=0.55)
            box.set_stroke(BLUE, 5).set_fill("#DBEAFE", 1).move_to(RIGHT * 3.5 + UP * 0.1)
            ant = VGroup(
                Line(box.get_top() + LEFT * 0.45, box.get_top() + LEFT * 0.45 + UP * 0.55),
                Line(box.get_top() + RIGHT * 0.45, box.get_top() + RIGHT * 0.45 + UP * 0.55),
            ).set_stroke(BLUE, 5)
            rlab = ktext("라우터", 28, GRAY).next_to(box, DOWN, buff=0.3)
            now = chip("지금의 공유기", BLUE, 26).next_to(box, UP, buff=0.9)
            self.act(d, Create(arrow), FadeIn(VGroup(box, ant, rlab), scale=1.2),
                     FadeIn(now, shift=DOWN * 0.2), rt=min(1.6, d * 0.6))

        self.run_beats(S, [a0, a1, a2])

    # --- 10: 그물의 한계 = 보험 ---
    def seg10(self, S):
        def a0(d):
            nodes, edges, pts = build_mesh(0.55, (0, 0.3))
            self.st["mesh10"] = VGroup(edges, nodes)
            self.act(d, FadeIn(nodes), Create(edges), rt=min(1.4, d * 0.6))

        def a1(d):
            import math
            ms = VGroup()
            for i in range(6):
                ang = PI / 6 + i * PI / 3
                p = P3((4.3 * math.cos(ang), 0.3 + 2.9 * math.sin(ang)))
                mm = missile(1.0).move_to(p)
                mm.rotate(ang - PI / 2)  # 그물 중심을 향하게
                ms.add(mm)
            self.st["missiles"] = ms
            self.act(d, LaggedStart(*[FadeIn(m, scale=1.3) for m in ms], lag_ratio=0.12),
                     rt=min(1.6, d * 0.6))

        def a2(d):
            tag = chip("보험", BLUE, 40).to_corner(UR, buff=0.6)
            self.st["ins"] = tag
            self.act(d, FadeIn(tag, scale=1.4))

        self.run_beats(S, [a0, a1, a2])

    # --- 11: 통가 ---
    def seg11(self, S):
        def a0(d):
            date = chip("2022", INK, 28).to_corner(UL, buff=0.5)
            anims = [FadeIn(date, shift=DOWN * 0.2)]
            if "missiles" in self.st:
                anims.append(FadeOut(self.st.pop("missiles")))
            if "ins" in self.st:
                anims.append(FadeOut(self.st.pop("ins")))
            if "mesh10" in self.st:
                anims.append(self.st["mesh10"].animate.scale(0.85).shift(LEFT * 2.4))
            self.act(d, *anims)

        def a1(d):
            # 실사: 2022 통가 폭발 — NOAA 위성 실영상(프레임 넘기기)
            _paths = [os.path.join(ASSETS, f"tonga_f{i}.png") for i in range(9)]
            for _p in _paths:                       # 실사용 소재 대장 기록(photo() 밖 경로)
                record_asset_use(_p, self._cur_seg)
            frames = [ImageMobject(p) for p in _paths]
            for f in frames:
                f.height = 3.5
                f.move_to(RIGHT * 4.15 + UP * 0.45)
            border = Rectangle(width=frames[0].width + 0.1, height=frames[0].height + 0.1)
            border.set_stroke(INK, 4).move_to(frames[0])
            lab = chip("통가 — NOAA 위성 실영상", INK, 20).next_to(border, DOWN, buff=0.25)
            cable = Line(LEFT * 0.5 + UP * 0.3, border.get_left() + LEFT * 0.05, buff=0.1).set_stroke(LGRAY, 4)
            t1 = max(0.4, min(0.9, d * 0.25))
            self.add(frames[0])
            if self.subtitle:
                self.remove(self.subtitle)
                self.add(self.subtitle)
            self.play(FadeIn(border), FadeIn(lab), Create(cable), run_time=t1)
            broken = DashedVMobject(Line(cable.get_start(), cable.get_end()), num_dashes=8)
            broken.set_stroke(RED, 4)
            wk = chip("5주 고립", RED, 30).next_to(border, UP, buff=0.28)
            t2 = max(0.3, min(0.8, d * 0.2))
            self.play(Transform(cable, broken), FadeIn(wk, scale=1.2), run_time=t2)
            rest, cur, step = d - t1 - t2, 0, 0.24
            while rest > step:
                self.remove(frames[cur])
                cur = (cur + 1) % 9
                self.add(frames[cur])
                if self.subtitle:
                    self.remove(self.subtitle)
                    self.add(self.subtitle)
                self.wait(step)
                rest -= step
            if rest > 2.0 / config.frame_rate:
                self.wait(rest)
            self.st["sat_border"] = border

        def a2(d):
            self.act(d, Indicate(self.st["sat_border"], color=RED, scale_factor=1.05))

        self.run_beats(S, [a0, a1, a2])

    # --- 12: 법칙 ---
    def seg12(self, S):
        # 주의: "정리할게요."(6자)는 다음 문장과 병합되므로 문장은 3개 —
        # [사슬 그리기, 유지, 법칙 팝] 순으로 매핑한다.
        def a1(d):
            m = missile(1.1).move_to(LEFT * 4.4 + UP * 1.0)
            ar1 = Arrow(LEFT * 3.7 + UP * 1.0, LEFT * 2.2 + UP * 1.0, color=GRAY, stroke_width=5)
            nodes, edges, _ = build_mesh(0.22, (-0.6, 0.55))
            miniweb = VGroup(edges, nodes)
            ar2 = Arrow(RIGHT * 1.0 + UP * 1.0, RIGHT * 2.5 + UP * 1.0, color=GRAY, stroke_width=5)
            globe = VGroup(
                Circle(radius=0.65).set_stroke(BLUE, 4),
                Line(LEFT * 0.65, RIGHT * 0.65).set_stroke(BLUE, 3),
                Circle(radius=0.65).set_stroke(BLUE, 3).stretch(0.45, 0),
            ).move_to(RIGHT * 3.9 + UP * 1.0)
            self.st["chain"] = VGroup(m, ar1, miniweb, ar2, globe)
            self.act(d, LaggedStart(FadeIn(m), Create(ar1), FadeIn(miniweb),
                                    Create(ar2), Create(globe), lag_ratio=0.25),
                     rt=min(2.2, d * 0.75))

        def a2(d):
            self.hold(d)

        def a3(d):
            p1 = ktext("모든 해결은,", fs=54, color=INK, bold=True)
            p2 = chip("새로운 문제", BLUE, 44)
            p3 = ktext("를 낳는다", fs=54, color=INK, bold=True)
            law = VGroup(p1, p2, p3).arrange(RIGHT, buff=0.3).move_to(DOWN * 1.0)
            self.act(d, FadeIn(law, scale=1.15), rt=min(1.2, d * 0.55))

        self.run_beats(S, [a1, a2, a3])

    # --- 13: 말이 안 통함 ---
    def seg13(self, S):
        def a0(d):
            import math
            centers = [P3((-3.4, 0.0)), P3((0.0, 1.6)), P3((3.4, 0.0))]
            syms = ["01", "@#", "?~"]
            groups = VGroup()
            for c, s in zip(centers, syms):
                node = Dot(c, radius=0.18, color=INK)
                bub = RoundedRectangle(corner_radius=0.2, width=1.3, height=0.9)
                bub.set_stroke(GRAY, 4).set_fill(WHITE, 1)
                bub.move_to([c[0], c[1] + 1.15, 0])
                txt = mtext(s, fs=40, color=GRAY).move_to(bub)
                groups.add(VGroup(node, bub, txt))
            links = VGroup()
            for i, j in ((0, 1), (1, 2), (0, 2)):
                ln = DashedLine(centers[i], centers[j], buff=0.3).set_stroke(RED, 3)
                mid = [(centers[i][0] + centers[j][0]) / 2, (centers[i][1] + centers[j][1]) / 2, 0]
                x = VGroup(Line(UL * 0.16, DR * 0.16), Line(UR * 0.16, DL * 0.16))
                x.set_stroke(RED, 5).move_to(mid)
                links.add(VGroup(ln, x))
            self.st["babel"] = groups
            self.act(d, LaggedStart(*[FadeIn(g, scale=1.2) for g in groups], lag_ratio=0.2),
                     LaggedStart(*[Create(l) for l in links], lag_ratio=0.2),
                     rt=min(2.0, d * 0.7))

        def a1(d):
            self.act(d, Wiggle(self.st["babel"], scale_value=1.06))

        self.run_beats(S, [a0, a1])

    # --- 14: 다음 편 ---
    def seg14(self, S):
        def a0(d):
            card = RoundedRectangle(corner_radius=0.2, width=2.8, height=2.8)
            card.set_stroke(INK, 5).set_fill(WHITE, 1).move_to(LEFT * 2.6 + UP * 0.5)
            header = RoundedRectangle(corner_radius=0.2, width=2.8, height=0.75)
            header.set_stroke(width=0).set_fill(RED, 1)
            header.move_to(card.get_top() + DOWN * 0.375)
            yr = ktext("1983", 30, WHITE, bold=True).move_to(header)
            day = ktext("1. 1", 64, INK, bold=True).move_to(card.get_center() + DOWN * 0.35)
            self.st["cal"] = VGroup(card, header, yr, day)
            self.act(d, FadeIn(self.st["cal"], scale=1.15))

        def a1(d):
            # CTA 자리를 먼저 예약하고, 예고 문구는 그 금줄을 피해 배치한다.
            self.reserve_cta()
            tag = chip("NCP → TCP/IP", INK, 30).move_to(RIGHT * 2.8 + UP * 1.3)
            sub2 = ktext("하루 만에 언어를 갈아탄 날", 30, GRAY).next_to(tag, DOWN, buff=0.4)
            self.avoid_zones(tag)
            self.avoid_zones(sub2)
            self.act(d, FadeIn(tag, scale=1.2), FadeIn(sub2, shift=UP * 0.15))

        def a2(d):
            self.show_cta(d)

        self.run_beats(S, [a0, a1, a2])


class Episode02(EpisodeBase):
    """2편: TCP/IP Flag Day — 1983.1.1 언어 대전환. 하이브리드 v3(사건=실사 켄 번즈, 원리=도형).

    실사 5장면: calendar_night(NORAD 전산실) · three_nets(골드스톤/SRI 밴/IMP 3분할)
    · cerf_kahn(초상 2 + 훈장 보조) · flagday(BBN 1982 지도 줌) · badge(자체 재현 — 표기 필수).
    원리 장면(envelope, ip_tcp_roles, ncp_problem, ipv6_twist 등)은 도형 유지."""
    CLEAR_AFTER = {0, 1, 5, 6, 7, 10, 11, 12, 13}
    CTA = {"pos": RIGHT * 3.1 + DOWN * 0.9, "w": 2.6, "h": 0.85,
           "like": True, "buff": 0.3, "fs": (40, 34), "cc": DR}

    def intro(self):
        title = mtext("TCP/IP", fs=110, color=INK).move_to(UP * 0.9)
        sub = ktext("인터넷 전체가 하루 만에 언어를 갈아탄 날", fs=40, color=GRAY).next_to(title, DOWN, buff=0.5)
        num = chip("#02", BLUE, 30).to_corner(UL, buff=0.6)
        cc = Text("© nous-zero", font=KFONT, font_size=22, color=LGRAY).to_corner(DR, buff=0.45)
        self.claim_bottom(cc)   # 하단 띠의 정식 거주자 신고(감사 장부만 변경 — 화면 불변)
        self.play(FadeIn(title, scale=1.15), FadeIn(num), run_time=0.9)
        self.play(FadeIn(sub, shift=UP * 0.2), FadeIn(cc), run_time=0.7)
        self.wait(INTRO_D - 0.9 - 0.7 - 0.6)
        self.play(*[FadeOut(m) for m in (title, sub, num, cc)], run_time=0.6)

    # --- 공용 소품 ---
    def envelope_icon(self, w=2.0, h=1.3, color=BLUE):
        body = RoundedRectangle(corner_radius=0.08, width=w, height=h)
        body.set_stroke(color, 4).set_fill(WHITE, 1)
        flap = VGroup(Line(body.get_corner(UL), body.get_center() + UP * 0.06),
                      Line(body.get_corner(UR), body.get_center() + UP * 0.06))
        flap.set_stroke(color, 4)
        return VGroup(body, flap)

    def net_box(self, label, color, pos):
        b = RoundedRectangle(corner_radius=0.2, width=3.3, height=2.0)
        b.set_stroke(color, 4).set_fill(WHITE, 1).move_to(pos)
        t = ktext(label, 30, INK, bold=True).move_to(b.get_top() + DOWN * 0.42)
        return VGroup(b, t)

    # --- 0: 1982.12.31 밤 — 퇴근 못 한 전산실 (실사: NORAD 전산실) ---
    def seg00(self, S):
        def a0(d):
            card = RoundedRectangle(corner_radius=0.22, width=4.6, height=3.1)
            card.set_stroke(INK, 4).set_fill(PAPER, 1).move_to(LEFT * 3.4 + UP * 0.6)
            header = Rectangle(width=4.6, height=0.75).set_fill(RED, 1).set_stroke(width=0)
            header.move_to(card.get_top() + DOWN * 0.375)
            yr = ktext("1982년 12월", 30, WHITE, bold=True).move_to(header)
            day = mtext("31", fs=90, color=INK).move_to(card.get_center() + DOWN * 0.35)
            night = chip("밤", INK, 24).next_to(card, DOWN, buff=0.3)
            self.st["cal"] = VGroup(card, header, yr, day, night)
            self.act(d, FadeIn(VGroup(card, header, yr, day), scale=1.1), FadeIn(night))

        def a1(d):
            # 실사: 냉전기 대형 전산실의 실물 — 어둡게 눌러 '밤샘'의 공기를 만든다
            ph = self.photo("ep02_norad_computer_room_1984.jpg", height=3.6,
                            pos=RIGHT * 3.2 + UP * 0.55)
            shade = Rectangle(width=ph[0].width, height=ph[0].height)
            shade.set_fill("#0B1220", 0.42).set_stroke(width=0).move_to(ph[0])
            room = Group(ph[0], shade, ph[1])  # 사진 → 어둠막 → 액자 순으로 겹침
            cap = chip("NORAD 전산실 — 미 공군 기록(1984)", GRAY, 18)
            cap.next_to(room, DOWN, buff=0.22)
            self.st["room"] = room
            t1 = max(0.4, min(0.9, d * 0.3))
            self.play(FadeIn(room, scale=1.04), FadeIn(cap), run_time=t1)
            self.ken_burns(room, d - t1, zoom=1.09)

        def a2(d):
            note = chip("내일 아침 — 인터넷의 언어 교체", RED, 28).move_to(DOWN * 2.5)
            self.act(d, FadeIn(note, shift=UP * 0.25))

        self.run_beats(S, [a0, a1, a2])

    # --- 1: 지난 편 요약 — 그물망의 성공, 새 문제 ---
    def seg01(self, S):
        def a0(d):
            nodes, edges, _ = build_mesh(scale=0.62, shift=(0, 0.7))
            tag = chip("지난 편 — ARPANET 그물망", INK, 26).to_corner(UL, buff=0.5)
            self.st["mesh"] = VGroup(edges, nodes)
            self.act(d, Create(edges), FadeIn(nodes), FadeIn(tag), rt=min(1.8, d * 0.7))

        def a1(d):
            q = ktext("성공이 낳은 새 문제?", 44, RED, bold=True).move_to(DOWN * 2.3)
            self.act(d, FadeIn(q, scale=1.2), Wiggle(self.st["mesh"], scale_value=1.02))

        self.run_beats(S, [a0, a1])

    # --- 2: 세 개의 망 — 실사 3분할 (위성=골드스톤, 무선=SRI 밴, 아파넷=IMP) ---
    def seg02(self, S):
        def a0(d):
            era = chip("1970년대", INK, 28).to_corner(UL, buff=0.5)
            self.act(d, FadeIn(era, shift=DOWN * 0.2))

        def a1(d):
            specs = [
                ("ep02_goldstone_dish_1972.jpg", "위성망", BLUE,
                 LEFT * 4.3 + UP * 1.0, 2.8),
                ("ep02_sri_packet_radio_van_2x.jpg", "무선망", AMBER,
                 UP * 1.0, 2.0),
                ("imp_panel.jpg", "ARPANET", INK,
                 RIGHT * 4.3 + UP * 1.0, 2.3),
            ]
            nets, rects = [], []
            for fname, lab, co, pos, h in specs:
                ph = self.photo(fname, height=h, pos=pos)
                tag = chip(lab, co, 22)  # 방송 자막 스타일 — 사진 위 좌상단
                tag.move_to(ph[1].get_corner(UL)
                            + RIGHT * (tag.width / 2 + 0.12)
                            + DOWN * (tag.height / 2 + 0.12))
                nets.append(Group(ph, tag))
                rects.append(ph[1])  # 하류 장면(3~5)의 위치 앵커 = 액자 사각형
            self.st["nets"] = nets
            self.st["netr"] = rects
            t1 = max(0.6, min(2.4, d * 0.55))
            self.play(LaggedStart(*[FadeIn(n, scale=1.06) for n in nets],
                                  lag_ratio=0.3), run_time=t1)
            if self.subtitle:
                self.remove(self.subtitle)
                self.add(self.subtitle)
            self.ken_burns(Group(*nets), d - t1, zoom=1.02)

        def a2(d):
            oks = VGroup(*[chip("OK", BLUE, 20)
                           .move_to(r.get_corner(UR) + LEFT * 0.55 + DOWN * 0.4)
                           for r in self.st["netr"]])
            self.st["oks"] = oks
            self.act(d, LaggedStart(*[FadeIn(o, scale=1.3) for o in oks], lag_ratio=0.2))

        def a3(d):
            links, xs = VGroup(), VGroup()
            for i in (0, 1):
                a = self.st["netr"][i].get_right()
                b = self.st["netr"][i + 1].get_left()
                links.add(DashedLine(a, b, buff=0.15).set_stroke(LGRAY, 3))
                mid = (a + b) / 2
                xs.add(VGroup(Line(UL * 0.28, DR * 0.28),
                              Line(UR * 0.28, DL * 0.28)).set_stroke(RED, 8).move_to(mid))
            self.st["xlinks"] = VGroup(links, xs)
            t1 = max(0.3, min(0.8, d * 0.35))
            self.play(Create(links), run_time=t1)
            t2 = max(0.3, min(0.7, d * 0.3))
            self.play(FadeIn(xs, scale=1.4), run_time=t2)
            self.hold(d - t1 - t2)

        self.run_beats(S, [a0, a1, a2, a3])

    # --- 3: 규칙이 전부 다르다 — 언어 비유 ---
    def seg03(self, S):
        def a0(d):
            shapes = [RegularPolygon(n=4).scale(0.42), Circle(radius=0.42),
                      RegularPolygon(n=6).scale(0.42)]
            colors = [BLUE, AMBER, INK]
            rules = VGroup()
            for r, sh, co in zip(self.st["netr"], shapes, colors):
                sh.set_stroke(co, 4).set_fill(WHITE, 1)
                sh.move_to(r.get_bottom() + DOWN * 0.75)
                rules.add(sh)
            cap = ktext("망마다 포장 규칙이 다르다", 30, GRAY).move_to(DOWN * 2.75)
            self.st["rules"] = VGroup(rules, cap)
            self.act(d, LaggedStart(*[GrowFromCenter(s) for s in rules], lag_ratio=0.2),
                     FadeIn(cap))

        def a1(d):
            labels = ["한국어", "아랍어", "수화"]
            bubbles = VGroup()
            for r, lb in zip(self.st["netr"], labels):
                t = ktext(lb, 26, INK, bold=True)
                box = RoundedRectangle(corner_radius=0.18, width=t.width + 0.5,
                                       height=t.height + 0.36)
                box.set_stroke(INK, 3).set_fill(WHITE, 1)
                grp = VGroup(box, t.move_to(box))
                grp.move_to(r.get_top() + UP * 0.55)
                bubbles.add(grp)
            self.st["bubbles"] = bubbles
            self.act(d, LaggedStart(*[FadeIn(b, shift=UP * 0.2) for b in bubbles],
                                    lag_ratio=0.2))

        self.run_beats(S, [a0, a1])

    # --- 4: 다 뜯어고치기? 안 됨 — 각자의 사정 ---
    def seg04(self, S):
        def a0(d):
            q = ktext("전부 뜯어고쳐서 하나로?", 46, INK, bold=True).move_to(DOWN * 1.9)
            self.st["fixq"] = q
            outs = [FadeOut(self.st.pop(k)) for k in ("rules", "bubbles") if k in self.st]
            self.act(d, FadeIn(q, scale=1.15), *outs)

        def a1(d):
            ban = VGroup(Circle(radius=0.55).set_stroke(RED, 8),
                         Line(UL * 0.38, DR * 0.38).set_stroke(RED, 8))
            ban.next_to(self.st["fixq"], RIGHT, buff=0.4)
            self.st["ban"] = ban
            self.act(d, FadeIn(ban, scale=1.4))

        def a2(d):
            traits = ["느리지만 바다를 건넘", "끊기지만 이동", "빠르지만 고정"]
            chips = VGroup()
            for r, tr in zip(self.st["netr"], traits):
                c = chip(tr, GRAY, 19)
                c.move_to(r.get_bottom() + DOWN * 0.55)
                chips.add(c)
            self.act(d, LaggedStart(*[FadeIn(c, shift=UP * 0.15) for c in chips],
                                    lag_ratio=0.2))

        self.run_beats(S, [a0, a1, a2])

    # --- 5: 공통 봉투 — 발상의 전환 ---
    def seg05(self, S):
        def a0(d):
            outs = [FadeOut(self.st.pop(k)) for k in ("fixq", "ban", "oks", "xlinks")
                    if k in self.st]
            env = self.envelope_icon(2.2, 1.4)
            env.move_to(DOWN * 1.9)
            tag = chip("공통 봉투", BLUE, 28).next_to(env, RIGHT, buff=0.5)
            self.st["env"] = env
            self.st["envtag"] = tag
            self.act(d, *outs, FadeIn(env, scale=1.2), FadeIn(tag))

        def a1(d):
            data = RoundedRectangle(corner_radius=0.08, width=0.8, height=0.55)
            data.set_stroke(INK, 3).set_fill(PAPER, 1)
            data.move_to(self.st["env"].get_center() + UP * 1.7 + LEFT * 2.2)
            t1 = max(0.3, min(0.7, d * 0.3))
            self.play(FadeIn(data, shift=DOWN * 0.2), run_time=t1)
            t2 = max(0.4, min(1.0, d * 0.4))
            self.play(data.animate.scale(0.55).move_to(self.st["env"].get_center()),
                      run_time=t2)
            t3 = min(0.4, max(0.3, d * 0.15))
            self.play(FadeOut(data), Indicate(self.st["env"], color=BLUE), run_time=t3)
            self.hold(d - t1 - t2 - t3)

        def a2(d):
            env = self.st["env"]
            small = env.copy().scale(0.5)
            path_pts = [self.st["netr"][0].get_center(),
                        self.st["netr"][1].get_center(),
                        self.st["netr"][2].get_center()]
            t1 = max(0.3, min(0.6, d * 0.2))
            self.play(small.animate.move_to(path_pts[0]), run_time=t1)
            rest = d - t1
            for i in (1, 2):
                t = max(0.4, min(1.1, rest * 0.35))
                self.play(MoveAlongPath(small, Line(path_pts[i - 1], path_pts[i])),
                          run_time=t)
                rest -= t
            self.st["envsmall"] = small
            self.hold(rest)

        self.run_beats(S, [a0, a1, a2])

    # --- 6: 1974 — 서프·칸 (실사 초상 + 훈장 보조 컷) ---
    def seg06(self, S):
        def a0(d):
            cerf = self.photo("ep02_vint_cerf_1995.jpg", height=2.8,
                              pos=LEFT * 2.9 + UP * 0.7)
            kahn = self.photo("ep02_bob_kahn_2013.jpg", height=2.8,
                              pos=RIGHT * 2.9 + UP * 0.7)
            n1 = chip("빈트 서프 (사진 1995)", GRAY, 19).next_to(cerf, DOWN, buff=0.22)
            n2 = chip("로버트 칸 (사진 2013)", GRAY, 19).next_to(kahn, DOWN, buff=0.22)
            yr = chip("1974 — TCP/IP 설계 논문", INK, 26).move_to(UP * 3.15)
            duo = Group(cerf, kahn)
            self.st["duo"] = duo
            t1 = max(0.5, min(1.2, d * 0.3))
            self.play(LaggedStart(FadeIn(cerf, scale=1.05), FadeIn(kahn, scale=1.05),
                                  lag_ratio=0.25),
                      FadeIn(n1), FadeIn(n2), run_time=t1)
            t2 = max(0.3, min(0.6, d * 0.12))
            self.play(FadeIn(yr, shift=DOWN * 0.2), run_time=t2)
            # 보조 컷: 2005 자유훈장(저해상 — 작게, 짧게)
            medal = self.photo("ep02_cerf_kahn_medal_2005.jpg", height=1.5,
                               pos=RIGHT * 0.43 + UP * 0.55)
            mcap = chip("2005 자유훈장 — 백악관 기록", GRAY, 15)
            mcap.next_to(medal, DOWN, buff=0.16)
            t3 = max(0.3, min(0.6, d * 0.12))
            self.play(FadeIn(medal, scale=1.06), FadeIn(mcap), run_time=t3)
            self.ken_burns(duo, d - t1 - t2 - t3, zoom=1.03)

        def a1(d):
            name = mtext("TCP/IP", fs=72, color=BLUE).move_to(DOWN * 2.35)
            self.st["tcpname"] = name
            t1 = max(0.4, min(1.0, d * 0.5))
            self.play(FadeIn(name, scale=1.4), run_time=t1)
            t2 = min(0.6, max(0.3, d * 0.25))
            self.play(Flash(name.get_center(), color=BLUE, flash_radius=1.8),
                      run_time=t2)
            self.hold(d - t1 - t2)

        def a2(d):
            # "지금 이 영상도 이 규격으로 배달 중" — 봉투가 화면 아래를 가로지른다
            env = self.envelope_icon(1.1, 0.72)
            env.move_to(LEFT * 6.2 + DOWN * 3.3)
            t1 = max(0.3, min(0.5, d * 0.2))
            self.play(FadeIn(env, scale=1.2), run_time=t1)
            t2 = max(0.6, min(2.2, d * 0.55))
            self.play(MoveAlongPath(env, Line(env.get_center(),
                                              RIGHT * 6.2 + DOWN * 3.3)),
                      Indicate(self.st["tcpname"], color=BLUE, scale_factor=1.06),
                      run_time=t2)
            self.hold(d - t1 - t2)

        self.run_beats(S, [a0, a1, a2])

    # --- 7: IP는 주소, TCP는 품질 ---
    def seg07(self, S):
        def card(label, sub_label, color, pos):
            b = RoundedRectangle(corner_radius=0.22, width=5.6, height=4.6)
            b.set_stroke(color, 4).set_fill(WHITE, 1).move_to(pos)
            head = mtext(label, fs=44, color=color).move_to(b.get_top() + DOWN * 0.55)
            sub2 = ktext(sub_label, 27, GRAY).next_to(head, DOWN, buff=0.22)
            return VGroup(b, head, sub2)

        def a0(d):
            ipc = card("IP", "주소 담당", BLUE, LEFT * 3.3 + DOWN * 0.2)
            tcc = card("TCP", "품질 담당", RED, RIGHT * 3.3 + DOWN * 0.2)
            self.st["ipc"], self.st["tcc"] = ipc, tcc
            self.act(d, FadeIn(ipc, shift=RIGHT * 0.3), FadeIn(tcc, shift=LEFT * 0.3))

        def a1(d):
            env = self.envelope_icon(1.7, 1.1)
            env.move_to(self.st["ipc"][0].get_center() + UP * 0.1)
            addr = VGroup(*[Line(LEFT * 0.5, RIGHT * 0.5).set_stroke(GRAY, 3)
                            for _ in range(2)]).arrange(DOWN, buff=0.16)
            addr.move_to(env[0].get_center() + DOWN * 0.12)
            self.st["ipenv"] = VGroup(env, addr)
            self.act(d, FadeIn(env, scale=1.15), Create(addr))

        def a2(d):
            start = self.st["ipenv"].get_bottom() + DOWN * 0.35
            end = start + RIGHT * 3.4 + DOWN * 0.35
            route = ArcBetweenPoints(start, end, angle=0.7).set_stroke(LGRAY, 4)
            arrow = Arrow(end + LEFT * 0.7 + UP * 0.22, end, buff=0,
                          color=BLUE, stroke_width=6)
            self.act(d, Create(route), GrowFromCenter(arrow))

        def a3(d):
            self.act(d, Indicate(self.st["tcc"], color=RED, scale_factor=1.04))

        def a4(d):
            base = self.st["tcc"][0].get_center() + DOWN * 0.35
            slots = VGroup()
            for i in range(3):
                sq = RoundedRectangle(corner_radius=0.08, width=1.0, height=1.0)
                sq.set_stroke(LGRAY, 3).set_fill(PAPER, 1)
                num = mtext(str(i + 1), fs=40, color=GRAY).move_to(sq)
                slots.add(VGroup(sq, num).move_to(base + RIGHT * (i - 1) * 1.25))
            t1 = max(0.4, min(0.9, d * 0.3))
            self.play(LaggedStart(FadeIn(slots[0]), FadeIn(slots[2]), lag_ratio=0.3),
                      run_time=t1)  # 2번 조각이 빠진 채 도착
            miss = slots[1]
            t2 = max(0.4, min(0.9, d * 0.3))
            self.play(FadeIn(miss, shift=DOWN * 0.6), run_time=t2)  # 재전송 도착
            t3 = max(0.3, min(0.7, d * 0.25))
            self.play(*[s[0].animate.set_stroke(BLUE, 4) for s in slots], run_time=t3)
            self.hold(d - t1 - t2 - t3)

        self.run_beats(S, [a0, a1, a2, a3, a4])

    # --- 8: 전환 문제 — 옛 언어 NCP 위의 수백 대 ---
    def seg08(self, S):
        def a0(d):
            title = ktext("문제는 '전환'", 52, INK, bold=True).move_to(UP * 2.6)
            self.st["convt"] = title
            self.act(d, FadeIn(title, scale=1.15))

        def a1(d):
            grid = VGroup()
            for r in range(4):
                for c in range(5):
                    sq = RoundedRectangle(corner_radius=0.08, width=1.15, height=0.85)
                    sq.set_stroke(INK, 3).set_fill(WHITE, 1)
                    lab = mtext("NCP", fs=20, color=GRAY).move_to(sq)
                    grid.add(VGroup(sq, lab).move_to(
                        LEFT * 2.9 + RIGHT * c * 1.35 + UP * (1.3 - r * 1.05)))
            grid.move_to(LEFT * 1.6 + DOWN * 0.4)
            self.st["grid"] = grid
            tag = chip("옛 언어 NCP — 이미 잘 돌아가는 중", GRAY, 22)
            tag.move_to(DOWN * 3.0 + LEFT * 1.6)
            self.st["gridtag"] = tag
            self.act(d, LaggedStart(*[FadeIn(g, scale=1.1) for g in grid],
                                    lag_ratio=0.03), FadeIn(tag), rt=min(2.0, d * 0.7))

        def a2(d):
            warn = ktext("미루면, 영원히 못 한다", 34, RED, bold=True)
            warn.move_to(RIGHT * 4.6 + DOWN * 0.4)
            if warn.width > 4.0:
                warn.scale_to_fit_width(4.0)
            self.st["warn"] = warn
            self.act(d, FadeIn(warn, scale=1.2))

        self.run_beats(S, [a0, a1, a2])

    # --- 9: 초강수 공지 — 유예 없음 ---
    def seg09(self, S):
        def a0(d):
            outs = [FadeOut(self.st.pop(k)) for k in ("convt", "warn") if k in self.st]
            notice = RoundedRectangle(corner_radius=0.15, width=4.4, height=4.6)
            notice.set_stroke(RED, 5).set_fill(WHITE, 1).move_to(RIGHT * 4.3 + DOWN * 0.3)
            head = ktext("공 지", 38, RED, bold=True).move_to(notice.get_top() + DOWN * 0.55)
            rule = Line(notice.get_left() + RIGHT * 0.35, notice.get_right() + LEFT * 0.35)
            rule.set_stroke(LGRAY, 2).move_to(notice.get_top() + DOWN * 0.95)
            self.st["notice"] = VGroup(notice, head, rule)
            self.act(d, *outs, FadeIn(self.st["notice"], scale=1.08))

        def a1(d):
            l1 = ktext("1983.1.1부로", 28, INK, bold=True)
            l2 = ktext("옛 언어(NCP) 차단", 28, INK, bold=True)
            item1 = VGroup(l1, l2).arrange(DOWN, buff=0.14)
            item1.move_to(self.st["notice"][0].get_center() + UP * 0.75)
            self.st["item1"] = item1
            self.act(d, FadeIn(item1, shift=UP * 0.15))

        def a2(d):
            l1 = ktext("못 갈아탄 컴퓨터는", 26, GRAY)
            l2 = ktext("인터넷에서 잘린다", 28, INK, bold=True)
            item2 = VGroup(l1, l2).arrange(DOWN, buff=0.14)
            item2.move_to(self.st["notice"][0].get_center() + DOWN * 0.55)
            self.st["item2"] = item2
            self.act(d, FadeIn(item2, shift=UP * 0.15))

        def a3(d):
            stamp = chip("유예 없음", RED, 30).rotate(0.22)
            stamp.move_to(self.st["notice"][0].get_corner(DR) + UL * 0.9)
            t1 = max(0.3, min(0.6, d * 0.4))
            self.play(FadeIn(stamp, scale=1.8), run_time=t1)
            self.play(Flash(stamp.get_center(), color=RED, flash_radius=1.3),
                      run_time=min(0.5, max(0.3, d * 0.2)))
            self.hold(d - t1 - min(0.5, max(0.3, d * 0.2)))

        self.run_beats(S, [a0, a1, a2, a3])

    # --- 10: 1983.1.1 — 일제 전환(Flag Day) ---
    def seg10(self, S):
        def a0(d):
            outs = [FadeOut(self.st.pop(k)) for k in ("notice", "item1", "item2")
                    if k in self.st]
            card = RoundedRectangle(corner_radius=0.18, width=3.3, height=2.3)
            card.set_stroke(INK, 4).set_fill(PAPER, 1).move_to(RIGHT * 4.3 + UP * 1.6)
            header = Rectangle(width=3.3, height=0.6).set_fill(RED, 1).set_stroke(width=0)
            header.move_to(card.get_top() + DOWN * 0.3)
            yr = ktext("1983년 1월", 24, WHITE, bold=True).move_to(header)
            day = mtext("1", fs=64, color=INK).move_to(card.get_center() + DOWN * 0.25)
            self.st["cal83"] = VGroup(card, header, yr, day)
            self.act(d, *outs, FadeIn(self.st["cal83"], scale=1.15))

        def a1(d):
            grid = self.st["grid"]
            anims = []
            for g in grid:
                new_lab = mtext("TCP/IP", fs=17, color=WHITE).move_to(g[0])
                anims.append(g[0].animate.set_fill(BLUE, 1).set_stroke(BLUE, 3))
                anims.append(Transform(g[1], new_lab))
            tag2 = chip("약 400대 — 하루 만에 전환", BLUE, 22).move_to(DOWN * 3.0 + LEFT * 1.6)
            self.st["tag2"] = tag2
            old = self.st.pop("gridtag", None)
            outs = [FadeOut(old)] if old else []
            self.act(d, LaggedStart(*anims, lag_ratio=0.02), *outs, FadeIn(tag2),
                     rt=min(2.2, d * 0.75))

        def a2(d):
            # 실사: 그날의 판도 — 1982년 BBN ARPANET 지도, 넓게 → 노드 밀집부로 줌
            outs = [FadeOut(self.st.pop(k)) for k in ("grid", "cal83", "tag2")
                    if k in self.st]
            ph = self.photo("ep02_arpanet_map_1982.jpg", height=5.4, pos=UP * 0.15)
            fd = chip("Flag Day — 깃발의 날", INK, 28).move_to(UP * 3.4)
            cap = chip("ARPANET 지도 1982.6 — BBN", GRAY, 17)
            cap.move_to(DOWN * 3.15 + RIGHT * 4.9)
            t0 = max(0.25, min(0.4, d * 0.1))
            self.play(*outs, run_time=t0)
            t1 = max(0.4, min(0.8, d * 0.2))
            self.play(FadeIn(ph, scale=1.03), FadeIn(cap), run_time=t1)
            if self.subtitle:
                self.remove(self.subtitle)
                self.add(self.subtitle)
            t2 = max(0.3, min(0.6, d * 0.15))
            self.play(FadeIn(fd, scale=1.25), run_time=t2)
            self.ken_burns(ph, d - t0 - t1 - t2, zoom=1.22,
                           drift=LEFT * 0.9 + DOWN * 0.35)

        self.run_beats(S, [a0, a1, a2])

    # --- 11: 살아남은 자의 배지 (자체 재현 이미지 — "재현 이미지" 표기 필수/법무) ---
    def seg11(self, S):
        def a0(d):
            badge = self.photo("ep02_badge_recreation.png", height=4.3,
                               pos=UP * 0.35, framed=False)
            # 법무 조건: 실사 사료로 오인하지 않게 화면 안에 상시 표기
            note = legal_chip("재현 이미지", GRAY, 20).move_to(RIGHT * 3.7 + UP * 2.7)
            self.st["badge"] = badge
            t1 = max(0.4, min(0.9, d * 0.35))
            self.play(FadeIn(badge, scale=1.08), FadeIn(note), run_time=t1)
            self.ken_burns(badge, d - t1, zoom=1.05)

        def a1(d):
            quote = chip("“나는 TCP 전환에서 살아남았다”", RED, 24)
            quote.move_to(DOWN * 2.3)
            self.act(d, FadeIn(quote, scale=1.15))

        def a2(d):
            who = chip("댄 린치 — 사비로 500개 제작", GRAY, 24).move_to(DOWN * 3.15)
            self.act(d, FadeIn(who, shift=UP * 0.2))

        self.run_beats(S, [a0, a1, a2])

    # --- 12: 반전 — 두 번째 교체는 20년째 ---
    def seg12(self, S):
        def a0(d):
            tw = ktext("반전", 96, INK, bold=True)
            self.st["twist"] = tw
            self.act(d, FadeIn(tw, scale=1.5))

        def a1(d):
            out = [FadeOut(self.st.pop("twist"))] if "twist" in self.st else []
            tag = chip("두 번째 언어 교체 — 지금 진행 중", INK, 28).move_to(UP * 2.6)
            arrow = VGroup(mtext("IPv4", fs=44, color=GRAY),
                           mtext("→", fs=44, color=LGRAY),
                           mtext("IPv6", fs=44, color=BLUE))
            arrow.arrange(RIGHT, buff=0.5).move_to(UP * 1.5)
            self.st["ipv"] = VGroup(tag, arrow)
            self.act(d, *out, FadeIn(tag), FadeIn(arrow, shift=UP * 0.2))

        def a2(d):
            cause = chip("이유 — 주소가 바닥났다", RED, 26).move_to(UP * 0.45)
            self.act(d, FadeIn(cause, scale=1.15))

        def a3(d):
            left = VGroup(ktext("1983년", 30, INK, bold=True),
                          ktext("400대 — 하루", 27, GRAY)).arrange(DOWN, buff=0.16)
            right = VGroup(ktext("지금", 30, INK, bold=True),
                           ktext("수십억 대 — 20년째", 27, GRAY)).arrange(DOWN, buff=0.16)
            left.move_to(LEFT * 3.4 + DOWN * 1.0)
            right.move_to(RIGHT * 3.4 + DOWN * 1.0)
            vs = ktext("vs", 30, LGRAY).move_to(DOWN * 1.0)
            self.act(d, FadeIn(left, shift=RIGHT * 0.2), FadeIn(vs),
                     FadeIn(right, shift=LEFT * 0.2))

        def a4(d):
            track = RoundedRectangle(corner_radius=0.14, width=8.4, height=0.6)
            track.set_stroke(INK, 3).set_fill(PAPER, 1).move_to(DOWN * 2.5)
            fill = Rectangle(width=8.4 * 0.501, height=0.6).set_fill(BLUE, 1)
            fill.set_stroke(width=0)
            fill.align_to(track, LEFT).align_to(track, DOWN).shift(UP * 0)
            fill.move_to(track.get_left() + RIGHT * (8.4 * 0.501) / 2)
            lab = ktext("IPv6 전환율 50.1% — 2026년 3월에야 절반", 24, GRAY)
            lab.next_to(track, DOWN, buff=0.22)
            t1 = max(0.3, min(0.6, d * 0.25))
            self.play(FadeIn(track), FadeIn(lab), run_time=t1)
            start = fill.copy().stretch(0.001, 0).move_to(track.get_left() + RIGHT * 0.01)
            self.add(start)
            t2 = max(0.5, min(1.4, d * 0.45))
            self.play(Transform(start, fill), run_time=t2)
            self.hold(d - t1 - t2)

        self.run_beats(S, [a0, a1, a2, a3, a4])

    # --- 13: 법칙 #2 ---
    def seg13(self, S):
        def a0(d):
            num = chip("법칙 #2", BLUE, 30).move_to(UP * 1.7)
            phrase = ktext("성공한 표준은 축복이자 족쇄다", 56, INK, bold=True)
            phrase.move_to(UP * 0.3)
            ul = Underline(phrase, color=BLUE).set_stroke(BLUE, 8)
            self.st["law"] = VGroup(num, phrase, ul)
            self.act(d, FadeIn(num, shift=DOWN * 0.2), FadeIn(phrase, scale=1.1),
                     Create(ul), rt=min(1.4, d * 0.6))

        def a1(d):
            note = ktext("완벽할수록, 그 위에 쌓이는 것이 많다", 30, GRAY).move_to(DOWN * 1.3)
            self.act(d, FadeIn(note, shift=UP * 0.15))

        self.run_beats(S, [a0, a1])

    # --- 14: 질문 + 예고 + CTA ---
    def seg14(self, S):
        def a0(d):
            t = ktext("여러분이라면, 유예 없이 차단했을까요?", 32, INK, bold=True)
            box = RoundedRectangle(corner_radius=0.25, width=t.width + 0.8,
                                   height=t.height + 0.7)
            box.set_stroke(INK, 4).set_fill(PAPER, 1)
            tail = Triangle().scale(0.22).rotate(PI)
            tail.set_stroke(INK, 4).set_fill(PAPER, 1)
            tail.move_to(box.get_bottom() + DOWN * 0.16 + LEFT * 2.2)
            bubble = VGroup(box, tail, t.move_to(box)).move_to(UP * 1.9)
            self.st["bubble"] = bubble
            self.act(d, FadeIn(bubble, scale=1.1))

        def a1(d):
            cmt = chip("댓글로", BLUE, 28).next_to(self.st["bubble"], DOWN, buff=0.45)
            self.act(d, FadeIn(cmt, shift=UP * 0.2),
                     Indicate(self.st["bubble"], color=BLUE, scale_factor=1.03))

        def a2(d):
            self.reserve_cta()
            band_l, band_r, band_w = self.free_x_band(-2.0, -0.5, anchor=-2.9)
            tag = chip("#03 — 웹(Web)의 탄생", INK, 30).move_to(DOWN * 0.85 + LEFT * 2.9)
            teaser = ktext_block("도로는 깔렸는데, 실어 나를 짐이 없었다", 27, GRAY,
                                 max_width=min(13.0, band_w))
            teaser.next_to(tag, DOWN, buff=0.3)
            self.avoid_zones(tag)
            self.avoid_zones(teaser)
            self.act(d, FadeIn(tag, scale=1.15), FadeIn(teaser, shift=UP * 0.15))

        def a3(d):
            self.show_cta(d)

        self.run_beats(S, [a0, a1, a2, a3])


EP03_ASSET_EXTS = ("jpg", "jpeg", "png", "webp")


def find_asset(stem):
    """소재 파일 탐색 — asset-scout 저장 확장자가 미정이므로 4종 순회."""
    for ext in EP03_ASSET_EXTS:
        p = os.path.join(ASSETS, f"{stem}.{ext}")
        if os.path.exists(p):
            return p
    return None


class Episode03(EpisodeBase):
    """3편: WWW의 탄생 — 1989 'Vague but exciting'. 하이브리드 v3(사건=실사 켄 번즈, 원리=도형).

    실사 9장면: memo_three_words · cern_intro · knowledge_loss · proposal
    · vague_memo(0번 소재 클로즈업 재사용) · next_server · go_public · free_release · next.
    원리 장면(recap_road, hyperlink, web_trio, postal_system, law_plain, today_web*)은 도형.
    (*today_web 은 소재 있으면 실사, 없으면 그래픽 몽타주 — 플레이스홀더 아님.)
    소재 부재 시 PLACEHOLDER 카드(장면명 표기)로 렌더가 소재 지연에 볼모 잡히지 않게 한다."""
    CLEAR_AFTER = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13}
    PLACEHOLDERS_USED = []  # 렌더에 실제 쓰인 플레이스홀더 장면명 (보고용)
    CTA = {"pos": RIGHT * 5.2 + DOWN * 2.6, "w": 2.3, "h": 0.8,
           "like": True, "buff": 0.25, "fs": (36, 30), "cc": DL}

    def intro(self):
        title = mtext("WWW", fs=110, color=INK).move_to(UP * 0.9)
        sub = ktext("모호하지만 흥미로움 — 웹의 탄생", fs=40, color=GRAY).next_to(title, DOWN, buff=0.5)
        num = chip("#03", BLUE, 30).to_corner(UL, buff=0.6)
        cc = Text("© nous-zero", font=KFONT, font_size=22, color=LGRAY).to_corner(DR, buff=0.45)
        self.claim_bottom(cc)   # 하단 띠의 정식 거주자 신고(감사 장부만 변경 — 화면 불변)
        self.play(FadeIn(title, scale=1.15), FadeIn(num), run_time=0.9)
        self.play(FadeIn(sub, shift=UP * 0.2), FadeIn(cc), run_time=0.7)
        self.wait(INTRO_D - 0.9 - 0.7 - 0.6)
        self.play(*[FadeOut(m) for m in (title, sub, num, cc)], run_time=0.6)

    # --- 공용 소품 ---
    def ep_photo(self, scene_name, height=5.0, pos=ORIGIN, framed=True):
        """실사 사료 로드 — 부재 시 장면명이 박힌 PLACEHOLDER 카드. (Group, is_placeholder) 반환."""
        p = find_asset(f"ep03_{scene_name}")
        if p:
            return self.photo(os.path.basename(p), height, pos, framed), False
        if scene_name not in Episode03.PLACEHOLDERS_USED:
            Episode03.PLACEHOLDERS_USED.append(scene_name)
        card = RoundedRectangle(corner_radius=0.2, width=height * 1.5, height=height)
        card.set_stroke(LGRAY, 4).set_fill("#E5E7EB", 1).move_to(pos)
        t1 = mtext("PLACEHOLDER", fs=40, color=GRAY)
        t2 = ktext(f"ep03_{scene_name}", 30, GRAY)
        tg = VGroup(t1, t2).arrange(DOWN, buff=0.28)
        if tg.width > card.width - 0.5:
            tg.scale_to_fit_width(card.width - 0.5)
        tg.move_to(card)
        return Group(card, tg), True

    def envelope_icon(self, w=2.0, h=1.3, color=BLUE):
        body = RoundedRectangle(corner_radius=0.08, width=w, height=h)
        body.set_stroke(color, 4).set_fill(WHITE, 1)
        flap = VGroup(Line(body.get_corner(UL), body.get_center() + UP * 0.06 * (h / 1.3)),
                      Line(body.get_corner(UR), body.get_center() + UP * 0.06 * (h / 1.3)))
        flap.set_stroke(color, 4)
        return VGroup(body, flap)

    def speech_bubble(self, lines, pos, color=INK, fs=24, min_w=3.6):
        txts = VGroup(*[ktext(l, fs, INK) for l in lines])
        txts.arrange(DOWN, buff=0.13, aligned_edge=LEFT)
        box = RoundedRectangle(corner_radius=0.22,
                               width=max(min_w, txts.width + 0.6),
                               height=txts.height + 0.55)
        box.set_stroke(color, 3).set_fill(WHITE, 1)
        txts.move_to(box)
        return VGroup(box, txts).move_to(pos)

    def doc_card(self, pos, w=4.2, h=4.8, nlines=7):
        """회색 글줄만 있는 문서 카드 — 초기 웹/하이퍼링크 연출용."""
        win = RoundedRectangle(corner_radius=0.2, width=w, height=h)
        win.set_stroke(INK, 4).set_fill(PAPER, 1).move_to(pos)
        lines = VGroup()
        left_x = win.get_left()[0] + 0.5
        top_y = win.get_top()[1] - 0.65
        for i in range(nlines):
            ln_w = w - 1.0 - (0.9 if i % 3 == 2 else 0)
            ln = Line(ORIGIN, RIGHT * ln_w).set_stroke(LGRAY, 5)
            ln.move_to([left_x + ln_w / 2, top_y - i * 0.55, 0])
            lines.add(ln)
        return VGroup(win, lines)

    # --- 0: 1989 메모 — "Vague but exciting" (실사) ---
    def seg00(self, S):
        def a0(d):
            date = chip("1989 — 스위스 CERN", INK, 26).to_corner(UL, buff=0.5)
            ph, _ = self.ep_photo("memo_three_words", height=5.0, pos=DOWN * 0.15)
            self.st["memo"] = ph
            t1 = max(0.3, min(0.7, d * 0.3))
            self.play(FadeIn(date, shift=DOWN * 0.2), run_time=0.3)
            self.show_photo(ph, t1)
            self.ken_burns(ph, d - t1 - 0.3, zoom=1.05)

        def a1(d):
            self.ken_burns(self.st["memo"], d, zoom=1.05, drift=DOWN * 0.1)

        def a2(d):
            ph = self.st["memo"]
            hl = RoundedRectangle(corner_radius=0.08, width=3.4, height=0.7)
            hl.set_fill(AMBER, 0.4).set_stroke(AMBER, 3)
            hl.move_to(ph[0].get_center() + UP * 1.3)
            words = chip("Vague but exciting", AMBER, 28)
            words.next_to(ph, RIGHT, buff=0.4).shift(UP * 1.2)
            if words.get_right()[0] > 6.9:
                words.next_to(ph, UP, buff=0.3)
            t1 = max(0.3, min(0.8, d * 0.35))
            self.play(FadeIn(hl, scale=1.2), run_time=t1)
            t2 = max(0.3, min(0.7, d * 0.3))
            self.play(FadeIn(words, scale=1.25), run_time=t2)
            self.hold(d - t1 - t2)

        def a3(d):
            stamp = chip("웹의 탄생을 승인한 도장", RED, 26).rotate(0.12)
            stamp.move_to(self.st["memo"][0].get_corner(DR) + UL * 1.1)
            t1 = max(0.3, min(0.7, d * 0.4))
            self.play(FadeIn(stamp, scale=1.6), run_time=t1)
            self.play(Flash(stamp.get_center(), color=RED, flash_radius=1.4),
                      run_time=min(0.5, max(0.3, d * 0.2)))
            self.hold(d - t1 - min(0.5, max(0.3, d * 0.2)))

        self.run_beats(S, [a0, a1, a2, a3])

    # --- 1: 지난 편 요약 — 도로는 깔렸는데 짐이 없다 (도형) ---
    def seg01(self, S):
        def a0(d):
            nodes, edges, _ = build_mesh(scale=0.62, shift=(0, 0.9))
            tag = chip("지난 편 — 인터넷 도로망", INK, 24).to_corner(UL, buff=0.5)
            env = self.envelope_icon(1.6, 1.05)
            env.move_to(DOWN * 1.9 + LEFT * 2.2)
            etag = chip("TCP/IP — 공통 언어", BLUE, 22).next_to(env, RIGHT, buff=0.45)
            self.st["mesh"] = VGroup(edges, nodes)
            self.st["env1"] = env
            self.act(d, Create(edges), FadeIn(nodes), FadeIn(tag),
                     FadeIn(env, scale=1.15), FadeIn(etag), rt=min(2.0, d * 0.7))

        def a1(d):
            q = ktext("그런데?", 60, RED, bold=True).move_to(UP * 0.9)
            self.st["q1"] = q
            self.act(d, FadeIn(q, scale=1.3), Wiggle(self.st["mesh"], scale_value=1.02))

        def a2(d):
            env = self.st["env1"]
            cargo = DashedVMobject(
                RoundedRectangle(corner_radius=0.08, width=0.8, height=0.5),
                num_dashes=14).set_stroke(RED, 3)
            cargo.move_to(env[0].get_center())
            none = chip("실어 나를 짐이 없다", RED, 26).move_to(DOWN * 3.0)
            t1 = max(0.3, min(0.7, d * 0.3))
            self.play(FadeOut(self.st.pop("q1")), FadeIn(cargo, scale=1.3), run_time=t1)
            t2 = max(0.3, min(0.8, d * 0.3))
            self.play(FadeIn(none, shift=UP * 0.2),
                      self.st["mesh"].animate.set_opacity(0.35), run_time=t2)
            self.hold(d - t1 - t2)

        self.run_beats(S, [a0, a1, a2])

    # --- 2: CERN — 무대 소개 (실사) ---
    def seg02(self, S):
        def a0(d):
            place = chip("스위스 제네바 — CERN", INK, 26).to_corner(UL, buff=0.5)
            ph, _ = self.ep_photo("cern_intro", height=5.2, pos=DOWN * 0.1)
            self.st["cern"] = ph
            self.play(FadeIn(place, shift=DOWN * 0.2), run_time=0.3)
            t1 = max(0.3, min(0.7, d * 0.3))
            self.show_photo(ph, t1)
            self.ken_burns(ph, d - t1 - 0.3, zoom=1.06)

        def a1(d):
            n = chip("연구자 수천 명 — 세계 최대 실험 장비", GRAY, 20)
            n.next_to(self.st["cern"], DOWN, buff=0.25)
            t1 = max(0.3, min(0.6, d * 0.25))
            self.play(FadeIn(n, shift=UP * 0.15), run_time=t1)
            self.ken_burns(self.st["cern"], d - t1, zoom=1.04, drift=UP * 0.1)

        def a2(d):
            q = chip("진짜 고질병은 물리학이 아니었다", RED, 26).move_to(UP * 3.1)
            self.act(d, FadeIn(q, scale=1.2))

        self.run_beats(S, [a0, a1, a2])

    # --- 3: 지식 손실 — 신참·고참 대화 (실사 + 말풍선) ---
    def seg03(self, S):
        def a0(d):
            ph, _ = self.ep_photo("knowledge_loss", height=3.8, pos=LEFT * 3.7 + UP * 0.7)
            who1 = chip("신참", BLUE, 22).move_to(RIGHT * 0.6 + UP * 2.75)
            self.st["kl"] = ph
            self.st["who1"] = who1
            t1 = max(0.3, min(0.7, d * 0.35))
            self.show_photo(ph, t1)
            t2 = max(0.3, min(0.5, d * 0.2))
            self.play(FadeIn(who1, scale=1.2), run_time=t2)
            self.hold(d - t1 - t2)

        def a1(d):
            b1 = self.speech_bubble(["3년 전 그 실험 자료,", "어디서 봅니까?"],
                                    RIGHT * 3.2 + UP * 1.9, BLUE, 24)
            self.st["b1"] = b1
            self.act(d, FadeIn(b1, shift=UP * 0.2))

        def a2(d):
            who2 = chip("고참", INK, 22).move_to(RIGHT * 0.6 + UP * 0.35)
            self.act(d, FadeIn(who2, scale=1.2))

        def a3(d):
            b2 = self.speech_bubble(["담당자는 작년에 떠났고,", "자료는 그 사람 컴퓨터에만.",
                                     "시스템이 달라 열어도 못 읽어."],
                                    RIGHT * 3.2 + DOWN * 0.7, INK, 22)
            self.act(d, FadeIn(b2, shift=UP * 0.2))

        def a4(d):
            phrase = ktext("사람이 떠나면, 지식도 떠난다", 36, RED, bold=True)
            phrase.move_to(DOWN * 2.5)
            ul = Underline(phrase, color=RED).set_stroke(RED, 6)
            self.act(d, FadeIn(phrase, scale=1.15), Create(ul), rt=min(1.2, d * 0.55))

        def a5(d):
            note = chip("대화는 각색 — 문제는 실제", GRAY, 20).move_to(DOWN * 3.25)
            self.act(d, FadeIn(note, shift=UP * 0.15))

        self.run_beats(S, [a0, a1, a2, a3, a4, a5])

    # --- 4: 1989 제안서 — 팀 버너스리 (실사) ---
    def seg04(self, S):
        def a0(d):
            yr = chip("1989", INK, 28).to_corner(UL, buff=0.5)
            ph, _ = self.ep_photo("proposal", height=4.8, pos=LEFT * 2.6 + UP * 0.15)
            self.st["prop"] = ph
            self.play(FadeIn(yr, shift=DOWN * 0.2), run_time=0.3)
            t1 = max(0.3, min(0.7, d * 0.3))
            self.show_photo(ph, t1)
            self.ken_burns(ph, d - t1 - 0.3, zoom=1.05)

        def a1(d):
            self.ken_burns(self.st["prop"], d, zoom=1.04, drift=UP * 0.1)

        def a2(d):
            t1txt = mtext("Information Management:", fs=28, color=INK)
            t2txt = mtext("A Proposal", fs=28, color=INK)
            t3txt = ktext("정보 관리, 하나의 제안", 26, GRAY)
            title = VGroup(t1txt, t2txt, t3txt).arrange(DOWN, buff=0.18)
            title.move_to(RIGHT * 3.6 + UP * 1.2)
            if title.width > 5.6:
                title.scale_to_fit_width(5.6)
            self.act(d, FadeIn(title, shift=UP * 0.2))

        def a3(d):
            name = chip("팀 버너스리", BLUE, 30).move_to(RIGHT * 3.6 + DOWN * 0.8)
            t1 = max(0.3, min(0.8, d * 0.4))
            self.play(FadeIn(name, scale=1.35), run_time=t1)
            self.play(Flash(name.get_center(), color=BLUE, flash_radius=1.5),
                      run_time=min(0.5, max(0.3, d * 0.2)))
            self.hold(d - t1 - min(0.5, max(0.3, d * 0.2)))

        self.run_beats(S, [a0, a1, a2, a3])

    # --- 5: 메모 클로즈업 — 실물이 남은 실화 (0번 소재 재사용·줌인) ---
    def seg05(self, S):
        def a0(d):
            ph, _ = self.ep_photo("memo_three_words", height=6.0, pos=DOWN * 0.1)
            boss = chip("상사 마이크 센달", GRAY, 22).to_corner(UL, buff=0.5)
            self.st["memo2"] = ph
            t1 = max(0.4, min(0.9, d * 0.35))
            self.show_photo(ph, t1)
            self.play(FadeIn(boss), run_time=0.3)
            self.ken_burns(ph, d - t1 - 0.3, zoom=1.06)

        def a1(d):
            ph = self.st["memo2"]
            hl = RoundedRectangle(corner_radius=0.08, width=3.8, height=0.8)
            hl.set_fill(AMBER, 0.4).set_stroke(AMBER, 3)
            hl.move_to(ph[0].get_center() + UP * 1.5)
            words = chip("Vague but exciting", AMBER, 30).move_to(UP * 3.15)
            t1 = max(0.3, min(0.7, d * 0.3))
            self.play(FadeIn(hl, scale=1.2), run_time=t1)
            t2 = max(0.3, min(0.7, d * 0.3))
            self.play(FadeIn(words, scale=1.25), run_time=t2)
            self.hold(d - t1 - t2)

        def a2(d):
            ok = chip("정식 결재 대신 — 조용한 실험 시간", INK, 24).move_to(DOWN * 3.0)
            self.act(d, FadeIn(ok, shift=UP * 0.2))

        def a3(d):
            real = chip("각색 아님 — 실물이 남아 있는 실화", RED, 24).rotate(0.1)
            real.move_to(self.st["memo2"][0].get_corner(DR) + UL * 1.2)
            t1 = max(0.3, min(0.7, d * 0.35))
            self.play(FadeIn(real, scale=1.4), run_time=t1)
            self.ken_burns(self.st["memo2"], d - t1, zoom=1.08)

        self.run_beats(S, [a0, a1, a2, a3])

    # --- 6: 하이퍼링크 — 단어를 누르면 건너뛴다 (도형) ---
    def seg06(self, S):
        def a0(d):
            head = chip("핵심 아이디어 — 딱 한 줄", INK, 26).move_to(UP * 3.2)
            docA = self.doc_card(LEFT * 3.5 + DOWN * 0.3)
            word = RoundedRectangle(corner_radius=0.08, width=1.35, height=0.45)
            word.set_stroke(BLUE, 3).set_fill("#DBEAFE", 1)
            word.move_to(docA[1][2].get_center() + UP * 0.02)
            wul = Line(word.get_corner(DL) + DOWN * 0.06,
                       word.get_corner(DR) + DOWN * 0.06).set_stroke(BLUE, 4)
            self.st["docA"] = docA
            self.st["word"] = VGroup(word, wul)
            self.act(d, FadeIn(head, shift=DOWN * 0.2), Create(docA[0]),
                     LaggedStart(*[Create(l) for l in docA[1]], lag_ratio=0.08),
                     FadeIn(self.st["word"]), rt=min(2.0, d * 0.7))

        def a1(d):
            word = self.st["word"]
            cursor = Triangle().scale(0.16).rotate(-PI / 5)
            cursor.set_fill(INK, 1).set_stroke(INK, 2)
            cursor.move_to(self.st["docA"][0].get_corner(DR) + UL * 0.6)
            t1 = max(0.3, min(0.6, d * 0.2))
            self.play(FadeIn(cursor, scale=1.3), run_time=t1)
            t2 = max(0.4, min(0.9, d * 0.25))
            self.play(cursor.animate.move_to(word.get_center() + DR * 0.12), run_time=t2)
            t3 = min(0.5, max(0.3, d * 0.15))
            self.play(Flash(word.get_center(), color=BLUE, flash_radius=1.0), run_time=t3)
            docB = self.doc_card(RIGHT * 3.5 + DOWN * 0.3, nlines=6)
            arc = ArcBetweenPoints(word.get_right() + RIGHT * 0.1,
                                   docB[0].get_top() + UP * 0.15, angle=-1.1)
            arc.set_stroke(BLUE, 5)
            self.st["arc"] = arc
            t4 = max(0.5, min(1.2, d * 0.3))
            self.play(Create(arc), FadeIn(docB, shift=UP * 0.2), run_time=t4)
            self.hold(d - t1 - t2 - t3 - t4)

        def a2(d):
            name = chip("하이퍼링크", BLUE, 38).move_to(UP * 2.0)
            t1 = max(0.4, min(0.9, d * 0.4))
            self.play(FadeIn(name, scale=1.4), run_time=t1)
            t2 = min(0.6, max(0.3, d * 0.25))
            self.play(Indicate(self.st["arc"], color=BLUE, scale_factor=1.05), run_time=t2)
            self.hold(d - t1 - t2)

        self.run_beats(S, [a0, a1, a2])

    # --- 7: 3요소 세트 — HTML/URL/HTTP 우편 비유 (도형) ---
    def trio_card(self, head, sub_label, color, pos, icon):
        b = RoundedRectangle(corner_radius=0.22, width=3.9, height=4.3)
        b.set_stroke(color, 4).set_fill(WHITE, 1).move_to(pos)
        h = mtext(head, fs=40, color=color).move_to(b.get_top() + DOWN * 0.55)
        s = ktext(sub_label, 26, GRAY).next_to(h, DOWN, buff=0.2)
        icon.move_to(b.get_center() + DOWN * 0.85)
        return VGroup(b, h, s, icon)

    def seg07(self, S):
        def a0(d):
            head = chip("발명 세 개 — 한 세트", INK, 28).move_to(UP * 3.2)
            self.act(d, FadeIn(head, shift=DOWN * 0.2))

        def a1(d):
            paper = Rectangle(width=1.5, height=2.0).set_stroke(INK, 3).set_fill(WHITE, 1)
            plines = VGroup(*[Line(ORIGIN, RIGHT * (1.0 - (0.3 if i == 3 else 0)))
                              .set_stroke(LGRAY, 4)
                              .move_to(paper.get_top() + DOWN * (0.4 + i * 0.35)
                                       + LEFT * (0.15 if i == 3 else 0))
                              for i in range(4)])
            icon = VGroup(paper, plines)
            card = self.trio_card("HTML", "문서 쓰는 공통 양식", BLUE,
                                  LEFT * 4.3 + DOWN * 0.4, icon)
            self.st["c_html"] = card
            self.act(d, FadeIn(card, scale=1.08), rt=min(1.2, d * 0.5))

        def a2(d):
            env = self.envelope_icon(1.7, 1.1, AMBER)
            addr = VGroup(*[Line(ORIGIN, RIGHT * 0.8).set_stroke(GRAY, 3)
                            for _ in range(2)]).arrange(DOWN, buff=0.14)
            addr.move_to(env[0].get_center() + DOWN * 0.18)
            icon = VGroup(env, addr)
            card = self.trio_card("URL", "문서마다 고유 주소", AMBER,
                                  DOWN * 0.4, icon)
            self.st["c_url"] = card
            self.act(d, FadeIn(card, scale=1.08), rt=min(1.2, d * 0.5))

        def a3(d):
            a = Dot(LEFT * 1.1 + DOWN * 0.25, radius=0.12, color=INK)
            b = Dot(RIGHT * 1.1 + DOWN * 0.25, radius=0.12, color=INK)
            ar = Arrow(a.get_center(), b.get_center(), buff=0.2, color=RED, stroke_width=6)
            env2 = self.envelope_icon(0.75, 0.5, RED).move_to(UP * 0.25)
            icon = VGroup(a, b, ar, env2)
            card = self.trio_card("HTTP", "주고받는 배달 규칙", RED,
                                  RIGHT * 4.3 + DOWN * 0.4, icon)
            link1 = Arrow(self.st["c_html"][0].get_right(),
                          self.st["c_url"][0].get_left(), buff=0.1,
                          color=LGRAY, stroke_width=5)
            link2 = Arrow(self.st["c_url"][0].get_right(),
                          card[0].get_left(), buff=0.1, color=LGRAY, stroke_width=5)
            t1 = max(0.4, min(1.0, d * 0.4))
            self.play(FadeIn(card, scale=1.08), run_time=t1)
            t2 = max(0.3, min(0.8, d * 0.3))
            self.play(GrowFromCenter(link1), GrowFromCenter(link2), run_time=t2)
            self.hold(d - t1 - t2)

        self.run_beats(S, [a0, a1, a2, a3])

    # --- 8: 3층 누적 — 도로망 → 공통 언어 → 우편 시스템 (도형, 2편 봉투 문법 통일) ---
    def seg08(self, S):
        def band(self_, label, color, y):
            b = RoundedRectangle(corner_radius=0.18, width=10.2, height=1.7)
            b.set_stroke(color, 4).set_fill(WHITE, 1).move_to(UP * y)
            lab = ktext(label, 28, INK, bold=True)
            lab.move_to(b.get_right() + LEFT * (lab.width / 2 + 0.5))
            return VGroup(b, lab)

        def a0(d):
            road = band(self, "인터넷 — 도로망", INK, -2.2)
            nodes, edges, _ = build_mesh(scale=0.28, shift=(-2.6, -2.2))
            self.st["l_road"] = VGroup(road, edges, nodes)
            self.act(d, FadeIn(road[0]), FadeIn(road[1]),
                     Create(edges), FadeIn(nodes), rt=min(1.8, d * 0.65))

        def a1(d):
            lang = band(self, "TCP/IP — 공통 언어", BLUE, -0.3)
            env = self.envelope_icon(1.3, 0.85).move_to(LEFT * 2.6 + DOWN * 0.3)
            web = band(self, "웹 — 우편 시스템", RED, 1.6)
            doc = Rectangle(width=0.8, height=1.0).set_stroke(RED, 3).set_fill(WHITE, 1)
            dlines = VGroup(*[Line(ORIGIN, RIGHT * 0.5).set_stroke(LGRAY, 3)
                              .move_to(doc.get_top() + DOWN * (0.25 + i * 0.22))
                              for i in range(3)])
            docg = VGroup(doc, dlines).move_to(LEFT * 2.6 + UP * 1.6)
            self.st["l_web"] = web
            self.act(d, LaggedStart(
                FadeIn(VGroup(lang, env), shift=UP * 0.3),
                FadeIn(VGroup(web, docg), shift=UP * 0.3), lag_ratio=0.45),
                rt=min(2.2, d * 0.7))

        def a2(d):
            env = self.envelope_icon(0.9, 0.6, RED)
            start = self.st["l_web"][0].get_left() + RIGHT * 0.8 + UP * 0.45
            end = self.st["l_web"][0].get_right() + LEFT * 0.8 + UP * 0.45
            env.move_to(start)
            t1 = max(0.3, min(0.5, d * 0.2))
            self.play(FadeIn(env, scale=1.2), run_time=t1)
            t2 = max(0.6, min(2.0, d * 0.5))
            self.play(MoveAlongPath(env, Line(start, end)), run_time=t2)
            self.hold(d - t1 - t2)

        self.run_beats(S, [a0, a1, a2])

    # --- 9: NeXT — 세계 최초의 웹서버 (실사) ---
    def seg09(self, S):
        def a0(d):
            yr = chip("1990 — 세계 최초의 웹서버", INK, 26).to_corner(UL, buff=0.5)
            ph, _ = self.ep_photo("next_server", height=5.0, pos=LEFT * 2.5 + DOWN * 0.1)
            self.st["next"] = ph
            self.play(FadeIn(yr, shift=DOWN * 0.2), run_time=0.3)
            t1 = max(0.3, min(0.7, d * 0.25))
            self.show_photo(ph, t1)
            nx = chip("NeXT 컴퓨터", GRAY, 20).next_to(ph, DOWN, buff=0.25)
            self.play(FadeIn(nx), run_time=0.3)
            self.ken_burns(ph, d - t1 - 0.6, zoom=1.05)

        def a1(d):
            ph = self.st["next"]
            hl = RoundedRectangle(corner_radius=0.08, width=2.2, height=1.0)
            hl.set_fill(AMBER, 0.35).set_stroke(AMBER, 3)
            hl.move_to(ph[0].get_center() + DOWN * 0.6)
            self.act(d, FadeIn(hl, scale=1.2))

        def a2(d):
            l1 = ktext("이 기계는 서버입니다.", 30, INK, bold=True)
            card = RoundedRectangle(corner_radius=0.15, width=l1.width + 0.7,
                                    height=l1.height + 1.5)
            card.set_stroke(INK, 3).set_fill(PAPER, 1)
            card.move_to(RIGHT * 3.7 + UP * 0.6)
            l1.move_to(card.get_center() + UP * 0.35)
            self.st["label_card"] = VGroup(card, l1)
            self.act(d, FadeIn(self.st["label_card"], scale=1.1))

        def a3(d):
            l2 = ktext("전원을 끄지 마시오.", 32, RED, bold=True)
            l2.move_to(self.st["label_card"][0].get_center() + DOWN * 0.4)
            t1 = max(0.3, min(0.8, d * 0.4))
            self.play(FadeIn(l2, scale=1.2), run_time=t1)
            t2 = min(0.6, max(0.3, d * 0.25))
            self.play(Wiggle(self.st["label_card"], scale_value=1.05), run_time=t2)
            self.hold(d - t1 - t2)

        self.run_beats(S, [a0, a1, a2, a3])

    # --- 10: 1991 공개 — 최초의 웹사이트 (실사) ---
    def seg10(self, S):
        def a0(d):
            yr = chip("1991 — 세상에 공개", INK, 26).to_corner(UL, buff=0.5)
            ph, _ = self.ep_photo("go_public", height=5.2, pos=DOWN * 0.1)
            self.st["pub"] = ph
            self.play(FadeIn(yr, shift=DOWN * 0.2), run_time=0.3)
            t1 = max(0.3, min(0.7, d * 0.25))
            self.show_photo(ph, t1)
            self.ken_burns(ph, d - t1 - 0.3, zoom=1.06)

        def a1(d):
            # 33자 = 상한(20자) 초과 → LEGAL_CAPTION_LEGACY 등록분(3편 발행본 소급 금지).
            # 4편부터는 같은 문구를 쓰면 빌드가 죽는다.
            cap = legal_chip("최초의 웹사이트 — '웹이란 무엇인가' 안내문 (재현 화면)", GRAY, 20)
            cap.next_to(self.st["pub"], DOWN, buff=0.25)
            t1 = max(0.3, min(0.6, d * 0.2))
            self.play(FadeIn(cap, shift=UP * 0.15), run_time=t1)
            self.ken_burns(self.st["pub"], d - t1, zoom=1.05, drift=UP * 0.12)

        self.run_beats(S, [a0, a1])

    # --- 11: 1993.4.30 — 웹을 공짜로 풀다 (실사) ---
    def seg11(self, S):
        def a0(d):
            date = chip("1993. 4. 30", RED, 28).to_corner(UL, buff=0.5)
            ph, _ = self.ep_photo("free_release", height=5.0, pos=DOWN * 0.1)
            self.st["free"] = ph
            self.play(FadeIn(date, shift=DOWN * 0.2), run_time=0.3)
            t1 = max(0.3, min(0.7, d * 0.25))
            self.show_photo(ph, t1)
            self.ken_burns(ph, d - t1 - 0.3, zoom=1.05)

        def a1(d):
            tag = chip("특허료 없이, 누구나", BLUE, 26).move_to(UP * 3.1)
            t1 = max(0.3, min(0.6, d * 0.25))
            self.play(FadeIn(tag, scale=1.2), run_time=t1)
            self.ken_burns(self.st["free"], d - t1, zoom=1.05)

        def a2(d):
            stamp = chip("무료 — 영원히", BLUE, 32).rotate(0.2)
            stamp.move_to(self.st["free"][0].get_corner(DR) + UL * 1.2)
            t1 = max(0.3, min(0.7, d * 0.35))
            self.play(FadeIn(stamp, scale=1.7), run_time=t1)
            self.play(Flash(stamp.get_center(), color=BLUE, flash_radius=1.6),
                      run_time=min(0.5, max(0.3, d * 0.2)))
            self.hold(d - t1 - min(0.5, max(0.3, d * 0.2)))

        self.run_beats(S, [a0, a1, a2])

    # --- 12: 오늘의 웹 — 몽타주 (소재 있으면 실사, 없으면 그래픽) ---
    def seg12(self, S):
        real = find_asset("ep03_today_web")

        def a0(d):
            if real:
                ph = self.photo(os.path.basename(real), height=5.2, pos=DOWN * 0.1)
                self.st["today"] = ph
                t1 = max(0.3, min(0.8, d * 0.3))
                self.show_photo(ph, t1)
                self.ken_burns(ph, d - t1, zoom=1.06)
                return
            wins = Group()
            icons = ["play", "cart", "doc", "chat", "grid", "video"]
            pos_grid = [LEFT * 3.9 + UP * 1.8, UP * 1.8, RIGHT * 3.9 + UP * 1.8,
                        LEFT * 3.9 + DOWN * 0.4, DOWN * 0.4, RIGHT * 3.9 + DOWN * 0.4]
            for kind, p in zip(icons, pos_grid):
                w = RoundedRectangle(corner_radius=0.15, width=3.0, height=1.9)
                w.set_stroke(INK, 3).set_fill(WHITE, 1).move_to(p)
                bar = Line(w.get_corner(UL) + DOWN * 0.4, w.get_corner(UR) + DOWN * 0.4)
                bar.set_stroke(LGRAY, 2)
                dots = VGroup(*[Dot(radius=0.045, color=LGRAY) for _ in range(3)])
                dots.arrange(RIGHT, buff=0.12)
                dots.move_to(w.get_corner(UL) + RIGHT * 0.42 + DOWN * 0.2)
                if kind in ("play", "video"):
                    ic = Triangle().scale(0.22).rotate(-PI / 2)
                    ic.set_fill(RED, 1).set_stroke(RED, 2)
                elif kind == "cart":
                    ic = VGroup(RoundedRectangle(corner_radius=0.05, width=0.55, height=0.4)
                                .set_stroke(AMBER, 4),
                                Dot(radius=0.05, color=AMBER).shift(DOWN * 0.32 + LEFT * 0.15),
                                Dot(radius=0.05, color=AMBER).shift(DOWN * 0.32 + RIGHT * 0.15))
                elif kind == "chat":
                    ic = RoundedRectangle(corner_radius=0.18, width=0.6, height=0.42)
                    ic.set_stroke(BLUE, 4)
                elif kind == "grid":
                    ic = VGroup(*[RoundedRectangle(corner_radius=0.04, width=0.24, height=0.24)
                                  .set_stroke(GRAY, 3) for _ in range(4)])
                    ic.arrange_in_grid(rows=2, buff=0.08)
                else:
                    ic = VGroup(*[Line(ORIGIN, RIGHT * 0.6).set_stroke(LGRAY, 4)
                                  .shift(DOWN * i * 0.16) for i in range(3)])
                ic.move_to(w.get_center() + DOWN * 0.2)
                wins.add(VGroup(w, bar, dots, ic))
            self.st["wins"] = wins
            self.act(d, LaggedStart(*[FadeIn(w, scale=1.1) for w in wins],
                                    lag_ratio=0.12), rt=min(2.4, d * 0.7))

        def a1(d):
            base = RoundedRectangle(corner_radius=0.15, width=11.5, height=0.9)
            base.set_stroke(BLUE, 4).set_fill("#DBEAFE", 1).move_to(DOWN * 2.35)
            blab = ktext("1993 — 공짜가 된 기술", 26, BLUE, bold=True).move_to(base)
            iff = chip("사용료를 물렸다면 — 지금의 웹은 없다", RED, 22).move_to(DOWN * 3.3)
            t1 = max(0.4, min(0.9, d * 0.35))
            self.play(FadeIn(VGroup(base, blab), shift=UP * 0.2), run_time=t1)
            t2 = max(0.3, min(0.8, d * 0.3))
            self.play(FadeIn(iff, scale=1.15), run_time=t2)
            self.hold(d - t1 - t2)

        self.run_beats(S, [a0, a1])

    # --- 13: 법칙 — 글자만 있던 초기 웹 (도형) ---
    def seg13(self, S):
        def a0(d):
            num = chip("이 시리즈의 법칙", BLUE, 28).move_to(UP * 2.9)
            self.st["lawnum"] = num
            self.act(d, FadeIn(num, shift=DOWN * 0.2))

        def a1(d):
            p1 = ktext("모든 해결은,", fs=48, color=INK, bold=True)
            p2 = chip("새로운 문제", BLUE, 40)
            p3 = ktext("를 낳는다", fs=48, color=INK, bold=True)
            law = VGroup(p1, p2, p3).arrange(RIGHT, buff=0.28).move_to(UP * 1.9)
            self.st["law"] = law
            self.act(d, FadeIn(law, scale=1.12), rt=min(1.2, d * 0.55))

        def a2(d):
            win = self.doc_card(DOWN * 1.1, w=7.2, h=3.9, nlines=5)
            tag = chip("초기 웹 — 글자뿐", GRAY, 22)
            tag.move_to(win[0].get_corner(UL) + RIGHT * (tag.width / 2 + 0.15)
                        + DOWN * (tag.height / 2 + 0.15))
            self.st["plain"] = win
            self.act(d, Create(win[0]),
                     LaggedStart(*[Create(l) for l in win[1]], lag_ratio=0.1),
                     FadeIn(tag), rt=min(1.8, d * 0.65))

        def a3(d):
            slot = DashedVMobject(Rectangle(width=1.9, height=1.3), num_dashes=22)
            slot.set_stroke(LGRAY, 3)
            slot.move_to(self.st["plain"][0].get_right() + LEFT * 1.5 + DOWN * 0.5)
            x = VGroup(Line(UL * 0.3, DR * 0.3), Line(UR * 0.3, DL * 0.3))
            x.set_stroke(RED, 6).move_to(slot)
            cap = chip("사진 한 장 못 띄움", GRAY, 20).next_to(slot, DOWN, buff=0.2)
            self.st["slot"] = slot
            self.st["slotx"] = x
            self.act(d, Create(slot), FadeIn(x, scale=1.3), FadeIn(cap))

        def a4(d):
            pic = Rectangle(width=1.9, height=1.3).set_stroke(BLUE, 4).set_fill("#DBEAFE", 1)
            mount = Triangle().scale(0.3).set_fill(BLUE, 1).set_stroke(BLUE, 2)
            mount.move_to(pic.get_center() + DOWN * 0.2)
            sun = Circle(radius=0.13).set_fill(AMBER, 1).set_stroke(AMBER, 2)
            sun.move_to(pic.get_center() + UP * 0.3 + RIGHT * 0.5)
            img = VGroup(pic, mount, sun).move_to(self.st["slot"].get_center())
            flip = chip("그림이 뜨는 순간 — 판이 뒤집힌다", RED, 24).move_to(UP * 0.6)
            t1 = max(0.3, min(0.7, d * 0.3))
            self.play(FadeOut(self.st.pop("slotx")), FadeIn(img, scale=1.2), run_time=t1)
            t2 = min(0.5, max(0.3, d * 0.2))
            self.play(Flash(img.get_center(), color=BLUE, flash_radius=1.4), run_time=t2)
            t3 = max(0.3, min(0.8, d * 0.3))
            self.play(FadeIn(flip, scale=1.2),
                      Wiggle(self.st["plain"], scale_value=1.03), run_time=t3)
            self.hold(d - t1 - t2 - t3)

        self.run_beats(S, [a0, a1, a2, a3, a4])

    # --- 14: 질문 + 예고 + CTA (실사 예고컷 + 도형) ---
    def seg14(self, S):
        def a0(d):
            t = ktext("여러분이 CERN이었다면, 공짜로 풀 수 있었을까요?", 32, INK, bold=True)
            box = RoundedRectangle(corner_radius=0.25, width=t.width + 0.8,
                                   height=t.height + 0.7)
            box.set_stroke(INK, 4).set_fill(PAPER, 1)
            tail = Triangle().scale(0.22).rotate(PI)
            tail.set_stroke(INK, 4).set_fill(PAPER, 1)
            tail.move_to(box.get_bottom() + DOWN * 0.16 + LEFT * 2.2)
            bubble = VGroup(box, tail, t.move_to(box)).move_to(UP * 2.2)
            self.st["bubble"] = bubble
            self.act(d, FadeIn(bubble, scale=1.1))

        def a1(d):
            cmt = chip("댓글로", BLUE, 28).next_to(self.st["bubble"], DOWN, buff=0.4)
            self.act(d, FadeIn(cmt, shift=UP * 0.2),
                     Indicate(self.st["bubble"], color=BLUE, scale_factor=1.03))

        def a2(d):
            # 아웃트로 결함 2건 수리(2026-07-30 191.5초 프레임 실측 → release-director 지적).
            #  ①예고 부제가 우하단 구독 버튼 밑으로 파묻힘(가로 1.19 세로 0.10 겹침)
            #    + 예고 사진과도 겹침(가로 0.79 세로 0.33) — 프레임 안이라 fit_frame() 무력.
            #    → CTA 자리를 미리 예약(reserve_cta)하고, 사진·CTA를 피한 '남는 칸' 폭을
            #      실측해(free_x_band) 그 폭에 맞춰 줄바꿈(ktext_block)한다.
            #  ②최초 웹사이트 화면(ep03_next.png = ep03_first_website.png, md5 동일)에
            #    '재현 화면' 표기 누락 — 본문 seg10 에는 있는데 아웃트로에는 빠져 있어,
            #    나란한 '#04 모자이크' 예고 때문에 모자이크 화면으로 오인될 수 있었다
            #    (법무 조건-2 재현 표기의 취지). seg10 과 같은 양식의 캡션을 붙인다.
            # 세로 예산: 댓글로 칩 아래(0.28) ~ © 배지 위(-3.37) = 3.65 안에
            # [사진 + 여백 0.22 + 캡션 0.70] 이 들어가야 한다 → 사진 높이 상한 약 2.41.
            # 표기를 넣느라 사진을 2.6→2.3 으로 줄인 것(7% 축소, 좌측 여백은 그대로).
            # 이 수치는 눈대중이 아니라 --layout-audit 이 © 배지 침범 1.68×0.23 을
            # 적발해서 나온 값이다.
            self.reserve_cta()
            ph, _ = self.ep_photo("next", height=2.3, pos=LEFT * 3.9 + DOWN * 1.05)
            cap = legal_chip("최초의 웹사이트 (재현 화면)", GRAY, 20)
            cap.next_to(ph, DOWN, buff=0.22)
            shot = Group(ph, cap)          # 사진과 표기는 한 덩어리로 뜨고 진다
            # 예고컷도 보호 영역으로 등록 — 예고 문구가 사진 위로 올라타지 못하게
            # 기계로 막는다(예전엔 #04 태그가 사진 테두리를 0.25 밟고 있었다).
            self.reserve_zone("예고컷(재현 화면)", shot, owners=[shot, ph, cap])
            tag = chip("#04 — 모자이크 & 넷스케이프", INK, 28)
            tag.move_to(RIGHT * 1.6 + DOWN * 1.1)
            self.avoid_zones(tag)          # 사진·CTA 를 침범하면 자동으로 비켜 간다
            band_l, band_r, band_w = self.free_x_band(-2.75, -1.6, anchor=1.6)
            teaser = ktext_block("밋밋한 웹에 처음 그림을 띄운, 대학 시급 알바생", 24, GRAY,
                                 max_width=band_w, aligned_edge=LEFT)
            teaser.next_to(tag, DOWN, buff=0.26, aligned_edge=LEFT)
            if teaser.get_right()[0] > band_r:      # 왼쪽 정렬로 넘치면 남는 칸 안으로
                teaser.shift(RIGHT * (band_r - teaser.get_right()[0]))
            if teaser.get_left()[0] < band_l:
                teaser.shift(RIGHT * (band_l - teaser.get_left()[0]))
            t1 = max(0.3, min(0.7, d * 0.3))
            self.show_photo(shot, t1)
            t2 = max(0.3, min(0.8, d * 0.3))
            self.play(FadeIn(tag, scale=1.15), FadeIn(teaser, shift=UP * 0.15), run_time=t2)
            self.hold(d - t1 - t2)

        def a3(d):
            self.show_cta(d)

        self.run_beats(S, [a0, a1, a2, a3])


# ---------- 4편 팔레트 (썸네일 스펙 §8 전달 메모 — 시각 언어 통일) -----------------
EP04_PAPER = "#F6F1E4"    # 차트 지면(썸네일 인셋과 동일)
EP04_GREEN = "#0E7B3D"    # 상승선
EP04_RED = "#B91C1C"      # 최고점
CRT_BG = "#0A0F0C"        # 재현 시세판 배경(검은 CRT)
CRT_GREEN = "#22C55E"     # 시세판 상승 표시
CRT_DIM = "#4B5563"       # 시세판 보조 글자


class Episode04(Episode03):
    """4편: Mosaic·Netscape — 1995-08-09 상장, NSCP 한 종목 개장 약 2시간 지연.

    Episode03 을 상속하지만 **재사용하는 것은 소품 헬퍼 3개뿐**이다
    (speech_bubble·envelope_icon·doc_card — 편 무관 도형). seg00~14·intro·ep_photo·
    CTA 는 전부 여기서 재정의하며, construct 가 15세그 전수 정의를 기계 검사한다
    (상속의 함정: seg 하나를 빠뜨리면 3편 장면이 3편 소재로 조용히 렌더된다).

    저작권 지형이 1~3편과 정반대다(legal-review-ep04 §0): 보고 싶은 화면 전부가
    살아있는 기업의 저작물·상표(🔴 금지 9건 — Mosaic 실캡처·Netscape N·모질라 공룡·
    나스닥 로고·IE·신문 1면 등). 그래서 이 편은 "사료를 구해 오는 편"이 아니라
    **"데이터 그래픽으로 짓는 편"**이다 — 시각 클라이맥스는 seg11 주가 재현 차트
    (28→71→74.75→58.25, 저작권 0), UI 는 전부 관용 문법 재현 + 「재현 화면」 표기.

    4편은 이 조립기의 새 문법(2026-07-30 안전장치)의 첫 실전이다:
    legal_chip 20자×3.5초 · 자동 보호구역 **차단**(ZONE_STRICT_FROM_EP=4 — 사진 위
    도장은 claim_all_photos, 하단 진입은 claim_bottom 신고 필수) · 실사용 manifest.
    배치는 thumbnail-spec §7-2: 법무 캡션 기본 우상단, y −3.10 아래 신규 배치 금지."""
    CLEAR_AFTER = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13}
    PLACEHOLDERS_USED = []
    CTA = {"pos": RIGHT * 5.2 + DOWN * 2.6, "w": 2.3, "h": 0.8,
           "like": True, "buff": 0.25, "fs": (36, 30), "cc": DL}

    def construct(self):
        # 상속 함정 방어: seg00~14 가 **이 클래스에** 전부 정의돼 있어야 렌더를 시작한다.
        missing = [f"seg{k:02d}" for k in range(15)
                   if f"seg{k:02d}" not in type(self).__dict__]
        if missing:
            raise RuntimeError(f"Episode04 미정의 세그 {missing} — 상속으로 3편 장면이 "
                               f"대신 렌더되는 것을 차단한다")
        super().construct()
        self._write_pending_assets()

    def _write_pending_assets(self):
        """소재 미도착으로 PLACEHOLDER 가 쓰인 슬롯을 파일로 남긴다(rule6 — 임의 대체 금지).
        asset-scout 조달분이 도착하면 이 목록이 곧 재렌더 체크리스트다."""
        path = os.path.join(OUT, "_PENDING_ASSETS.txt")
        lines = ["4편 소재 대기 목록 — 렌더에 PLACEHOLDER 로 표시된 슬롯 (자동 생성)",
                 "도착 시 같은 파일명(video/output/assets/ep04_*.jpg|png)으로 넣고 재렌더하면 자동 편입된다.",
                 ""]
        if self.PLACEHOLDERS_USED:
            lines += [f"- ep04_{s} (PLACEHOLDER 렌더됨)" for s in self.PLACEHOLDERS_USED]
        else:
            lines.append("- 없음 — 전 실사 슬롯 충족")
        lines += ["",
                  "[편입 결정 기록 — 2026-07-30 §16 이후 (배제는 전부 판정 근거 있음)]",
                  "- seg3: IMG-21(quad_pano, TASL 「Schwen, CC BY-SA」)+IMG-19(Altgeld, PD) 편입.",
                  "  IMG-03 배제(§16-2 조건⑥ NCSA 지칭 금지 ↔ seg3=NCSA 지칭 구간),",
                  "  IMG-23 배제(§16 판정 3건에 미포함 = 초상 미판정 — 판정 시 편입 가능).",
                  "- seg7: IMG-13(SGI, CC0) 주 비주얼 + IMG-09(클라크) 저해상 인셋(대장 조건).",
                  "  §16 확정 캡션 「Knnkanda, CC BY-SA」+「클라크 (연대 미상)」 동시 노출.",
                  "- seg13: MS 건물 사진(IMG-14~16)은 2015~16 촬영 = 1995 장면 직배치 금지(대장",
                  "  조건) → 실루엣 연출이 최종이다. find_asset('ep04_ms_campus') 분기는 해당",
                  "  파일명이 없어 영구 미발동(의도).",
                  "- seg0/10: 재현 시세판이 주력(counsel §4·썸네일 문법 일치). IMG-17/18 실사는",
                  "  '나스닥 오인 결합 금지'(§16-2 조건⑥) 탓에 나스닥 지칭 구간인 이 세그들에",
                  "  넣지 않는다 — 시대 공기 B롤이 필요해지면 별도 회부.",
                  "- seg06 웹 성장·seg12 지수: EP04-DAT-01/03 수치 도착 — 차트 업그레이드는",
                  "  선택 과업으로 남김(현행 정성 연출도 판정 통과 상태)."]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"[v2] 소재 대기 {len(self.PLACEHOLDERS_USED)}건 → {os.path.basename(path)}")

    # --- 인트로 ---
    def intro(self):
        title = mtext("NETSCAPE", fs=96, color=INK).move_to(UP * 0.9)
        sub = ktext("그림이 뜨자, 세상이 몰려왔다 — 모자이크 & 넷스케이프", fs=38,
                    color=GRAY).next_to(title, DOWN, buff=0.5)
        num = chip("#04", BLUE, 30).to_corner(UL, buff=0.6)
        cc = Text("© nous-zero", font=KFONT, font_size=22, color=LGRAY).to_corner(DR, buff=0.45)
        self.claim_bottom(cc)   # 하단 띠의 정식 거주자 신고(감사 장부만 변경 — 화면 불변)
        self.play(FadeIn(title, scale=1.15), FadeIn(num), run_time=0.9)
        self.play(FadeIn(sub, shift=UP * 0.2), FadeIn(cc), run_time=0.7)
        self.wait(INTRO_D - 0.9 - 0.7 - 0.6)
        self.play(*[FadeOut(m) for m in (title, sub, num, cc)], run_time=0.6)

    # --- 공용 소품 ---
    def ep_photo(self, scene_name, height=5.0, pos=ORIGIN, framed=True):
        """실사 사료 로드 — 부재 시 장면명이 박힌 PLACEHOLDER 카드. (Group, is_placeholder) 반환."""
        p = find_asset(f"ep04_{scene_name}")
        if p:
            return self.photo(os.path.basename(p), height, pos, framed), False
        if scene_name not in Episode04.PLACEHOLDERS_USED:
            Episode04.PLACEHOLDERS_USED.append(scene_name)
        card = RoundedRectangle(corner_radius=0.2, width=height * 1.5, height=height)
        card.set_stroke(LGRAY, 4).set_fill("#E5E7EB", 1).move_to(pos)
        t1 = mtext("PLACEHOLDER", fs=40, color=GRAY)
        t2 = ktext(f"ep04_{scene_name}", 30, GRAY)
        tg = VGroup(t1, t2).arrange(DOWN, buff=0.28)
        if tg.width > card.width - 0.5:
            tg.scale_to_fit_width(card.width - 0.5)
        tg.move_to(card)
        return Group(card, tg), True

    def cap_ur(self, cap, host, buff=0.3):
        """법무 캡션을 host(재현 패널) 우상단 안쪽에 놓는다 — thumbnail-spec §7-2 규칙 1.
        패널은 photo() 산 사진이 아니므로 자동 사진 구역이 없다(신고 불요)."""
        cap.move_to(host.get_corner(UR)
                    + LEFT * (cap.width / 2 + buff) + DOWN * (cap.height / 2 + buff))
        return cap

    def ticker_panel(self, w=10.0, h=4.4, pos=UP * 0.35, nscp_price="--.--"):
        """재현 시세판(검은 CRT·모노스페이스) — counsel §4 seg0 대체안 그대로.
        나스닥 로고 0·MarketSite 0·실존 타사 티커 0(가공 티커만 — 썸네일 스펙 §4 준수).
        반환: (panel_group, nscp_row, nscp_price_text)"""
        panel = RoundedRectangle(corner_radius=0.2, width=w, height=h)
        panel.set_stroke(CRT_DIM, 3).set_fill(CRT_BG, 1).move_to(pos)
        rows_spec = [("VTLK", "12.38", "+0.25", CRT_GREEN),
                     ("DYNC", " 8.10", "-0.13", CRT_DIM),
                     ("NSCP", nscp_price, "     ", AMBER),
                     ("MERX", "21.05", "+0.40", CRT_GREEN)]
        rows = VGroup()
        price_t = None
        nscp_row = None
        for i, (tk, px, chg, col) in enumerate(rows_spec):
            y = panel.get_top()[1] - 1.6 - i * 0.78   # 첫 행을 캡션(우상단) 아래로
            t_tk = mtext(tk, fs=30, color=col)
            t_px = mtext(px, fs=30, color=col)
            t_ch = mtext(chg, fs=26, color=col, bold=False)
            t_tk.move_to([panel.get_left()[0] + 1.5, y, 0])
            t_px.move_to([panel.get_center()[0] - 0.4, y, 0])
            t_ch.move_to([panel.get_right()[0] - 1.6, y, 0])
            row = VGroup(t_tk, t_px, t_ch)
            rows.add(row)
            if tk == "NSCP":
                nscp_row, price_t = row, t_px
        band = RoundedRectangle(corner_radius=0.08, width=w - 0.5, height=0.66)
        band.set_fill(AMBER, 0.14).set_stroke(AMBER, 2)
        band.move_to([panel.get_center()[0], nscp_row.get_center()[1], 0])
        return Group(panel, band, rows), nscp_row, price_t

    # --- 0: 1995-08-09 훅 — 한 종목이 열리지 않는다 (재현 시세판) ---
    def seg00(self, S):
        def a0(d):
            date = chip("1995. 8. 9 — 나스닥", INK, 26).to_corner(UL, buff=0.5)
            board, nscp, _ = self.ticker_panel()
            self.st["board"], self.st["nscp"] = board, nscp
            cap = legal_chip("시세판 (재현 화면)", GRAY, 20)
            self.cap_ur(cap, board[0])
            self.st["cap0"] = cap
            self.play(FadeIn(date, shift=DOWN * 0.2), run_time=0.3)
            t1 = max(0.3, min(0.8, d * 0.35))
            self.play(FadeIn(board), FadeIn(cap), run_time=t1)
            self.hold(d - t1 - 0.3)

        def a1(d):
            tag = chip("주문 폭주 — 첫 거래 지연", RED, 26)
            tag.next_to(self.st["board"][0], DOWN, buff=0.3)
            t1 = max(0.3, min(0.6, d * 0.3))
            self.play(FadeIn(tag, scale=1.2),
                      Indicate(self.st["nscp"], color=AMBER, scale_factor=1.06),
                      run_time=t1)
            t2 = min(0.5, max(0.3, d * 0.2))
            self.play(Flash(self.st["nscp"].get_center(), color=AMBER, flash_radius=1.5),
                      run_time=t2)
            self.hold(d - t1 - t2)

        def a2(d):
            who = chip("창업 16개월 — 아직 적자", INK, 26).move_to(UP * 3.1)
            self.act(d, FadeIn(who, shift=DOWN * 0.2))

        self.run_beats(S, [a0, a1, a2])

    # --- 1: 지난 편 회수 — 공짜가 된 웹 (재사용 실사 2건 + 표기 승계) ---
    def seg01(self, S):
        def a0(d):
            tag = chip("지난 편 — 웹, 공짜가 되다", INK, 24).to_corner(UL, buff=0.5)
            # EP03-IMG-09 재사용(© CERN 크레딧 승계 — counsel §4 seg1 조건)
            ph = self.photo("ep03_free_release.jpg", height=3.8, pos=LEFT * 3.4 + UP * 0.5)
            cap = legal_chip("© CERN", GRAY, 20).next_to(ph, DOWN, buff=0.22)
            shot = Group(ph, cap)          # 소재-표기 동시 노출(counsel §6-3 결합 규칙)
            self.st["free"] = shot
            self.play(FadeIn(tag, shift=DOWN * 0.2), run_time=0.3)
            t1 = max(0.3, min(0.7, d * 0.3))
            self.show_photo(shot, t1)
            self.ken_burns(shot, d - t1 - 0.3, zoom=1.04)

        def a1(d):
            # EP03-IMG-08 재사용("재현 화면" 표기 승계 — KB §7)
            ph = self.photo("ep03_next.png", height=3.6, pos=RIGHT * 3.3 + UP * 0.55)
            cap = legal_chip("최초의 웹사이트 (재현 화면)", GRAY, 20)
            cap.next_to(ph, DOWN, buff=0.22)
            shot = Group(ph, cap)
            self.st["site"] = shot
            t1 = max(0.3, min(0.7, d * 0.3))
            self.show_photo(shot, t1)
            self.ken_burns(shot, d - t1, zoom=1.04)

        def a2(d):
            why = chip("그런데 — 다들 안 씀", RED, 28).move_to(DOWN * 2.5)
            self.act(d, FadeIn(why, scale=1.25),
                     Wiggle(self.st["site"], scale_value=1.02))

        self.run_beats(S, [a0, a1, a2])

    # --- 2: 글자뿐인 웹 (재현 터미널) ---
    def seg02(self, S):
        def a0(d):
            term = RoundedRectangle(corner_radius=0.2, width=9.2, height=4.6)
            term.set_stroke(CRT_DIM, 3).set_fill(CRT_BG, 1).move_to(UP * 0.35)
            lines = VGroup()
            for i, wfrac in enumerate((0.8, 0.62, 0.72, 0.5, 0.66, 0.4)):
                ln = Line(ORIGIN, RIGHT * (term.width - 1.6) * wfrac)
                ln.set_stroke(CRT_GREEN, 6, opacity=0.75)
                ln.move_to(term.get_corner(UL) + RIGHT * (0.8 + ln.get_length() / 2)
                           + DOWN * (0.8 + i * 0.56))
                lines.add(ln)
            cap = legal_chip("초기 웹 (재현 화면)", GRAY, 20)
            self.cap_ur(cap, term)
            self.st["term"] = term
            t1 = max(0.3, min(0.8, d * 0.35))
            self.play(FadeIn(term), FadeIn(cap), run_time=t1)
            t2 = max(0.3, min(1.0, d * 0.3))
            self.play(LaggedStart(*[Create(l) for l in lines], lag_ratio=0.15), run_time=t2)
            self.hold(d - t1 - t2)

        def a1(d):
            # 사진은 따로 내려받아 딴 프로그램으로 — 파일 칩이 별창으로 이동
            file_chip = chip("image.gif — 내려받기", AMBER, 20)
            file_chip.move_to(self.st["term"].get_center() + DOWN * 1.2)
            viewer = RoundedRectangle(corner_radius=0.15, width=2.6, height=2.0)
            viewer.set_stroke(LGRAY, 3).set_fill(WHITE, 1)
            viewer.move_to(RIGHT * 5.3 + DOWN * 1.6)   # 우측 여백(터미널 모서리에 겹침 허용)
            vlabel = ktext("다른 프로그램", 20, GRAY).move_to(viewer)
            t1 = max(0.3, min(0.6, d * 0.3))
            self.play(FadeIn(file_chip, scale=1.2), run_time=t1)
            t2 = max(0.3, min(0.8, d * 0.35))
            self.play(FadeIn(viewer), FadeIn(vlabel),
                      file_chip.animate.move_to(viewer.get_top() + UP * 0.35), run_time=t2)
            self.hold(d - t1 - t2)

        def a2(d):
            ok = chip("학자 — 충분", GRAY, 24).move_to(DOWN * 2.5 + LEFT * 2.6)
            no = chip("보통 사람 — 불편", RED, 24).move_to(DOWN * 2.5 + RIGHT * 2.6)
            self.act(d, FadeIn(ok, shift=UP * 0.15), FadeIn(no, shift=UP * 0.15))

        self.run_beats(S, [a0, a1, a2])

    # --- 3: NCSA 알바생 — 시급 $6.85 (실사 + 각색 대화) ---
    # 소재 선정 기록(2026-07-30 §16 편입): 전산실 실사 후보 2건을 **배제**하고 캠퍼스
    # 건물 2컷으로 간다 — IMG-03(전산실 군중)은 §16-2 조건⑥ "NCSA·일리노이 지칭 동기화
    # 금지"가 이 세그(NCSA 지칭 구간)와 정면 충돌, IMG-23(1995 전산실)은 §16 판정
    # 3건(03·04·18)에 포함되지 않아 초상 미판정. 판정 없는 소재는 넣지 않는다(rule6).
    def seg03(self, S):
        def a0(d):
            place = chip("일리노이대 — NCSA", INK, 26).to_corner(UL, buff=0.5)
            # EP04-IMG-21 (CC BY-SA 4.0, Daniel Schwen). 대장 표기 "TASL 20자"는 오계수
            # (`Daniel Schwen, CC BY-SA 4.0` = 27자) — §16-1 축약 일반형 「<성>, CC <종류>」
            # 적용 = 16자. 전체 TASL 은 설명란 전문(§16-1 유효 조건, channel-adapter 관할).
            # ep_photo 2번째 반환값 = "자리표시자인가"(True=소재 없음). 실물일 때만
            # TASL 캡션을 단다. (r4 사고: 이 값을 real 로 잘못 읽어 논리가 뒤집혀
            # 사진은 들어가고 §16 캡션만 빠진 채 감사를 통과했다 — 캡션이 아예 안
            # 만들어지면 지속 검사의 대상조차 안 된다. 매니페스트 캡션 계수 대조로 적발.)
            ph, is_ph = self.ep_photo("uiuc_quad_pano", height=3.9, pos=DOWN * 0.3)
            shot = ph
            if not is_ph:
                # 파노라마 우하단 '안쪽' 워터마크 배치 — 사진 완전 포함 = 사진 구역
                # 통과·자막 대역 진입 0 (r5 실측: 사진 아래 배치는 켄 번즈 확대분이
                # 자막 대역을 0.18 물었다).
                cap = legal_chip("Schwen, CC BY-SA", GRAY, 18)
                cap.move_to(ph.get_corner(DR)
                            + LEFT * (cap.width / 2 + 0.35) + UP * (cap.height / 2 + 0.3))
                shot = Group(ph, cap)
            self.st["campus"] = shot
            self.play(FadeIn(place, shift=DOWN * 0.2), run_time=0.3)
            t1 = max(0.3, min(0.7, d * 0.3))
            self.show_photo(shot, t1)
            self.ken_burns(shot, d - t1 - 0.3, zoom=1.04)

        def a1(d):
            # 문장 2 = "시간당 6달러 85센트짜리 알바" → 시급 카드가 이 문장의 비주얼이다.
            # 겸사겸사 캠퍼스(TASL 캡션 포함)가 2문장을 살아 캡션 지속 여유가 두 배가 된다
            # (r6 실측 4.54초는 통과였지만 실음성이 추정보다 짧아지는 3편 경향 대비).
            wage = VGroup(mtext("$6.85", fs=64, color=AMBER),
                          ktext("시간당 — 실제 기록", 24, GRAY))
            wage.arrange(DOWN, buff=0.18).move_to(RIGHT * 4.9 + UP * 2.4)
            self.fit_frame(wage)
            self.claim_all_photos(wage)   # 사진 테두리에 걸칠 수 있는 의도 배치 — 신고
            self.act(d, FadeIn(wage, scale=1.3))

        def a2(d):
            # 문장 3(동료 대화 도입)에서 캠퍼스 → Altgeld Hall 전환.
            # EP04-IMG-19 (PD, Daderot — 1897 준공 = 시대 중립, 표기 불요)
            lab, _ = self.ep_photo("uiuc_altgeld_hall", height=4.4, pos=DOWN * 0.1)
            t1 = max(0.3, min(0.8, d * 0.4))
            self.play(FadeOut(self.st.pop("campus")), run_time=0.25)
            self.show_photo(lab, t1)
            self.st["lab"] = lab
            self.ken_burns(lab, d - t1 - 0.25, zoom=1.05)

        def a3(d):
            b1 = self.speech_bubble(["연구 문서인데,", "글자면 충분하잖아"],
                                    LEFT * 3.6 + UP * 2.5)
            self.claim_all_photos(b1)     # 사진 상단에 얹는 화면 문법 — 신고 후 사용
            self.st["b1"] = b1
            self.act(d, FadeIn(b1, scale=1.1))

        def a4(d):
            b2 = self.speech_bubble(["사람들은 그림 없으면", "안 봐요"],
                                    RIGHT * 3.4 + UP * 2.5, color=BLUE)
            self.claim_all_photos(b2)
            self.act(d, FadeIn(b2, scale=1.1),
                     self.st["b1"][0].animate.set_stroke(opacity=0.4))

        def a5(d):
            # 좌하단 — Altgeld 사진(x ±1.65, 켄 번즈 확대 포함)의 하단 테두리를 피한다
            # (r3 감사 실측 3.57×0.27 침범의 수리. 자막 대역 −3.10 위는 유지).
            note = chip("대화는 각색 — 시급은 실제", GRAY, 22)
            note.move_to(LEFT * 4.2 + DOWN * 2.55)
            self.act(d, FadeIn(note, shift=UP * 0.15))

        self.run_beats(S, [a0, a1, a2, a3, a4, a5])

    # --- 4: 1993-02-25 IMG 태그 제안 메일 (재현) ---
    def seg04(self, S):
        def a0(d):
            name = chip("마크 앤드리슨 — 그 알바생", INK, 26).to_corner(UL, buff=0.5)
            self.act(d, FadeIn(name, shift=DOWN * 0.2))

        def a1(d):
            date = chip("1993. 2. 25", RED, 26).to_corner(UR, buff=0.5)
            mail = RoundedRectangle(corner_radius=0.2, width=8.8, height=3.9)
            mail.set_stroke(INK, 4).set_fill(PAPER, 1).move_to(UP * 0.15)
            head = Line(mail.get_left() + RIGHT * 0.4, mail.get_right() + LEFT * 0.4)
            head.set_stroke(LGRAY, 3).move_to(mail.get_top() + DOWN * 1.0)
            subject = mtext("proposed new tag: IMG", fs=34, color=INK)
            subject.move_to(mail.get_top() + DOWN * 0.55)
            body = mtext('<IMG SRC="...">', fs=40, color=AMBER)
            body.move_to(mail.get_center() + DOWN * 0.5)
            cap = legal_chip("제안 메일 (재현 화면)", GRAY, 20)
            cap.next_to(mail, DOWN, buff=0.24)
            src = chip("1993-02-25 www-talk", GRAY, 18).next_to(cap, RIGHT, buff=0.3)
            self.st["mail"], self.st["body"] = mail, body
            t1 = max(0.3, min(0.9, d * 0.4))
            self.play(FadeIn(date, shift=DOWN * 0.2), FadeIn(mail), Create(head),
                      FadeIn(subject), FadeIn(cap), FadeIn(src), run_time=t1)
            t2 = max(0.3, min(0.7, d * 0.3))
            self.play(FadeIn(body, scale=1.25), run_time=t2)
            self.hold(d - t1 - t2)

        def a2(d):
            hl = SurroundingRectangle(self.st["body"], color=AMBER, buff=0.18)
            hl.set_stroke(AMBER, 4)
            what = chip("그림을 문서 안에 박는 명령", BLUE, 24)
            what.move_to(UP * 3.05)   # 하단은 캡션·출처 칩 자리 — 위로
            t1 = max(0.3, min(0.6, d * 0.3))
            self.play(Create(hl), run_time=t1)
            t2 = max(0.3, min(0.6, d * 0.3))
            self.play(FadeIn(what, shift=UP * 0.15), run_time=t2)
            self.hold(d - t1 - t2)

        self.run_beats(S, [a0, a1, a2])

    # --- 5: 1993-04-22 모자이크 공개 (재현 브라우저 — 실캡처 금지 §3-1) ---
    def seg05(self, S):
        def a0(d):
            date = chip("1993. 4. 22", RED, 26).to_corner(UL, buff=0.5)
            win = RoundedRectangle(corner_radius=0.2, width=7.8, height=5.0)
            win.set_stroke(INK, 4).set_fill("#EDEDED", 1).move_to(UP * 0.25 + LEFT * 1.4)
            bar = Rectangle(width=7.8, height=0.55).set_stroke(width=0)
            bar.set_fill("#D1D5DB", 1).move_to(win.get_top() + DOWN * 0.275)
            title = ktext("문서 보기", 20, GRAY).move_to(bar)
            lines = VGroup()
            for i, wfrac in enumerate((0.85, 0.7, 0.8, 0.55)):
                ln = Line(ORIGIN, RIGHT * 5.6 * wfrac).set_stroke(LGRAY, 5)
                ln.move_to(win.get_corner(UL) + RIGHT * (1.0 + 5.6 * wfrac / 2)
                           + DOWN * (1.1 + i * 0.5))
                lines.add(ln)
            cap = legal_chip("모자이크 (재현 화면)", GRAY, 20)
            self.cap_ur(cap, win)   # 창 아래는 자막 대역과 가까움 — 우상단 기본(§7-2)
            names = chip("앤드리슨 & 에릭 비나", INK, 24)
            names.move_to(RIGHT * 4.7 + UP * 2.6)
            self.st["win"], self.st["lines"] = win, lines
            t1 = max(0.3, min(0.9, d * 0.4))
            self.play(FadeIn(date, shift=DOWN * 0.2), FadeIn(win), FadeIn(bar),
                      FadeIn(title), FadeIn(cap), FadeIn(names), run_time=t1)
            t2 = max(0.3, min(0.8, d * 0.3))
            self.play(LaggedStart(*[Create(l) for l in lines], lag_ratio=0.2), run_time=t2)
            self.hold(d - t1 - t2)

        def a1(d):
            # 결정적 순간: 글 사이에 그림이 '바로' 뜬다
            img = RoundedRectangle(corner_radius=0.1, width=2.6, height=1.8)
            img.set_stroke(BLUE, 3).set_fill("#DBEAFE", 1)
            img.move_to(self.st["win"].get_center() + DOWN * 0.85)
            mount = Triangle().scale(0.35).set_stroke(BLUE, 3).set_fill(BLUE, 0.5)
            mount.move_to(img.get_center() + DOWN * 0.15)
            tag = chip("글과 그림, 한 화면", BLUE, 26).move_to(RIGHT * 4.7 + UP * 1.4)
            t1 = max(0.3, min(0.8, d * 0.4))
            self.play(FadeIn(VGroup(img, mount), scale=1.3), FadeIn(tag), run_time=t1)
            t2 = min(0.5, max(0.3, d * 0.2))
            self.play(Flash(img.get_center(), color=BLUE, flash_radius=1.6), run_time=t2)
            self.hold(d - t1 - t2)

        def a2(d):
            ez = chip("설치 — 몇 번 클릭이면 끝", EP04_GREEN, 22)
            ez.move_to(RIGHT * 4.5 + UP * 0.3)
            self.act(d, FadeIn(ez, shift=UP * 0.15))

        self.run_beats(S, [a0, a1, a2])

    # --- 6: 폭발 — 놀이터가 된 웹, 그러나 권리는 대학에 (도형·수치 미조달로 정성 연출) ---
    def seg06(self, S):
        def a0(d):
            base = [P3((x * 0.8, y * 0.55 + 0.6)) for x, y in MESH_P]
            more = [P3((x * 0.8 + 0.45, y * 0.55 + 0.15)) for x, y in MESH_P]
            dots1 = VGroup(*[Dot(p, radius=0.09, color=BLUE) for p in base])
            dots2 = VGroup(*[Dot(p, radius=0.07, color=LGRAY) for p in more])
            tag = chip("반응 — 폭발적", RED, 26).to_corner(UL, buff=0.5)
            self.st["dots"] = VGroup(dots1, dots2)
            t1 = max(0.3, min(0.6, d * 0.25))
            self.play(FadeIn(tag, shift=DOWN * 0.2),
                      LaggedStart(*[GrowFromCenter(dt) for dt in dots1], lag_ratio=0.06),
                      run_time=t1)
            t2 = max(0.3, min(1.0, d * 0.35))
            self.play(LaggedStart(*[GrowFromCenter(dt) for dt in dots2], lag_ratio=0.04),
                      run_time=t2)
            self.hold(d - t1 - t2)

        def a1(d):
            was = chip("연구자의 도구", GRAY, 24).move_to(DOWN * 2.3 + LEFT * 3.2)
            arrow = Arrow(was.get_right(), was.get_right() + RIGHT * 1.5, buff=0.15,
                          color=INK)
            now = chip("누구나 구경하는 놀이터", BLUE, 24)
            now.next_to(arrow, RIGHT, buff=0.15)
            self.act(d, FadeIn(was), GrowFromCenter(arrow), FadeIn(now, scale=1.15))

        def a2(d):
            owns = chip("권리는 대학(NCSA)에", RED, 26).move_to(UP * 3.05)
            self.act(d, FadeIn(owns, shift=DOWN * 0.2),
                     self.st["dots"].animate.set_opacity(0.35))

        def a3(d):
            cant = chip("연구소 — 감당 불가", RED, 24).move_to(UP * 2.2)
            self.act(d, FadeIn(cant, scale=1.2))

        self.run_beats(S, [a0, a1, a2, a3])

    # --- 7: 1994-02 짐 클라크의 편지 (실사 + 인용 1문장) ---
    # 소재 선정 기록(§16 편입): 주 비주얼 = SGI 워크스테이션(IMG-13, CC0·안전 —
    # 클라크의 회사를 하드웨어로 말한다, 로고 클로즈업 없음). 클라크 본인 사진(IMG-09)은
    # 500×465 저해상이라 대장 조건 "인서트/폴라로이드용 한정" → 작은 인셋으로만 얹고,
    # §16 확정 캡션 2종(TASL 18자 + 연대 미상 11자)을 동시 노출한다.
    def seg07(self, S):
        def a0(d):
            date = chip("1994. 2", RED, 26).to_corner(UL, buff=0.5)
            env = self.envelope_icon(2.0, 1.3).move_to(LEFT * 4.6 + UP * 2.3)
            ph, _ = self.ep_photo("sgi_indigo_crt_irix", height=3.6,
                                  pos=RIGHT * 3.4 + UP * 1.3)
            self.st["sgi"] = ph
            self.play(FadeIn(date, shift=DOWN * 0.2), run_time=0.3)
            t1 = max(0.3, min(0.7, d * 0.3))
            self.play(FadeIn(env, scale=1.2), run_time=0.35)
            self.show_photo(ph, t1)
            self.ken_burns(ph, d - t1 - 0.65, zoom=1.04)

        def a1(d):
            # 첫 문장 인용 — counsel §4 seg7 "가"(짧은 사실 문구, 대본이 출처 명시)
            quote = self.speech_bubble(["저를 모르시겠지만, 저는", "실리콘 그래픽스의",
                                        "창업자이자 전 회장입니다."],
                                       LEFT * 3.3 + DOWN * 0.6, fs=26, min_w=5.6)
            note = chip("기록에 남은 실제 문장", GRAY, 20)
            note.next_to(quote, DOWN, buff=0.24)
            self.st["quote"] = quote
            t1 = max(0.3, min(0.9, d * 0.4))
            self.play(FadeIn(quote, scale=1.06), run_time=t1)
            t2 = max(0.3, min(0.6, d * 0.25))
            self.play(FadeIn(note, shift=UP * 0.12), run_time=t2)
            self.hold(d - t1 - t2)

        def a2(d):
            # 클라크 인셋(EP04-IMG-09) — §16 확정 캡션 그대로. SGI 사진 테두리에 걸치는
            # 폴라로이드 문법이므로 claim_all_photos 로 신고한다(4편 차단 모드).
            ph, is_ph = self.ep_photo("jim_clark_2013", height=2.0,
                                      pos=RIGHT * 4.7 + DOWN * 1.35)
            shot = ph
            if not is_ph:   # 실물일 때만 §16 확정 캡션 2종(위 seg03 주석의 사고 수리)
                era = legal_chip("클라크 (연대 미상)", GRAY, 16)
                era.next_to(ph, UP, buff=0.16)
                # TASL 은 사진 왼쪽 — 아래 배치는 자막 대역을 0.10 물었다(r5 실측)
                tasl = legal_chip("Knnkanda, CC BY-SA", GRAY, 16)
                tasl.next_to(ph, LEFT, buff=0.2)
                shot = Group(ph, era, tasl)
            self.claim_all_photos(shot)
            # SGI 사진도 신고 — 인셋과 상호 걸침(폴라로이드 문법)이라 양방향 다 의도다
            # (r3 감사 실측: SGI 켄 번즈 확대분이 인셋 구역을 1.79×0.32 물었다).
            self.claim_all_photos(self.st["sgi"])
            # 이름 칩은 사진(x≥1.57)을 피해서 — r3 실측 0.69×0.54 침범의 수리
            name = chip("짐 클라크 — SGI 창업자", INK, 24).move_to(LEFT * 1.0 + UP * 3.05)
            t1 = max(0.3, min(0.7, d * 0.35))
            self.show_photo(shot, t1)
            t2 = max(0.3, min(0.5, d * 0.2))
            self.play(FadeIn(name, shift=DOWN * 0.15), run_time=t2)
            self.hold(d - t1 - t2)

        def a3(d):
            self.act(d, Indicate(self.st["quote"], color=BLUE, scale_factor=1.03))

        self.run_beats(S, [a0, a1, a2, a3])

    # --- 8: 백지 재작성 — 코드명 모질라 (재현 편집기 · 공룡 마스코트 금지 §3-4) ---
    def seg08(self, S):
        def a0(d):
            date = chip("1994. 4 — 회사 설립", INK, 26).to_corner(UL, buff=0.5)
            ed = RoundedRectangle(corner_radius=0.2, width=9.4, height=4.6)
            ed.set_stroke(CRT_DIM, 3).set_fill(CRT_BG, 1).move_to(UP * 0.3)
            lines = VGroup()
            for i, wfrac in enumerate((0.7, 0.55, 0.75, 0.45, 0.6)):
                ln = Line(ORIGIN, RIGHT * (ed.width - 1.8) * wfrac)
                ln.set_stroke(CRT_DIM, 6)
                ln.move_to(ed.get_corner(UL) + RIGHT * (0.9 + ln.get_length() / 2)
                           + DOWN * (0.8 + i * 0.6))
                lines.add(ln)
            self.st["ed"], self.st["code"] = ed, lines
            t1 = max(0.3, min(0.8, d * 0.35))
            self.play(FadeIn(date, shift=DOWN * 0.2), FadeIn(ed), run_time=t1)
            t2 = max(0.3, min(0.8, d * 0.3))
            self.play(LaggedStart(*[Create(l) for l in lines], lag_ratio=0.15), run_time=t2)
            self.hold(d - t1 - t2)

        def a1(d):
            ban = chip("모자이크 코드 — 한 줄도 금지", RED, 24)
            ban.move_to(self.st["ed"].get_center() + UP * 0.1)
            cross = VGroup(*[Line(l.get_start(), l.get_end()).set_stroke(RED, 4)
                             for l in self.st["code"]])
            self.act(d, FadeIn(ban, scale=1.2), Create(cross), rt=min(1.2, d * 0.5))
            self.st["cross"] = cross
            self.st["ban"] = ban

        def a2(d):
            cursor = Rectangle(width=0.16, height=0.42).set_stroke(width=0)
            cursor.set_fill(AMBER, 1)
            cursor.move_to(self.st["ed"].get_corner(UL) + RIGHT * 1.0 + DOWN * 0.85)
            fresh = chip("처음부터, 새로", BLUE, 26).move_to(DOWN * 2.5 + LEFT * 3.0)
            t1 = max(0.3, min(0.9, d * 0.4))
            self.play(FadeOut(self.st.pop("code")), FadeOut(self.st.pop("cross")),
                      FadeOut(self.st.pop("ban")), FadeIn(cursor), run_time=t1)
            t2 = max(0.3, min(0.6, d * 0.25))
            self.play(FadeIn(fresh, scale=1.2), run_time=t2)
            self.hold(d - t1 - t2)

        def a3(d):
            code_name = chip("코드명: 모질라", AMBER, 28)
            code_name.move_to(self.st["ed"].get_center() + UP * 0.2)
            mean = ktext("= 모자이크를 잡아먹는다", 24, LGRAY)   # 검은 편집기 위 — 밝은 회색
            mean.next_to(code_name, DOWN, buff=0.25)
            self.act(d, FadeIn(code_name, scale=1.3), FadeIn(mean, shift=UP * 0.1))

        self.run_beats(S, [a0, a1, a2, a3])

    # --- 9: 점유율 80% 안팎 (재현 데이터 차트 — "조사기관별 상이" 필수 캡션) ---
    def seg09(self, S):
        def a0(d):
            card = RoundedRectangle(corner_radius=0.2, width=9.4, height=4.9)
            card.set_stroke(INK, 4).set_fill(EP04_PAPER, 1).move_to(UP * 0.25)
            base_y = card.get_bottom()[1] + 0.75
            axis = Line([card.get_left()[0] + 0.8, base_y, 0],
                        [card.get_right()[0] - 0.8, base_y, 0]).set_stroke(INK, 3)
            ns_bar = Rectangle(width=2.4, height=3.0).set_stroke(width=0)
            ns_bar.set_fill(EP04_GREEN, 1)
            ns_bar.move_to([card.get_center()[0] - 1.9, base_y + 1.5, 0])
            ot_bar = Rectangle(width=2.4, height=0.75).set_stroke(width=0)
            ot_bar.set_fill(LGRAY, 1)
            ot_bar.move_to([card.get_center()[0] + 1.9, base_y + 0.375, 0])
            ns_lb = ktext("넷스케이프", 24, INK).next_to(ns_bar, DOWN, buff=0.18)
            ot_lb = ktext("그 외", 24, GRAY).next_to(ot_bar, DOWN, buff=0.18)
            pct = mtext("~80%", fs=44, color=EP04_GREEN).next_to(ns_bar, UP, buff=0.2)
            cap = legal_chip("점유율 (조사기관별 상이)", GRAY, 20)
            self.cap_ur(cap, card)
            yr = chip("1995", RED, 26).to_corner(UL, buff=0.5)
            self.st["ns_bar"] = ns_bar
            t1 = max(0.3, min(0.8, d * 0.35))
            self.play(FadeIn(yr, shift=DOWN * 0.2), FadeIn(card), Create(axis),
                      FadeIn(cap), run_time=t1)
            t2 = max(0.3, min(1.0, d * 0.35))
            self.play(FadeIn(ns_bar, shift=UP * 0.4), FadeIn(ot_bar, shift=UP * 0.15),
                      FadeIn(ns_lb), FadeIn(ot_lb), FadeIn(pct, scale=1.2), run_time=t2)
            self.hold(d - t1 - t2)

        def a1(d):
            window = chip("세상이 웹을 보는 창문", BLUE, 24).move_to(DOWN * 2.55)
            self.act(d, FadeIn(window, shift=UP * 0.15))

        def a2(d):
            one = chip("사실상 하나", RED, 28).move_to(UP * 3.05)
            t1 = max(0.3, min(0.7, d * 0.35))
            self.play(FadeIn(one, scale=1.3), run_time=t1)
            t2 = min(0.5, max(0.3, d * 0.2))
            self.play(Flash(self.st["ns_bar"].get_center(), color=EP04_GREEN,
                            flash_radius=1.8), run_time=t2)
            self.hold(d - t1 - t2)

        self.run_beats(S, [a0, a1, a2])

    # --- 10: 상장일 — 공모가 28, 주문 폭주 (재현) ---
    def seg10(self, S):
        def a0(d):
            date = chip("1995. 8. 9 — 상장", RED, 26).to_corner(UL, buff=0.5)
            ipo = VGroup(ktext("공모가", 26, GRAY), mtext("$28.00", fs=58, color=INK))
            ipo.arrange(DOWN, buff=0.2).move_to(UP * 1.9)
            self.st["ipo"] = ipo
            self.act(d, FadeIn(date, shift=DOWN * 0.2), FadeIn(ipo, scale=1.15))

        def a1(d):
            # 주문 폭주 — 매수 쪽만 쌓이는 막대 (요구서 seg10 대체안 그대로)
            buys = VGroup()
            for i in range(7):
                b = Rectangle(width=2.6, height=0.34).set_stroke(width=0)
                b.set_fill(AMBER, 0.9)
                b.move_to(LEFT * 3.3 + DOWN * (2.2 - i * 0.42))
                buys.add(b)
            sell = Rectangle(width=2.6, height=0.34).set_stroke(width=0)
            sell.set_fill(LGRAY, 0.9).move_to(RIGHT * 3.3 + DOWN * 2.2)
            b_lb = chip("사자 — 폭주", AMBER, 22).move_to(LEFT * 3.3 + UP * 0.65)
            s_lb = chip("팔자", GRAY, 22).move_to(RIGHT * 3.3 + UP * 0.65)
            self.act(d, FadeIn(b_lb), FadeIn(s_lb),
                     LaggedStart(*[FadeIn(b, shift=UP * 0.2) for b in buys],
                                 lag_ratio=0.12),
                     FadeIn(sell), rt=min(1.6, d * 0.6))

        def a2(d):
            # counsel §6-2 의무 대상 "seg0/10 시세판" — 미니 NSCP 행 재현 + 표기.
            band = RoundedRectangle(corner_radius=0.12, width=4.6, height=0.9)
            band.set_stroke(CRT_DIM, 3).set_fill(CRT_BG, 1)
            band.move_to(RIGHT * 3.9 + UP * 1.9)
            nscp = mtext("NSCP  --.--", fs=30, color=AMBER).move_to(band)
            cap = legal_chip("시세판 (재현 화면)", GRAY, 18)
            cap.next_to(band, DOWN, buff=0.2)
            delay = chip("첫 거래 — 약 2시간 지연", RED, 26).move_to(UP * 3.05 + LEFT * 1.6)
            t1 = max(0.3, min(0.7, d * 0.35))
            self.play(FadeIn(band), FadeIn(nscp), FadeIn(cap), run_time=t1)
            t2 = max(0.3, min(0.6, d * 0.25))
            self.play(FadeIn(delay, scale=1.2),
                      Wiggle(self.st["ipo"], scale_value=1.04), run_time=t2)
            self.hold(d - t1 - t2)

        def a3(d):
            self.hold(d)

        self.run_beats(S, [a0, a1, a2, a3])

    # --- 11: 클라이맥스 — 주가 재현 차트 28→71→74.75→58.25 (저작권 0) ---
    def seg11(self, S):
        # 좌표계: 카드 안에서 가격 p → y = base + (p - 20) * scale
        def a0(d):
            card = RoundedRectangle(corner_radius=0.2, width=9.8, height=5.2)
            card.set_stroke(INK, 4).set_fill(EP04_PAPER, 1).move_to(UP * 0.25)
            base_y, scale = card.get_bottom()[1] + 0.55, 0.058
            py = lambda p: base_y + (p - 20) * scale  # noqa: E731

            xs = {"open": -3.7, "first": -1.3, "peak": 1.1, "close": 3.7}
            ip_line = DashedLine([xs["open"], py(28), 0], [xs["close"] + 0.3, py(28), 0])
            ip_line.set_stroke(GRAY, 3)
            ip_lb = mtext("$28", fs=28, color=GRAY)
            ip_lb.next_to(ip_line.get_start(), UP, buff=0.15).shift(RIGHT * 0.3)
            cap = legal_chip("주가 (데이터 재구성)", GRAY, 20)
            self.cap_ur(cap, card)
            self.st.update(card=card, py=py, xs=xs)
            t1 = max(0.3, min(0.8, d * 0.35))
            self.play(FadeIn(card), FadeIn(cap), run_time=t1)
            t2 = max(0.3, min(0.7, d * 0.3))
            self.play(Create(ip_line), FadeIn(ip_lb), run_time=t2)
            # 첫 체결 — 28 에서 71 로 수직 점프
            jump = Line([xs["first"], py(28), 0], [xs["first"], py(71), 0])
            jump.set_stroke(EP04_GREEN, 6)
            dot71 = Dot([xs["first"], py(71), 0], radius=0.1, color=EP04_GREEN)
            lb71 = mtext("$71", fs=34, color=EP04_GREEN)
            lb71.next_to(dot71, UL, buff=0.12)
            first = ktext("첫 체결", 22, GRAY).next_to(lb71, UP, buff=0.1)
            t3 = max(0.3, min(0.9, d * 0.25))
            self.play(Create(jump), FadeIn(dot71, scale=1.4), FadeIn(lb71),
                      FadeIn(first), run_time=t3)
            self.st["p71"] = [xs["first"], py(71), 0]
            self.hold(d - t1 - t2 - t3)

        def a1(d):
            py, xs = self.st["py"], self.st["xs"]
            rise = Line(self.st["p71"], [xs["peak"], py(74.75), 0])
            rise.set_stroke(EP04_GREEN, 6)
            dot_pk = Dot([xs["peak"], py(74.75), 0], radius=0.11, color=EP04_RED)
            lb_pk = mtext("$74.75", fs=34, color=EP04_RED)
            lb_pk.next_to(dot_pk, UP, buff=0.15)
            fall = Line([xs["peak"], py(74.75), 0], [xs["close"], py(58.25), 0])
            fall.set_stroke(GRAY, 6)
            dot_cl = Dot([xs["close"], py(58.25), 0], radius=0.1, color=INK)
            lb_cl = mtext("$58.25", fs=32, color=INK)
            lb_cl.next_to(dot_cl, UR, buff=0.12)
            cl = ktext("마감", 22, GRAY).next_to(lb_cl, DOWN, buff=0.08)
            t1 = max(0.3, min(0.9, d * 0.35))
            self.play(Create(rise), FadeIn(dot_pk, scale=1.4), FadeIn(lb_pk), run_time=t1)
            t2 = min(0.5, max(0.3, d * 0.15))
            self.play(Flash(dot_pk.get_center(), color=EP04_RED, flash_radius=1.4),
                      run_time=t2)
            t3 = max(0.3, min(0.9, d * 0.3))
            self.play(Create(fall), FadeIn(dot_cl), FadeIn(lb_cl), FadeIn(cl), run_time=t3)
            self.hold(d - t1 - t2 - t3)

        def a2(d):
            worth = chip("몸값 — 하루 만에 약 $30억", AMBER, 26).move_to(DOWN * 2.62)
            self.act(d, FadeIn(worth, scale=1.25))

        self.run_beats(S, [a0, a1, a2])

    # --- 12: 닷컴 열풍의 방아쇠 — 오늘과의 겹침은 '작성자 관찰' (정성 연출) ---
    def seg12(self, S):
        def a0(d):
            trig = chip("닷컴 열풍의 방아쇠", RED, 28).to_corner(UL, buff=0.5)
            c1 = ArcBetweenPoints([-5.4, -1.8, 0], [0.6, 1.9, 0], angle=-0.6)
            c1.set_stroke(EP04_GREEN, 6)
            lb1 = chip("1995 — 인터넷이면 오른다", EP04_GREEN, 22)
            lb1.move_to(LEFT * 2.9 + UP * 2.3)   # UL 코너 칩과 세로 간격 확보
            self.st["c1"] = c1
            self.act(d, FadeIn(trig, shift=DOWN * 0.2), Create(c1), FadeIn(lb1),
                     rt=min(1.6, d * 0.6))

        def a1(d):
            how = chip("실적이 아니라 '인터넷'이라는 단어로", INK, 24).move_to(DOWN * 2.5)
            self.act(d, FadeIn(how, shift=UP * 0.15))

        def a2(d):
            c2 = ArcBetweenPoints([-0.6, -1.8, 0], [5.4, 1.9, 0], angle=-0.6)
            c2.set_stroke(AMBER, 6)
            lb2 = chip("오늘 — AI 투자 열기", AMBER, 22).move_to(RIGHT * 3.4 + UP * 2.5)
            # counsel §4 seg12: 사실과 의견의 분리 표기(권장 → 기계 강제로 채택)
            view = legal_chip("작성자 관찰", GRAY, 20)
            view.move_to(RIGHT * 4.9 + DOWN * 1.3)
            self.act(d, Create(c2), FadeIn(lb2), FadeIn(view, shift=UP * 0.12),
                     self.st["c1"].animate.set_stroke(opacity=0.45),
                     rt=min(1.4, d * 0.5))

        self.run_beats(S, [a0, a1, a2])

    # --- 13: 시리즈의 법칙 — 거인이 깨어난다 (실루엣 연출 · IE/MS 로고 금지 §3-3) ---
    def seg13(self, S):
        def a0(d):
            law = chip("시리즈의 법칙", INK, 24).to_corner(UL, buff=0.5)
            rule = ktext("모든 해결은 새로운 문제를 낳는다", 40, INK, bold=True)
            rule.move_to(UP * 1.6)
            self.st["rule"] = rule
            self.act(d, FadeIn(law, shift=DOWN * 0.2), FadeIn(rule, scale=1.08))

        def a1(d):
            # 거대한 그림자 — 화면 오른쪽에서 일어선다(하단 접지는 설계 — claim_bottom 신고)
            real = find_asset("ep04_ms_campus")
            if real:
                ph = self.photo(os.path.basename(real), height=4.2,
                                pos=RIGHT * 3.9 + UP * 0.2)
                self.st["giant"] = ph
                self.show_photo(ph, max(0.3, min(0.8, d * 0.4)))
                self.ken_burns(ph, d - 0.8, zoom=1.05)
                return
            shadow = Rectangle(width=3.6, height=6.6).set_stroke(width=0)
            shadow.set_fill("#374151", 0.92)
            shadow.move_to(RIGHT * 4.9 + DOWN * 0.7)   # 바닥에 접지한 실루엣
            self.claim_bottom(shadow)                   # 하단 진입은 설계 — 신고
            small = RoundedRectangle(corner_radius=0.12, width=1.7, height=1.2)
            small.set_stroke(BLUE, 4).set_fill(WHITE, 1)
            small.move_to(LEFT * 3.4 + DOWN * 1.4)
            s_lb = ktext("넷스케이프", 20, BLUE).next_to(small, DOWN, buff=0.15)
            self.st["giant"] = shadow
            t1 = max(0.4, min(1.2, d * 0.5))
            self.play(FadeIn(shadow, shift=UP * 0.8), FadeIn(small), FadeIn(s_lb),
                      self.st["rule"].animate.set_opacity(0.4), run_time=t1)
            self.hold(d - t1)

        def a2(d):
            who = chip("같은 달 — 인터넷 익스플로러", INK, 24)   # 잉크 상자·흰 글씨(그림자 위 가독)
            who.set_z_index(2)
            who.move_to(RIGHT * 3.6 + UP * 2.4)
            date = chip("1995. 8", RED, 24).next_to(who, DOWN, buff=0.25)
            self.act(d, FadeIn(who, scale=1.15), FadeIn(date))

        def a3(d):
            more = chip("그리고 — 숙제가 하나 더", AMBER, 26).move_to(DOWN * 2.5 + LEFT * 2.6)
            self.act(d, FadeIn(more, shift=UP * 0.15))

        self.run_beats(S, [a0, a1, a2, a3])

    # --- 14: 아웃트로 — 눌러도 안 움직이는 웹, 다음 편 자바스크립트 ---
    def seg14(self, S):
        def a0(d):
            page = self.doc_card(LEFT * 3.6 + UP * 1.4, w=3.8, h=3.4, nlines=5)
            cursor = Triangle().scale(0.18).rotate(-PI / 5)
            cursor.set_fill(INK, 1).set_stroke(WHITE, 2)
            cursor.move_to(page.get_center() + RIGHT * 0.8 + DOWN * 0.4)
            dead = chip("눌러도 — 무반응", RED, 24).next_to(page, RIGHT, buff=0.5)
            # 전단지 연출 일습을 한 묶음으로 — a1 에서 통째로 내려야 커서가 잔류하지 않는다
            # (첫 --layout-audit 실측: 잔류 커서가 예고 카드 구역을 0.28×0.27 침범 적발).
            self.st["page"] = Group(page, cursor, dead)
            t1 = max(0.3, min(0.8, d * 0.35))
            self.play(FadeIn(page), FadeIn(cursor), run_time=t1)
            t2 = max(0.3, min(0.6, d * 0.25))
            self.play(FadeIn(dead, scale=1.2),
                      Wiggle(cursor, scale_value=1.3), run_time=t2)
            self.hold(d - t1 - t2)

        def a1(d):
            t = ktext("여러분이라면, 며칠 만에 풀 수 있을까요?", 30, INK, bold=True)
            box = RoundedRectangle(corner_radius=0.25, width=t.width + 0.8,
                                   height=t.height + 0.7)
            box.set_stroke(INK, 4).set_fill(PAPER, 1)
            bubble = VGroup(box, t.move_to(box)).move_to(UP * 2.9)
            self.st["bubble"] = bubble
            self.act(d, FadeIn(bubble, scale=1.1),
                     FadeOut(self.st.pop("page")))

        def a2(d):
            cmt = chip("댓글로", BLUE, 28).next_to(self.st["bubble"], DOWN, buff=0.35)
            self.act(d, FadeIn(cmt, shift=UP * 0.2),
                     Indicate(self.st["bubble"], color=BLUE, scale_factor=1.03))

        def a3(d):
            # 3편 아웃트로 문법 승계: CTA 자리 예약 → 예고 카드 → 남는 칸 실측 배치
            self.reserve_cta()
            cal = RoundedRectangle(corner_radius=0.2, width=4.2, height=2.4)
            cal.set_stroke(INK, 4).set_fill(PAPER, 1)
            cal.move_to(LEFT * 3.9 + DOWN * 1.0)
            days = VGroup()
            for i in range(10):
                cell = RoundedRectangle(corner_radius=0.06, width=0.62, height=0.62)
                cell.set_stroke(LGRAY, 2).set_fill(WHITE, 1)
                cell.move_to(cal.get_corner(UL)
                             + RIGHT * (0.65 + (i % 5) * 0.74)
                             + DOWN * (0.7 + (i // 5) * 0.78))
                num = mtext(str(i + 1), fs=20, color=GRAY, bold=False).move_to(cell)
                days.add(VGroup(cell, num))
            ten = chip("열흘", AMBER, 22).next_to(cal, UP, buff=0.2)
            teaser_card = Group(cal, days, ten)
            self.reserve_zone("예고 카드(달력)", teaser_card,
                              owners=[teaser_card, cal, days, ten])
            tag = chip("#05 — 자바스크립트", INK, 28)
            tag.move_to(RIGHT * 1.6 + DOWN * 1.1)
            self.avoid_zones(tag)
            band_l, band_r, band_w = self.free_x_band(-2.75, -1.6, anchor=1.6)
            teaser = ktext_block("넷스케이프 개발자 한 명이 열흘 만에 만든 언어", 24, GRAY,
                                 max_width=band_w, aligned_edge=LEFT)
            teaser.next_to(tag, DOWN, buff=0.26, aligned_edge=LEFT)
            if teaser.get_right()[0] > band_r:
                teaser.shift(RIGHT * (band_r - teaser.get_right()[0]))
            if teaser.get_left()[0] < band_l:
                teaser.shift(RIGHT * (band_l - teaser.get_left()[0]))
            t1 = max(0.3, min(0.8, d * 0.35))
            self.play(FadeIn(cal), FadeIn(ten),
                      LaggedStart(*[FadeIn(dv, scale=1.2) for dv in days],
                                  lag_ratio=0.05), run_time=t1)
            t2 = max(0.3, min(0.8, d * 0.3))
            self.play(FadeIn(tag, scale=1.15), FadeIn(teaser, shift=UP * 0.15), run_time=t2)
            self.hold(d - t1 - t2)

        def a4(d):
            self.show_cta(d)

        self.run_beats(S, [a0, a1, a2, a3, a4])


# ---------- 조립(오디오·자막·먹싱) ----------

def build_srt():
    def fmt(t):
        h, rem = divmod(t, 3600)
        m, s = divmod(rem, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"

    lines, n, t = [], 1, INTRO_D
    for seg in TIMED:
        for txt, d in seg["sents"]:
            lines.append(f"{n}\n{fmt(t)} --> {fmt(t + d)}\n{txt}\n")
            n += 1
            t += d
        t += GAP
    path = os.path.join(OUT, f"{OUT_STEM}.srt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def build_audio():
    from pydub import AudioSegment
    track = AudioSegment.silent(duration=int(INTRO_D * 1000))
    for seg in TIMED:
        track += AudioSegment.from_wav(seg["wav"])
        track += AudioSegment.silent(duration=int(GAP * 1000))
    path = os.path.join(OUT, f"{OUT_STEM}_track.wav")
    track.export(path, format="wav")
    return path


def mix_bgm(track_path):
    """내레이션 트랙 아래에 BGM 을 깔고, 먹싱에 쓸 오디오 경로를 돌려준다.

    실제 로직은 video/bgm.py 에 있다(오디오 관할 모듈 분리 — 이 파일은 여러
    담당이 동시에 고치므로 충돌 면적을 줄인다). BGM 이 없거나 레벨 검수를
    통과하지 못하면 내레이션 경로를 그대로 돌려준다 — 조용히 넘어가지 않고
    이유를 화면에 남기는 것이 계약이다(감사 결함 2: 침묵은 통과가 아니다).

    ※ episode_track.wav 는 절대 덮어쓰지 않는다. 무음 비율·길이 불변식을 재는
      기준이 '내레이션 단독' 이어야 하기 때문(verify_output_spec.verify_body).
    """
    try:
        import bgm as _bgm
    except ImportError as e:
        print(f"[v2] 경고: BGM 모듈을 못 불러왔다 — {e} (BGM 없이 진행, 4편부터는 규격 미달)")
        return track_path
    try:
        return _bgm.apply(EP, OUT, OUT_STEM, track_path)
    except Exception as e:  # noqa: BLE001
        print(f"[v2] 경고: BGM 믹싱 실패 — {e} (내레이션만으로 진행)")
        return track_path


def partial_dir():
    return os.path.join(OUT, "media", "videos", f"{VH}p{VFPS}",
                        "partial_movie_files", f"Episode{EP}")


def assemble_partials():
    """파셜(애니메이션 단위 조각 영상) 전량을 번호순으로 이어붙여 무음 영상을 만든다.

    쉬운 말: 필름 조각 153장을 번호대로 이어 붙여 한 롤로 만드는 일.
    구간만 다시 구운 뒤(--from-anim) 전체를 복원할 때 쓴다 — 전량 재렌더(70분)를
    피하는 정식 경로. 결번(빠진 번호)이나 0바이트 조각이 있으면 **조립을 거부**한다:
    조용히 이어붙이면 내용이 누락된 채 길이만 맞아 검사기도 속는다.
    (2026-07-30 임시 스크립트로 하던 복구를 정식 옵션으로 편입 — 재발 시 즉시 복구.)
    """
    part = partial_dir()
    files = sorted(glob.glob(os.path.join(part, "uncached_*.mp4")),
                   key=lambda p: int(re.search(r"uncached_(\d+)", p).group(1)))
    if not files:
        print(f"[v2] 오류: 파셜이 없다 — {part}")
        return None
    nums = [int(re.search(r"uncached_(\d+)", p).group(1)) for p in files]
    missing = [n for n in range(max(nums) + 1) if n not in set(nums)]
    zero = [os.path.basename(p) for p in files if os.path.getsize(p) == 0]
    print(f"[v2] 파셜 {len(files)}개 (0~{max(nums)}) | 결번 {len(missing)}개 | "
          f"0바이트 {len(zero)}개")
    if missing or zero:
        print(f"[v2] *** 조립 거부: 결번 {missing[:10]} / 0바이트 {zero[:5]} — "
              f"빠진 구간을 --from-anim 으로 다시 구운 뒤 재시도 ***")
        return None
    lst = os.path.join(OUT, "_concat_all.txt")
    with open(lst, "w", encoding="utf-8", newline="\n") as f:
        for p in files:
            f.write("file '" + p.replace("\\", "/") + "'\n")
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    silent = os.path.join(OUT, "_ep_full_silent.mp4")
    print("[v2] 이어붙이기 ...")
    r = subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
                        "-safe", "0", "-i", lst, "-c", "copy", silent],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print("[v2] 오류: concat 실패 —", (r.stderr or "")[-600:])
        return None
    return silent


def mux_only():
    """--mux-only: 렌더 없이 파셜 전량 조립 + 오디오 먹싱 → episode.mp4 갱신."""
    if not FULL:
        print("[v2] 오류: --mux-only 는 --full(완성 규격) 에서만 쓴다.")
        return 1
    silent = assemble_partials()
    if not silent:
        return 1
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    track = os.path.join(OUT, f"{OUT_STEM}_track.wav")
    if os.path.exists(track):
        # 확정된 오디오 트랙(라우드니스 정규화분)을 재생성으로 덮어쓰지 않는다.
        print(f"[v2] 기존 오디오 트랙 사용(재생성 안 함): {os.path.basename(track)} "
              f"{wav_seconds(track):.2f}s")
    else:
        print("[v2] 오디오 트랙이 없어 세그 wav 로 새로 만든다.")
        track = build_audio()
    srt = os.path.join(OUT, f"{OUT_STEM}.srt")
    if not os.path.exists(srt):
        srt = build_srt()
    vdur = probe_duration(ff, silent)
    adur = wav_seconds(track)
    print(f"[v2] 무음 영상 {vdur:.2f}s / 오디오 {adur:.2f}s (차 {vdur - adur:+.2f}s)")
    if vdur + 0.05 < adur:
        print("[v2] *** 조립 거부: 영상이 오디오보다 짧다 — 내레이션 끝이 잘린다 ***")
        return 1
    # BGM 은 길이 검사를 통과한 '확정 내레이션 트랙' 위에 깐다(믹스 길이 = 내레이션 길이,
    # bgm.apply 가 불변식으로 강제). 그래서 위의 영상↔오디오 길이 판정은 그대로 유효하다.
    mux_audio = mix_bgm(track)
    final = os.path.join(OUT, OUT_NAME)
    r = subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-i", silent,
                        "-i", mux_audio, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", final],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print("[v2] 오류: 먹싱 실패 —", (r.stderr or "")[-600:])
        return 1
    print(f"[v2] 완성({VW}x{VH} {VFPS}fps): {final} — "
          f"{probe_duration(ff, final):.2f}s / {os.path.getsize(final) / 1e6:.1f}MB")
    print(f"[v2] 자막: {srt}")
    return run_spec_check("--body")


def probe_duration(ff, path):
    out = subprocess.run([ff, "-hide_banner", "-i", path, "-f", "null", "-"],
                         capture_output=True, text=True, errors="replace").stderr or ""
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    return (int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))) if m else -1.0


def run_spec_check(scope):
    """[P1 연결] 완성 렌더 직후 산출물 스펙을 기계 판정한다.

    '렌더가 끝났다'와 '규격에 맞다'는 다른 말이다(rule4). 지금까지는 그 사이를
    사람의 육안이 메웠고, 결함 5건이 전부 사용자 눈에 먼저 닿았다. 여기서 닫는다.
    검사기가 없거나 터져도 렌더 산출물 자체는 이미 만들어졌으므로, 예외는 경고로
    낮추고 렌더 결과를 무효화하지 않는다(단, 통과 선언도 하지 않는다).
    """
    script = os.path.join(ROOT, "video", "verify_output_spec.py")
    if not os.path.exists(script):
        print("[v2] 경고: verify_output_spec.py 없음 — 스펙 검사 생략(미확인 상태)")
        return None
    print("\n[v2] 산출물 스펙 실측 검사 ...")
    try:
        rc = subprocess.run([sys.executable, script, EP, scope]).returncode
    except Exception as e:  # noqa: BLE001
        print(f"[v2] 경고: 스펙 검사 실행 실패 — {e} (미확인 상태)")
        return None
    if rc == 0:
        print("[v2] 스펙 검사 통과.")
    else:
        print(f"[v2] *** 스펙 검사 미달(종료코드 {rc}) — 위 [spec] 미달 항목을 "
              f"고치기 전에는 발행 금지 ***")
    return rc


def main():
    print(f"[v2] {EP}편 | 음성: {'있음 — 소리 합성' if HAVE_AUDIO else '없음 — 무음'} | "
          f"{'완성 렌더' if FULL else '시안 렌더(최종본 아님)'} {VW}x{VH} {VFPS}fps")
    if AUDIO_SUB != "audio":
        print(f"[v2] 주의: 음성 스냅샷 '{AUDIO_SUB}' 타이밍 기준 시안 — 최종본 아님"
              f" (최종은 audio/ 확정 후 재렌더)")
    total = INTRO_D + sum(s["total"] + GAP for s in TIMED) + 1.2
    print(f"[v2] 예상 길이: {total:.0f}초 ({total / 60:.1f}분)")

    episodes = {"01": Episode01, "02": Episode02, "03": Episode03, "04": Episode04}
    if EP not in episodes:
        print(f"[v2] 오류: {EP}편 장면 클래스가 없음 (지원: {', '.join(episodes)})")
        sys.exit(1)
    if MUX_ONLY:
        sys.exit(mux_only() or 0)
    scene = episodes[EP]()
    scene.render()
    if LAYOUT_AUDIT:
        # 값싼 사전 검사(몇 분)에서는 **종료 코드로** 결함을 알린다 — 조용히 0을 돌려주면
        # 자동화(훅·CI·총감독 루프)가 통과로 읽는다. 70분 렌더는 이 관문을 먼저 통과한 뒤에.
        bad = []
        if scene._overflow:
            bad.append(f"프레임 이탈 {len(scene._overflow)}건")
        if scene._intrusion:
            bad.append(f"보호영역 침범 {len(scene._intrusion)}건")
        short = scene.legal_shortfalls()
        if short:
            bad.append(f"법무 표기 지속 미달 {len(short)}건")
        cov, tot = scene.zone_coverage()
        if cov < tot:
            bad.append(f"보호영역 미등록 구간 {tot - cov}개")
        if scene._advice:
            print(f"[v2] 권고 위반 {len(scene._advice)}건 — 차단은 아니지만 "
                  f"{EpisodeBase.ZONE_STRICT_FROM_EP}편부터는 차단이다. 위 목록 확인.")
        print("[v2] 레이아웃 감사 종료 — 위 [audit] 줄이 판정 결과다(영상 미생성).")
        if bad:
            print("[v2] 감사 불합격: " + " · ".join(bad))
            sys.exit(2)
        print("[v2] 감사 합격 — 이탈·침범·표기 지속·구간 커버리지 전항 통과.")
        return

    if NO_MUX:
        print("[v2] --no-mux: 파셜 생산만 하고 조립을 생략한다(청크 이어붙이기는 호출 측이 수행).")
        return

    hits = glob.glob(os.path.join(OUT, "media", "**", "ep_silent.mp4"), recursive=True)
    if not hits:
        print("[v2] 오류: 렌더 결과 mp4를 찾지 못함")
        sys.exit(1)
    silent = max(hits, key=os.path.getmtime)
    srt = build_srt()

    if HAVE_AUDIO:
        import imageio_ffmpeg
        audio = mix_bgm(build_audio())
        final = os.path.join(OUT, OUT_NAME)
        cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", silent, "-i", audio,
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", final]
        subprocess.run(cmd, check=True, capture_output=True)
        # [P2] '완성'이라는 단어는 --full 렌더에서만 쓴다. 시안은 해상도를 문구에 박아
        # 로그만 보고 최종본으로 오인하는 경로를 없앤다.
        if FULL:
            print(f"[v2] 완성({VW}x{VH} {VFPS}fps): {final}")
        else:
            print(f"[v2] 시안({VW}x{VH} {VFPS}fps) — 최종본 아님: {final}")
    else:
        # --out-name 지정 시 그 이름을 존중(예: episode_480p_draft.mp4), 미지정이면 기존 관례 유지
        silent_name = OUT_NAME if OUT_NAME != "episode.mp4" else "episode_silent_preview.mp4"
        final = os.path.join(OUT, silent_name)
        if os.path.exists(final):
            os.remove(final)
        os.replace(silent, final)
        print(f"[v2] 무음 시안: {final} (음성 도착 후 다시 실행하면 완성본)")
    ep_cls = episodes[EP]
    used_ph = getattr(ep_cls, "PLACEHOLDERS_USED", None)
    if used_ph:
        print(f"[v2] 플레이스홀더 사용 장면: {', '.join(used_ph)}")
    print(f"[v2] 자막: {srt}")
    # 완성 렌더에서만 스펙 검사를 건다. 시안은 애초에 480p 라 미달이 당연하므로
    # 여기서 돌리면 '늘 빨간불'이 되어 경고가 무뎌진다(경보 피로).
    if FULL and HAVE_AUDIO:
        run_spec_check("--body")


if __name__ == "__main__":
    main()
