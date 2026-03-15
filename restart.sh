#!/bin/bash

if [[ "$1" == "resetdb" ]]; then
  docker compose down -v
elif [[ "$1" == "clean" ]]; then
  docker compose down
  git pull
  docker builder prune -af
  docker compose build --no-cache --pull
  docker compose up -d
  docker compose logs -f codex
  exit 0
else
  docker compose down
fi

git pull
docker compose build --no-cache
docker compose up -d
docker compose logs -f codex
