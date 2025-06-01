# 안전재고관리 및 적정구매예산 제안 서비스

## 프로젝트 개요
이 서비스는 안전재고 미만인 품목을 대시보드에 표시하고, ChatGPT API를 활용하여 물가상승율, 품종별 외부환경 요소를 고려한 적정구매예산을 제안합니다. 또한 적정구매예산이 포함된 구매의뢰서를 제공합니다.

## 주요 기능
1. **안전재고 대시보드**: 안전재고 미만인 품목을 표시
2. **적정구매예산 제안**: 과거 구매이력과 예측 가격을 기반으로 ChatGPT API를 통해 적정예산 제안
3. **구매의뢰서 제공**: 적정구매예산이 포함된 구매의뢰서 생성

## 데이터셋
- `inventory.csv`: 재고현황
- `purchase_history.csv`: 구매이력
- `annual_unit_price.csv`: 연도별 구매단가
- `predict.csv`: 예상구매가

## 설치 및 실행
1. 필요 패키지 설치:
```
pip install -r requirements.txt
```

2. OpenAI API 키 설정:
```
export OPENAI_API_KEY=your-api-key
```

3. 애플리케이션 실행:
```
python app.py
```

4. 웹 브라우저에서 다음 주소로 접속:
```
http://127.0.0.1:5000/
```

## 개발 환경
- Python 3.8+
- Flask 웹 프레임워크
- Pandas, NumPy 데이터 처리
- Plotly 시각화
- OpenAI API (ChatGPT) 