import streamlit as st  # 웹 대시보드 화면을 만드는 라이브러리
import yfinance as yf    # 야후 파이낸스 주가 데이터 라이브러리
import pandas as pd      # 데이터 처리 라이브러리
import numpy as np       # 수학 연산 라이브러리
import plotly.graph_objects as go  # 차트 시각화 라이브러리
from plotly.subplots import make_subplots
import pandas_ta_classic as ta     # 기술적 지표 계산 라이브러리
import requests          # API 전송을 위한 라이브러리

# -----------------------------------------------------------------------------
# [페이지 기본 설정 및 CSS 여백 압축 스타일 적용]
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Quant Technical Analysis & Scanner Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        .stDataFrame td, .stDataFrame th {
            padding-left: 6px !important;
            padding-right: 6px !important;
            padding-top: 4px !important;
            padding-bottom: 4px !important;
            font-size: 14px !important;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# [비밀번호 인증 시스템]
# -----------------------------------------------------------------------------
CORRECT_PASSWORD = "1234"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 퀀트 대시보드 로그인")
    st.markdown("대시보드에 접근하려면 비밀번호를 입력해주세요.")
    
    input_pw = st.text_input("비밀번호", type="password")
    
    if st.button("로그인", use_container_width=True):
        if input_pw == CORRECT_PASSWORD:
            st.session_state.authenticated = True
            st.success("로그인 성공! 대시보드를 불러오는 중...")
            st.rerun()
        else:
            st.error("⚠️ 비밀번호가 틀렸습니다. 다시 확인해 주세요.")
    
    st.stop()

# =============================================================================
# [메인 대시보드 영역]
# =============================================================================

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
        "🪙 바이낸스 코인": {
            "Bitcoin (비트코인)": "BTC-USD",
            "Ethereum (이더리움)": "ETH-USD",
            "Ripple (리플)": "XRP-USD",
            "Solana (솔라나)": "SOL-USD",
            "Dogecoin (도지코인)": "DOGE-USD",
            "Cardano (에이다)": "ADA-USD",
            "Avalanche (아발란체)": "AVAX-USD",
            "Chainlink (체인링크)": "LINK-USD"
        },
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

st.sidebar.markdown("---")
st.sidebar.subheader("➕ 원하는 티커 추가하기")

add_sector = st.sidebar.selectbox("추가 대상 분야", list(st.session_state.sector_stocks.keys()), key="add_sec_box")
new_name = st.sidebar.text_input("종목 이름 (예: 수이 코인)", key="new_stock_name")
new_ticker = st.sidebar.text_input("야후/코인 티커 (예: SUI-USD)", key="new_stock_ticker")

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

st.sidebar.markdown("---")
st.sidebar.subheader("📲 텔레그램 알림 설정")

tg_token = st.sidebar.text_input("봇 토큰 (Bot Token)", type="password", key="tg_token_val")
tg_chat_id = st.sidebar.text_input("채팅 ID (Chat ID)", key="tg_chat_id_val
