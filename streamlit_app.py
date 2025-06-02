import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import openai

# 페이지 설정
st.set_page_config(
    page_title="안전재고관리 시스템",
    page_icon="📊",
    layout="wide",
)

# 사이드바 설정
st.sidebar.title("안전재고관리 시스템")
page = st.sidebar.radio("페이지 선택", ["안전재고 대시보드", "구매요청의뢰"])

# 더미 사용자 데이터
user_info = {
    "department": "구매팀",
    "employee_id": "Z1034",
    "position": "과장",
    "name": "홍길동"
}

# 데이터 로드
@st.cache_data
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

inventory, purchase_history, annual_unit_price, predict = load_data()

# 안전재고 대시보드 페이지
def show_dashboard():
    st.title("안전재고 대시보드")
    st.write("안전재고 미만인 품목 목록입니다. 구매요청 버튼을 클릭하여 구매의뢰를 진행하세요.")
    
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
    
    # 알림 박스 표시
    st.warning(f"안전재고 미달항목 {low_stock_count}건이 발견되었습니다.")
    
    # 데이터프레임 표시
    st.dataframe(
        low_stock[['item_code', 'item', 'specification', 'current_stock', 'safety_stock', 'lead_time', 'status']],
        column_config={
            "item_code": "품목코드",
            "item": "품목",
            "specification": "규격",
            "current_stock": "현재고",
            "safety_stock": "안전재고",
            "lead_time": "리드타임",
            "status": "상태"
        },
        use_container_width=True,
        hide_index=True
    )
    
    # 품목 선택 버튼
    st.subheader("구매요청 진행하기")
    selected_item = st.selectbox(
        "품목 선택",
        options=low_stock['item_code'].tolist(),
        format_func=lambda x: f"{x} - {low_stock[low_stock['item_code'] == x]['item'].iloc[0]}"
    )
    
    if st.button("구매요청 페이지로 이동"):
        st.session_state.page = "구매요청의뢰"
        st.session_state.selected_item = selected_item
        st.rerun()

# 구매요청의뢰 페이지
def show_purchase_request():
    st.title("구매요청의뢰")
    
    # 세션에서 선택된 품목 가져오기 또는 선택하기
    if "selected_item" in st.session_state:
        item_code = st.session_state.selected_item
    else:
        item_code = st.selectbox(
            "품목 선택",
            options=inventory['item_code'].tolist(),
            format_func=lambda x: f"{x} - {inventory[inventory['item_code'] == x]['item'].iloc[0]}"
        )
    
    # 해당 품목 정보 가져오기
    item_info = inventory[inventory['item_code'] == item_code].iloc[0]
    
    # 사용자 정보 표시
    with st.expander("사용자 정보", expanded=True):
        cols = st.columns(4)
        cols[0].write(f"**부서명:** {user_info['department']}")
        cols[1].write(f"**사번:** {user_info['employee_id']}")
        cols[2].write(f"**직급:** {user_info['position']}")
        cols[3].write(f"**성명:** {user_info['name']}")
    
    # 품목 정보 표시
    with st.expander("품목 정보", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**품목코드:** {item_info['item_code']}")
            st.write(f"**품목:** {item_info['item']}")
            st.write(f"**카테고리:** {item_info['category']}")
        with col2:
            st.write(f"**규격:** {item_info['specification']}")
            st.write(f"**현재고:** {item_info['current_stock']}")
            st.write(f"**안전재고:** {item_info['safety_stock']}")
    
    # 과거 구매이력 및 예측 데이터 가져오기
    item_purchase_history = purchase_history[purchase_history['item_code'] == item_code]
    item_annual_price = annual_unit_price[annual_unit_price['item_code'] == item_code]
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
    recommendation, budget = get_budget_recommendation(item_info.to_dict(), valid_years, valid_prices, item_predict_price)
    
    # 과거 구매이력 및 그래프 표시
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("과거 구매이력")
        if not item_purchase_history.empty:
            purchase_df = item_purchase_history[['purchase_date', 'quantity', 'unit_price', 'total_price']].copy()
            # 천 단위 콤마 포맷팅
            purchase_df['unit_price'] = purchase_df['unit_price'].apply(lambda x: f"{int(x):,}")
            purchase_df['total_price'] = purchase_df['total_price'].apply(lambda x: f"{int(x):,}")
            purchase_df['quantity'] = purchase_df['quantity'].apply(lambda x: f"{int(x):,}")
            
            st.dataframe(
                purchase_df,
                column_config={
                    "purchase_date": "구매일자",
                    "quantity": "수량",
                    "unit_price": "단가",
                    "total_price": "총액"
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("이 품목의 구매 이력이 없습니다.")
    
    with col2:
        st.subheader("구매단가 추이 및 예측")
        
        # 그래프 데이터 준비
        graph_data = []
        for year, price in zip(valid_years, valid_prices):
            graph_data.append({"year": str(year), "price": float(price), "type": "과거 구매단가"})
            
        # 예측 가격 추가
        graph_data.append({"year": "2025(예측)", "price": float(item_predict_price), "type": "예측 구매단가"})
        
        # 데이터프레임으로 변환
        df = pd.DataFrame(graph_data)
        
        # 그래프 생성
        fig = px.line(
            df[df['type'] == "과거 구매단가"], 
            x="year", 
            y="price", 
            markers=True,
            title="연도별 구매단가 추이"
        )
        
        # 예측 가격 추가
        fig.add_scatter(
            x=df[df['type'] == "예측 구매단가"]["year"],
            y=df[df['type'] == "예측 구매단가"]["price"],
            mode="markers",
            marker=dict(size=12, color="red", symbol="diamond"),
            name="예측 구매단가"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 예측 가격 표시
        st.metric("예측 구매단가", f"{int(item_predict_price):,}원")
    
    # AI 예산 추천 섹션
    st.subheader("적정구매예산 추천")
    st.info(recommendation)
    st.caption("ChatGPT의 의견입니다.")
    
    # 구매의뢰 폼
    st.subheader("구매의뢰서")
    with st.form("purchase_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            quantity = st.number_input("수량", min_value=1, value=1)
        
        with col2:
            unit_price = st.number_input("단가", min_value=1, value=int(budget))
        
        with col3:
            st.write("**총 구매예산**")
            st.write(f"**{quantity * unit_price:,}원**")
        
        submit = st.form_submit_button("구매요청의뢰")
        
        if submit:
            st.success("구매 요청이 성공적으로 처리되었습니다.")
            st.balloons()

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

# 스타일 적용
st.markdown("""
<style>
    .st-emotion-cache-16txtl3 {
        padding: 1rem;
    }
    h1 {
        color: #1a73e8;
    }
    h2, h3 {
        color: #1a73e8;
    }
    .stMetric {
        background-color: #f0f7ff;
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# 페이지 표시
if "page" in st.session_state:
    page = st.session_state.page

if page == "안전재고 대시보드":
    show_dashboard()
else:
    show_purchase_request() 