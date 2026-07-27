# -*- coding: utf-8 -*-
"""nous-zero 채널 비공개 분석 지표 수집기 (매일 08:45 KST, 로컬 예약 실행).

YouTube Analytics API(OAuth, 읽기 전용)로 시청 지속·트래픽 소스 등
공개 API(yt-dlp)로는 못 보는 지표를 받아 video/analytics/private-<날짜>.json 저장.
09:00 클라우드 대시보드 루틴이 이 파일을 합쳐서 분석한다.

- 토큰: ~/.claude/.tmp/youtube_oauth_token.json (2026-07-27 인증, 자동 갱신)
- 데이터 특성: 유튜브 분석은 1~2일 지연 확정 — 빈 결과는 오류가 아니라 '아직 미확정'.
- 규칙 6: 수집 실패 항목은 지어내지 않고 error 필드로 기록.
"""
import datetime
import json
import pathlib
import sys

TOKEN = pathlib.Path.home() / ".claude" / ".tmp" / "youtube_oauth_token.json"
ROOT = pathlib.Path(__file__).resolve().parent
OUT_DIR = ROOT / "analytics"
CHANNEL = "UCFDEkjffWuo6CxeOCThTjRA"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(str(TOKEN))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json())

    an = build("youtubeAnalytics", "v2", credentials=creds)
    today = datetime.date.today()
    start = (today - datetime.timedelta(days=14)).isoformat()
    end = today.isoformat()
    result = {"collected_at": datetime.datetime.now().isoformat(timespec="seconds"),
              "channel": CHANNEL, "range": [start, end], "note": "분석 데이터는 1~2일 지연 확정 — 빈 배열은 '미확정'이지 0이 아님"}

    def q(name, **kw):
        try:
            r = an.reports().query(ids=f"channel=={CHANNEL}", startDate=start, endDate=end, **kw).execute()
            result[name] = {"headers": [h["name"] for h in r.get("columnHeaders", [])],
                            "rows": r.get("rows", [])}
        except Exception as e:
            result[name] = {"error": str(e)[:300]}

    q("by_day", metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained",
      dimensions="day", sort="day")
    q("by_video", metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments",
      dimensions="video", sort="-views", maxResults=25)
    q("traffic_sources", metrics="views", dimensions="insightTrafficSourceType", sort="-views")
    q("search_terms", metrics="views", dimensions="insightTrafficSourceDetail",
      filters="insightTrafficSourceType==YT_SEARCH", sort="-views", maxResults=15)
    q("geography", metrics="views", dimensions="country", sort="-views", maxResults=15)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"private-{today.isoformat()}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved:", out)


if __name__ == "__main__":
    main()
