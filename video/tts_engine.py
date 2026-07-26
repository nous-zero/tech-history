# -*- coding: utf-8 -*-
"""개선 TTS 엔진 — 문장 단위 합성 + 발음 사전 + 자연 휴지.

edge-tts의 어색한 끊어읽기(#11)·영문 발음(#10) 개선판.
실행: python video/tts_engine.py  → video/output/voice-test/ 에 청음 비교 샘플 생성.
"""
import asyncio
import os
import re
import subprocess

import edge_tts
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
HERE = os.path.dirname(os.path.abspath(__file__))

# 발음 사전 — 영문·기호를 한국어 청자에게 자연스러운 소리로
PRONOUNCE = [
    ("ARPANET", "아파넷"), ("TCP/IP", "티씨피 아이피"), ("NCP", "엔씨피"),
    ("IMP", "아이엠피"), ("UCLA", "유씨엘에이"), ("LOGIN", "로그인"),
    ('"LO"', "엘오"), ("LO", "엘오"), ("L…", "엘,"), ("O…", "오,"),
    ("Web", "웹"), ("Flag Day", "플래그 데이"), ("IPv4", "아이피 버전 포"),
    ("IPv6", "아이피 버전 식스"), ("HTML", "에이치티엠엘"), ("HTTP", "에이치티티피"),
    ("URL", "유알엘"), ("WWW", "더블유 더블유 더블유"), ("CERN", "세른"),
    ("—", ", "), ("·", ", "), ("▷", ""), ("…", ","),
]

def preprocess(text):
    for a, b in PRONOUNCE:
        text = text.replace(a, b)
    text = re.sub(r'["“”\'\(\)\[\]]', "", text)     # 따옴표·괄호 제거(낭독 방해)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def sentences(text):
    parts = re.split(r"(?<=[.?!])\s+", preprocess(text))
    return [p.strip() for p in parts if p.strip()]

async def _synth(text, voice, rate, pitch, out):
    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(out)

def make_silence(path, sec):
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                    "-t", str(sec), "-c:a", "libmp3lame", path], check=True)

def synth_block(text, voice, rate, pitch, out_mp3, work_dir, gap=0.28):
    """문장 단위로 나눠 합성한 뒤 자연 휴지를 넣어 하나로 합침."""
    os.makedirs(work_dir, exist_ok=True)
    sil = os.path.join(work_dir, "_sil.mp3")
    if not os.path.exists(sil):
        make_silence(sil, gap)
    pieces = []
    for i, s in enumerate(sentences(text)):
        p = os.path.join(work_dir, "_s%03d.mp3" % i)
        asyncio.run(_synth(s, voice, rate, pitch, p))
        pieces.append(p)
    lst = os.path.join(work_dir, "_list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for i, p in enumerate(pieces):
            f.write("file '%s'\n" % p.replace("\\", "/"))
            if i < len(pieces) - 1:
                f.write("file '%s'\n" % sil.replace("\\", "/"))
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:a", "libmp3lame", "-ar", "24000", out_mp3], check=True)
    for p in pieces:
        os.remove(p)

def concat_mp3(files, out_mp3, work_dir, gap=0.45):
    sil = os.path.join(work_dir, "_gap.mp3")
    if not os.path.exists(sil):
        make_silence(sil, gap)
    lst = os.path.join(work_dir, "_join.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for i, p in enumerate(files):
            f.write("file '%s'\n" % p.replace("\\", "/"))
            if i < len(files) - 1:
                f.write("file '%s'\n" % sil.replace("\\", "/"))
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:a", "libmp3lame", "-ar", "24000", out_mp3], check=True)

# ── 청음 테스트 ──────────────────────────────────────────────
OLD_TEXT = ('인터넷이 인류에게 건넨 첫마디는 "LO"였습니다. 1969년, ARPANET의 첫 시험에서 '
            '"LOGIN" 다섯 글자를 보내려다 L… O… 그리고 시스템 다운 — 첫마디는 그렇게 "LO"가 됐습니다.')

NEW_TEXT = ("인터넷이 인류한테 건넨 첫마디, 뭐였는지 아세요? 엘오, 딱 두 글자였어요. "
            "1969년에 아파넷 첫 시험을 했거든요. 로그인 다섯 글자를 보내는데, 엘, 오, 까지 가고 시스템이 죽어버렸죠. "
            "그래서 인류 인터넷의 첫마디는 엘오가 됐습니다. 헬로를 하려다가 숨이 넘어간 셈이죠.")

DIALOG = [
    ("나", "1969년, 미 국방부의 어느 회의실. 이런 대화가 오갔을 겁니다.", ("ko-KR-SunHiNeural", "+18%", "+0Hz")),
    ("장군", "소련 미사일이 우리 전화 교환국 한 곳을 때리면, 통신은 어떻게 되나?", ("ko-KR-InJoonNeural", "+10%", "-20Hz")),
    ("참모", "전부 끊깁니다. 회선이 전부 중앙 한 곳으로 모이는 별 모양이라서요.", ("ko-KR-InJoonNeural", "+16%", "+25Hz")),
    ("장군", "심장이 하나라 심장만 노리면 죽는다? 그럼 심장이 없는 통신망을 만들면 되겠군.", ("ko-KR-InJoonNeural", "+10%", "-20Hz")),
    ("나", "이 발상 하나가, 지금 여러분이 쓰는 인터넷이 됩니다.", ("ko-KR-SunHiNeural", "+18%", "+0Hz")),
]

def main():
    out = os.path.join(HERE, "output", "voice-test")
    os.makedirs(out, exist_ok=True)
    # A. 기존 방식(개선 전): 문단 통짜, 특수문자 그대로, 느린 속도
    asyncio.run(_synth(OLD_TEXT, "ko-KR-SunHiNeural", "+4%", "+0Hz",
                       os.path.join(out, "A_기존방식.mp3")))
    # B. 개선 방식: 입말 대본 + 문장 단위 + 발음 사전 + 속도 +18%
    synth_block(NEW_TEXT, "ko-KR-SunHiNeural", "+18%", "+0Hz",
                os.path.join(out, "B_개선_여성.mp3"), out)
    # C. 개선 방식, 남성 목소리
    synth_block(NEW_TEXT, "ko-KR-InJoonNeural", "+15%", "+0Hz",
                os.path.join(out, "C_개선_남성.mp3"), out)
    # D. 대화 장면(배역 혼합, 개선 파이프라인)
    segs = []
    for i, (_, line, (v, r, p)) in enumerate(DIALOG):
        f = os.path.join(out, "_d%02d.mp3" % i)
        synth_block(line, v, r, p, f, out, gap=0.24)
        segs.append(f)
    concat_mp3(segs, os.path.join(out, "D_대화장면.mp3"), out)
    for f in segs:
        os.remove(f)
    print("청음 샘플 4개 생성 완료:", out)

if __name__ == "__main__":
    main()
