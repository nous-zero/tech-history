# -*- coding: utf-8 -*-
"""tech-history 02 백엔드 발행 이미지 생성기.

posts/frontend/images/generate_images.py의 톤앤매너 코드를 그대로 승계:
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
    draw.text((1150, 612), f"© 2026 박정훈 · tech-history backend {episode}",
              font=f_regular(18), fill=LGRAY, anchor="rs")


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


def _browser_frame(d, x1, y1, x2, y2):
    d.rectangle([x1, y1, x2, y2], outline=GRAY, width=3, fill=BG)
    d.line([x1, y1 + 36, x2, y1 + 36], fill=GRAY, width=3)
    for cx in (x1 + 18, x1 + 40, x1 + 62):
        d.ellipse([cx - 6, y1 + 12, cx + 6, y1 + 24], outline=GRAY, width=2)


def _person(d, cx, cy, r=16, color=GRAY, width=4):
    d.ellipse([cx - r, cy - r * 2, cx + r, cy], outline=color, width=width)
    d.arc([cx - r * 2, cy - 4, cx + r * 2, cy + r * 3], 200, 340,
          fill=color, width=width)


# ── 01 CGI ──────────────────────────────────────────────────────

def img_01_1():
    img, d = new_canvas()
    d.text((300, 62), "정적 웹 — 자판기", font=f_bold(30), fill=INK, anchor="mm")
    d.text((880, 62), "CGI — 서버 뒤의 요리사", font=f_bold(30), fill=BLUE, anchor="mm")
    d.line([590, 100, 590, 500], fill=DIVIDER, width=2)
    d.rounded_rectangle([170, 120, 430, 440], radius=12, outline=INK, width=4)
    for i in range(6):
        x = 205 + (i % 2) * 115
        y = 150 + (i // 2) * 80
        d.rectangle([x, y, x + 90, y + 55], outline=GRAY, width=3)
        d.text((x + 45, y + 27), "HTML", font=f_mono(18), fill=GRAY, anchor="mm")
    d.text((300, 480), "누가 눌러도 미리 만든 같은 파일이 나온다",
           font=f_regular(23), fill=INK, anchor="mm")
    d.rounded_rectangle([660, 160, 830, 400], radius=12, outline=GRAY, width=4)
    d.text((745, 200), "웹 서버", font=f_bold(24), fill=INK, anchor="mm")
    d.text((745, 240), "(배달부)", font=f_regular(20), fill=GRAY, anchor="mm")
    arrow(d, 840, 280, 920, 280, color=BLUE, width=5)
    d.ellipse([935, 215, 1075, 355], outline=BLUE, width=5)
    d.text((1005, 268), "요리사", font=f_bold(26), fill=BLUE, anchor="mm")
    d.text((1005, 308), "(프로그램)", font=f_regular(20), fill=GRAY, anchor="mm")
    d.text((880, 445), "요청이 오면 그 자리에서 HTML을 새로 조립",
           font=f_regular(23), fill=BLUE, anchor="mm")
    d.text((600, 545), "1993년 CGI — 파일을 '꺼내 주는' 웹에서 '새로 만들어 주는' 웹으로",
           font=f_regular(24), fill=INK, anchor="mm")
    signature(d, "01")
    img.save(os.path.join(HERE, "01-1-vending-vs-kitchen.png"))


def img_01_2():
    img, d = new_canvas()
    d.text((600, 62), "CGI의 청구서 — 요청마다 요리사를 새로 채용한다",
           font=f_bold(32), fill=INK, anchor="mm")
    for i in range(3):
        y = 150 + i * 110
        d.text((150, y + 27), f"요청 {i + 1}", font=f_regular(24), fill=INK, anchor="mm")
        arrow(d, 230, y + 27, 330, y + 27)
        d.rounded_rectangle([350, y, 720, y + 56], radius=10, outline=GRAY, width=3)
        d.text((535, y + 28), "프로세스(프로그램 한 벌) 신규 실행",
               font=f_regular(22), fill=INK, anchor="mm")
    d.text((870, 205), "채용", font=f_regular(20), fill=GRAY, anchor="mm")
    d.text((870, 260), "→ 해고", font=f_regular(20), fill=GRAY, anchor="mm")
    d.text((870, 315), "→ 재채용…", font=f_regular(20), fill=RED, anchor="mm")
    dashed_line(d, 150, 480, 1050, 480, color=RED, width=4)
    cross_mark(d, 600, 480, r=14)
    d.text((600, 530), "접속자가 늘면 서버는 요리가 아니라 '채용 비용'으로 주저앉는다",
           font=f_regular(24), fill=RED, anchor="mm")
    signature(d, "01")
    img.save(os.path.join(HERE, "01-2-cgi-process-cost.png"))


# ── 02 쿠키 ─────────────────────────────────────────────────────

def img_02_1():
    img, d = new_canvas()
    d.text((600, 62), "HTTP는 무상태 — 손님을 기억하지 못한다",
           font=f_bold(34), fill=INK, anchor="mm")
    _browser_frame(d, 130, 140, 430, 380)
    d.text((280, 270), "브라우저", font=f_bold(26), fill=INK, anchor="mm")
    d.rounded_rectangle([770, 140, 1070, 380], radius=12, outline=GRAY, width=4)
    d.text((920, 270), "서버", font=f_bold(26), fill=INK, anchor="mm")
    arrow(d, 450, 200, 750, 200, color=GRAY, width=4)
    d.text((600, 175), "요청 1: 장바구니에 담기", font=f_regular(22), fill=INK, anchor="mm")
    arrow(d, 450, 320, 750, 320, color=GRAY, width=4)
    d.text((600, 295), "요청 2: 결제하기", font=f_regular(22), fill=INK, anchor="mm")
    d.text((920, 430), "\"누구시죠? 처음 뵙는데요.\"", font=f_bold(26), fill=RED, anchor="mm")
    d.text((600, 520), "요청 하나가 끝나면 서버는 그 손님이 왔었다는 사실 자체를 잊는다",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((600, 558), "그래서 1994년까지 로그인 유지도, 장바구니도 불가능했다",
           font=f_regular(22), fill=GRAY, anchor="mm")
    signature(d, "02")
    img.save(os.path.join(HERE, "02-1-stateless-http.png"))


def img_02_2():
    img, d = new_canvas()
    d.text((600, 62), "쿠키 — 브라우저에 붙인 메모지", font=f_bold(34), fill=INK, anchor="mm")
    _browser_frame(d, 130, 140, 430, 400)
    d.text((280, 200), "브라우저", font=f_bold(24), fill=INK, anchor="mm")
    d.rounded_rectangle([200, 250, 360, 350], radius=8, fill=BLUE)
    d.text((280, 285), "쿠키", font=f_bold(24), fill=BG, anchor="mm")
    d.text((280, 320), "(작은 메모)", font=f_regular(18), fill=BG, anchor="mm")
    d.rounded_rectangle([770, 140, 1070, 400], radius=12, outline=GRAY, width=4)
    d.text((920, 200), "서버", font=f_bold(24), fill=INK, anchor="mm")
    arrow(d, 750, 240, 450, 240, color=BLUE, width=5)
    d.text((600, 215), "① 응답과 함께 메모를 심는다", font=f_regular(21), fill=BLUE, anchor="mm")
    arrow(d, 450, 330, 750, 330, color=BLUE, width=5)
    d.text((600, 305), "② 갈 때마다 자동으로 다시 내민다", font=f_regular(21), fill=BLUE, anchor="mm")
    d.text((920, 350), "\"아, 아까 그 손님\"", font=f_regular(22), fill=BLUE, anchor="mm")
    d.text((600, 480), "1994년 6월 고안(루 몬툴리, 23세) — 10월 13일 Mosaic Netscape 0.9beta부터 탑재",
           font=f_regular(23), fill=INK, anchor="mm")
    d.text((600, 520), "이름은 메시지가 안에 든 과자, 포춘 쿠키에서",
           font=f_regular(22), fill=GRAY, anchor="mm")
    signature(d, "02")
    img.save(os.path.join(HERE, "02-2-cookie-note.png"))


# ── 03 PHP ─────────────────────────────────────────────────────

def img_03_1():
    img, d = new_canvas()
    d.text((600, 62), "PHP — HTML 문서 안에 코드를 심는다", font=f_bold(34), fill=INK, anchor="mm")
    d.rectangle([150, 130, 500, 450], outline=INK, width=4, fill=BG)
    for y in (175, 210, 350, 390):
        d.line([185, y, 465, y], fill=LGRAY, width=5)
    d.rounded_rectangle([175, 250, 475, 310], radius=8, fill=BLUE)
    d.text((325, 280), "<?php 코드 조각 ?>", font=f_mono(22), fill=BG, anchor="mm")
    d.text((325, 490), "HTML 사이, 필요한 곳에만 코드", font=f_regular(22), fill=INK, anchor="mm")
    arrow(d, 530, 290, 640, 290, color=GRAY, width=5)
    d.text((585, 255), "서버 실행", font=f_regular(20), fill=GRAY, anchor="mm")
    _browser_frame(d, 670, 130, 1050, 450)
    for y in (200, 234, 350, 384):
        d.line([700, y, 1020, y], fill=LGRAY, width=5)
    d.rounded_rectangle([700, 265, 1020, 320], radius=8, outline=BLUE, width=4)
    d.text((860, 292), "코드가 채운 빈칸 (조회수 등)", font=f_regular(20), fill=BLUE, anchor="mm")
    d.text((860, 490), "완성된 페이지가 손님에게", font=f_regular(22), fill=INK, anchor="mm")
    d.text((600, 550), "프로그램 전체를 짜야 했던 CGI와 반대 — 진입장벽이 극적으로 낮아졌다",
           font=f_regular(24), fill=INK, anchor="mm")
    signature(d, "03")
    img.save(os.path.join(HERE, "03-1-php-embed.png"))


def img_03_2():
    img, d = new_canvas()
    d.text((600, 62), "이력서 조회수 세던 도구의 현재 성적표", font=f_bold(34), fill=INK, anchor="mm")
    d.line([200, 420, 1000, 420], fill=GRAY, width=3)
    d.rectangle([280, 150, 520, 420], fill=BLUE)
    d.text((400, 120), "PHP 74.5%", font=f_bold(30), fill=BLUE, anchor="mm")
    d.rectangle([680, 330, 920, 420], outline=GRAY, width=4)
    d.text((800, 300), "그 외 언어 전부", font=f_regular(24), fill=GRAY, anchor="mm")
    d.text((600, 470), "서버사이드 언어가 확인되는 웹사이트 기준 (W3Techs)",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((600, 515), "PHP로 만든 워드프레스 하나가 전체 웹사이트의 43.5%",
           font=f_regular(23), fill=GRAY, anchor="mm")
    signature(d, "03")
    img.save(os.path.join(HERE, "03-2-php-745.png"))


# ── 04 Rails ───────────────────────────────────────────────────

def img_04_1():
    img, d = new_canvas()
    d.text((600, 62), "MVC — 스파게티를 자르는 칼", font=f_bold(34), fill=INK, anchor="mm")
    d.text((160, 180), "사용자", font=f_bold(24), fill=INK, anchor="mm")
    d.text((160, 215), "요청", font=f_regular(22), fill=GRAY, anchor="mm")
    arrow(d, 220, 200, 300, 200, color=GRAY, width=5)
    boxes = [(320, "Controller", "흐름 제어", "주문받는 홀 매니저"),
             (620, "Model", "데이터·로직", "요리하는 주방"),
             (920, "View", "화면 완성", "접시에 담는 플레이팅")]
    for x, name, s1, s2 in boxes:
        d.rounded_rectangle([x, 130, x + 250, 330], radius=12, outline=BLUE, width=4)
        d.text((x + 125, 180), name, font=f_bold(32), fill=BLUE, anchor="mm")
        d.text((x + 125, 235), s1, font=f_bold(24), fill=INK, anchor="mm")
        d.text((x + 125, 285), s2, font=f_regular(21), fill=GRAY, anchor="mm")
    arrow(d, 570, 230, 620, 230, color=GRAY, width=5)
    arrow(d, 870, 230, 920, 230, color=GRAY, width=5)
    d.text((600, 420), "역할을 강제로 갈라놓으면, 섞여서 죽는 스파게티가 사라진다",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((600, 470), "2004년 Ruby on Rails — MVC + '설정보다 관습'으로 15분 만에 블로그를",
           font=f_regular(24), fill=BLUE, anchor="mm")
    d.text((600, 515), "형제들: Spring(2004) · Django(2005) · Laravel(2011)",
           font=f_regular(22), fill=GRAY, anchor="mm")
    signature(d, "04")
    img.save(os.path.join(HERE, "04-1-mvc-restaurant.png"))


def img_04_2():
    img, d = new_canvas()
    d.text((600, 66), "Rails로 돌아가는 쇼피파이 — BFCM 2025", font=f_bold(36), fill=INK, anchor="mm")
    d.rounded_rectangle([120, 140, 580, 400], radius=14, outline=BLUE, width=5)
    d.text((350, 220), "$146억", font=f_bold(64), fill=BLUE, anchor="mm")
    d.text((350, 300), "블랙프라이데이·사이버먼데이", font=f_regular(24), fill=INK, anchor="mm")
    d.text((350, 340), "주말 매출 (전년 대비 +27%)", font=f_regular(24), fill=INK, anchor="mm")
    d.rounded_rectangle([620, 140, 1080, 400], radius=14, outline=GRAY, width=4)
    d.text((850, 220), "분당 $510만", font=f_bold(48), fill=INK, anchor="mm")
    d.text((850, 300), "피크 시간대 처리액", font=f_regular(24), fill=GRAY, anchor="mm")
    d.text((600, 480), "초기 트위터·깃허브·쇼피파이가 Rails에서 태어났고, 쇼피파이는 지금도 Rails",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((600, 522), "(Shopify 공식 보도자료, BFCM 2025)", font=f_regular(20), fill=GRAY, anchor="mm")
    signature(d, "04")
    img.save(os.path.join(HERE, "04-2-shopify-bfcm.png"))


# ── 05 REST·JSON ───────────────────────────────────────────────

def img_05_1():
    img, d = new_canvas()
    d.text((600, 62), "REST — 식당의 표준 주문서", font=f_bold(36), fill=INK, anchor="mm")
    d.rectangle([320, 120, 880, 480], outline=INK, width=4, fill=BG)
    d.text((600, 160), "표준 주문서", font=f_bold(26), fill=INK, anchor="mm")
    d.line([360, 190, 840, 190], fill=DIVIDER, width=3)
    d.text((380, 225), "자원(주소):", font=f_regular(22), fill=GRAY, anchor="lm")
    d.text((560, 225), "/orders/3", font=f_mono(24), fill=BLUE, anchor="lm")
    rows = [("GET", "조회 — 3번 주문 보여줘"),
            ("POST", "생성 — 새 주문 넣어줘"),
            ("PUT", "수정 — 3번 주문 바꿔줘"),
            ("DELETE", "삭제 — 3번 주문 취소해줘")]
    for i, (verb, desc) in enumerate(rows):
        y = 275 + i * 50
        d.rounded_rectangle([380, y - 18, 500, y + 18], radius=6, fill=BLUE)
        d.text((440, y), verb, font=f_mono(20), fill=BG, anchor="mm")
        d.text((520, y), desc, font=f_regular(21), fill=INK, anchor="lm")
    d.text((600, 530), "새 기술이 아니라 'HTTP를 원래 설계대로 쓰자'는 원칙 — 2000년 필딩 박사논문",
           font=f_regular(23), fill=INK, anchor="mm")
    d.text((600, 566), "25년 뒤에도 API의 93%가 REST (Postman 2025)", font=f_regular(21), fill=BLUE, anchor="mm")
    signature(d, "05")
    img.save(os.path.join(HERE, "05-1-rest-order-sheet.png"))


def img_05_2():
    img, d = new_canvas()
    d.text((300, 62), "XML — 서류 뭉치", font=f_bold(30), fill=INK, anchor="mm")
    d.text((880, 62), "JSON — 쪽지 한 장", font=f_bold(30), fill=BLUE, anchor="mm")
    d.line([590, 100, 590, 500], fill=DIVIDER, width=2)
    xml_lines = ["<user>", "  <name>Kim</name>", "  <age>30</age>", "</user>"]
    d.rectangle([130, 130, 470, 420], outline=GRAY, width=4)
    for i, t in enumerate(xml_lines):
        d.text((160, 180 + i * 55), t, font=f_mono(26), fill=GRAY, anchor="lm")
    d.text((300, 465), "여닫는 태그가 앞뒤로 중복 — 무겁고 해석이 번거롭다",
           font=f_regular(21), fill=INK, anchor="mm")
    json_lines = ['{', '  "name": "Kim",', '  "age": 30', '}']
    d.rectangle([710, 130, 1050, 420], outline=BLUE, width=4)
    for i, t in enumerate(json_lines):
        d.text((740, 180 + i * 55), t, font=f_mono(26), fill=BLUE, anchor="lm")
    d.text((880, 465), "키&값 쌍 그대로 — 사람도 기계도 읽기 쉽다",
           font=f_regular(21), fill=INK, anchor="mm")
    d.text((600, 545), "2002년 json.org → 2006년 RFC 4627 — REST와 한 쌍이 되어 웹 API 표준으로",
           font=f_regular(23), fill=INK, anchor="mm")
    signature(d, "05")
    img.save(os.path.join(HERE, "05-2-json-vs-xml.png"))


# ── 06 AJAX ────────────────────────────────────────────────────

def img_06_1():
    img, d = new_canvas()
    d.text((300, 62), "그때까지 — 전체 새로고침", font=f_bold(28), fill=INK, anchor="mm")
    d.text((880, 62), "AJAX — 필요한 부분만", font=f_bold(28), fill=BLUE, anchor="mm")
    d.line([590, 100, 590, 500], fill=DIVIDER, width=2)
    _browser_frame(d, 130, 110, 470, 400)
    d.rectangle([160, 170, 440, 370], fill=(243, 244, 246))
    d.text((300, 270), "흰 화면…", font=f_regular(26), fill=LGRAY, anchor="mm")
    d.text((300, 445), "클릭 → 깜빡 → 페이지 전체를 다시 받는다",
           font=f_regular(22), fill=INK, anchor="mm")
    d.text((300, 480), "데이터 하나 바꾸는 데도 전부 다시", font=f_regular(21), fill=RED, anchor="mm")
    _browser_frame(d, 710, 110, 1050, 400)
    for y in (180, 214, 330, 364):
        d.line([740, y, 1020, y], fill=LGRAY, width=5)
    d.rounded_rectangle([740, 245, 1020, 305], radius=8, outline=BLUE, width=5)
    d.text((880, 275), "이 부분만 갱신", font=f_bold(22), fill=BLUE, anchor="mm")
    d.text((880, 445), "화면 뒤에서 몰래 서버와 통신", font=f_regular(22), fill=BLUE, anchor="mm")
    d.text((880, 480), "Gmail(2004)·구글맵(2005)이 위력을 증명", font=f_regular(21), fill=GRAY, anchor="mm")
    d.text((600, 545), "2005년 2월, 제시 제임스 가렛이 이 기법에 이름을 붙였다 — AJAX",
           font=f_regular(24), fill=INK, anchor="mm")
    signature(d, "06")
    img.save(os.path.join(HERE, "06-1-reload-vs-ajax.png"))


def img_06_2():
    img, d = new_canvas()
    d.text((600, 62), "백엔드의 재정의 — 화면 제조기에서 API 창구로",
           font=f_bold(32), fill=INK, anchor="mm")
    d.rounded_rectangle([140, 150, 340, 300], radius=12, outline=GRAY, width=4)
    d.text((240, 200), "서버", font=f_bold(26), fill=INK, anchor="mm")
    d.text((240, 250), "(과거)", font=f_regular(20), fill=GRAY, anchor="mm")
    arrow(d, 360, 225, 460, 225, color=GRAY, width=4)
    d.text((410, 195), "HTML", font=f_regular(20), fill=GRAY, anchor="mm")
    _browser_frame(d, 480, 150, 560, 300)
    d.text((350, 345), "완성된 화면을 만들어 보냈다", font=f_regular(21), fill=GRAY, anchor="mm")
    d.rounded_rectangle([680, 150, 880, 300], radius=12, outline=BLUE, width=5)
    d.text((780, 200), "서버", font=f_bold(26), fill=BLUE, anchor="mm")
    d.text((780, 250), "(API 창구)", font=f_regular(20), fill=BLUE, anchor="mm")
    arrow(d, 900, 190, 990, 190, color=BLUE, width=4)
    arrow(d, 900, 265, 990, 265, color=BLUE, width=4)
    d.text((945, 160), "JSON", font=f_regular(20), fill=BLUE, anchor="mm")
    d.rounded_rectangle([1010, 160, 1110, 220], radius=8, outline=GRAY, width=3)
    d.text((1060, 190), "웹", font=f_regular(22), fill=INK, anchor="mm")
    d.rounded_rectangle([1010, 240, 1110, 300], radius=8, outline=GRAY, width=3)
    d.text((1060, 270), "앱", font=f_regular(22), fill=INK, anchor="mm")
    d.text((895, 345), "데이터만 내주고, 화면은 각자 그린다", font=f_regular(21), fill=BLUE, anchor="mm")
    d.text((600, 440), "2007년 아이폰이 전환을 가속 — 모바일 앱에 필요한 건 HTML이 아니라 데이터",
           font=f_regular(23), fill=INK, anchor="mm")
    d.text((600, 485), "같은 서버가 웹과 앱을 동시에 섬기는 유일한 길이 API였다",
           font=f_regular(23), fill=INK, anchor="mm")
    signature(d, "06")
    img.save(os.path.join(HERE, "06-2-server-redefined.png"))


# ── 07 세션·JWT·해싱 ───────────────────────────────────────────

def img_07_1():
    img, d = new_canvas()
    d.text((600, 62), "상태 관리 30년 — 쿠키, 세션, JWT", font=f_bold(34), fill=INK, anchor="mm")
    cols = [(210, "쿠키 (1994)", "브라우저에 데이터 저장",
             "낳은 문제: 위변조 가능"),
            (600, "세션", "정보는 서버가, 손님엔 번호표만",
             "낳은 문제: 서버 여러 대면 복잡"),
            (990, "JWT (2015)", "서명된 증명서를 손님이 소지",
             "낳은 문제: 중간 무효화 난제")]
    for x, name, s1, s2 in cols:
        d.rounded_rectangle([x - 175, 140, x + 175, 380], radius=12,
                            outline=BLUE if "JWT" in name else GRAY, width=4)
        d.text((x, 190), name, font=f_bold(28),
               fill=BLUE if "JWT" in name else INK, anchor="mm")
        d.text((x, 255), s1, font=f_regular(20), fill=INK, anchor="mm")
        d.text((x, 330), s2, font=f_regular(19), fill=RED, anchor="mm")
    arrow(d, 395, 260, 415, 260, color=GRAY, width=4)
    arrow(d, 785, 260, 805, 260, color=GRAY, width=4)
    d.text((600, 440), "은행 번호표(세션)에서 공증 도장 찍힌 통행증(JWT)으로",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((600, 485), "어느 서버가 받아도 도장만 검사하면 된다 — 서버를 마음껏 늘릴 수 있는 이유",
           font=f_regular(23), fill=BLUE, anchor="mm")
    d.text((600, 528), "상태를 어디에 둘 것인가 — 완벽한 답은 없고 트레이드오프만 있다",
           font=f_regular(21), fill=GRAY, anchor="mm")
    signature(d, "07")
    img.save(os.path.join(HERE, "07-1-cookie-session-jwt.png"))


def img_07_2():
    img, d = new_canvas()
    d.text((600, 62), "2012 링크드인 유출 — 해싱을 '어떻게' 하느냐까지가 보안",
           font=f_bold(31), fill=INK, anchor="mm")
    stats = [(280, "1억 1,700만", "유출된 비밀번호"),
             (600, "72시간", "해독에 걸린 시간"),
             (920, "90%", "풀린 비율")]
    for x, big, small in stats:
        d.rounded_rectangle([x - 150, 140, x + 150, 330], radius=12, outline=RED, width=5)
        d.text((x, 210), big, font=f_bold(40), fill=RED, anchor="mm")
        d.text((x, 285), small, font=f_regular(22), fill=INK, anchor="mm")
    d.text((600, 400), "원인: 낡은 SHA-1 방식 + 소금(salt) 없는 저장",
           font=f_bold(26), fill=INK, anchor="mm")
    d.text((600, 450), "소금 = 해싱 전에 섞는 무작위 값 — 같은 비밀번호도 다른 결과가 나오게 하는 장치",
           font=f_regular(22), fill=GRAY, anchor="mm")
    d.text((600, 495), "소금이 없으면 미리 계산해 둔 정답표 대조 공격이 통한다",
           font=f_regular(22), fill=GRAY, anchor="mm")
    d.text((600, 550), "(Krebs on Security 2016.5 / arXiv:1703.06586)", font=f_regular(19), fill=LGRAY, anchor="mm")
    signature(d, "07")
    img.save(os.path.join(HERE, "07-2-linkedin-crack.png"))


# ── 08 C10K·Node ───────────────────────────────────────────────

def img_08_1():
    img, d = new_canvas()
    d.text((300, 62), "스레드 모델 — 테이블마다 전담 웨이터", font=f_bold(26), fill=INK, anchor="mm")
    d.text((880, 62), "이벤트 루프 — 웨이터 한 명", font=f_bold(26), fill=BLUE, anchor="mm")
    d.line([590, 100, 590, 500], fill=DIVIDER, width=2)
    for i in range(3):
        y = 150 + i * 110
        node(d, 170, y + 20, r=18)
        d.text((170, y + 62), f"테이블{i + 1}", font=f_regular(18), fill=GRAY, anchor="mm")
        _person(d, 300, y + 30, r=13)
        d.text((300, y + 72), f"웨이터{i + 1}", font=f_regular(18), fill=GRAY, anchor="mm")
        d.text((420, y + 25), "대기 중…", font=f_regular(20), fill=RED, anchor="mm")
    d.text((300, 500), "1만 명이면 웨이터 1만 명 — 월급(메모리)과", font=f_regular(21), fill=INK, anchor="mm")
    d.text((300, 532), "교대 비용(문맥 교환)이 폭증한다", font=f_regular(21), fill=INK, anchor="mm")
    for i, y in enumerate((150, 260, 370)):
        node(d, 700, y + 20, r=18)
        arrow(d, 730, y + 20, 810, 260, color=GRAY, width=3)
    _person(d, 850, 270, r=16, color=BLUE, width=5)
    d.text((850, 330), "웨이터 1명", font=f_bold(20), fill=BLUE, anchor="mm")
    arrow(d, 900, 265, 985, 265, color=BLUE, width=5)
    d.rounded_rectangle([1000, 210, 1130, 320], radius=10, outline=GRAY, width=4)
    d.text((1065, 250), "주방", font=f_bold(24), fill=INK, anchor="mm")
    d.text((1065, 290), "(I/O)", font=f_regular(19), fill=GRAY, anchor="mm")
    d.text((880, 500), "주문만 받고 요리는 주방에 — 완성 알림(이벤트)이 오면 서빙",
           font=f_regular(21), fill=BLUE, anchor="mm")
    d.text((880, 532), "기다림이 없어 한 명이 1만 테이블을 받는다", font=f_regular(21), fill=BLUE, anchor="mm")
    d.text((600, 585), "1999년 C10K 문제의 답 — 2009년 Node.js", font=f_regular(22), fill=INK, anchor="mm")
    signature(d, "08")
    img.save(os.path.join(HERE, "08-1-waiter-model.png"))


def img_08_2():
    img, d = new_canvas()
    d.text((600, 62), "페이팔의 Node.js 전환 성적표 (2013)", font=f_bold(36), fill=INK, anchor="mm")
    stats = [(240, "35%", "응답 시간 단축"),
             (480, "33%", "코드 감소"),
             (720, "40%", "파일 감소"),
             (960, "2배", "초당 처리 요청")]
    for x, big, small in stats:
        d.rounded_rectangle([x - 105, 160, x + 105, 380], radius=12, outline=BLUE, width=5)
        d.text((x, 240), big, font=f_bold(48), fill=BLUE, anchor="mm")
        d.text((x, 325), small, font=f_regular(21), fill=INK, anchor="mm")
    d.text((600, 450), "계정 개요 페이지를 Java에서 Node.js로 재작성한 결과",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((600, 495), "(PayPal 기술 블로그 자체 측정 — 단일 사례임에 유의)",
           font=f_regular(22), fill=GRAY, anchor="mm")
    signature(d, "08")
    img.save(os.path.join(HERE, "08-2-paypal-node.png"))


# ── 09 확장 ────────────────────────────────────────────────────

def img_09_1():
    img, d = new_canvas()
    d.text((300, 62), "수직 확장 — 더 큰 트럭 한 대", font=f_bold(27), fill=INK, anchor="mm")
    d.text((880, 62), "수평 확장 — 트럭 여러 대", font=f_bold(27), fill=BLUE, anchor="mm")
    d.line([590, 100, 590, 500], fill=DIVIDER, width=2)
    d.rounded_rectangle([170, 140, 430, 380], radius=12, outline=GRAY, width=6)
    d.text((300, 240), "괴물 서버", font=f_bold(30), fill=INK, anchor="mm")
    d.text((300, 300), "1대", font=f_bold(26), fill=GRAY, anchor="mm")
    cross_mark(d, 300, 355, r=13)
    d.text((300, 440), "성능엔 물리적 상한 · 2배 성능은 2배보다 비쌈",
           font=f_regular(20), fill=INK, anchor="mm")
    d.text((300, 472), "이 한 대가 죽으면 전체가 죽는다(단일 장애점)",
           font=f_regular(20), fill=RED, anchor="mm")
    node(d, 880, 170, r=24, outline=BLUE, width=5)
    d.text((880, 130), "로드 밸런서 (배차 담당)", font=f_bold(20), fill=BLUE, anchor="mm")
    for i, x in enumerate((720, 830, 940, 1050)):
        arrow(d, 880, 198, x + 25, 265, color=BLUE, width=3)
        d.rounded_rectangle([x - 25, 270, x + 75, 380], radius=8,
                            outline=GRAY if i == 2 else BLUE, width=4)
        d.text((x + 25, 310), "서버", font=f_regular(20), fill=INK, anchor="mm")
        if i == 2:
            cross_mark(d, x + 25, 345, r=10, width=4)
        else:
            d.text((x + 25, 345), "정상", font=f_regular(17), fill=BLUE, anchor="mm")
    d.text((880, 440), "요청을 골고루 분산 — 한 대가 죽어도 서비스는 계속",
           font=f_regular(20), fill=BLUE, anchor="mm")
    d.text((880, 472), "트래픽 따라 늘렸다 줄였다(탄력성)", font=f_regular(20), fill=INK, anchor="mm")
    d.text((600, 545), "\"서버를 키우지 말고 늘려라\" — 현대 백엔드의 기본 발상",
           font=f_regular(24), fill=INK, anchor="mm")
    signature(d, "09")
    img.save(os.path.join(HERE, "09-1-scale-up-vs-out.png"))


def img_09_2():
    img, d = new_canvas()
    d.text((600, 62), "2022. 11. 15. — 티켓마스터가 멈춘 날", font=f_bold(36), fill=INK, anchor="mm")
    d.rounded_rectangle([150, 140, 620, 380], radius=14, outline=RED, width=5)
    d.text((385, 220), "35억 건", font=f_bold(58), fill=RED, anchor="mm")
    d.text((385, 300), "하루 요청 (봇·암표상 포함,", font=f_regular(22), fill=INK, anchor="mm")
    d.text((385, 335), "사측 발표 수치)", font=f_regular(22), fill=INK, anchor="mm")
    d.rounded_rectangle([660, 140, 1060, 250], radius=12, outline=GRAY, width=4)
    d.text((860, 180), "240만 장 판매", font=f_bold(28), fill=INK, anchor="mm")
    d.text((860, 220), "단일 아티스트 일일 기록", font=f_regular(20), fill=GRAY, anchor="mm")
    d.rounded_rectangle([660, 270, 1060, 380], radius=12, outline=GRAY, width=4)
    d.text((860, 310), "2023. 1. 상원 청문회", font=f_bold(26), fill=INK, anchor="mm")
    d.text((860, 350), "기술과 독점 구조가 도마에", font=f_regular(20), fill=GRAY, anchor="mm")
    d.text((600, 460), "테일러 스위프트 Eras Tour 발매 — 수요는 언제든 설계 용량을 뛰어넘는다",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((600, 505), "확장은 '하면 좋은 것'이 아니라 생존 조건", font=f_regular(23), fill=RED, anchor="mm")
    signature(d, "09")
    img.save(os.path.join(HERE, "09-2-ticketmaster-35b.png"))


# ── 10 마이크로서비스 ──────────────────────────────────────────

def img_10_1():
    img, d = new_canvas()
    d.text((300, 62), "모놀리스 — 백화점 하나", font=f_bold(28), fill=INK, anchor="mm")
    d.text((880, 62), "마이크로서비스 — 전문 상점가", font=f_bold(28), fill=BLUE, anchor="mm")
    d.line([590, 100, 590, 500], fill=DIVIDER, width=2)
    d.rounded_rectangle([150, 120, 450, 420], radius=12, outline=INK, width=5)
    for i, t in enumerate(("로그인", "결제", "추천", "동영상")):
        y = 150 + i * 65
        d.rectangle([185, y, 415, y + 45], outline=GRAY, width=3)
        d.text((300, y + 22), t, font=f_regular(21), fill=INK, anchor="mm")
    cross_mark(d, 300, 232, r=11, width=4)
    d.text((300, 455), "결제 오류에 로그인까지 같이 다운 — 한 몸이니까",
           font=f_regular(20), fill=RED, anchor="mm")
    d.text((300, 487), "한 줄 수정에도 전체 재배포", font=f_regular(20), fill=INK, anchor="mm")
    node(d, 880, 150, r=22, outline=BLUE, width=5)
    d.text((880, 112), "API Gateway (정문 안내소)", font=f_bold(19), fill=BLUE, anchor="mm")
    shops = [(700, "로그인"), (820, "결제"), (940, "추천"), (1060, "동영상")]
    for x, t in shops:
        arrow(d, 880, 175, x, 245, color=BLUE, width=3)
        d.rounded_rectangle([x - 55, 250, x + 55, 340], radius=8, outline=BLUE, width=4)
        d.text((x, 295), t, font=f_regular(20), fill=INK, anchor="mm")
    d.text((880, 390), "기능별 독립 서버 — 따로 개발·배포·확장", font=f_regular(20), fill=BLUE, anchor="mm")
    d.text((880, 425), "한 상점이 닫혀도 옆 상점은 영업", font=f_regular(20), fill=INK, anchor="mm")
    d.text((880, 487), "대가: 분산 시스템의 복잡도 폭발", font=f_regular(20), fill=RED, anchor="mm")
    d.text((600, 545), "2014년 파울러&루이스가 명명 — 넷플릭스가 대표 실전 사례",
           font=f_regular(23), fill=INK, anchor="mm")
    signature(d, "10")
    img.save(os.path.join(HERE, "10-1-monolith-vs-micro.png"))


def img_10_2():
    img, d = new_canvas()
    d.text((600, 62), "2023년 프라임 비디오의 역주행", font=f_bold(36), fill=INK, anchor="mm")
    for i in range(6):
        x = 180 + (i % 3) * 110
        y = 160 + (i // 3) * 100
        d.rounded_rectangle([x, y, x + 90, y + 75], radius=8, outline=GRAY, width=3)
        d.text((x + 45, y + 37), "서비스", font=f_regular(17), fill=GRAY, anchor="mm")
    d.text((345, 390), "잘게 쪼갠 마이크로서비스", font=f_regular(21), fill=INK, anchor="mm")
    arrow(d, 540, 250, 660, 250, color=BLUE, width=6, head=18)
    d.text((600, 210), "다시 합침", font=f_bold(22), fill=BLUE, anchor="mm")
    d.rounded_rectangle([690, 150, 1020, 350], radius=12, outline=BLUE, width=6)
    d.text((855, 220), "모놀리스", font=f_bold(32), fill=BLUE, anchor="mm")
    d.text((855, 280), "인프라 비용 90%+ 절감", font=f_bold(24), fill=INK, anchor="mm")
    d.text((855, 390), "(Prime Video Tech Blog, 2023.3)", font=f_regular(19), fill=GRAY, anchor="mm")
    d.text((600, 460), "단, 전체 플랫폼이 아니라 스트리밍 품질 모니터링(VQA) 서비스 한 팀 한정",
           font=f_bold(24), fill=RED, anchor="mm")
    d.text((600, 510), "쪼개는 게 항상 답이 아니다 — 규모와 필요가 답을 정한다",
           font=f_regular(24), fill=INK, anchor="mm")
    signature(d, "10")
    img.save(os.path.join(HERE, "10-2-prime-video.png"))


# ── 11 서버리스·GraphQL ────────────────────────────────────────

def img_11_1():
    img, d = new_canvas()
    d.text((600, 62), "서버의 3단 진화 — 관리가 사라진다", font=f_bold(34), fill=INK, anchor="mm")
    cols = [(230, "자가용", "내 서버", "구입·주차·정비 전부 내 몫", GRAY),
            (600, "택시", "클라우드 가상 서버", "빌려 쓰지만 관리는 여전히 내 몫", GRAY),
            (970, "호출형 킥보드", "서버리스 (Lambda)", "탈 때만 쓰고 관리는 남의 일", BLUE)]
    for x, name, s1, s2, c in cols:
        d.rounded_rectangle([x - 165, 140, x + 165, 400], radius=12, outline=c, width=5)
        d.text((x, 195), name, font=f_bold(30), fill=c, anchor="mm")
        d.text((x, 260), s1, font=f_bold(23), fill=INK, anchor="mm")
        d.text((x, 330), s2, font=f_regular(19), fill=GRAY, anchor="mm")
    arrow(d, 400, 270, 430, 270, color=GRAY, width=4)
    arrow(d, 770, 270, 800, 270, color=GRAY, width=4)
    d.text((600, 460), "2014. 11. 13. AWS Lambda 발표 — 함수만 올리면, 실행된 시간만큼만 과금",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((600, 505), "10년 뒤 월 150만+ 고객, 월 수십조 건 요청 (Forbes 2025.2)",
           font=f_regular(23), fill=BLUE, anchor="mm")
    d.text((600, 548), "새 문제: 콜드 스타트 · 벤더 종속 · 긴 작업 부적합",
           font=f_regular(21), fill=GRAY, anchor="mm")
    signature(d, "11")
    img.save(os.path.join(HERE, "11-1-serverless-ladder.png"))


def img_11_2():
    img, d = new_canvas()
    d.text((300, 62), "REST — 정해진 메뉴판", font=f_bold(28), fill=INK, anchor="mm")
    d.text((880, 62), "GraphQL — 원하는 재료만 주문", font=f_bold(28), fill=BLUE, anchor="mm")
    d.line([590, 100, 590, 500], fill=DIVIDER, width=2)
    d.rectangle([150, 120, 450, 400], outline=GRAY, width=4)
    for i, t in enumerate(("이름", "나이", "주소", "사진", "친구 목록")):
        y = 155 + i * 48
        d.text((190, y), t, font=f_regular(21), fill=INK, anchor="lm")
        if i > 1:
            d.text((390, y), "불필요", font=f_regular(18), fill=RED, anchor="mm")
    d.text((300, 440), "과잉 요청: 필요 없는 필드까지 몽땅", font=f_regular(20), fill=INK, anchor="mm")
    d.text((300, 472), "과소 요청: 화면 하나에 창구 여러 곳", font=f_regular(20), fill=INK, anchor="mm")
    d.rectangle([710, 120, 1050, 400], outline=BLUE, width=4)
    d.text((880, 155), "주문서", font=f_bold(22), fill=BLUE, anchor="mm")
    for i, (t, on) in enumerate((("이름", True), ("나이", True), ("주소", False),
                                 ("사진", False), ("친구 목록", False))):
        y = 200 + i * 40
        d.rectangle([745, y - 12, 769, y + 12], outline=BLUE if on else LGRAY, width=3)
        if on:
            d.line([749, y, 757, y + 8], fill=BLUE, width=4)
            d.line([757, y + 8, 766, y - 8], fill=BLUE, width=4)
        d.text((790, y), t, font=f_regular(21), fill=INK if on else LGRAY, anchor="lm")
    d.text((880, 440), "필요한 모양의 데이터를 한 번에", font=f_regular(20), fill=BLUE, anchor="mm")
    d.text((880, 472), "대가: 캐싱·모니터링이 REST보다 복잡", font=f_regular(20), fill=GRAY, anchor="mm")
    d.text((600, 545), "페이스북 2012 사내 개발 → 2015 공개 — 대체가 아닌 공존 (REST 93% vs GraphQL 33%)",
           font=f_regular(22), fill=INK, anchor="mm")
    signature(d, "11")
    img.save(os.path.join(HERE, "11-2-graphql-order.png"))


# ── 12 언어 지형도·30년 ────────────────────────────────────────

def img_12_1():
    img, d = new_canvas()
    d.text((600, 62), "백엔드 언어 지형도 — 태생이 자리를 정한다", font=f_bold(34), fill=INK, anchor="mm")
    rows = [("Java + Spring", "금융권·관공서 — 수십 년 검증의 안정성"),
            ("C# + ASP.NET", "마이크로소프트 인프라 기업 생태계"),
            ("Go", "대규모 트래픽 인프라 — Docker·K8s도 Go로"),
            ("JS + Node.js", "브라우저 언어의 서버 진출 — 풀스택의 길"),
            ("Python + FastAPI", "빠른 개발, 그리고 AI 서빙의 표준 통로")]
    for i, (name, desc) in enumerate(rows):
        y = 120 + i * 80
        hl = i == 4
        d.rounded_rectangle([150, y, 470, y + 62], radius=10,
                            outline=BLUE if hl else GRAY, width=4)
        d.text((310, y + 31), name, font=f_bold(24), fill=BLUE if hl else INK, anchor="mm")
        d.text((510, y + 31), desc, font=f_regular(22), fill=INK, anchor="lm")
    d.text((600, 560), "정답은 없다 — 고객·규모·속도·팀이 이미 아는 언어, '필요'가 결정한다",
           font=f_regular(24), fill=INK, anchor="mm")
    signature(d, "12")
    img.save(os.path.join(HERE, "12-1-language-map.png"))


def img_12_2():
    img, d = new_canvas()
    d.text((600, 62), "서버의 직업 변천사 30년", font=f_bold(36), fill=INK, anchor="mm")
    d.line([120, 300, 1080, 300], fill=GRAY, width=4)
    stops = [(170, "1991", "파일 배달부", "정적 웹"),
             (390, "1993", "HTML 제조기", "CGI → PHP → 프레임워크"),
             (610, "2005", "API 창구", "AJAX 이후 — 데이터만"),
             (830, "2014", "분산 조율자", "마이크로서비스·서버리스"),
             (1050, "현재", "AI 모델 서빙", "FastAPI 합류 지점")]
    for i, (x, yr, job, sub) in enumerate(stops):
        hl = i == 4
        node(d, x, 300, r=13, outline=BLUE if hl else GRAY, width=5)
        d.text((x, 250), yr, font=f_bold(24), fill=BLUE if hl else INK, anchor="mm")
        ytxt = 350 if i % 2 == 0 else 415
        d.text((x, ytxt), job, font=f_bold(23), fill=BLUE if hl else INK, anchor="mm")
        d.text((x, ytxt + 36), sub, font=f_regular(17), fill=GRAY, anchor="mm")
    d.text((600, 520), "언어는 바뀌었지만 하는 일은 한 문장 — HTTP 요청을 받아, 처리하고, 응답을 돌려준다",
           font=f_regular(24), fill=INK, anchor="mm")
    d.text((600, 560), "하나로 이 흐름을 이해하면 나머지는 방언이다", font=f_regular(22), fill=BLUE, anchor="mm")
    signature(d, "12")
    img.save(os.path.join(HERE, "12-2-server-30years.png"))


ALL_IMAGES = [
    img_01_1, img_01_2, img_02_1, img_02_2, img_03_1, img_03_2,
    img_04_1, img_04_2, img_05_1, img_05_2, img_06_1, img_06_2,
    img_07_1, img_07_2, img_08_1, img_08_2, img_09_1, img_09_2,
    img_10_1, img_10_2, img_11_1, img_11_2, img_12_1, img_12_2,
]

if __name__ == "__main__":
    for fn in ALL_IMAGES:
        fn()
    print(f"생성 완료: {len(ALL_IMAGES)}장 PNG (1200x630)")
