#!/bin/bash
echo "Parando containers..."
docker compose down

echo "Atualizando repositório..."
git pull origin master

echo "Reconstruindo containers..."
docker compose up --build -d
