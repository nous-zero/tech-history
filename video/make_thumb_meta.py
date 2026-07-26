# -*- coding: utf-8 -*-
"""유튜브 썸네일(1280x720) + 메타데이터(제목/설명/태그) 생성. 사용: python video/make_thumb_meta.py 01"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INK = (31, 41, 55)
BLUE = (37, 99, 235)
RED = (220, 38, 38)
LGRAY = (156, 163, 175)
F = r"C:\Windows\Fonts"

META = {
    "01": {
        "thumb_lines": ["인터넷의", "첫마디는"],
        "thumb_big": '"LO"',
        "title": 'ARPANET — 핵전쟁이 만든 인터넷의 시작, 첫마디는 "LO" | 테크스토리 01',
        "desc_head": '1969년 인류 인터넷(ARPANET)의 첫 메시지는 왜 "LO" 두 글자였을까요?\n'
                     '핵전쟁 공포가 낳은 그물망 인터넷, 패킷과 라우터의 탄생 이야기입니다.',
        "tags": ["ARPANET", "인터넷 역사", "기술의 역사", "IT 역사", "패킷", "라우터",
                 "인터넷의 시작", "테크스토리", "네트워크", "LO"],
    },
}

def font(size, bold=True, mono=False):
    name = "consola.ttf" if mono else ("malgunbd.ttf" if bold else "malgun.ttf")
    return ImageFont.truetype(os.path.join(F, name), size)

def main(ep):
    out = os.path.join(ROOT, "video", "output", ep)
    os.makedirs(out, exist_ok=True)
    m = META[ep]
    img = Image.new("RGB", (1280, 720), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((60, 44), "테크스토리 #%s" % ep, font=font(40), fill=BLUE)
    d.line([60, 104, 400, 104], fill=BLUE, width=5)
    y = 190
    for line in m["thumb_lines"]:
        d.text((60, y), line, font=font(110), fill=INK)
        y += 140
    d.text((60, y + 6), m["thumb_big"], font=font(190), fill=BLUE)
    d.rounded_rectangle([760, 200, 1220, 560], radius=22, fill=INK)
    d.text((810, 260), "> LOGIN", font=font(40, mono=True), fill=LGRAY)
    d.text((810, 330), "LO", font=font(120, mono=True), fill=(255, 255, 255))
    d.rectangle([1010, 340, 1075, 450], fill=(255, 255, 255))
    d.text((810, 490), "SYSTEM DOWN", font=font(36, mono=True), fill=RED)
    d.text((1220, 690), "© 2026 박정훈", font=font(26, bold=False), fill=LGRAY, anchor="rs")
    img.save(os.path.join(out, "thumbnail.png"))

    chapters = ""
    ch_file = os.path.join(out, "chapters.txt")
    if os.path.exists(ch_file):
        chapters = open(ch_file, encoding="utf-8").read().strip()
    desc = (m["desc_head"] + "\n\n"
            "기술의 역사를 '문제 → 해결 → 새로운 문제'의 연쇄로 풀어가는 시리즈, 테크스토리입니다.\n"
            "전체 문서·이미지: https://github.com/nous-zero/tech-history\n\n"
            + ("챕터\n" + chapters + "\n\n" if chapters else "")
            + "등장인물과 대화는 이해를 돕기 위한 각색이며, 기술 내용은 모두 실제 기록입니다.\n"
            "출처: Internet Society, Paul Baran(RAND 1964), Al Jazeera·NPR(2022)\n\n"
            "#기술의역사 #ARPANET #인터넷역사")
    with open(os.path.join(out, "metadata.txt"), "w", encoding="utf-8") as f:
        f.write("[제목]\n%s\n\n[설명]\n%s\n\n[태그]\n%s\n" % (m["title"], desc, ", ".join(m["tags"])))
    print("완성: thumbnail.png / metadata.txt")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "01")
