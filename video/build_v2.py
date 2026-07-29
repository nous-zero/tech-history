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
  python video/build_v2.py 01           # 시안(480p15, 빠름)
  python video/build_v2.py 01 --full    # 완성(1080p30)
  python video/build_v2.py 01 --full --sub  # 자막을 영상에 구움(자막 기능 없는 플랫폼용)

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
        self.intro()
        for k, seg in enumerate(TIMED):
            getattr(self, f"seg{k:02d}")(seg["sents"])
            if self.subtitle:
                self.remove(self.subtitle)
                self.subtitle = None
            if k in self.CLEAR_AFTER:
                self.clear_stage(GAP)
            else:
                self.wait(GAP)
        self.wait(1.2)

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
        """흰 테두리 액자에 담긴 실사 사진. Group 반환(사진, [테두리])."""
        img = ImageMobject(os.path.join(ASSETS, fname))
        img.height = height
        img.move_to(pos)
        if framed:
            border = Rectangle(width=img.width + 0.1, height=img.height + 0.1)
            border.set_stroke(INK, 4).set_fill(None, 0).move_to(img)  # 흰 배경에서도 보이는 잉크색 액자
            return Group(img, border)
        return Group(img)

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

    # --- 인트로 ---
    def intro(self):
        title = mtext("ARPANET", fs=110, color=INK).move_to(UP * 0.9)
        sub = ktext("핵전쟁이 만든 인터넷의 시작", fs=40, color=GRAY).next_to(title, DOWN, buff=0.5)
        num = chip("#01", BLUE, 30).to_corner(UL, buff=0.6)
        cc = Text("© nous-zero", font=KFONT, font_size=22, color=LGRAY).to_corner(DR, buff=0.45)
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
            frames = [ImageMobject(os.path.join(ASSETS, f"tonga_f{i}.png")) for i in range(9)]
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
            tag = chip("NCP → TCP/IP", INK, 30).move_to(RIGHT * 2.8 + UP * 1.3)
            sub2 = ktext("하루 만에 언어를 갈아탄 날", 30, GRAY).next_to(tag, DOWN, buff=0.4)
            self.act(d, FadeIn(tag, scale=1.2), FadeIn(sub2, shift=UP * 0.15))

        def a2(d):
            btn_box = RoundedRectangle(corner_radius=0.3, width=2.6, height=0.85)
            btn_box.set_stroke(width=0).set_fill(RED, 1)
            btn_t = ktext("구독", 40, WHITE, bold=True).move_to(btn_box)
            btn = VGroup(btn_box, btn_t).move_to(RIGHT * 2.8 + DOWN * 0.9)
            cc = Text("© nous-zero", font=KFONT, font_size=22, color=LGRAY)
            cc.to_corner(DR, buff=0.4).shift(UP * 0.55)
            t1 = max(0.4, min(0.9, d * 0.35))
            self.play(FadeIn(btn, scale=1.5), run_time=t1)
            t2 = max(0.3, min(0.5, d * 0.2))
            self.play(Indicate(btn, color=RED, scale_factor=1.12), FadeIn(cc), run_time=t2)
            self.hold(d - t1 - t2)

        self.run_beats(S, [a0, a1, a2])


class Episode02(EpisodeBase):
    """2편: TCP/IP Flag Day — 1983.1.1 언어 대전환. 하이브리드 v3(사건=실사 켄 번즈, 원리=도형).

    실사 5장면: calendar_night(NORAD 전산실) · three_nets(골드스톤/SRI 밴/IMP 3분할)
    · cerf_kahn(초상 2 + 훈장 보조) · flagday(BBN 1982 지도 줌) · badge(자체 재현 — 표기 필수).
    원리 장면(envelope, ip_tcp_roles, ncp_problem, ipv6_twist 등)은 도형 유지."""
    CLEAR_AFTER = {0, 1, 5, 6, 7, 10, 11, 12, 13}

    def intro(self):
        title = mtext("TCP/IP", fs=110, color=INK).move_to(UP * 0.9)
        sub = ktext("인터넷 전체가 하루 만에 언어를 갈아탄 날", fs=40, color=GRAY).next_to(title, DOWN, buff=0.5)
        num = chip("#02", BLUE, 30).to_corner(UL, buff=0.6)
        cc = Text("© nous-zero", font=KFONT, font_size=22, color=LGRAY).to_corner(DR, buff=0.45)
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
            note = chip("재현 이미지", GRAY, 20).move_to(RIGHT * 3.7 + UP * 2.7)
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
            tag = chip("#03 — 웹(Web)의 탄생", INK, 30).move_to(DOWN * 0.85 + LEFT * 2.9)
            teaser = ktext("도로는 깔렸는데, 실어 나를 짐이 없었다", 27, GRAY)
            teaser.next_to(tag, DOWN, buff=0.3)
            self.act(d, FadeIn(tag, scale=1.15), FadeIn(teaser, shift=UP * 0.15))

        def a3(d):
            btn_box = RoundedRectangle(corner_radius=0.3, width=2.6, height=0.85)
            btn_box.set_stroke(width=0).set_fill(RED, 1)
            btn_t = ktext("구독", 40, WHITE, bold=True).move_to(btn_box)
            sub_btn = VGroup(btn_box, btn_t).move_to(RIGHT * 3.1 + DOWN * 0.9)
            like_box = RoundedRectangle(corner_radius=0.3, width=2.6, height=0.85)
            like_box.set_stroke(BLUE, 4).set_fill(WHITE, 1)
            like_t = ktext("좋아요", 34, BLUE, bold=True).move_to(like_box)
            like_btn = VGroup(like_box, like_t).next_to(sub_btn, DOWN, buff=0.3)
            cc = Text("© nous-zero", font=KFONT, font_size=22, color=LGRAY)
            cc.to_corner(DR, buff=0.4)
            t1 = max(0.4, min(0.9, d * 0.35))
            self.play(FadeIn(sub_btn, scale=1.5), FadeIn(like_btn, scale=1.3),
                      run_time=t1)
            t2 = max(0.3, min(0.5, d * 0.2))
            self.play(Indicate(sub_btn, color=RED, scale_factor=1.12), FadeIn(cc),
                      run_time=t2)
            self.hold(d - t1 - t2)

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

    def intro(self):
        title = mtext("WWW", fs=110, color=INK).move_to(UP * 0.9)
        sub = ktext("모호하지만 흥미로움 — 웹의 탄생", fs=40, color=GRAY).next_to(title, DOWN, buff=0.5)
        num = chip("#03", BLUE, 30).to_corner(UL, buff=0.6)
        cc = Text("© nous-zero", font=KFONT, font_size=22, color=LGRAY).to_corner(DR, buff=0.45)
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
            cap = chip("최초의 웹사이트 — '웹이란 무엇인가' 안내문 (재현 화면)", GRAY, 20)
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
            ph, _ = self.ep_photo("next", height=2.6, pos=LEFT * 3.9 + DOWN * 1.6)
            tag = chip("#04 — 모자이크 & 넷스케이프", INK, 28)
            tag.move_to(RIGHT * 1.6 + DOWN * 1.1)
            teaser = ktext("밋밋한 웹에 처음 그림을 띄운, 대학 시급 알바생", 24, GRAY)
            teaser.next_to(tag, DOWN, buff=0.28)
            t1 = max(0.3, min(0.7, d * 0.3))
            self.show_photo(ph, t1)
            t2 = max(0.3, min(0.8, d * 0.3))
            self.play(FadeIn(tag, scale=1.15), FadeIn(teaser, shift=UP * 0.15), run_time=t2)
            self.hold(d - t1 - t2)

        def a3(d):
            btn_box = RoundedRectangle(corner_radius=0.3, width=2.3, height=0.8)
            btn_box.set_stroke(width=0).set_fill(RED, 1)
            btn_t = ktext("구독", 36, WHITE, bold=True).move_to(btn_box)
            sub_btn = VGroup(btn_box, btn_t).move_to(RIGHT * 5.2 + DOWN * 2.6)
            like_box = RoundedRectangle(corner_radius=0.3, width=2.3, height=0.8)
            like_box.set_stroke(BLUE, 4).set_fill(WHITE, 1)
            like_t = ktext("좋아요", 30, BLUE, bold=True).move_to(like_box)
            like_btn = VGroup(like_box, like_t).next_to(sub_btn, DOWN, buff=0.25)
            cc = Text("© nous-zero", font=KFONT, font_size=22, color=LGRAY)
            cc.to_corner(DL, buff=0.4)
            t1 = max(0.4, min(0.9, d * 0.35))
            self.play(FadeIn(sub_btn, scale=1.5), FadeIn(like_btn, scale=1.3),
                      run_time=t1)
            t2 = max(0.3, min(0.5, d * 0.2))
            self.play(Indicate(sub_btn, color=RED, scale_factor=1.12), FadeIn(cc),
                      run_time=t2)
            self.hold(d - t1 - t2)

        self.run_beats(S, [a0, a1, a2, a3])


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


def main():
    print(f"[v2] {EP}편 | 음성: {'있음 — 소리 합성' if HAVE_AUDIO else '없음 — 무음'} | "
          f"{'완성 렌더' if FULL else '시안 렌더(최종본 아님)'} {VW}x{VH} {VFPS}fps")
    if AUDIO_SUB != "audio":
        print(f"[v2] 주의: 음성 스냅샷 '{AUDIO_SUB}' 타이밍 기준 시안 — 최종본 아님"
              f" (최종은 audio/ 확정 후 재렌더)")
    total = INTRO_D + sum(s["total"] + GAP for s in TIMED) + 1.2
    print(f"[v2] 예상 길이: {total:.0f}초 ({total / 60:.1f}분)")

    episodes = {"01": Episode01, "02": Episode02, "03": Episode03}
    if EP not in episodes:
        print(f"[v2] 오류: {EP}편 장면 클래스가 없음 (지원: {', '.join(episodes)})")
        sys.exit(1)
    scene = episodes[EP]()
    scene.render()

    hits = glob.glob(os.path.join(OUT, "media", "**", "ep_silent.mp4"), recursive=True)
    if not hits:
        print("[v2] 오류: 렌더 결과 mp4를 찾지 못함")
        sys.exit(1)
    silent = max(hits, key=os.path.getmtime)
    srt = build_srt()

    if HAVE_AUDIO:
        import imageio_ffmpeg
        audio = build_audio()
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


if __name__ == "__main__":
    main()
