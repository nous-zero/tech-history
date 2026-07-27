@echo off
rem 매일 08:45 KST — 비공개 분석 지표 수집 후 저장소에 커밋·푸시 (작업 스케줄러 등록용)
cd /d "C:\Users\745ra\OneDrive\바탕 화면\tech-history"
python video\fetch_analytics.py || exit /b 1
git pull --rebase origin main
git add video/analytics
git commit -m "analytics: 비공개 지표 스냅샷 (로컬 수집)" || exit /b 0
git push origin main
