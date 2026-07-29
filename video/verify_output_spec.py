# -*- coding: utf-8 -*-
"""산출물 스펙 실측 판정기 — 렌더 직후·발행 전에 '만든 것의 숫자'를 직접 잰다.

왜 필요한가 (2026-07-29 감사 처방 P1):
  refs/audit-reports/2026-07-29-quality-gate-failure.md 결론 —
  "이 팀의 검수는 *만든 것이 틀렸는가*(공작 결함)만 보고, *만들었어야 할 것을
   만들었는가*(범위)와 *만든 것의 규격 값*(계측)을 보지 않았다."
  결함 5건이 전부 사용자 눈에 먼저 닿았다. 사람이 '육안'으로 볼 수 없는 축
  (해상도 숫자·라우드니스·무음 비율·BGM 유무)을 기계 계측으로 대체하는 도구다.

  쉬운 말: 지금까지는 "잘 만들었나 눈으로 봤다"였고, 이 도구는 "자로 재서 숫자를
  적는다". 눈은 854x480 과 1920x1080 을 같은 화면에서 구분 못 하지만 자는 구분한다.

사용:
  python video/verify_output_spec.py 03              # 3편 표준 산출물 전부 검사
  python video/verify_output_spec.py 03 --body       # 본편만
  python video/verify_output_spec.py 03 --shorts     # 쇼츠만
  python video/verify_output_spec.py --file=<mp4> --kind=body|shorts   # 개별 파일
  python video/verify_output_spec.py 03 --quiet      # 표 생략, 판정·JSON 만

종료 코드: 0 = 통과(경고는 있을 수 있음) / 2 = 미달(FAIL 1건 이상) / 1 = 실행 오류
산출물: video/output/<편>_v2/_spec_report.json  (기계 판정용)

판정 등급
  FAIL — 발행 차단. 규격 미달이 확정된 항목.
  WARN — 값은 기록하되 차단하지 않음. 목표 미달이나 현행 표준상 허용된 항목.
  INFO — 참고 기록(측정 불가 사유 포함). rule6: 못 잰 것은 '미측정+사유'로 남기고
         임의 값으로 채우지 않는다.
"""
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import wave

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import imageio_ffmpeg  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ============================================================================
# 기준값 상수 — 전부 근거를 명기한다. 근거 없는 숫자는 여기에 두지 않는다(rule1·rule6).
# ============================================================================

# [해상도·프레임률] video-producer.md 관할 6 "본편 1080p 16:9, 쇼츠 9:16" +
# 감사 처방 P5-3(개정안 "본편 1920x1080 30fps"). build_v2.py:VW/VH/VFPS 와 같은 값.
RES_BODY = (1920, 1080)
RES_SHORTS = (1080, 1920)
FPS_REQUIRED = 30.0
FPS_TOL = 0.6            # 29.97/30000-1001 같은 표기 흔들림 허용

# [라우드니스] 목표 -16 LUFS ±1.0.
# 근거: video/normalize_loudness.py:12-19 의 3편 실측표 — -16(게인 +7.5dB·LRA 3.2·
# 원음충실도 0.936) vs -14(+16.3dB·LRA 2.0·0.784). -14 는 2dB 더 크게 들리자고
# 표현력을 절반으로 깎는다. 유튜브는 기준보다 큰 소리를 낮출 뿐 작은 소리를 올리지
# 않으므로 체감차는 2dB, 다이내믹 손실은 되돌릴 수 없다. + BGM 헤드룸 확보.
# ※ audio-producer.md 관할 5 의 "-14 LUFS" 문구는 이 실측 채택값과 불일치 →
#   감사 처방 P5-4 로 지시서 정정 대상(이 검사기는 실측 채택값 -16 을 따른다).
LUFS_TARGET = -16.0
LUFS_TOL = 1.0
TRUE_PEAK_MAX = -1.0     # dBTP. 유튜브 등 로시 인코딩 후 클리핑 여유(감사 처방 P1 표)

# [샘플레이트] 유튜브 권장 48kHz. 현행 본편은 24kHz 모노(감사 결함 6 실측).
# 24kHz 원본을 48kHz 로 올려 담아도 없던 소리는 생기지 않으므로 '차단'이 아니라
# '경고 + 값 표기'로 둔다(감사 결함 6 "정직한 한계 표기" 항 그대로).
SR_RECOMMEND = 48000
CH_RECOMMEND = 2

# [무음 비율] 상한 12%.
# 근거: 감사 결함 4 — 3편 내레이션 공백 21.5%(refs/pipeline-status.md:28)가
# '늘어짐'의 원인으로 실측 규명됨. 감사 처방 P1 표는 15%(잠정)였으나 본선 지시로
# 12% 채택. 최장 공백 0.5초는 trim_silence.py 의 내부 무음 상한 0.40s + 여유.
SILENCE_RATIO_MAX = 0.12
SILENCE_GAP_MAX = 0.5
# 무음 판정 임계는 trim_silence.py:130 기본값과 반드시 같아야 한다 — 다르면
# 다듬기 도구가 "끝냈다"고 한 트랙을 검사기가 "미달"이라 하는 엇갈림이 생긴다.
SILENCE_NOISE = "-35dB"
SILENCE_MIND = 0.15

# [무음 정의 정교화 — 2026-07-30 audio-producer 심의]
# 문제: 최초 판(원시 측정)은 episode_track.wav 의 무음을 통째로 세어 3편을 미달
# 판정했다(13.5% / 최장 2.91s). 그러나 이 트랙은 build_v2.build_audio(build_v2.py:2191)
# 가 **설계상 무음을 직접 삽입해** 만든 것이다:
#     track = silent(INTRO_D 2.8s) + Σ( seg wav + silent(GAP 0.35s) )
# 즉 최소 2.8 + 0.35×세그수 만큼의 무음은 '결함'이 아니라 '조립 사양'이다.
# 3편 실측 분해(15세그, 193.10s): INTRO 2.80s + GAP 5.25s = 설계 8.05s.
# 미달 판정의 근거였던 '최장 공백 2.91s'는 **트랙 맨 앞 0.00~2.91s = 인트로 카드**였다
# (2.80 설계 + seg000 머리 0.11). 2편도 같은 자리에서 2.90s — 즉 이 축은 편이 뭐든
# 항상 인트로만 집어내며 내레이션에 대해 아무것도 말하지 않는, 죽은 계측이었다.
#
# 정정 방향: 임계를 느슨하게 푸는 것이 아니라 **재는 대상을 정의한다**.
#   잉여 무음(excess) = 실측 무음 길이 − 그 구간이 설계 무음(INTRO·GAP)과 겹친 길이
#   분모 = 내레이션 실체 구간 = Σ(seg wav 길이) = 트랙 − 설계 무음 총량
# 두 지표 모두 이 하나의 개념에서 나온다. 임계값(12% / 0.5s)은 **바꾸지 않았다**.
#
# 검출력 회귀 실측(같은 도구, 같은 임계):
#   3편 원시 13.5% · 최장 2.91s(인트로) → 잉여  9.69% · 최장 0.37s  → 통과
#   2편 원시 22.2% · 최장 2.90s(인트로) → 잉여 18.41% · 최장 1.15s  → 미달 유지
# 2편은 미달로 남고(다듬기 미적용), 최장 공백 축은 '인트로 2.90s'라는 무의미한 값
# 대신 seg007 의 실제 1.15s 공백을 가리키게 됐다 — 검출력은 죽은 게 아니라 살아났다.
# 경계를 걸친 무음(세그 꼬리+GAP+다음 세그 머리)도 설계분만 빼고 나머지는 전부
# 잉여로 세므로, 조각을 넘나들며 숨는 긴 공백을 놓치지 않는다.
#
# 원시값은 지우지 않고 INFO 로 계속 출력한다 — 값을 화면에서 없애면 결함 2
# ("없는 것은 눈에 띄지 않는다")를 그대로 재발시킨다.

# [길이 불변식] 허용 오차 0.3초(본선 지시). 대본 합산 ↔ 오디오 트랙 ↔ 영상.
# 대본 합산식은 build_v2.py 조립식과 동일해야 한다: INTRO_D + Σ(세그 + GAP).
DUR_TOL = 0.3
INTRO_D = 2.8            # build_v2.py:61
GAP = 0.35               # build_v2.py:60
# 본편 영상은 오디오보다 '아웃트로 카드'만큼 길다(설계상 의도). build_v2.py:2194 의
# 예상 길이식이 +1.2s 를 더하는 이유가 이것. 실측(2편 완성본): 영상 172.93 - 오디오
# 171.97 = 0.96s. 따라서 '영상=오디오'가 아니라 '영상 = 오디오 + 꼬리(0~2.0s)'가 참인
# 불변식이다. 이 축은 두 방향을 각각 본다:
#   ① 영상 < 오디오  → 내레이션이 잘렸다(치명). ② 꼬리가 너무 길다 → 정적(dead air).
OUTRO_TAIL_MAX = 2.0

# [쇼츠] 유튜브 쇼츠 상한 60초. 10초 미만은 도달이 급격히 나빠져 하한으로 둔다.
SHORTS_MAX_SEC = 60.0
SHORTS_MIN_SEC = 10.0

# [BGM] 감사 결함 2 — 1~3편 본편에 BGM 없음. 사용자 결정(감사 §6): 1·2편 소급 없음,
# 3편부터 보완. 감사 처방 P1 표는 "4편부터 필수(1~3편 면제)". 그 전 편은 '없음'을
# 침묵하지 않고 반드시 출력한다 — 침묵=통과는 결함 2 를 낳은 바로 그 구조다.
BGM_REQUIRED_FROM_EP = 4

# ============================================================================


class Row(object):
    """검사 1건. 실측값과 기준을 함께 들고 다닌다(둘 중 하나만으론 판정 못 함)."""

    def __init__(self, target, item, measured, expected, verdict, note="", scope=""):
        self.target = target
        self.item = item
        self.measured = measured
        self.expected = expected
        self.verdict = verdict      # PASS / FAIL / WARN / INFO
        self.note = note
        self.scope = scope          # body / shorts — 부분 검사 병합용

    def as_dict(self):
        return {"target": self.target, "item": self.item, "measured": self.measured,
                "expected": self.expected, "verdict": self.verdict, "note": self.note,
                "scope": self.scope}


# ---------- 실측 원시 함수 (전부 ffmpeg/wave 직접 관측) ----------

def ff(args):
    """ffmpeg 실행 후 stderr 반환. ffmpeg 는 스트림 정보를 stderr 로 낸다."""
    r = subprocess.run([FF, "-hide_banner", "-nostats"] + args,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stderr


def probe(path):
    """컨테이너 규격 실측 — 디코딩 없이 헤더만 읽으므로 렌더 부하 0에 가깝다."""
    txt = ff(["-i", path])
    d = {"path": path, "exists": os.path.exists(path)}
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", txt)
    d["duration"] = (int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))) if m else None
    m = re.search(r"Video: .*?, (\d+)x(\d+)", txt)
    d["width"], d["height"] = (int(m.group(1)), int(m.group(2))) if m else (None, None)
    m = re.search(r"Video: .*?, ([\d.]+) fps", txt)
    d["fps"] = float(m.group(1)) if m else None
    m = re.search(r"Audio: (\w+)", txt)
    d["acodec"] = m.group(1) if m else None
    m = re.search(r"Audio: .*?, (\d+) Hz, ([^,]+)", txt)
    if m:
        d["sample_rate"] = int(m.group(1))
        ch = m.group(2).strip()
        d["channels"] = 1 if ch == "mono" else (2 if ch == "stereo" else ch)
    else:
        d["sample_rate"], d["channels"] = None, None
    return d


def loudness(path):
    """통합 라우드니스·트루피크·LRA 실측(ffmpeg loudnorm 1패스 분석).
    ※ 실제로 오디오를 끝까지 디코드하므로 200초 트랙에 수~십수 초 걸린다."""
    txt = ff(["-i", path, "-af", "loudnorm=print_format=summary", "-f", "null", "-"])

    def g(k):
        m = re.search(r"Input %s:\s+(-?[\d.]+|-?inf)" % k, txt)
        if not m:
            return None
        v = m.group(1)
        return float("-inf") if "inf" in v else float(v)

    return {"integrated": g("Integrated"), "true_peak": g("True Peak"), "lra": g("LRA")}


def silence_stats(path, total_dur):
    """무음 총 비율·최장 공백 실측(silencedetect). 임계는 trim_silence.py 와 동일."""
    txt = ff(["-i", path, "-af",
              "silencedetect=noise=%s:d=%s" % (SILENCE_NOISE, SILENCE_MIND),
              "-f", "null", "-"])
    spans, cur = [], None
    for m in re.finditer(r"silence_(start|end): (-?[\d.]+)", txt):
        k, v = m.group(1), float(m.group(2))
        if k == "start":
            cur = v
        elif cur is not None:
            spans.append((max(cur, 0.0), v))
            cur = None
    if cur is not None and total_dur:      # 끝까지 무음으로 닫힌 경우
        spans.append((max(cur, 0.0), total_dur))
    tot = sum(b - a for a, b in spans)
    return {"total_silence": tot,
            "ratio": (tot / total_dur) if total_dur else None,
            "max_gap": max([b - a for a, b in spans], default=0.0),
            "count": len(spans),
            "spans": spans}


def designed_silence_map(ep, audio_dir):
    """build_audio 조립식을 되짚어 '설계상 삽입된 무음'의 시각 경계를 복원한다.

    반환: (구간목록, 내레이션 실체 초). 구간은 (시작, 끝, 종류).
    추정이 아니라 실제 seg wav 길이를 누적해 만든 지도이므로, 트랙 길이와 소수점
    둘째 자리까지 맞는다(3편 실측: 조립 합산 193.104 vs wav 193.102, 차 0.002s).
    대본·세그 wav 가 없으면 (None, 사유) — 지도 없이 추측하지 않는다(rule6)."""
    sp = os.path.join(ROOT, "video", "scripts", "%s.json" % ep)
    if not os.path.exists(sp):
        return None, "대본 없음: %s" % os.path.basename(sp)
    with open(sp, encoding="utf-8") as f:
        data = json.load(f)
    regions, narr, t = [(0.0, INTRO_D, "INTRO")], 0.0, INTRO_D
    for seg in data["segments"]:
        wp = os.path.join(audio_dir, "seg%03d.wav" % seg["id"])
        if not os.path.exists(wp):
            return None, "세그 wav 누락: seg%03d" % seg["id"]
        with contextlib.closing(wave.open(wp, "rb")) as w:
            d = w.getnframes() / float(w.getframerate())
        narr += d
        t += d
        regions.append((t, t + GAP, "GAP"))
        t += GAP
    return (regions, narr), ""


def excess_silence(spans, regions, narr):
    """설계 무음을 뺀 '잉여 무음'을 집계 — 비율·최장 모두 이 하나의 개념에서 나온다.

    구간이 설계 무음(인트로·GAP)과 겹친 만큼만 면제하고 나머지는 전부 센다. 그래서
    세그 꼬리 → GAP → 다음 세그 머리로 이어지는 긴 공백도 설계분 0.35s 만 빠지고
    실제 초과분은 그대로 잡힌다."""
    tot, mx, mx_at, n = 0.0, 0.0, None, 0
    for s0, s1 in spans:
        designed = 0.0
        for r0, r1, _kind in regions:
            designed += max(0.0, min(s1, r1) - max(s0, r0))
        ex = max(0.0, (s1 - s0) - designed)
        if ex > 1e-6:
            tot += ex
            n += 1
            if ex > mx:
                mx, mx_at = ex, s0
    return {"total": tot, "ratio": (tot / narr) if narr else None,
            "max_gap": mx, "max_at": mx_at, "count": n}


def wav_info(path):
    """wav 헤더 + 표본 단위 클리핑 개수 실측(16bit 모노/스테레오)."""
    import numpy as np
    with contextlib.closing(wave.open(path, "rb")) as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    info = {"sample_rate": sr, "channels": ch, "sampwidth": sw,
            "duration": n / float(sr) if sr else None, "clipped": None}
    if sw == 2:
        x = np.frombuffer(raw, dtype="<i2")
        # 풀스케일에 닿은 표본 수 = 깎여나간(clipped) 표본. 0이어야 정상.
        info["clipped"] = int(((x >= 32767) | (x <= -32768)).sum())
    return info


def script_expected_seconds(ep, audio_dir):
    """대본 세그 wav 합산으로 기대 길이 산출 — build_v2.build_audio 와 같은 식.
    (INTRO_D 무음 + Σ(세그 + GAP)). 추정이 아니라 실제 wav 길이의 합이다."""
    sp = os.path.join(ROOT, "video", "scripts", "%s.json" % ep)
    if not os.path.exists(sp):
        return None, "대본 없음: %s" % sp
    with open(sp, encoding="utf-8") as f:
        data = json.load(f)
    total, missing = INTRO_D, []
    for seg in data["segments"]:
        wp = os.path.join(audio_dir, "seg%03d.wav" % seg["id"])
        if not os.path.exists(wp):
            missing.append(seg["id"])
            continue
        with contextlib.closing(wave.open(wp, "rb")) as w:
            total += w.getnframes() / float(w.getframerate())
        total += GAP
    if missing:
        return None, "세그 wav 누락: %s" % missing
    return total, ""


#  감사 축 이름 → 로그에 찍히는 문구. build_shorts.audit_frame()/build_v2.audit_layout()
#  이 같은 [audit] 형식을 쓰므로 본편·쇼츠를 한 코드로 판정한다.
#  '보호영역 침범' 은 2026-07-30 신설 — 프레임 안이지만 요소끼리 겹치는 유형
#  (3편 아웃트로: 예고 부제가 구독 버튼 밑으로 파묻힘)을 잡는 축이다.
AUDIT_AXES = ("프레임 이탈", "보호영역 침범")


def audit_lines(out_dir):
    """레이아웃 감사 로그 수집 — build_shorts/build_v2 의 [audit] 출력.
    같은 장면이 여러 로그에 나오면 '가장 최근 파일'의 값을 채택한다(옛 로그의
    수리 전 수치를 지금 값으로 오인하지 않기 위해).
    반환: {장면이름: {축이름: {"count": n, "source": 파일명}}}"""
    hits = {}
    files = []
    for fn in os.listdir(out_dir):
        if fn.endswith(".log") or (fn.startswith("_DONE") and fn.endswith(".txt")):
            files.append(os.path.join(out_dir, fn))
    for p in sorted(files, key=os.path.getmtime):      # 오래된 것 → 최신 순으로 덮어씀
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                txt = f.read()
        except OSError:
            continue
        for axis in AUDIT_AXES:
            for m in re.finditer(r"\[audit\] (\S+?): %s (\d+)건" % axis, txt):
                hits.setdefault(m.group(1), {})[axis] = {
                    "count": int(m.group(2)), "source": os.path.basename(p)}
    return hits


# ---------- 검사 축 ----------

def check_video_spec(rows, tag, p, kind):
    want = RES_BODY if kind == "body" else RES_SHORTS
    got = (p["width"], p["height"])
    rows.append(Row(tag, "해상도", "%sx%s" % got if got[0] else "판독 실패",
                    "%dx%d" % want, "PASS" if got == want else "FAIL"))
    fps = p["fps"]
    ok = fps is not None and abs(fps - FPS_REQUIRED) <= FPS_TOL
    rows.append(Row(tag, "프레임률", ("%.2f fps" % fps) if fps else "판독 실패",
                    "%.0f fps (±%.1f)" % (FPS_REQUIRED, FPS_TOL), "PASS" if ok else "FAIL"))


def check_audio_format(rows, tag, sr, ch, src):
    if sr is None:
        rows.append(Row(tag, "샘플레이트·채널", "판독 실패", "%d Hz" % SR_RECOMMEND, "WARN",
                        "오디오 스트림 없음 또는 파싱 실패"))
        return
    chs = {1: "모노", 2: "스테레오"}.get(ch, str(ch))
    ok = sr >= SR_RECOMMEND
    rows.append(Row(tag, "샘플레이트·채널", "%d Hz %s" % (sr, chs),
                    "%d Hz 권장(유튜브)" % SR_RECOMMEND,
                    "PASS" if ok else "WARN",
                    src + ("" if ok else " / 원본 TTS가 %dHz라 올려 담아도 정보는 늘지 않음 — 차단 아님" % sr)))


def check_loudness(rows, tag, path):
    ld = loudness(path)
    I, TP = ld["integrated"], ld["true_peak"]
    if I is None:
        rows.append(Row(tag, "라우드니스", "측정 실패", "%.1f LUFS" % LUFS_TARGET, "WARN",
                        "loudnorm 출력 파싱 실패"))
        return ld
    ok = abs(I - LUFS_TARGET) <= LUFS_TOL
    rows.append(Row(tag, "라우드니스(통합)", "%.1f LUFS" % I,
                    "%.1f ±%.1f LUFS" % (LUFS_TARGET, LUFS_TOL),
                    "PASS" if ok else "FAIL",
                    "" if ok else "기준 대비 %+.1f dB" % (I - LUFS_TARGET)))
    if TP is not None:
        rows.append(Row(tag, "트루피크", "%.1f dBTP" % TP, "≤ %.1f dBTP" % TRUE_PEAK_MAX,
                        "PASS" if TP <= TRUE_PEAK_MAX else "FAIL"))
    if ld["lra"] is not None:
        rows.append(Row(tag, "다이내믹 폭(LRA)", "%.1f LU" % ld["lra"], "참고", "INFO"))
    return ld


def check_bgm(rows, tag, out_dir, stem, required, rule):
    """BGM 존재 여부는 '있으면 존재/없으면 없음'을 반드시 출력한다.
    감사 결함 2 의 교훈: 없는 것은 눈에 띄지 않는다 — 침묵을 통과로 두면 영원히 못 잡는다.
    required=False 여도 행 자체는 반드시 남긴다(값 없는 항목을 지우면 결함 2가 재발한다)."""
    cand = os.path.join(out_dir, "%s_bgm.wav" % stem)
    if os.path.exists(cand):
        rows.append(Row(tag, "BGM 트랙", "있음 (%s)" % os.path.basename(cand), rule, "PASS"))
    else:
        rows.append(Row(tag, "BGM 트랙", "없음", rule, "FAIL" if required else "WARN",
                        "기대 경로: %s" % os.path.basename(cand)))


def body_bgm_rule(ep):
    """본편 BGM 의무 판정 — 감사 §6 사용자 결정(1~3편 소급 없음, 4편부터 필수)."""
    try:
        epn = int(re.sub(r"\D", "", ep) or 0)
    except ValueError:
        epn = 0
    required = epn >= BGM_REQUIRED_FROM_EP
    rule = "%d편부터 필수" % BGM_REQUIRED_FROM_EP
    if not required:
        rule += " (%s편 면제)" % ep
    return required, rule


def check_frame_audit(rows, tag, out_dir, expect_scenes=2, scope="", axes=None):
    """레이아웃 감사 로그 판정 — ①프레임 이탈 ②보호영역 침범(요소 간 겹침).

    ※ 로그에 찍히는 이름은 산출물 이름(shorts_A)이 아니라 Manim 장면 클래스 이름
    (Short03A·Episode03 등)이다 — `name = type(self).__name__`.
    그래서 이름을 미리 정해두고 찾으면 영원히 '미확인'이 된다. 찾은 이름을 그대로
    보고하는 방식으로 둔다(편마다 클래스 이름이 다른 것에도 자동 대응)."""
    # axes: 이 산출물에서 기대하는 감사 축. 쇼츠(build_shorts.py)에는 보호 영역 기능이
    # 아직 없으므로 그 축을 요구하지 않는다 — 있을 수 없는 줄을 기다리며 영원히 경고를
    # 띄우면 경고 자체가 무뎌진다(경보 피로).
    axes = AUDIT_AXES if axes is None else axes
    hits = audit_lines(out_dir)
    if scope:      # 본편/쇼츠 장면 이름이 한 폴더에 섞여 있으므로 접두어로 가른다
        hits = {k: v for k, v in hits.items() if k.startswith(scope)}
    if not hits:
        for axis in axes:
            rows.append(Row(tag, axis, "미확인", "0건", "WARN",
                            "렌더 로그에 [audit] 줄 없음 — 렌더 미실행이거나 로그 미보존"))
        return
    for nm in sorted(hits):
        for axis in axes:
            h = hits[nm].get(axis)
            if h is None:
                rows.append(Row(tag, "%s(%s)" % (axis, nm), "미확인", "0건", "WARN",
                                "이 축의 [audit] 줄이 없음 — 옛 렌더 로그(검사기 신설 전)"))
                continue
            rows.append(Row(tag, "%s(%s)" % (axis, nm), "%d건" % h["count"], "0건",
                            "PASS" if h["count"] == 0 else "FAIL", "출처: %s" % h["source"]))
    if len(hits) < expect_scenes:
        rows.append(Row(tag, "레이아웃 감사 범위", "%d장면" % len(hits),
                        "%d장면" % expect_scenes, "WARN",
                        "일부 장면의 감사 기록이 없다 — 부분 확인"))


# ---------- 편 단위 검사 ----------

def verify_body(rows, ep, out_dir):
    tag = "본편"
    mp4 = os.path.join(out_dir, "episode.mp4")
    if not os.path.exists(mp4):
        rows.append(Row(tag, "산출물 존재", "없음", mp4, "FAIL",
                        "완성본 미생성 — build_v2.py %s --full 필요" % ep))
        return
    p = probe(mp4)
    rows.append(Row(tag, "파일", os.path.basename(mp4), "episode.mp4", "INFO",
                    "%.1f MB" % (os.path.getsize(mp4) / 1e6)))
    check_video_spec(rows, tag, p, "body")
    # 본편에도 레이아웃 감사를 건다(2026-07-30 신설). 감사가 지적한 "본편 프레임 이탈
    # 불변식 부재"(유형 A 누적 5회) + 요소 간 겹침(3편 아웃트로) 두 축을 함께 판정한다.
    # 장면 클래스 이름이 EpisodeNN 이므로 접두어로 쇼츠(ShortNN*) 기록과 가른다.
    check_frame_audit(rows, tag, out_dir, expect_scenes=1, scope="Episode")

    # 오디오 규격은 mp4 컨테이너 실측값으로 본다(시청자가 받는 것이 이것이므로).
    check_audio_format(rows, tag, p["sample_rate"], p["channels"], "mp4 컨테이너 실측")
    check_loudness(rows, tag, mp4)

    # 내레이션 트랙(믹싱 전) — 무음 비율은 BGM 이 섞이면 잴 수 없으므로 여기서 잰다.
    trk = os.path.join(out_dir, "episode_track.wav")
    if os.path.exists(trk):
        wi = wav_info(trk)
        st = silence_stats(trk, wi["duration"])
        # 원시 측정값은 판정에서 내렸지만 화면에서는 내리지 않는다(위 '무음 정의' 주석).
        rows.append(Row(tag, "무음 원시 측정", "%.1f%% (총 %.1fs / %d구간) · 최장 %.2fs"
                        % (st["ratio"] * 100, st["total_silence"], st["count"], st["max_gap"]),
                        "참고(설계 무음 포함)", "INFO",
                        "임계 %s / 최소 %ss — 설계 무음(인트로 %.1fs + GAP %.2fs×세그수) 포함값"
                        % (SILENCE_NOISE, SILENCE_MIND, INTRO_D, GAP)))
        dmap, derr = designed_silence_map(ep, os.path.join(out_dir, "audio"))
        if dmap is None:
            # 지도를 못 만들면 원시값으로 판정하되, 그 사실을 반드시 표기한다 —
            # 설계 무음이 섞인 값이라 과대 판정될 수 있음을 숨기지 않는다.
            ratio = st["ratio"]
            rows.append(Row(tag, "무음 비율(내레이션)",
                            "%.1f%% (원시)" % (ratio * 100), "≤ %.0f%%" % (SILENCE_RATIO_MAX * 100),
                            "PASS" if ratio <= SILENCE_RATIO_MAX else "FAIL",
                            "설계 무음 분해 불가(%s) — 원시값 판정이라 과대평가 가능" % derr))
            rows.append(Row(tag, "최장 공백", "%.2fs (원시)" % st["max_gap"],
                            "≤ %.1fs" % SILENCE_GAP_MAX,
                            "PASS" if st["max_gap"] <= SILENCE_GAP_MAX else "FAIL", derr))
        else:
            regions, narr = dmap
            ng = len([1 for _a, _b, k in regions if k == "GAP"])
            ex = excess_silence(st["spans"], regions, narr)
            rows.append(Row(tag, "설계 무음(조립 사양)",
                            "%.2fs (인트로 %.1fs + GAP %.2fs×%d)"
                            % (INTRO_D + GAP * ng, INTRO_D, GAP, ng),
                            "build_v2.build_audio", "INFO",
                            "내레이션 실체 구간 %.2fs = 세그 wav 합산" % narr))
            rows.append(Row(tag, "무음 비율(내레이션 내부)",
                            "%.1f%% (잉여 %.1fs / %d구간)" % (ex["ratio"] * 100, ex["total"], ex["count"]),
                            "≤ %.0f%%" % (SILENCE_RATIO_MAX * 100),
                            "PASS" if ex["ratio"] <= SILENCE_RATIO_MAX else "FAIL",
                            "설계 무음 제외 · 분모 %.2fs" % narr))
            rows.append(Row(tag, "최장 공백(설계 제외)", "%.2fs" % ex["max_gap"],
                            "≤ %.1fs" % SILENCE_GAP_MAX,
                            "PASS" if ex["max_gap"] <= SILENCE_GAP_MAX else "FAIL",
                            ("최장 지점 %.2fs 부근" % ex["max_at"]) if ex["max_at"] is not None else ""))
        if wi["clipped"] is not None:
            rows.append(Row(tag, "클리핑(표본)", "%d개" % wi["clipped"], "0개",
                            "PASS" if wi["clipped"] == 0 else "FAIL", "episode_track.wav 표본 단위"))
    else:
        rows.append(Row(tag, "무음 비율(내레이션)", "미측정", "≤ %.0f%%" % (SILENCE_RATIO_MAX * 100),
                        "WARN", "episode_track.wav 없음 — BGM 합성본으로는 측정 불가(rule6)"))
        wi = None

    _req, _rule = body_bgm_rule(ep)
    check_bgm(rows, tag, out_dir, "episode", _req, _rule)

    # 길이 불변식: 대본 합산 ↔ 오디오 트랙 ↔ 영상. 셋이 서로 일치해야 한다.
    exp, err = script_expected_seconds(ep, os.path.join(out_dir, "audio"))
    vdur = p["duration"]
    if exp is None:
        rows.append(Row(tag, "길이 불변식", "미측정", "±%.1fs" % DUR_TOL, "WARN", err))
    else:
        rows.append(Row(tag, "길이(대본 세그 합산)", "%.2fs" % exp, "기준선", "INFO"))
        if wi and wi["duration"]:
            d = abs(wi["duration"] - exp)
            rows.append(Row(tag, "길이 일치(오디오 트랙↔대본)",
                            "%.2fs (차 %.2fs)" % (wi["duration"], d), "±%.1fs" % DUR_TOL,
                            "PASS" if d <= DUR_TOL else "FAIL"))
        if vdur:
            # 영상은 '대본 합산 + 아웃트로 꼬리'이므로 대본과의 직접 비교는 기록용.
            # 판정은 아래 '영상≥오디오' + '아웃트로 꼬리' 두 축이 담당한다.
            rows.append(Row(tag, "길이(영상)", "%.2fs" % vdur,
                            "대본 %.2fs + 아웃트로" % exp, "INFO"))
    if vdur and wi and wi["duration"]:
        tail = vdur - wi["duration"]
        if tail < -0.05:
            rows.append(Row(tag, "영상≥오디오(내레이션 생존)",
                            "영상 %.2fs < 오디오 %.2fs (부족 %.2fs)" % (vdur, wi["duration"], -tail),
                            "영상 ≥ 오디오", "FAIL", "내레이션 끝이 잘렸다"))
        else:
            rows.append(Row(tag, "영상≥오디오(내레이션 생존)",
                            "영상 %.2fs / 오디오 %.2fs" % (vdur, wi["duration"]),
                            "영상 ≥ 오디오", "PASS"))
            rows.append(Row(tag, "아웃트로 꼬리", "%.2fs" % tail,
                            "0~%.1fs" % OUTRO_TAIL_MAX,
                            "PASS" if tail <= OUTRO_TAIL_MAX else "FAIL",
                            "설계상 아웃트로 카드 길이(build_v2.py 예상식 +1.2s)"))


def verify_shorts(rows, ep, out_dir):
    names = ["shorts_A", "shorts_B"]
    check_frame_audit(rows, "쇼츠", out_dir, expect_scenes=len(names), scope="Short",
                      axes=("프레임 이탈",))
    for nm in names:
        tag = "쇼츠 %s" % nm[-1]
        mp4 = os.path.join(out_dir, "%s.mp4" % nm)
        if not os.path.exists(mp4):
            rows.append(Row(tag, "산출물 존재", "없음", mp4, "FAIL",
                            "build_shorts.py %s --full 필요" % ep))
            continue
        p = probe(mp4)
        rows.append(Row(tag, "파일", os.path.basename(mp4), "%s.mp4" % nm, "INFO",
                        "%.1f MB" % (os.path.getsize(mp4) / 1e6)))
        check_video_spec(rows, tag, p, "shorts")
        dur = p["duration"]
        if dur:
            ok = SHORTS_MIN_SEC <= dur <= SHORTS_MAX_SEC
            rows.append(Row(tag, "길이", "%.2fs" % dur,
                            "%.0f~%.0f초" % (SHORTS_MIN_SEC, SHORTS_MAX_SEC),
                            "PASS" if ok else "FAIL"))
        check_audio_format(rows, tag, p["sample_rate"], p["channels"], "mp4 컨테이너 실측")
        check_loudness(rows, tag, mp4)
        # 쇼츠 BGM 은 편 무관 필수 — build_shorts.py 의 make_bgm() 이 현행 문법에
        # 이미 포함돼 있으므로, 없다는 것은 옛 문법으로 만들어졌다는 신호다.
        check_bgm(rows, tag, out_dir, nm, True, "필수(쇼츠 문법)")
        # 오디오≥영상 불변식(엔딩 카드 생존) — build_shorts 가 이미 assert 로 막지만,
        # 산출물 쪽에서 한 번 더 잰다(하류 재측정 원칙, 감사 처방 P5-11).
        apath = os.path.join(out_dir, "%s_audio.wav" % nm)
        if os.path.exists(apath) and dur:
            wi = wav_info(apath)
            ok = wi["duration"] + 0.05 >= dur
            rows.append(Row(tag, "오디오≥영상(엔딩 생존)",
                            "오디오 %.2fs / 영상 %.2fs" % (wi["duration"], dur), "오디오 ≥ 영상",
                            "PASS" if ok else "FAIL"))
        rows.append(Row(tag, "무음 비율", "미측정", "≤ %.0f%%" % (SILENCE_RATIO_MAX * 100), "INFO",
                        "쇼츠 오디오는 BGM 합성본이라 내레이션 무음을 분리 측정 불가(rule6: 사유 기록)"))


# ---------- 출력 ----------

MARK = {"PASS": "통과", "FAIL": "미달", "WARN": "경고", "INFO": "기록"}


def render_table(rows):
    hdr = ("대상", "항목", "실측값", "기준", "판정")
    data = [(r.target, r.item, str(r.measured), str(r.expected),
             MARK.get(r.verdict, r.verdict)) for r in rows]
    w = [max(_dw(h), max([_dw(d[i]) for d in data] or [0])) for i, h in enumerate(hdr)]
    line = "+".join("-" * (x + 2) for x in w)
    out = [" " + " | ".join(_pad(h, w[i]) for i, h in enumerate(hdr)), line]
    for d in data:
        out.append(" " + " | ".join(_pad(c, w[i]) for i, c in enumerate(d)))
    return "\n".join(out)


def _dw(s):
    """한글은 콘솔에서 두 칸을 차지한다 — 표가 어긋나지 않게 폭을 2로 센다."""
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(s))


def _pad(s, width):
    return str(s) + " " * max(0, width - _dw(s))


def main():
    args = [a for a in sys.argv[1:]]
    ep = next((a for a in args if not a.startswith("-")), None)
    only_body = "--body" in args
    only_shorts = "--shorts" in args
    quiet = "--quiet" in args
    file_opt = next((a.split("=", 1)[1] for a in args if a.startswith("--file=")), None)
    kind_opt = next((a.split("=", 1)[1] for a in args if a.startswith("--kind=")), "body")

    rows = []
    if file_opt:
        path = os.path.abspath(file_opt)
        out_dir = os.path.dirname(path)
        if not os.path.exists(path):
            print("[spec] 오류: 파일 없음 — %s" % path)
            sys.exit(1)
        p = probe(path)
        tag = os.path.basename(path)
        rows.append(Row(tag, "파일", tag, kind_opt, "INFO",
                        "%.1f MB" % (os.path.getsize(path) / 1e6)))
        check_video_spec(rows, tag, p, kind_opt)
        check_audio_format(rows, tag, p["sample_rate"], p["channels"], "mp4 컨테이너 실측")
        check_loudness(rows, tag, path)
        # 개별 파일 검사는 편 단위 리포트(_spec_report.json)를 덮어쓰지 않는다 —
        # 한 파일만 본 결과가 '그 편 전체를 검사한 결과'로 오인되면 안 된다.
        report_path = os.path.join(out_dir, "_spec_report_%s.json" % os.path.splitext(tag)[0])
    else:
        if not ep:
            print(__doc__)
            sys.exit(1)
        out_dir = os.path.join(ROOT, "video", "output", "%s_v2" % ep)
        if not os.path.isdir(out_dir):
            print("[spec] 오류: 출력 폴더 없음 — %s" % out_dir)
            sys.exit(1)
        # 범위 표식은 '추가된 구간을 통째로 도장 찍는' 방식으로 단다 — 32곳의
        # Row 생성부에 일일이 인자를 넣으면 언젠가 한 곳을 빠뜨린다.
        if not only_shorts:
            n0 = len(rows)
            verify_body(rows, ep, out_dir)
            for r in rows[n0:]:
                r.scope = "body"
        if not only_body:
            n0 = len(rows)
            verify_shorts(rows, ep, out_dir)
            for r in rows[n0:]:
                r.scope = "shorts"
        report_path = os.path.join(out_dir, "_spec_report.json")

    # 이번 실행이 커버한 범위를 표시 — 부분 검사(--body/--shorts)가 반대쪽 결과를
    # 지워버리지 않게 하기 위한 표식이다. build_v2 --full 이 본편만, build_shorts
    # --full 이 쇼츠만 검사해 각각 리포트를 쓰면, 병합 없이는 뒤엣것이 앞엣것을
    # 덮어써 '검사한 적 없는 축'이 리포트에서 사라진다(= 결함 2 와 같은 부류).
    scopes = set(r.scope for r in rows if r.scope)
    for r in rows:
        if not r.scope:
            r.scope = "file"

    fails = [r for r in rows if r.verdict == "FAIL"]
    warns = [r for r in rows if r.verdict == "WARN"]
    code = 2 if fails else 0

    if not quiet:
        print(render_table(rows))
        print("")
    if fails:
        print("[spec] 미달 %d건:" % len(fails))
        for r in fails:
            print("  - %s / %s: 실측 %s ≠ 기준 %s %s"
                  % (r.target, r.item, r.measured, r.expected,
                     ("(%s)" % r.note) if r.note else ""))
    if warns:
        print("[spec] 경고 %d건(차단 아님):" % len(warns))
        for r in warns:
            print("  - %s / %s: 실측 %s (기준 %s)" % (r.target, r.item, r.measured, r.expected))

    # 이전 실행이 검사한 '다른 범위'의 행은 살려서 합친다(같은 범위는 새 값으로 교체).
    kept = []
    if scopes and os.path.exists(report_path):
        try:
            with open(report_path, encoding="utf-8") as f:
                prev = json.load(f)
            kept = [d for d in prev.get("rows", []) if d.get("scope") and d["scope"] not in scopes]
        except (OSError, ValueError):
            kept = []
    all_rows = kept + [r.as_dict() for r in rows]
    a_fail = [d for d in all_rows if d["verdict"] == "FAIL"]
    a_warn = [d for d in all_rows if d["verdict"] == "WARN"]

    payload = {"episode": ep, "generated_by": "video/verify_output_spec.py",
               "scopes_checked": sorted(set(d.get("scope", "") for d in all_rows)),
               "scopes_this_run": sorted(scopes) if scopes else ["file"],
               "verdict": "FAIL" if a_fail else "PASS",
               "exit_code": code,
               "counts": {"total": len(all_rows), "fail": len(a_fail), "warn": len(a_warn),
                          "pass": len([d for d in all_rows if d["verdict"] == "PASS"])},
               "standards": {"res_body": list(RES_BODY), "res_shorts": list(RES_SHORTS),
                             "fps": FPS_REQUIRED, "lufs": LUFS_TARGET, "lufs_tol": LUFS_TOL,
                             "true_peak_max": TRUE_PEAK_MAX, "sr_recommend": SR_RECOMMEND,
                             "silence_ratio_max": SILENCE_RATIO_MAX,
                             "silence_gap_max": SILENCE_GAP_MAX, "dur_tol": DUR_TOL},
               "rows": all_rows}
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        extra = ""
        if kept:
            extra = " / 이전 범위 %d행 병합" % len(kept)
        print("[spec] 판정: %s (이번 실행 미달 %d·경고 %d%s) → %s"
              % (payload["verdict"], len(fails), len(warns), extra, report_path))
    except OSError as e:
        print("[spec] 경고: 리포트 저장 실패 — %s" % e)
    sys.exit(code)


if __name__ == "__main__":
    main()
