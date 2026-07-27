# -*- coding: utf-8 -*-
"""nous-zero 채널 지표 통합 수집기 — 공개 지표(Data API) + 심층 지표(Analytics API).

전부 googleapis.com 경로라 클라우드 루틴에서도 동작한다(유튜브 사이트 차단과 무관,
2026-07-27 클라우드 실측: googleapis 통신 가능). 로컬(매일 08:45 작업 스케줄러)과
클라우드 루틴(09:00) 어느 쪽에서 돌려도 같은 파일을 만든다.

- 토큰 경로: 환경변수 YT_TOKEN_PATH > ~/.claude/.tmp/youtube_oauth_token.json
  (클라우드는 비공개 저장소 nous-zero/yt-keys 의 사본을 가리킴)
- 산출: video/analytics/snapshot-<날짜>.json (공개 지표),
        video/analytics/private-<날짜>.json (심층 지표)
- 규칙 6: 실패 항목은 지어내지 않고 error/미확정으로 기록. 분석 데이터는 1~2일 지연.
"""
import datetime
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
OUT_DIR = ROOT / "analytics"
CHANNEL = "UCFDEkjffWuo6CxeOCThTjRA"
TOKEN = pathlib.Path(os.environ.get(
    "YT_TOKEN_PATH", pathlib.Path.home() / ".claude" / ".tmp" / "youtube_oauth_token.json"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def get_creds():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    creds = Credentials.from_authorized_user_file(str(TOKEN))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        try:
            TOKEN.write_text(creds.to_json())
        except OSError:
            pass  # 읽기 전용 체크아웃(클라우드)이면 갱신본 저장 생략
    return creds


def collect_public(creds, today):
    """Data API(OAuth)로 공개 지표: 채널 통계 + 전체 업로드 영상별 통계."""
    from googleapiclient.discovery import build
    yt = build("youtube", "v3", credentials=creds)
    out = {"collected_at": datetime.datetime.now().isoformat(timespec="seconds"), "channel": CHANNEL}
    ch = yt.channels().list(part="snippet,statistics,contentDetails", id=CHANNEL).execute()
    item = ch["items"][0]
    out["channel_stats"] = item["statistics"]  # 구독자·총조회·영상수
    uploads = item["contentDetails"]["relatedPlaylists"]["uploads"]
    vids, page = [], None
    while True:
        pl = yt.playlistItems().list(part="contentDetails", playlistId=uploads,
                                     maxResults=50, pageToken=page).execute()
        vids += [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
        page = pl.get("nextPageToken")
        if not page:
            break
    videos = []
    for i in range(0, len(vids), 50):
        vr = yt.videos().list(part="snippet,statistics,contentDetails",
                              id=",".join(vids[i:i + 50])).execute()
        for v in vr.get("items", []):
            videos.append({"id": v["id"], "title": v["snippet"]["title"],
                           "published": v["snippet"]["publishedAt"],
                           "duration": v["contentDetails"]["duration"],
                           **{k: v["statistics"].get(k) for k in
                              ("viewCount", "likeCount", "commentCount")}})
    out["videos"] = sorted(videos, key=lambda x: x["published"])
    return out


def collect_private(creds, today):
    """Analytics API로 심층 지표 — 빈 배열은 '미확정(집계 1~2일 지연)'."""
    from googleapiclient.discovery import build
    an = build("youtubeAnalytics", "v2", credentials=creds)
    start = (today - datetime.timedelta(days=14)).isoformat()
    end = today.isoformat()
    result = {"collected_at": datetime.datetime.now().isoformat(timespec="seconds"),
              "channel": CHANNEL, "range": [start, end],
              "note": "분석 데이터는 1~2일 지연 확정 — 빈 배열은 '미확정'이지 0이 아님"}

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
    return result


def main():
    today = datetime.date.today()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    creds = get_creds()
    pub = collect_public(creds, today)
    (OUT_DIR / f"snapshot-{today.isoformat()}.json").write_text(
        json.dumps(pub, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved snapshot:", len(pub.get("videos", [])), "videos, subs:",
          pub["channel_stats"].get("subscriberCount"))
    priv = collect_private(creds, today)
    (OUT_DIR / f"private-{today.isoformat()}.json").write_text(
        json.dumps(priv, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved private metrics")


if __name__ == "__main__":
    main()
