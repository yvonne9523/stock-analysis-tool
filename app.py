import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import datetime

# -----------------------------------------------------------------------------
# 頁面配置與高質感深色 CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="全球股市小工具 - AI 股票與大盤量化分析終端",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .block-container { 
        padding-top: 3.2rem !important; 
        padding-bottom: 2rem; 
    }
    
    .card-box {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 18px 20px;
        margin-bottom: 15px;
    }
    .target-box {
        background: #0d1117;
        border: 1px solid #21262d;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }
    .target-title { font-size: 0.85rem; color: #8b949e; margin-bottom: 4px; }
    .target-val-buy { font-size: 1.45rem; font-weight: 700; color: #f85149; }
    .target-val-sell { font-size: 1.45rem; font-weight: 700; color: #3fb950; }
    .target-val-stop { font-size: 1.45rem; font-weight: 700; color: #e3b341; }
    .target-desc { font-size: 0.8rem; color: #8b949e; margin-top: 4px; }
    
    .decision-strong-buy {
        background: linear-gradient(145deg, rgba(248, 81, 73, 0.25), rgba(248, 81, 73, 0.08));
        border: 2px solid #f85149;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }
    .decision-batch-buy {
        background: linear-gradient(145deg, rgba(56, 189, 248, 0.25), rgba(56, 189, 248, 0.08));
        border: 2px solid #38bdf8;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }
    .decision-wait {
        background: linear-gradient(145deg, rgba(227, 179, 65, 0.25), rgba(227, 179, 65, 0.08));
        border: 2px solid #e3b341;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }
    .decision-avoid {
        background: linear-gradient(145deg, rgba(63, 185, 80, 0.25), rgba(63, 185, 80, 0.08));
        border: 2px solid #3fb950;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }

    div[data-testid="stRadio"] > div {
        flex-direction: row;
        align-items: center;
        gap: 15px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 分市場股票代碼解析字典
# -----------------------------------------------------------------------------
TW_KNOWN_MAP = {
    "台積電": "2330", "TSMC": "2330", "2330": "2330",
    "聯發科": "2454", "2454": "2454",
    "鴻海": "2317", "2317": "2317",
    "華邦電": "2344", "2344": "2344",
    "長榮": "2603", "2603": "2603",
    "長榮航": "2618", "2618": "2618",
    "陽明": "2609", "2609": "2609",
    "萬海": "2615", "2615": "2615",
    "廣達": "2382", "2382": "2382",
    "緯創": "3231", "3231": "3231",
    "技嘉": "2376", "2376": "2376",
    "華碩": "2357", "2357": "2357",
    "台新金": "2887", "2887": "2887",
    "富邦金": "2881", "2881": "2881",
    "國泰金": "2882", "2882": "2882",
    "中信金": "2891", "2891": "2891",
    "玉山金": "2884", "2884": "2884",
    "兆豐金": "2886", "2886": "2886",
    "0050": "0050", "元大台灣50": "0050",
    "0056": "0056", "元大高股息": "0056",
    "00878": "00878", "國泰永續高股息": "00878",
    "00919": "00919", "群益台灣精選高息": "00919",
    "00929": "00929", "復華台灣科技優息": "00929",
    "00940": "00940", "元大台灣價值高息": "00940"
}

US_KNOWN_MAP = {
    "台積電": "TSM", "台積電ADR": "TSM", "TSM": "TSM",
    "輝達": "NVDA", "NVIDIA": "NVDA", "NVDA": "NVDA",
    "特斯拉": "TSLA", "TESLA": "TSLA", "TSLA": "TSLA",
    "蘋果": "AAPL", "APPLE": "AAPL", "AAPL": "AAPL",
    "微軟": "MSFT", "MICROSOFT": "MSFT", "MSFT": "MSFT",
    "谷歌": "GOOGL", "GOOGLE": "GOOGL", "GOOGL": "GOOGL",
    "亞馬遜": "AMZN", "AMAZON": "AMZN", "AMZN": "AMZN",
    "臉書": "META", "META": "META",
    "超微": "AMD", "AMD": "AMD",
    "博通": "AVGO", "AVGO": "AVGO",
    "ARM": "ARM", "安謀": "ARM",
    "PLTR": "PLTR", "帕蘭提爾": "PLTR",
    "COIN": "COIN", "微策略": "MSTR", "MSTR": "MSTR",
    "QQQ": "QQQ", "SPY": "SPY", "SOXX": "SOXX"
}

INDEX_KNOWN_MAP = {
    "台股大盤": "^TWII", "加權指數": "^TWII", "TAIEX": "^TWII", "^TWII": "^TWII",
    "櫃買指數": "^TWOII", "櫃買": "^TWOII", "OTC": "^TWOII", "^TWOII": "^TWOII",
    "那斯達克": "^IXIC", "那指": "^IXIC", "NASDAQ": "^IXIC", "^IXIC": "^IXIC",
    "標普500": "^GSPC", "S&P500": "^GSPC", "SPX": "^GSPC", "^GSPC": "^GSPC",
    "費城半導體": "^SOX", "費半": "^SOX", "SOX": "^SOX", "^SOX": "^SOX",
    "道瓊指數": "^DJI", "道瓊": "^DJI", "DJI": "^DJI", "^DJI": "^DJI",
    "日經225": "^N225", "日經": "^N225", "^N225": "^N225"
}

@st.cache_data(ttl=86400, show_spinner=False)
def load_all_taiwan_stock_mapping():
    mapping = {}
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        res = requests.get(url, timeout=6).json()
        for item in res:
            code = item.get("Code", "").strip()
            name = item.get("Name", "").strip()
            if code and name:
                mapping[name] = code
                mapping[code] = code
    except Exception:
        pass
    mapping.update(TW_KNOWN_MAP)
    return mapping

def resolve_by_market(market_type, query_text):
    cleaned = query_text.strip().upper().replace(".TW", "").replace(".TWO", "")
    
    if "台灣" in market_type:
        tw_map = load_all_taiwan_stock_mapping()
        if cleaned in tw_map:
            code = tw_map[cleaned]
            name = query_text.strip()
            for k, v in tw_map.items():
                if v == code and not k.isdigit():
                    name = k
                    break
            return code, name
        for k, v in tw_map.items():
            if cleaned in k or k in cleaned:
                return v, k
        if cleaned.isdigit():
            return cleaned, f"台股 {cleaned}"
        return cleaned, cleaned
        
    elif "美國" in market_type:
        if query_text.strip() in US_KNOWN_MAP:
            return US_KNOWN_MAP[query_text.strip()], f"{query_text.strip()} (美股)"
        if cleaned in US_KNOWN_MAP:
            return US_KNOWN_MAP[cleaned], f"{cleaned} (美股)"
        for name, code in US_KNOWN_MAP.items():
            if name in query_text or query_text in name:
                return code, f"{name} (美股)"
        return cleaned, f"{cleaned} (美股)"
        
    else:
        if query_text.strip() in INDEX_KNOWN_MAP:
            return INDEX_KNOWN_MAP[query_text.strip()], query_text.strip()
        if cleaned in INDEX_KNOWN_MAP:
            return INDEX_KNOWN_MAP[cleaned], query_text.strip()
        for name, code in INDEX_KNOWN_MAP.items():
            if name in query_text or query_text in name:
                return code, name
        return cleaned, cleaned

# -----------------------------------------------------------------------------
# 資料獲取模組
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def fetch_twse_live_fundamentals(stock_id):
    url = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL"
    try:
        res = requests.get(url, timeout=6)
        if res.status_code == 200:
            for item in res.json():
                if item.get("Code") == stock_id:
                    pe_str = item.get("PEratio", "")
                    pb_str = item.get("PBratio", "")
                    yield_str = item.get("DividendYield", "")
                    pe_val = float(pe_str.replace(",", "")) if pe_str and pe_str != "-" else None
                    pb_val = float(pb_str.replace(",", "")) if pb_str and pb_str != "-" else None
                    yield_val = float(yield_str.replace(",", "")) if yield_str and yield_str != "-" else None
                    roe_val = (pb_val / pe_val) if (pb_val and pe_val and pe_val > 0) else None
                    return {
                        "trailingPE": pe_val, "priceToBook": pb_val,
                        "dividendYield": yield_val, "returnOnEquity": roe_val
                    }
    except Exception:
        pass
    return {}

def get_tw_stock_kline(stock_id, days=240):
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
        "start_date": start_date,
        "end_date": end_date
    }
    try:
        res = requests.get(url, params=params, timeout=8).json()
        if res.get("msg") == "success" and len(res.get("data", [])) > 0:
            df = pd.DataFrame(res["data"])
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            df.rename(columns={
                "open": "Open", "max": "High", "min": "Low",
                "close": "Close", "Trading_Volume": "Volume"
            }, inplace=True)
            return df[["Open", "High", "Low", "Close", "Volume"]]
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def load_market_data_routed(market_type, ticker_str, period_str):
    raw_code, display_name = resolve_by_market(market_type, ticker_str)
    days_map = {"3mo": 120, "6mo": 200, "1y": 380, "2y": 750}
    target_days = days_map.get(period_str, 200)
    
    df = pd.DataFrame()
    fund_info = {}
    
    if "台灣" in market_type and raw_code.isdigit():
        df = get_tw_stock_kline(raw_code, days=target_days)
        fund_info = fetch_twse_live_fundamentals(raw_code)
        if not df.empty and fund_info.get("trailingPE"):
            curr_p = float(df.iloc[-1]["Close"])
            fund_info["trailingEps"] = round(curr_p / fund_info["trailingPE"], 2)
        fund_info["longName"] = display_name
        
    if df.empty or fund_info.get("trailingPE") is None:
        try:
            yf_code = f"{raw_code}.TW" if ("台灣" in market_type and raw_code.isdigit()) else raw_code
            t = yf.Ticker(yf_code)
            if df.empty:
                df = t.history(period=period_str)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
            y_info = t.info
            for k in ["trailingPE", "priceToBook", "dividendYield", "trailingEps", "returnOnEquity"]:
                if fund_info.get(k) is None and y_info.get(k) is not None:
                    fund_info[k] = y_info.get(k)
            if not fund_info.get("longName"):
                fund_info["longName"] = y_info.get("longName", display_name)
        except Exception:
            pass
            
    return df, fund_info, raw_code, display_name

@st.cache_data(ttl=300, show_spinner=False)
def fetch_global_indices():
    indices = [
        {"name": "台股加權指數", "ticker": "^TWII"},
        {"name": "那斯達克 (美股科技)", "ticker": "^IXIC"},
        {"name": "標普500 (美股大型)", "ticker": "^GSPC"},
        {"name": "費城半導體", "ticker": "^SOX"},
    ]
    results = []
    for item in indices:
        try:
            t = yf.Ticker(item["ticker"])
            hist = t.history(period="5d")
            if len(hist) >= 2:
                curr = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                diff = curr - prev
                pct = (diff / prev) * 100
                results.append({
                    "name": item["name"], "price": curr,
                    "diff": diff, "pct": pct, "ticker": item["ticker"]
                })
        except Exception:
            pass
    return results

def compute_all_indicators(df):
    if df.empty or len(df) < 5:
        return df
    
    df["MA5"] = df["Close"].rolling(window=5).mean()
    df["MA20"] = df["Close"].rolling(window=20).mean()
    df["MA60"] = df["Close"].rolling(window=60).mean()
    
    df["BB_mid"] = df["Close"].rolling(window=20).mean()
    df["BB_std"] = df["Close"].rolling(window=20).std()
    df["BB_upper"] = df["BB_mid"] + 2 * df["BB_std"]
    df["BB_lower"] = df["BB_mid"] - 2 * df["BB_std"]
    
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))
    
    low_min = df["Low"].rolling(window=14).min()
    high_max = df["High"].rolling(window=14).max()
    rsv = 100 * ((df["Close"] - low_min) / (high_max - low_min + 1e-9))
    k_list, d_list = [], []
    k_prev, d_prev = 50.0, 50.0
    for val in rsv:
        if np.isnan(val):
            k_list.append(np.nan); d_list.append(np.nan)
        else:
            k_curr = (2/3) * k_prev + (1/3) * val
            d_curr = (2/3) * d_prev + (1/3) * k_curr
            k_list.append(k_curr); d_list.append(d_curr)
            k_prev, d_prev = k_curr, d_curr
    df["K"] = k_list
    df["D"] = d_list
    
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD_DIF"] = ema12 - ema26
    df["MACD_DEM"] = df["MACD_DIF"].ewm(span=9, adjust=False).mean()
    df["MACD_OSC"] = df["MACD_DIF"] - df["MACD_DEM"]
    return df

# -----------------------------------------------------------------------------
# 頂部大盤走勢看板
# -----------------------------------------------------------------------------
st.markdown("### 🌐 全球核心大盤即時行情")
market_indices = fetch_global_indices()

if market_indices:
    m_cols = st.columns(len(market_indices))
    for i, idx in enumerate(market_indices):
        d_color = "#f85149" if idx["diff"] >= 0 else "#3fb950"
        arrow = "▲" if idx["diff"] >= 0 else "▼"
        with m_cols[i]:
            st.markdown(f"""
            <div class="target-box" style="margin-bottom: 8px;">
                <div style="font-size: 0.8rem; color: #8b949e;">{idx['name']}</div>
                <div style="font-size: 1.3rem; font-weight: 700; color: #ffffff;">{idx['price']:,.2f}</div>
                <div style="font-size: 0.8rem; color: {d_color}; font-weight: 600;">{arrow} {idx['diff']:+,.2f} ({idx['pct']:+.2f}%)</div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("<hr style='border-color: #21262d; margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 側邊欄：全球股市小工具
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🌐 全球股市小工具")
    
    market_select = st.selectbox(
        "選擇市場別",
        options=["🇹🇼 台灣股市 (上市 / 櫃 / ETF)", "🇺🇸 美國股市 (美股 / ADR / ETF)", "🌐 全球大盤指數 (加權 / 那指 / 標普)"],
        index=0
    )
    
    default_ph = "例如: 台積電、鴻海、2330、0050" if "台灣" in market_select else "例如: NVDA、TSLA、AAPL、台積電" if "美國" in market_select else "例如: 加權指數、那斯達克、標普500"
    default_val = "台積電" if "台灣" in market_select else "NVDA" if "美國" in market_select else "加權指數"
    
    search_query = st.text_input(
        "輸入股票名稱或代碼",
        value=default_val,
        placeholder=default_ph
    ).strip()
    
    period_option = st.selectbox(
        "週期長度",
        options=["3mo", "6mo", "1y", "2y"],
        index=1,
        format_func=lambda x: {"3mo": "近 3 個月", "6mo": "近 6 個月", "1y": "近 1 年", "2y": "近 2 年"}.get(x, x)
    )
    
    st.markdown("---")
    st.caption("✨ **全球股市量化分析**：台股精準對應 2330，美股即時行情同步！")
    btn_refresh = st.button("🚀 重新載入", use_container_width=True)

# -----------------------------------------------------------------------------
# 主畫面呈現
# -----------------------------------------------------------------------------
if search_query:
    with st.spinner(f"正在載入「{search_query}」行情與決策診斷..."):
        df, info, clean_code, display_name = load_market_data_routed(market_select, search_query, period_option)
        
        if df is None or df.empty or len(df) < 5:
            st.error(f"❌ 查無「{search_query}」的價格資訊。")
            st.info("💡 請確認代碼或名稱是否屬於所選市場（例如在台股搜尋 `2330` 或 `台積電`；美股搜尋 `NVDA` 或 `TSM`）。")
        else:
            df = compute_all_indicators(df)
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            curr_price = float(latest["Close"])
            prev_price = float(prev["Close"])
            diff = curr_price - prev_price
            pct = (diff / prev_price) * 100 if prev_price != 0 else 0
            
            now_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            
            recent_window = df.tail(min(len(df), 60))
            recent_high = float(recent_window["High"].max())
            recent_low = float(recent_window["Low"].min())
            
            ma5 = float(latest["MA5"]) if not np.isnan(latest["MA5"]) else curr_price
            ma20 = float(latest["MA20"]) if not np.isnan(latest["MA20"]) else curr_price
            ma60 = float(latest["MA60"]) if not np.isnan(latest["MA60"]) else curr_price
            
            # --- 短・中・長線 關鍵價位演算法 ---
            # 1. 短線 (1~2週)：5日線防守，目標前波近期小高點 (+5%)
            short_buy_low = round(min(ma5, curr_price * 0.98), 1)
            short_buy_high = round(curr_price, 1)
            short_target = round(curr_price * 1.05, 1)
            short_stop = round(min(ma5 * 0.98, curr_price * 0.95), 1)
            
            # 2. 中線波段 (1~3個月)：月線支撐防守，目標波段壓力高點 (+10%~+15%)
            mid_target = round(max(recent_high, curr_price * 1.10), 1)
            mid_stop = round(curr_price * 0.92, 1)
            
            # 3. 長線價值 (半年~1年)：季線或估值目標 (+20%~+30%)
            long_target = round(max(recent_high * 1.15, curr_price * 1.25), 1)
            long_stop = round(min(ma60 * 0.95, curr_price * 0.85), 1)
            
            st.markdown(f"""
            <div style="margin-bottom: 15px;">
                <h1 style="margin: 0; font-size: 2.1rem; color: #f0f6fc;">{display_name} <span style="font-size: 1.2rem; color: #58a6ff;">({clean_code})</span></h1>
                <span style="color: #8b949e; font-size: 0.9rem;">更新時間：<b>{now_time_str}</b> ｜ 最新報價：<b style="color:{'#f85149' if diff>=0 else '#3fb950'}; font-size: 1.1rem;">${curr_price:,.2f}</b> ({diff:+,.2f}, {pct:+.2f}%)</span>
            </div>
            """, unsafe_allow_html=True)
            
            # -------------------------------------------------------------
            # 【全新升級】短・中・長線完整量化點位推薦看板
            # -------------------------------------------------------------
            st.markdown("### 🎯 短・中・長線量化進出場點位推薦")
            b1, b2, b3, b4 = st.columns(4)
            
            with b1:
                st.markdown(f"""
                <div class="target-box" style="border-left: 4px solid #f85149;">
                    <div class="target-title">💡 建議買進區間 (分批建倉)</div>
                    <div class="target-val-buy">${short_buy_low} ~ ${short_buy_high}</div>
                    <div class="target-desc">回測 5MA / 月線支撐右側進場</div>
                </div>
                """, unsafe_allow_html=True)
                
            with b2:
                st.markdown(f"""
                <div class="target-box" style="border-left: 4px solid #3fb950;">
                    <div class="target-title">⚡ 短線獲利目標 (1~2週)</div>
                    <div class="target-val-sell">${short_target}</div>
                    <div class="target-desc">預期空間 +{((short_target-curr_price)/curr_price)*100:.1f}% ｜ 停損 ${short_stop}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with b3:
                st.markdown(f"""
                <div class="target-box" style="border-left: 4px solid #38bdf8;">
                    <div class="target-title">🌊 中線波段目標 (1~3個月)</div>
                    <div style="font-size: 1.45rem; font-weight: 700; color: #38bdf8;">${mid_target}</div>
                    <div class="target-desc">預期空間 +{((mid_target-curr_price)/curr_price)*100:.1f}% ｜ 停損 ${mid_stop}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with b4:
                st.markdown(f"""
                <div class="target-box" style="border-left: 4px solid #a855f7;">
                    <div class="target-title">🏛️ 長線價值目標 (半年~1年)</div>
                    <div style="font-size: 1.45rem; font-weight: 700; color: #c084fc;">${long_target}</div>
                    <div class="target-desc">預期空間 +{((long_target-curr_price)/curr_price)*100:.1f}% ｜ 防守 ${long_stop}</div>
                </div>
                """, unsafe_allow_html=True)

            tab1, tab2, tab3 = st.tabs([
                "📊 支撐壓力 K 線與全指標",
                "⏳ 短中長線多空維度評估",
                "🏢 基本面真實財務評價"
            ])
            
            # -------------------------------------------------------------
            # TAB 1: 診斷入手確定性 + K 線圖
            # -------------------------------------------------------------
            with tab1:
                col_chart, col_sig = st.columns([7.2, 2.8])
                
                with col_sig:
                    st.markdown("#### 🚦 確定能否入手 (AI 核心診斷)")
                    
                    c_ma = curr_price > latest["MA20"]
                    c_macd = latest["MACD_OSC"] > 0
                    c_kd = (latest["K"] > latest["D"]) and (latest["K"] < 75)
                    c_rsi_safe = latest["RSI"] < 70
                    c_near_sup = curr_price <= (ma20 * 1.03)
                    
                    entry_points = sum([c_ma, c_macd, c_kd, c_rsi_safe])
                    
                    if entry_points >= 4:
                        d_class = "decision-strong-buy"
                        d_title = "🟢 【強烈建議入手】多頭主升段確立"
                        d_desc = f"各項技術指標共振偏多，站穩月線 (${latest['MA20']:.1f}) 且動能充沛，適合右側進場或加碼持有。"
                    elif c_near_sup and c_ma:
                        d_class = "decision-batch-buy"
                        d_title = "🔵 【可分批入手】回測支撐有守"
                        d_desc = f"股價回測月線/支撐區 (${ma20:.1f})，盈虧比極佳，建議採分批掛單建倉策略。"
                    elif latest["RSI"] >= 70:
                        d_class = "decision-wait"
                        d_title = "🟠 【暫緩入手】短線指標過熱 (防拉回)"
                        d_desc = f"RSI 高達 {latest['RSI']:.1f} 處於超買區，隨時可能回測均線，請勿追高，靜待回檔至支撐再進。"
                    elif not c_ma:
                        d_class = "decision-avoid"
                        d_title = "🔴 【不宜入手】短期格局偏空"
                        d_desc = f"股價位於月線 (${latest['MA20']:.1f}) 之下，空方力道主導，尚未出現止跌打底轉折訊號。"
                    else:
                        d_class = "decision-wait"
                        d_title = "🟡 【建議觀望】等待方向明朗"
                        d_desc = f"處於 ${ma20:.1f} ~ ${res1:.1f} 區間盤整，等待帶量突破壓力位後再順勢進場。"
                        
                    st.markdown(f"""
                    <div class="{d_class}">
                        <div style="font-size: 1.05rem; font-weight: 700; color: #ffffff; margin-bottom: 6px;">{d_title}</div>
                        <div style="font-size: 0.85rem; color: #e2e8f0; line-height: 1.5;">{d_desc}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("##### 📋 入手指標檢核清單")
                    check_ma = "✅ 站上 20MA 月線 (多頭排列)" if c_ma else "❌ 跌破 20MA 月線 (走弱)"
                    check_macd = "✅ MACD 柱狀體為紅 (動能向上)" if c_macd else "❌ MACD 柱狀體為綠 (動能減弱)"
                    check_kd = "✅ KD 黃金交叉/偏多向上" if c_kd else "❌ KD 處於高檔過熱或死亡交叉"
                    check_rsi = f"✅ RSI 安全區 ({latest['RSI']:.1f})" if c_rsi_safe else f"⚠️ RSI 嚴重過熱 ({latest['RSI']:.1f})"
                    
                    st.markdown(f"""
                    * {check_ma}
                    * {check_macd}
                    * {check_kd}
                    * {check_rsi}
                    """)
                    
                    st.markdown("---")
                    st.markdown("#### 📐 各週期目標速查")
                    st.markdown(f"""
                    * **短線目標 (1~2週)**: `${short_target}`
                    * **中線波段目標 (1~3月)**: `${mid_target}`
                    * **長線價值目標 (半年~1年)**: `${long_target}`
                    * **短線防守停損**: `${short_stop}`
                    """)
                    
                with col_chart:
                    sub_indicator = st.radio(
                        "📊 切換下方副圖指標：",
                        options=["Volume (成交量)", "MACD (指數平滑異同)", "KD (隨機指標 14,3)", "RSI (相對強弱 14)"],
                        index=0,
                        horizontal=True
                    )
                    
                    fig = make_subplots(
                        rows=2, cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.06,
                        row_heights=[0.72, 0.28],
                        subplot_titles=('', f'副圖指標：{sub_indicator}')
                    )
                    
                    fig.add_trace(go.Candlestick(
                        x=df.index,
                        open=df['Open'], high=df['High'],
                        low=df['Low'], close=df['Close'],
                        name='K線',
                        increasing_line_color='#f85149', increasing_fillcolor='#f85149',
                        decreasing_line_color='#3fb950', decreasing_fillcolor='#3fb950'
                    ), row=1, col=1)
                    
                    fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5MA', line=dict(color='#d29922', width=1.2)), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20MA(月線)', line=dict(color='#58a6ff', width=1.6)), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name='60MA(季線)', line=dict(color='#bc8cff', width=1.8)), row=1, col=1)
                    
                    # 標註中線壓力與短線支撐
                    fig.add_hline(
                        y=res1, line_dash="dash", line_color="#f85149", line_width=2,
                        annotation_text=f" 🚨 波段壓力 ${res1} ",
                        annotation_position="top left",
                        annotation_font_size=13,
                        annotation_font_color="#ffffff",
                        annotation_bgcolor="rgba(248, 81, 73, 0.85)",
                        row=1, col=1
                    )
                    fig.add_hline(
                        y=sup1, line_dash="dash", line_color="#3fb950", line_width=2,
                        annotation_text=f" 🛡️ 月線支撐 ${sup1} ",
                        annotation_position="bottom left",
                        annotation_font_size=13,
                        annotation_font_color="#ffffff",
                        annotation_bgcolor="rgba(63, 185, 80, 0.85)",
                        row=1, col=1
                    )
                    
                    if "Volume" in sub_indicator:
                        vol_colors = ['#f85149' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#3fb950' for i in range(len(df))]
                        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color=vol_colors), row=2, col=1)
                    elif "MACD" in sub_indicator:
                        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_DIF'], name='DIF快線', line=dict(color='#58a6ff', width=1.4)), row=2, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_DEM'], name='MACD慢線', line=dict(color='#d29922', width=1.4)), row=2, col=1)
                        colors = ['#f85149' if val >= 0 else '#3fb950' for val in df['MACD_OSC']]
                        fig.add_trace(go.Bar(x=df.index, y=df['MACD_OSC'], name='OSC柱狀體', marker_color=colors), row=2, col=1)
                    elif "KD" in sub_indicator:
                        fig.add_trace(go.Scatter(x=df.index, y=df['K'], name='K值 (14,3)', line=dict(color='#f85149', width=1.5)), row=2, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['D'], name='D值 (14,3)', line=dict(color='#3fb950', width=1.5)), row=2, col=1)
                        fig.add_hline(y=80, line_dash="dot", line_color="#f85149", row=2, col=1)
                        fig.add_hline(y=20, line_dash="dot", line_color="#3fb950", row=2, col=1)
                    elif "RSI" in sub_indicator:
                        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI (14)', line=dict(color='#f778ba', width=1.5)), row=2, col=1)
                        fig.add_hline(y=70, line_dash="dot", line_color="#f85149", row=2, col=1)
                        fig.add_hline(y=30, line_dash="dot", line_color="#3fb950", row=2, col=1)
                        
                    fig.update_layout(
                        paper_bgcolor='#0e1117',
                        plot_bgcolor='#161b22',
                        font=dict(color='#8b949e'),
                        height=560,
                        xaxis_rangeslider_visible=False,
                        margin=dict(l=10, r=10, t=10, b=10),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    fig.update_xaxes(gridcolor='#21262d', zeroline=False)
                    fig.update_yaxes(gridcolor='#21262d', zeroline=False)
                    st.plotly_chart(fig, use_container_width=True)

            # -------------------------------------------------------------
            # TAB 2: 短線 / 中線 / 長線 實戰維度評估
            # -------------------------------------------------------------
            with tab2:
                st.markdown("#### ⏳ 該檔標的【短線・中線・長線】多空維度量化評估")
                
                s_bull = curr_price > latest["MA5"] and latest["K"] > latest["D"]
                s_tag = "🚀 短線偏多攻擊" if s_bull else "⚠️ 短線震盪整理"
                s_color = "#f85149" if s_bull else "#e3b341"
                
                m_bull = curr_price > latest["MA20"] and latest["MACD_OSC"] > 0
                m_tag = "📈 中線多頭排列" if m_bull else "📉 中線偏空修正"
                m_color = "#f85149" if m_bull else "#3fb950"
                
                roe_val = info.get("returnOnEquity")
                l_bull = curr_price > latest["MA60"] or (roe_val is not None and roe_val >= 0.15)
                l_tag = "💎 長線體質優異 (具護城河)" if l_bull else "🛡️ 長線景氣循環 (逢低佈局)"
                l_color = "#58a6ff" if l_bull else "#8b949e"
                
                col_t1, col_t2, col_t3 = st.columns(3)
                
                with col_t1:
                    st.markdown(f"""
                    <div class="card-box" style="border-top: 3px solid {s_color};">
                        <h4 style="color: {s_color}; margin-top: 0;">⚡ 短線操作 (1 ~ 2 週)</h4>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #ffffff; margin-bottom: 8px;">{s_tag}</div>
                        <ul style="color: #cbd5e1; font-size: 0.88rem; padding-left: 18px; line-height: 1.6;">
                            <li><b>短線獲利目標</b>：<b>${short_target}</b> (預期 +{((short_target-curr_price)/curr_price)*100:.1f}%)。</li>
                            <li><b>核心觀察指標</b>：5日均線 (<b>${latest['MA5']:.2f}</b>)、KD隨機指標 (<b>{latest['K']:.1f}</b>)。</li>
                            <li><b>進出場原則</b>：站上 5MA 順勢做多；KD 高檔 (>80) 死亡交叉時分批停利。</li>
                            <li><b>關鍵停損點</b>：<b>${short_stop}</b> (跌破 5 日線即刻防守)。</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with col_t2:
                    st.markdown(f"""
                    <div class="card-box" style="border-top: 3px solid {m_color};">
                        <h4 style="color: {m_color}; margin-top: 0;">🌊 中線波段 (1 ~ 3 個月)</h4>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #ffffff; margin-bottom: 8px;">{m_tag}</div>
                        <ul style="color: #cbd5e1; font-size: 0.88rem; padding-left: 18px; line-height: 1.6;">
                            <li><b>波段滿足目標</b>：<b>${mid_target}</b> (預期 +{((mid_target-curr_price)/curr_price)*100:.1f}%)。</li>
                            <li><b>核心觀察指標</b>：20日生命線 (<b>${latest['MA20']:.2f}</b>)、MACD柱狀體。</li>
                            <li><b>波段買進區</b>：回測月線有守 (${sup1:.1f}) 為右側最佳買點。</li>
                            <li><b>波段防守點</b>：<b>${mid_stop}</b> (跌破月線轉弱減碼)。</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with col_t3:
                    st.markdown(f"""
                    <div class="card-box" style="border-top: 3px solid {l_color};">
                        <h4 style="color: {l_color}; margin-top: 0;">🏛️ 長線存股與價值 (半年 ~ 1年)</h4>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #ffffff; margin-bottom: 8px;">{l_tag}</div>
                        <ul style="color: #cbd5e1; font-size: 0.88rem; padding-left: 18px; line-height: 1.6;">
                            <li><b>長線價值目標</b>：<b>${long_target}</b> (預期 +{((long_target-curr_price)/curr_price)*100:.1f}%)。</li>
                            <li><b>核心觀察指標</b>：60日季線 (<b>${latest['MA60']:.2f}</b>)、ROE與殖利率。</li>
                            <li><b>存股進場策略</b>：拉回至季線鐵板 (${sup2:.1f}) 採取金字塔分批建倉。</li>
                            <li><b>長期底線</b>：<b>${long_stop}</b> (基本面長期獲利未衰退可持續持有)。</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)

            # -------------------------------------------------------------
            # TAB 3: 基本面
            # -------------------------------------------------------------
            with tab3:
                st.markdown("#### 🏢 即時真實財務指標與基本面評價")
                f1, f2 = st.columns(2)
                
                pe_live = info.get("trailingPE")
                pb_live = info.get("priceToBook")
                yield_live = info.get("dividendYield")
                eps_live = info.get("trailingEps")
                roe_live = info.get("returnOnEquity")
                
                pe_text = f"{pe_live:.2f} 倍" if pe_live is not None and pe_live > 0 else "N/A (虧損或指數無資料)"
                pb_text = f"{pb_live:.2f} 倍" if pb_live is not None else "N/A"
                yield_text = f"{yield_live:.2f}%" if yield_live is not None else "無配息 / 無資料"
                eps_text = f"${eps_live:.2f}" if eps_live is not None else "N/A"
                roe_text = f"{roe_live*100:.2f}%" if roe_live is not None else "N/A"
                
                with f1:
                    st.markdown("##### 📌 核心財務估值數據")
                    f_df1 = pd.DataFrame({
                        "指標名稱": ["本益比 (P/E)", "股價淨值比 (P/B)", "每股盈餘 (EPS)", "現金殖利率", "股東權益報酬率 (ROE)"],
                        "數值": [pe_text, pb_text, eps_text, yield_text, roe_text]
                    })
                    st.dataframe(f_df1, use_container_width=True, hide_index=True)
                    
                with f2:
                    st.markdown("##### 🛡️ 營運體質與護城河評鑑")
                    
                    if roe_live is not None and roe_live >= 0.18:
                        star_rating = "⭐⭐⭐⭐⭐ (頂級藍籌股)"
                        comment = f"獲利能力極佳，ROE 達 **{roe_text}**，具備強大產業護城河，拉回至季線均為長線佈局優質標的。"
                    elif roe_live is not None and roe_live >= 0.10:
                        star_rating = "⭐⭐⭐⭐ (優質營運企業)"
                        comment = f"營運體質穩定，當前 ROE 為 **{roe_text}**，適合逢低分批定期定額佈局。"
                    elif pe_live is not None and pe_live > 30:
                        star_rating = "⭐⭐⭐ (高成長/高估值題材股)"
                        comment = f"當前本益比 **{pe_text}** 處於較高水準，市場給予高成長溢價，建議順勢搭配技術面操作。"
                    else:
                        star_rating = "⭐⭐⭐ (穩健型 / 景氣循環股 / 大盤指數)"
                        comment = "受總體經濟及產業週期波動影響，建議逢低於支撐區間介入，嚴格設定停損點。"
                        
                    st.markdown(f"""
                    <div class="card-box">
                        <p><b>長線存股評級</b>：{star_rating}</p>
                        <p><b>即時診斷</b>：{comment}</p>
                        <p style="color: #8b949e; font-size: 0.85rem;"><b>資料來源</b>：全球金融市場即時開放數據</p>
                    </div>
                    """, unsafe_allow_html=True)
