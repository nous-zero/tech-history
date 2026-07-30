# 사실 재검증: "나스닥이 두 시간 멈췄다"는 사실인가 (1995-08-09 넷스케이프 상장)

의뢰: release-director 6대 (2026-07-30) · 판정: planner-writer · 관련 산출물: `video/scripts/04.json`

## 결론 (1줄)

**가설 B가 맞다** — 1995-08-09에 멈춘 것은 나스닥 시장이 아니라 **넷스케이프(NSCP) 한 종목의 첫 거래(개장)** 이며, 매수 주문 폭주(order imbalance)로 **약 2시간 개시가 지연**됐다. 시장 전체 정지(halt)를 서술한 출처는 검색 범위에서 0건. 기존 대본 title·seg0의 "나스닥 시장이 거래를 열지 못했다"는 **과장 오류 → 정정 완료**.

## 출처별 원문 인용 (영어 검색, rule10)

| # | 출처 | 원문(verbatim) | 해석 |
|---|---|---|---|
| 1 | Poynter, "The 'Netscape Moment,' 20 years on" (2015) — https://www.poynter.org/reporting-editing/2015/the-netscape-moment-20-years-on/ (WebFetch 직접 인용) | "For nearly two hours that morning, an order imbalance kept **the company's shares** from being traded: Demand was that strong." | 거래가 막힌 주체 = "the company's shares"(넷스케이프 주식). 시장 아님 |
| 2 | NPR, "Netscape's IPO Anniversary and the Internet Boom" (2005) — https://www.npr.org/2005/08/09/4792365/netscapes-ipo-anniversary-and-the-internet-boom (검색 결과 인용문) | "Trading **of the stock** on the NASDAQ exchange was delayed nearly two hours because of a huge order imbalance." | "trading of the stock" = 그 종목의 거래가 지연(delayed). halt(정지) 표현 없음 |
| 3 | Fortune, "Remembering Netscape" (2015) — https://fortune.com/2015/08/09/remembering-netscape (검색 결과 인용문) | "demand **for the shares** was so high that for almost two hours that morning, trading couldn't open" | 수요 폭주로 (그 주식의) 거래 개시가 안 됨 — 개장 지연 |

- 보조: 복수 출처가 "first trade did not hit the ticker until around 11:00 AM, at a price of $71"(첫 체결 약 오전 11시, 71달러)로 서술 — 나스닥 정규장은 9시 30분 개장이므로 지연 폭 약 1.5~2시간과 정합.
- **"시장 전체 halt"를 주장하는 출처: 0건**(영어 4회 + 한국어 대본 원고 검토 범위 내).

## 용어 구분

- **delayed opening(개장 지연)**: 특정 종목의 첫 체결가를 정할 수 없어(매수·매도 불균형) 그 종목만 거래 개시를 미루는 것 — 이번 사건. 시장의 정상 절차다.
- **trading halt(거래 정지)**: 거래소가 종목 또는 시장 거래를 공식 중단시키는 조치 — 이번 사건 아님.

## 대본에 그대로 쓸 수 있는 정확한 사실 서술 (1문장)

> "1995년 8월 9일, 매수 주문이 폭주해 나스닥에서 넷스케이프 주식의 첫 거래가 약 2시간 동안 열리지 못했다."

## 정정 내역

- `video/scripts/04.json` **title**: "나스닥이 두 시간 멈췄다" → "주문 폭주로 첫 거래가 두 시간 막혔다"
- **seg0**: "미국 나스닥 시장이 두 시간 가까이 거래를 열지 못했습니다" → "미국 나스닥의 한 종목이 두 시간 가까이 첫 거래를 열지 못했습니다" (scene명도 `nasdaq_halt`→`nasdaq_delay`로 개칭, 소재 요구서 동기화)
- **seg10**: "거래 자체를" → "이 주식의 첫 거래를" (주어 명확화 — 원문도 넷스케이프 거래를 지칭했으나 오독 여지 제거)
- 그 외 세그먼트: "나스닥·멈춤·정지" 전수 grep — 같은 서술 없음(seg11 "겨우 열린 첫 거래 가격"은 개장 지연과 정합, 유지)

## 소급 대상 보고 (정정하지 않음 — 사용자 결정 사안)

- `posts/frontend/frontend-story-04-mosaic-netscape.md` (링크드인 **기게시** 원고): "주문이 폭주해 나스닥이 2시간 가까이 거래를 열지 못했습니다" — **같은 유형의 과장 오류**. X 초안(같은 파일 하단)도 "나스닥이 2시간 마비됐다"로 동일. 지시대로 수정하지 않고 보고만 한다.
- `refs/ep04-production-log.md` 상단 소재 요약의 "나스닥 상장(2시간 마비)" — 총감독 관리 파일이라 보고만.
