# -*- coding: utf-8 -*-
"""tech-history 발행 이미지 생성기.

visual-style-guide.md의 톤앤매너를 코드로 고정한다:
색 4개(먹·회, 파랑, 빨강, 흰 배경) / 형태 어휘(장치=원, 연결=선, 조각=사각형,
끊김=빨간 점선+X, 강조 경로=굵은 파랑) / 우하단 서명.
실행: python generate_images.py  → 같은 폴더에 PNG 생성 (1200x630, 링크드인·X 업로드 규격)
"""
import math
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = (255, 255, 255)
INK = (31, 41, 55)
GRAY = (107, 114, 128)
LGRAY = (156, 163, 175)
DIVIDER = (229, 231, 235)
BLUE = (37, 99, 235)
RED = (220, 38, 38)

FONT_DIR = r"C:\Windows\Fonts"
HERE = os.path.dirname(os.path.abspath(__file__))


def f_regular(size):
    return ImageFont.truetype(os.path.join(FONT_DIR, "malgun.ttf"), size)


def f_bold(size):
    return ImageFont.truetype(os.path.join(FONT_DIR, "malgunbd.ttf"), size)


def f_mono(size):
    return ImageFont.truetype(os.path.join(FONT_DIR, "consola.ttf"), size)


def new_canvas():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def signature(draw, episode="01"):
    draw.text((1150, 612), f"tech-history {episode}", font=f_regular(18),
              fill=LGRAY, anchor="rs")


def arrow(draw, x1, y1, x2, y2, color=GRAY, width=4, head=14):
    draw.line([x1, y1, x2, y2], fill=color, width=width)
    ang = math.atan2(y2 - y1, x2 - x1)
    for side in (-1, 1):
        a = ang + math.pi + side * 0.45
        draw.line([x2, y2, x2 + head * math.cos(a), y2 + head * math.sin(a)],
                  fill=color, width=width)


def dashed_line(draw, x1, y1, x2, y2, color=RED, width=4, on=14, off=10):
    dist = math.hypot(x2 - x1, y2 - y1)
    dx, dy = (x2 - x1) / dist, (y2 - y1) / dist
    t = 0.0
    while t < dist:
        seg = min(on, dist - t)
        draw.line([x1 + dx * t, y1 + dy * t,
                   x1 + dx * (t + seg), y1 + dy * (t + seg)],
                  fill=color, width=width)
        t += on + off


def cross_mark(draw, cx, cy, r=13, color=RED, width=6):
    draw.line([cx - r, cy - r, cx + r, cy + r], fill=color, width=width)
    draw.line([cx + r, cy - r, cx - r, cy + r], fill=color, width=width)


def node(draw, cx, cy, r=14, outline=GRAY, width=4):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BG,
                 outline=outline, width=width)


def img_01_1_lo():
    img, d = new_canvas()
    d.text((600, 62), "1969년 10월 29일, 인류 인터넷의 첫마디",
           font=f_bold(36), fill=INK, anchor="mm")
    d.rounded_rectangle([250, 120, 950, 450], radius=16, fill=INK)
    for i, x in enumerate((292, 316, 340)):
        d.ellipse([x - 7, 151, x + 7, 165], fill=GRAY)
    d.text((300, 228), "> 전송할 메시지: LOGIN", font=f_regular(26),
           fill=LGRAY, anchor="lm")
    d.text((300, 330), "LO", font=f_mono(96), fill=BG, anchor="lm")
    lo_w = d.textlength("LO", font=f_mono(96))
    cx = 300 + lo_w + 16
    d.rectangle([cx, 330 - 40, cx + 36, 330 + 40], fill=BG)
    d.text((300, 418), "*** SYSTEM DOWN ***", font=f_mono(26),
           fill=RED, anchor="lm")
    d.text((600, 505), '"LOGIN" 다섯 글자를 보내려다, 두 글자 만에 시스템 다운.',
           font=f_regular(26), fill=INK, anchor="mm")
    d.text((600, 548), '인터넷의 첫마디는 그렇게 "LO"가 됐다.',
           font=f_regular(26), fill=INK, anchor="mm")
    signature(d)
    img.save(os.path.join(HERE, "01-1-first-message-lo.png"))


def img_01_2_star_vs_mesh():
    img, d = new_canvas()
    d.text((300, 62), "기존 전화망 — 별 모양", font=f_bold(30), fill=INK, anchor="mm")
    d.text((880, 62), "ARPANET — 그물 모양", font=f_bold(30), fill=INK, anchor="mm")
    d.line([590, 100, 590, 500], fill=DIVIDER, width=2)

    center = (300, 320)
    outer = [(430, 320), (365, 207), (235, 207), (170, 320), (235, 433), (365, 433)]
    for px, py in outer:
        d.line([center[0], center[1], px, py], fill=GRAY, width=3)
    for px, py in outer:
        node(d, px, py)
    node(d, *center, r=22)
    cross_mark(d, *center, r=15)
    d.text((300, 540), "모든 회선이 중앙 교환국 한 곳으로 모인다",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((300, 578), "중앙이 파괴되면(빨간 X) 전체 마비",
           font=f_regular(24), fill=RED, anchor="mm")

    A, C, Dn, B = (700, 250), (850, 190), (1010, 205), (1075, 390)
    E, F, G = (725, 390), (875, 320), (910, 470)
    for p, q in [(A, C), (C, Dn), (Dn, B), (A, F), (C, F), (F, Dn), (E, F)]:
        d.line([p[0], p[1], q[0], q[1]], fill=GRAY, width=3)
    dashed_line(d, F[0], F[1], B[0], B[1])
    cross_mark(d, 975, 355, r=12, width=5)
    for p, q in [(A, E), (E, G), (G, B)]:
        d.line([p[0], p[1], q[0], q[1]], fill=BLUE, width=6)
    for px, py in (C, Dn, F):
        node(d, px, py)
    for px, py in (A, E, G, B):
        node(d, px, py, outline=BLUE, width=5)
    d.text((700, 220), "출발", font=f_bold(22), fill=BLUE, anchor="mm")
    d.text((1100, 394), "도착", font=f_bold(22), fill=BLUE, anchor="lm")
    d.text((880, 540), "교차로마다 우체국 컴퓨터 IMP(라우터의 조상)가 있어",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((880, 578), "끊긴 길(빨간 X)을 피해 옆길(파란 선)로 우회시킨다",
           font=f_regular(24), fill=BLUE, anchor="mm")
    signature(d)
    img.save(os.path.join(HERE, "01-2-star-vs-mesh.png"))


def img_01_3_packet_header():
    img, d = new_canvas()
    d.text((600, 62), "패킷과 헤더 — 데이터는 택배처럼 배달된다",
           font=f_bold(34), fill=INK, anchor="mm")

    d.rectangle([110, 170, 230, 330], outline=INK, width=4, fill=BG)
    for y in (205, 235, 265, 295):
        d.line([130, y, 210, y], fill=LGRAY, width=4)
    d.text((170, 372), "보낼 데이터", font=f_regular(24), fill=INK, anchor="mm")

    arrow(d, 252, 250, 328, 250)

    for i in range(3):
        y = 165 + i * 62
        d.rectangle([360, y, 424, y + 42], fill=BLUE)
        d.text((392, y + 21), "주소", font=f_regular(18), fill=BG, anchor="mm")
        d.rectangle([424, y, 545, y + 42], outline=INK, width=3, fill=BG)
        d.text((484, y + 21), "조각", font=f_regular(20), fill=INK, anchor="mm")
    d.text((452, 372), "조각(패킷)마다", font=f_regular(22), fill=INK, anchor="mm")
    d.text((452, 404), "주소표(헤더)를 붙인다", font=f_regular(22), fill=BLUE, anchor="mm")

    arrow(d, 568, 250, 640, 250)

    routes = [((660, 250), (735, 180), (810, 180), (885, 250)),
              ((660, 250), (772, 250), (885, 250)),
              ((660, 250), (735, 320), (810, 320), (885, 250))]
    for pts in routes:
        for j in range(len(pts) - 1):
            d.line([pts[j][0], pts[j][1], pts[j + 1][0], pts[j + 1][1]],
                   fill=GRAY, width=3)
    for px, py in [(735, 180), (810, 180), (772, 250), (735, 320), (810, 320)]:
        node(d, px, py, r=10, width=3)
    node(d, 660, 250, r=10, outline=BLUE, width=4)
    node(d, 885, 250, r=10, outline=BLUE, width=4)
    d.text((772, 372), "우체국 컴퓨터(라우터)들이", font=f_regular(22), fill=INK, anchor="mm")
    d.text((772, 404), "각자 다른 길로 릴레이", font=f_regular(22), fill=INK, anchor="mm")

    arrow(d, 908, 250, 955, 250)

    d.rectangle([975, 170, 1095, 330], outline=INK, width=4, fill=BG)
    for y in (205, 235, 265, 295):
        d.line([995, y, 1075, y], fill=LGRAY, width=4)
    d.text((1035, 372), "도착 후 재조립", font=f_regular(24), fill=INK, anchor="mm")

    d.text((600, 560), "'패킷'은 데이터 조각, '헤더'는 조각에 붙는 주소표 — 이름만 낯설 뿐 택배 송장과 같다",
           font=f_regular(24), fill=INK, anchor="mm")
    signature(d)
    img.save(os.path.join(HERE, "01-3-packet-header.png"))


def img_02_1_flag_day():
    img, d = new_canvas()
    d.text((600, 66), "인터넷 전체가 언어를 갈아탄 날", font=f_bold(36), fill=INK, anchor="mm")
    d.text((600, 148), "1983. 1. 1.", font=f_bold(56), fill=INK, anchor="mm")
    d.rounded_rectangle([270, 215, 510, 345], radius=14, outline=GRAY, width=4)
    d.text((390, 262), "NCP", font=f_bold(42), fill=GRAY, anchor="mm")
    d.text((390, 312), "옛 언어", font=f_regular(22), fill=GRAY, anchor="mm")
    arrow(d, 545, 280, 655, 280, color=INK, width=6, head=18)
    d.rounded_rectangle([690, 215, 930, 345], radius=14, outline=BLUE, width=5)
    d.text((810, 262), "TCP/IP", font=f_bold(42), fill=BLUE, anchor="mm")
    d.text((810, 312), "새 공통 언어", font=f_regular(22), fill=BLUE, anchor="mm")
    d.text((600, 435), "이날 아침까지 못 갈아탄 컴퓨터는 접속이 끊겼다 — 호스트 약 400대의 일제 전환",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((600, 480), '살아남은 자의 기념 배지: "I survived the TCP transition, 1/1/83"',
           font=f_regular(24), fill=RED, anchor="mm")
    signature(d, "02")
    img.save(os.path.join(HERE, "02-1-flag-day.png"))


def img_02_2_common_language():
    img, d = new_canvas()
    d.text((600, 60), "왜 서로 연결이 안 됐나 — 언어가 달랐다", font=f_bold(34), fill=INK, anchor="mm")
    d.line([590, 110, 590, 500], fill=DIVIDER, width=2)

    nets_l = [(180, 210, "유선망"), (400, 210, "위성망"), (290, 370, "무선망")]
    pairs = [(0, 1), (0, 2), (1, 2)]
    for a, b in pairs:
        x1, y1 = nets_l[a][0], nets_l[a][1]
        x2, y2 = nets_l[b][0], nets_l[b][1]
        dashed_line(d, x1, y1, x2, y2, color=RED, width=3)
        cross_mark(d, (x1 + x2) // 2, (y1 + y2) // 2, r=10, width=4)
    for x, y, name in nets_l:
        d.ellipse([x - 62, y - 62, x + 62, y + 62], fill=BG, outline=GRAY, width=4)
        d.text((x, y), name, font=f_bold(24), fill=INK, anchor="mm")
    d.text((300, 540), "망마다 규칙이 달라 서로 못 알아듣는다",
           font=f_regular(24), fill=RED, anchor="mm")

    nets_r = [(740, 200, "유선망"), (900, 180, "위성망"), (1050, 200, "무선망")]
    for x, y, name in nets_r:
        d.line([x, y + 48, x, 330], fill=BLUE, width=5)
        d.ellipse([x - 55, y - 55, x + 55, y + 55], fill=BG, outline=GRAY, width=4)
        d.text((x, y), name, font=f_bold(22), fill=INK, anchor="mm")
    d.rounded_rectangle([680, 330, 1110, 395], radius=10, fill=BLUE)
    d.text((895, 362), "공통 언어(규약) TCP/IP", font=f_bold(26), fill=BG, anchor="mm")
    d.text((880, 540), "규약 하나로 통일하면 어떤 망이든 연결된다",
           font=f_regular(24), fill=BLUE, anchor="mm")
    signature(d, "02")
    img.save(os.path.join(HERE, "02-2-common-language.png"))


def img_02_3_tcp_ip_roles():
    img, d = new_canvas()
    d.text((600, 62), "TCP/IP — 한 팀의 두 역할", font=f_bold(34), fill=INK, anchor="mm")
    d.rounded_rectangle([150, 140, 560, 430], radius=14, outline=BLUE, width=4)
    d.text((355, 195), "IP", font=f_bold(44), fill=BLUE, anchor="mm")
    d.text((355, 250), "주소 담당", font=f_bold(26), fill=INK, anchor="mm")
    d.text((355, 300), "봉투에 받는 주소를 쓰고", font=f_regular(24), fill=INK, anchor="mm")
    d.text((355, 340), "길을 찾아 배달한다", font=f_regular(24), fill=INK, anchor="mm")
    d.rounded_rectangle([640, 140, 1050, 430], radius=14, outline=BLUE, width=4)
    d.text((845, 195), "TCP", font=f_bold(44), fill=BLUE, anchor="mm")
    d.text((845, 250), "품질 담당", font=f_bold(26), fill=INK, anchor="mm")
    d.text((845, 300), "다 도착했는지 확인하고", font=f_regular(24), fill=INK, anchor="mm")
    d.text((845, 340), "빠진 조각은 다시 받아", font=f_regular(24), fill=INK, anchor="mm")
    d.text((845, 380), "순서대로 재조립한다", font=f_regular(24), fill=INK, anchor="mm")
    d.text((600, 500), "택배로 치면 — 송장과 배달이 IP, 검수와 조립이 TCP. 그래서 붙여서 'TCP/IP'",
           font=f_regular(24), fill=INK, anchor="mm")
    signature(d, "02")
    img.save(os.path.join(HERE, "02-3-tcp-ip-roles.png"))


if __name__ == "__main__":
    img_01_1_lo()
    img_01_2_star_vs_mesh()
    img_01_3_packet_header()
    img_02_1_flag_day()
    img_02_2_common_language()
    img_02_3_tcp_ip_roles()
    print("생성 완료: 01편 3장 + 02편 3장 PNG (1200x630)")
