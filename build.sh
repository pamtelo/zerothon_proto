#!/usr/bin/env bash
# 지정된 Python 버전 설치
curl -L https://install-python.python-build.dev/3.9.0 | bash
export PATH="/home/render/.python/python3.9/bin:$PATH"
python -m pip install --upgrade pip

# requirements.txt 설치
pip install -r requirements.txt 