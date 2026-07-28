# -*- coding: utf-8 -*-
"""tech-history 쇼츠 조립기 — 본편 음성·사료를 재사용해 세로형(1080x1920) 쇼츠 생산.

규칙(2026-07-27 SEO 분석 박제분):
  - 본편 1개당 쇼츠 2종: ①반전형("~의 진짜 이유") ②요약형("N초 요약")
  - 첫 1.5초 훅 카드가 전부. 자막은 굽는다(쇼츠는 CC 사용률 낮음). 다크 배경(피드 대비).
사용:
  python video/build_shorts.py <편번호>           # 시안(540x960, 15fps)
  python video/build_shorts.py <편번호> --full    # 완성(1080x1920, 30fps)
출력: video/output/<편>_v2/shorts_A.mp4 (반전형), shorts_B.mp4 (요약형)
지원 편: 01(아파넷 LO), 02(TCP/IP Flag Day)
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

GAP = 0.15
HOOK_D = 1.3   # 훅 카드
END_D = 1.6    # 엔딩 카드
SPEED = 1.35   # 나레이션 배속(음정 유지) — 쇼츠 문법
ZOOM_DRIFT = 0.985  # 문장마다 화면이 서서히 밀고 들어감(정지화면 제거)

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


class ShortBase(MovingCameraScene):
    SPEC = None  # {"segs": [...], "hook": [...], "title": ...}

    def construct(self):
        self.add(grid_bg())
        self.subtitle = None
        self.hook_card()
        keep = self.SPEC.get("keep", set())  # 이 세그 뒤에는 화면을 지우지 않음(이야기 연속)
        for k, i in enumerate(self.SPEC["segs"]):
            info = seg_info(i)
            getattr(self, f"seg{i:03d}")(info)
            if self.subtitle:
                self.remove(self.subtitle)
                self.subtitle = None
            if i in keep:
                self.hold(GAP)
            else:
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

    POP_POS = [UP * 5.3 + LEFT * 1.2, UP * 5.0 + RIGHT * 1.3, UP * 5.4]

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
                pop = ktext(pops[i], fs=86, color=color)
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
        # 줌 하한선(폭 7.2) 아래로는 더 밀고 들어가지 않음 — 자막 안전지대 보호
        frame = self.camera.frame
        if frame.width * (ZOOM_DRIFT ** steps) < 7.2:
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
        img.move_to(pos)
        if not framed:  # 투명 PNG(배지 등) — 흰 액자 없이
            return Group(img)
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
    bgm_path = os.path.join(OUT, f"{name}_bgm.wav")
    make_bgm(len(track) / 1000 + 0.5, bgm_path)
    bgm = AudioSegment.from_wav(bgm_path).apply_gain(-13)
    track = bgm[:len(track)].overlay(track)  # 비트 위에 육성
    apath = os.path.join(OUT, f"{name}_audio.wav")
    track.export(apath, format="wav")
    import imageio_ffmpeg
    final = os.path.join(OUT, f"{name}.mp4")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", silent, "-i", apath,
                    "-c:v", "libx264", "-crf", "23", "-preset", "medium",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", final],
                   check=True, capture_output=True)
    print(f"[shorts] {name}: {final} ({len(track) / 1000:.0f}초 오디오)")


SHORTS = {"01": ((ShortA, "shorts_A"), (ShortB, "shorts_B")),
          "02": ((Short02A, "shorts_A"), (Short02B, "shorts_B"))}

if __name__ == "__main__":
    if EP not in SHORTS:
        print(f"[shorts] 오류: {EP}편 쇼츠 SPEC 없음 (지원: {', '.join(SHORTS)})")
        sys.exit(1)
    for cls, name in SHORTS[EP]:
        build(cls, name)
