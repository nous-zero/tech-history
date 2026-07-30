# -*- coding: utf-8 -*-
"""tech-history 쇼츠 조립기 — 본편 음성·사료를 재사용해 세로형(1080x1920) 쇼츠 생산.

규칙(2026-07-27 SEO 분석 박제분):
  - 본편 1개당 쇼츠 2종: ①반전형("~의 진짜 이유") ②요약형("N초 요약")
  - 첫 1.5초 훅 카드가 전부. 자막은 굽는다(쇼츠는 CC 사용률 낮음). 다크 배경(피드 대비).
사용:
  python video/build_shorts.py <편번호>           # 시안(540x960, 15fps)
  python video/build_shorts.py <편번호> --full    # 완성(1080x1920, 30fps)
  python video/build_shorts.py <편번호> --audit   # 세이프 영역 감사(저비용, 오디오 생략)
출력: video/output/<편>_v2/shorts_A.mp4 (반전형), shorts_B.mp4 (요약형)
      시안은 shorts_A_540p_draft.mp4 — 완성본 이름을 덮어쓰지 않는다(감사 처방 P2).
지원 편: 01(아파넷 LO), 02(TCP/IP Flag Day), 03(WWW 탄생)

스펙 검사(자동): --full 렌더가 끝나면 video/verify_output_spec.py 가 자동 실행돼
해상도(1080x1920)·길이(≤60s)·라우드니스·BGM 존재·프레임 이탈 로그를 실측 판정한다.
수동 실행: python video/verify_output_spec.py <편번호> --shorts  (종료코드 2 = 미달)
"""
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
AUDIT = "--audit" in sys.argv  # 세이프 영역 감사 모드(저프레임 렌더 — 기하만 검사, 오디오 생략)
OUT = os.path.join(ROOT, "video", "output", f"{EP}_v2")
AUDIO_DIR = os.path.join(OUT, "audio")
ASSETS = os.path.join(ROOT, "video", "output", "assets")

GAP = 0.15
HOOK_D = 1.3   # 훅 카드
END_D = 1.6    # 엔딩 카드
SPEED = 1.35   # 나레이션 배속(음정 유지) — 쇼츠 문법
ZOOM_DRIFT = 0.985  # 문장마다 화면이 서서히 밀고 들어감(정지화면 제거)

# --- 세이프 영역(2026-07-29 실사고 대응) -------------------------------------
# 사고: 3편 쇼츠에서 상단 팝·하단 문구·좌측 화자 라벨이 좌우로 잘려 나감.
# 원인: 요소는 '줌 안 들어간 프레임(폭 9.0)' 기준으로 배치·축소되는데, 카메라 드리프트가
#       프레임을 폭 7.2까지 밀고 들어가 실제 보이는 폭이 7.2로 줄어듦 → 8.2폭 텍스트가 잘림.
# 조치: ①드리프트 하한을 8.3으로 올려 '9.0 기준 도형'이 최대 줌에서도 살아남게 하고
#       ②모든 글자 요소의 최대 폭·배치를 세이프 상자 안으로 강제(ktext/chip/keep_in).
ZOOM_FLOOR = 8.3          # 카메라가 밀고 들어갈 수 있는 최소 프레임 폭(= 최소 가시 폭)
SAFE_W = 7.6              # 글자 요소 최대 폭(최소 가시 폭의 92%)
SAFE_TOP = 6.9            # 글자 요소 상·하한 |y| (최소 가시 높이 14.76의 절반 × 0.94)
SUB_W = 8.2               # 자막 상자 폭(카메라 고정 — 프레임 폭의 91%)

DARK = "#0B1220"
DGRID = "#1B2A44"
INK = "#1F2937"
GRAY = "#9CA3AF"
BLUE = "#3B82F6"
BLUE_L = "#93C5FD"
RED = "#EF4444"
AMBER = "#F59E0B"
KFONT = "Malgun Gothic"
MONO = "Consolas"

from manim import (  # noqa: E402
    config, MovingCameraScene, VGroup, VMobject, Group, Text, Dot, Circle, Line,
    DashedLine, Rectangle, RoundedRectangle, Triangle, ImageMobject,
    Create, FadeIn, FadeOut, Transform, Indicate, Flash, LaggedStart, MoveAlongPath, linear,
    UP, DOWN, LEFT, RIGHT, ORIGIN, UL, UR, DL, DR, WHITE, PI,
)
import numpy as np  # noqa: E402

# --- '팝 인' 과대 배율 자동 제한 -----------------------------------------------
# FadeIn(m, scale=1.8)은 '1.8배 크기에서 시작해 제자리로 줄어드는' 연출이다.
# 폭이 넓은 글자에 이걸 쓰면 시작 순간 화면 밖으로 삐져나가 잘린 채로 보인다
# (실측: 3편 A '각색 아님 — 실물이 남은 실화' 칩 폭 6.75 × 1.5 = 10.1 > 프레임 9.0).
# 아래 래퍼가 '지금 보이는 프레임 폭'을 넘지 않게 배율을 자동으로 깎는다.
VIS_W = [9.0]   # 현재 보이는 프레임 폭(카메라 드리프트 반영) — ShortBase가 갱신
_FadeIn = FadeIn


def FadeIn(m, **kw):  # noqa: F811
    k = kw.get("scale")
    if k and k > 1:
        w = float(getattr(m, "width", 0.0) or 0.0)
        h = float(getattr(m, "height", 0.0) or 0.0)
        lim = 99.0
        if w > 0.01:
            lim = min(lim, VIS_W[0] * 0.98 / w)
        if h > 0.01:
            lim = min(lim, VIS_W[0] * (16 / 9) * 0.98 / h)
        if k > lim:
            kw["scale"] = max(1.0, lim)
    return _FadeIn(m, **kw)


# [P2 / 2026-07-29 감사 처방] 시안·완성본 파일명 분리.
# build_v2 와 같은 함정이 여기에도 있었다 — 시안(540x960)이 완성본과 같은 shorts_A.mp4 를
# 덮어써서, 파일명만 보고는 무엇이 최종인지 알 수 없었다. 시안은 '_draft' 를 강제한다.
# refs/audit-reports/2026-07-29-quality-gate-failure.md §3-P2, 근본원인 R4.
NAME_SUFFIX = "" if FULL else "_540p_draft"

config.background_color = DARK
config.frame_width = 9.0
config.frame_height = 16.0
if AUDIT:
    # 감사 모드 — 해상도는 시안과 같게(540x960) 두고 프레임률만 5fps로 낮춰 싸게 돌린다.
    # 해상도를 더 낮추면 안 된다: manim 은 글자를 '픽셀 크기 캔버스'에 Pango 로 그린 뒤
    # 월드 좌표로 환산하므로, 캔버스가 좁으면 긴 문장이 자동 줄바꿈돼 기하가 달라진다.
    #   실측(같은 문장·fs40): 270x480 → 폭 13.04·높이 1.27(2줄) /
    #                        540x960·1080x1920·2160x3840 → 모두 폭 15.55·높이 0.53(1줄)
    # 즉 540 이상이면 시안·완성본 기하가 동일하다(시안 검수가 완성본을 대표함).
    config.pixel_width, config.pixel_height, config.frame_rate = 540, 960, 5
elif FULL:
    config.pixel_width, config.pixel_height, config.frame_rate = 1080, 1920, 30
else:
    config.pixel_width, config.pixel_height, config.frame_rate = 540, 960, 15
# 감사 렌더는 별도 media_dir 을 쓴다 — manim 의 글자 SVG 캐시는 파일명에 픽셀 크기를
# 넣지 않아서, 다른 해상도로 만든 캐시가 본렌더에 섞이면 글자 크기가 틀어진다.
config.media_dir = os.path.join(OUT, "media_audit" if AUDIT else "media_shorts")
config.disable_caching = True

with open(os.path.join(ROOT, "video", "scripts", f"{EP}.json"), encoding="utf-8") as f:
    SCRIPT = json.load(f)


FAST_DIR = os.path.join(OUT, "audio_fast")


def seg_info(i):
    """배속 처리된 음성 사용 — 없으면 ffmpeg atempo로 생성(음정 유지)."""
    os.makedirs(FAST_DIR, exist_ok=True)
    src = os.path.join(AUDIO_DIR, f"seg{i:03d}.wav")
    wav = os.path.join(FAST_DIR, f"seg{i:03d}.wav")
    if not os.path.exists(wav) or os.path.getmtime(wav) < os.path.getmtime(src):
        import imageio_ffmpeg
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", src,
                        "-filter:a", f"atempo={SPEED}", wav], check=True, capture_output=True)
    with wave.open(wav) as w:
        dur = w.getnframes() / float(w.getframerate())
    return {"id": i, "text": SCRIPT["segments"][i]["text"], "dur": dur, "wav": wav}


def make_bgm(dur_s, path):
    """저음 펄스 BGM 합성(104BPM 킥+햇+서브 드론) — 무음 제거용, 낮게 깔림."""
    sr = 44100
    t = np.arange(int(dur_s * sr)) / sr
    beat = 60 / 104
    sig = 0.05 * np.sin(2 * np.pi * 55 * t) * (0.7 + 0.3 * np.sin(2 * np.pi * t / 8))
    for k in np.arange(0, dur_s, beat):
        idx = (t >= k) & (t < k + 0.18)
        tt = t[idx] - k
        sig[idx] += 0.33 * np.sin(2 * np.pi * (60 * np.exp(-tt * 9) + 40) * tt) * np.exp(-tt * 16)
    rng = np.random.default_rng(7)
    noise = rng.standard_normal(len(t)) * 0.10
    for k in np.arange(beat / 2, dur_s, beat):
        idx = (t >= k) & (t < k + 0.05)
        sig[idx] += noise[idx] * np.exp(-(t[idx] - k) * 90)
    sig = np.tanh(sig) * 0.8
    data = (sig * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


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
        out[-1] = out[-1] + " " + buf if out else buf
    return out


def grid_bg():
    g = VGroup()
    for x in np.arange(-4.6, 4.7, 0.5):
        g.add(Line([x, -8.1, 0], [x, 8.1, 0]).set_stroke(DGRID, 1.2))
    for y in np.arange(-8.0, 8.1, 0.5):
        g.add(Line([-4.6, y, 0], [4.6, y, 0]).set_stroke(DGRID, 1.2))
    return g


def keep_in(m, max_w=SAFE_W, top=SAFE_TOP):
    """세이프 상자(가로 max_w·세로 ±top) 안으로 강제 — 넘치면 축소하고, 치우쳤으면 밀어 넣는다.

    쉬운 말: 액자(화면) 밖으로 삐져나간 글자를 '먼저 줄이고, 그래도 걸치면 안쪽으로 민다'."""
    if m.width > max_w:
        m.scale_to_fit_width(max_w)
    if m.height > 2 * top:
        m.scale_to_fit_height(2 * top)
    dx = dy = 0.0
    left, right = m.get_left()[0], m.get_right()[0]
    if left < -max_w / 2:
        dx = -max_w / 2 - left
    elif right > max_w / 2:
        dx = max_w / 2 - right
    bot, tp = m.get_bottom()[1], m.get_top()[1]
    if tp > top:
        dy = top - tp
    elif bot < -top:
        dy = -top - bot
    if dx or dy:
        m.shift(np.array([dx, dy, 0.0]))
    return m


class SafeText(Text):
    """배치(move_to·next_to) 직후 스스로 세이프 상자 안으로 들어가는 글자."""

    def move_to(self, *a, **kw):
        super().move_to(*a, **kw)
        return keep_in(self)

    def next_to(self, *a, **kw):
        super().next_to(*a, **kw)
        return keep_in(self)


class SafeGroup(VGroup):
    """배치 직후 스스로 세이프 상자 안으로 들어가는 묶음(칩·말풍선·여러 줄 문구)."""

    def move_to(self, *a, **kw):
        super().move_to(*a, **kw)
        return keep_in(self)

    def next_to(self, *a, **kw):
        super().next_to(*a, **kw)
        return keep_in(self)


def wrap_lines(s, n):
    """한 문장을 공백 기준으로 n줄에 균등 분배(글자 수 기준). 나눌 수 없으면 None."""
    words = s.split()
    if len(words) < n:
        return None
    target = len(s) / n
    lines, cur = [], ""
    for w in words:
        cand = (cur + " " + w).strip()
        if cur and len(cand) > target * 1.15 and len(lines) < n - 1:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    lines.append(cur)
    return lines if len(lines) == n and all(lines) else None


def ktext(s, fs=44, color=WHITE, bold=True, max_w=SAFE_W, max_lines=2):
    """한글 문구 — 세이프 폭을 넘으면 ①줄바꿈 먼저 ②그래도 넘치면 축소."""
    weight = "BOLD" if bold else "NORMAL"

    def mk(ls):
        if len(ls) == 1:
            return SafeText(ls[0], font=KFONT, font_size=fs, color=color, weight=weight)
        g = SafeGroup(*[Text(x, font=KFONT, font_size=fs, color=color, weight=weight) for x in ls])
        return g.arrange(DOWN, buff=0.14)

    t = mk([s])
    n = 2
    while t.width > max_w and n <= max_lines:
        ls = wrap_lines(s, n)
        if ls:
            cand = mk(ls)
            if cand.width < t.width:
                t = cand
        n += 1
    if t.width > max_w:
        t.scale_to_fit_width(max_w)
    return t


def chip(s, color=RED, fs=34, max_w=SAFE_W):
    t = Text(s, font=KFONT, font_size=fs, color=WHITE, weight="BOLD")
    if t.width > max_w - 0.55:      # 상자 여백(0.55)까지 합쳐 세이프 폭을 넘지 않게
        t.scale_to_fit_width(max_w - 0.55)
    box = RoundedRectangle(corner_radius=0.16, width=t.width + 0.55, height=t.height + 0.42)
    box.set_fill(color, 1).set_stroke(width=0)
    t.move_to(box)
    return SafeGroup(box, t)


def rect_overlap(a, b, eps=0.01):
    """두 바운딩박스(왼,오른,아래,위)의 겹침 폭·높이. 안 겹치면 None.
    (build_v2.rect_overlap 과 동일 — 두 조립기는 별도 스크립트라 공유 모듈이 없다.)"""
    ox = min(a[1], b[1]) - max(a[0], b[0])
    oy = min(a[3], b[3]) - max(a[2], b[2])
    return (ox, oy) if (ox > eps and oy > eps) else None


# --- 쇼츠 UI 가림 영역(2026-07-30 4편 이월 과업 ④) ----------------------------
#
# 쇼츠는 '프레임 안'이어도 안심할 수 없다: 앱이 영상 위에 자기 UI를 얹는다.
# 오른쪽 세로줄에 좋아요·댓글·공유·사운드 버튼, 아래에 채널명·제목·설명·진행바.
#
# 수치 근거(2026-07-30 실측 조사) — **공식 픽셀 수치는 공개돼 있지 않다.**
# 구글은 광고 도움말(support.google.com/google-ads/answer/13547298)에서 1080x1920
# 세이프존을 **그림(PNG 템플릿)으로만** 제공하고 본문에 숫자를 적지 않는다(직접 열어 확인).
# 그래서 아래 값은 **제3자 측정치의 보수적 상한**이며 '추정'으로 표기한다:
#   · 하단 여백: 300px(=15.6%) ~ 450px(=23.4%) 사이로 출처마다 다름 → 384px(20%) 채택
#   · 우측 여백:  96px(= 8.9%) ~ 130px(=12.0%) 사이 → 130px(12%) 채택
# 보수적(넓은) 쪽을 택한 이유: 이 검사의 목적은 '가려질 위험 경고'이고, 좁게 잡아
# 놓치는 비용이 넓게 잡아 한 번 더 보는 비용보다 크다. 앱 UI 는 연 3~5회 바뀌므로
# 이 상수는 **재검증 대상**이다(마지막 확인 2026-07-30).
SHORTS_UI_BOTTOM = 0.20   # 화면 아래에서부터 가려지는 비율(추정)
SHORTS_UI_RIGHT = 0.12    # 화면 오른쪽에서부터 가려지는 비율(추정)
# 자동 등록 구역 위반을 '차단'으로 셀 편 — 1~3편은 이미 발행돼 소급 변경하지 않는다.
ZONE_STRICT_FROM_EP = 4


def _zone_strict():
    try:
        return int(re.sub(r"\D", "", EP) or 0) >= ZONE_STRICT_FROM_EP
    except ValueError:
        return False


class ShortBase(MovingCameraScene):
    SPEC = None  # {"segs": [...], "hook": [...], "title": ...}

    def construct(self):
        VIS_W[0] = float(config.frame_width)
        self._grid = grid_bg()
        self.add(self._grid)
        self.subtitle = None
        self.reserve_ui_zones()   # 훅 카드 첫 컷부터 UI 대역이 살아 있게(전 구간 커버리지)
        self.hook_card()
        keep = self.SPEC.get("keep", set())  # 이 세그 뒤에는 화면을 지우지 않음(이야기 연속)
        for k, i in enumerate(self.SPEC["segs"]):
            self._cur_seg = i
            info = seg_info(i)
            getattr(self, f"seg{i:03d}")(info)
            if self.subtitle:
                self.remove(self.subtitle)
                self.subtitle = None
            if i in keep:
                self.hold(GAP)
            else:
                self.clear_stage(GAP if k < len(self.SPEC["segs"]) - 1 else 0.3)
        self._cur_seg = "end"
        self.end_card()
        self.report_overflow()

    # --- 불변식: 화면에 있는 모든 요소는 '지금 보이는 프레임' 안에 있어야 한다 -------
    # (2026-07-29 잘림 사고 재발 방지 — rule5 §2·§4. --audit 모드에서 초소형 렌더로 전수 검사)
    def _describe(self, m):
        txts = [s.text for s in m.get_family() if isinstance(s, Text)]
        if txts:
            return "「" + " / ".join(t[:16] for t in txts[:2]) + "」"
        return type(m).__name__

    # --- 보호 영역(본편 build_v2.EpisodeBase 에서 이식 — 2026-07-30 과업 ④) --------
    #
    # 이식 전 쇼츠에는 '프레임 이탈'만 있었다. 즉 **화면 안이면 무조건 통과**였고,
    # ①요소끼리 겹치거나 ②쇼츠 앱 UI(우측 버튼줄·하단 제목줄)에 가려지는 유형은
    # 원리상 검출되지 않았다. 본편에 있던 reserve_zone / avoid_zones / 침범 감사를
    # 그대로 옮기고, 쇼츠 고유의 'UI 가림 대역' 두 개를 상시 구역으로 얹는다.
    #
    # 본편과 다른 점: 쇼츠는 카메라가 밀고 들어간다(MovingCameraScene). UI 는 화면에
    # 붙어 있지 월드 좌표에 붙어 있지 않으므로, UI 대역은 **매 감사 시점의 카메라
    # 프레임에서 다시 계산**한다(고정 상자로 두면 줌이 들어간 순간 엉뚱한 곳을 지킨다).
    LAYOUT_MARGIN = 0.20     # 요소 사이 최소 여유(월드 단위, 프레임 폭 9.0 기준)
    UI_BOTTOM_ZONE = "쇼츠 UI 하단 대역(제목·채널·진행바)"
    UI_RIGHT_ZONE = "쇼츠 UI 우측 대역(좋아요·댓글·공유)"
    PHOTO_ZONE_PREFIX = "사진/스크린샷"

    _zones = None
    _intrusion = None
    _advice = None
    _zones_seen = None
    _seg_covered = None
    _cur_seg = "hook"
    _photo_n = 0

    @staticmethod
    def bbox(m, pad=0.0):
        return (m.get_left()[0] - pad, m.get_right()[0] + pad,
                m.get_bottom()[1] - pad, m.get_top()[1] + pad)

    def reserve_zone(self, name, m, pad=None, owners=(), kind="block",
                     enforce=True, track=None, ui=None):
        """침범 금지 구역 등록. 인자 의미는 build_v2.EpisodeBase.reserve_zone 과 같다.

        ui: ("bottom"|"right") — 카메라 프레임을 따라 움직이는 앱 UI 대역.
            월드 좌표가 아니라 '지금 보이는 화면'의 비율로 매번 다시 계산된다.
        """
        if self._zones is None:
            self._zones = {}
        pad = self.LAYOUT_MARGIN if pad is None else pad
        box = self.bbox(m) if hasattr(m, "get_left") else (tuple(m) if m else (0, 0, 0, 0))
        self._zones[name] = {"box": box, "pad": pad, "owners": set(),
                             "kind": kind, "enforce": enforce, "track": track, "ui": ui}
        if owners:
            self.claim_zone(name, *owners)
        return box

    def claim_zone(self, name, *owners):
        z = (self._zones or {}).get(name)
        if not z:
            return
        for o in owners:
            z["owners"].add(id(o))
            try:
                z["owners"].update(id(c) for c in o.get_family())
            except Exception:  # noqa: BLE001
                pass

    def claim_ui(self, *mobs):
        """앱 UI 대역에 **일부러** 두는 요소(구독 칩·© 표기 등)를 정식 거주자로 신고."""
        for nm in (self.UI_BOTTOM_ZONE, self.UI_RIGHT_ZONE):
            self.claim_zone(nm, *mobs)
        return mobs[0] if mobs else None

    def claim_all_photos(self, *mobs):
        """사진 위에 일부러 얹는 도장·라벨을 '정상 연출'로 신고."""
        for nm, z in (self._zones or {}).items():
            if z["kind"] == "edge" and nm.startswith(self.PHOTO_ZONE_PREFIX):
                self.claim_zone(nm, *mobs)
        return mobs[0] if mobs else None

    def reserve_ui_zones(self):
        """쇼츠 앱이 덮는 두 대역을 상시 구역으로 등록(전 구간 커버리지의 뼈대)."""
        self.reserve_zone(self.UI_BOTTOM_ZONE, None, pad=0.0, kind="block",
                          enforce=False, ui="bottom")
        self.reserve_zone(self.UI_RIGHT_ZONE, None, pad=0.0, kind="block",
                          enforce=False, ui="right")

    def _zone_box(self, z):
        """구역의 지금 상자 — UI 대역은 카메라 프레임에서, track 은 그 mobject 에서."""
        if z.get("ui"):
            f = self.camera.frame
            l, r = f.get_left()[0], f.get_right()[0]
            b, t = f.get_bottom()[1], f.get_top()[1]
            if z["ui"] == "bottom":
                return (l, r, b, b + (t - b) * SHORTS_UI_BOTTOM)
            return (r - (r - l) * SHORTS_UI_RIGHT, r, b, t)
        tr = z.get("track")
        if tr is not None:
            try:
                return self.bbox(tr)
            except Exception:  # noqa: BLE001
                return z["box"]
        return z["box"]

    def _live_ids(self):
        live = set()
        for m in self.mobjects:
            try:
                live.update(id(x) for x in m.get_family())
            except Exception:  # noqa: BLE001
                live.add(id(m))
        return live

    @staticmethod
    def _contains(outer, inner, eps=0.01):
        return (outer[0] - eps <= inner[0] and inner[1] <= outer[1] + eps
                and outer[2] - eps <= inner[2] and inner[3] <= outer[3] + eps)

    def _obstacles(self, exclude=()):
        boxes = [(nm, self._zone_box(z), z["pad"])
                 for nm, z in (self._zones or {}).items() if z.get("enforce", True)]
        boxes += [(self._describe(m), self.bbox(m), self.LAYOUT_MARGIN) for m in exclude]
        return boxes

    def avoid_zones(self, m, pad=None, rounds=4):
        """m 이 (강제) 보호 영역을 침범하면 비켜 세운다 — keep_in() 의 '겹침' 짝.
        비킨 뒤 세이프 상자 안으로 다시 밀어 넣어 회피가 새 잘림을 만들지 않게 한다."""
        pad = self.LAYOUT_MARGIN if pad is None else pad
        for _ in range(rounds):
            worst = None
            for nm, z in (self._zones or {}).items():
                if id(m) in z["owners"] or not z.get("enforce", True):
                    continue
                ov = rect_overlap(self.bbox(m, pad * 0.5), self._zone_box(z))
                if ov and (worst is None or min(ov) > min(worst[1])):
                    worst = (nm, ov, z)
            if worst is None:
                break
            _nm, (ox, oy), z = worst
            zl, zr, zb, zt = self._zone_box(z)
            l, r, b, t = self.bbox(m)
            if ox <= oy:
                away = -1.0 if (l + r) / 2 <= (zl + zr) / 2 else 1.0
                m.shift(np.array([(ox + pad * 0.5) * away, 0.0, 0.0]))
            else:
                away = 1.0 if (b + t) / 2 >= (zb + zt) / 2 else -1.0
                m.shift(np.array([0.0, (oy + pad * 0.5) * away, 0.0]))
            keep_in(m)
        return m

    def _register_photo_zone(self, grp, label):
        type(self)._photo_n += 1
        nm = f"{self.PHOTO_ZONE_PREFIX} {type(self)._photo_n}: {label}"
        self.reserve_zone(nm, grp, pad=0.0, owners=[grp], kind="edge",
                          enforce=False, track=grp)
        return nm

    def audit_frame(self):
        # 시안·완성 렌더에서도 항상 돈다(비용: 바운딩박스 계산뿐) — 잘림은 조용히 지나가면 안 된다.
        if self._intrusion is None:
            self._intrusion, self._advice = {}, {}
            self._zones_seen, self._seg_covered = set(), set()
        if self.UI_BOTTOM_ZONE not in (self._zones or {}):
            self.reserve_ui_zones()   # construct 를 안 거친 경로(단위 검사 등) 대비
        frame = self.camera.frame
        hw, hh = frame.width / 2, frame.height / 2
        live = self._live_ids()
        zones = []
        for nm, z in self._zones.items():
            tr = z.get("track")
            if tr is not None and id(tr) not in live:
                continue
            zones.append((nm, self._zone_box(z), z))
            self._zones_seen.add(nm)
        if zones:
            self._seg_covered.add(self._cur_seg)
        strict = _zone_strict()
        for m in self.mobjects:
            if m is frame or m is getattr(self, "_grid", None) or m is self.subtitle:
                continue
            try:
                left, right = m.get_left()[0], m.get_right()[0]
                bot, top = m.get_bottom()[1], m.get_top()[1]
            except Exception:
                continue
            ox = max(0.0, -hw - left, right - hw)
            oy = max(0.0, -hh - bot, top - hh)
            if max(ox, oy) > 0.02:
                key = self._describe(m)
                prev = self.overflow.get(key, (0.0, 0.0, 0.0))
                self.overflow[key] = (max(prev[0], ox), max(prev[1], oy), frame.width)
            box = (left, right, bot, top)
            for nm, zbox, z in zones:
                if id(m) in z["owners"]:
                    continue
                hard = rect_overlap(box, zbox)
                if not hard:
                    continue
                if z["kind"] == "edge" and (self._contains(zbox, box)
                                            or self._contains(box, zbox)):
                    continue   # 사진 안에 온전히(의도한 겹쳐 찍기) / 밖에 온전히 = 정상
                auto = not z.get("enforce", True)
                bucket = self._intrusion if (not auto or strict) else self._advice
                k = f"{self._describe(m)} ↔ {nm}"
                p = bucket.get(k, (0.0, 0.0))
                bucket[k] = (max(p[0], hard[0]), max(p[1], hard[1]))

    overflow = None

    def zone_coverage(self):
        segs = ["hook"] + list((self.SPEC or {}).get("segs", [])) + ["end"]
        return len(self._seg_covered or set()), len(segs)

    def report_overflow(self):
        """[audit] 줄 출력 — verify_output_spec.py 가 이 형식을 정규식으로 읽는다."""
        name = type(self).__name__
        if not self.overflow:
            print(f"[audit] {name}: 프레임 이탈 0건 — 모든 요소가 화면 안")
        else:
            print(f"[audit] {name}: 프레임 이탈 {len(self.overflow)}건 "
                  f"(가로 초과/세로 초과, 월드 단위 · 프레임 폭 9.0 기준)")
            for k, (ox, oy, fw) in sorted(self.overflow.items(),
                                          key=lambda x: -max(x[1][0], x[1][1])):
                print(f"    - {k}: 가로 +{ox:.2f} / 세로 +{oy:.2f} (당시 가시 폭 {fw:.2f})")
        self.report_zones()

    def report_zones(self):
        name = type(self).__name__
        it = self._intrusion or {}
        ad = self._advice or {}
        seen = self._zones_seen or set()
        blocking = sum(1 for nm in seen
                       if (self._zones or {}).get(nm, {}).get("enforce", True))
        cov, tot = self.zone_coverage()
        strict = "차단" if _zone_strict() else "권고"
        print(f"[audit] {name}: 보호영역 침범 {len(it)}건 "
              f"(등록 구역 {len(seen)}개[명시 {blocking}·자동 {len(seen) - blocking}"
              f"={strict}], 구간 커버리지 {cov}/{tot})")
        for k, (ox, oy) in sorted(it.items(), key=lambda x: -min(x[1])):
            print(f"    - 침범 {k}: 겹침 가로 {ox:.2f} / 세로 {oy:.2f}")
        print(f"[audit] {name}: 표시영역 권고 위반 {len(ad)}건 "
              f"({ZONE_STRICT_FROM_EP}편부터 차단 · UI 가림 추정 하단 "
              f"{SHORTS_UI_BOTTOM:.0%}·우측 {SHORTS_UI_RIGHT:.0%})")
        for k, (ox, oy) in sorted(ad.items(), key=lambda x: -min(x[1])):
            print(f"    - 권고 {k}: 겹침 가로 {ox:.2f} / 세로 {oy:.2f}")

    def play(self, *a, **kw):
        if self.overflow is None:
            self.overflow = {}
        super().play(*a, **kw)
        VIS_W[0] = float(self.camera.frame.width)
        self.audit_frame()

    def wait(self, *a, **kw):
        if self.overflow is None:
            self.overflow = {}
        super().wait(*a, **kw)
        VIS_W[0] = float(self.camera.frame.width)
        self.audit_frame()

    # --- 공통 ---
    def sub(self, txt):
        t = Text(txt, font=KFONT, font_size=40, color=WHITE, weight="BOLD")
        if t.width > SUB_W - 0.5:   # 상자(+0.5)까지 합쳐 프레임 폭의 91% 이내
            t.scale_to_fit_width(SUB_W - 0.5)
        t.move_to(DOWN * 5.1)
        bg = RoundedRectangle(corner_radius=0.18, width=t.width + 0.5, height=t.height + 0.42)
        bg.set_fill("#000000", 0.55).set_stroke(width=0).move_to(t)
        grp = VGroup(bg, t)
        # 카메라에 고정 — 줌이 들어가도 자막은 항상 같은 화면 크기·위치
        frame = self.camera.frame
        base_w = grp.width

        def pin(m):
            k = frame.width / config.frame_width
            m.set_width(base_w * k)
            m.move_to(frame.get_center() + DOWN * frame.height * 0.319)

        grp.add_updater(pin)
        if self.subtitle:
            self.remove(self.subtitle)
        self.add(grp)
        self.subtitle = grp

    POP_POS = [UP * 5.3 + LEFT * 0.9, UP * 5.0 + RIGHT * 1.0, UP * 5.4]

    def beats(self, info, acts):
        sents = split_sents(info["text"])
        chars = sum(len(s) for s in sents) or 1
        durs = [max(0.7, info["dur"] * len(s) / chars) for s in sents]
        scale = info["dur"] / sum(durs)
        pops = self.SPEC.get("pops", {}).get(info["id"], [])
        pop_i = 0
        for i, (txt, d) in enumerate(zip(sents, [x * scale for x in durs])):
            self.sub(txt)
            pop = None
            if i < len(pops) and pops[i]:
                # 텍스트 팝 — 키워드가 화면 상단에 쾅 박힘 (앰버/흰색 교차, 살짝 기울임)
                color = AMBER if pop_i % 2 == 0 else WHITE
                # 팝은 세이프 폭보다 좁게(6.4) — 화면 밖 여유를 남겨 '쾅' 배율을 살린다.
                # 줄바꿈은 금지(max_lines=1): 두 줄이 되면 위로 커져 상단 날짜 칩과 겹친다.
                pop = ktext(pops[i], fs=86, color=color, max_w=6.4, max_lines=1)
                pop.rotate(0.05 * (1 if pop_i % 2 else -1))
                pop.move_to(self.POP_POS[pop_i % 3])
                pop_i += 1
                t_in = min(0.22, d * 0.2)
                self.play(FadeIn(pop, scale=1.8), run_time=t_in)
                d -= t_in
            if i < len(acts) and acts[i]:
                acts[i](max(0.3, d - (0.15 if pop else 0)))
            else:
                self.hold(max(0.3, d - (0.15 if pop else 0)))
            if pop is not None:
                self.play(FadeOut(pop, scale=0.8), run_time=0.15)

    def _drift(self, steps=1.0):
        # 줌 하한선(ZOOM_FLOOR) 아래로는 더 밀고 들어가지 않음 — 화면 밖 잘림 방지
        frame = self.camera.frame
        if frame.width * (ZOOM_DRIFT ** steps) < ZOOM_FLOOR:
            return None
        return frame.animate.scale(ZOOM_DRIFT ** steps)

    def act(self, d, *anims, rt=None):
        if anims:
            rt = max(0.3, min(rt if rt is not None else min(1.2, d * 0.6), d))
            drift = self._drift()
            self.play(*(list(anims) + ([drift] if drift else [])), run_time=rt)
            d -= rt
        self.hold(d)

    def hold(self, d):
        # 정지화면 금지 — 대기 시간에도 화면이 천천히 밀고 들어간다
        if d <= 2.0 / config.frame_rate:
            return
        drift = self._drift(max(1.0, d * 2))
        if drift:
            self.play(drift, run_time=d, rate_func=linear)
        else:
            self.wait(d)

    def clear_stage(self, rt):
        ms = [m for m in self.mobjects if m is not self.subtitle]
        fade = ms[1:]  # ms[0] = 모눈 배경은 유지
        frame = self.camera.frame
        reset = frame.animate.scale(config.frame_width / frame.width)  # 줌 원위치
        if fade:
            self.play(*[FadeOut(m) for m in fade], reset, run_time=max(0.25, rt))
        else:
            self.play(reset, run_time=max(0.25, rt))

    def photo(self, fname, height=4.5, pos=ORIGIN, framed=True):
        img = ImageMobject(os.path.join(ASSETS, fname))
        img.height = height
        if img.width > SAFE_W:      # 가로 사진이 프레임 밖으로 새어 액자가 잘리는 것 방지
            img.scale_to_fit_width(SAFE_W)
        img.move_to(pos)
        if not framed:  # 투명 PNG(배지 등) — 흰 액자 없이
            grp = Group(img)
        else:
            border = Rectangle(width=img.width + 0.1, height=img.height + 0.1)
            border.set_stroke(WHITE, 5).move_to(img)
            grp = Group(img, border)
        # 사진 1장 = 보호영역 1개(테두리를 무는 배치만 적발 — 과업 ④)
        self._register_photo_zone(grp, fname)
        return grp

    def show(self, *ms):
        self.add(*ms)
        if self.subtitle:
            self.remove(self.subtitle)
            self.add(self.subtitle)

    def hook_card(self):
        lines = self.SPEC["hook"]
        t1 = ktext(lines[0], fs=72, color=WHITE).move_to(UP * 1.6)
        t2 = ktext(lines[1], fs=88, color=AMBER).move_to(UP * 0.1)
        frame = self.camera.frame
        frame.scale(1.12)  # 펀치 인으로 시작
        self.play(FadeIn(t1, scale=1.2), frame.animate.scale(1 / 1.12), run_time=0.4)
        self.play(FadeIn(t2, scale=1.35), Flash(t2.get_center(), color=AMBER, flash_radius=2.2), run_time=0.45)
        self.play(frame.animate.scale(0.97), run_time=max(0.2, HOOK_D - 0.85), rate_func=linear)
        self.play(FadeOut(t1), FadeOut(t2), frame.animate.scale(1 / 0.97), run_time=0.25)

    def end_card(self):
        t = ktext("전체 이야기는 채널에서", fs=52).move_to(UP * 0.8)
        btn = chip("구독", RED, 46).move_to(DOWN * 0.6)
        cc = Text("© nous-zero", font=KFONT, font_size=26, color=GRAY).move_to(DOWN * 2.0)
        self.play(FadeIn(t, shift=UP * 0.2), FadeIn(btn, scale=1.4), FadeIn(cc), run_time=0.5)
        self.wait(END_D - 0.5)

    # --- 세그 장면 (세로 구도) ---
    def seg000(self, info):
        term = RoundedRectangle(corner_radius=0.25, width=SAFE_W, height=5.2)
        term.set_stroke(BLUE_L, 4).set_fill("#101A30", 1).move_to(UP * 1.6)
        prompt = Text(">", font=MONO, font_size=44, color=GRAY, weight="BOLD")
        prompt.move_to(term.get_corner(UL) + RIGHT * 0.6 + DOWN * 0.7)
        self.st = {"term": term}

        def a0(d):
            self.act(d, Create(term), FadeIn(prompt))

        def a1(d):
            hello = Text("HELLO", font=MONO, font_size=64, color=GRAY, weight="BOLD")
            hello.move_to(term.get_center() + UP * 0.6)
            strike = Line(hello.get_left() + LEFT * 0.15, hello.get_right() + RIGHT * 0.15).set_stroke(RED, 7)
            t1 = max(0.3, min(0.7, d * 0.4))
            self.play(FadeIn(hello), run_time=t1)
            t2 = max(0.3, min(0.5, d * 0.3))
            self.play(Create(strike), run_time=t2)
            self.hold(d - t1 - t2)

        def a2(d):
            lo = Text("LO", font=MONO, font_size=150, color=BLUE, weight="BOLD")
            lo.move_to(term.get_center() + DOWN * 0.9)
            self.act(d, FadeIn(lo, scale=1.5), Flash(lo.get_center(), color=BLUE, flash_radius=2.0))

        self.beats(info, [a0, a1, a2])

    def seg001(self, info):
        def a0(d):
            date = chip("1969.10.29", INK, 36).move_to(UP * 6.3)
            self.act(d, FadeIn(date, shift=DOWN * 0.2))

        def a1(d):
            a = Dot(LEFT * 3.0 + DOWN * 3.0, radius=0.18, color=BLUE)
            b = Dot(RIGHT * 3.0 + DOWN * 3.0, radius=0.18, color=WHITE)
            la = ktext("UCLA", 30, GRAY).next_to(a, DOWN, buff=0.25)
            lb = ktext("스탠퍼드", 30, GRAY).next_to(b, DOWN, buff=0.25)
            link = Line(a.get_center(), b.get_center(), buff=0.25).set_stroke(GRAY, 3)
            self.act(d, FadeIn(a), FadeIn(b), FadeIn(la), FadeIn(lb), Create(link))

        def a2(d):
            boxes = VGroup()
            for ch in "LOGIN":
                sq = RoundedRectangle(corner_radius=0.1, width=1.25, height=1.25)
                sq.set_stroke(GRAY, 3).set_fill("#101A30", 1)
                letter = Text(ch, font=MONO, font_size=60, color=GRAY, weight="BOLD").move_to(sq)
                boxes.add(VGroup(sq, letter))
            boxes.arrange(RIGHT, buff=0.28).move_to(DOWN * 0.8)
            self.st["login"] = boxes
            self.act(d, LaggedStart(*[FadeIn(b, scale=1.2) for b in boxes], lag_ratio=0.12))

        self.beats(info, [a0, a1, a2])

    def seg002(self, info):
        def a0(d):
            boxes = self.st.get("login")
            if boxes is None:
                self.hold(d)
                return
            t_each = max(0.3, min(0.7, d * 0.2))
            for i in (0, 1):
                self.play(boxes[i][0].animate.set_stroke(BLUE, 5).set_fill("#14264a", 1),
                          boxes[i][1].animate.set_color(BLUE), run_time=t_each)
            x = VGroup(Line(UL * 0.5, DR * 0.5), Line(UR * 0.5, DL * 0.5)).set_stroke(RED, 10)
            x.move_to(boxes.get_center() + UP * 2.2)
            t3 = max(0.3, min(0.8, d * 0.3))
            self.play(FadeIn(x, scale=1.5), *[boxes[i][1].animate.set_color("#4B5563") for i in (2, 3, 4)],
                      run_time=t3)
            self.hold(d - 2 * t_each - t3)

        def a1(d):
            ph = self.photo("imp_log.jpg", height=3.4, pos=UP * 2.2)
            cap = chip("실제 기록", RED, 30).next_to(ph, UP, buff=0.3)
            self.show(ph)
            self.act(d, FadeIn(cap, scale=1.2), rt=0.5)
            self.st["log"] = ph

        def a2(d):
            self.act(d, Indicate(self.st["log"][1], color=AMBER, scale_factor=1.04))

        self.beats(info, [a0, a1, a2])

    def seg003(self, info):
        def a0(d):
            why = ktext("왜?", fs=110, color=WHITE).move_to(UP * 1.5)
            self.st = {"why": why}
            self.act(d, FadeIn(why, scale=1.5))

        def a1(d):
            ph = self.photo("baker.jpg", height=4.6, pos=UP * 1.3)
            cold = chip("냉전 시대", INK, 34).next_to(ph, UP, buff=0.4)
            self.play(FadeOut(self.st.pop("why")), run_time=0.25)
            self.show(ph)
            self.act(d - 0.25, FadeIn(cold), rt=0.4)

        self.beats(info, [a0, a1])

    def seg005(self, info):
        import math
        center = Circle(radius=0.5).set_stroke(RED, 5).set_fill("#3a0d0d", 1).move_to(UP * 1.8)
        outer, spokes = VGroup(), VGroup()
        for i in range(8):
            ang = i * PI / 4
            p = np.array([3.0 * math.cos(ang), 1.8 + 2.6 * math.sin(ang), 0])
            outer.add(Dot(p, radius=0.15, color=GRAY))
            spokes.add(DashedLine(center.get_center(), p, buff=0.4).set_stroke("#4B5563", 3))

        def a0(d):
            self.act(d, Create(center), LaggedStart(*[Create(s) for s in spokes], lag_ratio=0.06),
                     FadeIn(outer), rt=min(1.4, d * 0.6))

        def a1(d):
            x = VGroup(Line(UL * 0.6, DR * 0.6), Line(UR * 0.6, DL * 0.6)).set_stroke(RED, 12)
            x.move_to(center)
            self.act(d, FadeIn(x, scale=1.6), Flash(center.get_center(), color=RED, flash_radius=1.6))

        def a2(d):
            phrase = ktext("심장이 없는 통신망", fs=58, color=AMBER).move_to(DOWN * 2.6)
            self.act(d, FadeIn(phrase, scale=1.25))

        self.beats(info, [a0, a1, a2])

    def seg006(self, info):
        P = [(-2.8, 3.3), (-0.2, 3.9), (2.6, 3.4), (-3.0, 1.4), (-0.4, 1.9), (2.4, 1.5),
             (-1.8, -0.2), (0.9, 0.1), (2.9, -0.4)]
        pts = [np.array([x, y, 0]) for x, y in P]
        E = [(0, 1), (1, 2), (0, 3), (1, 4), (2, 5), (3, 4), (4, 5), (3, 6), (4, 7),
             (5, 8), (6, 7), (7, 8), (4, 6), (5, 7)]
        nodes = VGroup(*[Dot(p, radius=0.16, color=WHITE) for p in pts])
        edges = VGroup(*[Line(pts[a], pts[b], buff=0.2).set_stroke(GRAY, 3) for a, b in E])
        self.st = {"mesh": (nodes, edges)}

        def a0(d):
            self.act(d, LaggedStart(*[FadeIn(n, scale=1.3) for n in nodes], lag_ratio=0.05),
                     LaggedStart(*[Create(e) for e in edges], lag_ratio=0.04), rt=min(1.8, d * 0.7))

        def a1(d):
            self.act(d, Indicate(edges, color=BLUE, scale_factor=1.0))

        def a2(d):
            cut = edges[8]
            broken = DashedLine(cut.get_start(), cut.get_end()).set_stroke(RED, 4)
            alt = [edges[i] for i in (3, 6)]
            t1 = max(0.3, min(0.7, d * 0.3))
            self.play(Transform(cut, broken), run_time=t1)
            t2 = max(0.3, min(0.9, d * 0.35))
            self.play(*[e.animate.set_stroke(BLUE, 7) for e in alt], run_time=t2)
            self.hold(d - t1 - t2)

        self.beats(info, [a0, a1, a2])

    def seg012(self, info):
        def a0(d):
            self.hold(d)

        def a1(d):
            m = Triangle().scale(0.5).rotate(PI).set_fill(RED, 1).set_stroke(RED, 3).move_to(UP * 3.6 + LEFT * 2.6)
            ar1 = Line(LEFT * 1.6 + UP * 3.6, LEFT * 0.4 + UP * 3.6).set_stroke(GRAY, 5)
            net = VGroup(*[Dot(np.array([0.9 + 0.75 * (i % 3), 3.1 + 0.75 * (i // 3), 0]), radius=0.1, color=WHITE)
                           for i in range(6)])
            self.act(d, FadeIn(m), Create(ar1), FadeIn(net), rt=min(1.4, d * 0.6))

        def a2(d):
            p1 = ktext("모든 해결은,", fs=62, color=WHITE).move_to(UP * 0.6)
            p2 = chip("새로운 문제", AMBER, 56).move_to(DOWN * 0.8)
            p3 = ktext("를 낳는다", fs=62, color=WHITE).move_to(DOWN * 2.2)
            self.act(d, FadeIn(p1, shift=UP * 0.15), FadeIn(p2, scale=1.25), FadeIn(p3, shift=DOWN * 0.15),
                     rt=min(1.1, d * 0.55))

        self.beats(info, [a0, a1, a2])


class ShortA(ShortBase):
    SPEC = {"segs": [0, 1, 2], "keep": {0, 1},
            "hook": ["인터넷의 첫마디는", '"헬로"가 아니다'],
            "pops": {0: ["첫마디?", None, "딱 두 글자"],
                     1: [None, "첫 전송", None],
                     2: ["크래시!", "그래서 LO", None]}}


class ShortB(ShortBase):
    SPEC = {"segs": [3, 5, 6, 12],
            "hook": ["핵전쟁이 만든", "인터넷"],
            "pops": {3: [None, "냉전"],
                     5: ["심장 하나", None, None],
                     6: ["그물망", None, "옆길이 있다"],
                     12: [None, "법칙", None]}}


# ---------- 2편: TCP/IP Flag Day — 세로 장면 ----------

class Short02Base(ShortBase):
    """2편 세그 장면(세로 구도·다크). 본편 build_v2.Episode02 연출을 9:16으로 재구성."""

    def construct(self):
        self.st = {}
        super().construct()

    def envelope_icon(self, w=2.2, h=1.4, color=BLUE):
        body = RoundedRectangle(corner_radius=0.08, width=w, height=h)
        body.set_stroke(color, 5).set_fill("#101A30", 1)
        flap = VGroup(Line(body.get_corner(UL), body.get_center() + UP * 0.06),
                      Line(body.get_corner(UR), body.get_center() + UP * 0.06))
        flap.set_stroke(color, 5)
        return VGroup(body, flap)

    # --- 0: 1982.12.31 밤 — 퇴근 못 한 전산실 (실사: NORAD) ---
    def seg000(self, info):
        def a0(d):
            card = RoundedRectangle(corner_radius=0.2, width=3.6, height=2.5)
            card.set_stroke(BLUE_L, 4).set_fill("#101A30", 1).move_to(UP * 3.0)
            header = Rectangle(width=3.6, height=0.62).set_fill(RED, 1).set_stroke(width=0)
            header.move_to(card.get_top() + DOWN * 0.31)
            yr = ktext("1982년 12월", fs=26).move_to(header)
            day = Text("31", font=MONO, font_size=80, color=WHITE, weight="BOLD")
            day.move_to(card.get_center() + DOWN * 0.28)
            night = chip("밤", INK, 26).next_to(card, RIGHT, buff=0.35)
            self.st["cal"] = VGroup(card, header, yr, day, night)
            self.act(d, FadeIn(VGroup(card, header, yr, day), scale=1.1), FadeIn(night))

        def a1(d):
            ph = self.photo("ep02_norad_computer_room_1984.jpg", height=3.6, pos=DOWN * 1.1)
            shade = Rectangle(width=ph[0].width, height=ph[0].height)
            shade.set_fill(DARK, 0.42).set_stroke(width=0).move_to(ph[0])
            room = Group(ph[0], shade, ph[1])  # 사진 → 어둠막 → 액자: '밤샘'의 공기
            cap = chip("NORAD 전산실 — 미 공군 기록(1984)", INK, 20).next_to(room, DOWN, buff=0.25)
            self.st["room"] = room
            t1 = max(0.4, min(0.9, d * 0.35))
            self.play(FadeIn(room, scale=1.04), FadeIn(cap), run_time=t1)
            if self.subtitle:
                self.remove(self.subtitle)
                self.add(self.subtitle)
            self.hold(d - t1)

        def a2(d):
            note = chip("내일 아침 — 인터넷의 언어 교체", RED, 28).move_to(UP * 1.2)
            self.act(d, FadeIn(note, shift=UP * 0.2))

        self.beats(info, [a0, a1, a2])

    # --- 2: 세 개의 망 — 실사 3단(위성·무선·아파넷), 서로 불통 ---
    def seg002(self, info):
        def a0(d):
            era = chip("1970년대", INK, 30).move_to(LEFT * 3.2 + UP * 4.5)
            self.act(d, FadeIn(era, shift=DOWN * 0.2))

        def a1(d):
            specs = [("ep02_goldstone_dish_1972.jpg", "위성망", BLUE, UP * 2.9),
                     ("ep02_sri_packet_radio_van_2x.jpg", "무선망", AMBER, ORIGIN),
                     ("imp_panel.jpg", "ARPANET", INK, DOWN * 2.9)]
            nets, rects = [], []
            for fname, lab, co, pos in specs:
                ph = self.photo(fname, height=2.2, pos=pos)
                tag = chip(lab, co, 22)  # 방송 자막 스타일 — 사진 좌상단
                tag.move_to(ph[1].get_corner(UL) + RIGHT * (tag.width / 2 + 0.1)
                            + DOWN * (tag.height / 2 + 0.1))
                nets.append(Group(ph, tag))
                rects.append(ph[1])
            self.st["nets"], self.st["netr"] = nets, rects
            t1 = max(0.6, min(2.2, d * 0.55))
            self.play(LaggedStart(*[FadeIn(n, scale=1.06) for n in nets], lag_ratio=0.25),
                      run_time=t1)
            if self.subtitle:
                self.remove(self.subtitle)
                self.add(self.subtitle)
            self.hold(d - t1)

        def a2(d):
            oks = VGroup(*[chip("OK", BLUE, 20).move_to(r.get_corner(UR) + LEFT * 0.5 + DOWN * 0.35)
                           for r in self.st["netr"]])
            self.st["oks"] = oks
            self.act(d, LaggedStart(*[FadeIn(o, scale=1.3) for o in oks], lag_ratio=0.2))

        def a3(d):
            links, xs = VGroup(), VGroup()
            for i in (0, 1):
                a = self.st["netr"][i].get_bottom()
                b = self.st["netr"][i + 1].get_top()
                links.add(DashedLine(a, b, buff=0.12).set_stroke(GRAY, 3))
                mid = (a + b) / 2
                xs.add(VGroup(Line(UL * 0.26, DR * 0.26),
                              Line(UR * 0.26, DL * 0.26)).set_stroke(RED, 9).move_to(mid))
            t1 = max(0.3, min(0.7, d * 0.35))
            self.play(Create(links), run_time=t1)
            t2 = max(0.3, min(0.6, d * 0.3))
            self.play(FadeIn(xs, scale=1.5), run_time=t2)
            self.hold(d - t1 - t2)

        self.beats(info, [a0, a1, a2, a3])

    # --- 5: 발상의 전환 — 망 위에 공통 봉투 ---
    def seg005(self, info):
        def a0(d):
            env = self.envelope_icon(2.6, 1.65).move_to(UP * 2.3)
            tag = chip("공통 봉투", BLUE, 32).next_to(env, DOWN, buff=0.45)
            self.st["env"] = env
            self.act(d, FadeIn(env, scale=1.2), FadeIn(tag))

        def a1(d):
            data = RoundedRectangle(corner_radius=0.08, width=0.85, height=0.6)
            data.set_stroke(WHITE, 3).set_fill(INK, 1).move_to(UP * 4.2 + LEFT * 2.6)
            t1 = max(0.3, min(0.6, d * 0.3))
            self.play(FadeIn(data, shift=DOWN * 0.2), run_time=t1)
            t2 = max(0.4, min(0.9, d * 0.4))
            self.play(data.animate.scale(0.55).move_to(self.st["env"].get_center()),
                      run_time=t2)
            t3 = max(0.3, min(0.5, d * 0.15))
            self.play(FadeOut(data), Indicate(self.st["env"], color=BLUE), run_time=t3)
            self.hold(d - t1 - t2 - t3)

        def a2(d):
            # 어떤 망(파랑·앰버·흰색)을 지나든 봉투는 통과한다
            pts = [LEFT * 2.9 + DOWN * 1.8, DOWN * 2.6, RIGHT * 2.9 + DOWN * 3.4]
            dots = VGroup(*[Dot(p, radius=0.16, color=c)
                            for p, c in zip(pts, [BLUE, AMBER, WHITE])])
            lines = VGroup(*[DashedLine(pts[i], pts[i + 1], buff=0.22).set_stroke(GRAY, 3)
                             for i in (0, 1)])
            small = self.st["env"].copy().scale(0.42)
            t1 = max(0.3, min(0.7, d * 0.25))
            self.play(FadeIn(dots), Create(lines), run_time=t1)
            t2 = max(0.3, min(0.5, d * 0.15))
            self.play(small.animate.move_to(pts[0]), run_time=t2)
            rest = d - t1 - t2
            for i in (1, 2):
                t = max(0.35, min(1.0, rest * 0.4))
                self.play(MoveAlongPath(small, Line(pts[i - 1], pts[i])), run_time=t)
                rest -= t
            self.hold(rest)

        self.beats(info, [a0, a1, a2])

    # --- 9: 초강수 공지 — 유예 없음 ---
    def seg009(self, info):
        def a0(d):
            notice = RoundedRectangle(corner_radius=0.18, width=6.6, height=6.6)
            notice.set_stroke(RED, 6).set_fill("#101A30", 1).move_to(UP * 0.4)
            head = ktext("공 지", fs=52, color=RED).move_to(notice.get_top() + DOWN * 0.75)
            rule = Line(notice.get_left() + RIGHT * 0.5, notice.get_right() + LEFT * 0.5)
            rule.set_stroke(GRAY, 2).move_to(notice.get_top() + DOWN * 1.35)
            self.st["notice"] = VGroup(notice, head, rule)
            self.act(d, FadeIn(self.st["notice"], scale=1.08))

        def a1(d):
            item1 = VGroup(ktext("1983.1.1부로", fs=40),
                           ktext("옛 언어(NCP) 차단", fs=40)).arrange(DOWN, buff=0.2)
            item1.move_to(self.st["notice"][0].get_center() + UP * 1.05)
            self.act(d, FadeIn(item1, shift=UP * 0.15))

        def a2(d):
            item2 = VGroup(ktext("못 갈아탄 컴퓨터는", fs=34, color=GRAY),
                           ktext("인터넷에서 잘린다", fs=40)).arrange(DOWN, buff=0.2)
            item2.move_to(self.st["notice"][0].get_center() + DOWN * 1.15)
            self.act(d, FadeIn(item2, shift=UP * 0.15))

        def a3(d):
            stamp = chip("유예 없음", RED, 44).rotate(0.2)
            stamp.move_to(self.st["notice"][0].get_corner(DR) + UL * 1.1)
            t1 = max(0.3, min(0.6, d * 0.35))
            self.play(FadeIn(stamp, scale=1.9), run_time=t1)
            t2 = max(0.3, min(0.5, d * 0.2))
            self.play(Flash(stamp.get_center(), color=RED, flash_radius=1.6), run_time=t2)
            self.hold(d - t1 - t2)

        self.beats(info, [a0, a1, a2, a3])

    # --- 10: 1983.1.1 — 일제 전환(Flag Day) ---
    def seg010(self, info):
        def a0(d):
            card = RoundedRectangle(corner_radius=0.18, width=3.2, height=2.3)
            card.set_stroke(BLUE_L, 4).set_fill("#101A30", 1).move_to(UP * 3.3)
            header = Rectangle(width=3.2, height=0.58).set_fill(RED, 1).set_stroke(width=0)
            header.move_to(card.get_top() + DOWN * 0.29)
            yr = ktext("1983년 1월", fs=24).move_to(header)
            day = Text("1", font=MONO, font_size=76, color=WHITE, weight="BOLD")
            day.move_to(card.get_center() + DOWN * 0.26)
            self.st["cal83"] = VGroup(card, header, yr, day)
            self.act(d, FadeIn(self.st["cal83"], scale=1.15))

        def a1(d):
            grid = VGroup()
            for r in range(4):
                for c in range(4):
                    sq = RoundedRectangle(corner_radius=0.08, width=1.35, height=0.95)
                    sq.set_stroke(GRAY, 3).set_fill("#101A30", 1)
                    lab = Text("NCP", font=MONO, font_size=22, color=GRAY,
                               weight="BOLD").move_to(sq)
                    grid.add(VGroup(sq, lab).move_to(
                        RIGHT * (c - 1.5) * 1.55 + UP * (0.75 - r * 1.15)))
            grid.move_to(DOWN * 0.9)
            self.st["grid"] = grid
            t1 = max(0.5, min(1.2, d * 0.35))
            self.play(LaggedStart(*[FadeIn(g, scale=1.1) for g in grid], lag_ratio=0.04),
                      run_time=t1)
            anims = []
            for g in grid:
                new_lab = Text("TCP/IP", font=MONO, font_size=17, color=WHITE,
                               weight="BOLD").move_to(g[0])
                anims.append(g[0].animate.set_fill(BLUE, 1).set_stroke(BLUE, 3))
                anims.append(Transform(g[1], new_lab))
            tag = chip("약 400대 — 하루 만에 전환", BLUE, 26).move_to(DOWN * 3.6)
            self.st["tag400"] = tag
            t2 = max(0.6, min(1.6, (d - t1) * 0.7))
            self.play(LaggedStart(*anims, lag_ratio=0.03), FadeIn(tag), run_time=t2)
            self.hold(d - t1 - t2)

        def a2(d):
            # 실사: 그날의 판도 — 1982.6 BBN ARPANET 지도
            outs = [FadeOut(self.st.pop(k)) for k in ("cal83", "grid", "tag400")
                    if k in self.st]
            t0 = max(0.25, min(0.4, d * 0.12))
            self.play(*outs, run_time=t0)
            ph = self.photo("ep02_arpanet_map_1982.jpg", height=4.6, pos=UP * 0.9)
            cap = chip("ARPANET 지도 1982.6 — BBN", INK, 18).next_to(ph, DOWN, buff=0.25)
            fd = chip("Flag Day — 깃발의 날", AMBER, 30).move_to(UP * 4.1)
            self.show(ph)
            t1 = max(0.3, min(0.6, d * 0.2))
            self.play(FadeIn(cap), FadeIn(fd, scale=1.25), run_time=t1)
            self.hold(d - t0 - t1)

        self.beats(info, [a0, a1, a2])

    # --- 11: 살아남은 자의 배지 (자체 재현 — "재현 이미지" 표기 필수/법무) ---
    def seg011(self, info):
        def a0(d):
            badge = self.photo("ep02_badge_recreation.png", height=4.4, pos=UP * 1.6,
                               framed=False)
            # 법무 조건: 실사 사료로 오인하지 않게 세그 내내 상시 표기
            note = chip("재현 이미지", INK, 22).move_to(RIGHT * 3.1 + UP * 4.1)
            self.st["badge"] = badge
            t1 = max(0.4, min(0.9, d * 0.35))
            self.play(FadeIn(badge, scale=1.08), FadeIn(note), run_time=t1)
            if self.subtitle:
                self.remove(self.subtitle)
                self.add(self.subtitle)
            self.hold(d - t1)

        def a1(d):
            quote = chip("“나는 TCP 전환에서 살아남았다”", RED, 30).move_to(DOWN * 2.2)
            self.act(d, FadeIn(quote, scale=1.15))

        def a2(d):
            who = chip("댄 린치 — 사비로 500개 제작", INK, 26).move_to(DOWN * 3.4)
            self.act(d, FadeIn(who, shift=UP * 0.2))

        self.beats(info, [a0, a1, a2])


class Short02A(Short02Base):
    """반전형(~28초): 유예 없음 → 일제 전환 → 살아남은 자의 배지."""
    SPEC = {"segs": [9, 10, 11],
            "hook": ["인터넷에서 살아남은", "사람들에게만 준 배지"],
            "pops": {9: [None, "차단", "잘린다", None],
                     10: [None, "400대", None],
                     11: [None, None, "실화"]}}


class Short02B(Short02Base):
    """요약형(~40초): 밤샘 전산실 → 3망 불통 → 공통 봉투 → 유예 없음 → 일제 전환."""
    SPEC = {"segs": [0, 2, 5, 9, 10],
            "hook": ["인터넷 전체가 하루 만에", "언어를 갈아탄 날"],
            "pops": {0: [None, "전원 밤샘", "언어 교체"],
                     2: [None, None, "딱 하나", "불통"],
                     5: ["발상의 전환", None, "통한다"],
                     9: [None, "차단", "잘린다", None],
                     10: [None, "400대", None]}}


# ---------- 3편: WWW 탄생 — 'Vague but exciting' — 세로 장면 ----------

class Short03Base(ShortBase):
    """3편 세그 장면(세로 구도·다크). 본편 build_v2.Episode03 연출을 9:16으로 재구성.

    실사 소재(자산 대장 refs/asset-ledger.md 실측 매핑):
      seg0·4·5 = ep03_memo_vague_but_exciting.jpg (제안서 표지+센달 메모, © CERN)
      seg3     = ep03_cern_computing_1980.jpg (CERN 전산센터 1980, © CERN)
      seg11    = ep03_free_release_p1.jpg (1993 공개 성명서 표지, © CERN)
    법무 조건: © CERN 소재는 장면 내 출처 칩 + 엔딩 카드 '사료: © CERN' 병기."""

    def construct(self):
        self.st = {}
        super().construct()

    def end_card(self):
        # 기본 엔딩 + CERN 사료 크레딧 축약 1줄(법무 조건)
        t = ktext("전체 이야기는 채널에서", fs=52).move_to(UP * 0.8)
        btn = chip("구독", RED, 46).move_to(DOWN * 0.6)
        src = Text("사료: © CERN", font=KFONT, font_size=26, color=GRAY).move_to(DOWN * 1.8)
        cc = Text("© nous-zero", font=KFONT, font_size=26, color=GRAY).move_to(DOWN * 2.5)
        self.play(FadeIn(t, shift=UP * 0.2), FadeIn(btn, scale=1.4),
                  FadeIn(src), FadeIn(cc), run_time=0.5)
        self.wait(END_D - 0.5)

    def memo_closeup(self, height=2.4, pos=ORIGIN):
        """메모 손글씨 클로즈업 — 표지 스캔 상단 22%를 잘라 쓴다(렌더 중간산출물)."""
        src = os.path.join(ASSETS, "ep03_memo_vague_but_exciting.jpg")
        dst = os.path.join(OUT, "media_shorts", "ep03_memo_closeup.jpg")
        if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            from PIL import Image
            im = Image.open(src)
            im.crop((0, 0, im.width, int(im.height * 0.22))).save(dst, quality=92)
        img = ImageMobject(dst)
        img.height = height
        if img.width > SAFE_W:
            img.scale_to_fit_width(SAFE_W)
        img.move_to(pos)
        border = Rectangle(width=img.width + 0.1, height=img.height + 0.1)
        border.set_stroke(WHITE, 5).move_to(img)
        return Group(img, border)

    def doc_card_dark(self, pos, w=4.4, h=3.2, nlines=5):
        """회색 글줄 문서 카드(다크) — 하이퍼링크 연출용."""
        win = RoundedRectangle(corner_radius=0.2, width=w, height=h)
        win.set_stroke(GRAY, 3).set_fill("#101A30", 1).move_to(pos)
        lines = VGroup()
        left_x = win.get_left()[0] + 0.45
        top_y = win.get_top()[1] - 0.55
        for i in range(nlines):
            ln_w = w - 0.9 - (0.8 if i % 3 == 2 else 0)
            ln = Line(ORIGIN, RIGHT * ln_w).set_stroke("#4B5563", 5)
            ln.move_to([left_x + ln_w / 2, top_y - i * 0.5, 0])
            lines.add(ln)
        return VGroup(win, lines)

    def bubble(self, lines, pos, color=BLUE, fs=26):
        txts = VGroup(*[Text(l, font=KFONT, font_size=fs, color=WHITE, weight="BOLD")
                        for l in lines])
        txts.arrange(DOWN, buff=0.14, aligned_edge=LEFT)
        box = RoundedRectangle(corner_radius=0.22, width=txts.width + 0.6,
                               height=txts.height + 0.5)
        box.set_stroke(color, 4).set_fill("#101A30", 1)
        txts.move_to(box)
        return SafeGroup(box, txts).move_to(pos)

    # --- 0: 1989 메모 — 낙서 세 단어 (실사: 제안서 표지) ---
    def seg000(self, info):
        def a0(d):
            date = chip("1989 — 스위스 CERN", INK, 28).move_to(UP * 6.3)
            ph = self.photo("ep03_memo_vague_but_exciting.jpg", height=5.2, pos=UP * 1.4)
            cred = chip("메모 원본 — © CERN", INK, 20).next_to(ph, DOWN, buff=0.25)
            self.st["memo"] = ph
            t1 = max(0.3, min(0.5, d * 0.2))
            self.play(FadeIn(date, shift=DOWN * 0.2), run_time=t1)
            self.show(ph)
            self.act(d - t1, FadeIn(cred), rt=0.4)

        def a1(d):
            # 손글씨 위치: 표지 스캔의 가로 52~77%·세로 상단 1~4% (육안 실측)
            ph = self.st["memo"]
            w, h = ph[0].width, ph[0].height
            hl = RoundedRectangle(corner_radius=0.08, width=w * 0.30, height=h * 0.055)
            hl.set_fill(AMBER, 0.4).set_stroke(AMBER, 3)
            hl.move_to(ph[0].get_center() + RIGHT * w * 0.145 + UP * h * 0.472)
            self.act(d, FadeIn(hl, scale=1.3))

        def a2(d):
            words = chip("Vague but exciting", AMBER, 36).move_to(DOWN * 3.2)
            t1 = max(0.3, min(0.7, d * 0.35))
            self.play(FadeIn(words, scale=1.3), run_time=t1)
            t2 = max(0.3, min(0.5, d * 0.2))
            self.play(Flash(words.get_center(), color=AMBER, flash_radius=2.0), run_time=t2)
            self.hold(d - t1 - t2)

        def a3(d):
            stamp = chip("웹의 탄생을 승인한 도장", RED, 30).rotate(0.12)
            stamp.move_to(self.st["memo"][1].get_corner(DR) + UL * 1.2)
            t1 = max(0.3, min(0.7, d * 0.4))
            self.play(FadeIn(stamp, scale=1.6), run_time=t1)
            t2 = max(0.3, min(0.5, d * 0.2))
            self.play(Flash(stamp.get_center(), color=RED, flash_radius=1.6), run_time=t2)
            self.hold(d - t1 - t2)

        self.beats(info, [a0, a1, a2, a3])

    # --- 3: 지식 소실 — 신참·고참 대화 (실사: CERN 전산센터 1980) ---
    def seg003(self, info):
        def a0(d):
            ph = self.photo("ep03_cern_computing_1980.jpg", height=3.0, pos=UP * 3.3)
            cred = chip("CERN 전산센터 1980 — © CERN", INK, 18).next_to(ph, DOWN, buff=0.2)
            who1 = chip("신참", BLUE, 24).move_to(LEFT * 3.4 + UP * 0.9)
            self.st["who1"] = who1
            self.show(ph)
            self.act(d, FadeIn(cred), FadeIn(who1, scale=1.2), rt=0.5)

        def a1(d):
            b1 = self.bubble(["3년 전 그 실험 자료,", "어디서 봅니까?"],
                             RIGHT * 1.0 + UP * 0.4, BLUE)
            self.act(d, FadeIn(b1, shift=UP * 0.2))

        def a2(d):
            who2 = chip("고참", INK, 24).move_to(LEFT * 3.4 + DOWN * 1.0)
            self.act(d, FadeIn(who2, scale=1.2))

        def a3(d):
            b2 = self.bubble(["담당자는 작년에 떠났고,", "자료는 그 사람 컴퓨터에만.",
                              "시스템이 달라 열어도 못 읽어."],
                             RIGHT * 0.6 + DOWN * 1.9, GRAY, 24)
            self.act(d, FadeIn(b2, shift=UP * 0.2))

        def a4(d):
            phrase = ktext("사람이 떠나면, 지식도 떠난다", fs=44, color=RED)
            phrase.move_to(DOWN * 3.5)
            self.act(d, FadeIn(phrase, scale=1.2))

        def a5(d):
            # 각색 고지는 상단으로 — 하단(DOWN*4.3)은 카메라 고정 자막이 최대 줌에서
            # y=-4.29까지 올라와 글자가 겹친다(실측). 이 시점엔 상단 팝이 없어 자리가 빈다.
            note = chip("대화는 각색 — 문제는 실제", GRAY, 22).move_to(UP * 5.6)
            self.act(d, FadeIn(note, shift=UP * 0.15))

        self.beats(info, [a0, a1, a2, a3, a4, a5])

    # --- 4: 1989 제안서 — 팀 버너스리 (실사: 제안서 표지 재사용) ---
    def seg004(self, info):
        def a0(d):
            yr = chip("1989", INK, 28).move_to(UP * 6.3)
            ph = self.photo("ep03_memo_vague_but_exciting.jpg", height=4.6, pos=UP * 1.9)
            cred = chip("제안서 표지 — © CERN", INK, 20).next_to(ph, DOWN, buff=0.25)
            self.st["prop"] = ph
            t1 = max(0.3, min(0.5, d * 0.2))
            self.play(FadeIn(yr, shift=DOWN * 0.2), run_time=t1)
            self.show(ph)
            self.act(d - t1, FadeIn(cred), rt=0.4)

        def a1(d):
            # 인쇄 제목 위치: 세로 상단 21% 지점(육안 실측)
            ph = self.st["prop"]
            w, h = ph[0].width, ph[0].height
            hl = RoundedRectangle(corner_radius=0.08, width=w * 0.62, height=h * 0.05)
            hl.set_fill(AMBER, 0.35).set_stroke(AMBER, 3)
            hl.move_to(ph[0].get_center() + UP * h * 0.285)
            self.act(d, FadeIn(hl, scale=1.2))

        def a2(d):
            t1txt = Text("Information Management:", font=MONO, font_size=34,
                         color=WHITE, weight="BOLD")
            t2txt = Text("A Proposal", font=MONO, font_size=34, color=WHITE, weight="BOLD")
            t3txt = ktext("정보 관리, 하나의 제안", fs=30, color=GRAY)
            title = SafeGroup(t1txt, t2txt, t3txt).arrange(DOWN, buff=0.18).move_to(DOWN * 2.2)
            self.act(d, FadeIn(title, shift=UP * 0.2))

        def a3(d):
            name = chip("팀 버너스리", BLUE, 40).move_to(DOWN * 4.0)
            t1 = max(0.3, min(0.7, d * 0.4))
            self.play(FadeIn(name, scale=1.35), run_time=t1)
            t2 = max(0.3, min(0.5, d * 0.2))
            self.play(Flash(name.get_center(), color=BLUE, flash_radius=1.6), run_time=t2)
            self.hold(d - t1 - t2)

        self.beats(info, [a0, a1, a2, a3])

    # --- 5: 메모 클로즈업 — 실물이 남은 실화 (실사: 표지 상단 크롭) ---
    def seg005(self, info):
        def a0(d):
            boss = chip("상사 마이크 센달", INK, 26).move_to(UP * 6.3)
            cu = self.memo_closeup(height=2.4, pos=UP * 3.3)
            cred = chip("© CERN", INK, 18).next_to(cu, DOWN, buff=0.2)
            self.st["cu"] = cu
            t1 = max(0.3, min(0.5, d * 0.2))
            self.play(FadeIn(boss, shift=DOWN * 0.2), run_time=t1)
            self.show(cu)
            self.act(d - t1, FadeIn(cred), rt=0.4)

        def a1(d):
            # 크롭 내 손글씨: 가로 52~77%·세로 5~18% (원본 실측을 크롭 좌표로 환산)
            cu = self.st["cu"]
            w, h = cu[0].width, cu[0].height
            hl = RoundedRectangle(corner_radius=0.08, width=w * 0.28, height=h * 0.30)
            hl.set_fill(AMBER, 0.35).set_stroke(AMBER, 3)
            hl.move_to(cu[0].get_center() + RIGHT * w * 0.145 + UP * h * 0.385)
            words = chip("Vague but exciting", AMBER, 36).move_to(UP * 0.7)
            t1 = max(0.3, min(0.6, d * 0.3))
            self.play(FadeIn(hl, scale=1.3), run_time=t1)
            t2 = max(0.3, min(0.6, d * 0.3))
            self.play(FadeIn(words, scale=1.3), run_time=t2)
            self.hold(d - t1 - t2)

        def a2(d):
            ok = chip("정식 결재 대신 — 조용히 해볼 시간", BLUE, 28).move_to(DOWN * 1.6)
            self.act(d, FadeIn(ok, shift=UP * 0.2))

        def a3(d):
            real = chip("각색 아님 — 실물이 남은 실화", RED, 32).rotate(0.1)
            real.move_to(DOWN * 3.3)
            t1 = max(0.3, min(0.7, d * 0.4))
            self.play(FadeIn(real, scale=1.5), run_time=t1)
            t2 = max(0.3, min(0.5, d * 0.2))
            self.play(Flash(real.get_center(), color=RED, flash_radius=1.8), run_time=t2)
            self.hold(d - t1 - t2)

        self.beats(info, [a0, a1, a2, a3])

    # --- 6: 하이퍼링크 — 누르면 건너뛴다 (도형) ---
    def seg006(self, info):
        def a0(d):
            head = chip("핵심 아이디어 — 딱 한 줄", INK, 28).move_to(UP * 6.3)
            docA = self.doc_card_dark(UP * 2.8)
            word = RoundedRectangle(corner_radius=0.08, width=1.4, height=0.5)
            word.set_stroke(BLUE, 4).set_fill("#14264a", 1)
            word.move_to(docA[1][2].get_center() + UP * 0.02)
            wul = Line(word.get_corner(DL) + DOWN * 0.07,
                       word.get_corner(DR) + DOWN * 0.07).set_stroke(BLUE, 5)
            self.st["docA"] = docA
            self.st["word"] = VGroup(word, wul)
            self.act(d, FadeIn(head, shift=DOWN * 0.2), Create(docA[0]),
                     LaggedStart(*[Create(l) for l in docA[1]], lag_ratio=0.08),
                     FadeIn(self.st["word"]), rt=min(1.6, d * 0.6))

        def a1(d):
            word = self.st["word"]
            cursor = Triangle().scale(0.18).rotate(-PI / 5)
            cursor.set_fill(WHITE, 1).set_stroke(WHITE, 2)
            cursor.move_to(self.st["docA"][0].get_corner(DR) + UL * 0.5)
            t1 = max(0.3, min(0.5, d * 0.2))
            self.play(FadeIn(cursor, scale=1.3), run_time=t1)
            t2 = max(0.3, min(0.8, d * 0.25))
            self.play(cursor.animate.move_to(word.get_center() + DR * 0.12), run_time=t2)
            t3 = max(0.3, min(0.5, d * 0.15))
            self.play(Flash(word.get_center(), color=BLUE, flash_radius=1.0), run_time=t3)
            docB = self.doc_card_dark(DOWN * 2.4, nlines=4)
            jump = DashedLine(word.get_center() + DOWN * 0.3,
                              docB[0].get_top() + UP * 0.12).set_stroke(BLUE, 6)
            self.st["jump"] = jump
            t4 = max(0.4, min(1.0, d * 0.3))
            self.play(Create(jump), FadeIn(docB, shift=UP * 0.2), run_time=t4)
            self.hold(d - t1 - t2 - t3 - t4)

        def a2(d):
            name = chip("하이퍼링크", BLUE, 48).move_to(UP * 0.2 + LEFT * 1.6)
            t1 = max(0.3, min(0.8, d * 0.4))
            self.play(FadeIn(name, scale=1.4), run_time=t1)
            t2 = max(0.3, min(0.6, d * 0.25))
            self.play(Indicate(self.st["jump"], color=BLUE_L, scale_factor=1.05), run_time=t2)
            self.hold(d - t1 - t2)

        self.beats(info, [a0, a1, a2])

    # --- 11: 1993.4.30 — 웹을 공짜로 풀다 (실사: 공개 성명서) ---
    def seg011(self, info):
        def a0(d):
            date = chip("1993. 4. 30", RED, 32).move_to(UP * 6.3)
            ph = self.photo("ep03_free_release_p1.jpg", height=4.8, pos=UP * 1.6)
            cred = chip("공개 성명서 원본 — © CERN", INK, 20).next_to(ph, DOWN, buff=0.25)
            self.st["free"] = ph
            t1 = max(0.3, min(0.5, d * 0.2))
            self.play(FadeIn(date, shift=DOWN * 0.2), run_time=t1)
            self.show(ph)
            self.act(d - t1, FadeIn(cred), rt=0.4)

        def a1(d):
            # 성명서 제목 블록: 세로 상단 24~27% (육안 실측)
            ph = self.st["free"]
            w, h = ph[0].width, ph[0].height
            hl = RoundedRectangle(corner_radius=0.08, width=w * 0.86, height=h * 0.06)
            hl.set_fill(AMBER, 0.35).set_stroke(AMBER, 3)
            hl.move_to(ph[0].get_center() + UP * h * 0.245)
            tag = chip("특허료 없이, 누구나", BLUE, 32).move_to(DOWN * 2.9)
            t1 = max(0.3, min(0.6, d * 0.3))
            self.play(FadeIn(hl, scale=1.2), run_time=t1)
            t2 = max(0.3, min(0.6, d * 0.3))
            self.play(FadeIn(tag, scale=1.25), run_time=t2)
            self.hold(d - t1 - t2)

        def a2(d):
            stamp = chip("무료 — 영원히", BLUE, 40).rotate(0.2)
            stamp.move_to(self.st["free"][1].get_corner(DR) + UL * 1.2)
            t1 = max(0.3, min(0.7, d * 0.4))
            self.play(FadeIn(stamp, scale=1.7), run_time=t1)
            t2 = max(0.3, min(0.5, d * 0.2))
            self.play(Flash(stamp.get_center(), color=BLUE, flash_radius=1.8), run_time=t2)
            self.hold(d - t1 - t2)

        self.beats(info, [a0, a1, a2])


class Short03A(Short03Base):
    """반전형(~32초): 메모 실물 중심 — 낙서 세 단어가 웹을 승인했다."""
    SPEC = {"segs": [0, 4, 5],
            "hook": ["웹의 탄생 승인 =", "낙서 세 단어"],
            "pops": {0: [None, "세 단어", None, None],
                     4: ["제안서 한 장", None, None, None],
                     5: [None, None, None, "실화"]}}


class Short03B(Short03Base):
    """요약형(~41초): 지식 소실 → 제안서 → 하이퍼링크 → 공짜 개방.

    기획 확정안의 후보(3·4·6~7·11~12) 중 40초 제약(제목 '40초 요약')에 맞춰
    실측 합산으로 3·4·6·11 채택 — 7(3종 세트)·12(오늘의 웹)는 길이 초과로 제외."""
    SPEC = {"segs": [3, 4, 6, 11],
            "hook": ["웹은 원래", "유료가 될 뻔했다"],
            "pops": {3: [None, None, None, "열어도 못 읽어", "지식도 떠난다", None],
                     4: ["제안서 한 장", None, None, None],
                     6: [None, "건너뛰기", None],
                     11: [None, "특허료 없이", "공짜"]}}


# ---------- 4편(Mosaic·Netscape) — 실사 0, 전부 재현·데이터 그래픽 ----------------
EP04_PAPER = "#F6F1E4"    # 본편 seg11 차트·썸네일 인셋과 동일 팔레트(시각 언어 통일)
EP04_GREEN = "#0E7B3D"
EP04_RED_PK = "#B91C1C"
CRT_BG = "#0A0F0C"
CRT_DIM = "#4B5563"
CRT_GREEN = "#22C55E"


class Short04Base(ShortBase):
    """4편 세그 장면(세로 구도·다크). 본편 Episode04 연출을 9:16으로 재구성.

    소재: **실사 0장** — 시세판·메일·브라우저·차트 전부 관용 문법 재현+사실 데이터
    (본편 counsel 판정 §4 승계, 저작권 위험 0). IMG-05 등 CC 사진은 쓰지 않는다
    (총감독 조건: 사용 시 counsel 선행 → 미사용 권장을 채택).
    BGM 은 build() 의 자체 합성(-13dB 언더레이) — 내레이션 동반 필수 조건 충족.

    배치 규율: 4편부터 쇼츠 UI 대역(우측 12%=x>3.42·하단 20%=y<-4.8)이 **차단**이다
    — 본문 요소를 x ±3.3 안에 설계한다(자막은 감사 제외 대상이라 기존 위치 유지).
    법무 표기: 재현 컷마다 표기 칩을 세그 지속 내내 유지(counsel §6-2 — 배속 재수출도
    동일 소재이므로 표기 승계. 쇼츠는 세그당 7.7~12.5초라 3.5초 하한을 크게 상회)."""

    def construct(self):
        self.st = {}
        super().construct()

    def repro_tag(self, txt):
        """법무 표기 칩 — 좌상단 고정(팝 자리 UP*5.0~5.4 와 분리). 세그 내내 유지."""
        return chip(txt, INK, 22, max_w=4.6).move_to(UP * 6.6 + LEFT * 1.8)

    def hook_card(self):
        """4편판 훅 — 기본판(SAFE_W 7.6)은 우측 UI 차단 대역(±3.42, 줌 시 ±3.15)을
        문다(--audit 실측 0.48 침범). 폭 6.0(±3.0)으로 좁혀 재정의 — 기본판은 기존
        편 재렌더 동일성을 위해 불변."""
        lines = self.SPEC["hook"]
        # 1·2행 세로 분리 + 등장 배율 축소 — 감사 검수 A_1.5·B_1.5 실측: 2행이 1.35배
        # 확대 상태로 들어오며 페이드 중 1행과 글자가 포개짐(2행은 줄바꿈돼 키가 커서
        # 확대 시 1행 영역까지 올라온다). 위치 이격 0.7 + 배율 1.15 로 등장 순간에도 분리.
        t1 = ktext(lines[0], fs=62, color=WHITE, max_w=6.0).move_to(UP * 2.3)
        t2 = ktext(lines[1], fs=74, color=AMBER, max_w=6.0).move_to(DOWN * 0.1)
        frame = self.camera.frame
        frame.scale(1.12)
        self.play(FadeIn(t1, scale=1.1), frame.animate.scale(1 / 1.12), run_time=0.4)
        self.play(FadeIn(t2, scale=1.15),
                  Flash(t2.get_center(), color=AMBER, flash_radius=2.2), run_time=0.45)
        self.play(frame.animate.scale(0.97), run_time=max(0.2, HOOK_D - 0.85),
                  rate_func=linear)
        self.play(FadeOut(t1), FadeOut(t2), frame.animate.scale(1 / 0.97), run_time=0.25)

    def end_card(self):
        """4편판 엔딩 — 문구 폭을 ±2.9 로 좁힘(기본판 fs52 는 ±3.43 = 대역 0.28 침범)."""
        t = ktext("전체 이야기는 채널에서", fs=44, color=WHITE, max_w=5.8).move_to(UP * 0.8)
        btn = chip("구독", RED, 46).move_to(DOWN * 0.6)
        cc = Text("© nous-zero", font=KFONT, font_size=26, color=GRAY).move_to(DOWN * 2.0)
        self.play(FadeIn(t, shift=UP * 0.2), FadeIn(btn, scale=1.4), FadeIn(cc),
                  run_time=0.5)
        self.wait(END_D - 0.5)

    def sub(self, txt):
        """4편판 자막 — 기준선을 화면 75% 지점으로 상향(기본판 81.9% ≈ y1573px 는
        쇼츠 하단 제목·채널 오버레이 구역. 감사 검수 A_8·A_18·B_10 실측 y1570~1610
        → 약 133px 상향). 기본판은 기존 편 재렌더 동일성을 위해 불변."""
        t = Text(txt, font=KFONT, font_size=40, color=WHITE, weight="BOLD")
        if t.width > SUB_W - 0.5:
            # 긴 문장은 2줄 분할(감사 재검수 A_18: 한 줄 압축 = 여백 24px·과축소)
            ls = wrap_lines(txt, 2)
            if ls:
                t = VGroup(*[Text(x, font=KFONT, font_size=38, color=WHITE,
                                  weight="BOLD") for x in ls]).arrange(DOWN, buff=0.12)
        if t.width > SUB_W - 1.4:      # 안전여백 6.8월드 = 양측 여백 >=130px(지시 60px+)
            t.scale_to_fit_width(SUB_W - 1.4)
        t.move_to(DOWN * 4.0)
        bg = RoundedRectangle(corner_radius=0.18, width=t.width + 0.5, height=t.height + 0.42)
        bg.set_fill("#000000", 0.55).set_stroke(width=0).move_to(t)
        grp = VGroup(bg, t)
        frame = self.camera.frame
        base_w = grp.width

        def pin(m):
            k = frame.width / config.frame_width
            m.set_width(base_w * k)
            # 상단 고정 앵커(72.5%): 2줄이 되면 아래로 자라 위 요소를 침범하지 않는다
            cx, cy = frame.get_center()[0], frame.get_center()[1]
            top_y = cy - frame.height * 0.225
            m.move_to([cx, top_y - m.height / 2, 0])

        grp.add_updater(pin)
        if self.subtitle:
            self.remove(self.subtitle)
        self.add(grp)
        self.subtitle = grp

    def ticker_panel(self, w=6.0, h=5.0, pos=UP * 1.6):
        """재현 시세판(검은 CRT) — 본편 ticker_panel 의 세로 구도판. 로고 0·가공 티커."""
        panel = RoundedRectangle(corner_radius=0.2, width=w, height=h)
        panel.set_stroke(CRT_DIM, 3).set_fill(CRT_BG, 1).move_to(pos)
        rows_spec = [("VTLK", "12.38", CRT_GREEN), ("DYNC", " 8.10", CRT_DIM),
                     ("NSCP", "--.--", AMBER), ("MERX", "21.05", CRT_GREEN)]
        rows = VGroup()
        nscp = None
        for i, (tk, px, col) in enumerate(rows_spec):
            y = panel.get_top()[1] - 1.1 - i * 0.95
            t_tk = Text(tk, font=MONO, font_size=34, color=col, weight="BOLD")
            t_px = Text(px, font=MONO, font_size=34, color=col, weight="BOLD")
            t_tk.move_to([panel.get_left()[0] + 1.2, y, 0])
            t_px.move_to([panel.get_right()[0] - 1.3, y, 0])
            row = VGroup(t_tk, t_px)
            rows.add(row)
            if tk == "NSCP":
                nscp = row
        band = RoundedRectangle(corner_radius=0.08, width=w - 0.4, height=0.8)
        band.set_fill(AMBER, 0.14).set_stroke(AMBER, 2)
        band.move_to([panel.get_center()[0], nscp.get_center()[1], 0])
        return VGroup(panel, band, rows), nscp

    # --- 0: 훅 상황 — 한 종목이 열리지 않는다 ---
    def seg000(self, info):
        board, nscp = self.ticker_panel()
        cap = self.repro_tag("시세판 (재현 화면)")
        date = chip("1995. 8. 9 — 나스닥", INK, 26, max_w=5.0).move_to(UP * 4.6)
        self.st["nscp"] = nscp

        def a0(d):
            self.play(FadeIn(date, shift=DOWN * 0.2), FadeIn(cap), run_time=0.3)
            self.act(d - 0.3, FadeIn(board, scale=1.05))

        def a1(d):
            delay = chip("첫 거래 — 열리지 않음", RED, 30, max_w=5.4)
            delay.next_to(board, DOWN, buff=0.45)
            t1 = max(0.3, min(0.6, d * 0.3))
            self.play(FadeIn(delay, scale=1.2),
                      Indicate(self.st["nscp"], color=AMBER, scale_factor=1.08),
                      run_time=t1)
            self.act(d - t1, Flash(self.st["nscp"].get_center(), color=AMBER,
                                   flash_radius=1.6))

        def a2(d):
            # DOWN*3.4 는 상향된 자막(상단 -3.55)에 덮인다 — 하단 한계 y-3.4 규칙
            who = chip("창업 16개월 — 아직 적자", INK, 28, max_w=5.6).move_to(DOWN * 2.7)
            self.act(d, FadeIn(who, shift=UP * 0.2))

        self.beats(info, [a0, a1, a2])

    # --- 3: 시급 $6.85 알바생 (대화는 각색) ---
    def seg003(self, info):
        def a0(d):
            place = chip("일리노이대 — NCSA", INK, 26, max_w=5.0).move_to(UP * 4.6)
            self.act(d, FadeIn(place, shift=DOWN * 0.2))

        def a1(d):
            wage = VGroup(Text("$6.85", font=MONO, font_size=96, color=AMBER,
                               weight="BOLD"),
                          ktext("시간당 — 실제 기록", fs=30, color=GRAY, max_w=5.0))
            wage.arrange(DOWN, buff=0.3).move_to(UP * 2.2)
            self.st["wage"] = wage
            self.act(d, FadeIn(wage, scale=1.25))

        def a3(d):
            b1 = chip("연구 문서인데, 글자면 충분하잖아", GRAY, 26, max_w=6.0)
            b1.move_to(DOWN * 0.5 + LEFT * 0.3)
            self.st["b1"] = b1
            self.act(d, FadeIn(b1, shift=UP * 0.15))

        def a4(d):
            b2 = chip("사람들은 그림 없으면 안 봐요", BLUE, 28, max_w=6.0)
            b2.move_to(DOWN * 1.6 + RIGHT * 0.2)
            self.act(d, FadeIn(b2, scale=1.15))

        def a5(d):
            # 각색 고지는 표기 의무 축(counsel §5) — 재검수 B_10: 하단 40% 가림 →
            # 상향 + 축소로 자막 최상단(-3.32, 최대 줌)에서 0.3+ 이격
            note = chip("대화는 각색 — 시급은 실제", GRAY, 22, max_w=5.4)
            note.move_to(DOWN * 2.6)
            self.act(d, FadeIn(note, shift=UP * 0.15))

        self.beats(info, [a0, a1, None, a3, a4, a5, None])

    # --- 4: 1993-02-25 IMG 태그 제안 메일 (재현) ---
    def seg004(self, info):
        mail = RoundedRectangle(corner_radius=0.2, width=6.0, height=4.4)
        mail.set_stroke(WHITE, 4).set_fill("#F9FAFB", 1).move_to(UP * 1.6)
        cap = self.repro_tag("제안 메일 (재현 화면)")

        def a0(d):
            date = chip("1993. 2. 25 — 공개 게시판", INK, 24, max_w=5.6).move_to(UP * 4.6)
            subject = Text("proposed new tag:", font=MONO, font_size=30,
                           color=INK, weight="BOLD")
            subject.move_to(mail.get_top() + DOWN * 0.8)
            self.st["mail"] = mail
            t1 = max(0.3, min(0.7, d * 0.35))
            self.play(FadeIn(date, shift=DOWN * 0.2), FadeIn(cap), run_time=0.3)
            self.play(FadeIn(mail), FadeIn(subject), run_time=t1)
            self.hold(d - t1 - 0.3)

        def a1(d):
            body = Text('<IMG SRC="...">', font=MONO, font_size=40,
                        color="#B45309", weight="BOLD")
            body.move_to(self.st["mail"].get_center() + DOWN * 0.4)
            self.st["body"] = body
            t1 = max(0.3, min(0.7, d * 0.4))
            self.play(FadeIn(body, scale=1.3), run_time=t1)
            self.act(d - t1, Flash(body.get_center(), color=AMBER, flash_radius=1.8))

        def a2(d):
            what = chip("그림을 문서 안에 박는 명령", BLUE, 26, max_w=6.0)
            what.move_to(DOWN * 2.0)
            self.act(d, FadeIn(what, shift=UP * 0.15))

        self.beats(info, [a0, a1, a2, None])

    # --- 5: 1993-04-22 모자이크 공개 (재현 브라우저) ---
    def seg005(self, info):
        win = RoundedRectangle(corner_radius=0.2, width=6.0, height=5.6)
        win.set_stroke(WHITE, 4).set_fill("#EDEDED", 1).move_to(UP * 1.2)
        cap = self.repro_tag("모자이크 (재현 화면)")

        def a0(d):
            date = chip("1993. 4. 22 — 정식 공개", RED, 24, max_w=5.6).move_to(UP * 4.7)
            bar = Rectangle(width=6.0, height=0.5).set_stroke(width=0)
            bar.set_fill("#D1D5DB", 1).move_to(win.get_top() + DOWN * 0.25)
            lines = VGroup()
            for i, wf in enumerate((0.85, 0.7, 0.8, 0.55)):
                ln = Line(ORIGIN, RIGHT * 4.6 * wf).set_stroke("#9CA3AF", 6)
                ln.move_to(win.get_corner(UL) + RIGHT * (0.7 + 4.6 * wf / 2)
                           + DOWN * (1.0 + i * 0.5))
                lines.add(ln)
            self.st["win"] = win
            t1 = max(0.3, min(0.8, d * 0.4))
            self.play(FadeIn(date, shift=DOWN * 0.2), FadeIn(cap), run_time=0.3)
            self.play(FadeIn(win), FadeIn(bar),
                      LaggedStart(*[Create(l) for l in lines], lag_ratio=0.15),
                      run_time=t1)
            self.hold(d - t1 - 0.3)

        def a1(d):
            img = RoundedRectangle(corner_radius=0.1, width=3.2, height=2.2)
            img.set_stroke(BLUE, 4).set_fill("#DBEAFE", 1)
            img.move_to(self.st["win"].get_center() + DOWN * 1.0)
            mount = Triangle().scale(0.4).set_stroke(BLUE, 3).set_fill(BLUE, 0.5)
            mount.move_to(img.get_center() + DOWN * 0.2)
            t1 = max(0.3, min(0.8, d * 0.4))
            self.play(FadeIn(VGroup(img, mount), scale=1.35), run_time=t1)
            self.act(d - t1, Flash(img.get_center(), color=BLUE, flash_radius=2.0))

        def a2(d):
            ez = chip("설치 — 몇 번 클릭이면 끝", EP04_GREEN, 26, max_w=5.8)
            ez.move_to(DOWN * 2.6)
            self.act(d, FadeIn(ez, shift=UP * 0.15))

        self.beats(info, [a0, a1, a2])

    # --- 10: 상장일 — 공모가 28, 주문 폭주 ---
    def seg010(self, info):
        cap = self.repro_tag("시세판 (재현 화면)")

        def a0(d):
            # 세로 배치 계획(감사 검수 A_18 칩 3개 충돌의 수리 — 층을 분리):
            #   date 4.35 / ipo 3.0 / delay 1.6 / 라벨 0.45 / 막대 -0.26~-2.9 / band -3.8
            date = chip("1995. 8. 9 — 상장", RED, 26, max_w=5.0).move_to(UP * 4.35)
            ipo = VGroup(ktext("공모가", fs=30, color=GRAY, max_w=3.0),
                         Text("$28.00", font=MONO, font_size=80, color=WHITE,
                              weight="BOLD"))
            ipo.arrange(DOWN, buff=0.25).move_to(UP * 3.0)
            self.st["ipo"] = ipo
            self.play(FadeIn(date, shift=DOWN * 0.2), FadeIn(cap), run_time=0.3)
            self.act(d - 0.3, FadeIn(ipo, scale=1.2))

        def a1(d):
            buys = VGroup()
            for i in range(7):
                b = Rectangle(width=2.4, height=0.36).set_stroke(width=0)
                b.set_fill(AMBER, 0.9)
                b.move_to(LEFT * 1.7 + DOWN * (2.9 - i * 0.44))
                buys.add(b)
            sell = Rectangle(width=2.4, height=0.36).set_stroke(width=0)
            sell.set_fill("#6B7280", 0.9).move_to(RIGHT * 1.7 + DOWN * 2.9)
            b_lb = chip("사자", AMBER, 24, max_w=2.0).move_to(LEFT * 1.7 + UP * 0.45)
            s_lb = chip("팔자", GRAY, 24, max_w=2.0).move_to(RIGHT * 1.7 + UP * 0.45)
            self.act(d, FadeIn(b_lb), FadeIn(s_lb), FadeIn(sell),
                     LaggedStart(*[FadeIn(b, shift=UP * 0.2) for b in buys],
                                 lag_ratio=0.12), rt=min(1.6, d * 0.6))

        def a2(d):
            # DOWN*3.8 은 상향된 자막에 반쯤 덮였다(A_18 재검 실측) → 팔자 열의 빈
            # 공간(우측, 매도 없음의 시각 강조와도 결)로 이동. 최대 줌 대역(3.15) 안.
            band = RoundedRectangle(corner_radius=0.12, width=3.6, height=0.8)
            band.set_stroke(CRT_DIM, 3).set_fill(CRT_BG, 1).move_to(RIGHT * 1.0 + DOWN * 2.1)
            nscp = Text("NSCP  --.--", font=MONO, font_size=26, color=AMBER,
                        weight="BOLD").move_to(band)
            # 라벨(0.45)과 공모가(3.0) 사이 빈 층(1.6) — 칩끼리 겹치지 않는다
            delay = chip("약 2시간 지연", RED, 28, max_w=4.0).move_to(UP * 1.6)
            t1 = max(0.3, min(0.7, d * 0.4))
            self.play(FadeIn(band), FadeIn(nscp), run_time=t1)
            self.act(d - t1, FadeIn(delay, scale=1.25),
                     Indicate(self.st["ipo"], color=AMBER, scale_factor=1.05))

        self.beats(info, [a0, a1, a2, None])

    # --- 11: 클라이맥스 — 주가 재현 차트 28→71→74.75→58.25 ---
    def seg011(self, info):
        card = RoundedRectangle(corner_radius=0.2, width=6.0, height=6.2)
        card.set_stroke(WHITE, 4).set_fill(EP04_PAPER, 1).move_to(UP * 1.0)
        base_y, scale = card.get_bottom()[1] + 0.7, 0.082
        py = lambda p: base_y + (p - 20) * scale  # noqa: E731
        # close 2.4→2.2: $58.25 라벨이 카드 우측 경계를 넘어 우측 UI 대역(x986px)에
        # 걸렸다(감사 검수 A_28 실측 — 내 대역 검사는 감사 시점의 줌이 바닥까지 안 가
        # 경계 0.0~0.05 차로 못 잡은 한계. 라벨을 안쪽으로 넣어 원인 제거).
        xs = {"open": -2.4, "first": -0.9, "peak": 0.7, "close": 2.2}
        cap = self.repro_tag("주가 (데이터 재구성)")

        def a0(d):
            ip_line = DashedLine([xs["open"], py(28), 0], [xs["close"] + 0.2, py(28), 0])
            ip_line.set_stroke("#6B7280", 3)
            ip_lb = Text("$28", font=MONO, font_size=30, color="#6B7280", weight="BOLD")
            ip_lb.next_to(ip_line.get_start(), UP, buff=0.12).shift(RIGHT * 0.25)
            jump = Line([xs["first"], py(28), 0], [xs["first"], py(71), 0])
            jump.set_stroke(EP04_GREEN, 7)
            dot71 = Dot([xs["first"], py(71), 0], radius=0.12, color=EP04_GREEN)
            lb71 = Text("$71", font=MONO, font_size=40, color=EP04_GREEN,
                        weight="BOLD").next_to(dot71, UL, buff=0.12)
            self.st["p71"] = [xs["first"], py(71), 0]
            t1 = max(0.3, min(0.7, d * 0.3))
            self.play(FadeIn(cap), FadeIn(card), run_time=t1)
            t2 = max(0.3, min(0.6, d * 0.25))
            self.play(Create(ip_line), FadeIn(ip_lb), run_time=t2)
            self.act(d - t1 - t2, Create(jump), FadeIn(dot71, scale=1.4), FadeIn(lb71))

        def a1(d):
            rise = Line(self.st["p71"], [xs["peak"], py(74.75), 0])
            rise.set_stroke(EP04_GREEN, 7)
            dot_pk = Dot([xs["peak"], py(74.75), 0], radius=0.13, color=EP04_RED_PK)
            lb_pk = Text("$74.75", font=MONO, font_size=34, color=EP04_RED_PK,
                         weight="BOLD").next_to(dot_pk, UP, buff=0.14)
            fall = Line([xs["peak"], py(74.75), 0], [xs["close"], py(58.25), 0])
            fall.set_stroke("#6B7280", 7)
            dot_cl = Dot([xs["close"], py(58.25), 0], radius=0.12, color=INK)
            lb_cl = Text("$58.25", font=MONO, font_size=30, color=INK,
                         weight="BOLD").next_to(dot_cl, DOWN, buff=0.14)
            lb_cl.shift(LEFT * 0.55)   # 라벨 우단을 카드 안쪽으로(A_28 수리)
            t1 = max(0.3, min(0.8, d * 0.35))
            self.play(Create(rise), FadeIn(dot_pk, scale=1.4), FadeIn(lb_pk), run_time=t1)
            t2 = min(0.5, max(0.3, d * 0.15))
            self.play(Flash(dot_pk.get_center(), color=EP04_RED_PK, flash_radius=1.6),
                      run_time=t2)
            self.act(d - t1 - t2, Create(fall), FadeIn(dot_cl), FadeIn(lb_cl))

        def a2(d):
            worth = chip("몸값 — 하루 만에 약 $30억", AMBER, 28, max_w=6.0)
            worth.move_to(DOWN * 3.0)   # 자막 상향 회귀 예방(하단 한계 y-3.4)
            self.act(d, FadeIn(worth, scale=1.2))

        self.beats(info, [a0, a1, a2])


class Short04A(Short04Base):
    """반전형(~35초): 적자 회사 상장날 — 주문 폭주·2시간 지연·주가 3배."""
    SPEC = {"segs": [0, 10, 11],
            "hook": ["$28 → $71", "적자 회사의 상장날"],
            "pops": {0: [None, "주문 폭주", None],
                     10: [None, None, "2시간 지연", None],
                     11: [None, None, "$30억"]}}


class Short04B(Short04Base):
    """요약형(~46초): 시급 $6.85 알바생 → IMG 태그 → 모자이크 → 상장."""
    SPEC = {"segs": [3, 4, 5, 11],
            "hook": ["시급 $6.85 알바생이", "웹에 그림을 넣었다"],
            "pops": {3: [None, "$6.85", None, None, None, None, None],
                     4: [None, "IMG", None, None],
                     5: [None, "모자이크", None],
                     11: ["$71", None, "$30억"]}}


def video_seconds(path):
    """mp4 재생 길이(초) 실측 — ffmpeg 표준출력 파싱(추정 금지, rule6)."""
    import imageio_ffmpeg
    out = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", path],
                         capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stderr
    for line in out.split("\n"):
        if "Duration:" in line:
            h, m, s = line.split("Duration:")[1].split(",")[0].strip().split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError("영상 길이 판독 실패: " + path)


def build(short_cls, name):
    config.output_file = f"{name}_silent"
    scene = short_cls()
    scene.render()
    import glob
    silent = max(glob.glob(os.path.join(OUT, "media_shorts", "**", f"{name}_silent.mp4"),
                           recursive=True), key=os.path.getmtime)
    from pydub import AudioSegment
    track = AudioSegment.silent(duration=int(HOOK_D * 1000))
    segs = short_cls.SPEC["segs"]
    for k, i in enumerate(segs):
        track += AudioSegment.from_wav(seg_info(i)["wav"])  # 배속본 사용(화면 타이밍과 동일 소스)
        track += AudioSegment.silent(duration=int((GAP if k < len(segs) - 1 else 0.3) * 1000))
    track += AudioSegment.silent(duration=int(END_D * 1000))
    # --- 불변식: 오디오 길이 >= 무음영상 길이 ---
    # ffmpeg -shortest 는 둘 중 짧은 쪽에 맞춰 자른다. 장면이 프레임 양자화·hold 오차로
    # 계획보다 길어지면 오디오가 더 짧아져 '엔딩 카드'가 통째로 잘려나간다.
    # (2026-07-29 3편 실사고: 무음영상 42.73s vs 오디오 41.52s → 엔딩 '사료: © CERN' 카드
    #  1.6s 중 0.4s만 남아 사실상 안 보임. rule5 §4 — 같은 부류 재발 방지로 기계 검사 승격.)
    vsec = video_seconds(silent)
    if vsec + 0.2 > len(track) / 1000.0:
        track += AudioSegment.silent(duration=int((vsec + 0.2 - len(track) / 1000.0) * 1000))
    assert len(track) / 1000.0 >= vsec, f"{name}: 오디오({len(track)/1000:.2f}s) < 영상({vsec:.2f}s)"
    out_name = f"{name}{NAME_SUFFIX}"
    bgm_path = os.path.join(OUT, f"{out_name}_bgm.wav")
    make_bgm(len(track) / 1000 + 0.5, bgm_path)
    bgm = AudioSegment.from_wav(bgm_path).apply_gain(-13)
    track = bgm[:len(track)].overlay(track)  # 비트 위에 육성
    apath = os.path.join(OUT, f"{out_name}_audio.wav")
    track.export(apath, format="wav")
    import imageio_ffmpeg
    final = os.path.join(OUT, f"{out_name}.mp4")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", silent, "-i", apath,
                    "-c:v", "libx264", "-crf", "23", "-preset", "medium",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", final],
                   check=True, capture_output=True)
    # [P2] '완성'은 --full 에서만. 시안은 해상도를 문구에 함께 표기한다.
    tag = (f"완성({config.pixel_width}x{config.pixel_height} {config.frame_rate}fps)" if FULL
           else f"시안({config.pixel_width}x{config.pixel_height} {config.frame_rate}fps) — 최종본 아님")
    print(f"[shorts] {name} {tag}: {final} ({len(track) / 1000:.0f}초 오디오)")


SHORTS = {"01": ((ShortA, "shorts_A"), (ShortB, "shorts_B")),
          "02": ((Short02A, "shorts_A"), (Short02B, "shorts_B")),
          "03": ((Short03A, "shorts_A"), (Short03B, "shorts_B")),
          "04": ((Short04A, "shorts_A"), (Short04B, "shorts_B"))}

if __name__ == "__main__":
    if EP not in SHORTS:
        print(f"[shorts] 오류: {EP}편 쇼츠 SPEC 없음 (지원: {', '.join(SHORTS)})")
        sys.exit(1)
    if AUDIT:
        # 세이프 영역 감사 — 90x160·4fps 초소형 렌더로 전 장면을 실제로 돌려
        # '지금 보이는 프레임을 벗어난 요소'를 전수 측정한다(오디오 조립·인코딩 생략).
        for cls, name in SHORTS[EP]:
            config.output_file = f"{name}_audit"
            cls().render()
        sys.exit(0)
    for cls, name in SHORTS[EP]:
        build(cls, name)
    # [P1 연결] 완성 렌더 직후 산출물 스펙 실측 판정(해상도·길이·라우드니스·BGM·
    # 프레임 이탈). '렌더 완료'는 '규격 통과'가 아니다(rule4).
    # 시안은 540x960 이라 미달이 당연하므로 --full 에서만 건다(경보 피로 방지).
    if FULL:
        spec = os.path.join(ROOT, "video", "verify_output_spec.py")
        if not os.path.exists(spec):
            print("[shorts] 경고: verify_output_spec.py 없음 — 스펙 검사 생략(미확인)")
        else:
            print("\n[shorts] 산출물 스펙 실측 검사 ...")
            rc = subprocess.run([sys.executable, spec, EP, "--shorts"]).returncode
            if rc == 0:
                print("[shorts] 스펙 검사 통과.")
            else:
                print(f"[shorts] *** 스펙 검사 미달(종료코드 {rc}) — "
                      f"위 [spec] 미달 항목을 고치기 전에는 발행 금지 ***")
