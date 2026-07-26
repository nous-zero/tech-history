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
AUDIO_DIR = os.path.join(OUT, "audio")
os.makedirs(OUT, exist_ok=True)

GAP = 0.35          # 세그먼트 사이 쉼(초) — 음성에도 같은 길이 무음 삽입
INTRO_D = 2.8       # 인트로 카드 길이
SEC_PER_CHAR = 0.155  # 음성 없을 때 길이 추정(한국어 낭독 대략치)

INK = "#1F2937"
GRAY = "#6B7280"
LGRAY = "#9CA3AF"
BLUE = "#2563EB"
RED = "#DC2626"
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
    config, Scene, VGroup, VMobject, Text, Dot, Circle, Line, DashedLine,
    Rectangle, RoundedRectangle, RegularPolygon, Triangle, Arrow, Underline,
    SurroundingRectangle, DashedVMobject, ArcBetweenPoints,
    Create, FadeIn, FadeOut, Transform, ReplacementTransform, Indicate, Wiggle,
    Flash, MoveAlongPath, LaggedStart, GrowFromCenter,
    UP, DOWN, LEFT, RIGHT, ORIGIN, UL, UR, DL, DR, WHITE, PI,
)

config.background_color = WHITE
if FULL:
    config.pixel_width, config.pixel_height, config.frame_rate = 1920, 1080, 30
else:
    config.pixel_width, config.pixel_height, config.frame_rate = 854, 480, 15
config.media_dir = os.path.join(OUT, "media")
config.output_file = "ep_silent"
config.disable_caching = True

CLEAR_AFTER = {2, 3, 5, 6, 7, 8, 9, 11, 12, 13}

MESH_P = [(-4.5, 1.6), (-2.2, 2.2), (0.2, 1.9), (2.6, 2.1), (4.6, 1.5),
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


class Episode(Scene):
    def construct(self):
        self.subtitle = None
        self.st = {}
        self.intro()
        for k, seg in enumerate(TIMED):
            getattr(self, f"seg{k:02d}")(seg["sents"])
            if self.subtitle:
                self.remove(self.subtitle)
                self.subtitle = None
            if k in CLEAR_AFTER:
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

    def run_beats(self, S, acts):
        for i, (txt, d) in enumerate(S):
            self.sub(txt)
            if i < len(acts) and acts[i]:
                acts[i](d)
            else:
                self.hold(d)

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
            boxes = self.st["login"]
            hl = SurroundingRectangle(VGroup(boxes[0], boxes[1]),
                                      color=BLUE, corner_radius=0.15, buff=0.18)
            hl.set_stroke(BLUE, 6)
            self.st["hl"] = hl
            self.act(d, Create(hl))

        def a2(d):
            self.act(d, Indicate(VGroup(self.st["login"][0], self.st["login"][1]),
                                 color=BLUE, scale_factor=1.15))

        self.run_beats(S, [a0, a1, a2])

    # --- 3: 냉전 ---
    def seg03(self, S):
        def a0(d):
            why = ktext("왜?", fs=96, color=INK, bold=True)
            self.st["why"] = why
            self.act(d, FadeIn(why, scale=1.5))

        def a1(d):
            pent = RegularPolygon(n=5).scale(1.5).set_stroke(BLUE, 5).set_fill("#DBEAFE", 0.6)
            pent.move_to(DOWN * 0.2)
            lab = ktext("미 국방부", 28, GRAY).next_to(pent, DOWN, buff=0.3)
            cold = chip("냉전 시대", INK, 30).to_corner(UL, buff=0.5)
            m = missile(1.2).move_to(UP * 2.6 + RIGHT * 3.4)
            t1 = max(0.4, min(1.2, d * 0.45))
            self.play(FadeOut(self.st.pop("why")), Create(pent), FadeIn(lab), FadeIn(cold), run_time=t1)
            arc = ArcBetweenPoints(m.get_center(), pent.get_top() + UP * 0.7 + RIGHT * 0.4, angle=-PI / 5)
            t2 = max(0.4, min(1.2, d * 0.3))
            self.play(MoveAlongPath(m, arc), run_time=t2)
            self.hold(d - t1 - t2)

        self.run_beats(S, [a0, a1])

    # --- 4~5: 별 모양 → 붕괴 ---
    def seg04(self, S):
        def a0(d):
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
            self.act(d, Create(center), FadeIn(clab),
                     LaggedStart(*[Create(s) for s in spokes], lag_ratio=0.08),
                     LaggedStart(*[FadeIn(o) for o in outer], lag_ratio=0.08),
                     rt=min(2.0, d * 0.7))

        def a1(d):
            m = missile(1.2).move_to(UP * 3.4 + RIGHT * 0.2)
            self.st["missile"] = m
            self.act(d, FadeIn(m, shift=DOWN * 0.4))

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
            body = RoundedRectangle(corner_radius=0.18, width=2.0, height=3.4)
            body.set_stroke(INK, 5).set_fill("#F3F4F6", 1).move_to(LEFT * 3.0 + UP * 0.3)
            lab = mtext("IMP", fs=44, color=INK).move_to(body.get_top() + DOWN * 0.55)
            vents = VGroup(*[Line(LEFT * 0.55, RIGHT * 0.55).set_stroke(LGRAY, 3)
                             .move_to(body.get_center() + DOWN * (0.3 + 0.3 * i))
                             for i in range(3)])
            self.st["imp"] = VGroup(body, lab, vents)
            self.act(d, FadeIn(self.st["imp"], scale=1.15))

        def a1(d):
            size = chip("냉장고 크기", INK, 26).next_to(self.st["imp"], DOWN, buff=0.35)
            self.st["impsize"] = size
            self.act(d, FadeIn(size), Indicate(self.st["imp"], color=BLUE, scale_factor=1.04))

        def a2(d):
            arrow = Arrow(LEFT * 1.6 + UP * 0.3, RIGHT * 0.6 + UP * 0.3, color=GRAY, stroke_width=6)
            box = RoundedRectangle(corner_radius=0.12, width=1.8, height=0.55)
            box.set_stroke(BLUE, 5).set_fill("#DBEAFE", 1).move_to(RIGHT * 2.6 + UP * 0.1)
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
            island = Circle(radius=0.55).set_stroke(INK, 5).set_fill(WHITE, 1)
            island.move_to(RIGHT * 4.6 + UP * 0.3)
            ilab = ktext("통가", 28, INK, bold=True).move_to(island)
            cable = Line(LEFT * 0.4 + UP * 0.3, island.get_left(), buff=0.1).set_stroke(LGRAY, 4)
            t1 = max(0.4, min(1.0, d * 0.3))
            self.play(FadeIn(island), FadeIn(ilab), Create(cable), run_time=t1)
            broken = DashedVMobject(Line(cable.get_start(), cable.get_end()), num_dashes=8)
            broken.set_stroke(RED, 4)
            wk = chip("5주 고립", RED, 32).next_to(island, UP, buff=0.6)
            t2 = max(0.4, min(1.0, d * 0.3))
            self.play(Transform(cable, broken), FadeIn(wk, scale=1.3), run_time=t2)
            self.st["island"] = VGroup(island, ilab)
            self.hold(d - t1 - t2)

        def a2(d):
            ring = DashedVMobject(Circle(radius=0.95), num_dashes=16)
            ring.set_stroke(GRAY, 3).move_to(self.st["island"][0])
            self.act(d, Create(ring), Indicate(self.st["island"], color=RED, scale_factor=1.1))

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
    path = os.path.join(OUT, "episode.srt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def build_audio():
    from pydub import AudioSegment
    track = AudioSegment.silent(duration=int(INTRO_D * 1000))
    for seg in TIMED:
        track += AudioSegment.from_wav(seg["wav"])
        track += AudioSegment.silent(duration=int(GAP * 1000))
    path = os.path.join(OUT, "audio_track.wav")
    track.export(path, format="wav")
    return path


def main():
    print(f"[v2] {EP}편 | 음성: {'있음 — 완성 조립' if HAVE_AUDIO else '없음 — 무음 시안'} | "
          f"{'1080p30' if FULL else '480p15 시안'}")
    total = INTRO_D + sum(s["total"] + GAP for s in TIMED) + 1.2
    print(f"[v2] 예상 길이: {total:.0f}초 ({total / 60:.1f}분)")

    scene = Episode()
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
        final = os.path.join(OUT, "episode.mp4")
        cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", silent, "-i", audio,
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", final]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"[v2] 완성: {final}")
    else:
        final = os.path.join(OUT, "episode_silent_preview.mp4")
        if os.path.exists(final):
            os.remove(final)
        os.replace(silent, final)
        print(f"[v2] 무음 시안: {final} (음성 도착 후 다시 실행하면 완성본)")
    print(f"[v2] 자막: {srt}")


if __name__ == "__main__":
    main()
