#!/usr/bin/env bash
# Python 3.9 설치 및 설정
echo "Python 3.9 설치 중..."
curl -L https://install-python.python-build.dev/3.9.0 | bash
export PATH="/home/render/.python/python3.9/bin:$PATH"

# 필요한 시스템 라이브러리 설치
echo "시스템 라이브러리 설치 중..."
apt-get update && apt-get install -y build-essential libssl-dev libffi-dev python3-dev

# Pip 업그레이드 및 의존성 설치
echo "Pip 업그레이드 중..."
python -m pip install --upgrade pip setuptools wheel

# requirements.txt 설치
echo "의존성 패키지 설치 중..."
pip install --no-cache-dir -r requirements.txt 