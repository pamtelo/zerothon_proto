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

# 실행 권한 확인
echo "Build script is running..."

# Python 버전 확인
python --version

# Python 패키지 설치
pip install -r requirements.txt

# CSV 파일이 있는지 확인하고 권한 설정
for file in *.csv; do
  if [ -f "$file" ]; then
    echo "CSV file found: $file"
    chmod 644 "$file"
  fi
done

# static 및 templates 디렉토리 권한 설정
if [ -d "static" ]; then
  chmod -R 755 static
  echo "Set permissions for static directory"
fi

if [ -d "templates" ]; then
  chmod -R 755 templates
  echo "Set permissions for templates directory"
fi

# 웹 서비스 실행을 위한 wsgi.py 권한 설정
if [ -f "wsgi.py" ]; then
  chmod 755 wsgi.py
  echo "Set permissions for wsgi.py"
fi

echo "Build script completed successfully."