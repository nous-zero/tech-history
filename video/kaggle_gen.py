import json, os, re, shutil
import requests

cfg = json.load(open("gen_config.json"))
EPISODE, ONLY = cfg["episode"], cfg["only"]

import torch, torchaudio
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

url = f"https://raw.githubusercontent.com/nous-zero/tech-history/main/video/scripts/{EPISODE}.json"
script = requests.get(url).json()
print("대본:", script["title"], "/ 문단", len(script["segments"]), flush=True)

device = "cuda" if torch.cuda.is_available() else "cpu"
print("장치:", device, flush=True)
assert device == "cuda", "GPU가 안 잡혔습니다 — 오른쪽 Session options에서 Accelerator를 GPU로 바꾸세요"
model = ChatterboxMultilingualTTS.from_pretrained(device=device)

# --- 숫자 → 한글 발음 변환 (TTS 입력 전용 — 화면 자막은 원문 숫자 유지) ---
_SINO = "영일이삼사오육칠팔구"

def _sino(n):
    n = int(n)
    if n == 0:
        return "영"
    out = ""
    for val, name in ((10000, "만"), (1000, "천"), (100, "백"), (10, "십"), (1, "")):
        d, n = n // val, n % val
        if d:
            out += ("" if d == 1 and name else _SINO[d]) + name
    return out

_MONTH = {6: "유", 10: "시"}  # 6월=유월, 10월=시월

def normalize_numbers(t):
    t = re.sub(r"(\d+)월", lambda m: (_MONTH.get(int(m.group(1))) or _sino(m.group(1))) + "월", t)
    return re.sub(r"\d+", lambda m: _sino(m.group(0)), t)

REF = "ref.wav" if os.path.exists("ref.wav") else None  # 육성 복제용(선택)
if REF:
    # 주의: ONLY 부분 재생산은 기존 조각들도 같은 ref로 만들어졌을 때만 사용
    print("ref.wav 감지 — 육성 복제 모드,", f"부분 재생산 {ONLY}" if ONLY else "전체 생산", flush=True)
out_dir = f"voice_{EPISODE}_fix"
shutil.rmtree(out_dir, ignore_errors=True)  # 이전 실행 잔존 파일 제거 — 산출물은 이번 생산분만
os.makedirs(out_dir)
for seg in script["segments"]:
    if ONLY and seg["id"] not in ONLY:
        continue
    text = normalize_numbers(seg["text"])
    print(f"seg{seg['id']:03d} 읽을 문장: {text}", flush=True)
    kwargs = {"language_id": "ko"}
    if REF:
        kwargs["audio_prompt_path"] = REF
    limit = 0.25 * len(text) + 5  # 비정상 길이(환각 반복) 감시선
    for attempt in range(3):
        wav = model.generate(text, **kwargs)
        sec = wav.shape[-1] / model.sr
        if sec <= limit:
            break
        print(f"  {sec:.1f}초 — 비정상(기준 {limit:.0f}초), 재시도 {attempt + 1}/3", flush=True)
    torchaudio.save(os.path.join(out_dir, f"seg{seg['id']:03d}.wav"), wav, model.sr)
    print(f"seg{seg['id']:03d} 완료 ({sec:.1f}초)", flush=True)
print("합성 완료:", "전체" if not ONLY else f"세그먼트 {ONLY}", flush=True)
