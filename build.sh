#!/usr/bin/env bash
# 필요한 시스템 라이브러리 설치
echo "시스템 라이브러리 설치 중..."
apt-get update && apt-get install -y build-essential libssl-dev libffi-dev

# Pip 업그레이드 및 의존성 설치
echo "Pip 업그레이드 중..."
python -m pip install --upgrade pip setuptools wheel

# requirements.txt 설치
echo "의존성 패키지 설치 중..."
pip install --no-cache-dir -r requirements.txt 