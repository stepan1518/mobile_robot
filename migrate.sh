#!/bin/bash
set -euo pipefail

# Путь к конфигу — можно переопределить при запуске
ENV_PROPERTIES="${ENV_PROPERTIES:-./resources/env.properties}"

# Принудительно чистим всё старое + пересобираем образ без кэша (только при необходимости)
if [[ "${1:-}" == "--rebuild" ]] || [[ "${1:-}" == "-r" ]]; then
  echo "Чистим старые образы и кэш..."
  docker compose down -v --remove-orphans --rmi all 2>/dev/null || true
  docker builder prune -af
  REBUILD="--no-cache"
else
  REBUILD=""
fi

echo "Используем конфиг: $ENV_PROPERTIES"

# Запускаем с передачей переменной
ENV_PROPERTIES="$ENV_PROPERTIES" \
  docker compose --profile migrate build $REBUILD flyway

ENV_PROPERTIES="$ENV_PROPERTIES" \
  docker compose --profile migrate up --abort-on-container-exit flyway