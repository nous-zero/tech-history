# -*- coding: utf-8 -*-
"""유튜브 OAuth 열쇠(토큰) 재발급 스크립트 — 사용자 컴퓨터에서 딱 한 번 실행.

*** 클라우드/원격 세션에서는 실행 불가 — 로그인 창(브라우저)이 뜰 화면이 있는
    본인 컴퓨터(노트북/데스크톱)에서만 실행해야 함. ***

무엇을 하는가:
  1. yt-keys 저장소의 기존(만료된) 토큰 파일에서 앱 정보(client_id/secret)만 재사용
     — 비밀정보는 이 스크립트(공개 저장소 tech-history)에 절대 하드코딩하지 않음.
  2. 브라우저를 자동으로 열어 구글 로그인 화면을 띄움.
  3. nous-zero 채널을 관리하는 구글 계정으로 로그인 → 읽기 전용 권한 허용.
  4. 새로 발급된 토큰을 같은 파일에 덮어씀.
  5. yt-keys 저장소가 git 저장소면 자동으로 commit + push까지 시도(실패 시 안내만).

사용법 (사용자 컴퓨터, 터미널에서):
  cd tech-history        # (또는 이 스크립트가 있는 저장소 아무 곳)
  pip install google-api-python-client google-auth google-auth-oauthlib
  YT_TOKEN_PATH=<yt-keys 로컬 경로>/youtube_oauth_token.json python tools/reauth_youtube.py

YT_TOKEN_PATH를 생략하면 기본값(~/.claude/.tmp/youtube_oauth_token.json)을 사용합니다.
"""
import json
import os
import pathlib
import subprocess
import sys

TOKEN = pathlib.Path(os.environ.get(
    "YT_TOKEN_PATH", pathlib.Path.home() / ".claude" / ".tmp" / "youtube_oauth_token.json"))


def main():
    if not TOKEN.exists():
        print(f"[오류] 토큰 파일이 없습니다: {TOKEN}")
        print("       YT_TOKEN_PATH 환경변수로 yt-keys 저장소 내 youtube_oauth_token.json 경로를 지정하세요.")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("[오류] google-auth-oauthlib 가 설치되어 있지 않습니다.")
        print("       실행: pip install google-api-python-client google-auth google-auth-oauthlib")
        sys.exit(1)

    old = json.loads(TOKEN.read_text())
    client_id = old.get("client_id")
    client_secret = old.get("client_secret")
    scopes = old.get("scopes") or [
        "https://www.googleapis.com/auth/yt-analytics.readonly",
        "https://www.googleapis.com/auth/youtube.readonly",
    ]
    if not client_id or not client_secret:
        print("[오류] 기존 토큰 파일에 client_id/client_secret이 없습니다 — 수동 재발급이 필요합니다.")
        sys.exit(1)

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": old.get("token_uri", "https://oauth2.googleapis.com/token"),
            "redirect_uris": ["http://localhost"],
        }
    }

    print("브라우저가 곧 자동으로 열립니다. nous-zero 채널을 관리하는")
    print("구글 계정으로 로그인한 뒤 '허용(Allow)'을 눌러주세요.\n")

    flow = InstalledAppFlow.from_client_config(client_config, scopes)
    creds = flow.run_local_server(port=0)

    TOKEN.write_text(creds.to_json())
    print(f"\n[성공] 새 열쇠(토큰) 저장 완료: {TOKEN}")
    print(f"       새 만료(expiry): {json.loads(creds.to_json()).get('expiry')}")

    # yt-keys 저장소면 자동 commit + push 시도
    repo_dir = TOKEN.parent
    if (repo_dir / ".git").exists():
        try:
            subprocess.run(["git", "-C", str(repo_dir), "add", TOKEN.name], check=True)
            subprocess.run(
                ["git", "-C", str(repo_dir), "commit", "-m", "token: youtube OAuth 재발급"],
                check=True,
            )
            subprocess.run(["git", "-C", str(repo_dir), "push"], check=True)
            print("\n[완료] yt-keys 저장소에 커밋·푸시까지 자동으로 마쳤습니다.")
            print("       내일 오전 9시 자동 루틴부터 정상 수집됩니다.")
        except subprocess.CalledProcessError as e:
            print(f"\n[안내] git 자동 커밋/푸시 실패({e}). 아래를 직접 실행해주세요:")
            print(f"       cd {repo_dir}")
            print(f"       git add {TOKEN.name}")
            print("       git commit -m 'token: youtube OAuth 재발급'")
            print("       git push")
    else:
        print(f"\n[안내] {repo_dir} 가 git 저장소가 아닙니다 — yt-keys 저장소로 이 파일을")
        print("       직접 복사한 뒤 commit·push 해주세요.")


if __name__ == "__main__":
    main()
