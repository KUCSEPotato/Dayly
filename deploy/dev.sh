#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")/.."

# Explicit -f always selects the isolated development project and DB volume.
case "${1:-up}" in
  up)
    if ! docker compose -f compose.dev.yaml up -d --build --wait; then
      printf '%s\n' '개발 서버를 시작하지 못했습니다.' \
        'Docker Desktop 실행 여부와 위 오류 로그를 확인하세요.' \
        '8081 포트가 이미 사용 중이면 해당 서비스를 종료한 뒤 다시 실행하세요. 운영용 8080 환경은 그대로 유지됩니다.' >&2
      exit 1
    fi
    printf '%s\n' '개발 서버: http://localhost:8081'
    ;;
  down) docker compose -f compose.dev.yaml down ;;
  logs) docker compose -f compose.dev.yaml logs -f ;;
  ps) docker compose -f compose.dev.yaml ps ;;
  *) printf '%s\n' '사용법: sh deploy/dev.sh [up|down|logs|ps]' >&2; exit 2 ;;
esac
