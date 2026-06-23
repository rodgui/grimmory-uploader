#!/bin/bash
# Deploy grimmory-uploader para VPS
# Uso: ./deploy.sh
set -e
echo "📤 Deploy uploader → VPS"
ssh busca.rodgui.com "cd ~/grimmory-uploader && git pull && cp upload_server.py Dockerfile requirements.txt docker-compose.yml /opt/uploader/ && cd /opt/uploader && docker compose up -d --build"
echo "✅ https://upload.rodgui.com"
