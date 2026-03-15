#!/bin/bash

if [[ "$1" == "resetdb" ]]; then
  docker compose down -v
else
  docker compose down
fi

git pull
docker builder prune -f
docker compose build --no-cache
docker compose up -d
docker compose logs -f codex
