# -*- coding: utf-8 -*-
"""본편 BGM 믹싱 — 내레이션 트랙 아래에 음악 침대(bed)를 정해진 상대 레벨로 깐다.

왜 이 파일이 따로 있나
  build_v2.py 는 2,700줄짜리 영상 조립기이고 지금도 여러 담당이 동시에 고친다.
  BGM 은 '오디오' 관할이므로 로직을 이 모듈에 모으고, build_v2 에는 호출 두 줄만
  심는다(충돌 면적 최소화). 쇼츠(build_shorts.py:145 make_bgm)는 numpy 로 비트를
  '합성'하지만, 본편은 다큐 톤이라 합성 비트가 맞지 않아 **라이선스가 소스에서
  나오는 실제 음원**을 쓴다(refs/free-media-sources.md 3절 해법 그대로).

무엇을 만드나 (본편 폴더 video/output/NN_v2/ 기준)
  episode_bgm.wav  — 내레이션 길이에 맞춘 BGM 침대(게인·페이드 적용 후). 이 파일의
                     존재 여부를 verify_output_spec.check_bgm 이 검사한다.
  episode_mix.wav  — 내레이션 + BGM 최종 믹스. 먹싱에 실제로 들어가는 소리.
  episode_track.wav 는 **건드리지 않는다** — 무음 비율·길이 불변식을 재는 기준이
  내레이션 단독 트랙이어야 하기 때문(BGM 이 섞이면 무음을 잴 수 없다, rule6).

레벨 기준 (추정이 아니라 현행 쇼츠에서 뽑은 실측 — refs/audio-bgm-proposal.md 2절)
  내레이션 대비 BGM **-19 LU**(허용 -18 ~ -22 LU). 쇼츠 실측: BGM -29.1 LUFS 에
  게인 -13dB → 실효 -42.1, 믹스 -22.8 → 차 약 19 LU.
  '몇 dB 를 걸까'를 고정하지 않고 **매번 두 소리를 재서 필요한 게인을 계산**한다 —
  음원이 바뀌어도 귀에 들리는 비율이 유지된다(음원마다 마스터 레벨이 다르므로
  고정 게인은 음원이 바뀌는 순간 틀린 값이 된다).

덕킹(음성이 나올 때 음악을 자동으로 낮추는 것)은 쓰지 않는다.
  무음 다듬기로 문장 사이가 0.40초 상한까지 줄어 반응이 느린 덕킹은 오히려
  펌핑(음악이 들썩임)을 만든다 — 정적 -19 LU 고정이 먼저다(제안서 2절 권고).

음원 선택은 이 파일이 아니라 **video/bgm_manifest.json**(저장소에 커밋됨)에 적는다.
음원 파일 자체는 video/output/ 아래라 .gitignore 대상이므로, '어떤 음원을 썼는지'는
매니페스트와 refs/asset-ledger.md 두 곳에 글자로 남는다(파일이 없어도 복원 가능).

단독 실행(검증용):
  python video/bgm.py 03 --dry     # 섞지 않고 게인 계산·검증만
  python video/bgm.py 03           # episode_bgm.wav + episode_mix.wav 생성
  python video/bgm.py 03 --source=video/output/assets/bgm/후보B.mp3   # 후보 A/B 청음
"""
import io
import json
import os
import re
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# 기준값 — 근거 없는 숫자를 두지 않는다(rule1·rule6).
# ---------------------------------------------------------------------------
BGM_OFFSET_LU = 19.0        # 내레이션 대비 BGM 을 얼마나 아래로 둘까(목표)
BGM_OFFSET_MIN = 18.0       # 허용 하한(이보다 작으면 BGM 이 말을 가린다)
BGM_OFFSET_MAX = 22.0       # 허용 상한(이보다 크면 있으나 마나)
FADE_IN_S = 3.0             # 인트로 카드(2.8초) 동안 서서히 올라온다
FADE_OUT_S = 4.0            # 아웃트로에서 서서히 사라진다
LOOP_XFADE_S = 3.0          # 음원이 짧아 이어 붙일 때 겹쳐 넘기는 길이(이음매 제거)
MIX_SR = 48000              # 믹스 샘플레이트. BGM 원음이 48kHz 라 여기에 맞춘다
MIX_CH = 2                  # 스테레오


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def manifest_path():
    return os.path.join(ROOT, "video", "bgm_manifest.json")


def load_manifest():
    p = manifest_path()
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def source_for(ep, override=None):
    """편 번호 → (음원 절대경로, 매니페스트 항목). 미지정이면 (None, 사유).

    override 는 매니페스트를 건너뛰고 특정 파일을 쓰게 한다 — 후보 음원을
    바꿔가며 같은 문단으로 A/B 청음할 때 쓴다(공통 수칙 2: 실측 우선)."""
    if override:
        p = override if os.path.isabs(override) else os.path.join(ROOT, override)
        if not os.path.exists(p):
            return None, "지정 음원 없음: %s" % p
        return p, {"file": override, "source": "(--source 로 직접 지정 — 대장 미확인)",
                   "license": "(미확인)"}
    man = load_manifest()
    entry = (man.get("episodes") or {}).get(str(ep))
    if not entry:
        return None, "bgm_manifest.json 에 %s편 항목이 없음" % ep
    rel = entry.get("file")
    if not rel:
        return None, "%s편 항목에 file 키가 없음" % ep
    path = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return None, "음원 파일 없음: %s" % path
    return path, entry


def measure(path):
    """통합 라우드니스·트루피크·LRA 실측(ffmpeg loudnorm 1패스 분석).

    '문서에 이렇게 적혀 있다'가 아니라 '지금 이 파일을 재서 이 값이 나온다'만
    통과로 인정한다(GOVERNANCE §8 전제조건 1)."""
    r = subprocess.run([ffmpeg(), "-hide_banner", "-nostats", "-i", path,
                        "-af", "loudnorm=print_format=summary", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    txt = r.stderr or ""

    def g(k):
        m = re.search(r"Input %s:\s+(-?[\d.]+|-?inf)" % k, txt)
        if not m:
            return None
        v = m.group(1)
        return float("-inf") if "inf" in v else float(v)

    return {"integrated": g("Integrated"), "true_peak": g("True Peak"), "lra": g("LRA")}


def decode_to_wav(src, dst, sr=MIX_SR, ch=MIX_CH):
    """음원(mp3 등)을 믹스 규격 wav 로 디코드. pydub 의 ffmpeg 자동탐색에 기대지
    않는다 — 이 PC 는 PATH 에 ffmpeg 가 없다(ep04 환경 실측)."""
    subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", src,
                    "-ar", str(sr), "-ac", str(ch), "-c:a", "pcm_s16le", dst],
                   check=True, capture_output=True)
    return dst


def _bed(seg, need_ms):
    """필요한 길이만큼 침대를 만든다. 음원이 짧으면 크로스페이드로 이어 붙인다.

    쉬운 말: 이불이 짧으면 같은 이불을 겹쳐 이어 붙이되, 이은 자리가 티 나지
    않게 3초 동안 서서히 겹쳐 넘긴다(딱 잘라 붙이면 '툭' 하는 이음매가 들린다)."""
    if len(seg) >= need_ms:
        return seg[:need_ms], 0
    x = int(LOOP_XFADE_S * 1000)
    x = min(x, max(0, len(seg) // 3))
    out, loops = seg, 0
    while len(out) < need_ms:
        out = out.append(seg, crossfade=x) if x > 0 else out + seg
        loops += 1
    return out[:need_ms], loops


def apply(ep, out_dir, stem, narration_wav, dry=False, override=None):
    """내레이션 트랙에 BGM 을 깔아 믹스를 만든다.

    반환: 먹싱에 쓸 오디오 경로. BGM 을 못 깔면 내레이션 경로를 그대로 돌려주고
    이유를 화면에 크게 남긴다 — 조용히 넘어가면 3편까지 BGM 부재가 무지적된
    사고(감사 결함 2)를 그대로 재발시킨다."""
    src, entry = source_for(ep, override)
    if src is None:
        print("[bgm] *** BGM 없음: %s ***" % entry)
        print("[bgm]     4편부터는 BGM 이 필수다(verify_output_spec.BGM_REQUIRED_FROM_EP) — "
              "video/bgm_manifest.json 에 음원을 등록할 것.")
        return narration_wav

    from pydub import AudioSegment

    print("[bgm] 음원: %s" % os.path.relpath(src, ROOT))
    print("[bgm]   출처 %s / 라이선스 %s"
          % (entry.get("source_url", "?"), entry.get("license", "?")))

    narr_m = measure(narration_wav)
    src_wav = os.path.join(out_dir, "_bgm_src_%dk.wav" % (MIX_SR // 1000))
    decode_to_wav(src, src_wav)

    narration = AudioSegment.from_wav(narration_wav)
    need_ms = len(narration)
    # 내레이션을 믹스 규격(48kHz 스테레오)으로 올려 담는다. 없던 정보가 생기지는
    # 않지만, BGM 이 진짜 48kHz 스테레오라 믹스를 24kHz 모노로 깎으면 음악 쪽 정보가 준다.
    #
    # ※ 모노를 두 채널에 그대로 복제하면 **측정 라우드니스가 3dB 올라간다** —
    #   BS.1770 은 채널별 에너지를 더하므로 같은 소리를 두 번 더하는 셈이기 때문.
    #   실측(2026-07-30, 3편 트랙): 보정 없이 섞었더니 믹스가 -13.1 LUFS 로 나와
    #   본편 규격 -16±1 을 벗어났다. 그래서 채널당 -3.01dB 를 걸어 '가운데 정위'로
    #   놓는다(에너지 보존). 추정이 아니라 아래에서 다시 재서 확인한다.
    #   쉬운 말: 같은 목소리를 스피커 두 대로 나눠 틀면 합쳐서 두 배 크게 들리니,
    #   한 대당 소리를 절반으로 줄여야 원래 크기가 된다.
    narr_mix = narration.set_frame_rate(MIX_SR).set_channels(MIX_CH)
    if narration.channels == 1 and MIX_CH == 2:
        narr_mix = narr_mix.apply_gain(-3.01)
    narr_ref_path = os.path.join(out_dir, "_bgm_narr_mixfmt.wav")
    narr_mix.export(narr_ref_path, format="wav")
    ref_m = measure(narr_ref_path)

    raw = AudioSegment.from_wav(src_wav)
    bed, loops = _bed(raw, need_ms)
    bed = bed.fade_in(int(FADE_IN_S * 1000)).fade_out(int(FADE_OUT_S * 1000))

    # 게인 계산 — 페이드까지 반영된 '실제 깔릴 소리'를 재고 목표 차이를 맞춘다.
    # 기준은 원본 모노 트랙이 아니라 **믹스 규격으로 변환한 내레이션**이다.
    # 두 소리를 같은 형식에서 재야 비교가 성립한다(형식이 다르면 3dB 가 숨는다).
    pre = os.path.join(out_dir, "_bgm_pre.wav")
    bed.export(pre, format="wav")
    pre_m = measure(pre)
    if ref_m["integrated"] is None or pre_m["integrated"] is None:
        print("[bgm] *** 라우드니스 측정 실패 — 게인을 추정으로 정하지 않는다(rule6). BGM 생략 ***")
        return narration_wav
    gain = (ref_m["integrated"] - BGM_OFFSET_LU) - pre_m["integrated"]
    print("[bgm] 내레이션 원본(%dHz %dch) %.1f LUFS → 믹스 규격(%dHz %dch) %.1f LUFS"
          % (narration.frame_rate, narration.channels, narr_m["integrated"],
             MIX_SR, MIX_CH, ref_m["integrated"]))
    print("[bgm] BGM 원본 %.1f LUFS → 게인 %+.2f dB (목표 차 %.0f LU)"
          % (pre_m["integrated"], gain, BGM_OFFSET_LU))
    if loops:
        print("[bgm] 음원 %.1fs < 필요 %.1fs → %d회 이어붙임(크로스페이드 %.1fs)"
              % (len(raw) / 1000.0, need_ms / 1000.0, loops, LOOP_XFADE_S))
    else:
        print("[bgm] 음원 %.1fs ≥ 필요 %.1fs → 루프 없음(앞부분만 사용)"
              % (len(raw) / 1000.0, need_ms / 1000.0))
    if dry:
        os.remove(pre)
        os.remove(narr_ref_path)
        return narration_wav

    bed = bed.apply_gain(gain)
    bgm_path = os.path.join(out_dir, "%s_bgm.wav" % stem)
    bed.export(bgm_path, format="wav")
    os.remove(pre)

    mix = bed.overlay(narr_mix)
    mix_path = os.path.join(out_dir, "%s_mix.wav" % stem)
    mix.export(mix_path, format="wav")

    # --- 자체 검수: 만든 것을 다시 재서 기준 안에 있는지 확인(rule4) ---
    bgm_m = measure(bgm_path)
    mix_m = measure(mix_path)
    off = ref_m["integrated"] - bgm_m["integrated"]
    ok = BGM_OFFSET_MIN <= off <= BGM_OFFSET_MAX
    print("[bgm] 실측 검수 — BGM %.1f LUFS / 내레이션 %.1f LUFS → 차 %.1f LU "
          "(기준 %.0f~%.0f) %s"
          % (bgm_m["integrated"], ref_m["integrated"], off,
             BGM_OFFSET_MIN, BGM_OFFSET_MAX, "통과" if ok else "*** 미달 ***"))
    print("[bgm] 믹스 %.1f LUFS / 트루피크 %.1f dBTP / 길이 %.2fs (내레이션 %.2fs)"
          % (mix_m["integrated"], mix_m["true_peak"] if mix_m["true_peak"] is not None else float("nan"),
             len(mix) / 1000.0, len(narration) / 1000.0))
    # 본편 규격 -16 LUFS(±1) 는 verify_output_spec 이 mp4 에서 다시 재지만, 여기서
    # 먼저 걸러야 70분 렌더 뒤에야 미달을 아는 낭비를 막는다.
    drift = mix_m["integrated"] - narr_m["integrated"]
    if abs(drift) > 0.7:
        print("[bgm] *** 경고: 믹스가 내레이션 대비 %+.1f dB 이동했다 — 본편 -16±1 규격을 "
              "벗어날 수 있다(채널·샘플레이트 변환 확인 필요) ***" % drift)
    if not ok:
        print("[bgm] *** 상대 레벨이 기준을 벗어났다 — 믹스를 쓰지 않고 내레이션만 넘긴다 ***")
        return narration_wav
    if abs(len(mix) - len(narration)) > 20:
        print("[bgm] *** 믹스 길이가 내레이션과 다르다 — 길이 불변식 위반, 내레이션만 넘긴다 ***")
        return narration_wav

    report = {"episode": str(ep), "source": os.path.relpath(src, ROOT),
              "manifest": entry, "gain_db": round(gain, 2), "loops": loops,
              "fade_in_s": FADE_IN_S, "fade_out_s": FADE_OUT_S,
              "narration_lufs_source": narr_m["integrated"],
              "narration_lufs_mixfmt": ref_m["integrated"],
              "bgm_lufs": bgm_m["integrated"],
              "offset_lu": round(off, 2), "offset_range": [BGM_OFFSET_MIN, BGM_OFFSET_MAX],
              "mix_lufs": mix_m["integrated"], "mix_true_peak": mix_m["true_peak"],
              "mix_seconds": round(len(mix) / 1000.0, 3),
              "sample_rate": MIX_SR, "channels": MIX_CH,
              "files": {"bgm": os.path.basename(bgm_path), "mix": os.path.basename(mix_path)}}
    with open(os.path.join(out_dir, "_bgm_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return mix_path


def main():
    args = sys.argv[1:]
    ep = next((a for a in args if not a.startswith("-")), None)
    if not ep:
        print(__doc__)
        return 1
    out_dir = os.path.join(ROOT, "video", "output", "%s_v2" % ep)
    stem = "episode"
    narr = os.path.join(out_dir, "%s_track.wav" % stem)
    if not os.path.exists(narr):
        print("[bgm] 오류: 내레이션 트랙 없음 — %s" % narr)
        return 1
    override = next((a.split("=", 1)[1] for a in args if a.startswith("--source=")), None)
    got = apply(ep, out_dir, stem, narr, dry="--dry" in args, override=override)
    print("[bgm] 먹싱에 쓸 오디오: %s" % os.path.relpath(got, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
