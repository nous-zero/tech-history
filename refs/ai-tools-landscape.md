# 무료 AI 도구 지형도 (2026-07-28 조사)

tech-scout(신기술)·asset-creator(소재 제작)·audio-producer(음성) 에이전트의 공용 지식 베이스.
환경 전제: 로컬 GPU 2GB(약함) → 무료 코랩 T4(16GB)·캐글이 주력. 라이선스 표기: 상업 사용 가능 여부가 핵심 판정 기준.
[❓]=미검증 — 사용 전 반드시 원문 재확인. **"무료 티어 상업 가능" 주장은 사용 시점에 약관 재검증 의무**(2026 1분기에도 정책 변경 다수).

## 1. TTS/음성 복제 (한국어) — 현 주력: Chatterbox Multilingual + GPT-SoVITS(파인튜닝 중)

| 모델 | 라이선스 | 한국어 | 복제 | 비고 |
|---|---|---|---|---|
| **Qwen3-TTS**(알리바바, 2026-01) | Apache 2.0 ✅ | 예(10개 언어) | 3초 급속 복제 | 0.6B/1.7B — T4 여유. **Chatterbox의 1순위 도전자**(벤치마크 우수 주장은 2차 출처 — 귀로 판정 필요) |
| **CosyVoice 3**(2025-12) | Apache 2.0 ✅ | 예(9개 언어) | 제로샷 | 0.5B — 경량 백업 |
| IndexTTS-2 | **상업 별도 문의**(제한) | [❓] | 예 | 수익화 채널엔 라이선스 확인 전 금지 |
| Kokoro(82M) | Apache 2.0 | 준수(복제 불가) | 아니오 | CPU 가능 |
| XTTS v2 | CPML=**비상업** | 예 | 예 | 수익화 채널 사용 불가 |

## 2. AI 영상 생성

- **Wan 2.2**(알리바바) — **Apache 2.0, 산출물 제약 없음**. TI2V-5B는 T4 적합, 14B는 GGUF 양자화로 16GB 구동(느림). 기성 코랩 노트북 존재(theelderemo/wan2.2-google-colab, Isi-dev, Wan2GP). **무료·상업안전 B롤 생성의 기본값.**
- LTX-Video/2.3 — 최속(2~3배), 스타일라이즈 모션.
- **HunyuanVideo — 함정**: 라이선스가 **한국에서 명시적 사용 불가**(Tencent Community License 지역 제외) → 우리는 못 씀.
- 웹 무료 티어(Kling·Luma·Pika·Hailuo): 상업권 출처 상충·[❓] — **수익화 영상엔 초안/프리비즈 용도만**, 본편은 오픈소스(Wan)로.

## 3. AI 이미지 생성

- **FLUX.1 schnell** — Apache 2.0, 상업 자유, T4 OK. (FLUX.1 dev는 비상업 가중치 — 주의)
- **Qwen-Image** — Apache 2.0, **다국어(한글) 텍스트 렌더링 최강** — 한글 썸네일에 직접 유용.
- SDXL — 관대한 라이선스+LoRA 생태계. SD3.5 — 매출 한도부 커뮤니티 라이선스.

## 4. 사료 복원 — 이 채널의 최고 레버리지 카테고리

- 업스케일: **Real-ESRGAN**(BSD, T4 여유·CPU 가능)
- 얼굴 복원: **CodeFormer**(품질 우수하나 S-Lab 라이선스 **비상업 — 산출물 범위 [❓], 수익화 사용 전 확인**) / GFPGAN(Apache 2.0 — 안전 대체)
- 흑백 채색: **DDColor**(Apache 2.0) — DeOldify 대체 SOTA
- 영상 복원: **SeedVR2**(ByteDance, ICLR 2026) — 시간 일관성 강한 4x 영상 업스케일, ComfyUI 저VRAM 노드 존재. 라이선스 [❓] 확인 후 도입. "복원된 역사"를 채널 시그니처로 만들 기회.

## 5. AI 음악/BGM

- **ACE-Step 1.5**(2026-01) — **MIT, 라이선스 정리된 학습 데이터, <4GB VRAM, Suno v5보다 우수 평가(SongEval)**. **다큐 BGM의 정답 — 즉시 도입 권장.** (github.com/ace-step/ACE-Step-1.5)
- YuE 7B — Apache 2.0, 보컬 곡. Stable Audio Open — 매출 한도부. MusicGen — 가중치 CC-BY-NC → 수익화 위험.
- **Suno 무료 티어 = 수익화 금지**(소급 불가) — 사용 금지.

## 6. 자동 편집·자막·쇼츠

- AI-Youtube-Shorts-Generator(오픈소스 OpusClip 대체: LLM 하이라이트+Whisper+9:16 자동 크롭)
- OpenShorts(셀프호스팅: faster-whisper 단어 자막+얼굴 추적 세로 리프레임)
- FunClip(ModelScope: 전사+LLM 클리핑+무음 제거) / auto-editor(pip, 무음 컷)
- 전부 CPU 가능 — 기존 faster-whisper 재활용.

## 7. 아바타/립싱크 (필요 시만 — 얼굴 없는 채널이라 저순위)

- LatentSync(ByteDance, Apache 2.0) / MuseTalk(Tencent) / SadTalker(구형).

## 8. 무료 컴퓨트 (코랩 너머)

| 서비스 | 무료 쿼터 | 비고 |
|---|---|---|
| **Kaggle** | **주 30시간 보장**, T4 x2/P100, 세션 9h | 카드 불요. **오늘 추가하면 무료 GPU 2배** |
| Lightning AI | 월 ~80h 상당 [❓] | 폰 인증, 실개발 환경 |
| HF Spaces ZeroGPU | 일 ~3.5분(공유 H200 — 초대형 VRAM) | 대형 모델 맛보기용 |
| Modal | 월 $30 크레딧 [❓] | 카드 필요 |

## 9. 월간 스카우팅 루틴 (tech-scout 표준 절차)

1. HF Trending(models?sort=trending — TTS/영상/이미지 필터) — 주 1회 10분
2. Reddit: r/StableDiffusion(영상·이미지 SOTA 최초 상륙지)·r/LocalLLaMA(TTS·로컬 모델)·r/comfyui(저VRAM 워크플로)
3. GitHub Trending(python, 주간) + Topics: text-to-speech·video-generation
4. HF Daily Papers(huggingface.co/papers) — papers-with-code의 사실상 후계
5. 뉴스레터: Ben's Bites·TLDR AI·The Rundown
6. 릴리스 트래커: llm-stats.com/llm-updates · aireleasetracker.com

## 지금 당장 채널을 가장 개선하는 우선순위 (2026-07-28 판정)

1. **BGM: ACE-Step 1.5 즉시 도입** — Suno 무료 티어 수익화 금지 문제를 근본 해결
2. **사료 복원 파이프라인**: Real-ESRGAN + GFPGAN(얼굴) + DDColor(채색) + SeedVR2(영상, 라이선스 확인 후) — "복원된 역사" 시그니처
3. **TTS 결선**: Qwen3-TTS-1.7B vs Chatterbox — 같은 한국어 문단으로 반나절 A/B
4. **B롤: Wan 2.2 TI2V-5B 코랩** — 분위기 컷 생성
5. **쇼츠: OpenShorts류 셀프호스팅** — 구독료 $0
6. **컴퓨트: 캐글 계정 추가** — 무료 GPU 예산 2배

미검증 잔여([❓]): Pika 무료 상업권 / IndexTTS-2 라이선스 / CodeFormer 산출물 상업 / SeedVR2 라이선스 / Modal 금액 / Qwen3-TTS 한국어 실청감.
