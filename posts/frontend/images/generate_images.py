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


def img_03_1_vague():
    img, d = new_canvas()
    d.text((600, 66), "웹의 탄생을 승인한 세 단어", font=f_bold(36), fill=INK, anchor="mm")
    d.rectangle([400, 120, 800, 480], outline=INK, width=4, fill=BG)
    d.text((600, 165), "Information Management:", font=f_mono(22), fill=GRAY, anchor="mm")
    d.text((600, 195), "A Proposal (1989)", font=f_mono(22), fill=GRAY, anchor="mm")
    for y in (240, 270, 300, 400, 430):
        d.line([440, y, 760, y], fill=LGRAY, width=4)
    d.text((600, 350), "Vague but exciting.", font=f_bold(38), fill=RED, anchor="mm")
    d.text((600, 530), "팀 버너스리의 제안서 표지에 상사 마이크 센달이 남긴 실제 메모",
           font=f_regular(24), fill=INK, anchor="mm")
    signature(d, "03")
    img.save(os.path.join(HERE, "03-1-vague-but-exciting.png"))


def img_03_2_web_trio():
    img, d = new_canvas()
    d.text((600, 66), "웹 = 인터넷 위의 우편 시스템", font=f_bold(34), fill=INK, anchor="mm")
    items = [(260, "HTML", "공통 문서 양식", "(편지지 양식)"),
             (600, "URL", "문서의 고유 주소", "(받는 곳 주소)"),
             (940, "HTTP", "주고받는 규칙", "(배달 규칙)")]
    for x, name, s1, s2 in items:
        d.rounded_rectangle([x - 150, 160, x + 150, 400], radius=14, outline=BLUE, width=4)
        d.text((x, 220), name, font=f_bold(40), fill=BLUE, anchor="mm")
        d.text((x, 290), s1, font=f_regular(24), fill=INK, anchor="mm")
        d.text((x, 330), s2, font=f_regular(22), fill=GRAY, anchor="mm")
    d.text((600, 470), "도로망(인터넷)과 공통 언어(TCP/IP) 위에 세워진 문서 배달 체계",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((600, 510), "1989년 한 제안서에서 세 발명이 한 세트로 나왔다",
           font=f_regular(22), fill=GRAY, anchor="mm")
    signature(d, "03")
    img.save(os.path.join(HERE, "03-2-web-trio.png"))


def _browser_frame(d, x1, y1, x2, y2):
    d.rectangle([x1, y1, x2, y2], outline=GRAY, width=3, fill=BG)
    d.line([x1, y1 + 36, x2, y1 + 36], fill=GRAY, width=3)
    for i, cx in enumerate((x1 + 18, x1 + 40, x1 + 62)):
        d.ellipse([cx - 6, y1 + 12, cx + 6, y1 + 24], outline=GRAY, width=2)


def img_04_1_text_vs_image():
    img, d = new_canvas()
    d.text((300, 62), "1992년의 웹", font=f_bold(30), fill=INK, anchor="mm")
    d.text((880, 62), "Mosaic 이후 (1993)", font=f_bold(30), fill=INK, anchor="mm")
    d.line([590, 100, 590, 500], fill=DIVIDER, width=2)
    _browser_frame(d, 100, 110, 500, 440)
    for y in range(180, 420, 34):
        d.line([130, y, 470, y], fill=LGRAY, width=5)
    _browser_frame(d, 680, 110, 1080, 440)
    for y in (180, 214):
        d.line([710, y, 1050, y], fill=LGRAY, width=5)
    d.rectangle([710, 240, 1050, 380], fill=BLUE)
    d.ellipse([760, 265, 800, 305], fill=BG)
    d.polygon([(830, 380), (930, 280), (1030, 380)], fill=BG)
    d.line([710, 410, 1050, 410], fill=LGRAY, width=5)
    d.text((300, 540), "글자만 보이던 문서", font=f_regular(24), fill=INK, anchor="mm")
    d.text((880, 540), "글과 그림이 한 화면에 — 웹이 대중의 것이 되다",
           font=f_regular(24), fill=BLUE, anchor="mm")
    signature(d, "04")
    img.save(os.path.join(HERE, "04-1-text-vs-image-web.png"))


def img_04_2_ipo():
    img, d = new_canvas()
    d.text((600, 62), "1995년 8월 9일 — 넷스케이프 상장일", font=f_bold(34), fill=INK, anchor="mm")
    pts = [(260, 355, "공모가 $28"), (500, 194, "개장 $71"),
           (740, 180, "장중 최고 $74.75"), (980, 242, "종가 $58.25")]
    d.line([180, 460, 1060, 460], fill=GRAY, width=3)
    for i in range(len(pts) - 1):
        d.line([pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]], fill=BLUE, width=5)
    for x, y, label in pts:
        node(d, x, y, r=10, outline=BLUE, width=4)
        d.text((x, y - 34), label, font=f_bold(22), fill=INK, anchor="mm")
    d.text((600, 520), "창업 16개월 적자 회사의 상장 — 주문 폭주로 나스닥 개장이 2시간 늦어졌다",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((600, 558), "닷컴 열풍의 방아쇠", font=f_regular(22), fill=GRAY, anchor="mm")
    signature(d, "04")
    img.save(os.path.join(HERE, "04-2-netscape-ipo.png"))


def img_05_1_ten_days():
    img, d = new_canvas()
    d.text((600, 66), "10일 만에 태어난 언어", font=f_bold(36), fill=INK, anchor="mm")
    d.text((600, 180), "JavaScript", font=f_bold(64), fill=INK, anchor="mm")
    for i in range(10):
        x = 285 + i * 64
        if i == 9:
            d.rounded_rectangle([x, 260, x + 54, 314], radius=8, fill=BLUE)
            d.text((x + 27, 287), "10", font=f_bold(24), fill=BG, anchor="mm")
        else:
            d.rounded_rectangle([x, 260, x + 54, 314], radius=8, outline=GRAY, width=3)
            d.text((x + 27, 287), str(i + 1), font=f_regular(24), fill=GRAY, anchor="mm")
    d.text((600, 400), "1995년, 마감에 쫓긴 브렌던 아이크가 열흘 만에 만든 언어",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((600, 448), "스택오버플로 2025 조사: 개발자 66%가 사용 — 30년째 최정상",
           font=f_bold(24), fill=BLUE, anchor="mm")
    d.text((600, 496), "Java와는 이름만 비슷한 남남 (인도와 인도네시아의 관계)",
           font=f_regular(22), fill=GRAY, anchor="mm")
    signature(d, "05")
    img.save(os.path.join(HERE, "05-1-ten-days.png"))


def img_05_2_dom_map():
    img, d = new_canvas()
    d.text((600, 62), "DOM — 브라우저가 그리는 페이지 지도", font=f_bold(34), fill=INK, anchor="mm")
    d.rectangle([120, 160, 330, 400], outline=INK, width=4, fill=BG)
    for i, t in enumerate(("<html>", " <body>", "  <h1>", "  <button>")):
        d.text((145, 205 + i * 46), t, font=f_mono(24), fill=GRAY, anchor="lm")
    d.text((225, 440), "HTML 문서", font=f_regular(22), fill=INK, anchor="mm")
    arrow(d, 355, 280, 425, 280)
    tree = {(600, 210): [(510, 320), (600, 320), (690, 320)]}
    for parent, kids in tree.items():
        for k in kids:
            d.line([parent[0], parent[1], k[0], k[1]], fill=GRAY, width=3)
    node(d, 600, 210, r=16)
    node(d, 510, 320, r=14)
    node(d, 600, 320, r=14)
    node(d, 690, 320, r=14, outline=BLUE, width=5)
    d.text((600, 380), "지도 (DOM)", font=f_regular(22), fill=INK, anchor="mm")
    d.text((600, 412), "JS: \"이 버튼 색을 바꿔\"", font=f_regular(22), fill=BLUE, anchor="mm")
    arrow(d, 770, 280, 840, 280)
    _browser_frame(d, 865, 160, 1085, 400)
    d.line([895, 230, 1055, 230], fill=LGRAY, width=5)
    d.line([895, 264, 1055, 264], fill=LGRAY, width=5)
    d.rounded_rectangle([915, 300, 1035, 350], radius=8, fill=BLUE)
    d.text((975, 325), "버튼", font=f_bold(22), fill=BG, anchor="mm")
    d.text((975, 440), "화면이 그 자리에서 반응", font=f_regular(22), fill=INK, anchor="mm")
    d.text((600, 520), "브라우저는 문서를 읽어 지도를 만들고, JavaScript는 지도를 보며 화면을 바꾼다",
           font=f_regular(24), fill=INK, anchor="mm")
    signature(d, "05")
    img.save(os.path.join(HERE, "05-2-dom-map.png"))


def img_06_1_bundling():
    img, d = new_canvas()
    d.text((600, 66), "끼워팔기 — 이미 깔려 있는 공짜", font=f_bold(36), fill=INK, anchor="mm")
    d.rounded_rectangle([340, 130, 860, 470], radius=16, outline=INK, width=5)
    d.text((600, 178), "Windows 95", font=f_bold(32), fill=INK, anchor="mm")
    d.rounded_rectangle([450, 230, 750, 400], radius=12, outline=BLUE, width=5)
    d.text((600, 295), "IE", font=f_bold(56), fill=BLUE, anchor="mm")
    d.text((600, 360), "기본 탑재 · 공짜", font=f_regular(24), fill=BLUE, anchor="mm")
    d.text((600, 525), "아무리 좋은 제품도, 이미 깔려 있는 공짜를 이기긴 어렵다",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((600, 562), "이 전략은 훗날 미국 반독점 소송(2001)의 핵심 쟁점이 된다",
           font=f_regular(22), fill=GRAY, anchor="mm")
    signature(d, "06")
    img.save(os.path.join(HERE, "06-1-bundling.png"))


def img_06_2_html_css_js():
    img, d = new_canvas()
    d.text((600, 66), "웹 화면의 3대 요소 — 30년째 불변", font=f_bold(34), fill=INK, anchor="mm")
    items = [(260, "HTML", "구조", "뼈대"),
             (600, "CSS", "표현", "옷"),
             (940, "JavaScript", "동작", "움직임")]
    for x, name, s1, s2 in items:
        d.rounded_rectangle([x - 150, 160, x + 150, 400], radius=14, outline=BLUE, width=4)
        d.text((x, 225), name, font=f_bold(38), fill=BLUE, anchor="mm")
        d.text((x, 295), s1, font=f_bold(26), fill=INK, anchor="mm")
        d.text((x, 340), f"비유: {s2}", font=f_regular(22), fill=GRAY, anchor="mm")
    d.text((600, 470), "1996년 CSS의 등장으로 완성된 조합 — 지금도 모든 웹페이지의 근간",
           font=f_regular(24), fill=INK, anchor="mm")
    signature(d, "06")
    img.save(os.path.join(HERE, "06-2-html-css-js.png"))


def img_07_1_jit():
    img, d = new_canvas()
    d.text((300, 62), "기존 방식 — 한 줄씩 통역", font=f_bold(28), fill=INK, anchor="mm")
    d.text((880, 62), "V8 — 통째로 번역 (JIT)", font=f_bold(28), fill=BLUE, anchor="mm")
    d.line([590, 100, 590, 500], fill=DIVIDER, width=2)
    for i in range(3):
        y = 140 + i * 110
        d.rectangle([120, y, 280, y + 60], outline=GRAY, width=3)
        d.text((200, y + 30), f"{i + 1}번째 줄", font=f_regular(22), fill=GRAY, anchor="mm")
        arrow(d, 300, y + 30, 360, y + 30)
        d.rectangle([380, y, 500, y + 60], outline=GRAY, width=3)
        d.text((440, y + 30), "통역", font=f_regular(22), fill=GRAY, anchor="mm")
    d.text((300, 520), "문장마다 멈춘다 — 느리다", font=f_regular(24), fill=INK, anchor="mm")
    d.rectangle([660, 150, 830, 400], outline=INK, width=4)
    d.text((745, 250), "코드", font=f_bold(26), fill=INK, anchor="mm")
    d.text((745, 290), "전체", font=f_bold(26), fill=INK, anchor="mm")
    arrow(d, 850, 275, 930, 275, color=BLUE, width=6, head=18)
    d.rectangle([950, 150, 1120, 400], outline=BLUE, width=5)
    d.text((1035, 250), "기계어", font=f_bold(26), fill=BLUE, anchor="mm")
    d.text((1035, 290), "즉시 실행", font=f_regular(24), fill=BLUE, anchor="mm")
    d.text((880, 520), "책 전체를 미리 번역해 두고 읽는다 — 수십 배 빠르다",
           font=f_regular(24), fill=BLUE, anchor="mm")
    signature(d, "07")
    img.save(os.path.join(HERE, "07-1-jit.png"))


def img_07_2_share():
    img, d = new_canvas()
    d.text((600, 62), "왕좌의 교체 (점유율 흐름 모식도)", font=f_bold(34), fill=INK, anchor="mm")
    d.line([180, 470, 1080, 470], fill=GRAY, width=3)
    ie = [(220, 170), (420, 260), (850, 440)]
    ch = [(220, 430), (420, 260), (700, 200), (1040, 190)]
    for i in range(len(ie) - 1):
        d.line([ie[i][0], ie[i][1], ie[i + 1][0], ie[i + 1][1]], fill=GRAY, width=5)
    for i in range(len(ch) - 1):
        d.line([ch[i][0], ch[i][1], ch[i + 1][0], ch[i + 1][1]], fill=BLUE, width=6)
    cross_mark(d, 850, 440, r=12, width=5)
    node(d, 420, 260, r=10, outline=INK, width=4)
    d.text((250, 145), "IE", font=f_bold(26), fill=GRAY, anchor="mm")
    d.text((1040, 155), "Chrome 약 65%", font=f_bold(24), fill=BLUE, anchor="rm")
    d.text((420, 225), "2012 역전", font=f_regular(22), fill=INK, anchor="mm")
    for x, yr in ((220, "2008"), (420, "2012"), (850, "2022"), (1040, "2026")):
        d.text((x, 500), yr, font=f_regular(22), fill=GRAY, anchor="mm")
    d.text((600, 560), "IE는 2022년 공식 지원 종료, Chrome은 현재 세계 1위 (수치: StatCounter)",
           font=f_regular(22), fill=INK, anchor="mm")
    signature(d, "07")
    img.save(os.path.join(HERE, "07-2-browser-share.png"))


def img_08_1_jquery():
    img, d = new_canvas()
    d.text((600, 62), "사투리 지옥을 끝낸 통역사", font=f_bold(34), fill=INK, anchor="mm")
    d.rounded_rectangle([460, 110, 740, 180], radius=10, outline=INK, width=4)
    d.text((600, 145), "코드 한 벌 (표준어)", font=f_bold(24), fill=INK, anchor="mm")
    arrow(d, 600, 195, 600, 245, color=GRAY, width=4)
    d.rounded_rectangle([440, 260, 760, 335], radius=10, fill=BLUE)
    d.text((600, 297), "jQuery — 통역사", font=f_bold(28), fill=BG, anchor="mm")
    for x in (300, 600, 900):
        arrow(d, 600 if x == 600 else (520 if x == 300 else 680), 350, x, 405, color=GRAY, width=4)
    for x, name in ((300, "IE 사투리"), (600, "Firefox 사투리"), (900, "그 외 브라우저")):
        d.rounded_rectangle([x - 130, 415, x + 130, 480], radius=10, outline=GRAY, width=3)
        d.text((x, 447), name, font=f_regular(22), fill=INK, anchor="mm")
    d.text((600, 540), "개발자는 표준어만, 사투리 통역은 jQuery가 — 지금도 전 세계 웹사이트 67.3%에서 현역",
           font=f_regular(23), fill=INK, anchor="mm")
    d.text((600, 575), "(W3Techs, 2026.7)", font=f_regular(20), fill=GRAY, anchor="mm")
    signature(d, "08")
    img.save(os.path.join(HERE, "08-1-jquery-translator.png"))


def img_08_2_runtime():
    img, d = new_canvas()
    d.text((600, 62), "런타임 — 코드를 실행해 주는 플레이어", font=f_bold(34), fill=INK, anchor="mm")
    d.text((300, 120), "2008년까지: 브라우저 안에서만", font=f_bold(24), fill=INK, anchor="mm")
    d.text((880, 120), "Node.js 이후: 어디서든", font=f_bold(24), fill=BLUE, anchor="mm")
    d.line([590, 100, 590, 500], fill=DIVIDER, width=2)
    _browser_frame(d, 150, 160, 450, 420)
    d.ellipse([255, 240, 345, 330], fill=BLUE)
    d.text((300, 285), "JS", font=f_bold(30), fill=BG, anchor="mm")
    d.text((300, 460), "유일한 실행 장소", font=f_regular(22), fill=GRAY, anchor="mm")
    for x, name in ((730, "서버"), (880, "내 컴퓨터"), (1030, "개발 도구")):
        d.rounded_rectangle([x - 65, 180, x + 65, 380], radius=10, outline=GRAY, width=3)
        d.text((x, 220), name, font=f_regular(22), fill=INK, anchor="mm")
        d.ellipse([x - 35, 260, x + 35, 330], fill=BLUE)
        d.text((x, 295), "JS", font=f_bold(24), fill=BG, anchor="mm")
    d.text((880, 460), "같은 코드, 새 플레이어들", font=f_regular(22), fill=BLUE, anchor="mm")
    d.text((600, 540), "음악(코드)은 그대로, 플레이어(런타임)가 늘었다 — JS가 만능 언어가 된 순간",
           font=f_regular(24), fill=INK, anchor="mm")
    signature(d, "08")
    img.save(os.path.join(HERE, "08-2-runtime.png"))


def img_09_1_jenga():
    img, d = new_canvas()
    d.text((600, 62), "11줄이 빠지자 생긴 일 — 2016 left-pad 사태", font=f_bold(32), fill=INK, anchor="mm")
    d.rounded_rectangle([380, 120, 820, 200], radius=10, outline=INK, width=4)
    d.text((600, 160), "페이스북 · 넷플릭스 · 페이팔의 서비스", font=f_bold(24), fill=INK, anchor="mm")
    d.line([600, 200, 600, 240], fill=GRAY, width=4)
    d.rounded_rectangle([340, 240, 860, 320], radius=10, outline=GRAY, width=3)
    d.text((600, 280), "수천 개의 코드 부품 (부품의 부품)", font=f_regular(24), fill=INK, anchor="mm")
    d.line([600, 320, 600, 360], fill=GRAY, width=4)
    dashed_line(d, 480, 360, 640, 360, color=GRAY, width=3)
    dashed_line(d, 480, 430, 640, 430, color=GRAY, width=3)
    dashed_line(d, 480, 360, 480, 430, color=GRAY, width=3)
    dashed_line(d, 640, 360, 640, 430, color=GRAY, width=3)
    d.text((560, 395), "빈 자리", font=f_regular(22), fill=GRAY, anchor="mm")
    arrow(d, 660, 395, 740, 395, color=RED, width=4)
    d.rounded_rectangle([760, 360, 1000, 430], radius=10, outline=RED, width=4)
    d.text((880, 383), "left-pad — 단 11줄", font=f_bold(22), fill=RED, anchor="mm")
    d.text((880, 412), "개발자가 삭제함", font=f_regular(20), fill=RED, anchor="mm")
    d.text((600, 500), "받침돌 하나가 사라지자 탑 전체가 흔들렸다",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((600, 540), "npm은 몇 시간 만에 강제 복구하고, 배포된 부품의 삭제 규정을 바꿨다",
           font=f_regular(22), fill=GRAY, anchor="mm")
    signature(d, "09")
    img.save(os.path.join(HERE, "09-1-leftpad-jenga.png"))


def img_09_2_lib_vs_fw():
    img, d = new_canvas()
    d.text((300, 62), "라이브러리 = 반찬가게", font=f_bold(28), fill=INK, anchor="mm")
    d.text((880, 62), "프레임워크 = 밀키트", font=f_bold(28), fill=INK, anchor="mm")
    d.line([590, 100, 590, 480], fill=DIVIDER, width=2)
    for i in range(6):
        x = 130 + (i % 3) * 120
        y = 140 + (i // 3) * 110
        if i == 4:
            d.rounded_rectangle([x, y, x + 100, y + 90], radius=8, outline=BLUE, width=4)
            d.text((x + 50, y + 45), "선택", font=f_bold(22), fill=BLUE, anchor="mm")
        else:
            d.rounded_rectangle([x, y, x + 100, y + 90], radius=8, outline=GRAY, width=3)
    d.text((300, 400), "필요한 반찬(기능)만 골라 담는다", font=f_regular(23), fill=INK, anchor="mm")
    d.text((300, 435), "예: jQuery, left-pad", font=f_regular(21), fill=GRAY, anchor="mm")
    d.rounded_rectangle([700, 130, 1060, 360], radius=12, outline=BLUE, width=4)
    for i, t in enumerate(("정해진 재료", "정해진 순서", "완성된 틀")):
        d.rounded_rectangle([730, 155 + i * 70, 1030, 210 + i * 70], radius=8, outline=GRAY, width=3)
        d.text((880, 182 + i * 70), t, font=f_regular(22), fill=INK, anchor="mm")
    d.text((880, 400), "재료와 순서가 다 정해져 있다 — 조립만 하면 완성", font=f_regular(23), fill=INK, anchor="mm")
    d.text((880, 435), "예: Bootstrap", font=f_regular(21), fill=GRAY, anchor="mm")
    d.text((600, 530), "밀키트의 대가는 획일화 — 그래서 2017년 Tailwind는 다시 잘게 쪼갠 블록으로",
           font=f_regular(22), fill=GRAY, anchor="mm")
    signature(d, "09")
    img.save(os.path.join(HERE, "09-2-library-vs-framework.png"))


def img_10_1_state():
    img, d = new_canvas()
    d.text((300, 62), "과거 — 사람이 일일이 갱신", font=f_bold(26), fill=INK, anchor="mm")
    d.text((880, 62), "React — 장부만 고치면 자동", font=f_bold(26), fill=BLUE, anchor="mm")
    d.line([590, 100, 590, 500], fill=DIVIDER, width=2)
    d.rounded_rectangle([120, 250, 260, 330], radius=10, outline=INK, width=4)
    d.text((190, 290), "데이터", font=f_bold(24), fill=INK, anchor="mm")
    for i, y in enumerate((160, 260, 360)):
        d.rounded_rectangle([380, y, 520, y + 60], radius=8, outline=GRAY, width=3)
        d.text((450, y + 30), f"화면 {i + 1}", font=f_regular(22), fill=INK, anchor="mm")
    d.line([260, 280, 380, 190], fill=GRAY, width=3)
    d.line([260, 290, 380, 290], fill=GRAY, width=3)
    dashed_line(d, 260, 300, 380, 390, color=RED, width=3)
    cross_mark(d, 320, 345, r=10, width=4)
    d.text((300, 470), "하나만 빼먹어도 화면이 어긋난다 (3 vs 2)", font=f_regular(22), fill=RED, anchor="mm")
    d.rounded_rectangle([650, 250, 770, 330], radius=10, outline=INK, width=4)
    d.text((710, 290), "상태", font=f_bold(24), fill=INK, anchor="mm")
    arrow(d, 785, 290, 835, 290, color=BLUE, width=4)
    d.rounded_rectangle([845, 245, 965, 335], radius=10, fill=BLUE)
    d.text((905, 290), "React", font=f_bold(26), fill=BG, anchor="mm")
    for y in (160, 260, 360):
        arrow(d, 975, 290 if y == 260 else (270 if y == 160 else 310), 1030, y + 30, color=BLUE, width=3)
        d.rounded_rectangle([1035, y, 1150, y + 60], radius=8, outline=BLUE, width=3)
        d.text((1092, y + 30), "화면", font=f_regular(22), fill=INK, anchor="mm")
    d.text((880, 470), "장부(상태)만 고치면 화면 전부를 알아서 갱신", font=f_regular(22), fill=BLUE, anchor="mm")
    d.text((600, 545), "2013년 React의 발상 전환 — 화면 맞추기를 사람 손에서 프레임워크로",
           font=f_regular(24), fill=INK, anchor="mm")
    signature(d, "10")
    img.save(os.path.join(HERE, "10-1-state-auto.png"))


def img_10_2_build():
    img, d = new_canvas()
    d.text((600, 62), "빌드 — 내가 쓴 코드와 배달되는 코드는 다르다", font=f_bold(32), fill=INK, anchor="mm")
    for i in range(9):
        x = 130 + (i % 3) * 90
        y = 160 + (i // 3) * 90
        d.rectangle([x, y, x + 70, y + 70], outline=GRAY, width=3)
    d.text((250, 460), "수백 개의 파일 · 최신 문법", font=f_regular(22), fill=INK, anchor="mm")
    arrow(d, 440, 290, 520, 290, color=GRAY, width=5)
    d.rounded_rectangle([540, 190, 820, 390], radius=12, fill=BLUE)
    d.text((680, 255), "BUILD 공장", font=f_bold(30), fill=BG, anchor="mm")
    d.text((680, 305), "번역 · 묶기 · 솎아내기", font=f_regular(24), fill=BG, anchor="mm")
    arrow(d, 840, 290, 920, 290, color=GRAY, width=5)
    d.rectangle([950, 220, 1090, 290], outline=BLUE, width=4)
    d.rectangle([950, 310, 1090, 360], outline=BLUE, width=4)
    d.text((1020, 460), "몇 개의 압축 파일", font=f_regular(22), fill=BLUE, anchor="mm")
    d.text((600, 540), "구형 브라우저용 번역, 파일 묶기, 안 쓰는 부품 제거 — 손님에게는 완제품만 배달된다",
           font=f_regular(23), fill=INK, anchor="mm")
    signature(d, "10")
    img.save(os.path.join(HERE, "10-2-build-factory.png"))


def img_11_1_csr_ssr():
    img, d = new_canvas()
    d.text((300, 62), "SPA — 그때그때 그리기", font=f_bold(28), fill=INK, anchor="mm")
    d.text((880, 62), "SSR — 미리 그려 보내기", font=f_bold(28), fill=BLUE, anchor="mm")
    d.line([590, 100, 590, 500], fill=DIVIDER, width=2)
    _browser_frame(d, 130, 120, 470, 400)
    d.ellipse([270, 230, 330, 290], outline=LGRAY, width=6)
    d.text((300, 340), "(아직 빈 화면)", font=f_regular(22), fill=LGRAY, anchor="mm")
    d.text((300, 445), "검색 로봇: \"빈 종이만 보이는데?\"", font=f_regular(23), fill=RED, anchor="mm")
    d.text((300, 480), "사람에겐 매끄럽지만, 검색에 안 잡힌다", font=f_regular(21), fill=GRAY, anchor="mm")
    _browser_frame(d, 710, 120, 1050, 400)
    d.line([740, 190, 1020, 190], fill=INK, width=6)
    for y in (230, 264, 298, 332):
        d.line([740, y, 1020, y], fill=LGRAY, width=5)
    d.text((880, 445), "검색 로봇: \"내용 잘 읽었습니다\"", font=f_regular(23), fill=BLUE, anchor="mm")
    d.text((880, 480), "대신 서버가 매번 그림을 그린다 (부담)", font=f_regular(21), fill=GRAY, anchor="mm")
    d.text((600, 545), "그래서 오늘의 표준은 두 방식을 섞는 하이브리드 (대표: Next.js)",
           font=f_regular(24), fill=INK, anchor="mm")
    signature(d, "11")
    img.save(os.path.join(HERE, "11-1-csr-vs-ssr.png"))


def img_11_2_og():
    img, d = new_canvas()
    d.text((600, 62), "링크 미리보기의 정체 — OG 태그", font=f_bold(34), fill=INK, anchor="mm")
    d.rounded_rectangle([180, 130, 700, 195], radius=20, outline=GRAY, width=3)
    d.text((210, 162), "https://tech-history.example/01", font=f_mono(22), fill=GRAY, anchor="lm")
    d.rounded_rectangle([180, 220, 700, 470], radius=12, outline=INK, width=4)
    d.rectangle([184, 224, 696, 350], fill=BLUE)
    d.text((440, 287), "대표 이미지", font=f_bold(24), fill=BG, anchor="mm")
    d.text((210, 385), "인터넷의 첫마디는 \"LO\"였다", font=f_bold(24), fill=INK, anchor="lm")
    d.text((210, 425), "기술의 역사 시리즈 1편…", font=f_regular(22), fill=GRAY, anchor="lm")
    d.text((870, 250), "og:image", font=f_mono(24), fill=BLUE, anchor="lm")
    d.line([740, 280, 860, 255], fill=BLUE, width=3)
    d.text((870, 380), "og:title", font=f_mono(24), fill=BLUE, anchor="lm")
    d.line([710, 385, 860, 385], fill=BLUE, width=3)
    d.text((870, 425), "og:description", font=f_mono(24), fill=BLUE, anchor="lm")
    d.line([710, 425, 860, 425], fill=BLUE, width=3)
    d.text((600, 530), "페이지가 적어둔 자기소개(OG 태그)를 수집 로봇이 읽어가 미리보기가 된다",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((600, 566), "로봇이 읽으려면 완성된 화면이 필요 — SSR이 필요한 대표적 이유",
           font=f_regular(22), fill=GRAY, anchor="mm")
    signature(d, "11")
    img.save(os.path.join(HERE, "11-2-og-preview.png"))


ALL_IMAGES = [
    img_01_1_lo, img_01_2_star_vs_mesh, img_01_3_packet_header,
    img_02_1_flag_day, img_02_2_common_language, img_02_3_tcp_ip_roles,
    img_03_1_vague, img_03_2_web_trio,
    img_04_1_text_vs_image, img_04_2_ipo,
    img_05_1_ten_days, img_05_2_dom_map,
    img_06_1_bundling, img_06_2_html_css_js,
    img_07_1_jit, img_07_2_share,
    img_08_1_jquery, img_08_2_runtime,
    img_09_1_jenga, img_09_2_lib_vs_fw,
    img_10_1_state, img_10_2_build,
    img_11_1_csr_ssr, img_11_2_og,
]

if __name__ == "__main__":
    for fn in ALL_IMAGES:
        fn()
    print(f"생성 완료: {len(ALL_IMAGES)}장 PNG (1200x630)")
