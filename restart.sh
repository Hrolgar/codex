#!/bin/bash

if [[ "$1" == "resetdb" ]]; then
  docker compose down -v
else
  docker compose down
fi

git pull
docker compose up -d --build --no-cache
docker compose logs -f codex
