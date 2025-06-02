from flask import Flask, render_template, request, redirect, url_for, jsonify
import openai
import os
import json
import csv
from datetime import datetime
import traceback

app = Flask(__name__)

# 데이터 로드 - CSV 파일을 직접 읽어 딕셔너리로 변환
def load_data():
    try:
        # 파일 경로 설정 - 현재 디렉토리 기준
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 인벤토리 데이터 로드
        inventory = []
        inventory_path = os.path.join(base_dir, 'inventory.csv')
        with open(inventory_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 컬럼 이름 공백 제거
                clean_row = {k.strip() if k else k: v for k, v in row.items()}
                # 숫자 타입 변환
                if 'current_stock' in clean_row and clean_row['current_stock']:
                    try:
                        clean_row['current_stock'] = int(clean_row['current_stock'])
                    except (ValueError, TypeError):
                        clean_row['current_stock'] = 0
                if 'safety_stock' in clean_row and clean_row['safety_stock']:
                    try:
                        clean_row['safety_stock'] = int(clean_row['safety_stock'])
                    except (ValueError, TypeError):
                        clean_row['safety_stock'] = 0
                inventory.append(clean_row)
        
        # 구매 이력 데이터 로드
        purchase_history = []
        purchase_path = os.path.join(base_dir, 'purchase_history.csv')
        with open(purchase_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 컬럼 이름 공백 제거 및 원본 컬럼명 보존
                clean_row = {}
                for k, v in row.items():
                    key = k.strip() if k else k
                    clean_row[key] = v
                
                # 숫자 타입 변환
                if 'purchase_year' in clean_row and clean_row['purchase_year']:
                    try:
                        clean_row['purchase_year'] = int(clean_row['purchase_year'])
                    except (ValueError, TypeError):
                        clean_row['purchase_year'] = 0
                if 'lead_time' in clean_row and clean_row['lead_time']:
                    try:
                        clean_row['lead_time'] = int(clean_row['lead_time'])
                    except (ValueError, TypeError):
                        clean_row['lead_time'] = 3
                if 'quantity' in clean_row and clean_row['quantity']:
                    try:
                        clean_row['quantity'] = int(clean_row['quantity'])
                    except (ValueError, TypeError):
                        clean_row['quantity'] = 0
                if 'unit_price' in clean_row and clean_row['unit_price']:
                    try:
                        clean_row['unit_price'] = int(clean_row['unit_price'])
                    except (ValueError, TypeError):
                        clean_row['unit_price'] = 0
                if 'total_price' in clean_row and clean_row['total_price']:
                    try:
                        clean_row['total_price'] = int(clean_row['total_price'])
                    except (ValueError, TypeError):
                        clean_row['total_price'] = 0
                
                # 모든 키가 있는지 확인하고, 없으면 빈 값 추가
                required_keys = ['purchase_date', 'quantity', 'unit_price', 'total_price']
                for key in required_keys:
                    if key not in clean_row:
                        clean_row[key] = ""
                
                purchase_history.append(clean_row)
        
        # 연간 단가 데이터 로드
        annual_unit_price = []
        annual_path = os.path.join(base_dir, 'annual_unit_price.csv')
        with open(annual_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 컬럼 이름 공백 제거
                clean_row = {k.strip() if k else k: v for k, v in row.items()}
                # 숫자로 변환 가능한 필드 변환
                for key, value in clean_row.items():
                    if key != 'item_code' and value and value.strip():
                        try:
                            clean_row[key] = int(value)
                        except (ValueError, TypeError):
                            pass
                annual_unit_price.append(clean_row)
        
        # 예측 데이터 로드
        predict = []
        predict_path = os.path.join(base_dir, 'predict.csv')
        with open(predict_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 컬럼 이름 공백 제거
                clean_row = {k.strip() if k else k: v for k, v in row.items()}
                # 숫자 타입 변환
                if 'predict_price' in clean_row and clean_row['predict_price']:
                    try:
                        clean_row['predict_price'] = int(clean_row['predict_price'])
                    except (ValueError, TypeError):
                        clean_row['predict_price'] = 0
                predict.append(clean_row)
        
        return inventory, purchase_history, annual_unit_price, predict
    
    except Exception as e:
        print(f"데이터 로드 중 오류 발생: {e}")
        traceback.print_exc()
        # 오류 시 빈 데이터 반환
        return [], [], [], []

# 더미 사용자 데이터
user_info = {
    "department": "구매팀",
    "employee_id": "Z1034",
    "position": "과장",
    "name": "홍길동"
}

@app.route('/')
def index():
    try:
        inventory, purchase_history, _, _ = load_data()
        
        # 데이터가 비어 있으면 에러 메시지 표시
        if not inventory:
            return "데이터를 로드할 수 없습니다. 관리자에게 문의하세요.", 500
        
        # 안전재고 미만인 항목 필터링
        low_stock = []
        for item in inventory:
            if 'current_stock' in item and 'safety_stock' in item:
                if item['current_stock'] < item['safety_stock']:
                    low_stock.append(item.copy())  # 복사본 사용
        
        # 품목별로 가장 최근 구매 기록의 리드타임 가져오기
        for item in low_stock:
            item_code = item.get('item_code', '')
            # 해당 품목의 구매 이력 가져오기
            item_history = [h for h in purchase_history if h.get('item_code', '') == item_code]
            
            if item_history:
                # 구매 연도를 기준으로 정렬하여 가장 최근 데이터 가져오기
                item_history.sort(key=lambda x: x.get('purchase_year', 0), reverse=True)
                latest_purchase = item_history[0]
                lead_time = f"{latest_purchase.get('lead_time', 3)}일"
                item['lead_time'] = lead_time
            else:
                # 구매 이력이 없는 경우 기본값 설정
                item['lead_time'] = "3일"
        
        # 상태 설정: 현재고가 안전재고보다 작거나 같으면 "재고 부족", 안전재고의 105% 이내면 "주의"
        for item in low_stock:
            current = item.get('current_stock', 0)
            safety = item.get('safety_stock', 0)
            
            if current <= safety:
                item['status'] = "⚠ 재고 부족"
            elif current <= safety * 1.05:
                item['status'] = "⚠ 주의"
            else:
                item['status'] = "정상"
        
        # 안전재고 미달 항목 개수
        low_stock_count = len(low_stock)
        
        return render_template('index.html', low_stock=low_stock, low_stock_count=low_stock_count)
    
    except Exception as e:
        print(f"인덱스 페이지 처리 중 오류 발생: {e}")
        traceback.print_exc()
        return f"서버 오류가 발생했습니다: {str(e)}", 500

@app.route('/purchase_request/<item_code>')
def purchase_request(item_code):
    try:
        inventory, purchase_history, annual_unit_price, predict = load_data()
        
        # 데이터가 비어 있으면 에러 메시지 표시
        if not inventory:
            return "데이터를 로드할 수 없습니다. 관리자에게 문의하세요.", 500
        
        # 해당 품목 정보 가져오기
        item_info = next((item for item in inventory if item.get('item_code', '') == item_code), None)
        if not item_info:
            return "품목을 찾을 수 없습니다.", 404
        
        # 해당 품목의 구매 이력 가져오기
        item_purchase_history = [h for h in purchase_history if h.get('item_code', '') == item_code]
        
        # 구매 이력 데이터 확인
        print(f"품목 {item_code}의 구매 이력 건수: {len(item_purchase_history)}")
        if item_purchase_history:
            print(f"첫 번째 구매 이력 데이터 키: {list(item_purchase_history[0].keys())}")
            print(f"unit_price 값: {item_purchase_history[0].get('unit_price', '없음')}")
            print(f"total_price 값: {item_purchase_history[0].get('total_price', '없음')}")
        
        # 구매 이력 데이터 천단위 콤마 포맷팅
        purchase_history_records = []
        for record in item_purchase_history:
            formatted_record = record.copy()
            
            # 필수 필드 확인
            print(f"처리 중인 레코드: {formatted_record}")
            
            # 공백 처리된 컬럼명 확인
            for key in list(formatted_record.keys()):
                if ' unit_price' == key:
                    formatted_record['unit_price'] = formatted_record.pop(key)
                if ' total_price' == key:
                    formatted_record['total_price'] = formatted_record.pop(key)
            
            # 단가 포맷팅
            if 'unit_price' in formatted_record and formatted_record['unit_price']:
                try:
                    formatted_record['unit_price'] = format(int(formatted_record['unit_price']), ',')
                except (ValueError, TypeError):
                    pass
            
            # 총액 포맷팅
            if 'total_price' in formatted_record and formatted_record['total_price']:
                try:
                    formatted_record['total_price'] = format(int(formatted_record['total_price']), ',')
                except (ValueError, TypeError):
                    pass
            
            # 수량 포맷팅
            if 'quantity' in formatted_record and formatted_record['quantity']:
                try:
                    formatted_record['quantity'] = format(int(formatted_record['quantity']), ',')
                except (ValueError, TypeError):
                    pass
            
            purchase_history_records.append(formatted_record)
        
        # CSV 데이터 디버깅 로그
        if purchase_history_records:
            print(f"포맷팅 후 첫 번째 레코드: {purchase_history_records[0]}")
        else:
            print("포맷팅된 구매이력 데이터가 없습니다.")
        
        # 연도별 구매 단가 가져오기
        item_annual_price = next((item for item in annual_unit_price if item.get('item_code', '') == item_code), None)
        if not item_annual_price:
            item_annual_price = {'item_code': item_code}
        
        # 예측 가격 가져오기
        item_predict_price = next((item.get('predict_price', 0) for item in predict if item.get('item_code', '') == item_code), 0)
        
        # 그래프 데이터 준비
        years = [key for key in item_annual_price.keys() if key != 'item_code']
        valid_years = []
        valid_prices = []
        
        for year in years:
            price = item_annual_price.get(year)
            if price and str(price).strip():
                valid_years.append(year)
                valid_prices.append(price)
        
        # ChatGPT API를 사용하여 적정구매예산 추천
        recommendation, budget = get_budget_recommendation(item_info, valid_years, valid_prices, item_predict_price)
        
        # Chart.js용 그래프 데이터 준비
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
    
    except Exception as e:
        print(f"구매요청 페이지 처리 중 오류 발생: {e}")
        traceback.print_exc()
        return f"서버 오류가 발생했습니다: {str(e)}", 500

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
            category = item_info.get('category', '')
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
        다음은 품목 '{item_info.get('item', '')}' ({item_info.get('specification', '')})에 대한 정보입니다:
        - 카테고리: {item_info.get('category', '')}
        - 연도별 구매단가: {', '.join([f'{year}: {price}원' for year, price in zip(years, prices)])}
        - 머신러닝으로 예측한 다음해 구매 가격: {predict_price}원
        
        이 정보와 아래 요소들을 고려하여 적정구매예산을 제안해주세요:
        1. 물가상승률
        2. {item_info.get('category', '')} 품종의 시장 동향
        3. {item_info.get('category', '')} 가격에 영향을 미치는 외부환경 요소
        
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
        traceback.print_exc()
        # 오류 발생 시 기본 추천 제공
        return f"현재 시장 상황을 고려할 때, 예측 가격 {predict_price}원에 약 5%의 여유를 추가하는 것이 적절합니다.", round(predict_price * 1.05)

@app.route('/submit_purchase', methods=['POST'])
def submit_purchase():
    try:
        # 구매요청 처리 로직
        # 실제 시스템에서는 DB에 저장하거나 메일 발송 등의 작업 수행
        return jsonify({"status": "success", "message": "구매 요청이 성공적으로 처리되었습니다."})
    except Exception as e:
        print(f"구매 요청 처리 중 오류 발생: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"오류가 발생했습니다: {str(e)}"}), 500

if __name__ == "__main__":
    # 로컬 개발 환경에서는 localhost에서 실행
    # Render.com 등 배포 환경에서는 0.0.0.0으로 바인딩하고 환경 변수에서 포트 가져옴
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port) 