# 출처 (Origin)

- 원본: https://github.com/feiskyer/claude-code-settings
  (`skills/youtube-transcribe-skill/SKILL.md`)
- 커밋: 45ad30f5ec6949677e80b35cea3ac88c91f25309 (설치일 2026-07-27)
- 라이선스: MIT

## 로컬 수정 사항 (원본과 다른 점)

1. **쿠키 기본값 제거**: 원본은 `--cookies-from-browser=chrome`(브라우저 로그인 쿠키
   읽기)이 기본이었으나, 쿠키 없이 먼저 시도하고 로그인 필수 영상일 때만 사용자
   허락을 받아 쓰도록 변경 (2026-07-27 실측: 이 PC에서 쿠키 없이 정상 동작).
2. **자막 언어 기본값**: `zh-Hans,zh-Hant,en` → `ko,en` (한국어 채널 프로젝트 기준).
