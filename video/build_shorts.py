# -*- coding: utf-8 -*-
"""tech-history 쇼츠 조립기 — 본편 음성·사료를 재사용해 세로형(1080x1920) 쇼츠 생산.

규칙(2026-07-27 SEO 분석 박제분):
  - 본편 1개당 쇼츠 2종: ①반전형("~의 진짜 이유") ②요약형("N초 요약")
  - 첫 1.5초 훅 카드가 전부. 자막은 굽는다(쇼츠는 CC 사용률 낮음). 다크 배경(피드 대비).
사용:
  python video/build_shorts.py 01           # 시안(540x960, 15fps)
  python video/build_shorts.py 01 --full    # 완성(1080x1920, 30fps)
출력: video/output/01_v2/shorts_A.mp4 (반전형), shorts_B.mp4 (요약형)
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
OUT = os.path.join(ROOT, "video", "output", f"{EP}_v2")
AUDIO_DIR = os.path.join(OUT, "audio")
ASSETS = os.path.join(ROOT, "video", "output", "assets")

GAP = 0.3
HOOK_D = 1.6   # 훅 카드
END_D = 2.2    # 엔딩 카드

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
    config, Scene, VGroup, VMobject, Group, Text, Dot, Circle, Line, DashedLine,
    Rectangle, RoundedRectangle, Triangle, ImageMobject,
    Create, FadeIn, FadeOut, Transform, Indicate, Flash, LaggedStart, linear,
    UP, DOWN, LEFT, RIGHT, ORIGIN, UL, UR, DL, DR, WHITE, PI,
)
import numpy as np  # noqa: E402

config.background_color = DARK
config.frame_width = 9.0
config.frame_height = 16.0
if FULL:
    config.pixel_width, config.pixel_height, config.frame_rate = 1080, 1920, 30
else:
    config.pixel_width, config.pixel_height, config.frame_rate = 540, 960, 15
config.media_dir = os.path.join(OUT, "media_shorts")
config.disable_caching = True

with open(os.path.join(ROOT, "video", "scripts", f"{EP}.json"), encoding="utf-8") as f:
    SCRIPT = json.load(f)


def seg_info(i):
    wav = os.path.join(AUDIO_DIR, f"seg{i:03d}.wav")
    with wave.open(wav) as w:
        dur = w.getnframes() / float(w.getframerate())
    return {"id": i, "text": SCRIPT["segments"][i]["text"], "dur": dur, "wav": wav}


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


def ktext(s, fs=44, color=WHITE, bold=True):
    t = Text(s, font=KFONT, font_size=fs, color=color, weight="BOLD" if bold else "NORMAL")
    if t.width > 8.2:
        t.scale_to_fit_width(8.2)
    return t


def chip(s, color=RED, fs=34):
    t = Text(s, font=KFONT, font_size=fs, color=WHITE, weight="BOLD")
    box = RoundedRectangle(corner_radius=0.16, width=t.width + 0.55, height=t.height + 0.42)
    box.set_fill(color, 1).set_stroke(width=0)
    t.move_to(box)
    return VGroup(box, t)


class ShortBase(Scene):
    SPEC = None  # {"segs": [...], "hook": [...], "title": ...}

    def construct(self):
        self.add(grid_bg())
        self.subtitle = None
        self.hook_card()
        for k, i in enumerate(self.SPEC["segs"]):
            info = seg_info(i)
            getattr(self, f"seg{i:03d}")(info)
            if self.subtitle:
                self.remove(self.subtitle)
                self.subtitle = None
            self.clear_stage(GAP if k < len(self.SPEC["segs"]) - 1 else 0.3)
        self.end_card()

    # --- 공통 ---
    def sub(self, txt):
        t = Text(txt, font=KFONT, font_size=40, color=WHITE, weight="BOLD")
        if t.width > 8.0:
            t.scale_to_fit_width(8.0)
        t.move_to(DOWN * 5.1)
        bg = RoundedRectangle(corner_radius=0.18, width=t.width + 0.5, height=t.height + 0.42)
        bg.set_fill("#000000", 0.55).set_stroke(width=0).move_to(t)
        grp = VGroup(bg, t)
        if self.subtitle:
            self.remove(self.subtitle)
        self.add(grp)
        self.subtitle = grp

    def beats(self, info, acts):
        sents = split_sents(info["text"])
        chars = sum(len(s) for s in sents) or 1
        durs = [max(0.7, info["dur"] * len(s) / chars) for s in sents]
        scale = info["dur"] / sum(durs)
        for i, (txt, d) in enumerate(zip(sents, [x * scale for x in durs])):
            self.sub(txt)
            if i < len(acts) and acts[i]:
                acts[i](d)
            else:
                self.hold(d)

    def act(self, d, *anims, rt=None):
        if anims:
            rt = max(0.3, min(rt if rt is not None else min(1.2, d * 0.6), d))
            self.play(*anims, run_time=rt)
            d -= rt
        self.hold(d)

    def hold(self, d):
        if d > 2.0 / config.frame_rate:
            self.wait(d)

    def clear_stage(self, rt):
        ms = [m for m in self.mobjects if m is not self.subtitle]
        fade = ms[1:]  # ms[0] = 모눈 배경은 유지
        if fade:
            self.play(*[FadeOut(m) for m in fade], run_time=max(0.25, rt))
        else:
            self.hold(rt)

    def photo(self, fname, height=4.5, pos=ORIGIN):
        img = ImageMobject(os.path.join(ASSETS, fname))
        img.height = height
        img.move_to(pos)
        border = Rectangle(width=img.width + 0.1, height=img.height + 0.1)
        border.set_stroke(WHITE, 5).move_to(img)
        return Group(img, border)

    def show(self, *ms):
        self.add(*ms)
        if self.subtitle:
            self.remove(self.subtitle)
            self.add(self.subtitle)

    def hook_card(self):
        lines = self.SPEC["hook"]
        t1 = ktext(lines[0], fs=72, color=WHITE).move_to(UP * 1.6)
        t2 = ktext(lines[1], fs=88, color=AMBER).move_to(UP * 0.1)
        self.play(FadeIn(t1, scale=1.2), run_time=0.4)
        self.play(FadeIn(t2, scale=1.35), Flash(t2.get_center(), color=AMBER, flash_radius=2.2), run_time=0.5)
        self.wait(HOOK_D - 0.9)
        self.play(FadeOut(t1), FadeOut(t2), run_time=0.3)

    def end_card(self):
        t = ktext("전체 이야기는 채널에서", fs=52).move_to(UP * 0.8)
        btn = chip("구독", RED, 46).move_to(DOWN * 0.6)
        cc = Text("© nous-zero", font=KFONT, font_size=26, color=GRAY).move_to(DOWN * 2.0)
        self.play(FadeIn(t, shift=UP * 0.2), FadeIn(btn, scale=1.4), FadeIn(cc), run_time=0.5)
        self.wait(END_D - 0.5)

    # --- 세그 장면 (세로 구도) ---
    def seg000(self, info):
        term = RoundedRectangle(corner_radius=0.25, width=8.2, height=5.2)
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
    SPEC = {"segs": [0, 1, 2],
            "hook": ["인터넷의 첫마디는", '"헬로"가 아니다']}


class ShortB(ShortBase):
    SPEC = {"segs": [3, 5, 6, 12],
            "hook": ["핵전쟁이 만든", "인터넷"]}


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
        track += AudioSegment.from_wav(os.path.join(AUDIO_DIR, f"seg{i:03d}.wav"))
        track += AudioSegment.silent(duration=int((GAP if k < len(segs) - 1 else 0.3) * 1000))
    track += AudioSegment.silent(duration=int(END_D * 1000))
    apath = os.path.join(OUT, f"{name}_audio.wav")
    track.export(apath, format="wav")
    import imageio_ffmpeg
    final = os.path.join(OUT, f"{name}.mp4")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", silent, "-i", apath,
                    "-c:v", "libx264", "-crf", "23", "-preset", "medium",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", final],
                   check=True, capture_output=True)
    print(f"[shorts] {name}: {final} ({len(track) / 1000:.0f}초 오디오)")


if __name__ == "__main__":
    build(ShortA, "shorts_A")
    build(ShortB, "shorts_B")
