import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from flask import Flask, render_template, request, redirect, url_for, jsonify
import openai
import os
import json

app = Flask(__name__)

# 데이터 로드
def load_data():
    inventory = pd.read_csv('inventory.csv')
    purchase_history = pd.read_csv('purchase_history.csv')
    annual_unit_price = pd.read_csv('annual_unit_price.csv')
    predict = pd.read_csv('predict.csv')
    
    # 모든 데이터프레임의 컬럼 이름 공백 제거
    inventory.columns = inventory.columns.str.strip()
    purchase_history.columns = purchase_history.columns.str.strip()
    annual_unit_price.columns = annual_unit_price.columns.str.strip()
    predict.columns = predict.columns.str.strip()
    
    return inventory, purchase_history, annual_unit_price, predict

# 더미 사용자 데이터
user_info = {
    "department": "구매팀",
    "employee_id": "Z1034",
    "position": "과장",
    "name": "홍길동"
}

@app.route('/')
def index():
    inventory, purchase_history, _, _ = load_data()
    
    # 안전재고 미만인 항목 필터링
    low_stock = inventory[inventory['current_stock'] < inventory['safety_stock']].copy()
    
    # 품목별로 가장 최근 구매 기록의 리드타임 가져오기
    for idx, item in low_stock.iterrows():
        item_code = item['item_code']
        # 해당 품목의 구매 이력 가져오기
        item_history = purchase_history[purchase_history['item_code'] == item_code]
        
        if not item_history.empty:
            # 구매 연도를 기준으로 정렬하여 가장 최근 데이터 가져오기
            latest_purchase = item_history.sort_values(by='purchase_year', ascending=False).iloc[0]
            lead_time = f"{latest_purchase['lead_time']}일"
            low_stock.loc[idx, 'lead_time'] = lead_time
        else:
            # 구매 이력이 없는 경우 기본값 설정
            low_stock.loc[idx, 'lead_time'] = "3일"
    
    # 상태 설정: 현재고가 안전재고보다 작거나 같으면 "재고 부족", 안전재고의 105% 이내면 "주의"
    for idx, item in low_stock.iterrows():
        current = item['current_stock']
        safety = item['safety_stock']
        
        if current <= safety:
            low_stock.loc[idx, 'status'] = "⚠ 재고 부족"
        elif current <= safety * 1.05:
            low_stock.loc[idx, 'status'] = "⚠ 주의"
        else:
            low_stock.loc[idx, 'status'] = "정상"
    
    # 안전재고 미달 항목 개수
    low_stock_count = len(low_stock)
    
    return render_template('index.html', low_stock=low_stock.to_dict('records'), low_stock_count=low_stock_count)

@app.route('/purchase_request/<item_code>')
def purchase_request(item_code):
    inventory, purchase_history, annual_unit_price, predict = load_data()
    
    # 해당 품목 정보 가져오기
    item_info_series = inventory[inventory['item_code'] == item_code].iloc[0]
    
    # Series를 딕셔너리로 변환하여 템플릿에 전달
    item_info = item_info_series.to_dict()
    
    # 해당 품목의 구매 이력 가져오기
    item_purchase_history = purchase_history[purchase_history['item_code'] == item_code]
    
    # 구매 이력 데이터 천단위 콤마 포맷팅
    purchase_history_records = item_purchase_history.to_dict('records')
    for record in purchase_history_records:
        if 'unit_price' in record:
            try:
                record['unit_price'] = format(int(record['unit_price']), ',')
            except (ValueError, TypeError):
                pass
        if 'total_price' in record:
            try:
                record['total_price'] = format(int(record['total_price']), ',')
            except (ValueError, TypeError):
                pass
        if 'quantity' in record:
            try:
                record['quantity'] = format(int(record['quantity']), ',')
            except (ValueError, TypeError):
                pass
    
    # 연도별 구매 단가 가져오기
    item_annual_price = annual_unit_price[annual_unit_price['item_code'] == item_code]
    
    # 예측 가격 가져오기
    item_predict_price = predict[predict['item_code'] == item_code].iloc[0]['predict_price']
    
    # 그래프 데이터 준비
    years = [col for col in item_annual_price.columns if col != 'item_code']
    prices = item_annual_price.iloc[0][years].values
    
    # 결측치 제거
    valid_years = []
    valid_prices = []
    for year, price in zip(years, prices):
        if not pd.isna(price):
            valid_years.append(year)
            valid_prices.append(price)
    
    # ChatGPT API를 사용하여 적정구매예산 추천
    recommendation, budget = get_budget_recommendation(item_info, valid_years, valid_prices, item_predict_price)
    
    # 그래프 데이터 준비
    graph_data = []
    for year, price in zip(valid_years, valid_prices):
        graph_data.append({"year": str(year), "price": float(price), "type": "과거 구매단가"})
        
    # 예측 가격 추가
    graph_data.append({"year": "2025(예측)", "price": float(item_predict_price), "type": "예측 구매단가"})
    
    # 숫자 포맷팅 (천단위 콤마)
    formatted_predict_price = format(int(item_predict_price), ',')
    formatted_budget = format(int(budget), ',')
    
    return render_template(
        'purchase_request.html', 
        user_info=user_info,
        item_info=item_info,
        purchase_history=purchase_history_records,
        graph_data=json.dumps(graph_data),
        predict_price=formatted_predict_price,
        recommendation=recommendation,
        budget=formatted_budget
    )

def get_budget_recommendation(item_info, years, prices, predict_price):
    try:
        # API 키가 설정되어 있는지 확인
        api_key = os.environ.get("OPENAI_API_KEY")
        
        # API 키가 없거나 테스트 모드인 경우 기본 추천 제공
        if not api_key or api_key == "your-api-key":
            # 품목 카테고리에 따른 기본 추천 메시지
            category_messages = {
                "철강재": "철강 시장의 최근 가격 안정화와 원자재 수급 상황을 고려할 때, 예측가격에 약 5%의 여유 예산을 추가하는 것이 적절합니다.",
                "특수강재": "특수강 시장의 가격 변동성과 공급망 리스크를 고려하여, 예측가격에 약 7%의 여유 예산을 설정하는 것이 안전합니다.",
                "비철제품": "비철금속 시장의 가격 상승 추세와 국제 원자재 시장 동향을 고려하여, 약 8%의 추가 예산을 권장합니다.",
                "배관설비재": "최근 원자재 가격 상승과 공급망 불확실성을 감안할 때, 예측가격에 약 6% 추가 예산이 필요합니다.",
                "석유화학제품": "국제 유가 변동성과 석유화학 시장 동향을 고려하여, 예측가격보다 약 10% 높은 예산을 책정하는 것이 바람직합니다."
            }
            
            # 카테고리에 맞는 메시지 선택, 없으면 기본 메시지 사용
            category = item_info['category']
            recommendation_text = category_messages.get(category, f"현재 시장 상황을 고려할 때, 예측 가격 {predict_price}원에 약 5%의 여유를 추가하는 것이 적절합니다.")
            
            # 카테고리별 예산 조정 비율 설정
            adjustment_rates = {
                "철강재": 1.05,
                "특수강재": 1.07,
                "비철제품": 1.08,
                "배관설비재": 1.06,
                "석유화학제품": 1.10
            }
            
            # 예산 계산
            adjustment_rate = adjustment_rates.get(category, 1.05)
            budget = round(predict_price * adjustment_rate)
            
            return recommendation_text, budget
        
        # OpenAI API 설정 및 호출 (이 부분은 API 키가 있을 때만 실행됨)
        openai.api_key = api_key
        
        # 프롬프트 구성
        prompt = f"""
        다음은 품목 '{item_info['item']}' ({item_info['specification']})에 대한 정보입니다:
        - 카테고리: {item_info['category']}
        - 연도별 구매단가: {', '.join([f'{year}: {price}원' for year, price in zip(years, prices)])}
        - 머신러닝으로 예측한 다음해 구매 가격: {predict_price}원
        
        이 정보와 아래 요소들을 고려하여 적정구매예산을 제안해주세요:
        1. 물가상승률
        2. {item_info['category']} 품종의 시장 동향
        3. {item_info['category']} 가격에 영향을 미치는 외부환경 요소
        
        적정 구매예산과 80자 이내의 한국어로 추천 근거를 제시해 주세요.
        """
        
        # OpenAI API 호출
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 구매 전문가입니다. 품목에 대한 적정구매예산을 추천해 주세요."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # 응답 처리
        recommendation_text = response.choices[0].message.content
        
        # 예산 추출 (간단한 처리 예시)
        budget = round(predict_price * 1.05)  # 예시로 예측가격의 5% 추가
        
        return recommendation_text, budget
        
    except Exception as e:
        print(f"OpenAI API 호출 중 오류 발생: {e}")
        # 오류 발생 시 기본 추천 제공
        return f"현재 시장 상황을 고려할 때, 예측 가격 {predict_price}원에 약 5%의 여유를 추가하는 것이 적절합니다.", round(predict_price * 1.05)

@app.route('/submit_purchase', methods=['POST'])
def submit_purchase():
    # 구매요청 처리 로직
    # 실제 시스템에서는 DB에 저장하거나 메일 발송 등의 작업 수행
    return jsonify({"status": "success", "message": "구매 요청이 성공적으로 처리되었습니다."})

if __name__ == "__main__":
    # 로컬 개발 환경에서는 localhost에서 실행
    # Render.com 등 배포 환경에서는 0.0.0.0으로 바인딩하고 환경 변수에서 포트 가져옴
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port) 