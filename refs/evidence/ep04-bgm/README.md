# EP04-AUD-01 BGM 증거 묶음 — Pixabay #568180 "Corporate Explainer Video"

목적: **채택 시점(2026-07-30)에 이 트랙이 유튜브 Content ID 미등록이었음**과
**채택 시점의 라이선스 원문**을, 파일이 사라져도 살아남는 형태로 증명한다
(counsel 판정 `refs/legal-review-ep04.md` §7-B-3 증빙 ⑦⑧ 이행분).

## 1. 결론 요약

| 증빙 | 상태 | 근거 |
|---|---|---|
| ⑨ 라이선스 페이지 Wayback | ✅ 확보 | https://web.archive.org/web/20260729055902/https://pixabay.com/service/license-summary/ (HTTP 200, 내용 검수 완료 — "Content License"·"without having to attribute the author"·Standalone 정의 원문 포함) |
| ⑩ 트랙 페이지 Wayback | ❌ **불가(서비스 측 차단 실측)** | 아래 §3. 대체 증거 = 본 폴더의 파일 4종 + RFC 3161 공인 타임스탬프 4건(§2) |

## 2. 대체 증거 체인 (2026-07-30 확보)

모든 파일은 **RFC 3161 신뢰 타임스탬프**(freetsa.org, 무료 공인 TSA)로 봉인됨 —
`.tsr` 응답이 각 파일의 sha256과 **2026-07-30 02:25:16 GMT**를 제3자 서명으로 묶는다.
검증: `openssl ts -reply -in <파일>.tsr -text` (Message data = 파일 sha256).

| 파일 | sha256 | 내용·증명력 |
|---|---|---|
| `pixabay-568180-trackpage-20260730.html` | `85066c17…3000ae` | 트랙 페이지 원문(121,685B, 2026-07-30 10:53 KST 수신). **"Content ID Registered" 문자열 0건**(배지 부재) + `__BOOTSTRAP_URL__ = '/bootstrap/692c0b25….json'` 참조 포함 |
| `pixabay-568180-bootstrap-20260730.json` | `692c0b25…93abb` | **파일 sha256 = Pixabay 부트스트랩 URL의 해시와 정확히 일치**(내용 주소 방식) — 페이지가 참조하는 바로 그 데이터임이 암호학적으로 입증됨. 내용: 대상 트랙(id 568180) `hasYoutubeContentId: false` / `contentIdCertificateUrl: null`, **같은 파일 안에** 대조 트랙 3건(573878·571038·573983) `hasYoutubeContentId: true` — A/B 대조 내장 |
| `jina-render-568180-20260730.txt` | `f482b4fe…68fe1` | 제3자(r.jina.ai)가 렌더링한 대상 트랙 페이지 텍스트 — "Content ID" 표기 없음 |
| `jina-render-573878-control-20260730.txt` | `334f4ed0…bf392` | 같은 제3자 렌더러의 대조 트랙 페이지 — **"Content ID Registered" 표기 존재**(= 렌더러가 배지를 원래 그린다는 대안 설명 배제) |

증명 논리: ①공인 TSA가 "이 내용이 2026-07-30에 존재했다"를 서명 ②내용 주소 URL이
"이 JSON이 Pixabay가 서빙한 원본이다"를 입증 ③A/B 대조가 "배지 부재 = 미등록"을 입증.

## 3. Wayback 불가 사유 (실측 로그, rule6)

2026-07-30 실측 — Pixabay가 archive.org 계열 요청을 차단:

- SPN 직접 4회(01:44·01:46·01:47·02:04): 캡처 생성되나 전부 HTTP **204(빈 내용)** — CDX 실측
  (`http://web.archive.org/cdx/search/cdx?url=pixabay.com/music/corporate-corporate-explainer-video-568180/`)
- 부트스트랩 JSON SPN: HTTP **404**(빈 digest `3I42H3S6…`) — 같은 URL이 우리 회선에선 200
- 우회 전수 시도: r.jina.ai 경유 SPN(204/403) · archive.today(429 ×3) · megalodon.jp(봇 차단 명시)
  · ghostarchive.org(Cloudflare 차단) · 브라우저판(아카이브 사이트 별도 승인 게이트)
- 트랙 페이지의 Wayback 200 캡처는 **역사상 0건**(전체 CDX 조회) — 오늘만의 장애가 아님

## 4. 후속 의무 (미이행분)

- 발행 직전 `hasYoutubeContentId` 재실측 1행을 대장에 추가(counsel 조건① — 증빙 ⑪). **release-director 게이트 항목.**
- Wayback SPN이 향후 열리면(워커 IP 교체 등) 트랙 페이지 재시도해 ⑩을 정식 보강 — 선택 사항, 본 묶음으로 방어 가능.
