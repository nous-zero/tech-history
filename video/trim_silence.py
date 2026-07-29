# -*- coding: utf-8 -*-
"""
내레이션 '사이(dead air)' 다듬기 — TTS 세그먼트의 과도한 무음을 상한선까지 줄인다.

배경(2026-07-29 실측): 3편 TTS의 조음 속도(침묵 제외)는 7.4자/초로 사용자 육성
녹음 4.62자/초보다 1.6배 빠르다. 즉 "말이 느린" 것이 아니라 "사이가 긴" 것이
본편의 늘어지는 느낌의 원인이다. 따라서 배속(atempo)이 아니라 무음 다듬기로
교정한다 — 배속은 이미 빠른 조음을 더 빠르게 만들어 부자연스러워진다.

사용법:
  python video/trim_silence.py --in=video/output/03_v2/audio --out=<dir> [옵션]
  주요 옵션(기본값):
    --lead=0.15    앞 무음 상한(초)
    --trail=0.15   뒤 무음 상한(초)
    --inner=0.40   문장 사이(내부) 무음 상한(초)
    --noise=-35dB  무음 판정 임계(silencedetect)
    --mind=0.15    무음으로 셀 최소 길이(초)
    --xfade=0.012  이어붙이는 지점 크로스페이드(초) — 클릭음 방지
    --dry          실제 파일을 쓰지 않고 예상 수치만 출력

주의: 길이가 바뀌므로 영상 재렌더가 필요하다(build_v2.py는 wav 길이로 타이밍을 잡는다).
"""
import sys, io, os, re, wave, subprocess, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()


def opt(name, default):
    for a in sys.argv[1:]:
        if a.startswith(f"--{name}="):
            return a.split("=", 1)[1]
    return default


def flag(name):
    return any(a == f"--{name}" for a in sys.argv[1:])


def detect_silences(path, noise, mind):
    """ffmpeg silencedetect로 무음 구간 [(시작s, 끝s), ...]을 얻는다."""
    r = subprocess.run([FF, "-hide_banner", "-nostats", "-i", path,
                        "-af", f"silencedetect=noise={noise}:d={mind}",
                        "-f", "null", "-"],
                       capture_output=True, text=True, errors="replace")
    out, cur = [], None
    for m in re.finditer(r"silence_(start|end): (-?[\d.]+)", r.stderr):
        k, v = m.group(1), float(m.group(2))
        if k == "start":
            cur = v
        elif cur is not None:
            out.append((max(cur, 0.0), v))
            cur = None
    return out


def read_wav(path):
    with contextlib.closing(wave.open(path, "rb")) as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2, "모노 16bit wav만 지원"
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32)
    return x, sr


def write_wav(path, x, sr):
    x = np.clip(x, -32768, 32767).astype("<i2")
    with contextlib.closing(wave.open(path, "wb")) as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(x.tobytes())


def plan_cuts(sil, dur, lead, trail, inner):
    """무음 구간별로 '잘라낼 구간'(시작s, 끝s) 목록을 만든다.
    앞·뒤는 상한을 남기고 바깥쪽을, 내부는 상한을 남기고 가운데를 잘라낸다."""
    cuts = []
    for (a, b) in sil:
        length = b - a
        if a <= 0.05:                      # 앞 무음
            keep = lead
            if length > keep:
                cuts.append((a, b - keep))  # 발화 직전 keep초만 남김
        elif b >= dur - 0.05:              # 뒤 무음
            keep = trail
            if length > keep:
                cuts.append((a + keep, b))
        else:                              # 내부(문장 사이) 무음
            keep = inner
            if length > keep:
                mid = (a + b) / 2.0
                cuts.append((mid - (length - keep) / 2.0, mid + (length - keep) / 2.0))
    return [(a, b) for (a, b) in cuts if b - a > 0.005]


def apply_cuts(x, sr, cuts, xfade):
    """잘라낸 뒤 이어붙이기. 접합부는 짧은 크로스페이드로 불연속(클릭음)을 막는다."""
    n = len(x)
    keep = []
    prev = 0
    for (a, b) in cuts:
        s, e = int(round(a * sr)), int(round(b * sr))
        s, e = max(0, min(n, s)), max(0, min(n, e))
        if s > prev:
            keep.append((prev, s))
        prev = max(prev, e)
    if prev < n:
        keep.append((prev, n))
    if not keep:
        return x
    f = max(1, int(round(xfade * sr)))
    out = x[keep[0][0]:keep[0][1]].copy()
    for (s, e) in keep[1:]:
        piece = x[s:e].copy()
        m = min(f, len(out), len(piece))
        if m > 1:
            ramp = np.linspace(0.0, 1.0, m, dtype=np.float32)
            tail = out[-m:] * (1.0 - ramp) + piece[:m] * ramp
            out = np.concatenate([out[:-m], tail, piece[m:]])
        else:
            out = np.concatenate([out, piece])
    return out


def main():
    src_dir = os.path.abspath(opt("in", ""))
    dst_dir = os.path.abspath(opt("out", ""))
    lead = float(opt("lead", 0.15)); trail = float(opt("trail", 0.15))
    inner = float(opt("inner", 0.40)); xfade = float(opt("xfade", 0.012))
    noise = opt("noise", "-35dB"); mind = float(opt("mind", 0.15))
    dry = flag("dry")
    if not src_dir or not os.path.isdir(src_dir):
        print("--in=<세그먼트 wav 폴더> 필요"); sys.exit(2)
    if not dry:
        if not dst_dir:
            print("--out=<출력 폴더> 필요"); sys.exit(2)
        os.makedirs(dst_dir, exist_ok=True)

    files = sorted(f for f in os.listdir(src_dir)
                   if re.fullmatch(r"seg\d{3}\.wav", f))
    print(f"# trim_silence  lead={lead} trail={trail} inner={inner} "
          f"noise={noise} mind={mind} xfade={xfade}{' [DRY]' if dry else ''}")
    print("| 파일 | 전(s) | 후(s) | 감소(s) | 감소% | 컷수 |")
    print("|---|---|---|---|---|---|")
    b_tot = a_tot = 0.0
    for fn in files:
        sp = os.path.join(src_dir, fn)
        x, sr = read_wav(sp)
        dur = len(x) / sr
        cuts = plan_cuts(detect_silences(sp, noise, mind), dur, lead, trail, inner)
        y = apply_cuts(x, sr, cuts, xfade)
        nd = len(y) / sr
        if not dry:
            write_wav(os.path.join(dst_dir, fn), y, sr)
        b_tot += dur; a_tot += nd
        print(f"| {fn} | {dur:.2f} | {nd:.2f} | {dur-nd:.2f} | "
              f"{100*(dur-nd)/dur:.1f}% | {len(cuts)} |")
    print(f"\n합계: {b_tot:.2f}s → {a_tot:.2f}s (감소 {b_tot-a_tot:.2f}s, "
          f"{100*(b_tot-a_tot)/b_tot:.1f}%)")


if __name__ == "__main__":
    main()
