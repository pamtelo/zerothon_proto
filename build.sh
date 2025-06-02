#!/usr/bin/env bash

# 필요한 시스템 라이브러리 설치
echo "Installing system libraries..."
apt-get update && apt-get install -y build-essential libssl-dev libffi-dev

echo "Upgrading pip..."
pip install --upgrade pip wheel setuptools

# NumPy 및 기타 의존성 설치 - 컴파일 단계 건너뛰도록 사전 컴파일된 휠 사용
echo "Installing numpy and pandas..."
pip install --only-binary=:all: numpy==1.22.4 pandas==1.4.3

echo "Installing other dependencies..."
pip install --no-cache-dir -r requirements.txt

echo "Setup complete!"