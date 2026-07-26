# -*- coding: utf-8 -*-
"""tech-history 영상 공장 — 대본(md) → 유튜브용 MP4 + 자막(SRT) + 썸네일 + 메타데이터.

무료 부품: edge-tts(한국어 남녀 음성) + Pillow(슬라이드) + FFmpeg(조립).
사용: python video/make_video.py 01   (편 번호)
출력: video/output/NN/ 폴더에 episode.mp4, episode.srt, thumbnail.png, metadata.txt
"""
import asyncio
import glob
import os
import re
import subprocess
import sys

import edge_tts
import imageio_ffmpeg
from mutagen.mp3 import MP3
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 1920, 1080
BG = (255, 255, 255)
INK = (31, 41, 55)
GRAY = (107, 114, 128)
LGRAY = (156, 163, 175)
BLUE = (37, 99, 235)
RED = (220, 38, 38)
FONT_DIR = r"C:\Windows\Fonts"

NARRATOR = ("ko-KR-SunHiNeural", "+4%", "+0Hz")
VOICES = {
    "장군": ("ko-KR-InJoonNeural", "-4%", "-20Hz"),
    "참모": ("ko-KR-InJoonNeural", "+4%", "+25Hz"),
    "연구원": ("ko-KR-InJoonNeural", "+2%", "+0Hz"),
    "선배": ("ko-KR-InJoonNeural", "-2%", "-12Hz"),
    "후배": ("ko-KR-InJoonNeural", "+6%", "+30Hz"),
    "운영자": ("ko-KR-InJoonNeural", "+4%", "+22Hz"),
    "관리자": ("ko-KR-InJoonNeural", "-4%", "-15Hz"),
    "기획": ("ko-KR-InJoonNeural", "-2%", "-10Hz"),
    "개발자": ("ko-KR-InJoonNeural", "+4%", "+18Hz"),
    "신참": ("ko-KR-InJoonNeural", "+6%", "+28Hz"),
    "고참": ("ko-KR-InJoonNeural", "-4%", "-16Hz"),
    "임원": ("ko-KR-InJoonNeural", "-3%", "-14Hz"),
    "동료": ("ko-KR-InJoonNeural", "+4%", "+20Hz"),
    "알바생": ("ko-KR-InJoonNeural", "+5%", "+15Hz"),
    "사용자": ("ko-KR-InJoonNeural", "+3%", "+10Hz"),
}
IMAGE_CUES = {  # 이 문구가 든 문단 '다음'에 해당 이미지를 3초 보여줌
    "01": [("건넨 첫마디는", "01-1-first-message-lo.png", "1969년, 인류 인터넷의 첫마디"),
           ("산 이웃 쪽으로 보냅니다", "01-3-packet-header.png", "패킷과 헤더 — 데이터는 택배처럼 배달된다"),
           ("해보게", "01-2-star-vs-mesh.png", "별 모양 전화망 vs 그물망 ARPANET")],
}

def font(size, bold=False, mono=False):
    name = "consola.ttf" if mono else ("malgunbd.ttf" if bold else "malgun.ttf")
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)

def wrap(draw, text, fnt, max_w):
    lines, line = [], ""
    for word in text.split(" "):
        cand = (line + " " + word).strip()
        if draw.textlength(cand, font=fnt) <= max_w:
            line = cand
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines

def base_slide(ep, label_text):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((80, 70), label_text, font=font(34, bold=True), fill=BLUE)
    d.line([80, 120, 480, 120], fill=BLUE, width=4)
    d.text((W - 80, H - 50), "© 2026 박정훈 · tech-history %s" % ep,
           font=font(26), fill=LGRAY, anchor="rs")
    return img, d

def text_slide(path, ep, label, speaker, text, title_card=False, note=None):
    img, d = base_slide(ep, label)
    max_w = W - 320
    size = 62 if title_card else 54
    while True:
        fnt = font(size, bold=title_card)
        lines = wrap(d, text, fnt, max_w)
        if len(lines) <= (7 if title_card else 9) or size <= 34:
            break
        size -= 4
    lh = int(size * 1.55)
    block_h = len(lines) * lh + (90 if speaker else 0)
    y = max(190, (H - block_h) // 2)
    if speaker:
        bw = d.textlength(speaker, font=font(34, bold=True)) + 56
        d.rounded_rectangle([160, y, 160 + bw, y + 62], radius=14, fill=BLUE)
        d.text((160 + bw / 2, y + 31), speaker, font=font(34, bold=True), fill=BG, anchor="mm")
        y += 100
    color = INK
    for l in lines:
        d.text((160, y), l, font=fnt, fill=color)
        y += lh
    if note:
        d.text((160, H - 130), note, font=font(28), fill=GRAY)
    img.save(path)

def image_slide(path, ep, label, image_file, caption):
    img, d = base_slide(ep, label)
    src = Image.open(os.path.join(ROOT, "posts", "frontend", "images", image_file))
    src.thumbnail((1560, 800))
    img.paste(src, ((W - src.width) // 2, 170))
    d.text((W // 2, 1015), caption, font=font(34), fill=INK, anchor="mm")
    img.save(path)

def parse_episode(ep):
    md = glob.glob(os.path.join(ROOT, "posts", "frontend", "frontend-story-%s-*.md" % ep))[0]
    t = open(md, encoding="utf-8").read()
    body = re.search(r"## LinkedIn 본문\s*\n(.*?)\n---", t, re.S).group(1)
    paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    label, disclosure, segments = "", "", []
    for p in paras:
        if p.startswith("!["):
            continue
        if p.startswith("[") and not label:
            label = p.strip("[]")
            continue
        if p.startswith("(등장인물"):
            disclosure = p.strip("()")
            continue
        if p.startswith("#") or p.startswith("©") or p.startswith("(대화는 각색입니다"):
            continue
        m = re.match(r'^([가-힣A-Za-z]{1,4}):\s*"(.*)"\s*$', p, re.S)
        if m:
            segments.append({"speaker": m.group(1), "text": m.group(2).replace("\n", " ")})
        else:
            segments.append({"speaker": None, "text": p.replace("\n", " ")})
    return md, label, disclosure, segments

async def tts(text, voice, rate, pitch, out):
    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(out)

def run_ffmpeg(args):
    r = subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error"] + args,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])

def fmt_ts(sec):
    ms = int(round(sec * 1000))
    return "%02d:%02d:%02d,%03d" % (ms // 3600000, ms % 3600000 // 60000, ms % 60000 // 1000, ms % 1000)

def main(ep):
    out_dir = os.path.join(ROOT, "video", "output", ep)
    os.makedirs(out_dir, exist_ok=True)
    md, label, disclosure, segments = parse_episode(ep)
    label_short = "테크스토리 #%s" % ep
    print("대본: %s / 문단 %d개" % (os.path.basename(md), len(segments)))

    chunks, srt, t_cursor, chapters = [], [], 0.0, [(0.0, "인트로")]
    cues = list(IMAGE_CUES.get(ep, []))
    for i, seg in enumerate(segments):
        mp3 = os.path.join(out_dir, "seg%03d.mp3" % i)
        png = os.path.join(out_dir, "seg%03d.png" % i)
        voice, rate, pitch = VOICES.get(seg["speaker"], NARRATOR) if seg["speaker"] else NARRATOR
        asyncio.run(tts(seg["text"], voice, rate, pitch, mp3))
        dur = MP3(mp3).info.length
        if i == 0:
            text_slide(png, ep, label_short, None, label, title_card=True,
                       note=disclosure if disclosure else None)
        else:
            text_slide(png, ep, label_short, seg["speaker"], seg["text"])
        mp4 = os.path.join(out_dir, "seg%03d.mp4" % i)
        run_ffmpeg(["-loop", "1", "-i", png, "-i", mp3, "-t", "%.3f" % (dur + 0.35),
                    "-r", "30", "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-ar", "24000", "-ac", "1", mp4])
        srt.append((t_cursor, t_cursor + dur,
                    ("%s: %s" % (seg["speaker"], seg["text"])) if seg["speaker"] else seg["text"]))
        if seg["speaker"] and (not chapters or chapters[-1][1] != "장면 재연") and i > 0:
            chapters.append((t_cursor, "장면 재연"))
        t_cursor += dur + 0.35
        chunks.append(mp4)
        for cue in list(cues):
            if cue[0] in seg["text"]:
                cpng = os.path.join(out_dir, "cue%03d.png" % i)
                image_slide(cpng, ep, label_short, cue[1], cue[2])
                cmp4 = os.path.join(out_dir, "cue%03d.mp4" % i)
                run_ffmpeg(["-loop", "1", "-i", cpng, "-f", "lavfi",
                            "-i", "anullsrc=r=24000:cl=mono", "-t", "3.0",
                            "-r", "30", "-c:v", "libx264", "-tune", "stillimage",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "24000", "-ac", "1", cmp4])
                chapters.append((t_cursor, cue[2].split(" — ")[0]))
                t_cursor += 3.0
                chunks.append(cmp4)
                cues.remove(cue)
        print("  seg %d/%d (%.1fs) %s" % (i + 1, len(segments), dur, seg["speaker"] or "나레이션"))

    lst = os.path.join(out_dir, "concat.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write("file '%s'\n" % c.replace("\\", "/"))
    final = os.path.join(out_dir, "episode.mp4")
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                "-movflags", "+faststart", final])

    with open(os.path.join(out_dir, "episode.srt"), "w", encoding="utf-8") as f:
        for n, (a, b, txt) in enumerate(srt, 1):
            f.write("%d\n%s --> %s\n%s\n\n" % (n, fmt_ts(a), fmt_ts(b), txt))

    with open(os.path.join(out_dir, "chapters.txt"), "w", encoding="utf-8") as f:
        seen = set()
        for tsec, name in chapters:
            key = name
            if key in seen:
                continue
            seen.add(key)
            f.write("%02d:%02d %s\n" % (int(tsec) // 60, int(tsec) % 60, name))

    for c in chunks:
        os.remove(c)
    print("완성: %s (총 %.1f초)" % (final, t_cursor))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "01")
