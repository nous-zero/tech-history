# -*- coding: utf-8 -*-
"""조립기 안전장치 자체 검사 — 렌더 없이 몇 초에 끝난다.

왜 있나: 이 저장소에는 테스트가 없었고, 그래서 "검사가 돌았다"와 "검사가 무언가를
봤다"를 구분해 주는 장치도 없었다(3편 보호영역 '침범 0건 / 등록 구역 0개' 사고).
안전장치를 넣었으면 **그 안전장치가 살아 있는지**도 기계가 스스로 말해야 한다.

검사 대상(2026-07-30 4편 이월 과업 ②③④):
  ② 법무 표기 캡션 20자 상한 + counsel §9-4 지속 공식
  ③ 본편 보호영역 — 구역 상자 계산·테두리 걸침 판정·강제/감사 전용 분리
  ④ 쇼츠 보호영역 — 카메라 상대 UI 대역 계산
  공통 [audit] 로그 형식 ↔ verify_output_spec 정규식의 계약

사용:  python video/selftest_guards.py            (전체)
      python video/selftest_guards.py --part=v2   (부분)
종료코드 0=전항 통과, 1=실패(무엇이 왜 틀렸는지 출력).

manim 의 전역 config(프레임 폭 등)를 본편(16:9)과 쇼츠(9:16)가 서로 다르게 쓰므로
파트마다 별도 프로세스로 돌린다 — 한 프로세스에서 둘 다 임포트하면 뒤에 임포트한
쪽 설정이 앞을 덮어써 검사 자체가 거짓말을 한다.
"""
import os
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
FAILS = []


def check(name, got, want):
    ok = got == want
    print(("  OK  " if ok else "  FAIL") + f" {name}: {got!r}" +
          ("" if ok else f" (기대 {want!r})"))
    if not ok:
        FAILS.append(name)


def check_raises(name, fn, exc):
    try:
        fn()
    except exc as e:
        print(f"  OK   {name}: 예외 발생 — {str(e).splitlines()[0][:70]}")
        return
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL {name}: 다른 예외 {type(e).__name__}: {e}")
        FAILS.append(name)
        return
    print(f"  FAIL {name}: 예외가 나지 않았다(막혔어야 한다)")
    FAILS.append(name)


def check_ok(name, fn):
    try:
        fn()
        print(f"  OK   {name}: 통과(막히면 안 되는 것)")
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL {name}: 통과해야 하는데 예외 — {type(e).__name__}: {e}")
        FAILS.append(name)


# ---------------------------------------------------------------- part: v2
def part_v2():
    print("[② 법무 표기 캡션 + ③ 본편 보호영역]")
    sys.argv = ["build_v2.py", "03", "--layout-audit"]
    sys.path.insert(0, HERE)
    import build_v2 as B

    # ② counsel 4편 단일 규칙: 20자 이내 + 최소 3.5초.
    #    요구 지속 = max(2.0, 문자수÷6, 3.5) — 20자 이내는 전부 3.5초로 수렴하고,
    #    레거시처럼 20자를 넘는 문구만 공식이 3.5초를 넘어선다.
    check("상한 상수", B.LEGAL_CAPTION_MAX, 20)
    check("단일 규칙 하한", B.LEGAL_MIN_HOLD, 3.5)
    check("지속요구 6자", round(B.legal_min_seconds("가나다라마바"), 3), 3.5)
    check("지속요구 20자", round(B.legal_min_seconds("가" * 20), 3), 3.5)
    check("지속요구 21자(공식이 3.5 미만)", round(B.legal_min_seconds("가" * 21), 3), 3.5)
    check("지속요구 33자(공식이 3.5 초과)", round(B.legal_min_seconds("가" * 33), 3), 5.5)
    check("20자÷6 < 3.5 검산", round(20 / 6, 3) < B.LEGAL_MIN_HOLD, True)

    # ② 상한 강제: 21자 차단 / 20자 통과 / 레거시 등록분만 예외
    check_raises("21자 신규 차단", lambda: B.legal_chip("가" * 21), B.LegalCaptionError)
    check_ok("20자 통과", lambda: B.legal_chip("가" * 20))
    legacy = "최초의 웹사이트 — '웹이란 무엇인가' 안내문 (재현 화면)"
    check("레거시 표 등록 확인", ("03", legacy) in B.LEGAL_CAPTION_LEGACY, True)
    check_ok("레거시 33자(03편) 통과", lambda: B.legal_chip(legacy))
    B.EP = "04"
    check_raises("레거시 33자(04편) 차단",
                 lambda: B.legal_chip(legacy), B.LegalCaptionError)
    B.EP = "03"

    # ③ 상자 겹침·포함 판정(테두리 걸침 = '반은 안, 반은 밖')
    E = B.EpisodeBase
    photo = (-2.0, 2.0, -1.0, 1.0)
    check("완전히 안(의도한 겹쳐찍기)", E._contains(photo, (-1.0, 1.0, -0.5, 0.5)), True)
    check("완전히 밖", B.rect_overlap(photo, (3.0, 4.0, -1.0, 1.0)), None)
    straddle = (1.0, 3.0, -0.5, 0.5)      # 오른쪽 테두리를 문 상태
    check("테두리 걸침 = 겹침 있음", B.rect_overlap(photo, straddle) is not None, True)
    check("테두리 걸침 = 포함 아님", E._contains(photo, straddle), False)

    # ③ 감사 전용 구역은 배치 계산(_obstacles)에 절대 끼지 않는다
    #    — 이 성질이 깨지면 기존 편(01·02·03)의 화면이 달라진다.
    sc = E.__new__(E)
    sc._zones = {
        "명시": {"box": (0, 1, 0, 1), "pad": 0.1, "owners": set(),
                 "kind": "block", "enforce": True, "track": None},
        "자동": {"box": (2, 3, 2, 3), "pad": 0.1, "owners": set(),
                 "kind": "block", "enforce": False, "track": None},
    }
    names = [n for n, _b, _p in sc._obstacles()]
    check("배치 계산에 들어가는 구역", names, ["명시"])

    # ② counsel 예외 등록부(§17-3) — 3중 키 완전 일치, 문구 변형 시 실효
    exc = B.LEGAL_CAPTION_EXCEPTIONS
    check("면제 등록 (04, 12, 작성자 관찰)",
          ("04", 12, "작성자 관찰") in exc, True)
    check("면제 하한", exc.get(("04", 12, "작성자 관찰"), {}).get("required_min_sec"), 2.0)
    check("문구 변형 = 실효(공백 제거)", ("04", 12, "작성자관찰") in exc, False)
    check("세그 불일치 = 실효", ("04", 11, "작성자 관찰") in exc, False)
    check("편 불일치 = 실효", ("05", 12, "작성자 관찰") in exc, False)

    # ③ 4편부터 자동 구역이 '차단'으로 승격
    check("자동구역 차단 기준편", E.ZONE_STRICT_FROM_EP, 4)
    B.EP = "03"
    check("03편 = 권고", E._auto_zone_blocks(), False)
    B.EP = "04"
    check("04편 = 차단", E._auto_zone_blocks(), True)


# ------------------------------------------------------------ part: shorts
def part_shorts():
    print("[④ 쇼츠 보호영역]")
    sys.argv = ["build_shorts.py", "03", "--audit"]
    sys.path.insert(0, HERE)
    import build_shorts as S

    check("UI 하단 비율", S.SHORTS_UI_BOTTOM, 0.20)
    check("UI 우측 비율", S.SHORTS_UI_RIGHT, 0.12)
    check("자동구역 차단 기준편", S.ZONE_STRICT_FROM_EP, 4)

    # 카메라 상대 계산 — 줌이 들어가도 UI 대역이 '지금 보이는 화면'을 따라와야 한다.
    class FakeFrame(object):
        def __init__(self, w, h, cx=0.0, cy=0.0):
            self.w, self.h, self.cx, self.cy = w, h, cx, cy

        def get_left(self):
            return [self.cx - self.w / 2, 0, 0]

        def get_right(self):
            return [self.cx + self.w / 2, 0, 0]

        def get_bottom(self):
            return [0, self.cy - self.h / 2, 0]

        def get_top(self):
            return [0, self.cy + self.h / 2, 0]

    class FakeCam(object):
        def __init__(self, f):
            self.frame = f

    class Probe(S.ShortBase):
        # MovingCameraScene.camera 는 읽기 전용 프로퍼티라 가짜 카메라를 못 꽂는다.
        # 하위 클래스에서 평범한 속성으로 덮어 검사용 프레임을 주입한다.
        camera = None

    sc = Probe.__new__(Probe)
    sc.camera = FakeCam(FakeFrame(9.0, 16.0))
    bottom = {"ui": "bottom"}
    right = {"ui": "right"}
    check("하단 대역(줌 없음)", tuple(round(v, 3) for v in sc._zone_box(bottom)),
          (-4.5, 4.5, -8.0, -4.8))
    check("우측 대역(줌 없음)", tuple(round(v, 3) for v in sc._zone_box(right)),
          (3.42, 4.5, -8.0, 8.0))
    sc.camera = FakeCam(FakeFrame(8.3, 8.3 * 16 / 9))   # 드리프트 하한까지 줌 인
    b2 = sc._zone_box(bottom)
    check("하단 대역이 줌을 따라옴", round(b2[2], 2) != -8.0, True)
    check("하단 대역 높이 = 프레임의 20%",
          round((b2[3] - b2[2]) / (8.3 * 16 / 9), 3), 0.2)

    # 감사 전용 구역은 배치 계산에서 제외(본편과 같은 불변식)
    sc._zones = {
        "명시": {"box": (0, 1, 0, 1), "pad": 0.2, "owners": set(),
                 "kind": "block", "enforce": True, "track": None, "ui": None},
        "자동": {"box": (2, 3, 2, 3), "pad": 0.2, "owners": set(),
                 "kind": "block", "enforce": False, "track": None, "ui": None},
    }
    check("배치 계산에 들어가는 구역", [n for n, _b, _p in sc._obstacles()], ["명시"])


# ------------------------------------------------------------ part: verify
def part_verify():
    print("[[audit] 로그 형식 ↔ 검사기 정규식 계약]")
    import tempfile
    sys.path.insert(0, HERE)
    import verify_output_spec as V

    log = (
        "[audit] Episode04: 프레임 이탈 0건\n"
        "[audit] Episode04: 보호영역 침범 2건 "
        "(등록 구역 15개[명시 3·자동 12=차단], 구간 커버리지 16/16)\n"
        "[audit] Episode04: 표시영역 권고 위반 0건 (4편부터 차단)\n"
        "[audit] Episode04: 법무 표기 지속 미달 1건 (표기 3건, 상한 20자)\n"
        "[audit] Short04A: 프레임 이탈 0건 — 모든 요소가 화면 안\n"
        "[audit] Short04A: 보호영역 침범 0건 "
        "(등록 구역 5개[명시 0·자동 5=차단], 구간 커버리지 7/7)\n"
    )
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "_t.log"), "w", encoding="utf-8") as f:
        f.write(log)
    hits = V.audit_lines(d)

    check("장면 2개 포착", sorted(hits), ["Episode04", "Short04A"])
    z = hits["Episode04"]["보호영역 침범"]
    check("침범 건수", z["count"], 2)
    check("등록 구역 수", z["zones"], 15)
    check("구간 커버리지", z["cover"], (16, 16))
    lg = hits["Episode04"]["법무 표기 지속 미달"]
    check("법무 미달 건수", lg["count"], 1)
    check("법무 표기 총수", lg["items"], 3)
    check("권고 축 포착", hits["Episode04"]["표시영역 권고 위반"]["count"], 0)
    check("쇼츠 커버리지", hits["Short04A"]["보호영역 침범"]["cover"], (7, 7))
    check("두 파일의 기준편 상수 일치",
          V.ZONE_STRICT_FROM_EP, 4)

    # 커버리지 미기록(옛 로그)은 '통과'가 아니라 '미확인'으로 남아야 한다
    old = "[audit] Episode03: 보호영역 침범 0건 (등록 구역 3개)\n"
    d2 = tempfile.mkdtemp()
    with open(os.path.join(d2, "_o.log"), "w", encoding="utf-8") as f:
        f.write(old)
    h2 = V.audit_lines(d2)["Episode03"]["보호영역 침범"]
    check("옛 로그 커버리지 = 미기록", h2["cover"], None)
    rows = []
    V.check_frame_audit(rows, "본편", d2, expect_scenes=1, scope="Episode",
                        axes=("보호영역 침범",))
    verdicts = [r.verdict for r in rows if "보호영역" in r.item]
    check("커버리지 미기록 판정", verdicts, ["WARN"])


PARTS = {"v2": part_v2, "shorts": part_shorts, "verify": part_verify}


def main():
    arg = next((a.split("=", 1)[1] for a in sys.argv[1:]
                if a.startswith("--part=")), None)
    if arg:
        PARTS[arg]()
        if FAILS:
            print(f"실패 {len(FAILS)}건: {FAILS}")
            sys.exit(1)
        print("전항 통과")
        return
    bad = []
    for name in PARTS:
        print(f"\n===== {name} =====")
        r = subprocess.run([sys.executable, os.path.abspath(__file__),
                            f"--part={name}"],
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        if r.returncode != 0:
            bad.append(name)
    print("\n" + "=" * 50)
    if bad:
        print(f"[selftest] 실패 파트: {bad} — 안전장치가 깨졌다. 렌더 전에 고칠 것.")
        sys.exit(1)
    print("[selftest] 안전장치 3종(법무 캡션·본편 보호영역·쇼츠 보호영역) 전항 통과")


if __name__ == "__main__":
    main()
