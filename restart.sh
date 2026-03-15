#!/bin/bash

if [[ "$1" == "resetdb" ]]; then
  docker compose down -v
else
  docker compose down
fi

git pull
docker builder prune -af
docker compose build --no-cache --pull
docker compose up -d
docker compose logs -f codex
