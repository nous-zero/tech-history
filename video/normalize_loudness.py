# -*- coding: utf-8 -*-
"""
내레이션 라우드니스 정규화 — 조각 묶음 전체를 '하나의 소리'로 보고 목표 LUFS 에 맞춘다.

핵심 설계(2026-07-29 실측으로 결정):
  * 조각별 개별 정규화 금지. 15조각에 **동일한 게인·리미터**를 걸어 조각 간 상대 균형을 보존한다.
    (조각별로 각각 -16 에 맞추면 TTS 테이크 편차가 인위적으로 평탄해지고 순서가 뒤집힌다.)
  * 목표는 **조립 트랙**(인트로 무음 + 조각 + 조각 사이 GAP) 기준으로 잰다. 조각 하나하나가
    아니라 시청자가 실제로 듣는 트랙이 기준이기 때문.
  * 압축기(컴프레서)는 기본 미사용. 게인 + 트루피크 리미터만으로 목표에 닿으면 그게 최선이다.

왜 -16 LUFS 인가 (3편 실측):
  | 목표    | 필요 게인 | LRA(다이내믹 폭) | 포락선상관(원음 충실도) |
  | -16     | +7.5dB   | 3.2              | 0.936                   |
  | -15     | +11.5dB  | 2.4              | 0.862                   |
  | -14     | +16.3dB  | 2.0              | 0.784                   |
  -14 는 2dB 더 크게 들리자고 표현력을 절반으로 깎는다. 유튜브는 기준보다 큰 소리를 낮출 뿐
  작은 소리를 올리지 않으므로 -16 과 -14 의 체감차는 2dB 뿐이고, 다이내믹 손실은 되돌릴 수 없다.
  또한 BGM 을 나중에 얹을 헤드룸(여유 공간)이 필요하다.

사용법:
  python video/normalize_loudness.py --in=<조각 폴더> --out=<출력 폴더> [--lufs=-16] [--tp=-1.0]
    --gap=0.35 --intro=2.8   조립 트랙 계산용(build_v2.py 상수와 맞출 것)
    --comp                   목표가 게인만으로 안 닿을 때 압축기 허용(기본 미사용)
    --dry                    쓰지 않고 수렴 결과만 출력

주의: 라우드니스는 길이를 바꾸지 않는다 → 영상 재렌더 불필요, 재먹싱만으로 교체 가능.
"""
import sys, io, os, re, wave, contextlib, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()


def opt(n, d):
    for a in sys.argv[1:]:
        if a.startswith(f"--{n}="):
            return a.split("=", 1)[1]
    return d


def flag(n):
    return any(a == f"--{n}" for a in sys.argv[1:])


def run(af, s, d):
    subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", s, "-af", af,
                    "-ac", "1", "-c:a", "pcm_s16le", d], check=True)


def loud(p):
    r = subprocess.run([FF, "-hide_banner", "-nostats", "-i", p, "-af",
                        "loudnorm=print_format=summary", "-f", "null", "-"],
                       capture_output=True, text=True, errors="replace")
    g = lambda k: float(re.search(rf"Input {k}:\s+([+-]?[\d.]+|-?inf)", r.stderr).group(1))
    return g("Integrated"), g("True Peak"), g("LRA")


def rd(p):
    with contextlib.closing(wave.open(p)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64), w.getframerate()


def assemble(files, out, intro, gap):
    x0, sr = rd(files[0])
    parts = [np.zeros(int(intro * sr))]
    for f in files:
        x, _ = rd(f)
        parts += [x, np.zeros(int(gap * sr))]
    x = np.concatenate(parts)
    with contextlib.closing(wave.open(out, "wb")) as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(np.clip(x, -32768, 32767).astype("<i2").tobytes())
    return loud(out)


def envcorr(a, b, sr):
    """20ms 포락선 상관 — 처리본이 원음의 강약 형태를 얼마나 따라가는가(1.0 = 완전 동일)."""
    W = int(0.020 * sr); n = min(len(a), len(b)) // W * W
    ea = np.abs(a[:n].reshape(-1, W)).mean(1); eb = np.abs(b[:n].reshape(-1, W)).mean(1)
    m = (ea > 50) | (eb > 50)
    return float(np.corrcoef(ea[m], eb[m])[0, 1]) if m.sum() > 10 else float("nan")


def main():
    src = os.path.abspath(opt("in", "")); dst = os.path.abspath(opt("out", ""))
    target = float(opt("lufs", -16.0)); tp_max = float(opt("tp", -1.0))
    intro = float(opt("intro", 2.8)); gap = float(opt("gap", 0.35))
    use_comp, dry = flag("comp"), flag("dry")
    if not os.path.isdir(src):
        print("--in=<조각 wav 폴더> 필요"); sys.exit(2)
    names = sorted(f for f in os.listdir(src) if re.fullmatch(r"seg\d{3}\.wav", f))
    if not names:
        print(f"segNNN.wav 를 찾지 못함: {src}"); sys.exit(2)
    work = dst if (dst and not dry) else os.path.join(src, "_ln_tmp")
    os.makedirs(work, exist_ok=True)
    probe = os.path.join(work, "_track.wav")

    I0, TP0, LRA0 = assemble([os.path.join(src, n) for n in names], probe, intro, gap)
    print(f"입력 조립 트랙: {I0:.1f} LUFS / TP {TP0:.1f} dBTP / LRA {LRA0:.1f} LU  ({len(names)}조각)")

    comp = ("acompressor=threshold=-16dB:ratio=3:attack=5:release=140:knee=6:makeup=1,"
            if use_comp else "")
    g, c = target - I0, tp_max - 1.5
    for it in range(12):
        af = f"{comp}volume={g:.2f}dB,alimiter=limit={10**(c/20):.4f}:attack=5:release=60:level=disabled"
        for n in names:
            run(af, os.path.join(src, n), os.path.join(work, n))
        I, TP, LRA = assemble([os.path.join(work, n) for n in names], probe, intro, gap)
        print(f"  반복{it}: 게인 {g:+.2f}dB / 천장 {c:.2f}dBFS -> {I:.2f} LUFS / TP {TP:.2f} dBTP")
        if abs(I - target) <= 0.1 and TP <= tp_max:
            break
        if TP > tp_max: c -= (TP - tp_max) + 0.1
        if abs(I - target) > 0.1: g += (target - I) * 0.9
    else:
        print("!! 수렴 실패 — --comp 로 압축기를 허용하거나 목표를 완화할 것")

    ec, clip = [], 0
    for n in names:
        a, sr = rd(os.path.join(src, n)); b, _ = rd(os.path.join(work, n))
        ec.append(envcorr(a, b, sr)); clip += int((np.abs(b) >= 32767).sum())
    print(f"\n확정 필터: {af}")
    print(f"결과: {I:.1f} LUFS / TP {TP:.1f} dBTP / LRA {LRA0:.1f} -> {LRA:.1f} LU")
    print(f"검수: 클리핑 {clip} 샘플 / 포락선상관 평균 {np.mean(ec):.3f} (최저 {min(ec):.3f})")
    if np.mean(ec) < 0.90:
        print("  경고: 충실도 0.90 미만 — 목표가 소재에 비해 과하다. 목표를 낮출 것.")
    if os.path.exists(probe): os.remove(probe)
    if dry:
        for n in names: os.remove(os.path.join(work, n))
        os.rmdir(work); print("[DRY] 파일 미기록")


if __name__ == "__main__":
    main()
