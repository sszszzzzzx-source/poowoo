import streamlit as st  # 웹 대시보드 화면을 만드는 라이브러리
import yfinance as yf    # 야후 파이낸스 주가 데이터 라이브러리
import pandas as pd      # 데이터 처리 라이브러리
import numpy as np       # 수학 연산 라이브러리
import plotly.graph_objects as go  # 차트 시각화 라이브러리
from plotly.subplots import make_subplots
import pandas_ta_classic as ta     # 기술적 지표 계산 라이브러리
import requests          # 텔레그램 API 전송을 위한 라이브러리

# -----------------------------------------------------------------------------
# [페이지 기본 설정]
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Quant Technical Analysis & Scanner Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 퀀트 기술적 분석 & 고급 매수 신호 시스템")

# -----------------------------------------------------------------------------
# [텔레그램 메세지 전송 함수]
# -----------------------------------------------------------------------------
def send_telegram_message(token, chat_id, message):
    if not token or not chat_id:
        return False, "봇 토큰과 Chat ID를 모두 입력해주세요."
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=payload, timeout=5)
        if response.status_code == 200:
            return True, "텔레그램 알림 전송 성공!"
        else:
            return False, f"전송 실패 (오류 코드: {response.status_code})"
    except Exception as e:
        return False, f"전송 중 에러 발생: {str(e)}"

# -----------------------------------------------------------------------------
# [AI 실시간 등락 요인 및 시황 분석 함수]
# -----------------------------------------------------------------------------
def generate_market_analysis(stock_name, ticker, df, news_items, change_pct):
    if df.empty:
        return "분석할 데이터가 없습니다."
    
    latest = df.iloc[-1]
    rsi = latest['RSI'] if 'RSI' in df.columns and pd.notnull(latest['RSI']) else 50
    mdd = latest['MDD_Pct'] if 'MDD_Pct' in df.columns and pd.notnull(latest['MDD_Pct']) else 0
    
    news_summaries = []
    if news_items:
        for item in news_items[:3]:
            news_summaries.append(item.get('title', ''))
    
    news_text = " / ".join(news_summaries) if news_summaries else "최근 특이 뉴스 없음"
    
    analysis = f"🤖 **[AI 실시간 등락 요인 및 시황 분석]**\n\n"
    if change_pct >= 0:
        analysis += f"• **등락 현황**: **{stock_name} ({ticker})** 종목은 최근 기준 **+{change_pct:.2f}% 상승세(반등)**를 나타내고 있습니다.\n"
        analysis += f"• **상승 분석**: RSI({rsi:.2f}) 지표와 볼린저밴드 하단 부근에서의 저가 매수세 유입, 그리고 기술적 반등 모멘텀이 복합적으로 작용하고 있을 가능성이 높습니다.\n"
    else:
        analysis += f"• **등락 현황**: **{stock_name} ({ticker})** 종목은 최근 기준 **{change_pct:.2f}% 하락세(조정)**를 나타내고 있습니다.\n"
        analysis += f"• **하락 분석**: 고점 대비 낙폭(MDD: {mdd:.2f}%)이 발생하며 단기 매물 출회 및 조정 국면에 진입해 있으며, RSI({rsi:.2f}) 과매도 구간 지지력 테스트가 진행 중입니다.\n"
    
    analysis += f"• **관련 뉴스 헤드라인**: {news_text}"
    return analysis

# -----------------------------------------------------------------------------
# [1. 분야별 하위 종목 (티커) 세션 상태 초기화 및 관리]
# -----------------------------------------------------------------------------
if "sector_stocks" not in st.session_state:
    st.session_state.sector_stocks = {
        "양자컴퓨터": {
            "QTUM (Defiance 양자컴퓨터 ETF)": "QTUM",
            "DFNC (Defiance Quantum ETF)": "DFNC",
            "IonQ (아이온큐)": "IONQ",
            "IONX (2X Long IONQ ETF)": "IONX",
            "D-Wave Quantum (디 웨이브 퀀텀)": "QBTS",
            "Rigetti Computing (리게티 컴퓨팅)": "RGTI",
            "Quantum Computing (퀀텀 컴퓨팅)": "QUBT",
            "American Superconductor (아메리칸 수퍼컨덕터)": "AMSC",
            "Sealsq (실스크)": "LAES",
            "BTQ Technologies (BTQ 테크놀로지스)": "BTQ.V",
            "Honeywell (하니웰 - Quantinuum)": "HON"
        },
        "AI에너지": {
            "Bloom Energy (블룸 에너지)": "BE",
            "Vistra (비스트라)": "VST",
            "NuScale Power (뉴스케일 파워)": "SMR",
            "Oklo (오클로)": "OKLO",
            "Nano Nuclear Energy (나노 뉴클리어)": "NNE",
            "GE Vernova (GE 버노바)": "GEV",
            "Vertiv Holdings (버티브 홀딩스)": "VRT",
            "Iren (아이렌)": "IREN",
            "Eos Energy (이오스 에너지)": "EOSE",
            "Constellation Energy (콘스텔레이션)": "CEG",
            "Applied Optoelectronics (어플라이드 옵토)": "AAOI",
            "Eaton (이튼)": "ETN",
            "Modine Manufacturing (모딘 매뉴팩처링)": "MOD",
            "Amphenol (암페놀)": "APH",
            "First Solar (퍼스트 솔라)": "FSLR",
            "Fabrinet (패브리넷)": "FN"
        },
        "AI": {
            "NVIDIA (엔비디아)": "NVDA",
            "Microsoft (마이크로소프트)": "MSFT",
            "Broadcom (브로드컴)": "AVGO",
            "AMD": "AMD",
            "Palantir (팔란티어)": "PLTR"
        },
        "우주": {
            "Rocket Lab (로켓랩)": "RKLB",
            "Intuitive Machines (인투이티브 머신스)": "LUNR",
            "AST Spacemobile (AST 스페이스모바일)": "ASTS",
            "Planet Labs (플래닛 랩스)": "PL"
        },
        "로봇": {
            "Intuitive Surgical (인투이티브 서지컬)": "ISRG",
            "Symbotic (심보틱)": "SYM",
            "Servicenow (서비스나우)": "NOW",
            "iRobot (아이로봇)": "IRBT"
        },
        "나스닥": {
            "Apple (애플)": "AAPL",
            "Amazon (아마존)": "AMZN",
            "Alphabet (구글)": "GOOGL",
            "Meta (메타)": "META",
            "Tesla (테슬라)": "TSLA"
        },
        "ETF": {
            "QQQ (나스닥 100 ETF)": "QQQ",
            "TQQQ (나스닥 3배 레버리지)": "TQQQ",
            "SOXX (반도체 ETF)": "SOXX",
            "SOXL (반도체 3배 레버리지)": "SOXL",
            "JEPQ (JP모건 나스닥 커버드콜)": "JEPQ"
        }
    }

# -----------------------------------------------------------------------------
# [사이드바 구성]
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 분석 및 스캔 설정")

selected_sector = st.sidebar.selectbox("1. 분야 선택", list(st.session_state.sector_stocks.keys()))

stock_dict = st.session_state.sector_stocks[selected_sector]
selected_stock_name = st.sidebar.selectbox("2. 개별 분석 종목 선택", list(stock_dict.keys()))
ticker_symbol = stock_dict[selected_stock_name]

timeframe_map = {
    "전체 일봉 (All History)": ("1d", "max"),
    "전체 주봉 (Weekly All)": ("1wk", "max"),
    "전체 월봉 (Monthly All)": ("1mo", "max"),
    "최근 5년 일봉 (5 Years)": ("1d", "5y"),
    "4시간봉 (4 Hours - 최근 60일)": ("60m", "60d"),
    "1시간봉 (1 Hour - 최근 60일)": ("60m", "60d"),
    "10분봉 (10 Mins - 최근 5일)": ("10m", "5d"),
    "5분봉 (5 Mins - 최근 7일)": ("5m", "7d")
}

selected_tf_name = st.sidebar.selectbox("3. 차트 타임프레임 (봉) 선택", list(timeframe_map.keys()))
interval_code, period_code = timeframe_map[selected_tf_name]

# 티커 직접 추가
st.sidebar.markdown("---")
st.sidebar.subheader("➕ 원하는 티커 추가하기")

add_sector = st.sidebar.selectbox("추가 대상 분야", list(st.session_state.sector_stocks.keys()), key="add_sec_box")
new_name = st.sidebar.text_input("종목 이름 (예: 코인베이스)", key="new_stock_name")
new_ticker = st.sidebar.text_input("야후 티커 (예: COIN)", key="new_stock_ticker")

if st.sidebar.button("🚀 분야에 종목 추가", use_container_width=True):
    if new_name and new_ticker:
        clean_ticker = new_ticker.upper().strip()
        duplicate_sector = None
        for sec, stocks in st.session_state.sector_stocks.items():
            if clean_ticker in stocks.values():
                duplicate_sector = sec
                break
        
        if duplicate_sector:
            st.sidebar.error(f"⚠️ 티커 '{clean_ticker}'는 이미 [{duplicate_sector}] 분야에 등록되어 있습니다!")
        else:
            formatted_name = f"{new_name} ({clean_ticker})"
            st.session_state.sector_stocks[add_sector][formatted_name] = clean_ticker
            st.sidebar.success(f"'{formatted_name}' 추가 완료!")
            st.rerun()
    else:
        st.sidebar.warning("종목 이름과 티커를 모두 입력해주세요.")

st.sidebar.markdown("---")
st.sidebar.subheader("🚨 단타 매수 신호 알림 기준")
mdd_threshold = st.sidebar.slider("이전 고점 대비 하락 폭 (MDD %)", min_value=1.0, max_value=15.0, value=3.0, step=0.5)
rsi_threshold = st.sidebar.slider("RSI 상한 기준 (이하)", min_value=20, max_value=50, value=42, step=1)
use_ma_filter = st.sidebar.checkbox("20일선 위에 위치한 정배열 종목만 매수신호 허용", value=False)

# 텔레그램 설정
st.sidebar.markdown("---")
st.sidebar.subheader("📲 텔레그램 알림 설정")

tg_token = st.sidebar.text_input("봇 토큰 (Bot Token)", type="password", key="tg_token_val")
tg_chat_id = st.sidebar.text_input("채팅 ID (Chat ID)", key="tg_chat_id_val")

if st.sidebar.button("🔔 텔레그램 연동 테스트", use_container_width=True):
    success, msg = send_telegram_message(
        tg_token, 
        tg_chat_id, 
        f"✅ *[Quant System]* 텔레그램 연동 성공!\n연동 시간: 정상 작동 중"
    )
    if success:
        st.sidebar.success(msg)
    else:
        st.sidebar.error(msg)

st.sidebar.markdown("---")
st.sidebar.subheader("📅 주요 거시경제 일정")
st.sidebar.link_button("🗓️ Investing.com 경제캘린더", "https://kr.investing.com/economic-calendar/", use_container_width=True)

# -----------------------------------------------------------------------------
# [2. 데이터 수집 및 기술적 지표 연산]
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_and_analyze_data(ticker, interval, period, mdd_crit, rsi_crit, ma_filter):
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    
    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        df = df.xs(ticker, axis=1, level=1)

    # 1. 이동평균선
    df['SMA20'] = df['Close'].rolling(window=20).mean()
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['SMA120'] = df['Close'].rolling(window=120).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()

    # 2. RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # 3. 볼린저밴드 (20, 2)
    std = df['Close'].rolling(window=20).std()
    df['BB_Middle'] = df['SMA20']
    df['BB_Upper'] = df['SMA20'] + (std * 2)
    df['BB_Lower'] = df['SMA20'] - (std * 2)

    # 4. MACD (12, 26, 9)
    try:
        macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        if macd is not None and not macd.empty:
            df['MACD'] = macd.iloc[:, 0]
            df['MACD_Hist'] = macd.iloc[:, 1]
            df['MACD_Signal'] = macd.iloc[:, 2]
    except Exception:
        exp12 = df['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

    # 5. ATR
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14).mean()

    # 6. MDD 및 매수 신호
    df['Rolling_Max'] = df['High'].rolling(window=30).max()
    df['MDD_Pct'] = ((df['Close'] - df['Rolling_Max']) / df['Rolling_Max']) * 100

    base_signal = (
        (df['MDD_Pct'] <= -mdd_crit) & 
        (df['Close'] <= df['BB_Lower'] * 1.01) & 
        (df['RSI'] < rsi_crit)
    )

    if ma_filter:
        df['Buy_Signal'] = base_signal & (df['Close'] >= df['SMA20'])
    else:
        df['Buy_Signal'] = base_signal

    return df

def run_backtest(df, target_pct=5.0, stop_pct=3.0, hold_bars=10):
    signals = df[df['Buy_Signal']].index
    results = []

    for idx in signals:
        loc = df.index.get_loc(idx)
        if loc + hold_bars >= len(df):
            continue
        
        buy_price = df.iloc[loc]['Close']
        future_data = df.iloc[loc+1 : loc+1+hold_bars]
        
        max_price = future_data['High'].max()
        min_price = future_data['Low'].min()
        
        max_return = ((max_price - buy_price) / buy_price) * 100
        min_return = ((min_price - buy_price) / buy_price) * 100
        
        if max_return >= target_pct:
            success = True
        elif min_return <= -stop_pct:
            success = False
        else:
            final_price = future_data.iloc[-1]['Close']
            ret = ((final_price - buy_price) / buy_price) * 100
            success = ret > 0

        results.append({
            "날짜": idx.strftime('%Y-%m-%d %H:%M') if hasattr(idx, 'strftime') else str(idx),
            "매수가 ($)": buy_price,
            "최고 수익률 (%)": max_return,
            "최대 손실률 (%)": min_return,
            "성공 여부": "✅ 성공" if success else "❌ 실패"
        })
    
    return pd.DataFrame(results)

@st.cache_data(ttl=600)
def get_stock_news(ticker):
    try:
        t = yf.Ticker(ticker)
        return t.news
    except Exception:
        return []

@st.cache_data(ttl=600)
def get_option_chain_data(ticker, expiration_date=None):
    """야후 파이낸스에서 옵션 체인 데이터 수집"""
    try:
        t = yf.Ticker(ticker)
        expirations = t.options
        if not expirations:
            return None, None, []
        
        selected_exp = expiration_date if expiration_date in expirations else expirations[0]
        opt = t.option_chain(selected_exp)
        return opt.calls, opt.puts, expirations
    except Exception:
        return None, None, []

# -----------------------------------------------------------------------------
# [3. 메인 대시보드 화면 구성 (탭 UI)]
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 개별 종목 차트 & 뉴스", 
    "📈 백테스팅 승률 검증",
    "🚨 섹터 전체 종목 신호 스캐너", 
    "📐 피보나치 되돌림 분석",
    "📊 콜/풋 옵션 분석"
])

df = load_and_analyze_data(ticker_symbol, interval_code, period_code, mdd_threshold, rsi_threshold, use_ma_filter)

# -----------------------------------------------------------------------------
# TAB 1: 개별 종목 차트 & 뉴스
# -----------------------------------------------------------------------------
with tab1:
    if df.empty:
        st.error(f"'{ticker_symbol}'의 데이터를 불러오지 못했습니다. 선택하신 봉(타임프레임) 기간이나 티커 기호를 확인해 주세요.")
    else:
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        change_pct = ((latest['Close'] - prev['Close']) / prev['Close']) * 100

        atr_val = latest['ATR'] if pd.notnull(latest['ATR']) else (latest['Close'] * 0.02)
        target_1 = latest['Close'] + (atr_val * 1.5)
        target_2 = latest['Close'] + (atr_val * 3.0)
        stop_loss = latest['Close'] - (atr_val * 1.5)

        st.subheader(f"📌 {selected_stock_name} ({ticker_symbol}) - {selected_tf_name}")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("현재가", f"${latest['Close']:.2f}", f"{change_pct:.2f}%")
        col2.metric("RSI (14)", f"{latest['RSI']:.2f}" if pd.notnull(latest['RSI']) else "N/A")
        col3.metric("ATR (변동성 폭)", f"${atr_val:.2f}")
        col4.metric("추천 1차 목표가", f"${target_1:.2f}", f"손절가: ${stop_loss:.2f}")

        if latest['Buy_Signal']:
            st.error(f"🚨 [단타 매수 신호 포착] -{mdd_threshold}% 하락 + 볼린저 하단 접근 + RSI {rsi_threshold} 미만 조건 충족!")

        # 🤖 AI 실시간 등락 요인 및 시황 분석 박스
        news_items = get_stock_news(ticker_symbol)
        analysis_msg = generate_market_analysis(selected_stock_name, ticker_symbol, df, news_items, change_pct)
        st.info(analysis_msg)

        fig = make_subplots(
            rows=4, cols=1, 
            shared_xaxes=True, 
            vertical_spacing
